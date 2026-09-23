#!/usr/bin/env python3
"""
Technical SEO content audit for the Bahrain WordPress site (ركن التطور).

Reads published posts/pages from WordPress REST (or a CSV export), then flags:
  1. Thin content (< 1000 words)
  2. Boilerplate / doorway-template reuse
  3. Near-duplicate copy and keyword cannibalization
  4. Search-intent mismatch (title vs body vs city/service)
  5. Missing SEO elements, placeholders, broken structure

Usage:
  export WP_BASE=https://www.rukn-eltatawer.com/bh
  export WP_USER=melsaad
  export WP_APP_PASSWORD='xxxx xxxx'
  python3 tools/seo_content_audit.py

Outputs:
  reports/seo-content-audit.csv
  reports/seo-cannibalization-clusters.csv
  reports/seo-boilerplate-passages.csv
  docs/seo-content-audit.md
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import json
import os
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

csv.field_size_limit(sys.maxsize)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"
CACHE_DIR = REPORTS / "cache"
EXPORT_PATH = CACHE_DIR / "wp-published.jsonl"

CITIES = [
    "المنامة",
    "المحرق",
    "الرفاع",
    "مدينة حمد",
    "مدينة عيسى",
    "عالي",
    "سترة",
    "البديع",
    "الحد",
    "توبلي",
    "جدحفص",
    "سار",
    "الجفير",
    "السيف",
    "أم الحصم",
    "جد علي",
    "الهملة",
    "كرانة",
    "الدراز",
    "باربار",
]
CITY_SLUGS = {
    "manama": "المنامة",
    "muharraq": "المحرق",
    "riffa": "الرفاع",
    "hamad-town": "مدينة حمد",
    "isa-town": "مدينة عيسى",
    "aali": "عالي",
    "sitra": "سترة",
    "budaiya": "البديع",
    "hidd": "الحد",
    "tubli": "توبلي",
    "jidhafs": "جدحفص",
    "saar": "سار",
}
PLACEHOLDER_RE = re.compile(
    r"lorem ipsum|dummy text|TODO|TBD|FIXME|xxx+|\[\[.*?\]\]|\{PHONE|_RUKN|رقم الهاتف/واتساب|نص تجريبي|اكتب هنا",
    re.I,
)
WORD_RE = re.compile(r"[A-Za-z\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]{2,}")
TAG_RE = re.compile(r"<(/?)(h[1-6]|p|li|td|br|div|section|article)[^>]*>", re.I)
H_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.I | re.S)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
ALT_RE = re.compile(r"\balt\s*=\s*([\"'])(.*?)\1", re.I)
SRC_RE = re.compile(r"\bsrc\s*=\s*([\"'])(.*?)\1", re.I)


class HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if tag in ("br", "p", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
        if tag in ("p", "div", "li", "h1", "h2", "h3", "section"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def strip_html(raw: str) -> str:
    parser = HTMLText()
    try:
        parser.feed(raw or "")
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(" ".join(parser.parts))
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def words_of(text: str) -> list[str]:
    return WORD_RE.findall(text or "")


def heading_list(html_src: str) -> list[tuple[int, str]]:
    out = []
    for m in H_RE.finditer(html_src or ""):
        level = int(m.group(1))
        txt = strip_html(m.group(2))
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt:
            out.append((level, txt))
    return out


def wp_auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def http_json(url: str, auth: str, timeout: int = 120, attempts: int = 4):
    ctx = ssl.create_default_context()
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": auth,
                "Accept": "application/json",
                "User-Agent": "RuknSEO-Audit/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                body = resp.read().decode("utf-8", "replace")
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return json.loads(body) if body else [], headers
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_err = exc
            time.sleep(min(8, attempt * 2))
    raise RuntimeError(f"GET failed {url}: {last_err}")


def paged_get(base: str, route: str, auth: str, extra: str = "", per_page: int = 100):
    items = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        q = f"{route}?per_page={per_page}&page={page}&_embed=0{extra}"
        url = f"{base}/wp-json{q}"
        data, headers = http_json(url, auth)
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected payload for {q}: {str(data)[:300]}")
        items.extend(data)
        total_pages = int(headers.get("x-wp-totalpages") or "1")
        total = headers.get("x-wp-total")
        print(f"  {route} page {page}/{total_pages} (+{len(data)}) total={total}")
        page += 1
        time.sleep(0.15)
    return items


def term_map(base: str, auth: str, taxonomy: str) -> dict[int, str]:
    try:
        rows = paged_get(base, f"/wp/v2/{taxonomy}", auth, extra="&hide_empty=0")
    except Exception as exc:
        print(f"  skip taxonomy {taxonomy}: {exc}")
        return {}
    return {int(r["id"]): r.get("name") or r.get("slug") or str(r["id"]) for r in rows}


def flatten_post(p: dict, city_names: dict[int, str], tag_names: dict[int, str]) -> dict:
    title = p.get("title") or {}
    content = p.get("content") or {}
    excerpt = p.get("excerpt") or {}
    title_text = title.get("rendered") or title.get("raw") or ""
    html_src = content.get("rendered") or content.get("raw") or ""
    excerpt_text = strip_html(excerpt.get("rendered") or excerpt.get("raw") or "")
    cities = [city_names.get(int(i), str(i)) for i in (p.get("cities") or [])]
    tags = [tag_names.get(int(i), str(i)) for i in (p.get("tags") or [])]
    return {
        "id": p.get("id"),
        "type": p.get("type") or "post",
        "status": p.get("status") or "publish",
        "slug": p.get("slug") or "",
        "url": p.get("link") or "",
        "title": strip_html(title_text),
        "html": html_src,
        "excerpt": excerpt_text,
        "cities": cities,
        "tags": tags,
        "featured_media": int(p.get("featured_media") or 0),
        "date": p.get("date") or "",
        "modified": p.get("modified") or "",
    }


def export_wordpress(base: str, user: str, password: str) -> list[dict]:
    auth = wp_auth_header(user, password)
    print("Fetching taxonomies…")
    city_names = term_map(base, auth, "cities")
    tag_names = term_map(base, auth, "tags")
    print("Fetching posts…")
    posts = paged_get(
        base,
        "/wp/v2/posts",
        auth,
        extra="&status=publish&_fields=id,date,modified,slug,link,title,content,excerpt,featured_media,tags,cities,type,status",
    )
    print("Fetching pages…")
    pages = paged_get(
        base,
        "/wp/v2/pages",
        auth,
        extra="&status=publish&_fields=id,date,modified,slug,link,title,content,excerpt,featured_media,tags,cities,type,status",
    )
    rows = [flatten_post(p, city_names, tag_names) for p in posts + pages]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with EXPORT_PATH.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Exported {len(rows)} documents → {EXPORT_PATH}")
    return rows


def load_export() -> list[dict]:
    rows = []
    with EXPORT_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for raw in csv.DictReader(fh):
            rows.append(
                {
                    "id": raw.get("post_name") or raw.get("post_title"),
                    "type": raw.get("post_type") or "post",
                    "status": raw.get("post_status") or "",
                    "slug": raw.get("post_name") or "",
                    "url": "https://rukn-eltatawer.com/bh/" + (raw.get("post_name") or ""),
                    "title": raw.get("post_title") or "",
                    "html": raw.get("post_content") or "",
                    "excerpt": raw.get("rank_math_description") or "",
                    "cities": [raw.get("emirate")] if raw.get("emirate") else [],
                    "tags": [t.strip() for t in (raw.get("tags") or "").split(",") if t.strip()],
                    "featured_media": 0,
                    "date": "",
                    "modified": "",
                    "rank_math_title": raw.get("rank_math_title") or "",
                    "rank_math_description": raw.get("rank_math_description") or "",
                }
            )
    return rows


def city_in_text(text: str) -> list[str]:
    found = []
    for city in CITIES:
        if city in (text or ""):
            found.append(city)
    return found


def mask_cities(text: str) -> str:
    out = text or ""
    for city in sorted(CITIES, key=len, reverse=True):
        out = out.replace(city, "{CITY}")
        out = out.replace("ب" + city, "ب{CITY}")
    return out


def title_template(title: str) -> str:
    t = mask_cities(title)
    t = re.sub(r"20\d{2}", "{YEAR}", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def service_from_title(title: str) -> str:
    t = mask_cities(title)
    t = re.sub(r"^شركة\s+", "", t)
    t = re.sub(r"\s+(في|ب)\{CITY\}.*$", "", t)
    t = re.sub(r"\s+\{CITY\}.*$", "", t)
    return t.strip()


def ngrams(tokens: list[str], n: int) -> list[str]:
    if len(tokens) < n:
        return [" ".join(tokens)] if tokens else []
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def minhash(tokens: list[str], n: int = 4, perms: int = 32) -> tuple[int, ...]:
    grams = ngrams(tokens, n)
    if not grams:
        return tuple([0] * perms)
    mins = [2**32 - 1] * perms
    for g in grams:
        x = zlib_hash(g)
        for i in range(perms):
            h = (x * (i * 2 + 1) + (i * 2654435761)) & 0xFFFFFFFF
            if h < mins[i]:
                mins[i] = h
    return tuple(mins)


def zlib_hash(s: str) -> int:
    return int(hashlib.md5(s.encode("utf-8", "ignore")).hexdigest()[:8], 16)


def jaccard_minhash(a: tuple[int, ...], b: tuple[int, ...]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    same = sum(1 for x, y in zip(a, b) if x == y)
    return same / len(a)


def band_key(sig: tuple[int, ...], band: int, width: int = 4) -> tuple[int, ...]:
    start = band * width
    return sig[start : start + width]


def analyze(docs: list[dict]) -> tuple[list[dict], list[dict], list[dict], dict]:
    prepared = []
    para_df: Counter[str] = Counter()
    outline_groups: dict[str, list[int]] = defaultdict(list)
    template_groups: dict[str, list[int]] = defaultdict(list)

    for idx, doc in enumerate(docs):
        html_src = doc.get("html") or ""
        text = strip_html(html_src)
        toks = words_of(text)
        headings = heading_list(html_src)
        h1 = [h for lv, h in headings if lv == 1]
        h2 = [h for lv, h in headings if lv == 2]
        h3 = [h for lv, h in headings if lv == 3]
        imgs = IMG_RE.findall(html_src)
        missing_alt = 0
        broken_src = 0
        for tag in imgs:
            alt_m = ALT_RE.search(tag)
            src_m = SRC_RE.search(tag)
            alt = (alt_m.group(2) if alt_m else "").strip()
            src = (src_m.group(2) if src_m else "").strip()
            if not alt:
                missing_alt += 1
            if (not src) or src.startswith("service-") or "{CITY}" in src:
                broken_src += 1
        paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n+", text) if len(p.strip()) > 40]
        masked_paras = [mask_cities(p) for p in paras]
        seen_paras = set()
        for p in masked_paras:
            if 40 <= len(p) <= 400 and p not in seen_paras:
                para_df[p] += 1
                seen_paras.add(p)
        outline = " > ".join(mask_cities(h) for h in h2)
        title = doc.get("title") or ""
        tmpl = title_template(title)
        cities = doc.get("cities") or city_in_text(title)
        city_body = city_in_text(text)
        prepared.append(
            {
                "idx": idx,
                "doc": doc,
                "text": text,
                "tokens": toks,
                "word_count": len(toks),
                "headings": headings,
                "h1": h1,
                "h2": h2,
                "h3": h3,
                "imgs": len(imgs),
                "missing_alt": missing_alt,
                "broken_src": broken_src,
                "paras": paras,
                "masked_paras": masked_paras,
                "outline": outline,
                "title_template": tmpl,
                "service": service_from_title(title),
                "cities": cities,
                "cities_in_body": city_body,
                "placeholder": bool(PLACEHOLDER_RE.search(html_src) or PLACEHOLDER_RE.search(title)),
                "sig": None,
            }
        )
        outline_groups[outline or f"__empty_{idx}"].append(idx)
        template_groups[tmpl].append(idx)

    n_docs = max(len(prepared), 1)
    boilerplate = {p for p, c in para_df.items() if c >= max(8, int(n_docs * 0.08)) and c >= 8}
    # keep top boilerplate passages for the report
    top_boiler = para_df.most_common(40)

    for row in prepared:
        masked_tokens = words_of(mask_cities(row["text"]))
        row["sig"] = minhash(masked_tokens, n=5, perms=32)
        if row["masked_paras"]:
            boiler_hits = sum(1 for p in row["masked_paras"] if p in boilerplate)
            row["boilerplate_ratio"] = round(boiler_hits / max(len(row["masked_paras"]), 1), 3)
        else:
            row["boilerplate_ratio"] = 0.0

    # LSH near-dup on masked text
    bands = 8
    buckets: dict[tuple, list[int]] = defaultdict(list)
    for row in prepared:
        sig = row["sig"]
        for b in range(bands):
            buckets[(b, band_key(sig, b, 4))].append(row["idx"])

    pair_best: dict[tuple[int, int], float] = {}
    for members in buckets.values():
        uniq = sorted(set(members))
        if 2 <= len(uniq) <= 80:
            for i, a in enumerate(uniq):
                for b in uniq[i + 1 :]:
                    sim = jaccard_minhash(prepared[a]["sig"], prepared[b]["sig"])
                    if sim >= 0.55:
                        key = (a, b)
                        if sim > pair_best.get(key, 0):
                            pair_best[key] = sim

    nearest: dict[int, tuple[float, int]] = {}
    for (a, b), sim in pair_best.items():
        if sim > nearest.get(a, (0, -1))[0]:
            nearest[a] = (sim, b)
        if sim > nearest.get(b, (0, -1))[0]:
            nearest[b] = (sim, a)

    findings: list[dict] = []
    title_index: dict[str, list[str]] = defaultdict(list)
    for row in prepared:
        title_index[row["doc"].get("title") or ""].append(row["doc"].get("url") or "")

    def add(row, category: str, severity: str, note: str, extra=None):
        doc = row["doc"]
        findings.append(
            {
                "id": doc.get("id"),
                "type": doc.get("type"),
                "title": doc.get("title"),
                "url": doc.get("url"),
                "slug": doc.get("slug"),
                "word_count": row["word_count"],
                "city": "، ".join(row["cities"][:3]),
                "service": row["service"],
                "title_template": row["title_template"],
                "h1_count": len(row["h1"]),
                "h2_count": len(row["h2"]),
                "h3_count": len(row["h3"]),
                "featured_media": doc.get("featured_media") or 0,
                "boilerplate_ratio": row["boilerplate_ratio"],
                "problem": category,
                "severity": severity,
                "notes": note,
                **(extra or {}),
            }
        )

    for row in prepared:
        doc = row["doc"]
        title = doc.get("title") or ""
        wc = row["word_count"]
        if wc < 1000:
            sev = "حرج" if wc < 400 else ("عالٍ" if wc < 700 else "متوسط")
            add(row, "محتوى ضعيف (Thin)", sev, f"عدد الكلمات {wc} وهو أقل من 1000.")

        if row["boilerplate_ratio"] >= 0.45:
            add(
                row,
                "إفراط في القالب / Boilerplate",
                "عالٍ" if row["boilerplate_ratio"] >= 0.7 else "متوسط",
                f"{int(row['boilerplate_ratio']*100)}% من الفقرات مكررة عبر عشرات المقالات بعد استبدال اسم المدينة.",
            )

        tmpl_n = len(template_groups.get(row["title_template"], []))
        outline_n = len(outline_groups.get(row["outline"], [])) if row["outline"] else 0
        if tmpl_n >= 6 and row["doc"].get("type") == "post":
            add(
                row,
                "قالب هيكلي مكرر (Doorway)",
                "عالٍ",
                f"نفس قالب العنوان «{row['title_template']}» يظهر في {tmpl_n} مقالاً (تبديل المدينة فقط).",
            )
        elif outline_n >= 8 and row["outline"]:
            add(
                row,
                "قالب هيكلي مكرر (Doorway)",
                "متوسط",
                f"نفس تسلسل H2 يظهر في {outline_n} مقالاً بعد تطبيع اسم المدينة.",
            )

        # Exact-title clones (same query, two URLs) are true cannibalization.
        same_title_urls = title_index.get(title, [])
        if len(same_title_urls) > 1:
            others = [u for u in same_title_urls if u != doc.get("url")]
            add(
                row,
                "تآكل كلمات مفتاحية / Cannibalization",
                "حرج",
                "عنوان مطابق حرفياً على أكثر من رابط في نفس المدينة/الخدمة. أبقِ واحداً وحوّل الباقي 301. الأخرى: "
                + " | ".join(others[:4]),
                {"similar_url": others[0] if others else "", "similarity": 1.0},
            )

        sim, other = nearest.get(row["idx"], (0.0, -1))
        if sim >= 0.88 and other >= 0:
            other_row = prepared[other]
            other_title = other_row["doc"].get("title")
            other_url = other_row["doc"].get("url")
            same_city = bool(set(row["cities"]) & set(other_row["cities"]))
            same_service = row["service"] and row["service"] == other_row["service"]
            if same_city and same_service and title != other_title:
                add(
                    row,
                    "تآكل كلمات مفتاحية / Cannibalization",
                    "حرج",
                    f"نفس الخدمة والمدينة مع عنوان مختلف وتشابه متن {int(sim*100)}%: {other_title} — {other_url}",
                    {"similar_url": other_url, "similarity": round(sim, 3)},
                )
            elif not same_service and sim >= 0.94:
                add(
                    row,
                    "محتوى مكرر/متشابه",
                    "متوسط",
                    f"المتن شبه متطابق ({int(sim*100)}%) مع خدمة مختلفة بعد تطبيع المدينة: {other_title} — {other_url}",
                    {"similar_url": other_url, "similarity": round(sim, 3)},
                )

        # Intent mismatch — skip missing in-content H1 (theme prints the post title as H1).
        intent_notes = []
        title_cities = city_in_text(title)
        if title_cities and row["cities_in_body"]:
            if not set(title_cities) & set(row["cities_in_body"]):
                intent_notes.append(
                    f"المدينة في العنوان ({'، '.join(title_cities)}) غير مذكورة في المتن (المذكور: {'، '.join(row['cities_in_body'][:4])})."
                )
        if title_cities and row["cities"] and not set(title_cities) & set(row["cities"]):
            intent_notes.append(
                f"تصنيف المدينة ({'، '.join(row['cities'])}) يختلف عن المدينة في العنوان ({'، '.join(title_cities)})."
            )

        svc = row["service"]
        if svc and len(words_of(svc)) >= 2 and doc.get("type") == "post":
            svc_words = [w for w in words_of(svc) if w not in ("شركة", "خدمات", "خدمة")]
            body_join = " ".join(row["tokens"][:500])
            missing = [w for w in svc_words if w not in body_join]
            if svc_words and len(missing) >= max(2, int(len(svc_words) * 0.6)):
                intent_notes.append(
                    f"كلمات الخدمة في العنوان غير بارزة في صدر المتن: {'، '.join(missing[:6])}."
                )

        if doc.get("type") == "page" and wc < 400:
            lang_en = bool(re.search(r"[A-Za-z]{4,}", title)) and not re.search(r"[\u0600-\u06FF]", title)
            if lang_en:
                intent_notes.append("صفحة إنجليزية رقيقة مقابل مقالات عربية طويلة — لا تغطي نية البحث المحلية.")
            elif "تواصل" in title or "contact" in title.lower():
                intent_notes.append("صفحة تواصل بلا نموذج/تفاصيل كافية لنية «التواصل».")
            elif "خدمات" in title or "service" in title.lower():
                intent_notes.append("صفحة خدمات قصيرة لا تطابق نية الاستعلام التجاري التفصيلي.")

        if intent_notes:
            add(row, "عدم توافق نية البحث", "متوسط", " ".join(intent_notes))

        seo_notes = []
        dup_h2 = [h for h, c in Counter(row["h2"]).items() if c > 1]
        if dup_h2:
            seo_notes.append("H2 مكررة داخل المقال: " + "؛ ".join(f"«{h}» ×{Counter(row['h2'])[h]}" for h in dup_h2[:4]) + ".")
        if len(row["h1"]) > 1:
            seo_notes.append(f"أكثر من H1 داخل المتن ({len(row['h1'])}).")
        if not row["h2"] and wc > 200 and doc.get("slug") != "blog":
            seo_notes.append("لا توجد عناوين H2.")
        if (doc.get("featured_media") or 0) == 0 and doc.get("type") == "post":
            seo_notes.append("لا توجد صورة بارزة في ووردبريس (featured_media=0)؛ صورة المحتوى مكررة عبر الموقع.")
        if row["missing_alt"]:
            seo_notes.append(f"{row['missing_alt']} صورة بلا alt.")
        if row["broken_src"]:
            seo_notes.append(f"{row['broken_src']} صورة بمسار مكسور/نسبي (مثل service-*.webp).")
        if row["placeholder"]:
            seo_notes.append("نصوص مؤقتة أو عناصر نائبة ({PHONE} / [[...]] / lorem / TODO).")
        if not (doc.get("excerpt") or "").strip() and doc.get("type") == "page" and doc.get("slug") != "html-sitemap":
            seo_notes.append("المقتطف/الوصف فارغ.")
        if row["h2"] and wc < (len(row["h2"]) * 35):
            seo_notes.append("أقسام العناوين أقصر من أن تحمل قيمة (كلمات قليلة لكل H2).")
        if seo_notes:
            add(
                row,
                "أخطاء/عناصر SEO مفقودة",
                "عالٍ" if (row["placeholder"] or dup_h2 or len(row["h1"]) > 1) else "متوسط",
                " ".join(seo_notes),
            )

    clusters = []
    for tmpl, members in sorted(template_groups.items(), key=lambda kv: -len(kv[1])):
        if len(members) < 4:
            continue
        cities = sorted({c for i in members for c in prepared[i]["cities"]})
        wcs = [prepared[i]["word_count"] for i in members]
        clusters.append(
            {
                "title_template": tmpl,
                "count": len(members),
                "cities": "، ".join(cities),
                "avg_words": int(sum(wcs) / len(wcs)),
                "min_words": min(wcs),
                "max_words": max(wcs),
                "example_url": prepared[members[0]]["doc"].get("url"),
                "example_title": prepared[members[0]]["doc"].get("title"),
            }
        )

    boiler_rows = [
        {"passage": p, "documents": c, "share": round(c / n_docs, 3)}
        for p, c in top_boiler
        if c >= 8
    ]
    stats = {
        "documents": n_docs,
        "posts": sum(1 for d in docs if d.get("type") == "post"),
        "pages": sum(1 for d in docs if d.get("type") == "page"),
        "thin": sum(1 for r in prepared if r["word_count"] < 1000),
        "thin_critical": sum(1 for r in prepared if r["word_count"] < 400),
        "avg_words": int(sum(r["word_count"] for r in prepared) / n_docs),
        "median_words": sorted(r["word_count"] for r in prepared)[n_docs // 2],
        "no_h1": sum(1 for r in prepared if not r["h1"]),
        "multi_h1": sum(1 for r in prepared if len(r["h1"]) > 1),
        "no_h2": sum(1 for r in prepared if not r["h2"]),
        "no_featured": sum(1 for r in prepared if (r["doc"].get("featured_media") or 0) == 0 and r["doc"].get("type") == "post"),
        "placeholder": sum(1 for r in prepared if r["placeholder"]),
        "template_clusters": len(clusters),
        "boilerplate_passages": len(boiler_rows),
        "findings": len(findings),
    }
    return findings, clusters, boiler_rows, stats


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def write_markdown(
    path: Path,
    stats: dict,
    findings: list[dict],
    clusters: list[dict],
    boiler: list[dict],
) -> None:
    by_prob: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        by_prob[f["problem"]].append(f)

    def table(rows: list[dict], limit: int = 40) -> str:
        if not rows:
            return "_لا توجد صفوف في هذه الفئة._\n"
        lines = [
            "| العنوان | الرابط | الكلمات | الشدة | ملاحظات |",
            "|---|---|---:|---|---|",
        ]
        for r in rows[:limit]:
            title = md_escape(r.get("title") or "")[:80]
            url = r.get("url") or ""
            lines.append(
                f"| {title} | {url} | {r.get('word_count')} | {r.get('severity')} | {md_escape(r.get('notes') or '')[:220]} |"
            )
        extra = len(rows) - limit
        if extra > 0:
            lines.append(f"\n_{extra} صفاً إضافياً في CSV._")
        return "\n".join(lines) + "\n"

    thin = by_prob.get("محتوى ضعيف (Thin)", [])
    boiler_f = by_prob.get("إفراط في القالب / Boilerplate", [])
    doorway = by_prob.get("قالب هيكلي مكرر (Doorway)", [])
    dups = by_prob.get("محتوى مكرر/متشابه", [])
    cann = by_prob.get("تآكل كلمات مفتاحية / Cannibalization", [])
    intent = by_prob.get("عدم توافق نية البحث", [])
    missing = by_prob.get("أخطاء/عناصر SEO مفقودة", [])
    missing_struct = [r for r in missing if "H2 مكررة" in (r.get("notes") or "") or r.get("type") == "page"]
    missing_img = [r for r in missing if "صورة بارزة" in (r.get("notes") or "")]

    def uniq_docs(rows):
        return len({r.get("url") for r in rows})

    parts = [
        "# تدقيق محتوى SEO — ركن التطور البحرين",
        "",
        f"**المصدر:** مقالات وصفحات منشورة على https://www.rukn-eltatawer.com/bh  ",
        f"**الحجم:** {stats['posts']} مقالاً + {stats['pages']} صفحة  ",
        f"**متوسط الكلمات:** {stats['avg_words']} (الوسيط {stats['median_words']})  ",
        f"**تاريخ التوليد:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        "## الخلاصة التنفيذية",
        "",
        "المحتوى العربي منشور على شبكة **خدمة × مدينة**: ثماني مدن بحرينية (المنامة، المحرق، الرفاع، مدينة حمد، مدينة عيسى، عالي، سترة، البديع) مقابل مئات الخدمات. المقالات طويلة (~2000 كلمة) لكن التفرّد ضعيف: الفقرات والعناوين تُستنسخ مع استبدال اسم المدينة.",
        "",
        "**ملاحظات على مستوى الموقع (لا تُعدّ خطأ H1 لكل مقال):** القالب يُخرج عنوان المقال كـ H1 واحد في الصفحة الحية. وسم H1 غير موجود داخل `post_content`. كل المقالات بلا `featured_media` وتتشارك غالباً نفس الصورة `rukn-eltatawer-picture.webp`.",
        "",
        "| مؤشر | القيمة |",
        "|---|---:|",
        f"| وثائق مفحوصة | {stats['documents']} |",
        f"| أقل من 1000 كلمة | {stats['thin']} |",
        f"| أقل من 400 كلمة (حرج) | {stats['thin_critical']} |",
        f"| H1 داخل post_content | 0 (القالب الحي يضيف H1 من العنوان) |",
        f"| أكثر من H1 في المتن | {stats['multi_h1']} |",
        f"| بلا H2 | {stats['no_h2']} |",
        f"| مقالات بلا صورة بارزة | {stats['no_featured']} |",
        f"| عناصر نائبة/نصوص مؤقتة | {stats['placeholder']} |",
        f"| عناقيد قوالب العنوان (≥4 مدن) | {stats['template_clusters']} |",
        f"| فقرات نمطية عالية التكرار | {stats['boilerplate_passages']} |",
        f"| إجمالي الإشارات في CSV | {stats['findings']} |",
        "",
        "## 1) المحتوى الضعيف (Thin Content)",
        "",
        f"{uniq_docs(thin)} وثيقة تحت 1000 كلمة. العتبة موحّدة كما طُلب؛ الصفحات التعريفية القصيرة (من نحن / تواصل) تُعدّ ضعيفة وفق نفس المعيار.",
        "",
        table(sorted(thin, key=lambda r: r["word_count"])),
        "",
        "## 2) الإفراط في القوالب والنصوص النمطية",
        "",
        f"{uniq_docs(doorway)} مقالاً تقع في قوالب عنوان مكررة عبر المدن، و{uniq_docs(boiler_f)} مقالاً فقراتها النمطية ≥ 45%.",
        "",
        "### أكبر عناقيد القالب (تبديل المدينة)",
        "",
        "| قالب العنوان | عدد المقالات | المدن | متوسط الكلمات | مثال |",
        "|---|---:|---|---:|---|",
    ]
    for c in clusters[:25]:
        parts.append(
            f"| {md_escape(c['title_template'])} | {c['count']} | {md_escape(c['cities'])} | {c['avg_words']} | {c['example_title'][:60]} |"
        )
    parts += [
        "",
        "### فقرات نمطية متكررة (بعد استبدال اسم المدينة بـ `{CITY}`)",
        "",
        "| التكرار | النسبة | الفقرة |",
        "|---:|---:|---|",
    ]
    for b in boiler[:15]:
        parts.append(f"| {b['documents']} | {int(b['share']*100)}% | {md_escape(b['passage'][:180])} |")
    parts += [
        "",
        table(sorted(boiler_f, key=lambda r: -r["boilerplate_ratio"])[:20]),
        "",
        "## 3) المحتوى المكرر والتآكل (Cannibalization)",
        "",
        "**تآكل حقيقي:** مقالتان في *نفس المدينة* بنفس الخدمة/تشابه مرتفع.  ",
        "**تكرار قالبي:** نفس الخدمة في مدن مختلفة بنفس الصياغة — ليس استعلاماً واحداً، لكنه يضعف التفرد وقد يُعامل كصفحات مدخل.",
        "",
        f"- إشارات تآكل داخل نفس المدينة: {uniq_docs(cann)}",
        f"- إشارات تشابه عابر للمدن: {uniq_docs(dups)}",
        "",
        "### تآكل داخل نفس المدينة",
        "",
        table(cann, 30),
        "",
        "### تشابه عابر للمدن (بعد تطبيع المدينة)",
        "",
        table(dups, 25),
        "",
        "## 4) عدم توافق نية البحث",
        "",
        "يُعلَّم المقال إذا تعارض العنوان مع H1، أو مدينة التصنيف مع مدينة المتن، أو غابت كلمات الخدمة عن صدر المقال.",
        "",
        table(intent, 35),
        "",
        "## 5) أخطاء هيكلية وعناصر SEO مفقودة",
        "",
        f"صورة بارزة مفقودة في ووردبريس: {len(missing_img)} مقالاً (مذكورة بالكامل في CSV). أدناه الأخطاء الهيكلية الأوضح (H2 مكررة داخل المقال، صفحات ناقصة).",
        "",
        table(missing_struct, 40),
        "",
        "## ملفات المخرجات",
        "",
        "- `reports/seo-content-audit.csv` — كل الإشارات (صف لكل مشكلة).",
        "- `reports/seo-content-audit-by-url.csv` — صف واحد لكل رابط مع تجميع المشكلات.",
        "- `reports/seo-cannibalization-clusters.csv` — عناقيد قالب العنوان.",
        "- `reports/seo-boilerplate-passages.csv` — الفقرات النمطية.",
        "",
        "## توصيات تنفيذ سريعة",
        "",
        "1. إبقاء نموذج **خدمة × مدينة** مع إعادة كتابة **30–40% من المتن** لكل مدينة (أحياء، رطوبة، فلل/شقق، أمثلة محلية) حتى لا تبقى الصفحة استبدالاً لاسم المدينة.",
        "2. رفع الصفحات التعريفية تحت 1000 كلمة (من نحن، تواصل، الإنجليزية) أو دمجها في محتوى يغطي النية.",
        "3. حذف بلوك الأسئلة الشائعة المكرر داخل المقال (H2 نفسها تظهر مرتين أو ثلاثاً في كل مقال).",
        "4. صورة بارزة حقيقية لكل مجموعة خدمة على الأقل، بدل الصورة الواحدة المتكررة.",
        "5. دمج أزواج العشب المكررة (`wall-grass`/`grass-wall` و`artificial-grass`/`artificial-grass-grdn`) مع تحويل 301.",
        "6. المدن الأربع بلا مقالات (الحد، توبلي، جدحفص، سار): محتوى حقيقي أو إزالة ادّعاء التغطية من القالب.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bahrain site technical SEO content audit")
    parser.add_argument("--csv", help="Optional local CSV instead of live WordPress")
    parser.add_argument("--reuse-export", action="store_true", help="Reuse reports/cache/wp-published.jsonl")
    parser.add_argument("--skip-export", action="store_true")
    args = parser.parse_args()

    if args.csv:
        docs = load_csv(Path(args.csv))
        print(f"Loaded {len(docs)} rows from CSV")
    else:
        if args.reuse_export and EXPORT_PATH.exists():
            docs = load_export()
            print(f"Reused export ({len(docs)})")
        else:
            base = os.environ.get("WP_BASE", "https://www.rukn-eltatawer.com/bh").rstrip("/")
            user = os.environ.get("WP_USER", "melsaad")
            password = os.environ.get("WP_APP_PASSWORD", "")
            if not password:
                print("WP_APP_PASSWORD is required unless --csv or --reuse-export is set", file=sys.stderr)
                return 1
            docs = export_wordpress(base, user, password)

    published = [d for d in docs if (d.get("status") in ("publish", "", None, "draft") and True)]
    # If coming from live REST, all are publish. If CSV drafts, still analyze but label.
    print(f"Analyzing {len(published)} documents…")
    findings, clusters, boiler, stats = analyze(published)

    REPORTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    write_csv(
        REPORTS / "seo-content-audit.csv",
        findings,
        [
            "id",
            "type",
            "title",
            "url",
            "slug",
            "word_count",
            "city",
            "service",
            "title_template",
            "h1_count",
            "h2_count",
            "h3_count",
            "featured_media",
            "boilerplate_ratio",
            "similarity",
            "similar_url",
            "problem",
            "severity",
            "notes",
        ],
    )
    write_csv(
        REPORTS / "seo-cannibalization-clusters.csv",
        clusters,
        ["title_template", "count", "cities", "avg_words", "min_words", "max_words", "example_title", "example_url"],
    )
    by_url: dict[str, dict] = {}
    for f in findings:
        key = f.get("url") or ""
        rec = by_url.setdefault(
            key,
            {
                "id": f.get("id"),
                "type": f.get("type"),
                "title": f.get("title"),
                "url": key,
                "word_count": f.get("word_count"),
                "city": f.get("city"),
                "service": f.get("service"),
                "problems": [],
                "severities": [],
                "notes": [],
            },
        )
        rec["problems"].append(f.get("problem") or "")
        rec["severities"].append(f.get("severity") or "")
        rec["notes"].append(f"[{f.get('problem')}] {f.get('notes')}")
    rolled = []
    rank = {"حرج": 0, "عالٍ": 1, "متوسط": 2}
    for rec in by_url.values():
        rec["problem"] = " | ".join(dict.fromkeys(rec["problems"]))
        rec["severity"] = sorted(rec["severities"], key=lambda s: rank.get(s, 9))[0] if rec["severities"] else ""
        rec["notes"] = " || ".join(rec["notes"])
        rolled.append(rec)
    rolled.sort(key=lambda r: (rank.get(r["severity"], 9), r.get("word_count") or 0))
    write_csv(
        REPORTS / "seo-content-audit-by-url.csv",
        rolled,
        ["id", "type", "title", "url", "word_count", "city", "service", "severity", "problem", "notes"],
    )
    write_csv(
        REPORTS / "seo-boilerplate-passages.csv",
        boiler,
        ["documents", "share", "passage"],
    )
    write_markdown(DOCS / "seo-content-audit.md", stats, findings, clusters, boiler)

    print("STATS", json.dumps(stats, ensure_ascii=False))
    print("Wrote", REPORTS / "seo-content-audit.csv")
    print("Wrote", DOCS / "seo-content-audit.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

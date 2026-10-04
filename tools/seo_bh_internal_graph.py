#!/usr/bin/env python3
"""Add unique internal links and recategorize Bahrain posts for topical SEO."""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rewrite_bh_articles import CITIES, angle_for, parse_title, pick, seed  # noqa: E402
from rewrite_bh_kayan import CITY_SLUG, req  # noqa: E402

MARKER = "kayan-seo-graph"
PRIMARY = "#076bb5"
CATS = {
    10: ("كشف تسربات المياه", "/bh/category/water-leak-detection/"),
    12: ("عزل الأسطح", "/bh/category/roof-insulation/"),
    14: ("الصيانة العامة", "/bh/category/general-maintenance/"),
    16: ("السباكة وتسليك المجاري", "/bh/category/plumbing/"),
    18: ("التكييف والكهرباء", "/bh/category/ac-electrical/"),
    20: ("التنظيف والتعقيم", "/bh/category/cleaning/"),
    22: ("مكافحة الحشرات", "/bh/category/pest-control/"),
    24: ("الحدائق والمسابح", "/bh/category/gardens-pools/"),
    26: ("الصبغ والديكورات", "/bh/category/painting-decor/"),
}
HOST = "https://www.rukn-eltatawer.com"


def title_of(p: dict) -> str:
    t = p.get("title") or {}
    raw = t.get("raw") or t.get("rendered") or ""
    return re.sub(r"<[^>]+>", "", raw).strip()


def target_cat(svc: str) -> int:
    s = svc or ""
    if any(k in s for k in ("عزل صوتي", "صوت منزل", "أنظمة صوت", "طرد الطيور", "شحن", "نجار")):
        return 14
    if any(k in s for k in ("تسرب", "تسريبات")):
        return 10
    if "عزل" in s:
        return 12
    if any(k in s for k in ("ورق جدران", "ورق حائط", "دهان", "صبغ", "بويات", "جبس", "ديكور")):
        return 26
    if any(k in s for k in ("تنظيف", "تعقيم", "جلي", "سجاد", "موكيت")):
        return 20
    if any(k in s for k in ("مكافحة", "حشرات", "صراصير", "قوارض", "بعوض", "طارد للحمام", "نمل")):
        return 22
    if any(k in s for k in ("سباك", "سباكة", "مجاري", "تسليك", "سخان", "بيارة")):
        return 16
    if any(k in s for k in ("حديق", "نجيل", "مسبح", "ري أوتومات", "شبكات ري", "حمامات خارجية")):
        return 24
    if any(k in s for k in ("تكييف", "مكيف", "فريون", "كهرب", "إنارة", "تمديدات كهرب")):
        return 18
    return 14


def fetch_posts(with_content: bool = True) -> list[dict]:
    posts = []
    page = 1
    fields = "id,slug,title,content,categories,link" if with_content else "id,slug,title,categories,link"
    while page <= 40:
        code, data = req(
            "GET",
            f"/wp/v2/posts&per_page=50&page={page}&context=edit&status=publish"
            f"&_fields={fields}",
        )
        if code != 200 or not data:
            break
        posts.extend(data)
        print(f"fetched {page} n={len(data)} total={len(posts)}", flush=True)
        if len(data) < 50:
            break
        page += 1
    return posts


def family_slug(slug: str) -> str:
    for sl in sorted(CITY_SLUG.values(), key=len, reverse=True):
        if slug.endswith("-" + sl):
            return slug[: -(len(sl) + 1)]
    return slug


def index_posts(posts: list[dict]):
    by_svc = defaultdict(list)
    by_city = defaultdict(list)
    by_fam = defaultdict(list)
    meta = {}
    for p in posts:
        title = title_of(p)
        svc, city = parse_title(title)
        if city not in CITIES:
            city = ""
        fam = family_slug(p.get("slug") or "")
        rec = {
            "id": p["id"],
            "slug": p.get("slug") or "",
            "title": title,
            "svc": svc,
            "city": city,
            "fam": fam,
            "href": f"{HOST}/bh/{p.get('slug')}/",
            "pack": angle_for(svc) if svc else "gen",
            "cats": p.get("categories") or [],
        }
        meta[p["id"]] = rec
        if svc:
            by_svc[svc].append(rec)
        if city:
            by_city[city].append(rec)
        if fam:
            by_fam[fam].append(rec)
    return by_svc, by_city, by_fam, meta


def pick_links(rec: dict, by_svc, by_city, by_fam, n: int) -> tuple[list, list]:
    others = [x for x in by_fam.get(rec["fam"], []) if x["id"] != rec["id"]]
    others = others[n % max(len(others), 1) :] + others[: n % max(len(others), 1)]
    cities = others[:3]
    same = [x for x in by_city.get(rec["city"], []) if x["id"] != rec["id"]]
    same_pack = [x for x in same if x["pack"] == rec["pack"] and x["svc"] != rec["svc"]]
    other_pack = [x for x in same if x["pack"] != rec["pack"]]
    rel = []
    used = set()
    for pool in (same_pack, other_pack, same):
        start = n % max(len(pool), 1) if pool else 0
        rot = pool[start:] + pool[:start]
        for x in rot:
            if x["id"] in used or x["slug"] == rec["slug"]:
                continue
            rel.append(x)
            used.add(x["id"])
            if len(rel) == 3:
                break
        if len(rel) == 3:
            break
    return cities, rel


def graph_html(rec: dict, cities: list, related: list, cat_id: int, n: int) -> str:
    h2 = pick(
        n,
        [
            f"صفحات تكمل {rec['svc']} في البحرين",
            f"ماذا يطلبه عملاؤنا مع هذه الخدمة في {rec['city']}؟",
            f"روابط داخلية لـ {rec['svc']}",
            f"استكمال الموضوع في {rec['city']} ومدن أخرى",
        ],
    )
    city_h = pick(n + 1, [f"{rec['svc']} في مدن أخرى", "نفس الخدمة خارج هذه المدينة", "مدن نغطيها أيضاً"])
    rel_h = pick(n + 2, [f"خدمات قريبة في {rec['city']}", f"قد تحتاجها بعد المعاينة في {rec['city']}", "موضوعات مرتبطة"])
    lis_c = "".join(f'<li><a href="{x["href"]}">{x["title"]}</a></li>' for x in cities)
    lis_r = "".join(f'<li><a href="{x["href"]}">{x["title"]}</a></li>' for x in related)
    cname, cpath = CATS.get(cat_id, CATS[14])
    note = pick(
        n + 3,
        [
            f"هذه الروابط لصفحات منشورة على الموقع وليست قائمة تسويق عامة. اختر المدينة أو الخدمة الأقرب لحالتك في {rec['city']}.",
            f"جوجل والباحث يستفيدان من ربط {rec['svc']} بصفحات المدن والخدمات المجاورة بدل صفحات يتيمة.",
            f"إن كانت حالتك أقرب لرابط أدناه فافتحه بدل تكرار السؤال في واتساب.",
        ],
    )
    cols = ""
    if lis_c:
        cols += f'<div><h3>{city_h}</h3><ul>{lis_c}</ul></div>'
    if lis_r:
        cols += f'<div><h3>{rel_h}</h3><ul>{lis_r}</ul></div>'
    return (
        f'<section class="{MARKER}" style="margin:22px 0;padding:16px 18px;border:1px solid #d7e4f2;'
        f'border-right:5px solid {PRIMARY};border-radius:14px;background:#f7fbfe">'
        f"<style>.{MARKER} h2{{margin:0 0 10px;font-size:22px}}.{MARKER} h3{{margin:12px 0 8px;font-size:17px}}"
        f".{MARKER} .cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}"
        f".{MARKER} ul{{margin:0;padding:0 18px 0 0}}.{MARKER} a{{color:{PRIMARY};font-weight:600}}"
        f"@media(max-width:640px){{.{MARKER} .cols{{grid-template-columns:1fr}}}}</style>"
        f"<h2>{h2}</h2><p>{note}</p><div class='cols'>{cols}</div>"
        f'<p style="margin:12px 0 0">التصنيف: <a href="{HOST}{cpath}">{cname}</a></p></section>'
    )


def strip_old(html: str) -> str:
    return re.sub(rf'<section class="{MARKER}"[\s\S]*?</section>', "", html, flags=re.I)


def inject(html: str, block: str) -> str:
    html = strip_old(html)
    if "-YC-FaqsSimple-vsingle" in html:
        return html.replace('<div class="-YC-FaqsSimple-vsingle">', block + '\n<div class="-YC-FaqsSimple-vsingle">', 1)
    if "</article>" in html:
        return html.replace("</article>", block + "</article>", 1)
    return html + block


def process_one(post: dict, by_svc, by_city, by_fam, meta) -> tuple[int, str, int, bool]:
    pid = post["id"]
    rec = meta[pid]
    n = seed(rec["title"], rec["slug"], "seo-graph")
    cities, related = pick_links(rec, by_svc, by_city, by_fam, n)
    cur = rec["cats"][0] if rec["cats"] else 14
    tgt = target_cat(rec["svc"])
    new_cat = tgt if cur == 14 and tgt != 14 else cur
    html = (post.get("content") or {}).get("raw") or (post.get("content") or {}).get("rendered") or ""
    block = graph_html(rec, cities, related, new_cat, n)
    new_html = inject(html, block)
    payload = {"content": new_html}
    if new_cat != cur:
        payload["categories"] = [new_cat]
    code, out = req("POST", f"/wp/v2/posts/{pid}", payload)
    if code not in (200, 201):
        return pid, f"err{code}:{str(out)[:70]}", len(cities) + len(related), new_cat != cur
    return pid, "ok", len(cities) + len(related), new_cat != cur


def sample_report(posts, by_svc, by_city, by_fam, meta) -> None:
    print("=== seo graph sample ===")
    shown = 0
    for p in posts:
        rec = meta[p["id"]]
        if rec["slug"] not in (
            "home-cleaning-manama",
            "air-freight-manama",
            "home-plumber-manama",
            "water-leak-detection-manama",
            "home-electrician-elec-sitra",
        ):
            continue
        n = seed(rec["title"], rec["slug"], "seo-graph")
        cities, related = pick_links(rec, by_svc, by_city, by_fam, n)
        cur = rec["cats"][0] if rec["cats"] else 14
        tgt = target_cat(rec["svc"])
        new_cat = tgt if cur == 14 and tgt != 14 else cur
        print(rec["slug"], "city_links", [x["slug"] for x in cities], "rel", [x["slug"] for x in related], f"cat {cur}->{new_cat}")
        shown += 1
    moves = 0
    for rec in meta.values():
        cur = rec["cats"][0] if rec["cats"] else 14
        tgt = target_cat(rec["svc"])
        if cur == 14 and tgt != 14:
            moves += 1
    print("conservative_category_moves", moves, "posts", len(meta), "shown", shown)


def main() -> int:
    posts = fetch_posts(with_content="--dry-run" not in sys.argv)
    by_svc, by_city, by_fam, meta = index_posts(posts)
    sample_report(posts, by_svc, by_city, by_fam, meta)
    if "--dry-run" in sys.argv:
        return 0
    if not os.environ.get("WP_APP_PASSWORD"):
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1
    if "--limit" in sys.argv:
        posts = posts[: int(sys.argv[sys.argv.index("--limit") + 1])]
    ok = err = moves = 0
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = [pool.submit(process_one, p, by_svc, by_city, by_fam, meta) for p in posts]
        for i, fut in enumerate(as_completed(futs), 1):
            pid, st, nlinks, moved = fut.result()
            if st == "ok":
                ok += 1
                moves += int(moved)
            else:
                err += 1
                if err <= 8:
                    print("fail", pid, st)
            if i % 80 == 0:
                print(f"progress {i}/{len(posts)} ok={ok} err={err} cat_moves={moves}", flush=True)
    print(f"done ok={ok} err={err} cat_moves={moves}")
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Live WordPress REST fixes for the Bahrain SEO content audit.

Tasks
  1. Deduplicate FAQ accordion H2 items (and FAQPage JSON-LD) in post_content.
  2. Assign featured_media = rukn-eltatawer-picture.webp on posts missing a thumbnail.
  3. Draft keyword-cannibalization duplicates and print 301 rules.

Credentials (never committed):
  WP_BASE / WP_USER / WP_APP_PASSWORD  or  /home/ubuntu/.config/rukn-bh/wp.env

Usage:
  python3 tools/wp_seo_content_fixes.py --dry-run
  python3 tools/wp_seo_content_fixes.py --limit 1
  python3 tools/wp_seo_content_fixes.py --apply
"""
from __future__ import annotations

import argparse
import base64
import csv
import html as htmlmod
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ENV_FILE = Path("/home/ubuntu/.config/rukn-bh/wp.env")
FEATURED_SLUG = "rukn-eltatawer-picture"
CITIES = [
    "manama",
    "muharraq",
    "riffa",
    "hamad-town",
    "isa-town",
    "aali",
    "sitra",
    "budaiya",
]
# loser slug prefix -> keeper slug prefix (cleaner URL)
CANNIBAL_PAIRS = [
    ("grass-wall", "wall-grass"),
    ("artificial-grass-grdn", "artificial-grass"),
]

ITEM_RE = re.compile(
    r'<div class="-YC-FaqsSimple-vsingle-Item-v2[^"]*">'
    r'<div class="-YC-FaqsSimple-vsingle-Title"[^>]*>'
    r'<div class="--fq-count">\d+</div>'
    r'<h2>(.*?)</h2>'
    r'<i class="[^"]*"></i>'
    r'</div>'
    r'<div class="-FaqsSimple-vsingle-Content-Row-v1[^"]*">'
    r'<div class="-p-FaqsSimple-vsingle-ContentValue-v1[^"]*">(.*?)</div>'
    r'</div>'
    r'</div>',
    re.S,
)


def load_env() -> None:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


def auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def http_json(method: str, url: str, auth: str, payload=None, timeout: int = 90, attempts: int = 4):
    ctx = ssl.create_default_context()
    last: Exception | None = None
    body = None
    headers = {
        "Authorization": auth,
        "Accept": "application/json",
        "User-Agent": "RuknSEO-Fixes/1.0",
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read().decode("utf-8", "replace")
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                return resp.status, json.loads(raw) if raw else {}, hdrs
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw) if raw else {"raw": raw[:500]}
            except json.JSONDecodeError:
                parsed = {"raw": raw[:500]}
            if exc.code in (429, 500, 502, 503, 504) and attempt < attempts:
                time.sleep(min(12, attempt * 2))
                last = exc
                continue
            return exc.code, parsed, {}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(min(12, attempt * 2))
    raise RuntimeError(f"{method} {url} failed: {last}")


def paged_posts(base: str, auth: str, extra: str, per_page: int = 100):
    page = 1
    total_pages = 1
    while page <= total_pages:
        url = (
            f"{base}/wp-json/wp/v2/posts?per_page={per_page}&page={page}"
            f"&status=publish&context=edit{extra}"
        )
        code, data, hdrs = http_json("GET", url, auth, timeout=120)
        if code != 200 or not isinstance(data, list):
            raise RuntimeError(f"posts page {page} failed {code} {str(data)[:300]}")
        total_pages = int(hdrs.get("x-wp-totalpages") or "1")
        print(f"  fetched posts page {page}/{total_pages} (+{len(data)})", flush=True)
        for item in data:
            yield item
        page += 1
        time.sleep(0.12)


def find_featured_id(base: str, auth: str) -> int:
    q = urllib.parse.urlencode({"search": FEATURED_SLUG, "per_page": 20})
    code, data, _ = http_json("GET", f"{base}/wp-json/wp/v2/media?{q}", auth)
    if code == 200 and isinstance(data, list):
        for item in data:
            url = item.get("source_url") or ""
            slug = item.get("slug") or ""
            if FEATURED_SLUG in url or FEATURED_SLUG in slug:
                return int(item["id"])
    raise RuntimeError("Could not find rukn-eltatawer-picture.webp in the media library")


def normalize_q(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    text = htmlmod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def dedupe_faq_items(html: str) -> tuple[str, int, int]:
    matches = list(ITEM_RE.finditer(html))
    if not matches:
        return html, 0, 0
    seen: set[str] = set()
    uniq: list[tuple[str, str]] = []
    for match in matches:
        question_html, answer_html = match.group(1), match.group(2)
        key = normalize_q(question_html)
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append((question_html, answer_html))
    if len(uniq) == len(matches):
        return html, len(matches), 0
    rebuilt = []
    for i, (question_html, answer_html) in enumerate(uniq):
        active = " active" if i == 0 else ""
        rebuilt.append(
            f'<div class="-YC-FaqsSimple-vsingle-Item-v2{active}">'
            f'<div class="-YC-FaqsSimple-vsingle-Title" data-toggle-faqs="{i}">'
            f'<div class="--fq-count">{i+1:02d}</div>'
            f"<h2>{question_html}</h2>"
            f'<i class="fa-solid fa-plus"></i></div>'
            f'<div class="-FaqsSimple-vsingle-Content-Row-v1 -Toggle-Content">'
            f'<div class="-p-FaqsSimple-vsingle-ContentValue-v1 -ToggleContentValue">{answer_html}</div>'
            f"</div></div>"
        )
    start, end = matches[0].start(), matches[-1].end()
    html = html[:start] + "".join(rebuilt) + html[end:]
    return html, len(matches), len(matches) - len(uniq)


def dedupe_faq_jsonld(html: str) -> str:
    def repl(match: re.Match) -> str:
        raw = match.group(1)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return match.group(0)
        types = data.get("@type")
        if types != "FAQPage" and "FAQPage" not in (types or []):
            return match.group(0)
        entities = data.get("mainEntity") or []
        seen: set[str] = set()
        uniq = []
        for ent in entities:
            name = normalize_q(ent.get("name") or "")
            if not name or name in seen:
                continue
            seen.add(name)
            uniq.append(ent)
        if len(uniq) == len(entities):
            return match.group(0)
        data["mainEntity"] = uniq
        dumped = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f'<script type="application/ld+json">{dumped}</script>'

    return re.sub(
        r'<script type="application/ld\+json">(.*?)</script>',
        repl,
        html,
        flags=re.S,
    )


def clean_post_html(html: str) -> tuple[str, int]:
    cleaned, total, dropped = dedupe_faq_items(html or "")
    cleaned = dedupe_faq_jsonld(cleaned)
    return cleaned, dropped


def get_by_slug(base: str, auth: str, slug: str):
    q = urllib.parse.urlencode({"slug": slug, "status": "publish,draft", "context": "edit", "per_page": 5})
    code, data, _ = http_json("GET", f"{base}/wp-json/wp/v2/posts?{q}", auth)
    if code == 200 and isinstance(data, list) and data:
        return data[0]
    return None


def write_redirects(pairs: list[dict], path_txt: Path, path_htaccess: Path, path_rankmath: Path) -> None:
    path_txt.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 301 redirects — paste into Rank Math > Redirections or .htaccess", ""]
    ht = ["# Bahrain cannibalization 301s", ""]
    rm = ["source,destination,type"]
    for row in pairs:
        old = row["old_url"].rstrip("/") + "/"
        new = row["new_url"].rstrip("/") + "/"
        path = urllib.parse.urlparse(old).path
        lines.append(f"{old}  ->  {new}")
        ht.append(f"Redirect 301 {path} {new}")
        rm.append(f"{path},{new},301")
    path_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path_htaccess.write_text("\n".join(ht) + "\n", encoding="utf-8")
    path_rankmath.write_text("\n".join(rm) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes to WordPress")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only (default if --apply is omitted)")
    parser.add_argument("--limit", type=int, default=0, help="Max posts to update (0 = all)")
    parser.add_argument("--sleep", type=float, default=0.18, help="Delay between PUT requests")
    parser.add_argument("--skip-cannibal", action="store_true")
    parser.add_argument("--skip-faq", action="store_true")
    parser.add_argument("--skip-featured", action="store_true")
    args = parser.parse_args()
    apply = bool(args.apply) and not args.dry_run

    load_env()
    base = os.environ.get("WP_BASE", "https://www.rukn-eltatawer.com/bh").rstrip("/")
    user = os.environ.get("WP_USER", "")
    password = os.environ.get("WP_APP_PASSWORD", "")
    if not user or not password:
        print("Missing WP_USER / WP_APP_PASSWORD", file=sys.stderr)
        return 1
    auth = auth_header(user, password)
    REPORTS.mkdir(parents=True, exist_ok=True)

    print(f"Site {base}  mode={'APPLY' if apply else 'DRY-RUN'}", flush=True)
    featured_id = 0 if args.skip_featured else find_featured_id(base, auth)
    print(f"Featured media id = {featured_id}", flush=True)

    draft_ids: set[int] = set()
    redirect_rows: list[dict] = []
    if not args.skip_cannibal:
        print("Resolving cannibalization pairs…", flush=True)
        for loser_pfx, keeper_pfx in CANNIBAL_PAIRS:
            for city in CITIES:
                loser_slug = f"{loser_pfx}-{city}"
                keeper_slug = f"{keeper_pfx}-{city}"
                loser = get_by_slug(base, auth, loser_slug)
                keeper = get_by_slug(base, auth, keeper_slug)
                time.sleep(0.08)
                if not loser or not keeper:
                    print(f"  missing pair {loser_slug} / {keeper_slug} loser={bool(loser)} keeper={bool(keeper)}")
                    continue
                redirect_rows.append(
                    {
                        "old_slug": loser_slug,
                        "new_slug": keeper_slug,
                        "old_id": loser["id"],
                        "new_id": keeper["id"],
                        "old_url": loser.get("link") or f"{base}/{loser_slug}/",
                        "new_url": keeper.get("link") or f"{base}/{keeper_slug}/",
                        "old_status": loser.get("status"),
                        "new_status": keeper.get("status"),
                    }
                )
                draft_ids.add(int(loser["id"]))
        print(f"  {len(redirect_rows)} pairs", flush=True)

    log_rows: list[dict] = []
    updated = 0
    skipped = 0
    failed = 0
    extra = "&_fields=id,slug,link,status,featured_media,content,title"
    count_done = 0
    print("Scanning published posts…", flush=True)
    for post in paged_posts(base, auth, extra):
        pid = int(post["id"])
        if pid in draft_ids:
            skipped += 1
            continue
        raw = (post.get("content") or {}).get("raw") or ""
        dropped = 0
        new_html = raw
        if not args.skip_faq:
            new_html, dropped = clean_post_html(raw)
        need_image = (not args.skip_featured) and int(post.get("featured_media") or 0) == 0
        need_faq = dropped > 0 and new_html != raw
        if not need_faq and not need_image:
            skipped += 1
            continue
        payload = {}
        if need_faq:
            payload["content"] = new_html
        if need_image:
            payload["featured_media"] = featured_id
        log_rows.append(
            {
                "id": pid,
                "slug": post.get("slug"),
                "url": post.get("link"),
                "faq_removed": dropped,
                "featured": int(need_image),
                "bytes_before": len(raw),
                "bytes_after": len(new_html),
                "action": "PUT" if apply else "dry-run",
            }
        )
        if args.limit and count_done >= args.limit:
            if apply:
                print(f"Reached --limit {args.limit}", flush=True)
                break
            continue
        if apply:
            code, data, _ = http_json("PUT", f"{base}/wp-json/wp/v2/posts/{pid}", auth, payload)
            if code in (200, 201):
                updated += 1
                count_done += 1
            else:
                failed += 1
                log_rows[-1]["action"] = f"FAIL {code} {str(data)[:180]}"
                print(f"  FAIL post {pid} {code} {str(data)[:180]}", flush=True)
            time.sleep(args.sleep)
        else:
            count_done += 1
            updated += 1
        if args.limit and count_done >= args.limit and apply:
            print(f"Reached --limit {args.limit}", flush=True)
            break

    drafted = 0
    if redirect_rows and not args.skip_cannibal:
        write_redirects(
            redirect_rows,
            REPORTS / "seo-301-redirects.txt",
            REPORTS / "seo-301-htaccess.txt",
            REPORTS / "seo-301-rankmath.csv",
        )
        if apply and not args.limit:
            for row in redirect_rows:
                code, data, _ = http_json(
                    "PUT",
                    f"{base}/wp-json/wp/v2/posts/{row['old_id']}",
                    auth,
                    {"status": "draft"},
                )
                if code in (200, 201):
                    drafted += 1
                    row["drafted"] = "yes"
                else:
                    row["drafted"] = f"FAIL {code}"
                    print(f"  FAIL draft {row['old_slug']} {code}", flush=True)
                time.sleep(args.sleep)
        elif apply and args.limit:
            print("Skipping cannibal drafts because --limit is set", flush=True)

    log_path = REPORTS / "seo-content-fixes-log.csv"
    with log_path.open("w", encoding="utf-8-sig", newline="") as fh:
        fields = ["id", "slug", "url", "faq_removed", "featured", "bytes_before", "bytes_after", "action"]
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(log_rows)

    pair_path = REPORTS / "seo-cannibalization-actions.csv"
    with pair_path.open("w", encoding="utf-8-sig", newline="") as fh:
        fields = ["old_slug", "new_slug", "old_id", "new_id", "old_url", "new_url", "old_status", "drafted"]
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(redirect_rows)

    print(
        json.dumps(
            {
                "mode": "APPLY" if apply else "DRY-RUN",
                "featured_id": featured_id,
                "posts_needing_faq_or_image": len(log_rows),
                "updated": updated,
                "skipped": skipped,
                "failed": failed,
                "cannibal_pairs": len(redirect_rows),
                "drafted": drafted if apply else 0,
                "log": str(log_path),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if redirect_rows:
        print("\n=== 301 rules (old -> new) ===")
        for row in redirect_rows:
            print(f"{row['old_url']} -> {row['new_url']}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

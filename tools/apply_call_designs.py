#!/usr/bin/env python3
"""Apply Call-main page shapes + snippet 5 to live Rukn Bahrain.

Credentials via env: WP_BASE, WP_USER, WP_APP_PASSWORD.
Never commit credentials.
"""

from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "tools" / "pages"
SNIPPET = ROOT / "tools" / "bh-fix-snippet.php"

WP_BASE = os.environ.get("WP_BASE", "https://www.rukn-eltatawer.com/bh").rstrip("/")
WP_USER = os.environ.get("WP_USER", "melsaad")
WP_PASS = os.environ.get("WP_APP_PASSWORD", "")

CTX = ssl.create_default_context()

PAGE_MAP = {
    3381: ("about-us.html", "من نحن | ركن التطور البحرين", "عن ركن التطور في مملكة البحرين: خدمات منزلية، معاينة، وضمان مكتوب."),
    3379: ("contact-us.html", "تواصل معنا | ركن التطور البحرين", "تواصل عبر واتساب أو النموذج لتنسيق المعاينة في البحرين."),
    3387: ("cities.html", "مدن الخدمة | ركن التطور البحرين", "تغطية مدن مملكة البحرين: المنامة والمحرق والرفاع ومدينة حمد ومدينة عيسى وعالي وسترة والبديع."),
    3385: ("our-services.html", "خدماتنا | ركن التطور البحرين", "تصنيفات الخدمات المنزلية في البحرين من كشف التسربات إلى الصيانة العامة."),
    3383: ("privacy-policy-bahrain.html", None, None),  # filename override below
    13923: ("blog.html", "مدونة ركن التطور البحرين", "أدلة خدمات المنزل في مدن مملكة البحرين."),
    3397: ("about-us-en.html", "About us | Rukn Eltatawer Bahrain", "Rukn Eltatawer home services in the Kingdom of Bahrain."),
    3395: ("contact-us-en.html", "Contact | Rukn Eltatawer Bahrain", "WhatsApp the Bahrain team for an inspection."),
    3393: ("cities-en.html", "Cities | Rukn Eltatawer Bahrain", "Bahrain cities we cover, starting with Manama."),
    3391: ("services-en.html", "Services | Rukn Eltatawer Bahrain", "Home service categories in Bahrain."),
    3389: ("home-services-bahrain.html", "Home services in Bahrain | Rukn Eltatawer", "English hub for Rukn Eltatawer in Bahrain."),
}

# privacy filename is privacy.html
PAGE_MAP[3383] = (
    "privacy.html",
    "سياسة الخصوصية | ركن التطور البحرين",
    "كيف نجمع ونستخدم بيانات طلبات الخدمات في مملكة البحرين.",
)

CREATE_PAGES = [
    {
        "slug": "terms",
        "file": "terms.html",
        "title": "الشروط والأحكام | ركن التطور البحرين",
        "excerpt": "شروط حجز وتنفيذ خدمات ركن التطور داخل مملكة البحرين.",
    },
    {
        "slug": "faq",
        "file": "faq.html",
        "title": "الأسئلة الشائعة | ركن التطور البحرين",
        "excerpt": "تغطية المدن، المعاينة، الأسعار، والضمان في البحرين.",
    },
]


def auth_header() -> str:
    token = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    return "Basic " + token


def request(method: str, path: str, body=None, timeout: int = 90):
    url = WP_BASE + "/wp-json" + path
    data = None
    headers = {
        "Authorization": auth_header(),
        "User-Agent": "rukn-bh-apply/1.0",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            raw = resp.read()
            if not raw:
                return {}, resp.status
            return json.loads(raw.decode("utf-8")), resp.status
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")
        print(f"HTTP {exc.code} {method} {path}: {err[:800]}", file=sys.stderr)
        raise


def update_snippet() -> None:
    code = SNIPPET.read_text(encoding="utf-8")
    print(f"snippet bytes={len(code)}")
    print("deactivate snippet 5")
    request("PUT", "/code-snippets/v1/snippets/5", {"active": False})
    time.sleep(1.5)
    print("upload snippet 5")
    payload = {
        "name": "Rukn BH Live Fixes",
        "desc": "Call-main shapes, header overlay, city 500, 404, UAE leftovers, FABs, temp +971 WA",
        "code": code,
        "scope": "global",
        "active": False,
        "priority": 1,
        "tags": ["bahrain", "rukn"],
    }
    request("PUT", "/code-snippets/v1/snippets/5", payload, timeout=120)
    time.sleep(1)
    print("activate snippet 5")
    request("PUT", "/code-snippets/v1/snippets/5", {"active": True})
    snip, _ = request("GET", "/code-snippets/v1/snippets/5")
    print("snippet", snip.get("id"), "active=", snip.get("active"), "len=", len(snip.get("code") or ""))
    if snip.get("code_error"):
        print("CODE ERROR", snip.get("code_error"), file=sys.stderr)
        sys.exit(2)


def upsert_pages() -> None:
    for page_id, (filename, title, excerpt) in PAGE_MAP.items():
        html = (PAGES_DIR / filename).read_text(encoding="utf-8")
        body = {"content": html, "status": "publish"}
        if title:
            body["title"] = title
        if excerpt:
            body["excerpt"] = excerpt
        print(f"update page {page_id} {filename} ({len(html)} chars)")
        request("POST", f"/wp/v2/pages/{page_id}", body, timeout=120)

    existing, _ = request("GET", "/wp/v2/pages?per_page=100&_fields=id,slug")
    slugs = {p["slug"]: p["id"] for p in existing}
    for spec in CREATE_PAGES:
        html = (PAGES_DIR / spec["file"]).read_text(encoding="utf-8")
        body = {
            "title": spec["title"],
            "slug": spec["slug"],
            "status": "publish",
            "content": html,
            "excerpt": spec["excerpt"],
        }
        if spec["slug"] in slugs:
            pid = slugs[spec["slug"]]
            print(f"update created page {pid} {spec['slug']}")
            request("POST", f"/wp/v2/pages/{pid}", body, timeout=120)
        else:
            print(f"create page {spec['slug']}")
            created, _ = request("POST", "/wp/v2/pages", body, timeout=120)
            print(" created id", created.get("id"), created.get("link"))


def delete_zip_media() -> None:
    media, _ = request("GET", "/wp/v2/media?per_page=50&_fields=id,mime_type,source_url")
    for item in media:
        url = item.get("source_url") or ""
        if item.get("mime_type") == "application/zip" or url.endswith(".zip"):
            mid = item["id"]
            print(f"delete media zip {mid} {url}")
            try:
                request("DELETE", f"/wp/v2/media/{mid}?force=true")
            except Exception as exc:
                print(" delete failed", exc)


def main() -> None:
    if not WP_PASS:
        sys.exit("WP_APP_PASSWORD is required")
    update_snippet()
    upsert_pages()
    delete_zip_media()
    print("done")


if __name__ == "__main__":
    main()

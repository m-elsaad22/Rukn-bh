#!/usr/bin/env python3
"""Deploy Bahrain live fixes via WordPress REST + WPVibe CLI."""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("WP_BASE", "https://www.rukn-eltatawer.com/bh").rstrip("/")
USER = os.environ.get("WP_USER", "melsaad")
PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
ROOT = os.path.dirname(os.path.abspath(__file__))
SNIPPET_PATH = os.path.join(ROOT, "bh-fix-snippet.php")
WA = "+971586634710"


def req(method: str, route: str, payload=None, timeout=120):
    url = f"{BASE}/?rest_route={route}"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "RuknBH-Fix/1.0",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body[:800]}
        return exc.code, parsed


def cli(command: str, write: bool = False, timeout: int = 180):
    code, data = req(
        "POST",
        "/wpvibe/v1/cli/run",
        {"command": command, "confirm_write": write},
        timeout=timeout,
    )
    stdout = data.get("stdout") if isinstance(data, dict) else ""
    stderr = data.get("stderr") if isinstance(data, dict) else ""
    print(f"CLI [{code}/{data.get('exit_code') if isinstance(data, dict) else '?'}] {command[:110]}")
    if stderr:
        print("  stderr:", stderr[:400])
    if stdout and len(stdout) < 400:
        print("  stdout:", stdout.replace("\n", " ")[:350])
    return data


def option_update(key: str, value, json_fmt: bool = False):
    if json_fmt:
        payload = json.dumps(value, ensure_ascii=False)
        # WP-CLI needs the JSON as a single argument
        return cli(f"wp option update {key} {json.dumps(payload)} --format=json", write=True)
    if isinstance(value, (dict, list)):
        return cli(
            f"wp option update {key} {json.dumps(json.dumps(value, ensure_ascii=False))} --format=json",
            write=True,
        )
    escaped = value.replace("'", "'\\''")
    return cli(f"wp option update {key} '{escaped}'", write=True)


def main() -> int:
    if not PASSWORD:
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1
    snippet = open(SNIPPET_PATH, encoding="utf-8").read().replace("<?php", "", 1).strip()
    if " mar" in snippet:
        print("snippet still contains typo ' mar'", file=sys.stderr)
        return 1

    print("=== options: WhatsApp UAE, hide phone, Bahrain HQ ===")
    cli(f"wp option update whatsapp_number '{WA}'", write=True)
    cli("wp option update phonenumber ''", write=True)
    cli("wp option update rukn_hide_call_global on", write=True)
    cli("wp option update company__adress 'المنامة، مملكة البحرين'", write=True)
    cli(
        "wp option update footer__company__adress_url 'https://www.google.com/maps?q=26.2285,50.5860'",
        write=True,
    )
    cli("wp option update search_placeholder 'ابحث في الموقع'", write=True)
    cli("wp option update search_title 'بحث'", write=True)
    cli("wp option update hide__description_show 1", write=True)
    cli("wp option update kayan_i18n_default_country bh", write=True)

    copy = (
        'حقوق النشر {%YEAR%} © جميع الحقوق محفوظة لصالح "شركة ركن التطور - البحرين" '
        "<span>KAYAN WEB</span>"
    )
    cli(f"wp option update copyrights {json.dumps(copy)}", write=True)

    print("=== Polylang: stop browser language hijack ===")
    pll = cli("wp option get polylang --format=json")
    raw = pll.get("stdout") if isinstance(pll, dict) else ""
    try:
        pll_obj = json.loads(raw)
        pll_obj["browser"] = False
        cli(
            "wp option update polylang "
            + json.dumps(json.dumps(pll_obj, ensure_ascii=False))
            + " --format=json",
            write=True,
        )
    except json.JSONDecodeError:
        print("  could not parse polylang option")

    print("=== Rank Math titles / general ===")
    titles = cli("wp option get rank-math-options-titles --format=json")
    traw = titles.get("stdout") if isinstance(titles, dict) else ""
    try:
        tobj = json.loads(traw)
        tobj["homepage_description"] = (
            "خدمات منزلية متكاملة في مملكة البحرين: كشف تسربات بدون تكسير، عزل الأسطح، "
            "صيانة، تكييف، سباكة، تنظيف ومكافحة حشرات في المنامة والمحرق والرفاع وكل مدن البحرين. "
            "تواصل واتساب."
        )
        tobj["content_ai_language"] = "Arabic"
        tobj["content_ai_country"] = "Bahrain"
        cli(
            "wp option update rank-math-options-titles "
            + json.dumps(json.dumps(tobj, ensure_ascii=False))
            + " --format=json",
            write=True,
        )
    except json.JSONDecodeError:
        print("  could not parse rank math titles")

    general = cli("wp option get rank-math-options-general --format=json")
    graw = general.get("stdout") if isinstance(general, dict) else ""
    try:
        gobj = json.loads(graw)
        gobj["breadcrumbs_home_label"] = "الرئيسية"
        gobj["breadcrumbs_archive_format"] = "أرشيف %s"
        gobj["breadcrumbs_search_format"] = "نتائج %s"
        gobj["breadcrumbs_404_label"] = "الصفحة غير موجودة"
        cli(
            "wp option update rank-math-options-general "
            + json.dumps(json.dumps(gobj, ensure_ascii=False))
            + " --format=json",
            write=True,
        )
    except json.JSONDecodeError:
        print("  could not parse rank math general")

    smap = cli("wp option get rank-math-options-sitemap --format=json")
    sraw = smap.get("stdout") if isinstance(smap, dict) else ""
    try:
        sobj = json.loads(sraw)
        sobj["tax_cities_sitemap"] = "on"
        sobj["pt_services_sitemap"] = "off"
        sobj["pt_reviews_sitemap"] = "off"
        cli(
            "wp option update rank-math-options-sitemap "
            + json.dumps(json.dumps(sobj, ensure_ascii=False))
            + " --format=json",
            write=True,
        )
    except json.JSONDecodeError:
        print("  could not parse sitemap options")

    print("=== menu URLs without index.php ===")
    menu_urls = {
        5065: "https://rukn-eltatawer.com/bh/",
        5066: "https://rukn-eltatawer.com/bh/our-services/",
        5067: "https://rukn-eltatawer.com/bh/cities/",
        5068: "https://rukn-eltatawer.com/bh/about-us/",
        5069: "https://rukn-eltatawer.com/bh/contact-us/",
        5070: "https://rukn-eltatawer.com/bh/home-services-bahrain/",
        5071: "https://rukn-eltatawer.com/bh/html-sitemap/",
    }
    for item_id, url in menu_urls.items():
        cli(f"wp menu item update {item_id} --url={url}", write=True)
        cli(f"wp post term add {item_id} language ar", write=True)

    print("=== WPCode snippet 3257 ===")
    b64 = base64.b64encode(snippet.encode()).decode()
    cli(
        f"wp post update 3257 --post_content_base64={b64} --post_status=publish",
        write=True,
        timeout=180,
    )

    cached = cli("wp option get wpcode_snippets --format=json")
    craw = cached.get("stdout") if isinstance(cached, dict) else ""
    try:
        cobj = json.loads(craw)
        items = cobj.get("everywhere") or []
        if items and isinstance(items[0], dict):
            items[0]["code"] = snippet
            items[0]["title"] = "Bahrain live fixes"
            items[0]["modified"] = time.strftime("%Y-%m-%d %H:%M:%S")
            cli(
                "wp option update wpcode_snippets "
                + json.dumps(json.dumps(cobj, ensure_ascii=False))
                + " --format=json",
                write=True,
                timeout=180,
            )
    except json.JSONDecodeError:
        print("  could not parse wpcode_snippets cache")

    print("=== snippet endpoint fallback ===")
    code, data = req(
        "POST",
        "/wpvibe/v1/code-snippet",
        {
            "action": "update",
            "id": 3257,
            "title": "Bahrain live fixes",
            "code": snippet,
            "code_type": "php",
            "location": "everywhere",
            "insert_method": "auto",
        },
    )
    print("snippet API", code, str(data)[:300])

    print("=== blog page ===")
    existing = cli("wp post list --post_type=page --name=blog --format=json")
    eraw = existing.get("stdout") if isinstance(existing, dict) else ""
    blog_id = None
    try:
        rows = json.loads(eraw) if eraw.strip().startswith("[") else []
        if rows:
            blog_id = rows[0].get("ID") or rows[0].get("id")
    except json.JSONDecodeError:
        pass
    if not blog_id:
        created = cli(
            "wp post create --post_type=page --post_status=publish "
            "--post_title=المدونة --post_name=blog "
            "--post_content='<p>مقالات ونصائح عملية لخدمات المنزل في البحرين.</p>' --porcelain",
            write=True,
        )
        blog_id = (created.get("stdout") or "").strip()
    if blog_id:
        cli(f"wp post term add {blog_id} language ar", write=True)

    print("=== featured image fallback for posts missing thumbnails ===")
    cli(
        "wp db query "
        "\"INSERT INTO 2GGpPu6Sy_postmeta (post_id, meta_key, meta_value) "
        "SELECT p.ID, '_thumbnail_id', '1587' FROM 2GGpPu6Sy_posts p "
        "WHERE p.post_type='post' AND p.post_status='publish' "
        "AND p.ID NOT IN (SELECT post_id FROM 2GGpPu6Sy_postmeta WHERE meta_key='_thumbnail_id' AND meta_value<>'')\"",
        write=True,
        timeout=180,
    )

    print("=== rewrite + cache ===")
    cli("wp rewrite flush", write=True)
    cli("wp cache purge", write=True)
    cli("wp litespeed-purge all", write=True)

    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

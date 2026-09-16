#!/usr/bin/env python3
"""Apply remaining Bahrain live fixes (no credentials in this file)."""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("WP_BASE", "https://www.rukn-eltatawer.com/bh").rstrip("/")
USER = os.environ.get("WP_USER", "melsaad")
PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
ROOT = os.path.dirname(os.path.abspath(__file__))
SNIPPET_PATH = os.path.join(ROOT, "bh-fix-snippet.php")
HEADER_PATH = os.path.join(ROOT, "header-codes.html")
WA = "+971586634710"


def req(method: str, route: str, payload=None, timeout=180):
    url = f"{BASE}/?rest_route={route}"
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "RuknBH-Fix/1.1",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
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
        print("  stderr:", str(stderr)[:400])
    if stdout and len(str(stdout)) < 500:
        print("  stdout:", str(stdout).replace("\n", " ")[:350])
    return data


def content_edit(target_type, old, new, **extra):
    payload = {
        "target_type": target_type,
        "old_content": old,
        "new_content": new,
        "replace_all": True,
        **extra,
    }
    code, data = req("POST", "/wpvibe/v1/content/edit", payload)
    print("content/edit", target_type, extra, code, str(data)[:350])
    return code, data


def main() -> int:
    if not PASSWORD:
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1

    snippet = open(SNIPPET_PATH, encoding="utf-8").read()
    if snippet.startswith("<?php"):
        snippet = snippet.replace("<?php", "", 1).strip()
    header_html = open(HEADER_PATH, encoding="utf-8").read().strip()

    print("=== WhatsApp UAE + hide phone + HQ Manama ===")
    cli(f"wp option update whatsapp_number '{WA}'", write=True)
    cli("wp option update rukn_hide_call_global on", write=True)
    cli("wp option update company__adress 'المنامة، مملكة البحرين'", write=True)
    cli(
        "wp option update footer__company__adress_url 'https://www.google.com/maps?q=26.2285,50.5860'",
        write=True,
    )
    cli("wp option update kayan_lockdown_allow_header_injection 1", write=True)

    print("=== header___codes via content/edit (CSS hide-call + JS nav) ===")
    content_edit(
        "option",
        '<style>a[href^="tel:"],.fab-call,.btn-call{display:none!important}</style>',
        header_html,
        option_name="header___codes",
    )

    print("=== menu URLs without index.php (WP REST; WP-CLI emulator does not persist _menu_item_url) ===")
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
        code, data = req("POST", f"/wp/v2/menu-items/{item_id}", {"url": url})
        print("menu-item", item_id, code, data.get("url") if isinstance(data, dict) else data)

    print("=== blog page + permalinks ===")
    cli("wp option update page_for_posts 13923", write=True)
    cli("wp rewrite flush", write=True)

    print("=== Rank Math homepage copy (WhatsApp, no call) ===")
    titles = cli("wp option get rank-math-options-titles --format=json")
    traw = titles.get("stdout") if isinstance(titles, dict) else ""
    try:
        tobj = json.loads(traw)
        tobj["homepage_title"] = (
            "ركن التطور البحرين | خدمات منزلية في المنامة وكل مدن البحرين"
        )
        tobj["homepage_description"] = (
            "خدمات منزلية متكاملة في مملكة البحرين: كشف تسربات بدون تكسير، عزل الأسطح، "
            "صيانة، تكييف، سباكة، تنظيف ومكافحة حشرات في المنامة والمحرق والرفاع وكل مدن البحرين. "
            "تواصل واتساب."
        )
        tobj["content_ai_language"] = "Arabic"
        tobj["content_ai_country"] = "Bahrain"
        for pt in ("services", "reviews", "faqs", "pricing", "portfolio", "before_after"):
            tobj[f"pt_{pt}_custom_robots"] = "on"
            robots = tobj.get(f"pt_{pt}_robots") or []
            if "noindex" not in robots:
                robots = list(robots) + ["noindex"]
            tobj[f"pt_{pt}_robots"] = robots
        cli(
            "wp option update rank-math-options-titles "
            + json.dumps(json.dumps(tobj, ensure_ascii=False))
            + " --format=json",
            write=True,
        )
    except json.JSONDecodeError:
        print("  could not parse rank math titles")

    print("=== WPCode snippet 3257 (saved; may stay inactive until wp-admin) ===")
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
    print("snippet API", code, str(data)[:400])

    print("=== cache ===")
    cli("wp cache flush", write=True)
    cli("wp litespeed-purge all", write=True)

    print("DONE", time.strftime("%Y-%m-%d %H:%M:%S"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

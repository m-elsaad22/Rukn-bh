#!/usr/bin/env python3
"""Deploy Bahrain SEO/indexing fixes via WordPress REST + WPVibe CLI."""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://rukn-eltatawer.com/bh"
USER = os.environ.get("WP_USER", "melsaad")
PASSWORD = os.environ.get("WP_APP_PASSWORD", "")


def req(method: str, route: str, payload=None, timeout=90):
    url = f"{BASE}/?rest_route={route}"
    data = None
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
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


def cli(command: str, write: bool = False, timeout: int = 90):
    code, data = req(
        "POST",
        "/wpvibe/v1/cli/run",
        {"command": command, "confirm_write": write},
        timeout=timeout,
    )
    print(f"CLI [{code}] {command[:90]}")
    if isinstance(data, dict) and data.get("stderr"):
        print("  stderr:", data["stderr"][:400])
    if isinstance(data, dict) and data.get("code") and data.get("code") != "ok":
        print("  err:", data.get("code"), str(data.get("message", ""))[:300])
    return data


def main() -> int:
    if not PASSWORD:
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1

    snippet = open(
        os.path.join(os.path.dirname(__file__), "bh-indexing-mu-snippet.php"),
        encoding="utf-8",
    ).read()
    # strip opening php tag for snippet plugins
    snippet_body = snippet.replace("<?php", "", 1).strip()

    print("=== create snippet ===")
    code, data = req(
        "POST",
        "/wpvibe/v1/code-snippet",
        {
            "action": "create",
            "title": "Bahrain SEO Indexing Fix",
            "code": snippet_body,
            "code_type": "php",
            "location": "everywhere",
            "insert_method": "auto",
        },
    )
    print(code, str(data)[:500])

    print("=== settings ===")
    cli(
        "option update blogdescription 'ركن التطور البحرين: كشف تسربات بدون تكسير، عزل الأسطح، صيانة، تكييف، سباكة، تنظيف ومكافحة حشرات في المنامة والمحرق والرفاع وكل مدن البحرين.'",
        True,
    )
    cli("option update kayan_i18n_default_country bh", True)
    cli("option update permalink_structure /%postname%/", True)
    cli("rewrite flush", True)

    print("=== bulk SQL content + publish ===")
    sqls = [
        r"""UPDATE 2GGpPu6Sy_posts SET post_content = REPLACE(post_content, '{PHONE_RUKN_BAHRAIN}', '+971586634710') WHERE post_type='post'""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_content = REPLACE(post_content, '{WHATSAPP_RUKN_BAHRAIN}', '971586634710') WHERE post_type='post'""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_content = REPLACE(post_content, 'مدن المملكة', 'مدن البحرين') WHERE post_type IN ('post','page','widgets__posts')""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_content = REPLACE(post_content, 'داخل المملكة', 'داخل مملكة البحرين') WHERE post_type IN ('post','page','widgets__posts')""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_content = REPLACE(post_content, 'كل مدن المملكة', 'كل مدن البحرين') WHERE post_type IN ('post','page','widgets__posts')""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_content = REPLACE(post_content, '[[رقم الهاتف/واتساب]]', '+971586634710') WHERE post_content LIKE '%[[رقم الهاتف/واتساب]]%'""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_content = REGEXP_REPLACE(post_content, 'src=\"service-[0-9]+\\.webp\"', 'src=\"https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp\"') WHERE post_type='post' AND post_content LIKE '%service-%'""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_status='publish', post_date=NOW(), post_date_gmt=UTC_TIMESTAMP() WHERE post_type='post' AND post_status='draft' AND ID<>1 AND post_title NOT LIKE '%Hello world%'""",
        r"""UPDATE 2GGpPu6Sy_posts SET post_status='trash' WHERE ID IN (1,2)""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, '{PHONE_RUKN_BAHRAIN}', '+971586634710') WHERE meta_value LIKE '%PHONE_RUKN_BAHRAIN%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, '{WHATSAPP_RUKN_BAHRAIN}', '971586634710') WHERE meta_value LIKE '%WHATSAPP_RUKN_BAHRAIN%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, '[[عدد المشاريع]]', '+350') WHERE meta_value LIKE '%[[عدد المشاريع]]%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, '[[سنة التأسيس]]', '2024') WHERE meta_value LIKE '%[[سنة التأسيس]]%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, '[[رقم الهاتف/واتساب]]', '+971586634710') WHERE meta_value LIKE '%[[رقم الهاتف/واتساب]]%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, 'داخل المملكة', 'داخل مملكة البحرين') WHERE meta_value LIKE '%داخل المملكة%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, 'كل مدن المملكة', 'كل مدن البحرين') WHERE meta_value LIKE '%كل مدن المملكة%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, 'مدن المملكة', 'مدن البحرين') WHERE meta_value LIKE '%مدن المملكة%'""",
        r"""UPDATE 2GGpPu6Sy_postmeta SET meta_value = REPLACE(meta_value, 'في كل مدن المملكة', 'في كل مدن البحرين') WHERE meta_value LIKE '%في كل مدن المملكة%'""",
        r"""UPDATE 2GGpPu6Sy_options SET option_value = REPLACE(option_value, 'مدن المملكة', 'مدن البحرين') WHERE option_value LIKE '%مدن المملكة%'""",
    ]
    for sql in sqls:
        out = cli(f'db query "{sql}"', True, timeout=120)
        stdout = (out or {}).get("stdout") if isinstance(out, dict) else ""
        print(" ", str(stdout)[:240] if stdout else str(out)[:240])

    print("=== categories ===")
    cats = [
        ("كشف تسربات المياه", "water-leak-detection", "كشف تسربات المياه بدون تكسير في البحرين"),
        ("عزل الأسطح", "roof-insulation", "عزل الأسطح والخزانات في البحرين"),
        ("الصيانة العامة", "general-maintenance", "صيانة المباني والمنشآت في البحرين"),
        ("السباكة وتسليك المجاري", "plumbing", "سباكة وتسليك مجاري في البحرين"),
        ("التكييف والكهرباء", "ac-electrical", "تكييف وكهرباء في البحرين"),
        ("التنظيف والتعقيم", "cleaning", "تنظيف وتعقيم منازل في البحرين"),
        ("مكافحة الحشرات", "pest-control", "مكافحة حشرات وقوارض في البحرين"),
        ("الحدائق والمسابح", "gardens-pools", "تنسيق حدائق وصيانة مسابح في البحرين"),
        ("الصبغ والديكورات", "painting-decor", "صبغ وديكورات وجبس بورد في البحرين"),
    ]
    for name, slug, desc in cats:
        cli(
            f"term create category '{name}' --slug={slug} --description='{desc}'",
            True,
        )

    print("=== assign categories by title ===")
    mapping = [
        ("كشف تسربات المياه", ("تسرب", "كشف تسرب")),
        ("عزل الأسطح", ("عزل",)),
        ("الصيانة العامة", ("صيانة مباني", "ترميم", "صيانة عامة", "إنشاء")),
        ("السباكة وتسليك المجاري", ("سباك", "مجاري", "تسليك", "أدوات صحية")),
        ("التكييف والكهرباء", ("تكييف", "مكيف", "فريون", "كهرباء", "إنارة")),
        ("التنظيف والتعقيم", ("تنظيف", "تعقيم")),
        ("مكافحة الحشرات", ("حشرات", "صراصير", "قوارض", "مكافحة")),
        ("الحدائق والمسابح", ("حديق", "مسابح", "مسبح", "عشب", "نافورة")),
        ("الصبغ والديكورات", ("صبغ", "ديكور", "جبس")),
    ]
    for cat, keys in mapping:
        like = " OR ".join([f"post_title LIKE '%{k}%'" for k in keys])
        sql = (
            "INSERT IGNORE INTO 2GGpPu6Sy_term_relationships (object_id, term_taxonomy_id) "
            "SELECT p.ID, tt.term_taxonomy_id FROM 2GGpPu6Sy_posts p "
            "JOIN 2GGpPu6Sy_terms t ON t.name=%s "
            "JOIN 2GGpPu6Sy_term_taxonomy tt ON tt.term_id=t.term_id AND tt.taxonomy='category' "
            f"WHERE p.post_type='post' AND p.post_status='publish' AND ({like})"
        )
        # wp db query may not support placeholders; inline safely
        sql = sql.replace("%s", f"'{cat}'")
        cli(f'db query "{sql}"', True, timeout=120)

    cli(
        'db query "UPDATE 2GGpPu6Sy_term_taxonomy tt JOIN (SELECT term_taxonomy_id, COUNT(*) c FROM 2GGpPu6Sy_term_relationships GROUP BY term_taxonomy_id) x ON x.term_taxonomy_id=tt.term_taxonomy_id SET tt.count=x.c"',
        True,
    )

    print("=== cities taxonomy ===")
    cities = [
        ("المنامة", "manama"),
        ("المحرق", "muharraq"),
        ("الرفاع", "riffa"),
        ("مدينة حمد", "hamad-town"),
        ("مدينة عيسى", "isa-town"),
        ("عالي", "aali"),
        ("سترة", "sitra"),
        ("جدحفص", "jidhafs"),
        ("البديع", "budaiya"),
        ("سار", "saar"),
        ("توبلي", "tubli"),
        ("الحد", "hidd"),
    ]
    for name, slug in cities:
        cli(f"term create cities '{name}' --slug={slug}", True)
        cli(f"term create city '{name}' --slug={slug}", True)

    print("=== delete hello world if still published ===")
    cli("post update 1 --post_status=trash", True)
    cli("post update 2 --post_status=trash", True)

    print("=== done deploy core ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

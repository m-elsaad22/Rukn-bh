#!/usr/bin/env python3
"""Keep the UAE number on WhatsApp buttons only; hide it as a phone number."""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_bh_chrome import HEADER_CODES, option_update, run  # noqa: E402
from rewrite_bh_kayan import cli, req  # noqa: E402

VISIBLE = "واتساب 971586634710"
VISIBLE_NEW = "واتساب"
CONTACT_ID = 3379
CONTACT_OLD = "متاح يومياً — +971 58 663 4710 (مؤقت)"
CONTACT_NEW = "متاح يومياً عبر زر واتساب"


def patch_contact() -> None:
    code, data = req("GET", f"/wp/v2/pages/{CONTACT_ID}&context=edit&_fields=id,content", timeout=60)
    if code != 200:
        print("contact get", code, data)
        return
    raw = ((data.get("content") or {}).get("raw")) or ""
    new = raw.replace(CONTACT_OLD, CONTACT_NEW)
    if new == raw:
        print("contact skip")
        return
    code, out = req("POST", f"/wp/v2/pages/{CONTACT_ID}", {"content": new}, timeout=90)
    print("contact", code, str(out)[:160])


def digit_ids() -> list[int]:
    sql = (
        "SELECT ID FROM 2GGpPu6Sy_posts WHERE post_status='publish' AND post_type='post' "
        f"AND post_content LIKE '%{VISIBLE}%' ORDER BY ID"
    )
    out = cli(f'db query "{sql}" --limit=2000', write=False, timeout=90)
    raw = out.get("stdout") or ""
    try:
        data = json.loads(raw)
        rows = data.get("results") or data
    except json.JSONDecodeError:
        print("id parse", raw[:300])
        return []
    ids = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("ID"):
            ids.append(int(row["ID"]))
    print("digit ids", len(ids), flush=True)
    return ids


def scrub_post(pid: int) -> str:
    code, data = req(
        "GET",
        f"/wp/v2/posts/{pid}&context=edit&_fields=id,content,excerpt",
        timeout=60,
    )
    if code != 200:
        return f"{pid} get-{code}"
    raw = ((data.get("content") or {}).get("raw")) or ""
    excerpt = ((data.get("excerpt") or {}).get("raw")) or ""
    new = raw.replace(VISIBLE, VISIBLE_NEW)
    new_ex = excerpt.replace(VISIBLE, VISIBLE_NEW)
    if new == raw and new_ex == excerpt:
        return f"{pid} skip"
    payload = {}
    if new != raw:
        payload["content"] = new
    if new_ex != excerpt:
        payload["excerpt"] = new_ex
    code, out = req("POST", f"/wp/v2/posts/{pid}", payload, timeout=90)
    if code not in (200, 201):
        return f"{pid} post-{code}:{str(out)[:80]}"
    return f"{pid} ok"


def scrub_visible_digits() -> None:
    ids = digit_ids()
    if not ids:
        return
    ok = skip = err = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(scrub_post, pid): pid for pid in ids}
        for fut in as_completed(futs):
            try:
                msg = fut.result()
            except Exception as exc:  # noqa: BLE001
                msg = f"{futs[fut]} exc:{exc}"
            if msg.endswith(" ok"):
                ok += 1
            elif msg.endswith(" skip"):
                skip += 1
            else:
                err += 1
                print(msg, flush=True)
            if (ok + skip + err) % 50 == 0:
                print(f"progress ok={ok} skip={skip} err={err}", flush=True)
            time.sleep(0.04)
    print(f"digits ok={ok} skip={skip} err={err}", flush=True)


def main() -> int:
    if not os.environ.get("WP_APP_PASSWORD"):
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1

    print("=== keep WA UAE number on buttons; hide as phone ===", flush=True)
    option_update("header___codes", HEADER_CODES)
    run("option update whatsapp_number +971586634710")
    patch_contact()
    scrub_visible_digits()
    run(
        'db query "SELECT COUNT(*) AS left_digits FROM 2GGpPu6Sy_posts WHERE post_status=\'publish\' '
        f"AND post_type='post' AND post_content LIKE '%{VISIBLE}%'\"",
        write=False,
    )
    run(
        "cache purge --url=https://www.rukn-eltatawer.com/bh/,"
        "https://www.rukn-eltatawer.com/bh/contact-us/,"
        "https://www.rukn-eltatawer.com/bh/home-cleaning-manama/"
    )
    run("cache flush")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

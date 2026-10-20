#!/usr/bin/env python3
"""Upload tools/bh-fix-snippet.php to live Code Snippets id 5."""

from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNIPPET = ROOT / "tools" / "bh-fix-snippet.php"
WP_BASE = os.environ.get("WP_BASE", "https://www.rukn-eltatawer.com/bh").rstrip("/")
WP_USER = os.environ.get("WP_USER", "melsaad")
WP_PASS = os.environ.get("WP_APP_PASSWORD", "")
CTX = ssl.create_default_context()


def request(method: str, path: str, body=None, timeout: int = 120):
    url = WP_BASE + "/wp-json" + path
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode(),
        "User-Agent": "rukn-bh-gsc/1.0",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def main() -> None:
    if not WP_PASS:
        sys.exit("WP_APP_PASSWORD is required")
    code = SNIPPET.read_text(encoding="utf-8")
    print("deactivate", len(code))
    request("PUT", "/code-snippets/v1/snippets/5", {"active": False})
    time.sleep(1.2)
    request(
        "PUT",
        "/code-snippets/v1/snippets/5",
        {
            "name": "Rukn BH Live Fixes",
            "desc": "GSC indexing: city canonicals, noindex junk, author/empty-city 301s",
            "code": code,
            "scope": "global",
            "active": False,
            "priority": 1,
        },
    )
    time.sleep(1)
    request("PUT", "/code-snippets/v1/snippets/5", {"active": True})
    snip = request("GET", "/code-snippets/v1/snippets/5")
    print("active", snip.get("active"), "len", len(snip.get("code") or ""), "err", snip.get("code_error"))
    if snip.get("code_error"):
        sys.exit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Publish every Bahrain post with a unique timestamp one minute apart."""
from __future__ import annotations

import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import urllib.error
import urllib.request

BASE = "https://rukn-eltatawer.com/bh"
USER = os.environ.get("WP_USER", "melsaad")
PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
BAHRAIN = timezone(timedelta(hours=3))


def req(method: str, route: str, payload=None, timeout=90):
    url = f"{BASE}/?rest_route={route}"
    data = None if payload is None else json.dumps(payload).encode()
    headers = {
        "Authorization": "Basic "
        + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode(),
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 RuknBH-SEO/1.1",
    }
    if data:
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
            parsed = {"raw": body[:400]}
        return exc.code, parsed


def fetch_ids() -> list[int]:
    ids: list[int] = []
    page = 1
    while page <= 40:
        code, data = req(
            "GET",
            f"/wp/v2/posts&per_page=100&page={page}&status=publish,future,draft&_fields=id&orderby=id&order=asc",
        )
        if code != 200 or not isinstance(data, list) or not data:
            break
        ids.extend(int(p["id"]) for p in data)
        if len(data) < 100:
            break
        page += 1
    return ids


def set_date(pid: int, stamp: str) -> tuple[int, str]:
    code, out = req(
        "POST",
        f"/wp/v2/posts/{pid}",
        {"date": stamp, "status": "publish"},
    )
    if code in (200, 201) and out.get("status") == "publish":
        return pid, "ok"
    return pid, f"err{code}:{str(out)[:80]}"


def main() -> int:
    if not PASSWORD:
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1
    ids = fetch_ids()
    print("posts", len(ids))
    if not ids:
        return 1
    end = datetime.now(BAHRAIN).replace(second=0, microsecond=0)
    start = end - timedelta(minutes=len(ids) - 1)
    print("window", start.isoformat(), "->", end.isoformat())
    jobs = []
    for i, pid in enumerate(ids):
        stamp = (start + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%S")
        jobs.append((pid, stamp))
    ok = err = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(set_date, pid, stamp) for pid, stamp in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            _, status = fut.result()
            if status == "ok":
                ok += 1
            else:
                err += 1
                if err <= 8:
                    print("fail", status)
            if i % 200 == 0:
                print(f"progress {i}/{len(jobs)} ok={ok} err={err}")
    print(f"done ok={ok} err={err}")
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

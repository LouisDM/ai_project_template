#!/usr/bin/env python3
"""API smoke test — runs after deployment to verify critical paths.

Usage:
    python tests_e2e/api_smoke.py --base-url https://demo.premom.tech
    python tests_e2e/api_smoke.py --base-url http://cms.premom.tech:8006 --api-only
"""
import argparse
import sys
import time
from typing import Any

import httpx


class TestFailure(Exception):
    pass


def _step(label: str, fn):
    start = time.time()
    try:
        result = fn()
        elapsed = int((time.time() - start) * 1000)
        print(f"  [✓] {label:40s} ({elapsed}ms)")
        return result
    except TestFailure as e:
        print(f"  [✗] {label}")
        print(f"      {e}")
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"  [✗] {label}")
        print(f"      HTTP error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  [✗] {label}")
        print(f"      Unexpected: {type(e).__name__}: {e}")
        sys.exit(1)


def expect(cond: bool, msg: str):
    if not cond:
        raise TestFailure(msg)


def run(base_url: str, username: str, password: str) -> None:
    base_url = base_url.rstrip("/")
    print(f"\n部署后冒烟测试 — {base_url}")
    print("-" * 50)

    client = httpx.Client(timeout=10.0, follow_redirects=True)

    # Step 1: health
    def _health():
        r = client.get(f"{base_url}/health")
        expect(r.status_code == 200, f"status={r.status_code}, body={r.text[:200]}")
        expect(r.json().get("status") == "ok", f"body={r.text[:200]}")
        return r

    _step("GET /health", _health)

    # Step 2: login
    def _login():
        r = client.post(
            f"{base_url}/api/auth/login",
            json={"username": username, "password": password},
        )
        if r.status_code == 401:
            raise TestFailure(
                f"401 — admin 账号不存在或密码错误。\n"
                f"      建议: 在 EC2 上运行 sudo docker exec <project>-backend python seed.py"
            )
        expect(r.status_code == 200, f"status={r.status_code}, body={r.text[:200]}")
        token = r.json().get("access_token")
        expect(bool(token), "response missing access_token")
        return token

    token = _step(f"POST /api/auth/login ({username})", _login)
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Step 3: list items (baseline)
    def _list_baseline():
        r = client.get(f"{base_url}/api/items/", headers=auth_headers)
        expect(r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        expect(isinstance(data, list), f"response is not a list: {type(data)}")
        return data

    baseline = _step("GET /api/items/ (baseline)", _list_baseline)
    baseline_count = len(baseline)

    # Step 4: create item
    marker = f"SMOKE_TEST_{int(time.time())}"

    def _create():
        r = client.post(
            f"{base_url}/api/items/",
            headers=auth_headers,
            json={"title": marker, "description": "smoke test, safe to delete"},
        )
        expect(r.status_code == 201, f"status={r.status_code}, body={r.text[:200]}")
        item = r.json()
        expect(item.get("id") is not None, "response missing id")
        expect(item.get("title") == marker, f"title mismatch: {item.get('title')}")
        return item["id"]

    item_id = _step("POST /api/items/ (create)", _create)

    # Step 5: verify in list
    def _verify():
        r = client.get(f"{base_url}/api/items/", headers=auth_headers)
        expect(r.status_code == 200, f"status={r.status_code}")
        data: list[dict[str, Any]] = r.json()
        expect(
            any(it.get("id") == item_id for it in data),
            f"item id={item_id} not found in list of {len(data)} items",
        )
        expect(
            len(data) == baseline_count + 1,
            f"count mismatch: baseline={baseline_count}, now={len(data)}",
        )

    _step("GET /api/items/ (verify)", _verify)

    # Step 6: cleanup (delete)
    def _delete():
        r = client.delete(f"{base_url}/api/items/{item_id}", headers=auth_headers)
        expect(r.status_code in (204, 200), f"status={r.status_code}")

    _step(f"DELETE /api/items/{item_id} (cleanup)", _delete)

    client.close()
    print("-" * 50)
    print("全部通过 ✓")


def main():
    parser = argparse.ArgumentParser(description="API smoke test")
    parser.add_argument("--base-url", required=True, help="https://demo.premom.tech")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()
    run(args.base_url, args.username, args.password)


if __name__ == "__main__":
    main()

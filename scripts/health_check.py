#!/usr/bin/env python3
"""
This is the health check script to check if the API is healthy.
"""
import argparse
import sys
import time
import urllib.request
import urllib.error
import json


def check_once(url, timeout, expected_status, json_contains, headers):
    try:
        req_headers = {"User-Agent": "health-check-script/1.0"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            body = resp.read()
            if expected_status and code != expected_status:
                return False, f"unexpected status code: {code}"
            if json_contains:
                try:
                    data = json.loads(body)
                except Exception as e:
                    return False, f"failed to parse json: {e}"
                # simple substring check anywhere in serialized JSON
                if isinstance(json_contains, str) and json_contains not in json.dumps(data):
                    return False, f"expected JSON to contain '{json_contains}'"
            return True, "ok"
    except urllib.error.HTTPError as e:
        return False, f"HTTPError {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URLError: {e.reason}"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="URL to check (http(s)://)")
    parser.add_argument("--expected-status", type=int, default=200)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--backoff", type=float, default=2.0, help="backoff multiplier")
    parser.add_argument("--json-contains", type=str, default=None, help="optional substring expected in JSON response body")
    parser.add_argument("--bearer-token", type=str, default=None, help="optional bearer token for Authorization header")

    args = parser.parse_args()

    extra_headers = {}
    if args.bearer_token:
        extra_headers["Authorization"] = f"Bearer {args.bearer_token}"

    wait = 1.0
    for attempt in range(1, args.retries + 1):
        ok, msg = check_once(args.url, args.timeout, args.expected_status, args.json_contains, extra_headers)
        print(f"attempt {attempt}/{args.retries}: {msg}")
        if ok:
            print("Health check passed")
            sys.exit(0)
        if attempt < args.retries:
            time.sleep(wait)
            wait *= args.backoff

    print("Health check failed after retries", file=sys.stderr)
    sys.exit(2)


if __name__ == '__main__':
    main()

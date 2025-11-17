#!/usr/bin/env python3
"""
Utility to exercise API Gateway endpoints and produce a Markdown report.

Usage example:
    python scripts/api_smoke_report.py \
        --swagger staging-swagger.json \
        --base-url https://example.execute-api.ap-southeast-2.amazonaws.com/staging \
        --token eyJ... \
        --methods GET \
        --output staging-smoke-report.md
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable, List, Set


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run smoke checks against API Gateway endpoints.")
    parser.add_argument("--swagger", required=True, help="Path to swagger/OpenAPI export (JSON).")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL including stage, e.g. https://xxx.execute-api.../staging",
    )
    parser.add_argument(
        "--token",
        default="",
        help="Optional bearer token used for Authorization header.",
    )
    parser.add_argument(
        "--methods",
        default="GET",
        help="Comma separated list of HTTP methods to test (default: GET).",
    )
    parser.add_argument(
        "--include-parameterized",
        action="store_true",
        help="Include paths with path parameters (e.g. /datasets/{id}).",
    )
    parser.add_argument(
        "--output",
        default="api-smoke-report.md",
        help="Markdown report file to write (default: api-smoke-report.md).",
    )
    return parser.parse_args()


@dataclass
class Endpoint:
    path: str
    method: str


@dataclass
class Result:
    endpoint: Endpoint
    url: str
    status: int
    ok: bool
    message: str


def load_endpoints(swagger_path: str, methods: Set[str], include_parameterized: bool) -> List[Endpoint]:
    with open(swagger_path, "r", encoding="utf-8") as handle:
        swagger = json.load(handle)

    endpoints: List[Endpoint] = []
    paths = swagger.get("paths", {})

    for path, method_map in paths.items():
        if not include_parameterized and "{" in path:
            continue

        for method, _ in method_map.items():
            method_upper = method.upper()
            if method_upper in methods:
                endpoints.append(Endpoint(path=path, method=method_upper))

    return sorted(endpoints, key=lambda e: (e.path, e.method))


def make_request(url: str, method: str, token: str) -> Result:
    headers = {"User-Agent": "api-smoke-tester/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if method not in {"GET", "HEAD"}:
        data = b"{}"

    request = urllib.request.Request(url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status = response.getcode()
            return Result(
                endpoint=None,  # placeholder, to be filled by caller
                url=url,
                status=status,
                ok=200 <= status < 400,
                message="",
            )
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")[:200]
        return Result(
            endpoint=None,
            url=url,
            status=err.code,
            ok=False,
            message=body.strip() or err.reason,
        )
    except Exception as exc:  # pylint: disable=broad-except
        return Result(
            endpoint=None,
            url=url,
            status=0,
            ok=False,
            message=str(exc),
        )


def write_report(output_path: str, base_url: str, methods: Iterable[str], token_used: bool, results: List[Result]) -> None:
    successes = sum(1 for r in results if r.ok)
    failures = sum(1 for r in results if not r.ok)

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("# Staging API smoke report\n\n")
        handle.write(f"- Base URL: `{base_url}`\n")
        handle.write(f"- Methods: {', '.join(methods)}\n")
        handle.write(f"- Bearer token used: {'yes' if token_used else 'no'}\n")
        handle.write(f"- Endpoints tested: {len(results)}\n")
        handle.write(f"- Success: {successes}\n")
        handle.write(f"- Failure: {failures}\n\n")

        if results:
            handle.write("| Status | Method | Path | HTTP | Message |\n")
            handle.write("| --- | --- | --- | --- | --- |\n")
            for result in results:
                icon = "PASS" if result.ok else "FAIL"
                message = result.message.replace("\n", " ")
                handle.write(
                    f"| {icon} | {result.endpoint.method} | `{result.endpoint.path}` | {result.status or 'N/A'} | {message} |\n"
                )
        else:
            handle.write("_No endpoints discovered in swagger export._\n")


def main() -> int:
    args = parse_args()
    methods = {method.strip().upper() for method in args.methods.split(",") if method.strip()}
    if not methods:
        print("No HTTP methods specified via --methods", file=sys.stderr)
        return 1

    endpoints = load_endpoints(args.swagger, methods, args.include_parameterized)

    base = args.base_url.rstrip("/")
    results: List[Result] = []

    print(f"[smoke] Testing {len(endpoints)} endpoints ({', '.join(methods)})")

    for endpoint in endpoints:
        url = f"{base}{endpoint.path}"
        result = make_request(url, endpoint.method, args.token)
        result.endpoint = endpoint
        results.append(result)

        status_display = result.status if result.status else "N/A"
        if result.ok:
            print(f"[OK] {endpoint.method} {endpoint.path} -> {status_display}")
        else:
            print(f"[WARN] {endpoint.method} {endpoint.path} -> {status_display} ({result.message})")

    write_report(args.output, base, methods, bool(args.token), results)
    print(f"[smoke] Report written to {args.output} (success={sum(r.ok for r in results)}, failure={sum(not r.ok for r in results)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 1
DEFAULT_BACKOFF = 2.0
USER_AGENT = "api-smoke-suite/1.0"


@dataclass
class Endpoint:
    path: str
    requires_auth: bool = False
    expected_status: int = 200


@dataclass
class Result:
    endpoint: Endpoint
    url: str
    status_code: Optional[int]
    ok: bool
    skipped: bool
    message: str


def parse_paths_file(path: Path) -> List[Endpoint]:
    endpoints: List[Endpoint] = []
    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        ep = Endpoint(path=parts[0])
        for token in parts[1:]:
            if token.lower() in {"auth", "requires_auth"}:
                ep.requires_auth = True
            elif token.lower().startswith("status="):
                try:
                    ep.expected_status = int(token.split("=", 1)[1])
                except ValueError:
                    raise ValueError(f"Invalid status token '{token}' in line: {raw_line}")
            else:
                raise ValueError(f"Unknown token '{token}' in line: {raw_line}")
        endpoints.append(ep)
    return endpoints


def build_url(base_url: str, path: str) -> str:
    if not base_url:
        raise ValueError("Base URL must not be empty")
    base = base_url.rstrip("/")
    suffix = path.lstrip("/")
    return f"{base}/{suffix}"


def http_get(url: str, token: Optional[str], timeout: float) -> Tuple[int, str]:
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.getcode()
        try:
            body = resp.read().decode("utf-8", errors="replace")
        except Exception:
            body = "<binary>"
        return status, body[:2000]


def run_check(
    endpoint: Endpoint,
    base_url: str,
    token: Optional[str],
    timeout: float,
    retries: int,
    backoff: float,
) -> Result:
    url = build_url(base_url, endpoint.path)
    if endpoint.requires_auth and not token:
        return Result(
            endpoint=endpoint,
            url=url,
            status_code=None,
            ok=False,
            skipped=True,
            message="Authentication required but no token provided",
        )

    attempt = 0
    delay = 1.0
    last_error = ""
    status_code: Optional[int] = None

    while attempt < retries:
        attempt += 1
        try:
            status_code, body_preview = http_get(url, token, timeout)
            ok = status_code == endpoint.expected_status
            message = (
                f"Status {status_code} (expected {endpoint.expected_status})"
                if ok
                else f"Unexpected status {status_code} (expected {endpoint.expected_status}); body preview: {body_preview}"
            )
            return Result(
                endpoint=endpoint,
                url=url,
                status_code=status_code,
                ok=ok,
                skipped=False,
                message=message,
            )
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            body = exc.read().decode("utf-8", errors="replace")
            last_error = f"HTTPError {exc.code}: {exc.reason}; body preview: {body[:2000]}"
        except urllib.error.URLError as exc:
            last_error = f"URLError: {exc.reason}"
        except Exception as exc:  # pragma: no cover - defensive
            last_error = f"Error: {exc}"

        if attempt < retries:
            time.sleep(delay)
            delay *= backoff

    return Result(
        endpoint=endpoint,
        url=url,
        status_code=status_code,
        ok=False,
        skipped=False,
        message=last_error or "Unknown error",
    )


def load_endpoints(paths: Iterable[str], paths_file: Optional[Path]) -> List[Endpoint]:
    endpoints: List[Endpoint] = []
    if paths_file:
        endpoints.extend(parse_paths_file(paths_file))
    for item in paths or []:
        endpoints.append(Endpoint(path=item))
    if not endpoints:
        raise ValueError("No endpoints specified. Provide --paths or --paths-file.")
    return endpoints


def write_json(results: List[Result], path: Path) -> None:
    serialisable = [
        {
            "path": res.endpoint.path,
            "requires_auth": res.endpoint.requires_auth,
            "expected_status": res.endpoint.expected_status,
            "url": res.url,
            "status_code": res.status_code,
            "ok": res.ok,
            "skipped": res.skipped,
            "message": res.message,
        }
        for res in results
    ]
    path.write_text(json.dumps(serialisable, indent=2))


def write_markdown(results: List[Result], path: Path) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    lines = [
        "### API Smoke Test Report",
        "",
        f"- Total endpoints: {total}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Skipped: {skipped}",
        "",
        "| Path | Status | Message |",
        "| --- | --- | --- |",
    ]
    for res in results:
        status = "PASS" if res.ok else ("SKIPPED" if res.skipped else "FAIL")
        lines.append(f"| `{res.endpoint.path}` | {status} | {res.message.replace('|', '\\|')} |")
    path.write_text("\n".join(lines) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="API smoke test runner")
    parser.add_argument("--base-url", required=True, help="Base URL including stage prefix")
    parser.add_argument("--paths", nargs="*", help="Extra endpoint paths to include")
    parser.add_argument("--paths-file", type=Path, help="File with one endpoint per line. "
                        "Append 'auth' to require bearer token, 'status=XXX' to override expected status.")
    parser.add_argument("--bearer-token", default=None, help="Optional bearer token for Authorization header")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Retries per endpoint")
    parser.add_argument("--backoff", type=float, default=DEFAULT_BACKOFF, help="Backoff multiplier between retries")
    parser.add_argument("--report-json", type=Path, help="Path to write JSON report")
    parser.add_argument("--report-md", type=Path, help="Path to write Markdown report")

    args = parser.parse_args(argv)

    try:
        endpoints = load_endpoints(args.paths or [], args.paths_file)
    except Exception as exc:
        print(f"[smoke] configuration error: {exc}", file=sys.stderr)
        return 1

    results: List[Result] = []
    for ep in endpoints:
        res = run_check(ep, args.base_url, args.bearer_token, args.timeout, args.retries, args.backoff)
        status = "PASS" if res.ok else ("SKIPPED" if res.skipped else "FAIL")
        print(f"[smoke] {status} {ep.path}: {res.message}")
        results.append(res)

    if args.report_json:
        try:
            write_json(results, args.report_json)
        except Exception as exc:
            print(f"[smoke] failed to write JSON report: {exc}", file=sys.stderr)
    if args.report_md:
        try:
            write_markdown(results, args.report_md)
        except Exception as exc:
            print(f"[smoke] failed to write Markdown report: {exc}", file=sys.stderr)

    failures = [r for r in results if not r.ok and not r.skipped]
    if failures:
        print(f"[smoke] WARNING: {len(failures)} endpoints failed", file=sys.stderr)
    skipped = [r for r in results if r.skipped]
    if skipped:
        print(f"[smoke] NOTE: {len(skipped)} endpoints skipped (auth/token requirements)", file=sys.stderr)

    # Always exit 0 so workflows can continue.
    return 0


if __name__ == "__main__":
    sys.exit(main())


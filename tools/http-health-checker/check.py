import argparse
import concurrent.futures
import html
import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def normalize_url(value):
    value = value.strip()
    if not value:
        return ""
    if "://" not in value:
        value = "https://" + value
    return value


def certificate_info(url, timeout):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return {}
    port = parsed.port or 443
    context = ssl.create_default_context()
    with socket.create_connection((parsed.hostname, port), timeout=timeout) as connection:
        with context.wrap_socket(connection, server_hostname=parsed.hostname) as secure:
            certificate = secure.getpeercert()
    expires = datetime.fromtimestamp(
        ssl.cert_time_to_seconds(certificate["notAfter"]), timezone.utc
    )
    remaining = expires - datetime.now(timezone.utc)
    return {
        "ssl_expires_at": expires.isoformat(),
        "ssl_days_left": remaining.days,
    }


def check_url(url, timeout=10, verify_ssl=True):
    url = normalize_url(url)
    result = {
        "url": url,
        "ok": False,
        "status": None,
        "elapsed_ms": None,
        "final_url": None,
        "content_type": None,
        "error": None,
    }
    if not url:
        result["error"] = "empty URL"
        return result

    context = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "health-checker/1.0", "Accept": "*/*"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            response.read(1)
            result["status"] = response.status
            result["final_url"] = response.geturl()
            result["content_type"] = response.headers.get_content_type()
            result["ok"] = 200 <= response.status < 400
    except urllib.error.HTTPError as error:
        result["status"] = error.code
        result["final_url"] = error.geturl()
        result["content_type"] = error.headers.get_content_type() if error.headers else None
        result["error"] = str(error)
    except Exception as error:
        result["error"] = str(error)
    finally:
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)

    if urllib.parse.urlsplit(url).scheme == "https" and verify_ssl:
        try:
            result.update(certificate_info(url, timeout))
        except Exception as error:
            result["ssl_error"] = str(error)
    return result


def read_targets(values, filename=None):
    targets = [normalize_url(value) for value in values]
    if filename:
        for line in Path(filename).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                targets.append(normalize_url(line))
    return list(dict.fromkeys(target for target in targets if target))


def run_checks(targets, timeout, workers, verify_ssl):
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(check_url, url, timeout, verify_ssl) for url in targets]
        return [future.result() for future in futures]


def print_results(results):
    print(f"{'STATUS':<8} {'TIME':>9}  URL")
    for item in results:
        status = str(item["status"]) if item["status"] is not None else "ERROR"
        elapsed = f'{item["elapsed_ms"]:.1f} ms'
        suffix = f'  {item["error"]}' if item["error"] else ""
        print(f"{status:<8} {elapsed:>9}  {item['url']}{suffix}")


def write_json(filename, results):
    Path(filename).write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_html(filename, results):
    rows = []
    for item in results:
        state = "OK" if item["ok"] else "NG"
        status = item["status"] if item["status"] is not None else "-"
        error = item["error"] or ""
        rows.append(
            "<tr>"
            f"<td>{state}</td>"
            f"<td>{status}</td>"
            f"<td>{item['elapsed_ms']:.1f} ms</td>"
            f"<td>{html.escape(item['url'])}</td>"
            f"<td>{html.escape(error)}</td>"
            "</tr>"
        )
    document = (
        "<!doctype html><meta charset=\"utf-8\"><title>Health check</title>"
        "<style>body{font:14px system-ui;margin:32px;color:#222}table{border-collapse:collapse;width:100%}"
        "th,td{padding:8px 10px;border-bottom:1px solid #ddd;text-align:left}th{background:#f5f5f5}</style>"
        "<h1>Health check</h1><table><thead><tr><th>Result</th><th>Status</th>"
        "<th>Time</th><th>URL</th><th>Error</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
    Path(filename).write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--file")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--json")
    parser.add_argument("--html")
    parser.add_argument("--insecure", action="store_true")
    args = parser.parse_args()

    targets = read_targets(args.urls, args.file)
    if not targets:
        parser.error("URL or --file is required")
    results = run_checks(
        targets,
        timeout=max(args.timeout, 0.1),
        workers=max(args.workers, 1),
        verify_ssl=not args.insecure,
    )
    print_results(results)
    if args.json:
        write_json(args.json, results)
    if args.html:
        write_html(args.html, results)
    raise SystemExit(0 if all(item["ok"] for item in results) else 1)


if __name__ == "__main__":
    main()

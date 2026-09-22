import argparse
import csv
import os
import random
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

USER_AGENT = "GeniusKala-Host-Monitor/1.0"
TEHRAN = timezone(timedelta(hours=3, minutes=30))

FIELDS = [
    "timestamp_utc", "timestamp_tehran", "url", "test_url",
    "http_code", "dns_s", "connect_s", "tls_s", "ttfb_s", "total_s",
    "size_bytes", "remote_ip", "litespeed_cache", "status", "error"
]

def load_urls(path):
    urls = []
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {line}")
        urls.append(line)
    if not urls:
        raise ValueError("urls.txt contains no URLs.")
    return urls

def add_timing_param(url):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["gk_timing"] = "1"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

def curl_test(url, timeout):
    fmt = (
        r'{"http_code":"%{http_code}","dns":"%{time_namelookup}",'
        r'"connect":"%{time_connect}","tls":"%{time_appconnect}",'
        r'"ttfb":"%{time_starttransfer}","total":"%{time_total}",'
        r'"size":"%{size_download}","ip":"%{remote_ip}"}'
    )
    cmd = [
        "curl", "-L", "-sS", "--compressed",
        "-A", USER_AGENT,
        "--max-time", str(timeout),
        "-o", os.devnull,
        "-D", "-",
        "-w", "\n__GK__" + fmt,
        url
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return {"status": "ERROR", "error": p.stderr.strip() or f"curl exit {p.returncode}"}

    if "__GK__" not in p.stdout:
        return {"status": "ERROR", "error": "curl metrics not found"}

    headers_text, metrics_text = p.stdout.rsplit("__GK__", 1)
    import json
    m = json.loads(metrics_text.strip())

    # آخرین بلوک هدر بعد از redirectها
    blocks = [b for b in headers_text.replace("\r\n", "\n").split("\n\n") if b.startswith("HTTP/")]
    headers = {}
    if blocks:
        for line in blocks[-1].splitlines()[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

    return {
        "status": "OK",
        "error": "",
        "http_code": m.get("http_code", ""),
        "dns_s": m.get("dns", ""),
        "connect_s": m.get("connect", ""),
        "tls_s": m.get("tls", ""),
        "ttfb_s": m.get("ttfb", ""),
        "total_s": m.get("total", ""),
        "size_bytes": m.get("size", ""),
        "remote_ip": m.get("ip", ""),
        "litespeed_cache": headers.get("x-litespeed-cache", ""),
    }

def append_csv(path, row):
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(row)

def choose_url(urls, order, index):
    if order == "random":
        return random.choice(urls), index
    url = urls[index % len(urls)]
    return url, index + 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls-file", default="urls.txt")
    ap.add_argument("--order", choices=["sequential", "random"], default="sequential")
    ap.add_argument("--duration-minutes", type=int, required=True)
    ap.add_argument("--interval-minutes", type=int, required=True)
    ap.add_argument("--segment", type=int, required=True)
    ap.add_argument("--start-index", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    urls = load_urls(args.urls_file)
    out = Path("results")
    out.mkdir(exist_ok=True)
    csv_path = out / f"host-speed-segment-{args.segment:02d}.csv"

    deadline = time.monotonic() + args.duration_minutes * 60
    index = args.start_index
    sample = 0

    while True:
        original_url, index = choose_url(urls, args.order, index)
        test_url = add_timing_param(original_url)
        now = datetime.now(timezone.utc)
        result = curl_test(test_url, args.timeout)
        sample += 1

        row = {
            "timestamp_utc": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_tehran": now.astimezone(TEHRAN).strftime("%Y-%m-%d %H:%M:%S"),
            "url": original_url,
            "test_url": test_url,
            "http_code": result.get("http_code", ""),
            "dns_s": result.get("dns_s", ""),
            "connect_s": result.get("connect_s", ""),
            "tls_s": result.get("tls_s", ""),
            "ttfb_s": result.get("ttfb_s", ""),
            "total_s": result.get("total_s", ""),
            "size_bytes": result.get("size_bytes", ""),
            "remote_ip": result.get("remote_ip", ""),
            "litespeed_cache": result.get("litespeed_cache", ""),
            "status": result.get("status", "ERROR"),
            "error": result.get("error", ""),
        }
        append_csv(csv_path, row)

        print(
            f'[{sample}] {row["timestamp_tehran"]} | {original_url} | '
            f'HTTP {row["http_code"] or "-"} | TTFB {row["ttfb_s"] or "-"}s | '
            f'Total {row["total_s"] or "-"}s | LS {row["litespeed_cache"] or "-"}',
            flush=True
        )

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(args.interval_minutes * 60, remaining))

if __name__ == "__main__":
    main()

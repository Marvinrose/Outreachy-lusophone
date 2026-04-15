"""
Outreachy Round 32 - Task T418286
==================================
Script      : Task 2 - Intern.py
Contributor : Marvinrose Chibuezem

Purpose:
    Read a list of URLs from a CSV file and print the HTTP status code
    of each one in the required format:

        (STATUS CODE) URL
    e.g. (200) https://www.nytimes.com/...

Usage (Windows):
    python "Task 2 - Intern.py"
    python "Task 2 - Intern.py" "Task 2 - Intern.csv"

Usage (Mac / Linux):
    python3 "Task 2 - Intern.py"
    python3 "Task 2 - Intern.py" "Task 2 - Intern.csv"

Dependency:
    pip install requests
"""

import csv
import sys
import time
import threading
from collections import Counter

try:
    import requests
    from requests.exceptions import (
        ConnectionError as ReqConnectionError,
        Timeout,
        SSLError,
        TooManyRedirects,
        RequestException,
    )
except ImportError:
    print("Error: install the requests library first —  pip install requests")
    sys.exit(1)


# ── Settings ──────────────────────────────────────────────────────────────────

CSV_FILE    = "Task 2 - Intern.csv"
TIMEOUT     = 10   # seconds per request
MAX_WORKERS = 10   # concurrent threads

# Wikimedia's User-Agent policy requires scripts to identify themselves.
# https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = (
    "OutreachyApplicant/1.0 "
    "(Wikimedia Lusophone Wishlist T418286; "
    "contact: tecnologia@wmnobrasil.org)"
)

_lock = threading.Lock()


# ── Core functions ────────────────────────────────────────────────────────────

def get_status(url):
    """
    Return the HTTP status code of url as a string.

    Uses HEAD instead of GET - we only need the status code, not the page
    body, so HEAD is faster and uses less bandwidth.

    Returns a descriptive token on network errors instead of raising.
    Retries once on timeout or connection reset before giving up.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.head(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        return str(resp.status_code)
    except Timeout:
        # One retry after a short pause for transient timeouts
        try:
            time.sleep(1)
            resp = requests.head(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            return str(resp.status_code)
        except Exception:
            return "TIMEOUT"
    except SSLError:
        return "SSL_ERROR"
    except TooManyRedirects:
        return "TOO_MANY_REDIRECTS"
    except ReqConnectionError:
        return "CONNECTION_ERROR"
    except RequestException:
        return "REQUEST_ERROR"


def check_url(url, results):
    """Fetch the status for url, print it, and record it in results."""
    status = get_status(url)
    with _lock:
        print(f"({status}) {url}", flush=True)
    results.append(status)


def read_urls(filepath):
    """
    Read URLs from the CSV file.

    The file starts with a 'urls' header row which we skip.
    We open with utf-8-sig encoding to strip the invisible BOM byte
    that some text editors add, which would otherwise prevent the header
    check from matching and cause it to leak into the output.
    """
    urls = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            url = row[0].strip()
            # Skip the header row and any non-URL values
            if url.lower() in ("url", "urls") or not url.startswith("http"):
                continue
            urls.append(url)
    return urls


def print_summary(results, total, elapsed):
    """Print a grouped count of status codes after all URLs are checked."""
    counts = Counter(results)
    groups = [
        ("2xx OK",           lambda c: c.isdigit() and c[0] == "2"),
        ("3xx Redirect",     lambda c: c.isdigit() and c[0] == "3"),
        ("4xx Client error", lambda c: c.isdigit() and c[0] == "4"),
        ("5xx Server error", lambda c: c.isdigit() and c[0] == "5"),
        ("Network error",    lambda c: not c.isdigit()),
    ]
    print()
    print("─" * 48)
    print(f"  Summary  ({total} URLs · {elapsed:.1f}s)")
    print("─" * 48)
    for label, test in groups:
        for code in sorted(c for c in counts if test(c)):
            print(f"  ({code}) {label}: {counts[code]}")
    print("─" * 48)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else CSV_FILE

    try:
        urls = read_urls(filepath)
    except FileNotFoundError:
        print(f"Error: file not found — '{filepath}'")
        sys.exit(1)

    if not urls:
        print("No URLs found in the file.")
        sys.exit(1)

    results = []
    start = time.time()

    # Check URLs concurrently using threads. requests is a blocking library,
    # so threads (not asyncio) are the right tool here — the bottleneck is
    # network I/O and multiple threads run independently while each waits.
    active = []
    for url in urls:
        t = threading.Thread(target=check_url, args=(url, results), daemon=True)
        t.start()
        active.append(t)
        # Keep at most MAX_WORKERS threads running at once
        while sum(1 for th in active if th.is_alive()) >= MAX_WORKERS:
            time.sleep(0.05)

    for t in active:
        t.join()

    print_summary(results, len(urls), time.time() - start)


if __name__ == "__main__":
    main()
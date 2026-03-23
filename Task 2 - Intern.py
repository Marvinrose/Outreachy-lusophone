"""
Outreachy Round 32 - Task T418286
==================================
Script  : Task 2 - Intern.py
Purpose : Read a list of URLs from a CSV file and print the HTTP
          status code of each one in the required format:

              (STATUS CODE) URL
          e.g. (200) https://www.nytimes.com/...

Usage:
    python3 Task 2 - Intern.py                          # uses default CSV
    python3 Task 2 - Intern.py "Task 2 - Intern.csv"   # explicit path
    python3 Task 2 - Intern.py --workers 15             # set concurrency

Dependency:
    pip install requests

Design notes:
    - Respects Wikimedia's User-Agent policy (meta.wikimedia.org/wiki/User-Agent_policy).
    - Handles all common network errors with clear tokens instead of tracebacks.
    - Uses threads for concurrency — the CSV has ~170 URLs; sequential requests would take several minutes.
    - Prints a grouped summary at the end for quick health-check.
    - CSV reader is tolerant: handles the tab-separated extra columns, the "urls" header, empty rows, and duplicate entries in the file.

Contributor: Marvinrose Chibuezem
"""

import csv
import sys
import time
import argparse
import threading
from urllib.parse import urlparse
from collections import Counter

try:
    import requests
    from requests.exceptions import (
        ConnectionError as ReqConnectionError,
        Timeout,
        TooManyRedirects,
        SSLError,
        RequestException,
    )
except ImportError:
    print("Error: 'requests' library is not installed.")
    print("Fix:   pip install requests")
    sys.exit(1)


# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_CSV     = "Task 2 - Intern.csv"
REQUEST_TIMEOUT = 15    # seconds — generous for slow/legacy Brazilian news sites
MAX_WORKERS     = 10    # concurrent threads (respectful to servers)
RETRY_ON        = (Timeout, ReqConnectionError)   # errors worth retrying once

# Wikimedia User-Agent policy:
# Every automated request must identify the project and contact info.
USER_AGENT = (
    "OutreachyApplicant/1.0 "
    "(Wikimedia Lusophone Wishlist T418286; "
    "contact: tecnologia@wmnobrasil.org)"
)


# ── Thread safety ─────────────────────────────────────────────────────────────

_print_lock = threading.Lock()


def safe_print(line: str) -> None:
    """Write a line atomically so concurrent threads don't interleave output."""
    with _print_lock:
        print(line, flush=True)


# ── URL validation ────────────────────────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    """
    Return True for well-formed HTTP or HTTPS URLs.

    Uses urlparse (part of the standard library) rather than a regex —
    more readable and handles edge cases like international domain names.
    """
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except ValueError:
        return False


# ── HTTP request ──────────────────────────────────────────────────────────────

def get_status(url: str, attempt: int = 1) -> str:
    """
    Return the HTTP status code of *url* as a string, e.g. "200".

    On transient errors (timeout, connection reset) a single retry is
    attempted after a 1-second pause.  Persistent failures return a
    descriptive uppercase token so the caller can categorise them.

    Return values:
        "200", "301", "404", "500", ...  – actual HTTP status codes
        "INVALID_URL"                    – string is not a valid URL
        "TIMEOUT"                        – connection/read timed out
        "CONNECTION_ERROR"               – DNS failure, refused, reset
        "SSL_ERROR"                      – TLS certificate problem
        "TOO_MANY_REDIRECTS"             – redirect loop
        "REQUEST_ERROR"                  – any other requests exception
    """
    if not is_valid_url(url):
        return "INVALID_URL"

    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,    # follow redirects; report final code
        )
        return str(resp.status_code)

    except Timeout:
        if attempt == 1:
            time.sleep(1)
            return get_status(url, 2)
        return "TIMEOUT"

    except SSLError:
        return "SSL_ERROR"

    except TooManyRedirects:
        return "TOO_MANY_REDIRECTS"

    except ReqConnectionError:
        if attempt == 1:
            time.sleep(1)
            return get_status(url, 2)
        return "CONNECTION_ERROR"

    except RequestException:
        return "REQUEST_ERROR"


# ── Worker (run in a thread) ──────────────────────────────────────────────────

def worker(url: str, results: list) -> None:
    """
    Fetch status for *url*, print it in the required format, and
    append the status code to *results* for the summary.
    """
    status = get_status(url)
    safe_print(f"({status}) {url}")
    results.append(status)


# ── CSV reader ────────────────────────────────────────────────────────────────

def read_urls(filepath: str) -> list[str]:
    """
    Read URLs from the CSV file provided with the task.

    The actual file has:
      - A header row whose column is named "urls" (plural).
      - Tab characters (\t) separating extra metadata columns.
      - Occasional blank rows.
      - Some rows where only the first column holds a URL; others hold
        extra fragments or metadata in columns 2-4 that should be ignored.

    We therefore:
      1. Sniff the delimiter (comma or tab) from the first 4 KB.
      2. Read only column 0 of every row.
      3. Skip blank values and any header-like row (url / urls).
    """
    urls = []

    encodings = ["utf-8", "utf-8-sig", "latin-1"]

    for enc in encodings:
        try:
            with open(filepath, newline="", encoding=enc) as fh:
                sample = fh.read(4096)
                fh.seek(0)

                # Detect delimiter; default to comma if sniffer fails
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(fh, dialect)
                for row in reader:
                    if not row:
                        continue

                    url = row[0].strip()

                    # Skip empty cells and header rows
                    if not url or url.lower() in ("url", "urls"):
                        continue

                    urls.append(url)

            return urls   # success — stop trying encodings

        except UnicodeDecodeError:
            urls = []     # reset and try next encoding
            continue

    # If we get here, all encodings failed
    print(f"Error: could not decode '{filepath}' with any known encoding.",
          file=sys.stderr)
    sys.exit(1)


def open_csv(filepath: str) -> list[str]:
    """Wrap read_urls with file-not-found / permission error handling."""
    try:
        return read_urls(filepath)
    except FileNotFoundError:
        print(f"Error: file not found – '{filepath}'", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: no read permission for '{filepath}'", file=sys.stderr)
        sys.exit(1)


# ── Summary report ────────────────────────────────────────────────────────────

def print_summary(results: list[str], total: int, elapsed: float) -> None:
    """
    Print a grouped count of status codes.

    Groups: 2xx success · 3xx redirect · 4xx client error ·
            5xx server error · network/other
    """
    counts = Counter(results)

    groups = [
        ("2xx  OK",             lambda c: c.isdigit() and c[0] == "2"),
        ("3xx  Redirect",       lambda c: c.isdigit() and c[0] == "3"),
        ("4xx  Client error",   lambda c: c.isdigit() and c[0] == "4"),
        ("5xx  Server error",   lambda c: c.isdigit() and c[0] == "5"),
        ("Network / other",     lambda c: not c.isdigit()),
    ]

    print()
    print("─" * 52)
    print(f"  Summary  ({total} URLs  ·  {elapsed:.1f}s)")
    print("─" * 52)

    for label, test in groups:
        matching = sorted(c for c in counts if test(c))
        for code in matching:
            print(f"  ({code})  {label}:  {counts[code]}")

    print("─" * 52)


# ── CLI and main ──────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Print the HTTP status code for every URL in a CSV file."
    )
    p.add_argument(
        "csv_file",
        nargs="?",
        default=DEFAULT_CSV,
        help=f"Path to the CSV file (default: {DEFAULT_CSV!r})",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        metavar="N",
        help=f"Concurrent threads (default: {MAX_WORKERS})",
    )
    p.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip the summary report",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    urls = open_csv(args.csv_file)

    if not urls:
        print("No URLs found in the file.", file=sys.stderr)
        sys.exit(1)

    results: list[str] = []
    start = time.time()

    # ── Concurrent execution ──────────────────────────────────────────────
    #
    # We use plain threads (not asyncio) because requests is a blocking
    # library and the bottleneck is network I/O.  Each thread fetches one
    # URL; we keep at most `workers` threads alive at any time to avoid
    # overwhelming remote servers or our own network stack.
    #
    active: list[threading.Thread] = []

    for url in urls:
        t = threading.Thread(target=worker, args=(url, results), daemon=True)
        t.start()
        active.append(t)

        # Throttle: wait while we are at the concurrency limit
        while sum(1 for th in active if th.is_alive()) >= args.workers:
            time.sleep(0.05)

    # Wait for any remaining threads to finish
    for t in active:
        t.join()

    elapsed = time.time() - start

    if not args.no_summary:
        print_summary(results, len(urls), elapsed)


if __name__ == "__main__":
    main()
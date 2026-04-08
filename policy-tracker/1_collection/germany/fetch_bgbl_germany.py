"""
BGBl Teil I Fetcher (2019–2022)
===============================
Fetches all Gesetze and Verordnungen from Bundesgesetzblatt Teil I
via the OffeneGesetze.de API for the years 2019–2022.

Two-pass approach:
  1. List endpoint  → collects metadata + IDs (no full text available here)
  2. Detail endpoint → fetches full text for each publication individually

Output:  data/raw/germany/bgbl1_2019-2022_{date}.json
  - One JSON array of objects, each with metadata + full_text
  - No CSV delimiter problems, no broken rows

Resume support:
  - Progress is saved to bgbl_progress.json after every batch
  - If interrupted (Ctrl+C), just run again — already-fetched texts are reused
  - Progress file is cleaned up on successful completion

Usage:
    python fetch_bgbl_germany.py                  # fetch everything
    python fetch_bgbl_germany.py --download-pdfs  # also download issue PDFs

Requirements:
    pip install requests
"""

import argparse
import json
import os
import time
import datetime
import requests

# ── Configuration ──────────────────────────────────────────────────
API_BASE = "https://api.offenegesetze.de/v1/veroeffentlichung/"
YEARS = range(2019, 2023)
KIND = "bgbl1"
PAGE_SIZE = 100
REQUEST_DELAY = 0.3
DETAIL_DELAY = 0.3
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_TODAY = datetime.date.today().strftime("%Y%m%d")
OUTPUT_JSON = os.path.join(_PROJECT_ROOT, "data", "raw", "germany", f"bgbl1_2019-2022_{_TODAY}.json")
PROGRESS_FILE = os.path.join(_SCRIPT_DIR, "bgbl_progress.json")
PDF_DIR = "pdfs"


# ── Helpers ────────────────────────────────────────────────────────


def classify_doc_type(title: str) -> str:
    t = title.strip().lower()
    if "gesetz" in t:
        return "Gesetz"
    if "verordnung" in t:
        return "Verordnung"
    if "bekanntmachung" in t:
        return "Bekanntmachung"
    return "Sonstiges"


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(data: dict):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


# ── Pass 1: metadata ──────────────────────────────────────────────


def fetch_metadata() -> list[dict]:
    all_records = []

    for year in YEARS:
        print(f"\n  Year {year}")
        url = f"{API_BASE}?year={year}&kind={KIND}&limit={PAGE_SIZE}"
        page = 0

        while url:
            page += 1
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if page == 1:
                print(f"    {data['count']} publications listed")

            for item in data["results"]:
                all_records.append(
                    {
                        "id": item["id"],
                        "year": item["year"],
                        "issue_number": item["number"],
                        "order_in_issue": item["order"],
                        "title": item["title"],
                        "doc_type": classify_doc_type(item["title"]),
                        "date_published": item["date"],
                        "date_law": item.get("law_date"),
                        "bgbl_page": item["page"],
                        "pdf_page": item["pdf_page"],
                        "num_pages": item["num_pages"],
                        "url_web": item["url"],
                        "url_api": item["api_url"],
                        "url_pdf": item["document_url"],
                        "full_text": None,
                    }
                )

            url = data.get("next")
            if url:
                time.sleep(REQUEST_DELAY)

    return all_records


# ── Pass 2: full texts ───────────────────────────────────────────


def fetch_full_texts(records: list[dict]):
    cache = load_progress()
    total = len(records)
    fetched = 0
    reused = 0

    for i, rec in enumerate(records, 1):
        pid = rec["id"]

        if pid in cache:
            rec["full_text"] = cache[pid]
            reused += 1
            continue

        print(f"    [{i}/{total}] {pid}")
        try:
            resp = requests.get(f"{API_BASE}{pid}/", timeout=30)
            resp.raise_for_status()
            parts = resp.json().get("content", [])
            rec["full_text"] = "\n\n".join(parts)
        except requests.RequestException as e:
            print(f"      ⚠ {e}")
            rec["full_text"] = ""

        cache[pid] = rec["full_text"]
        fetched += 1

        if fetched % 25 == 0:
            save_progress(cache)

        time.sleep(DETAIL_DELAY)

    save_progress(cache)
    print(f"    Fetched {fetched} new, reused {reused} from cache")


# ── PDF download ─────────────────────────────────────────────────


def download_pdfs(records: list[dict]):
    os.makedirs(PDF_DIR, exist_ok=True)
    seen = set()
    queue = []

    for r in records:
        key = (r["year"], r["issue_number"])
        if key not in seen:
            seen.add(key)
            pdf_url = r["url_pdf"].split("#")[0]
            fname = f"bgbl1_{r['year']}_{r['issue_number']:02d}.pdf"
            queue.append((pdf_url, fname))

    print(f"\n  Downloading {len(queue)} issue PDFs …")
    for i, (url, fname) in enumerate(queue, 1):
        path = os.path.join(PDF_DIR, fname)
        if os.path.exists(path):
            continue
        print(f"    [{i}/{len(queue)}] {fname}")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
        except requests.RequestException as e:
            print(f"      ⚠ {e}")
        time.sleep(REQUEST_DELAY)


# ── Main ─────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Fetch BGBl Teil I (2019–2022) → JSON")
    parser.add_argument("--download-pdfs", action="store_true")
    args = parser.parse_args()

    # Pass 1
    print("═" * 50)
    print("Pass 1: Collecting metadata")
    print("═" * 50)
    records = fetch_metadata()
    print(f"\n  Total: {len(records)} publications")

    # Pass 2
    print("\n" + "═" * 50)
    print("Pass 2: Fetching full texts")
    print("  (Progress is saved — safe to interrupt with Ctrl+C)")
    print("═" * 50)
    fetch_full_texts(records)

    # Write JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    size_mb = os.path.getsize(OUTPUT_JSON) / (1024 * 1024)
    print(f"\n✓ Saved {len(records)} records to '{OUTPUT_JSON}' ({size_mb:.1f} MB)")

    # Summary
    from collections import Counter

    by_year = Counter(r["year"] for r in records)
    by_type = Counter(r["doc_type"] for r in records)
    has_text = sum(1 for r in records if r["full_text"])

    print(f"\n{'═' * 50}")
    print("Summary")
    print(f"{'═' * 50}")
    print(f"  Publications with full text: {has_text}/{len(records)}")
    print(f"\n  By year:")
    for y in sorted(by_year):
        print(f"    {y}: {by_year[y]}")
    print(f"\n  By type:")
    for t in sorted(by_type):
        print(f"    {t}: {by_type[t]}")

    # Optional PDFs
    if args.download_pdfs:
        download_pdfs(records)

    # Clean up progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    print(
        f"""
To load in Python:
  import json
  with open("{OUTPUT_JSON}", "r", encoding="utf-8") as f:
      data = json.load(f)

  # Or with pandas:
  import pandas as pd
  df = pd.read_json("{OUTPUT_JSON}")
"""
    )


if __name__ == "__main__":
    main()

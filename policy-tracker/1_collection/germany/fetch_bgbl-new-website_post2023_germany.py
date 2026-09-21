"""
BGBl Teil I fetcher (recht.bund.de, 2023 onward)
================================================
fetches the ZIP packages (Regelungstext + Anlagen as PDF) of publications in
Bundesgesetzblatt Teil I from the official platform https://www.recht.bund.de,
filtered by FNA (Fundstellennachweis A, which declares the "Sachgebiet" a policy belongs to). the offenegesetze.de api only covers
publications until 2022 — use fetch_bgbl_germany.py for those years.

there is no api. publications are addressed via their ELI permalink, which
follows a fixed scheme (see
https://www.recht.bund.de/de/service/webservice/webservice_node.html):
    https://www.recht.bund.de/eli/bund/bgbl-1/{year}/{number}
numbers restart at 1 every year and increase by one per publication.
the FNA number is only shown on the detail page of each publication, so every
detail page has to be requested once to decide whether its ZIP is downloaded.
for a list of FNA/Sachgebiet numbers:
https://www.recht.bund.de/de/informationen/rechtsgebiete/rechtsgebiete_node.html



two-pass approach:
  1. metadata pass → probes every BGBl.-Nr. of a year via its ELI permalink,
                     parses the html detail page (title, type, dates, FNA, ...)
                     and stops after MAX_CONSECUTIVE_MISSES missing numbers
  2. download pass → downloads the ZIP package (?view=zipdownload) of every
                     publication whose FNA matches the filter

output:
  - data/raw/germany/bgbl1_website_zip/bgbl1_{year}_{number}.zip
  - data/raw/germany/bgbl1_website_{start}-{end}_{date}.json
      one json array with metadata of ALL probed publications,
      incl. fna_codes, fna_match and zip_path (None if not downloaded)

resume support:
  - metadata is saved to bgbl_website_progress_{start}-{end}.json every batch
  - if interrupted (Ctrl+C), just run again — cached pages and existing ZIPs
    are reused
  - progress file is cleaned up on successful completion

usage:
run
    python fetch_bgbl-website_germany.py                      # years from configuration
    python fetch_bgbl-website_germany.py --years 2023 2024    # override years


requirements:
    pip install requests beautifulsoup4
"""

import argparse
import datetime
import io
import json
import os
import re
import time
import zipfile
from collections import Counter
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── configuration ──────────────────────────────────────────────────
# years to fetch (inclusive); can be overridden with --years START END
START_YEAR = 2023
END_YEAR = 2023 #datetime.date.today().year

# True → only collect metadata (no ZIP download); 
METADATA_ONLY = True

# FNA ("Sachgebiet") filter — a publication is kept if AT LEAST ONE of its FNA codes matches
# for a list of FNA/Sachgebiete see link above
# prefix match on the full code: "8" keeps 800-..., 860-5, 8253-1-3-38, ...
FNA_PREFIXES = ["8"]
# exact match: "611" keeps 611-1, 611-10-14, ... but NOT 6110-... or 612-...
FNA_EXACT = ["610", "611"]
# what the exact match is compared against:
#   "sachgebiet" → the number before the first "-" (611-1 → 611)
#   "full"       → the complete code (only a bare "611" would match)
FNA_EXACT_SCOPE = "sachgebiet"
# keep publications that list no FNA at all? (mostly Bekanntmachungen)
KEEP_WITHOUT_FNA = False

# probing
ELI_BASE = "https://www.recht.bund.de/eli/bund/bgbl-1"
MAX_CONSECUTIVE_MISSES = 5   # stop a year after this many missing numbers
MAX_NUMBER_PER_YEAR = 2000   # safety cap
LETTER_SUFFIXES = []         # e.g. ["a"] also probes 12a after a hit on 12

# http
REQUEST_DELAY = 0.5          # seconds between detail page requests
DOWNLOAD_DELAY = 1.0         # seconds between ZIP downloads
TIMEOUT = 60
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (research data collection; University of Mannheim)"
SAVE_EVERY = 25              # save progress after this many new pages

# paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_SCRIPT_DIR))
_TODAY = datetime.date.today().strftime("%Y%m%d")
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "data", "raw", "germany")
ZIP_DIR = os.path.join(OUTPUT_DIR, "bgbl1_newwebsite_post2023_zip")


# ── helpers ────────────────────────────────────────────────────────

_LABELS = [
    "Bundesgesetzblatt:",
    "Typ:",
    "BGBl.-Nr.:",
    "Veröffentlichungsdatum:",
    "Ausfertigungsdatum:",
    "Federführung:",
    "FNA:",
    "Sachgebiet:",
]
_FNA_CODE = re.compile(r"(?<![\w-])\d{2,5}(?:-[0-9]+[a-zA-Z]?)*(?![\w-])")


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _field(lines: list[str], label: str, multiline: bool = False) -> str | None:
    """value after a label (same or next line); multiline collects until the next label."""
    for i, line in enumerate(lines):
        if not line.startswith(label):
            continue
        parts = [line[len(label):].strip()]
        for nxt in lines[i + 1:]:
            if parts[0] and not multiline:
                break
            if not multiline and len(parts) > 1:
                break
            if any(nxt.startswith(l) for l in _LABELS):
                break
            if nxt.startswith("http") or nxt.startswith("Download"):
                break
            parts.append(nxt)
        value = " ".join(p for p in parts if p).strip()
        return value or None
    return None


def _iso_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value.strip(), "%d.%m.%Y").date().isoformat()
    except ValueError:
        return value


def _nr_slug(number: str) -> str:
    """'7' → '007', '12a' → '012a' (keeps files sorted)."""
    m = re.match(r"(\d+)(.*)", str(number))
    return f"{int(m.group(1)):03d}{m.group(2)}" if m else str(number)


def extract_fna_codes(fna_raw: str | None) -> list[str]:
    if not fna_raw:
        return []
    return list(dict.fromkeys(_FNA_CODE.findall(fna_raw)))


def fna_matches(codes: list[str]) -> bool:
    if not codes:
        return KEEP_WITHOUT_FNA
    for code in codes:
        if any(code.startswith(p) for p in FNA_PREFIXES):
            return True
        target = code.split("-")[0] if FNA_EXACT_SCOPE == "sachgebiet" else code
        if target in FNA_EXACT:
            return True
    return False


def load_progress(progress_file: str) -> dict:
    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(data: dict, progress_file: str):
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


# ── pass 1: metadata ──────────────────────────────────────────────


def parse_detail_page(html: str, page_url: str, year: int, number: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    lines = [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]

    if _field(lines, "BGBl.-Nr.:") is None:
        return None  # not a publication page

    # title = line directly before "BGBl. 2026 I Nr. 262 vom ..."
    title = None
    for i, line in enumerate(lines):
        if re.match(r"BGBl\. \d{4} I Nr\. ", line) and i > 0:
            title = lines[i - 1]
            break

    zip_link = soup.find("a", href=lambda h: h and "view=zipdownload" in h)
    url_zip = (
        urljoin(page_url, zip_link["href"])
        if zip_link
        else f"{ELI_BASE}/{year}/{number}/?view=zipdownload"
    )
    url_pdfs = sorted(
        {
            urljoin(page_url, a["href"])
            for a in soup.find_all("a", href=True)
            if ".pdf" in a["href"] and "__blob=publicationFile" in a["href"]
            and "viewer.html" not in a["href"]
        }
    )

    fna_raw = _field(lines, "FNA:", multiline=True)
    fna_codes = extract_fna_codes(fna_raw)

    return {
        "id": f"bgbl1_{year}_{number}",
        "year": year,
        "issue_number": str(number),
        "title": title,
        "doc_type": _field(lines, "Typ:"),
        "date_published": _iso_date(_field(lines, "Veröffentlichungsdatum:")),
        "date_law": _iso_date(_field(lines, "Ausfertigungsdatum:")),
        "lead_ministry": _field(lines, "Federführung:"),
        "fna_raw": fna_raw,
        "fna_codes": fna_codes,
        "sachgebiet": _field(lines, "Sachgebiet:"),
        "url_eli": f"{ELI_BASE}/{year}/{number}",
        "url_web": page_url,
        "url_zip": url_zip,
        "url_pdfs": url_pdfs,
        "fna_match": None,
        "zip_path": None,
    }


def fetch_detail(session: requests.Session, year: int, number: str) -> dict | None:
    url = f"{ELI_BASE}/{year}/{number}"
    resp = session.get(url, timeout=TIMEOUT)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return parse_detail_page(resp.text, resp.url, year, number)


def fetch_metadata(session, years: range, progress_file: str) -> tuple[list[dict], list[str]]:
    cache = load_progress(progress_file)
    records, failed = [], []
    new_since_save = 0

    def probe(year: int, number: str) -> dict | None:
        nonlocal new_since_save
        key = f"{year}/{number}"
        if key in cache:
            return cache[key]
        try:
            rec = fetch_detail(session, year, number)
        except requests.RequestException as e:
            print(f"      ⚠ {key}: {e}")
            failed.append(key)
            rec = None
        time.sleep(REQUEST_DELAY)
        if rec:
            cache[key] = rec
            new_since_save += 1
            if new_since_save >= SAVE_EVERY:
                save_progress(cache, progress_file)
                new_since_save = 0
        return rec

    for year in years:
        print(f"\n  Year {year}")
        misses, nr, found = 0, 0, 0

        while misses < MAX_CONSECUTIVE_MISSES and nr < MAX_NUMBER_PER_YEAR:
            nr += 1
            rec = probe(year, str(nr))
            if rec is None:
                misses += 1
                continue
            misses = 0
            records.append(rec)
            found += 1
            print(f"    [{year} Nr. {nr}] {(rec['title'] or '')[:70]}")

            for suffix in LETTER_SUFFIXES:
                rec_s = probe(year, f"{nr}{suffix}")
                if rec_s:
                    records.append(rec_s)
                    found += 1
                    print(f"    [{year} Nr. {nr}{suffix}] {(rec_s['title'] or '')[:70]}")

        print(f"    {found} publications found (last number probed: {nr})")

    save_progress(cache, progress_file)
    return records, failed


# ── pass 2: ZIP download ─────────────────────────────────────────


def download_zips(session, records: list[dict]) -> list[str]:
    os.makedirs(ZIP_DIR, exist_ok=True)
    targets = [r for r in records if r["fna_match"]]
    failed = []
    downloaded = reused = 0

    print(f"\n  Downloading {len(targets)} ZIP packages …")
    for i, rec in enumerate(targets, 1):
        fname = f"bgbl1_{rec['year']}_{_nr_slug(rec['issue_number'])}.zip"
        path = os.path.join(ZIP_DIR, fname)
        rel_path = os.path.relpath(path, _PROJECT_ROOT).replace(os.sep, "/")

        if os.path.exists(path):
            rec["zip_path"] = rel_path
            reused += 1
            continue

        print(f"    [{i}/{len(targets)}] {fname}")
        candidates = [rec["url_zip"], f"{rec['url_eli']}/?view=zipdownload"]
        for url in dict.fromkeys(candidates):
            try:
                resp = session.get(url, timeout=TIMEOUT)
                resp.raise_for_status()
                if not zipfile.is_zipfile(io.BytesIO(resp.content)):
                    raise ValueError("response is not a zip archive")
                with open(path + ".part", "wb") as f:
                    f.write(resp.content)
                os.replace(path + ".part", path)
                rec["zip_path"] = rel_path
                downloaded += 1
                break
            except (requests.RequestException, ValueError) as e:
                print(f"      ⚠ {url}: {e}")
        else:
            failed.append(rec["id"])

        time.sleep(DOWNLOAD_DELAY)

    print(f"    Downloaded {downloaded} new, reused {reused} existing")
    return failed


# ── main ─────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Fetch BGBl Teil I ZIPs (recht.bund.de)")
    parser.add_argument(
        "--years",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        default=[START_YEAR, END_YEAR],
        help=f"year range to fetch, inclusive (default: {START_YEAR} {END_YEAR})",
    )
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()

    start, end = args.years
    if start < 2023:
        print("⚠ recht.bund.de only covers 2023 onward — use fetch_bgbl_germany.py for earlier years")
        start = 2023
    years = range(start, end + 1)
    year_slug = f"{start}-{end}"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_json = os.path.join(OUTPUT_DIR, f"bgbl1_website_{year_slug}_{_TODAY}.json")
    progress_file = os.path.join(_SCRIPT_DIR, f"bgbl_website_progress_{year_slug}.json")
    session = make_session()

    # pass 1
    print("═" * 50)
    print(f"Pass 1: Collecting metadata ({year_slug})")
    print("  (Progress is saved — safe to interrupt with Ctrl+C)")
    print("═" * 50)
    records, failed_pages = fetch_metadata(session, years, progress_file)
    for rec in records:
        rec["fna_match"] = fna_matches(rec["fna_codes"])
    n_match = sum(1 for r in records if r["fna_match"])
    print(f"\n  Total: {len(records)} publications, {n_match} match the FNA filter")

    # pass 2
    failed_zips = []
    if not (args.metadata_only or METADATA_ONLY):
        print("\n" + "═" * 50)
        print("Pass 2: Downloading ZIP packages")
        print("═" * 50)
        failed_zips = download_zips(session, records)

    # write json
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    size_mb = os.path.getsize(output_json) / (1024 * 1024)
    print(f"\n✓ Saved {len(records)} records to '{output_json}' ({size_mb:.1f} MB)")

    # summary
    matched = [r for r in records if r["fna_match"]]
    by_year = Counter(r["year"] for r in records)
    by_year_match = Counter(r["year"] for r in matched)
    by_type = Counter(r["doc_type"] or "unbekannt" for r in records)
    no_fna = sum(1 for r in records if not r["fna_codes"])
    by_sachgebiet = Counter(
        code.split("-")[0] for r in matched for code in r["fna_codes"]
        if fna_matches([code])
    )

    print(f"\n{'═' * 50}")
    print("Summary")
    print(f"{'═' * 50}")
    print(f"  FNA filter: prefixes {FNA_PREFIXES}, exact {FNA_EXACT} ({FNA_EXACT_SCOPE})")
    print(f"  Publications matching filter: {len(matched)}/{len(records)}")
    print(f"  Publications without FNA:     {no_fna}")
    print(f"  ZIPs on disk:                 {sum(1 for r in matched if r['zip_path'])}")
    print(f"\n  By year (matched / all):")
    for y in sorted(by_year):
        print(f"    {y}: {by_year_match[y]} / {by_year[y]}")
    print(f"\n  By type:")
    for t in sorted(by_type):
        print(f"    {t}: {by_type[t]}")
    print(f"\n  Matched FNA Sachgebiete (codes, not publications):")
    for s, c in by_sachgebiet.most_common():
        print(f"    {s}: {c}")

    if failed_pages or failed_zips:
        print(f"\n  ⚠ Failed pages: {failed_pages or '-'}")
        print(f"  ⚠ Failed ZIPs:  {failed_zips or '-'}")
        print("  Run again to retry (progress file kept).")
    elif os.path.exists(progress_file):
        # clean up progress file
        os.remove(progress_file)

    print(
        f"""
To load in Python:
  import json
  with open("{output_json}", "r", encoding="utf-8") as f:
      data = json.load(f)

  # Or with pandas:
  import pandas as pd
  df = pd.read_json("{output_json}")
  df[df["fna_match"]]
"""
    )


if __name__ == "__main__":
    main()
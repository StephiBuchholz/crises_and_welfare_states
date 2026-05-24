#!/usr/bin/env python3
"""
step2_gs_classification.py

Interactive terminal tool for annotating the gold-standard sample.
Labels are saved incrementally — quit and resume possible at any time.

Instructions:

    python step2_gs_classification.py --coder [your initials]

By default the most recent gs_sample file in data/gold_standard/ is used.
To specify a different sample:

    python step2_gs_classification.py --input path/to/sample.json --coder sb

Adding a new classification dimension:
    Append one entry to DIMENSIONS below. Existing labels are never touched;
    only the new dimension will show as unlabelled on the next run.
"""

import argparse
import json
import os
import re
import sys
import textwrap
import webbrowser
from datetime import datetime
from pathlib import Path

# ─── CLASSIFICATION DIMENSIONS ────────────────────────────────────────────────
# To add a new dimension, append a dict here — nothing else needs to change.
#
# Supported types:
#   "date_extract"    — coder extracts a yyyy-mm date from the full text | required, no 'na'
#   "date_extract+na" — identical to date_extract, but "na" is explicitly a valid answer
#   "art_extract"     — coder extracts the number of the article/paragraph (no signs) or 'na'
#   "categorical"     — coder picks from a numbered list of options
#   "categorical+na"  — identical to categorical, but also accepts "na" / "0" for not applicable
#   "boolean"         — coder answers yes (1) or no (0)
#   "string"          — coder enters free text
#

_SPF_OPTIONS = [
    "unemployment",
    "family/children",
    "housing",
    "disability",
    "retirement",
    "survivors",
    "sickness/health/care",
    "labour market",
    "taxes",
]

DIMENSIONS = [
    {
        "key": "summary",
        "display": "Summary",
        "type": "string",
        "hint": (
            "Provide 1-2 sentences in English that pointedly summarize what this policy does.\n"
            "  Focus on who it targets and what it changes."
        ),
    },
    {
        "key": "legally_effective",
        "display": "Legally effective (Inkrafttreten)",
        "type": "date_extract",
        "hint": (
            "Extract the date the law enters into force.\n"
            "  Format: yyyy-mm  |  use BGBl-publication date if not else specified"
        ),
    },
    {
        "key": "leg_eff_terminate",
        "display": "Termination of legal effect (Außerkrafttreten)",
        "type": "date_extract+na",
        "hint": (
            "Extract the date that the effect of the law terminates. 'na' if none.\n"
            "  Format: yyyy-mm or 'na'"
        ),
    },
    {
        "key": "legally_effective_2",
        "display": "2nd legally effective (Inkrafttreten)",
        "type": "date_extract+na",
        "hint": (
            "If the law specifies several dates of entry into force, add the second here. 'na' if not applicable.\n"
            "  Format: yyyy-mm or 'na'"
        ),
    },
    {
        "key": "leg_eff_terminate_2",
        "display": "Termination of 2nd legal effect (Außerkrafttreten)",
        "type": "date_extract+na",
        "hint": (
            "Extract the 2nd date that the effect of the law terminates. 'na' if none.\n"
            "  Format: yyyy-mm or 'na'"
        ),
    },
    {
        "key": "art_leg_eff_2",
        "display": "Article/paragraph 2nd legally effective date refers to",
        "type": "art_extract",
        "hint": (
            "Which article/paragraph does the 2nd legal effect date refer to?\n"
            "  Format: number only (e.g. 4 or 4a), or 'na' when no 2nd date"
        ),
    },
    {
        "key": "legally_effective_3",
        "display": "3rd legally effective (Inkrafttreten)",
        "type": "date_extract+na",
        "hint": (
            "If the law specifies a third date of entry into force, add it here. 'na' if none.\n"
            "  Format: yyyy-mm or 'na'"
        ),
    },
    {
        "key": "leg_eff_terminate_3",
        "display": "Termination of 3rd legal effect (Außerkrafttreten)",
        "type": "date_extract+na",
        "hint": (
            "Extract the 3rd date that the effect of the law terminates. 'na' if none.\n"
            "  Format: yyyy-mm or 'na'"
        ),
    },
    {
        "key": "art_leg_eff_3",
        "display": "Article/paragraph 3rd legally effective date refers to",
        "type": "art_extract",
        "hint": (
            "Which article/paragraph does the 3rd legal effect date refer to? 'na' if none.\n"
            "  Format: number only (e.g. 4 or 4a), or 'na' when no 3rd date"
        ),
    },
    {
        "key": "social_policy_field_1",
        "display": "Social policy field 1",
        "type": "categorical",
        "hint": "Select the primary social policy domain. No 'na'. For definitions, see codebook.",
        "options": _SPF_OPTIONS,
    },
    {
        "key": "social_policy_field_2",
        "display": "Social policy field 2",
        "type": "categorical+na",
        "hint": "Select a second social policy domain if the law substantively addresses one. 'na' if not applicable.",
        "options": _SPF_OPTIONS,
    },
    {
        "key": "spf_justification",
        "display": "SPF justification",
        "type": "string",
        "hint": (
            "Brief justification for your social policy field choice(s).\n"
            "  Argue why you assign a second field if applicable."
        ),
    },
    {
        "key": "crisis_ref",
        "display": "Crisis reference",
        "type": "boolean",
        "hint": (
            "Does the law explicitly reference the crisis that motivated it?\n"
            "  Code 1 if the text explicitly references COVID-19/the pandemic or the\n"
            "2008 financial/economic crisis. Code 0 otherwise."
        ),
    },
    {
        "key": "nsr",
        "display": "New Social Risk (nsr)",
        "type": "categorical+na",
        "hint": (
            "If any, which New Social Risk does the policy target? 'na' if none.\n"
            "\n"
            "  Definition: New social risks are related to the socioeconomic transformations that\n"
            "  have brought post-industrial societies into existence: the tertiarisation of\n"
            "  employment, the decline of the standard full-time male worker and the massive entry\n"
            "  of women into the labour force. (Bonoli 2005)\n"
            "\n"
            "  1. reconciling work and family life\n"
            "     Policy aims to enhance reconciliation of work and family life, e.g. flexibilisation\n"
            "     of working hours, working-from-home, subsidies for mothers providing child care,\n"
            "     or enhancement of child care facility access.\n"
            "\n"
            "  2. single parenthood\n"
            "     Policy targets single parents and their children.\n"
            "\n"
            "  3. having a frail relative\n"
            "     Policy targets individuals providing unpaid, informal care to or households with\n"
            "     an in-house living frail elderly or disabled person.\n"
            "\n"
            "  4. possessing low or obsolete skills\n"
            "     Policy targets individuals employed in low value added service sectors (retail,\n"
            "     cleaning, catering etc.) where there is little scope for productivity increases;\n"
            "     at risk of poverty wage or unemployment due to low or obsolete skills.\n"
            "\n"
            "  5. insufficient social security coverage\n"
            "     Policy targets the risk of insufficient social security coverage due to atypical\n"
            "     career patterns, part-time work, non-standard or informal employment.\n"
            "\n"
            "  0 / na — policy does not target any new social risk."
        ),
        "options": [
            "reconciling work and family life",
            "single parenthood",
            "having a frail relative",
            "possessing low or obsolete skills",
            "insufficient social security coverage",
        ],
    },
    {
        "key": "nsr_justification",
        "display": "NSR justification",
        "type": "string",
        "hint": "Brief justification for your new social risk categorization (one sentence).",
    },
]
# ───────────────────────────────────────────────────────────────────────────────


# ─── PATHS ────────────────────────────────────────────────────────────────────

def _find_root(marker="CLAUDE.md"):
    for p in [Path(__file__).parent, *Path(__file__).parent.parents]:
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"project root not found (no {marker} above {Path(__file__).parent})")

PROJECT_ROOT  = _find_root()
OUTPUT_DIR    = PROJECT_ROOT / "data" / "gold_standard"
OUTPUT_PREFIX = "germany_2008-2015_2019-2022"


def _latest_sample(gold_dir: Path, prefix: str) -> Path | None:
    """Return the most recently dated gs_sample file for the given prefix, or None."""
    candidates = sorted(
        gold_dir.glob(f"{prefix}_gs_sample_*.json"),
        key=lambda p: p.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


DEFAULT_INPUT = _latest_sample(OUTPUT_DIR, OUTPUT_PREFIX)

PAGE_LINES = 50
WRAP_WIDTH = 100
# ───────────────────────────────────────────────────────────────────────────────


# ─── DISPLAY HELPERS ──────────────────────────────────────────────────────────


def term_width() -> int:
    try:
        return min(os.get_terminal_size().columns, 120)
    except OSError:
        return 80


def clear():
    print("\033[2J\033[H", end="", flush=True)


def hr(char="─"):
    print(char * term_width())


def bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def show_header(entry: dict, idx: int, total: int, labelled_ids: set):
    clear()

    hr("═")
    print(bold(f"  GOLD STANDARD  —  Entry {idx + 1}/{total}   [{entry['id']}]"))
    hr("═")
    print(f"  {'Title':<12}: {entry['title']}")
    print(
        f"  {'Type':<12}: {entry['doc_type']}   "
        f"Year: {entry['year']}   "
        f"Score: {entry.get('similarity_score', 0):.3f}"
    )
    pub = entry.get("date_published", "")[:10]
    enac = entry.get("date_law", "")[:10]
    wc = len(entry.get("full_text", "").split())
    print(f"  {'Published':<12}: {pub}   Enacted: {enac}   Words: {wc:,}")
    print(f"  {'URL':<12}: {entry.get('url_web', '')}")

    # per-dimension label summary
    gs = entry.get("gs_labels", {})
    print()
    print("  Labels:")
    for dim in DIMENSIONS:
        k = dim["key"]
        rec = gs.get(k)
        if rec:
            prov = f"  ({rec['coder']}, {rec['date']})"
            print(f"    {k:<30}: {rec['value']}{prov}")
        else:
            print(f"    {k:<30}: —  [not yet labelled]")

    done = len(labelled_ids)
    ratio = done / total if total else 0
    bar = "█" * int(ratio * 20) + "░" * (20 - int(ratio * 20))
    print()
    print(f"  Progress  [{bar}]  {done}/{total} fully labelled")
    hr()


# ─── FULL-TEXT PAGER ──────────────────────────────────────────────────────────


def _wrap_text(text: str) -> list[str]:
    w = min(WRAP_WIDTH, term_width())
    lines: list[str] = []
    for para in text.splitlines():
        stripped = para.strip()
        if stripped:
            lines.extend(textwrap.wrap(stripped, width=w) or [""])
        else:
            lines.append("")
    return lines


def pager(text: str):
    lines = _wrap_text(text)
    total_pgs = max(1, (len(lines) + PAGE_LINES - 1) // PAGE_LINES)
    page = 0
    highlight = None

    while True:
        clear()
        start = page * PAGE_LINES
        chunk = lines[start : start + PAGE_LINES]
        if highlight:
            chunk = [
                ln.replace(highlight, f"\033[43m{highlight}\033[0m") for ln in chunk
            ]
        print("\n".join(chunk))
        hr()
        print(
            f"  Page {page + 1}/{total_pgs}    [n] next  [p] prev  [/term] search  [q] done"
        )
        hr()

        cmd = input("  > ").strip()
        if cmd.lower() in ("q", ""):
            break
        elif cmd.lower() == "n" and page < total_pgs - 1:
            page += 1
        elif cmd.lower() == "p" and page > 0:
            page -= 1
        elif cmd.startswith("/") and len(cmd) > 1:
            term = cmd[1:]
            highlight = term
            for i, ln in enumerate(lines):
                if term.lower() in ln.lower():
                    page = i // PAGE_LINES
                    break
            else:
                print(f"  ('{term}' not found in text)")
                input("  Press Enter...")


# ─── HTML BROWSER VIEW ────────────────────────────────────────────────────────


def open_in_browser(entry: dict):
    url = entry.get("url_pdf", "")
    if not url:
        print("  (no url_pdf for this entry)")
        input("  Press Enter to continue...")
        return
    webbrowser.open(url)
    print(f"  Opened: {url}")
    input("  (press Enter to continue)")


# ─── LABELLING PROMPTS ────────────────────────────────────────────────────────

DATE_RE = re.compile(r"^\d{4}-\d{2}$")


def _valid_ym(s: str) -> bool:
    try:
        _, m = s.split("-")
        return 1 <= int(m) <= 12
    except ValueError:
        return False


def prompt_date_extract(dim: dict, current_rec: dict | None) -> str | None:
    current = current_rec["value"] if current_rec else None
    print()
    print(f"  {dim['display']}")
    print(f"  {dim['hint']}")
    if current:
        print(f"  Current: {current}  — Enter to keep")
    print()
    while True:
        raw = input(f"  {dim['key']} > ").strip()
        if raw == "":
            return current
        if DATE_RE.match(raw) and _valid_ym(raw):
            return raw
        else:
            print(
                "  ✗ Use yyyy-mm format, e.g. 2020-06  (this field is required, no 'na')"
            )


def prompt_date_extract_na(dim: dict, current_rec: dict | None) -> str | None:
    current = current_rec["value"] if current_rec else None
    print()
    print(f"  {dim['display']}")
    print(f"  {dim['hint']}")
    if current:
        print(f"  Current: {current}  — Enter to keep")
    print()
    while True:
        raw = input(f"  {dim['key']} > ").strip()
        if raw == "":
            return current
        if raw.lower() in ("na", "?"):
            return "na"
        if DATE_RE.match(raw) and _valid_ym(raw):
            return raw
        else:
            print("  ✗ Use yyyy-mm format, e.g. 2020-06, or 'na'")


def prompt_categorical(dim: dict, current_rec: dict | None) -> str | None:
    current = current_rec["value"] if current_rec else None
    options = dim["options"]
    print()
    print(f"  {dim['display']}")
    print(f"  {dim['hint']}")
    for i, opt in enumerate(options, 1):
        marker = "  ◀" if current == opt else ""
        print(f"    {i}. {opt}{marker}")
    print("    s. skip / keep current")
    if current:
        print(f"  Current: {current}  — Enter or 's' to keep")
    print()
    while True:
        raw = input(f"  {dim['key']} > ").strip().lower()
        if raw in ("s", ""):
            return current
        if raw.isdigit():
            i = int(raw) - 1
            if 0 <= i < len(options):
                return options[i]
        print(f"  ✗ Enter a number 1–{len(options)}, or 's' to skip.")


def prompt_categorical_na(dim: dict, current_rec: dict | None) -> str | None:
    current = current_rec["value"] if current_rec else None
    options = dim["options"]
    print()
    print(f"  {dim['display']}")
    print(f"  {dim['hint']}")
    print("    0. na (not applicable)")
    for i, opt in enumerate(options, 1):
        marker = "  ◀" if current == opt else ""
        print(f"    {i}. {opt}{marker}")
    print("    s. skip / keep current")
    if current:
        print(f"  Current: {current}  — Enter or 's' to keep")
    print()
    while True:
        raw = input(f"  {dim['key']} > ").strip().lower()
        if raw in ("s", ""):
            return current
        if raw in ("0", "na"):
            return "na"
        if raw.isdigit():
            i = int(raw) - 1
            if 0 <= i < len(options):
                return options[i]
        print(f"  ✗ Enter 0 for na, a number 1–{len(options)}, or 's' to skip.")


def prompt_boolean(dim: dict, current_rec: dict | None) -> int | None:
    current = current_rec["value"] if current_rec else None
    print()
    print(f"  {dim['display']}")
    print(f"  {dim['hint']}")
    if current is not None:
        label = "yes (1)" if current == 1 else "no (0)"
        print(f"  Current: {label}  — Enter to keep")
    print("    y / 1  →  yes (crisis explicitly referenced)")
    print("    n / 0  →  no  (no explicit crisis reference)")
    print("    s      →  skip / keep current")
    print()
    while True:
        raw = input(f"  {dim['key']} > ").strip().lower()
        if raw in ("s", "") and current is not None:
            return current
        if raw in ("y", "1"):
            return 1
        if raw in ("n", "0"):
            return 0
        print("  ✗ Enter y/1 (yes), n/0 (no), or s to skip.")


ART_RE = re.compile(r"^\d+[a-zA-Z]?$")


def prompt_art_extract(dim: dict, current_rec: dict | None) -> str | None:
    current = current_rec["value"] if current_rec else None
    print()
    print(f"  {dim['display']}")
    print(f"  {dim['hint']}")
    if current is not None:
        print(f"  Current: {current}  — Enter to keep")
    print()
    while True:
        raw = input(f"  {dim['key']} > ").strip()
        if raw == "":
            return current
        if raw.lower() in ("na", "?"):
            return "na"
        if ART_RE.match(raw):
            return raw
        print("  ✗ Enter a number (e.g. 3 or 3a), 'na', or Enter to keep current.")


def prompt_string(dim: dict, current_rec: dict | None) -> str | None:
    current = current_rec["value"] if current_rec else None
    print()
    print(f"  {dim['display']}")
    print(f"  {dim['hint']}")
    if current:
        print(f"  Current: {current}")
        print("  Enter to keep, or type a new value.")
    print()
    raw = input(f"  {dim['key']} > ").strip()
    if raw == "":
        return current
    return raw


def prompt_dimension(dim: dict, current_rec: dict | None) -> str | int | None:
    if dim["type"] == "date_extract":
        return prompt_date_extract(dim, current_rec)
    elif dim["type"] == "date_extract+na":
        return prompt_date_extract_na(dim, current_rec)
    elif dim["type"] == "art_extract":
        return prompt_art_extract(dim, current_rec)
    elif dim["type"] == "categorical":
        return prompt_categorical(dim, current_rec)
    elif dim["type"] == "categorical+na":
        return prompt_categorical_na(dim, current_rec)
    elif dim["type"] == "boolean":
        return prompt_boolean(dim, current_rec)
    elif dim["type"] == "string":
        return prompt_string(dim, current_rec)
    else:
        raise ValueError(f"Unknown dimension type: {dim['type']}")


# ─── PERSISTENCE ──────────────────────────────────────────────────────────────


def output_path(input_file: Path, coder_id: str) -> Path:
    return OUTPUT_DIR / f"{input_file.stem}_labelled_{coder_id}.json"


def load_labels(path: Path) -> dict[str, dict]:
    if path.exists():
        records = json.loads(path.read_text(encoding="utf-8"))
        return {r["id"]: r for r in records}
    return {}


def save_labels(labelled_map: dict, entries: list, path: Path):
    output = [labelled_map.get(e["id"], e) for e in entries]
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


def is_fully_labelled(record: dict) -> bool:
    """True when every dimension in DIMENSIONS has a stored value."""
    gs = record.get("gs_labels", {})
    return all(gs.get(dim["key"], {}).get("value") is not None for dim in DIMENSIONS)


# ─── MAIN LOOP ────────────────────────────────────────────────────────────────


def main():
    if os.name == "nt":
        os.system("chcp 65001 >nul 2>&1")
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(
        description="Interactive gold-standard annotation tool"
    )
    parser.add_argument(
        "--coder",
        default="sb",
        help="Your coder ID, stamped on every label you save (default: sb)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=(
            f"Path to the input JSON sample "
            f"(default: most recent gs_sample in data/gold_standard/)"
        ),
    )
    args = parser.parse_args()
    input_file = args.input
    coder_id = args.coder

    if input_file is None:
        sys.exit(
            "Error: no gs_sample file found in data/gold_standard/. "
            "Run step1_gs_randomsample.py first, or pass --input."
        )
    if not input_file.exists():
        sys.exit(f"Error: input file not found: {input_file}")

    out_file = output_path(input_file, coder_id)

    entries = json.loads(input_file.read_text(encoding="utf-8"))
    total = len(entries)
    labelled_map = load_labels(out_file)

    if labelled_map:
        n_done = sum(1 for r in labelled_map.values() if is_fully_labelled(r))
        print(f"Resuming — {n_done}/{total} fully labelled in {out_file.name}")
        input("Press Enter to continue...")

    unlabelled = [
        e for e in entries if not is_fully_labelled(labelled_map.get(e["id"], {}))
    ]
    already_done = [
        e for e in entries if is_fully_labelled(labelled_map.get(e["id"], {}))
    ]
    work_order = unlabelled + already_done
    labelled_ids = {eid for eid, r in labelled_map.items() if is_fully_labelled(r)}

    idx = 0
    while 0 <= idx < total:
        entry = work_order[idx]
        rec = labelled_map.get(entry["id"], entry)

        show_header(rec, idx, total, labelled_ids)
        print()
        print("  [r] read full text (terminal pager)")
        print("  [h] view in browser (HTML)")
        print("  [l] label this entry")
        print("  [s] skip to next  |  [b] back  |  [q] save and quit")
        hr()
        cmd = input("  > ").strip().lower()

        if cmd == "q":
            break
        elif cmd == "b":
            if idx > 0:
                idx -= 1
            continue
        elif cmd == "s":
            idx += 1
            continue
        elif cmd == "r":
            pager(entry.get("full_text", "(no full text)"))
            continue
        elif cmd == "h":
            open_in_browser(entry)
            continue
        elif cmd == "l":
            show_header(rec, idx, total, labelled_ids)
            today = datetime.now().strftime("%Y-%m-%d")

            gs_labels = dict(rec.get("gs_labels", {}))

            for dim in DIMENSIONS:
                value = prompt_dimension(dim, gs_labels.get(dim["key"]))
                if value is not None:
                    existing = gs_labels.get(dim["key"], {})
                    if value != existing.get("value"):
                        gs_labels[dim["key"]] = {
                            "value": value,
                            "coder": coder_id,
                            "date": today,
                        }

            updated = {**entry, "gs_labels": gs_labels}
            labelled_map[entry["id"]] = updated
            if is_fully_labelled(updated):
                labelled_ids.add(entry["id"])

            save_labels(labelled_map, entries, out_file)
            print(f"\n  ✓ Saved.  ({len(labelled_ids)}/{total} fully labelled)")
            input("  Press Enter to continue...")
            idx += 1

    save_labels(labelled_map, entries, out_file)
    print()
    hr("═")
    print(f"  Session complete.  {len(labelled_ids)}/{total} entries fully labelled.")
    print(f"  Output: {out_file}")
    hr("═")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
step1_gs_randomsample.py

Draws a random sample from the final policy set for gold-standard annotation.
Run this once per annotation round; the output is the input for step2_gs_classification.py.

Usage:
    python step1_gs_randomsample.py

Adjust INPUT_FILE, OUTPUT_PREFIX, SAMPLE_FRACTION, and RANDOM_SEED in the
CONFIGURATION section below before running.

Output:
    data/gold_standard/{OUTPUT_PREFIX}_gs_sample_{n}_{date}.json
"""

import json
import random
import datetime
from pathlib import Path

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

def _find_root(marker="CLAUDE.md"):
    for p in [Path(__file__).parent, *Path(__file__).parent.parents]:
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"project root not found (no {marker} above {Path(__file__).parent})")

PROJECT_ROOT = _find_root()

INPUT_FILE      = PROJECT_ROOT / "data/processed/germany/germany_2023-2026_final_policy_set.json"
OUTPUT_DIR      = PROJECT_ROOT / "data/gold_standard"
OUTPUT_PREFIX   = "germany_2023-2026"

SAMPLE_FRACTION = 0.10   # share of the input to draw; adjust as needed
RANDOM_SEED     = 42     # fix for reproducibility; change to draw a different sample

# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

records  = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
n_total  = len(records)
n_sample = round(n_total * SAMPLE_FRACTION)

random.seed(RANDOM_SEED)
sample = random.sample(records, n_sample)

_date    = datetime.date.today().isoformat()
out_file = OUTPUT_DIR / f"{OUTPUT_PREFIX}_gs_sample_{n_sample}_{_date}.json"
out_file.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Input:    {INPUT_FILE.name}  ({n_total} records)")
print(f"Sample:   {n_sample} ({SAMPLE_FRACTION:.0%}), seed={RANDOM_SEED}")
print(f"Output:   {out_file.name}")
print(f"\nNext: run  step2_gs_classification.py --input {out_file.name}  to label this sample.")

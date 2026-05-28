#!/usr/bin/env python3
"""
step1b_gs_subsample_40.py

Draws a random subsample of 40 from the 68-entry gold-standard file and
writes it to the same folder with '68' replaced by '40' in the filename.
All entry fields are preserved exactly as-is.

Usage:
    python step1b_gs_subsample_40.py
"""

import json
import random
from pathlib import Path

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

def _find_root(marker="CLAUDE.md"):
    for p in [Path(__file__).parent, *Path(__file__).parent.parents]:
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"project root not found (no {marker} above {Path(__file__).parent})")

PROJECT_ROOT = _find_root()

INPUT_FILE  = PROJECT_ROOT / "data/gold_standard/germany_2008-2015_2019-2022_gs_sample_68_2026-05-24.json"
SAMPLE_SIZE = 40
RANDOM_SEED = 42

# ─────────────────────────────────────────────────────────────────────────────

records = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

random.seed(RANDOM_SEED)
sample = random.sample(records, SAMPLE_SIZE)

out_file = INPUT_FILE.parent / INPUT_FILE.name.replace("_68_", f"_{SAMPLE_SIZE}_")
out_file.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Input:  {INPUT_FILE.name}  ({len(records)} records)")
print(f"Sample: {SAMPLE_SIZE}, seed={RANDOM_SEED}")
print(f"Output: {out_file.name}")

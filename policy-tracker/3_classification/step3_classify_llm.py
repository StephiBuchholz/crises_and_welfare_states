#!/usr/bin/env python3
"""
step3_classify_llm.py

LLM classification of German BGBl legislative texts.
Extracts date variables, social policy field(s), and crisis reference per entry,
following the codebook in 3_classification/codebook.md.

Prompt variants are defined in step2_promptdesigns.py; set PROMPT_KEY below to switch.

One script per model family: API clients, output-forcing syntax, and SDK imports differ
enough across providers (OpenAI / Anthropic / open-source) that a single script with
branching logic would be harder to read and audit than keeping each provider self-contained.
All scripts share the same PROMPTS and OUTPUT_SCHEMAS from step2_promptdesigns.py.

Output format:
- mirrors the gold-standard structure (llm_labels instead of gs_labels) and contains
  all info of all policy entries from original data collection.
- has additional run-level metadata block on top (date, model, prompt_key, temp, seed,
  input_file, system_fingerprint).

USAGE
-----
    python step3_classify_llm.py                         # default: gold-standard sample
    python step3_classify_llm.py --input path/to/file.json
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from step2_promptdesigns import OUTPUT_SCHEMAS, PROMPTS

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
MODEL = "gpt-4.1-mini"
PROMPT_KEY = "v1_zero_shot_batch_nodef_nojus"  # key into PROMPTS / JSON_SCHEMAS
TEMPERATURE = 0  # 0 = near-deterministic, matches primary run protocol
SEED = 42
# ──────────────────────────────────────────────────────────────────────────────

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "gold_standard" / "germany_cov_sample_20.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "gold_standard"
# ──────────────────────────────────────────────────────────────────────────────


def build_messages(entry: dict, prompt_key: str) -> list[dict]:
    prompt = PROMPTS[prompt_key]
    user_text = prompt["user"].format(
        title=entry.get("title", ""),
        date_published=entry.get("date_published", "")[:10],
        full_text=entry.get("full_text", ""),
    )
    return [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": user_text},
    ]


def classify_entry(entry: dict, client: OpenAI) -> tuple[dict, str | None]:
    response = client.chat.completions.create(
        model=MODEL,
        messages=build_messages(entry, PROMPT_KEY),
        response_format={"type": "json_schema", "json_schema": {
            "name": "policy_classification",
            "schema": OUTPUT_SCHEMAS[PROMPT_KEY],
            "strict": True,
        }},
        temperature=TEMPERATURE,
        seed=SEED,
    )
    return json.loads(response.choices[0].message.content), response.system_fingerprint


def wrap_as_labels(raw: dict, model: str, today: str) -> dict:
    """Convert flat LLM output to the {value, coder, date} provenance format."""
    return {
        key: {"value": val, "coder": model, "date": today} for key, val in raw.items()
    }


def main():
    parser = argparse.ArgumentParser(
        description="LLM classification of BGBl policy texts"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    load_dotenv()
    client = OpenAI(api_key=os.getenv("openai_classification_key"))
    today = date.today().isoformat()

    entries = json.loads(args.input.read_text(encoding="utf-8"))
    stem = args.input.stem
    out_file = OUTPUT_DIR / f"{today}_{stem}_llm_{MODEL}_{PROMPT_KEY}.json"

    fingerprints = set()
    entries_out = []
    for entry in tqdm(entries, desc="classifying"):
        try:
            raw, fingerprint = classify_entry(entry, client)
            llm_labels = wrap_as_labels(raw, MODEL, today)
            entries_out.append({**entry, "llm_labels": llm_labels})
            if fingerprint:
                fingerprints.add(fingerprint)
        except Exception as e:
            print(f"\nerror at {entry['id']}: {e}")
            entries_out.append({**entry, "llm_labels": None})

    output = {
        "run_metadata": {
            "date": today,
            "model": MODEL,
            "prompt_key": PROMPT_KEY,
            "temperature": TEMPERATURE,
            "seed": SEED,
            "input_file": str(args.input.name),
            "system_fingerprints": sorted(fingerprints),
        },
        "entries": entries_out,
    }
    out_file.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nsaved → {out_file}")


if __name__ == "__main__":
    main()

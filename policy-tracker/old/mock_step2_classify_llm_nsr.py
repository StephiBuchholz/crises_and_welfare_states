#!/usr/bin/env python3
"""
step2_classify_llm_nsr.py

THIS IS A MOCK CLASSIFICATION FOR THE PURPOSE OF TESTING THE NSR RESEARCH IDEA

Test classification of the New Social Risks (nsr) variable for German BGBl legislative texts.
Follows the same structure and principles as step2_classify_llm.py.

Output format mirrors step2_classify_llm.py: run-level metadata block + entries with nsr_labels.

USAGE
-----
    python step2_classify_llm_nsr.py                         # default: gold-standard sample
    python step2_classify_llm_nsr.py --input path/to/file.json

PROMPT TESTING
--------------
Define new prompt variants in PROMPTS below, then change PROMPT_KEY.
"""

# pip install openai tqdm python-dotenv

import argparse
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

# ─── MOCK DATASET ─────────────────────────────────────────────────────────────
# Run this block once to create the combined input file.

_ROOT = Path(__file__).resolve().parents[1] / "data" / "processed" / "germany"
_cov = json.loads((_ROOT / "germany_cov_filtered_final.json").read_text(encoding="utf-8"))
_gr  = json.loads((_ROOT / "germany_greatrec_2008-2015_auto_accepted.json").read_text(encoding="utf-8"))
_combined = [{**e, "crisis": "covid_2019-2022"} for e in _cov] + \
            [{**e, "crisis": "great_recession_2008-2015"} for e in _gr]
(_ROOT / "germany_mock_nsr_both_crises.json").write_text(
    json.dumps(_combined, ensure_ascii=False, indent=2), encoding="utf-8"
)
# ──────────────────────────────────────────────────────────────────────────────





# ─── CONFIGURATION ────────────────────────────────────────────────────────────
MODEL = "gpt-4.1-mini"
PROMPT_KEY = "v1_zero_shot"  # key into PROMPTS dict below
TEMPERATURE = 0  # 0 = near-deterministic, matches primary run protocol
SEED = 42
# ──────────────────────────────────────────────────────────────────────────────

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "germany" / "germany_mock_nsr_both_crises.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "germany"
# ──────────────────────────────────────────────────────────────────────────────

# ─── PROMPT VARIANTS ──────────────────────────────────────────────────────────
# Add new variants here. Only PROMPT_KEY needs to change to switch between them.
# Each variant is a dict with "system" and "user" keys.
# The "user" template receives: {title}, {date_published}, {full_text}.

PROMPTS = {
    "v1_zero_shot": {
        "system": (
            "You are an expert in German social policy legislation. "
            "You classify legislative texts (Gesetze, Verordnungen, Bekanntmachungen) from the Bundesgesetzblatt "
            "according to a structured codebook. "
            "Return your classifications as a JSON object with the exact fields specified. "
            "Be precise and extract information verbatim from the text where possible."
        ),
        "user": """\
Classify the legislative text below according to the New Social Risks (nsr) codebook rules.

──── NEW SOCIAL RISKS (nsr) ────
Type: categorical

If any, which New Social Risk does the policy target?

Definition: New social risks are related to the socioeconomic transformations that have brought
post-industrial societies into existence: the tertiarisation of employment, the decline of the
standard full-time male worker and the massive entry of women into the labour force.
(Definition derived from Bonoli (2005): https://doi.org/10.1332/0305573054325765)

Valid values:

  "reconciling work and family life"
      Choose when the policy aims to enhance the reconciliation of work and family life, for
      example due to flexibilisation of working hours, working-from-home, subsidies for mothers
      providing child care or the enhancement of child care facility access.

  "single parenthood"
      Choose when the policy targets single parents and their children.

  "having a frail relative"
      Choose when the policy targets individuals that provide unpaid, informal care to or
      households with an in-house living frail elderly or disabled person.

  "possessing low or obsolete skills"
      Choose when the policy targets individuals who are employed in low value added service
      sectors like retail sales, cleaning, catering or the like where there is little scope for
      productivity increases. The individuals are at risk of being paid a poverty wage or being
      unemployed due to low or obsolete skills.

  "insufficient social security coverage"
      Choose when the policy targets the risk of insufficient social security coverage and welfare
      due to atypical career patterns or atypical employment, part-time work, non-standard or
      informal employment.

  "na"
      Code "na" if the policy does not target any new social risk.

──── NSR JUSTIFICATION (nsr_justification) ────
Give a brief justification for your choice on the new social risk categorization in no more than one sentence.

──── LEGISLATIVE TEXT ────
Title     : {title}
Published : {date_published}

{full_text}""",
    },
}
# ──────────────────────────────────────────────────────────────────────────────

# ─── RESPONSE SCHEMA ──────────────────────────────────────────────────────────

_NSR_OPTIONS = [
    "reconciling work and family life",
    "single parenthood",
    "having a frail relative",
    "possessing low or obsolete skills",
    "insufficient social security coverage",
    "na",
]

JSON_SCHEMA = {
    "name": "nsr_classification",
    "schema": {
        "type": "object",
        "properties": {
            "nsr": {"type": "string", "enum": _NSR_OPTIONS},
            "nsr_justification": {"type": "string"},
        },
        "required": ["nsr", "nsr_justification"],
        "additionalProperties": False,
    },
    "strict": True,
}
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
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
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
        description="LLM classification of NSR variable for BGBl policy texts"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    load_dotenv()
    client = OpenAI(api_key=os.getenv("openai_classification_key"))
    today = date.today().isoformat()

    entries = json.loads(args.input.read_text(encoding="utf-8"))
    stem = args.input.stem
    out_file = OUTPUT_DIR / f"{today}_{stem}_llm_nsr_{MODEL}_{PROMPT_KEY}.json"

    fingerprints = set()
    entries_out = []
    for entry in tqdm(entries, desc="classifying nsr"):
        try:
            raw, fingerprint = classify_entry(entry, client)
            nsr_labels = wrap_as_labels(raw, MODEL, today)
            entries_out.append({**entry, "nsr_labels": nsr_labels})
            if fingerprint:
                fingerprints.add(fingerprint)
        except Exception as e:
            print(f"\nerror at {entry['id']}: {e}")
            entries_out.append({**entry, "nsr_labels": None})

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




#!/usr/bin/env python3
"""
step2_classify_llm.py

LLM classification of German BGBl legislative texts.
Extracts date variables, social policy field(s), and crisis reference per entry,
following the codebook in 3_classification/codebook.md.

Output format:
-  mirrors the gold-standard structure (llm_labels instead of gs_labels) and contains all info of all policy entries from original data colelction.
- but has additional feature: run-level metadata block on top of output file (date, model, prompt_key, temp, seed, inputfile, system_fingerprint)
USAGE
-----
    python step2_classify_llm.py                         # default: gold-standard sample
    python step2_classify_llm.py --input path/to/file.json

PROMPT TESTING
--------------
Define new prompt variants in PROMPTS below, then change PROMPT_KEY.
"""

# pip install openai

# imports

import argparse
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
MODEL = "gpt-4.1-mini"
PROMPT_KEY = "v1_zero_shot"  # key into PROMPTS dict below
TEMPERATURE = 0  # 0 = near-deterministic, matches primary run protocol
SEED = 42
# ──────────────────────────────────────────────────────────────────────────────

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "gold_standard" / "germany_cov_sample_20.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "gold_standard"
# ──────────────────────────────────────────────────────────────────────────────

# ─── PROMPT VARIANTS ──────────────────────────────────────────────────────────
# Add new variants here. Only PROMPT_KEY needs to change to switch between them.
# Each variant is a dict with "system" and "user" keys.
# The "user" template receives: {title}, {date_published}, {full_text}.

PROMPTS = {
    "v1_zero_shot": {
        "system": (
            "You are an expert in German social policy legislation. "  # adapt country here!
            "You classify legislative texts (Gesetze, Verordnungen, Bekanntmachungen) from the Bundesgesetzblatt "  # adapt types and publ. source here
            "according to a structured codebook. "
            "Return your classifications as a JSON object with the exact fields specified. "
            "Be precise and extract information verbatim from the text where possible."
        ),
        "user": """\
Classify the legislative text below according to these codebook rules.

──── DATE EXTRACTION ────
legally_effective   : Date the law enters into force (Inkrafttreten). Use the BGBl publication
                      date if no explicit date is stated. Format: yyyy-mm-dd.
leg_eff_terminate   : Date legal effect terminates (Außerkrafttreten). "na" if not specified.
legally_effective_2 : Second entry-into-force date if the law specifies multiple. "na" if not applicable.
leg_eff_terminate_2 : Termination date for legally_effective_2. "na" if not applicable.
art_leg_eff_2       : Article/paragraph number that legally_effective_2 refers to
                      (first number + optional letter only, e.g. "4a"). "na" if not applicable.
legally_effective_3 : Third entry-into-force date. "na" if not applicable.
leg_eff_terminate_3 : Termination date for legally_effective_3. "na" if not applicable.
art_leg_eff_3       : Article/paragraph number for legally_effective_3. "na" if not applicable.

──── SOCIAL POLICY FIELD ────
Assign 1–4 social policy domains. social_policy_field_1 is mandatory; use "na" for _2–_4 if
not applicable. Valid values:
  "unemploy benefits / job retention / activation"
  "social assistance and housing benefits"
  "family benefits"
  "social-security contributions"
  "in-work / employ-conditional benefits"
  "retirement benefits"
  "sickness benefits"
  "taxes"
  "crisis-induced one-time subsidies"
  "labour regulation"
  "mix"           ← last resort only, for large omnibus laws spanning multiple domains
  "false positive" ← only for _1, when the text is not social policy at all

──── CRISIS REFERENCE ────
crisis_ref : 1 if the text explicitly names COVID-19 / coronavirus / pandemic etc.,
             or the 2008 financial/economic crisis (Finanzkrise / Wirtschaftskrise) etc..
             0 otherwise.

──── LEGISLATIVE TEXT ────
Title     : {title} 
Published : {date_published}

{full_text}""",
    },
}  # this is the prompt section where the actual entry of leg-text dataset is entered into the prompt
# ──────────────────────────────────────────────────────────────────────────────

# ensuring structured model output (response format) (enters api call as separate argument from prompt argument)

# pre-define social_policy_field_* output options to pass into JSON_SCHEMA (below)

_SPF_OPTIONS = [
    "unemploy benefits / job retention / activation",
    "social assistance and housing benefits",
    "family benefits",
    "social-security contributions",
    "in-work / employ-conditional benefits",
    "retirement benefits",
    "sickness benefits",
    "taxes",
    "crisis-induced one-time subsidies",
    "labour regulation",
    "mix",
    "false positive",
]
_SPF_OPTIONS_NO_FP = [o for o in _SPF_OPTIONS if o != "false positive"]

# define response schema

JSON_SCHEMA = {
    "name": "policy_classification",
    "schema": {
        "type": "object",
        "properties": {
            "legally_effective": {"type": "string", "description": "yyyy-mm-dd"},
            "leg_eff_terminate": {"type": "string", "description": "yyyy-mm-dd or na"},
            "legally_effective_2": {
                "type": "string",
                "description": "yyyy-mm-dd or na",
            },
            "leg_eff_terminate_2": {
                "type": "string",
                "description": "yyyy-mm-dd or na",
            },
            "art_leg_eff_2": {"type": "string", "description": "article number or na"},
            "legally_effective_3": {
                "type": "string",
                "description": "yyyy-mm-dd or na",
            },
            "leg_eff_terminate_3": {
                "type": "string",
                "description": "yyyy-mm-dd or na",
            },
            "art_leg_eff_3": {"type": "string", "description": "article number or na"},
            "social_policy_field_1": {"type": "string", "enum": _SPF_OPTIONS},
            "social_policy_field_2": {
                "type": "string",
                "enum": _SPF_OPTIONS_NO_FP + ["na"],
            },
            "social_policy_field_3": {
                "type": "string",
                "enum": _SPF_OPTIONS_NO_FP + ["na"],
            },
            "social_policy_field_4": {
                "type": "string",
                "enum": _SPF_OPTIONS_NO_FP + ["na"],
            },
            "crisis_ref": {"type": "integer", "enum": [0, 1]},
        },
        "required": [
            "legally_effective",
            "leg_eff_terminate",
            "legally_effective_2",
            "leg_eff_terminate_2",
            "art_leg_eff_2",
            "legally_effective_3",
            "leg_eff_terminate_3",
            "art_leg_eff_3",
            "social_policy_field_1",
            "social_policy_field_2",
            "social_policy_field_3",
            "social_policy_field_4",
            "crisis_ref",
        ],
        "additionalProperties": False,
    },
    "strict": True,
}

# define sub-functions to wrap into main function


## define function for message builder (takes one legal document entry and prompt key and returns the messages list openAI API expects)
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


## function that later triggers the actual API call when in main()


def classify_entry(entry: dict, client: OpenAI) -> tuple[dict, str | None]:
    response = client.chat.completions.create(
        model=MODEL,
        messages=build_messages(entry, PROMPT_KEY),
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        temperature=TEMPERATURE,
        seed=SEED,
    )
    return json.loads(response.choices[0].message.content), response.system_fingerprint


## reformat the flat dict from the llm to nested format


def wrap_as_labels(raw: dict, model: str, today: str) -> dict:
    """Convert flat LLM output to the {value, coder, date} provenance format."""
    return {
        key: {"value": val, "coder": model, "date": today} for key, val in raw.items()
    }


## main function: makes the ultimate api call


def main():
    parser = argparse.ArgumentParser(
        description="LLM classification of BGBl policy texts"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    load_dotenv()
    client = OpenAI(
        api_key=os.getenv("openai_classification_key")
    )  # loads api key from .env file
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


if (
    __name__ == "__main__"
):  # the script runs main() when executed directly (python step2_classify_llm.py) but not when imported as a module.
    main()

#!/usr/bin/env python3
"""
step3_classify_llm.py

LLM classification of BGBl legislative texts using prompt variants
defined in step2_promptdesigns.py.

Supports OpenAI models (structured JSON output) and open-source models
served through the KISSKI SAIA API (OpenAI-compatible wrapper).
All models and all prompts run from this single script; one output JSON
is written per (model x prompt_key) combination.

Prompt variants, output schemas, and field definitions are fully defined in
step2_promptdesigns.py — do not hardcode any of those here.

USAGE
-----
    python step3_classify_llm.py                                            # all models x all prompts
    python step3_classify_llm.py --input path/to/file.json                  # default is set as DEFAULT_PATH; also adaptable there
    python step3_classify_llm.py --model gpt-4.1-mini                       # one model, all prompts
    python step3_classify_llm.py --prompt v1_zero_shot_batch_nodef_nojus    # all models, one prompt
    python step3_classify_llm.py --model gpt-4.1-mini --prompt v1_zero_shot_batch_nodef_nojus     # one model, one prompt
    
 Adapt desired output folder under OUTPUT_DIR. 
 output file names follow: {date}_{input_stem}_llm_{model}_{prompt_key}.json




 how functions here works together:

 main()
  └── for each model × prompt → run_prompt()       # loops all entries, writes output file
            └── for each entry → classify_entry()  # one API call, returns parsed result
                      └── build_messages()         # formats the prompt for that entry
 
    """



#________________________________________________________________________________________________


#imports

import argparse
import json
import os
import random
import re
import sys
import time
from collections import deque
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI, RateLimitError
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from step2_promptdesigns import OUTPUT_SCHEMAS, PROMPTS

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
# Prompts to run — applied to every model.
# Default: all variants defined in step2_promptdesigns.py.
# To run a subset, replace with an explicit list of keys, e.g.:
#   PROMPT_KEYS = ["v1_zero_shot_batch_nodef_nojus", "v3_zero_shot_batch_def_nojus"]
PROMPT_KEYS = list(PROMPTS.keys())

# Sampling settings — shared across all models and prompts.
TEMPERATURE = 0      # 0 = near-deterministic; matches primary run protocol
SEED        = 42
TOP_P       = 1.0    # set explicitly so backend changes cannot silently alter sampling

# One entry per model to run. Fields:
#   model        — model name string passed to the API
#   key_env      — env-var name holding the API key, from .env file
#   base_url_env — env-var name holding the base URL; None → use openai.com, from .env-file
#   output_fmt   — "json_schema" : OpenAI structured outputs (strict schema enforcement)
#                  "json_object" : JSON mode (valid JSON, schema not enforced by API)
#                  "text"        : plain text; JSON parsed from response content, last-resort option
#   timeout      — per-request timeout in seconds
#   rpm          — max requests per minute for proactive rate limiting; None → disabled; depends on API
#   rph          — max requests per hour  for proactive rate limiting; None → disabled; depends on API
MODELS = [
    {
        "model":        "gpt-4.1-mini",
        "key_env":      "openai_classification_key",
        "base_url_env": None,
        "output_fmt":   "json_schema",
        "timeout":      60.0,
        "rpm":          None,
        "rph":          None,
    },
    {
        "model":        "llama-3.3-70b-instruct",
        "key_env":      "SAIA_API_KEY",
        "base_url_env": "SAIA_API_ENDPOINT",
        "output_fmt":   "json_object",
        "timeout":      300.0,
        "rpm":          10,
        "rph":          200,
    },
    {
        "model":        "mistral-large-3-675b-instruct-2512",
        "key_env":      "SAIA_API_KEY",
        "base_url_env": "SAIA_API_ENDPOINT",
        "output_fmt":   "json_object",
        "timeout":      300.0,
        "rpm":          10,
        "rph":          200,
    },
    {
        "model":        "qwen3.5-397b-a17b",
        "key_env":      "SAIA_API_KEY",
        "base_url_env": "SAIA_API_ENDPOINT",
        "output_fmt":   "json_object",
        "timeout":      300.0,
        "rpm":          10,
        "rph":          200,
    },
    {
        "model":        "gemma-4-31b-it",
        "key_env":      "SAIA_API_KEY",
        "base_url_env": "SAIA_API_ENDPOINT",
        "output_fmt":   "json_object",
        "timeout":      300.0,
        "rpm":          10,
        "rph":          200,
    },
    {
        "model":        "openai-gpt-oss-120b",
        "key_env":      "SAIA_API_KEY",
        "base_url_env": "SAIA_API_ENDPOINT",
        "output_fmt":   "json_object",
        "timeout":      300.0,
        "rpm":          10,
        "rph":          200,
    },
]

# ─── PATHS ────────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "gold_standard" / "germany_cov_sample_20.json"
OUTPUT_DIR    = PROJECT_ROOT / "data" / "processed" / "germany" 
# ─────────────────────────────────────────────────────────────────────────────


# ─── RATE LIMITER ─────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Proactively enforces per-minute and per-hour API rate limits using a
    sliding-window timestamp deque. Sleeps before dispatching a request if
    either limit would be exceeded. One instance is shared across all prompt
    runs for a given model so the full hourly budget is tracked correctly.
    """

    def __init__(self, max_per_minute: int, max_per_hour: int):
        self.max_per_minute = max_per_minute
        self.max_per_hour   = max_per_hour
        self._timestamps: deque = deque()

    def wait_if_needed(self) -> None:
        """Block until the next request fits within both rate limits."""
        while True:
            now = time.time()
            while self._timestamps and self._timestamps[0] < now - 3600:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_per_hour:
                oldest     = self._timestamps[0]
                wait_s     = (oldest + 3600) - now + 1.0
                reset_time = datetime.fromtimestamp(oldest + 3600).strftime("%H:%M:%S")
                print(
                    f"\nHourly limit ({self.max_per_hour} req/h). "
                    f"Waiting {wait_s / 60:.1f} min (until ~{reset_time})...",
                    flush=True,
                )
                time.sleep(wait_s)
                continue

            recent = sum(1 for t in self._timestamps if t >= now - 60)
            if recent >= self.max_per_minute:
                oldest_recent = min(t for t in self._timestamps if t >= now - 60)
                wait_s        = (oldest_recent + 60) - now + 0.5
                print(
                    f"\nMinute limit ({self.max_per_minute} req/min). "
                    f"Waiting {wait_s:.1f} s...",
                    flush=True,
                )
                time.sleep(wait_s)
                continue

            break

    def record(self) -> None:
        """Record that a request was just dispatched."""
        self._timestamps.append(time.time())


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def build_messages(entry: dict, prompt_key: str) -> list[dict]:
    prompt    = PROMPTS[prompt_key]
    user_text = prompt["user"].format(
        title          = entry.get("title", ""),
        date_published = entry.get("date_published", "")[:10],
        full_text      = entry.get("full_text", ""),
    )
    return [
        {"role": "system", "content": prompt["system"]},
        {"role": "user",   "content": user_text},
    ]

##parsing in case of messy outputs of non-forceble outputs 
def parse_json_response(raw: str) -> dict: #only for SAIA models, bc API does not enforce schema structure
    """
    Robustly extract a JSON object from a raw LLM response.
    Handles clean JSON, intro-prefixed JSON, and ```json``` code blocks.
    """
    cleaned = raw.strip()
    decoder = json.JSONDecoder()

    brace_idx = cleaned.find("{") #in case llm returns a conversational preamble before a json -> strips that
    if brace_idx != -1:
        try:
            obj, _ = decoder.raw_decode(cleaned, brace_idx)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError: #raises error if no json can be retrieved
            pass

    code_block = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n\s*```", cleaned) #in case llm returns json output wrapped in markdown -> strips that
    if code_block:
        try:
            obj = decoder.decode(code_block.group(1).strip())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError: #raises error if no json can be retrieved
            pass

    raise json.JSONDecodeError("No valid JSON object found", cleaned, 0)

## as in goldstandard structure, add info who assigned a label and when to individual field values inside each entry's llm_labels
def wrap_as_labels(raw: dict, model: str, today: str) -> dict:
    """Convert flat LLM output dict to {value, coder, date} provenance format."""
    return {
        key: {"value": val, "coder": model, "date": today}
        for key, val in raw.items()
    }

#core function that makes one API call for one policy entry

    ####builds the kwargs dict (model, messages, temperature, seed, top_p), then adds response_format 
    #####depending on output_fmt — strict schema for OpenAI, JSON mode for SAIA, nothing for plain text.
def classify_entry(
    entry: dict,
    client: OpenAI,
    model_cfg: dict,
    prompt_key: str,
    rate_limiter: "RateLimiter | None",
) -> tuple["dict | None", "str | None", "str | None"]:
    """
    Call the API for one entry.
    Returns (parsed_dict, system_fingerprint, error_msg).
    On success error_msg is None; on failure parsed_dict is None.
    """
    output_fmt = model_cfg["output_fmt"]

    kwargs: dict = {
        "model":       model_cfg["model"],
        "messages":    build_messages(entry, prompt_key),
        "temperature": TEMPERATURE,
        "seed":        SEED,
        "top_p":       TOP_P,
    }
    if output_fmt == "json_schema":
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name":   "policy_classification",
                "schema": OUTPUT_SCHEMAS[prompt_key],
                "strict": True,
            },
        }
    elif output_fmt == "json_object":
        kwargs["response_format"] = {"type": "json_object"}
    # "text" → no response_format key

    MAX_RETRIES = 5
    BASE_DELAY  = 1.0

    for attempt in range(MAX_RETRIES):
        if rate_limiter:
            rate_limiter.wait_if_needed()
        try:
            if rate_limiter:
                rate_limiter.record()
            response = client.chat.completions.create(**kwargs)
            break

        except APITimeoutError:
            return None, None, f"APITimeoutError after {model_cfg['timeout']}s"

        except RateLimitError as e:
            if attempt == MAX_RETRIES - 1:
                return None, None, f"RateLimitError after {MAX_RETRIES} attempts: {e}"
            backoff = BASE_DELAY * (2 ** attempt)
            wait_s  = backoff + backoff * 0.25 * random.random()
            print(
                f"\nRateLimitError (attempt {attempt + 1}/{MAX_RETRIES}), "
                f"retrying in {wait_s:.1f} s...",
                flush=True,
            )
            time.sleep(wait_s)

        except Exception as e:
            return None, None, f"{type(e).__name__}: {e}"

    ####extract response content, system fingerpringt and then parses depending on output format
    content     = response.choices[0].message.content
    fingerprint = getattr(response, "system_fingerprint", None) or None

    try:
        parsed = json.loads(content) if output_fmt == "json_schema" else parse_json_response(content)
        return parsed, fingerprint, None
    except (json.JSONDecodeError, ValueError) as e:
        return None, fingerprint, f"JSON parse error: {e}"


# ─── PER-MODEL / PER-PROMPT RUN ───────────────────────────────────────────────
####function that does one complete pass: loops all entries, collects results, and writes one output JSON.
def run_prompt(
    model_cfg: dict,
    prompt_key: str,
    entries: list[dict],
    input_path: Path,
    client: OpenAI,
    rate_limiter: "RateLimiter | None",
) -> None:
    """Classify all entries for one (model, prompt_key) pair and write one output JSON."""
    model = model_cfg["model"]
    today = date.today().isoformat()

    fingerprints = set()
    entries_out  = []

    for entry in tqdm(entries, desc=prompt_key):
        parsed, fingerprint, err = classify_entry(
            entry, client, model_cfg, prompt_key, rate_limiter
        )
        if fingerprint:
            fingerprints.add(fingerprint)

        if parsed is not None:
            entries_out.append({**entry, "llm_labels": wrap_as_labels(parsed, model, today)})
        else:
            print(f"\nerror [{entry.get('id', '?')}]: {err}")
            entries_out.append({**entry, "llm_labels": None, "llm_error": err})

    safe_model = model.replace("/", "-")
    out_file   = OUTPUT_DIR / f"{today}_{input_path.stem}_llm_{safe_model}_{prompt_key}.json"

    output = { #for reproducibility and transparency: collects run metadata and stores them in the output json on top
        "run_metadata": {
            "date":                today,
            "model":               model,
            "prompt_key":          prompt_key,
            "temperature":         TEMPERATURE,
            "seed":                SEED,
            "top_p":               TOP_P,
            "input_file":          input_path.name,
            "system_fingerprints": sorted(fingerprints) if fingerprints else "na",
        },
        "entries": entries_out,
    }
    out_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved → {out_file}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
#### entry point: parses args, loads input, loops models x prompts, dispatches run_prompt()
def main() -> None:  
    parser = argparse.ArgumentParser(description="LLM classification of policy texts")
    parser.add_argument("--input",  type=Path, default=DEFAULT_INPUT,
                        help="Path to input JSON (default: gold-standard sample)")
    parser.add_argument("--model",  type=str,  default=None,
                        help="Run only this model (must match a model name in MODELS)")
    parser.add_argument("--prompt", type=str,  default=None,
                        help="Run only this prompt key (must match a key in PROMPT_KEYS)")
    args = parser.parse_args()

    load_dotenv()

    # Validate CLI filters early
    active_models  = [m for m in MODELS  if args.model  is None or m["model"] == args.model]
    active_prompts = [p for p in PROMPT_KEYS if args.prompt is None or p == args.prompt]

    if not active_models:
        parser.error(f"--model '{args.model}' not found in MODELS")
    if not active_prompts:
        parser.error(f"--prompt '{args.prompt}' not found in PROMPT_KEYS")

    entries = json.loads(args.input.read_text(encoding="utf-8"))
    print(f"Loaded {len(entries)} entries from {args.input.name}")
    print(f"Models  : {len(active_models)}  ({', '.join(m['model'] for m in active_models)})")
    print(f"Prompts : {len(active_prompts)}")
    print(f"Total runs : {len(active_models) * len(active_prompts)}")

    for model_cfg in active_models:
        model = model_cfg["model"]
        print(f"\n{'=' * 60}\nModel: {model}\n{'=' * 60}")

        api_key      = os.getenv(model_cfg["key_env"])
        base_url     = os.getenv(model_cfg["base_url_env"]) if model_cfg["base_url_env"] else None
        client       = OpenAI(api_key=api_key, base_url=base_url, timeout=model_cfg["timeout"])
        rate_limiter = (
            RateLimiter(model_cfg["rpm"], model_cfg["rph"])
            if model_cfg["rpm"] is not None
            else None
        )

        for i, prompt_key in enumerate(active_prompts, 1):
            print(f"\n  [{i}/{len(active_prompts)}] {prompt_key}")
            run_prompt(model_cfg, prompt_key, entries, args.input, client, rate_limiter)


if __name__ == "__main__":
    main(
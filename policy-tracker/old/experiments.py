""" 
experiments.py

This script provides the code to run the LLM annotation experiments on all (n=798) or a subset of DeLFI papers  with different LLM models, LLM prompt templates and different runs per model (run identifiers).

This script mostly re-uses the code that was used and extensively tested out in the preliminary experiments: 

experiments/preliminary_experiments/api_access/pre_test/pre_test.py

Where necessary, the relevant code parts are adjusted to the full/sub experiment setting.

Usage example 1 (from project root): full experiment:

    Mac/Linux:  caffeinate -i python3 experiments/experiments/experiments.py --model mistral-large-3-675b-instruct-2512 --prompt_template experiments/experiments/prompt_templates/prompt_template_1.md --run run_1 --experiment_name full_experiment
    Windows:    python experiments/experiments/experiments.py --model mistral-large-3-675b-instruct-2512 --prompt_template experiments/experiments/prompt_templates/prompt_template_1.md --run run_1 --experiment_name full_experiment

Usage example 2 (from project root): sub experiment:

    Mac/Linux:  caffeinate -i python3 experiments/experiments/experiments.py --model mistral-large-3-675b-instruct-2512 --prompt_template experiments/experiments/prompt_templates/prompt_template_2.md --run run_1 --experiment_name sub_experiment --year_range 2014-2016
    Windows:  python experiments/experiments/experiments.py --model mistral-large-3-675b-instruct-2512 --prompt_template experiments/experiments/prompt_templates/prompt_template_2.md --run run_1 --experiment_name sub_experiment --year_range 2014-2016
    
"""


# Load libraries
import argparse
from datetime import date, datetime
from dotenv import load_dotenv
import os
import mysql.connector
from mysql.connector import errorcode 
import pandas as pd
from openai import OpenAI, APITimeoutError, RateLimitError
from collections import deque
import json
from tqdm import tqdm
import time
import random
import warnings
import re

# Load environment variables
load_dotenv()


# =============================================================================
# Rate Limiter (KISSKI SAIA API: 10 req/min, 200 req/hour)
# =============================================================================

class RateLimiter:
    """
    Proactively enforces theKISSKI SAIA API basic rate limits (10 req/min, 200 req/hour; 
    see: https://kisski.gwdg.de/en/leistungen/2-02-llm-service/)
    for a user with a free account using a sliding-window timestamp deque. 
    Sleeps before dispatching a request if either limit would be exceeded.
    """

    def __init__(self, max_per_minute: int = 10, max_per_hour: int = 200):
        self.max_per_minute = max_per_minute
        self.max_per_hour   = max_per_hour
        self._timestamps: deque = deque()

    def wait_if_needed(self) -> None:
        """Block until the next request is within both rate limits."""
        while True:
            now = time.time()

            # Drop timestamps older than 1 hour from the sliding window
            while self._timestamps and self._timestamps[0] < now - 3600:
                self._timestamps.popleft()

            # Hourly limit check (most restrictive — evaluate first)
            if len(self._timestamps) >= self.max_per_hour:
                oldest     = self._timestamps[0]
                wait_s     = (oldest + 3600) - now + 1.0   # +1 s safety buffer
                reset_time = datetime.fromtimestamp(oldest + 3600).strftime("%H:%M:%S")
                print(f"\nHourly rate limit reached ({self.max_per_hour} req/hour). "
                      f"Waiting {wait_s / 60:.1f} min (until ~{reset_time})...", flush=True)
                time.sleep(wait_s)
                continue

            # Per-minute limit check
            recent_count = sum(1 for t in self._timestamps if t >= now - 60)
            if recent_count >= self.max_per_minute:
                oldest_in_window = min(t for t in self._timestamps if t >= now - 60)
                wait_s           = (oldest_in_window + 60) - now + 0.5   # +0.5 s safety buffer
                print(f"\nMinute rate limit reached ({self.max_per_minute} req/min). "
                      f"Waiting {wait_s:.1f} s...", flush=True)
                time.sleep(wait_s)
                continue

            break   # both limits satisfied

    def record(self) -> None:
        """Record that a request was just dispatched."""
        self._timestamps.append(time.time())


# =============================================================================
# 0) Parse command-line arguments
# =============================================================================


parser = argparse.ArgumentParser(description="Annotate DeLFI publications (full set or a year-range subset) via KISSKI SAIA API.")
parser.add_argument("--model",           type=str,  required=True,  help="LLM model name (e.g. mistral-large-3-675b-instruct-2512)")
parser.add_argument("--prompt_template", type=str,  required=True,  help="Path to prompt template markdown file (e.g. experiments/experiments/prompt_templates/prompt_template_1.md)")
parser.add_argument("--run",             type=str,  required=True,  help="Run identifier for repeated runs of the same LLM (e.g. run_1, run_2, run_3)")
parser.add_argument("--test",            action="store_true",        help="If set, annotate only the first 5 papers to test the pipeline end-to-end.")
parser.add_argument("--experiment_name", type=str, default="full_experiment", choices=["full_experiment", "sub_experiment"], help="Which experiment this run belongs to (controls filename prefix).")
parser.add_argument("--year_range", type=str, default=None, help="Optional year filter, inclusive, e.g. '2014-2016'. Omit for all years.")

args = parser.parse_args()

model           = args.model
prompt_template = args.prompt_template
run             = args.run
test            = args.test

print(f"Running {args.experiment_name} with experiments.py | model={model} | prompt_template={prompt_template} | run={run} | year_range={args.year_range} | test={test}")


# =============================================================================
# 1) Connection to MySQL Server
# =============================================================================

# Access the credentials
config = {
    "host" : os.getenv("DB_HOST"),
    "port" : int(os.getenv("DB_PORT")),
    "user" : os.getenv("DB_USER"),
    "password" : os.getenv("DB_PASSWORD"), 
    "database": 'delfi_study' 
}

# Create connection to db 
try:
    db_delfi = mysql.connector.connect(**config)
    if db_delfi.is_connected():
        print("Connected to delfi db")

except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Databases do not exist")
    else:
        print(err)
    raise SystemExit(1)



# =============================================================================
# 2) Fetch all papers from MySQL db
# =============================================================================

# Fetch all papers in stable, reproducible order
q = "SELECT * FROM paper ORDER BY id"
warnings.filterwarnings("ignore", category=UserWarning)
df = pd.read_sql(q, con=db_delfi)
# Close delfi db
db_delfi.close()

# Filter delfi papers by provided --year_range argument
if args.year_range:
    start, end = (int(y) for y in args.year_range.split("-"))
    df = df[df["year"].between(start, end)].reset_index(drop=True)
    print(f"--year_range {args.year_range}: filtered to {len(df)} papers.")

if test:
    df = df.head(5)
    print("--test mode: slicing to first 5 papers.")

n = len(df)
print(f"Procedding with {n} papers for annotations.")


# =============================================================================
# 3) LLM Annotation: SAIA API
# =============================================================================

# --- Prompt template helpers ---

def load_prompt_template(path: str) -> tuple[str, str]:
    """
    Parse a prompt template markdown file into (system_prompt_template, user_prompt_template).

    Expected markdown structure:
        #### 1) System prompt
        <system prompt text>

        #### 2) User prompt
        <user prompt text with {row['field']} placeholders>

    Returns:
        system_prompt_template:        Raw system prompt string (no placeholders).
        user_prompt_template: User prompt string with {row['field']} placeholders intact.
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    system_match = re.search(
        r"#### 1\) System prompt\s*\n(.*?)(?=#### 2\))",
        content, re.DOTALL
    )
    user_match = re.search(
        r"#### 2\) User prompt\s*\n(.*?)$",
        content, re.DOTALL
    )

    if not system_match or not user_match:
        raise ValueError(
            f"Could not parse '#### 1) System prompt' and '#### 2) User prompt' "
            f"sections from: {path}"
        )

    return system_match.group(1).strip(), user_match.group(1).strip()


def fill_user_prompt(template: str, row: pd.Series) -> str:
    """
    Substitute {row['field']} placeholders in the user prompt template with
    actual paper values. Only these placeholders are replaced; all other
    curly braces (e.g. in the JSON schema example) are left untouched.

    Args:
        template: User prompt string with {row['field']} placeholders.
        row:      Single paper row from the DeLFI DataFrame.

    Returns:
        Filled user prompt string ready to send to the LLM.
    """
    result = template
    for field in ['title', 'authors', 'year', 'abstract', 'text', 'references']:
        result = result.replace(f"{{row['{field}']}}", str(row[field]))
    return result


# Load and verify prompt template
system_prompt_template, user_prompt_template = load_prompt_template(prompt_template)
prompt_template_name = os.path.splitext(os.path.basename(prompt_template))[0]
print(f"\n--- Loaded prompt template: {prompt_template} ---")
print(f"System prompt template preview (first 750 chars):\n{system_prompt_template[:750]}")
print(f"\nUser prompt template preview (first 750 chars):\n{user_prompt_template[:750]}\n")

# Set API & LLM configs
saia_api_key = os.getenv("SAIA_API_KEY")
base_url = os.getenv("SAIA_API_ENDPOINT")
temperature = 0
seed = 42
top_p = 1.0  #  set top p explicitly for full transparency (even though it is not necessary/has no effect when temperature = 0)
             # so future SAIA backend or per-model default changes cannot silently alter sampling behaviour

# Start OpenAI client
# timeout=300s: covers the slowest legitimate 20-page paper responses (~17s avg,
# up to ~5 min for longest papers) while preventing infinite hangs on the SAIA backend
client = OpenAI(api_key=saia_api_key, base_url=base_url, timeout=300.0)


# Write helper function to parse LLM responses 

def extract_json_from_response(raw: str) -> dict:
    """
    Robustly parse a JSON object from a raw LLM response.

    Handles all observed apertus-70b-instruct-2509 patterns and is robust against trailing text:
      1. Clean JSON starting with {           → works for Mistral and LLama models (JSON prompting works reliably)
      2. Code-fenced JSON (anywhere in text)  → works for observed apertus pattern A
      3. Intro prefix + raw JSON              → works for observed apertus pattern B
         (raw_decode ignores trailing text after the closing })
    """
    cleaned = raw.strip()
    decoder = json.JSONDecoder()

    # Pattern 1 & 3: find the first { and let raw_decode extract exactly
    # the JSON object, stopping at the matching }, ignoring trailing text
    brace_idx = cleaned.find("{")
    if brace_idx != -1:
        try:
            obj, _ = decoder.raw_decode(cleaned, brace_idx)
            return obj  # already a dict, no second json.loads() needed
        except json.JSONDecodeError:
            pass

    # Pattern 2: extract from a ```json...``` or ```...``` code block
    code_block = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n\s*```", cleaned)
    if code_block:
        try:
            return decoder.decode(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("No valid JSON object found", cleaned, 0)


# Write function to classify single paper
def classify_paper(
        client: OpenAI,
        row: pd.Series,
        model: str,
        temperature: float,
        seed: int,
        top_p: float,
        system_prompt_template: str,
        user_prompt_template: str,
        rate_limiter: RateLimiter
) -> dict:

    """
    Classify a single DeLFI publication row via LLM API call according to our theoretical paradigm model about the existence and role of research software
    within the publications, with explicit JSON promting.

    System and user prompts are loaded from the prompt template markdown file
    (see --prompt_template argument) to ensure transparency and reproducibility.

    Rate limiting: rate_limiter.wait_if_needed() is called before every attempt
    (proactive sliding-window enforcement). RateLimitError is caught as a safety
    net and retried with exponential backoff + ±25% jitter (up to MAX_RETRIES attempts).

    Args:
        client: OpenAI client instance (SAIA API)
        row: Single row from the DeLFI publications DataFrame (pd.Series)
        model: LLM model name (e.g., "mistral-large-3-675b-instruct-2512")
        temperature: Temperature setting
        seed: Seed value for LLM sampling
        top_p: Top-p nucleus sampling
        system_prompt_template: System prompt string loaded from prompt template file (no {row['field']} placeholders)
        user_prompt_template: User prompt template string with {row['field']} placeholders
        rate_limiter: RateLimiter instance shared across all classify_paper calls in a run

    Returns:
        dict with LLM annotation fields, or error dict with llm_error / llm_raw_response keys

    """

    # Both prompts loaded from the prompt template file (--prompt_template argument)
    system_prompt = system_prompt_template                  # no {row['field']} placeholders, used as-is
    user_prompt   = fill_user_prompt(user_prompt_template, row)

    MAX_RETRIES = 5
    BASE_DELAY  = 1.0   # seconds; doubles each retry attempt (exponential backoff)
    response    = None

    for attempt in range(MAX_RETRIES):

        # Proactive check: wait before dispatching if either limit would be exceeded
        rate_limiter.wait_if_needed()

        try:
            rate_limiter.record()   # record immediately before dispatching
            response = client.chat.completions.create(
                model       = model,
                temperature = temperature,
                top_p       = top_p,
                seed        = seed,
                messages    = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ]
            )
            break   # success — exit retry loop

        except APITimeoutError:
            print(f"id={row['id']}: request timed out after 300s, skipping")
            return {
                "llm_error": "APITimeoutError: request timed out after 300s",
                "llm_raw_response": None
            }

        except RateLimitError as e:
            if attempt == MAX_RETRIES - 1:
                print(f"id={row['id']}: RateLimitError after {MAX_RETRIES} attempts, skipping")
                return {
                    "llm_error": f"RateLimitError after {MAX_RETRIES} attempts: {str(e)}",
                    "llm_raw_response": None
                }
            # Exponential backoff + ±25% jitter to avoid synchronized retries
            backoff = BASE_DELAY * (2 ** attempt)
            jitter  = backoff * 0.25 * random.random()
            wait_s  = backoff + jitter
            print(f"id={row['id']}: RateLimitError (attempt {attempt + 1}/{MAX_RETRIES}), "
                  f"retrying in {wait_s:.1f} s...", flush=True)
            time.sleep(wait_s)

    raw_content = response.choices[0].message.content

    try:
        result = extract_json_from_response(raw_content)
        if not isinstance(result, dict):
            print(f"id={row['id']}: parsed JSON is {type(result).__name__}, expected dict")
            return {
                "llm_error": f"JSON parsed to {type(result).__name__} instead of dict",
                "llm_raw_response": raw_content
            }
        return result
    except json.JSONDecodeError as e:
        print(f"id={row['id']}: {e}")
        return {
            "llm_error": f"JSON parse error: {str(e)}",
            "llm_raw_response": raw_content
        }


# Write function to classify all papers and return pandas df with labels
def classify_papers(
    client: OpenAI,
    df: pd.DataFrame,
    model: str,
    temperature: float,
    seed: int,
    top_p: float,
    system_prompt_template: str,
    user_prompt_template: str,
    checkpoint_path: str
) -> None:
    """
    Classify all DeLFI publications in df and write results to the checkpoint file.

    Each paper's annotation is appended to checkpoint_path immediately after the API call,
    so progress is preserved even if the script is interrupted mid-run.

    A single RateLimiter instance is shared across all classify_paper calls to enforce
    the KISSKI SAIA API limits (10 req/min, 200 req/hour) across the full run.

    Args:
        client: OpenAI client instance (SAIA API)
        df: pandas DataFrame with DeLFI publications to annotate (already filtered to exclude done papers)
        model: LLM model name (e.g., "mistral-large-3-675b-instruct-2512")
        temperature: Temperature setting
        seed: Seed value for LLM sampling
        top_p: Top-p nucleus sampling value
        system_prompt_template: System prompt string loaded from prompt template file (no {row['field']} placeholders)
        user_prompt_template: User prompt template string with {row['field']} placeholders
        checkpoint_path: Path to the checkpoint CSV file where results are appended after each paper
    """
    rate_limiter = RateLimiter(max_per_minute=10, max_per_hour=200)

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Annotating papers"):
        result = classify_paper(client, row, model, temperature, seed, top_p, system_prompt_template, user_prompt_template, rate_limiter)
        result["id"] = row["id"]

        # Append this paper's result to the checkpoint file immediately
        result_df = pd.DataFrame([result])
        write_header = not os.path.exists(checkpoint_path)
        result_df.to_csv(checkpoint_path, mode="a", header=write_header, index=False)

# =============================================================================
# 4) Run annotation and save output
# =============================================================================

# --- Experiment logging ---

LOG_PATH = f"experiments/experiments/configs/{args.experiment_name}s_configs_log.md"

def log_experiment(
    log_path: str,
    model: str,
    prompt_template_name: str,
    temperature: float,
    seed: int,
    top_p: float,
    run: str,
    datetime_run: str,
    out_filename: str
) -> None:
    """
    Append one experiment run as a new row to the markdown experiment log table.

    Creates the log file with title and table header on first call;
    appends only the data row on subsequent calls.

    Args:
        log_path:             Path to the markdown log file.
        model:                LLM model name (e.g. mistral-large-3-675b-instruct-2512).
        prompt_template_name: Name of the prompt template file without extension.
        temperature:          Temperature setting used for the LLM.
        seed:                 Random seed used for sampling and LLM call.
        top_p:                Top-p nucleus sampling value used for the LLM.
        run:                  Run identifier (e.g. run_1, run_2, run_3).
        datetime_run:         Date and time the run was executed (YYYY-MM-DD HH:MM).
        out_filename:         Output CSV filename for traceability.
    """
    api = "[KISSKI SAIA API](https://docs.hpc.gwdg.de/services/saia/index.html)"
    row = f"| {model} | {prompt_template_name} | {temperature} | {seed} | {top_p} | {run} | {datetime_run} | {api} | {out_filename} |\n"

    if not os.path.exists(log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("# Experiment Log\n\n")
            f.write("| Model | Prompt Template | Temperature | Seed | Top-p | Run | Date & Time | API | Output File |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")
            f.write(row)
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(row)

    print(f"Logged experiment run to {log_path}")

# --- Checkpoint / Resume ---

# The checkpoint file stores annotation results as they are produced, one row per paper.
# If the script is interrupted (e.g. API daily limit hit), re-running the same command
# will read the checkpoint, skip already-annotated papers, and continue from where it stopped.
checkpoint_filename = f"df_{args.experiment_name}_{model}_{prompt_template_name}_{run}_checkpoint.csv"
checkpoint_path     = f"experiments/experiments/results/checkpoints/{checkpoint_filename}"
os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

if os.path.exists(checkpoint_path):
    done_ids = set(pd.read_csv(checkpoint_path)["id"].tolist())
    df_todo  = df[~df["id"].isin(done_ids)].reset_index(drop=True)
    print(f"Checkpoint found: {len(done_ids)} papers already annotated, {len(df_todo)} remaining.")
else:
    df_todo = df
    print(f"No checkpoint found, starting fresh. Annotating {len(df_todo)} papers.")

# Annotate remaining papers, writing each result to the checkpoint file immediately
classify_papers(client, df_todo, model, temperature, seed, top_p, system_prompt_template, user_prompt_template, checkpoint_path)

datetime_run = datetime.now().strftime("%Y-%m-%d %H:%M")
today        = date.today().strftime("%Y-%m-%d")
out_filename = f"df_{args.experiment_name}_{model}_{prompt_template_name}_{run}_{today}.csv"
out_path     = f"experiments/experiments/results/{out_filename}"

# Read all results from checkpoint (covers both today's and any previous partial runs),
# then merge with the full paper df to attach paper metadata (title, authors, year, etc.)
results_df   = pd.read_csv(checkpoint_path)
df_annotated = df.merge(results_df, on="id", how="left")

os.makedirs(os.path.dirname(out_path), exist_ok=True)
df_annotated.drop(columns=['abstract', 'text', 'references']).to_csv(out_path, index=False) #drop columns before saving and pushing to github for legal reasons
print(f"Saved {len(df_annotated)} rows to {out_path}")

log_experiment(LOG_PATH, model, prompt_template_name, temperature, seed, top_p, run, datetime_run, out_filename)
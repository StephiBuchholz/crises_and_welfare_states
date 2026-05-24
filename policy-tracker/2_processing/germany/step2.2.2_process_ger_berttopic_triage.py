"""
interactive triage of BERTopic clusters for social-policy relevance.

iterates topics (id, count, top words) and prompts for a y/n decision.
on completion, extracts documents from accepted topics as System 2 candidates
and writes all output files.

controls:  y = yes   n / Enter = no   b = back   q = quit & save

run after executing step2.2.1_process_ger_berttopic.py, which has 
generated 
- _berttopic_topic_info.json (topic ids, counts, top words)
- _berttopic_topic_assignments.json (which topic each doc was assigned to)

used in this file.


after completing the triage, all policies are either in:

Candidates - in berttopic-triage selected topics [{...}_berttopic_candidates.json]
Noise pool (topic -1) - HDBSCAN couldn't assign these to any cluster; outliers in the embedding space [{...}_berttopic_noise_pool.json]
Other - not in berttopic-triage selected; topic not social policy relevant

"""
#imports 

import gzip
import json
import sys
import datetime
import os
import stat
from pathlib import Path

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

def _find_root(marker="CLAUDE.md"):
    for p in [Path(__file__).parent, *Path(__file__).parent.parents]:
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"project root not found (no {marker} above {Path(__file__).parent})")

PROJECT_ROOT  = _find_root()
OUTPUT_PREFIX = "germany_2008-2015_2019-2022"
DATA_DIR      = PROJECT_ROOT / "data" / "processed" / "germany"

TOPIC_INFO_FILE   = DATA_DIR / f"{OUTPUT_PREFIX}_berttopic_topic_info.json"
TOPIC_ASSIGN_FILE = DATA_DIR / f"{OUTPUT_PREFIX}_berttopic_topic_assignments.json.gz"
CANDIDATES_OUT    = DATA_DIR / f"{OUTPUT_PREFIX}_berttopic_candidates.json"
NOISE_POOL_OUT    = DATA_DIR / f"{OUTPUT_PREFIX}_berttopic_noise_pool.json"
PROGRESS_FILE     = Path(__file__).parent / ".triage_berttopic_progress.json"
LOG_DIR           = DATA_DIR / "runlogs_from_berttopic"

# ──────────────────────────────────────────────────────────────────────────────


def load_json(path):
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def save_progress(decisions):
    PROGRESS_FILE.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {}


def save_outputs(assignments, selected_ids):
    candidates = []
    noise_pool = []
    for entry in assignments:
        t = entry["topic_id"]
        if t in selected_ids:
            candidates.append(entry["doc"])
        elif t == -1:
            noise_pool.append(entry["doc"])

    CANDIDATES_OUT.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    NOISE_POOL_OUT.write_text(
        json.dumps(noise_pool, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nCandidates (selected topics):  {len(candidates)}")
    print(f"Noise pool (topic -1):         {len(noise_pool)}")
    print(f"Other (not selected):          {len(assignments) - len(candidates) - len(noise_pool)}")
    print(f"\nSaved: {CANDIDATES_OUT}")
    print(f"Saved: {NOISE_POOL_OUT}")
    return candidates, noise_pool


def save_run_log(topic_info, selected_ids, n_candidates, n_noise, n_total):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_date = datetime.date.today().isoformat()
    log_path = LOG_DIR / f"berttopic_runlog_{OUTPUT_PREFIX}_{run_date}.md"
    if log_path.exists():
        os.chmod(log_path, stat.S_IWRITE)

    rows = []
    for tid in sorted(selected_ids):
        info = next((x for x in topic_info if x["topic_id"] == tid), {})
        words = ", ".join(info.get("top_words", [])[:8])
        count = info.get("count", "?")
        rows.append(f"| {tid} | {count} | {words} |")

    content = f"""# BERTopic run log

| | |
|---|---|
| date | {run_date} |
| output prefix | `{OUTPUT_PREFIX}` |

## results

| metric | n |
|---|---|
| total documents | {n_total} |
| social-policy topics labelled | {len(selected_ids)} |
| candidates (System 2) | {n_candidates} |
| noise pool | {n_noise} |

## labelled social-policy topics

| topic_id | count | top words |
|---|---|---|
{chr(10).join(rows)}

## output files

- `{CANDIDATES_OUT}`
- `{NOISE_POOL_OUT}`
"""
    log_path.write_text(content, encoding="utf-8")
    os.chmod(log_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    print(f"\nRun log saved (read-only): {log_path}")


def run():
    for f in (TOPIC_INFO_FILE, TOPIC_ASSIGN_FILE):
        if not f.exists():
            print(f"ERROR: {f} not found — run step2.2.1_process_ger_berttopic.py first.")
            sys.exit(1)

    topic_info  = load_json(TOPIC_INFO_FILE)
    assignments = load_json(TOPIC_ASSIGN_FILE)
    decisions   = load_progress()

    real_topics = [t for t in topic_info if t["topic_id"] != -1]
    N = len(real_topics)

    start = next((i for i in range(N) if str(i) not in decisions), N)

    if start < N:
        if start > 0:
            yes_so_far = sum(1 for v in decisions.values() if v == "y")
            print(f"Resuming from topic {start + 1}/{N}  ({yes_so_far} selected so far)")

        i = start
        while i < N:
            t = real_topics[i]
            yes_count = sum(1 for v in decisions.values() if v == "y")
            words = ", ".join(t["top_words"][:8])
            print(f"\n{'─' * 60}")
            print(f"[{i + 1}/{N}]  topic {t['topic_id']:>3}  n={t['count']:>4}  ({yes_count} selected so far)")
            print(f"  {words}")
            print("\n  y = yes   n / Enter = no   b = back   q = quit")

            try:
                choice = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                save_progress(decisions)
                print("\nInterrupted – progress saved.")
                sys.exit(0)

            if choice == "q":
                save_progress(decisions)
                yes_count = sum(1 for v in decisions.values() if v == "y")
                print(f"\nProgress saved. {yes_count} selected so far.")
                sys.exit(0)
            elif choice == "b":
                if i > 0:
                    i -= 1
                continue
            elif choice == "y":
                decisions[str(i)] = "y"
            else:
                decisions[str(i)] = "n"

            save_progress(decisions)
            i += 1

    selected_ids = {
        real_topics[int(k)]["topic_id"]
        for k, v in decisions.items()
        if v == "y"
    }

    print(f"\n{'=' * 60}")
    print(f"Triage complete: {len(selected_ids)} / {N} topics selected as social policy")
    if selected_ids:
        for tid in sorted(selected_ids):
            info = next((t for t in real_topics if t["topic_id"] == tid), {})
            print(f"  topic {tid:>3}  n={info.get('count', '?'):>4}   {', '.join(info.get('top_words', [])[:8])}")

    candidates, noise_pool = save_outputs(assignments, selected_ids)
    save_run_log(topic_info, selected_ids, len(candidates), len(noise_pool), len(assignments))

    print(f"\nNext: run step_pooled_union_compile.py to merge System 1 and System 2 candidates.")


if __name__ == "__main__":
    run()

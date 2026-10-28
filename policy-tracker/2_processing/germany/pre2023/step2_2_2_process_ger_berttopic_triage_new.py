"""
step2_2_2 (new): interactive triage of BERTopic clusters for social-policy relevance.

revised version of step2_2_2_process_ger_berttopic_triage.py (the original is kept
unchanged). run after step2_2_1_process_ger_berttopic_new.py.

changes vs. the original:
  1. each topic is shown with its top words, the titles closest to the topic centre
     (representative titles) and a random sample of further titles from the topic
  2. a third option "mixed" (m): the topic is neither accepted nor rejected as a
     whole; instead each of its documents is reviewed individually in a second phase.
     document-level review stays inside System 2 — nothing is passed on to the
     System 1 (cosine similarity) borderline triage.

phase 1 — topic triage:     y = yes   n / Enter = no   m = mixed   b = back   q = quit & save
phase 2 — document review:  y = yes   n / Enter = no   b = back   q = quit & save
          (only for documents in topics labelled "mixed")

run after executing step2_2_1_process_ger_berttopic_new.py, which has generated
- {OUTPUT_PREFIX}_{RUN_TAG}_topic_info.json (topic ids, counts, top words, representative titles)
- {OUTPUT_PREFIX}_{RUN_TAG}_topic_assignments.json.gz (which topic each doc was assigned to)
- {OUTPUT_PREFIX}_{RUN_TAG}_params.json (parameters of the clustering run; optional)

used in this file.

how to use:
- manually set desired OUTPUT_PREFIX and RUN_TAG, then run in a terminal

after completing the triage, all policies are either in:

Candidates - in topics labelled "yes", or accepted in the document review of "mixed" topics [{...}_candidates.json]
Noise pool (topic -1) - HDBSCAN couldn't assign these to any cluster; outliers in the embedding space [{...}_noise_pool.json]
Other - topic labelled "no", or rejected in the document review of "mixed" topics

document-level decisions for "mixed" topics are also written to {...}_mixed_review.json.
"""
#imports

import gzip
import json
import random
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
OUTPUT_PREFIX = "germany_2016-2018"
RUN_TAG       = "berttopic_v2"   # must match step2_2_1_process_ger_berttopic_new.py
DATA_DIR      = PROJECT_ROOT / "data" / "processed" / "germany" / "pre2023"

N_SHOW_REPRESENTATIVE = 8     # titles closest to the topic centre shown per topic
N_SHOW_RANDOM         = 4     # additional randomly drawn titles shown per topic
RANDOM_SEED           = 42    # fixes the random sample, so it is identical on every resume
TITLE_CHARS           = 150   # display length of titles in phase 1
SNIPPET_CHARS         = 400   # display length of the text excerpt in phase 2

TOPIC_INFO_FILE   = DATA_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_topic_info.json"
TOPIC_ASSIGN_FILE = DATA_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_topic_assignments.json.gz"
PARAMS_FILE       = DATA_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_params.json"
CANDIDATES_OUT    = DATA_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_candidates.json"
NOISE_POOL_OUT    = DATA_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_noise_pool.json"
MIXED_REVIEW_OUT  = DATA_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_mixed_review.json"
PROGRESS_FILE     = Path(__file__).parent / f".triage_{RUN_TAG}_progress_{OUTPUT_PREFIX}.json"
LOG_DIR           = DATA_DIR / "runlogs_from_sys2_berttopic"

# ──────────────────────────────────────────────────────────────────────────────


def load_json(path):
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def save_progress(decisions, doc_decisions, fingerprint):
    PROGRESS_FILE.write_text(
        json.dumps(
            {"topics": fingerprint, "decisions": decisions, "doc_decisions": doc_decisions},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )


def load_progress(fingerprint):
    if not PROGRESS_FILE.exists():
        return {}, {}
    saved = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    if saved.get("topics") != fingerprint:
        print(f"ERROR: {PROGRESS_FILE.name} does not match the current topic set "
              f"(step2_2_1 was re-run or the file is from another corpus).\n"
              f"Delete or rename it to start a fresh triage.")
        sys.exit(1)
    return saved["decisions"], saved.get("doc_decisions", {})


def _short(text, n):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _tag(entry):
    return f"[{entry['doc_class']}] " if entry.get("doc_class", "regular") != "regular" else ""


def show_topic(i, N, t, members, yes_count, mixed_count):
    words = ", ".join(t["top_words"][:8])
    print(f"\n{'─' * 70}")
    print(f"[{i + 1}/{N}]  topic {t['topic_id']:>3}  n={t['count']:>4}  "
          f"({yes_count} yes, {mixed_count} mixed so far)")
    print(f"  words: {words}")

    reps = t.get("representative_titles", [])[:N_SHOW_REPRESENTATIVE]
    if reps:
        print("\n  closest to topic centre:")
        for title in reps:
            print(f"    · {_short(title, TITLE_CHARS)}")

    rest = [e for e in members if e["doc"]["title"] not in set(reps)]
    sample = random.Random(RANDOM_SEED + t["topic_id"]).sample(rest, min(N_SHOW_RANDOM, len(rest)))
    if sample:
        print("\n  random sample:")
        for e in sample:
            print(f"    · {_tag(e)}{_short(e['doc']['title'], TITLE_CHARS)}")

    print("\n  y = yes   n / Enter = no   m = mixed (review documents)   b = back   q = quit")


def show_doc(k, M, entry, n_accepted):
    doc = entry["doc"]
    body = entry.get("embed_text", "")
    print(f"\n{'─' * 70}")
    print(f"[doc {k + 1}/{M}]  topic {entry['topic_id']:>3}  ({n_accepted} accepted so far)")
    print(f"  {_tag(entry)}{doc['title']}")
    print(f"  {doc.get('doc_type', '?')} · {str(doc.get('date_published', ''))[:10]} · {doc.get('url_web', '')}")
    if body:
        print(f"\n  {_short(body, SNIPPET_CHARS)}")
    print("\n  y = yes   n / Enter = no   b = back   q = quit")


def ask(save):
    try:
        return input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        save()
        print("\nInterrupted – progress saved.")
        sys.exit(0)


def save_outputs(assignments, selected_ids, mixed_ids, doc_decisions):
    candidates = []
    noise_pool = []
    mixed_review = []
    for entry in assignments:
        t = entry["topic_id"]
        if t in selected_ids:
            candidates.append(entry["doc"])
        elif t in mixed_ids:
            decision = doc_decisions.get(entry["doc"]["id"], "n")
            mixed_review.append({
                "id": entry["doc"]["id"],
                "title": entry["doc"]["title"],
                "topic_id": t,
                "decision": decision,
            })
            if decision == "y":
                candidates.append(entry["doc"])
        elif t == -1:
            noise_pool.append(entry["doc"])

    CANDIDATES_OUT.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    NOISE_POOL_OUT.write_text(
        json.dumps(noise_pool, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    MIXED_REVIEW_OUT.write_text(
        json.dumps(mixed_review, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    n_mixed_yes = sum(1 for r in mixed_review if r["decision"] == "y")
    print(f"\nCandidates (yes topics + accepted from mixed): {len(candidates)}  "
          f"(of which from mixed: {n_mixed_yes})")
    print(f"Noise pool (topic -1):                         {len(noise_pool)}")
    print(f"Other (not selected):                          {len(assignments) - len(candidates) - len(noise_pool)}")
    print(f"\nSaved: {CANDIDATES_OUT}")
    print(f"Saved: {NOISE_POOL_OUT}")
    print(f"Saved: {MIXED_REVIEW_OUT}")
    return candidates, noise_pool, mixed_review


def save_run_log(topic_info, selected_ids, mixed_ids, mixed_review, n_candidates, n_noise, n_total):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_date = datetime.date.today().isoformat()
    log_path = LOG_DIR / f"{RUN_TAG}_runlog_{OUTPUT_PREFIX}_{run_date}.md"
    if log_path.exists():
        os.chmod(log_path, stat.S_IWRITE)

    def _words(tid):
        info = next((x for x in topic_info if x["topic_id"] == tid), {})
        return info.get("count", "?"), ", ".join(info.get("top_words", [])[:8])

    yes_rows = []
    for tid in sorted(selected_ids):
        count, words = _words(tid)
        yes_rows.append(f"| {tid} | {count} | {words} |")

    mixed_rows = []
    for tid in sorted(mixed_ids):
        count, words = _words(tid)
        accepted = sum(1 for r in mixed_review if r["topic_id"] == tid and r["decision"] == "y")
        mixed_rows.append(f"| {tid} | {count} | {accepted} | {words} |")

    n_mixed_yes = sum(1 for r in mixed_review if r["decision"] == "y")

    params_block = ""
    if PARAMS_FILE.exists():
        params = load_json(PARAMS_FILE)
        params_block = "\n## clustering parameters (step2_2_1_process_ger_berttopic_new.py)\n\n| parameter | value |\n|---|---|\n"
        params_block += "\n".join(f"| {k} | {v} |" for k, v in params.items()) + "\n"

    content = f"""# BERTopic run log ({RUN_TAG})

| | |
|---|---|
| date | {run_date} |
| output prefix | `{OUTPUT_PREFIX}` |
| run tag | `{RUN_TAG}` |

## results

| metric | n |
|---|---|
| total documents | {n_total} |
| social-policy topics labelled (yes) | {len(selected_ids)} |
| topics labelled mixed | {len(mixed_ids)} |
| documents reviewed in mixed topics | {len(mixed_review)} |
| documents accepted from mixed topics | {n_mixed_yes} |
| candidates (System 2) | {n_candidates} |
| noise pool | {n_noise} |

## labelled social-policy topics (yes)

| topic_id | count | top words |
|---|---|---|
{chr(10).join(yes_rows)}

## mixed topics (document-level review)

| topic_id | count | accepted | top words |
|---|---|---|---|
{chr(10).join(mixed_rows)}
{params_block}
## output files

- `{CANDIDATES_OUT}`
- `{NOISE_POOL_OUT}`
- `{MIXED_REVIEW_OUT}`
"""
    log_path.write_text(content, encoding="utf-8")
    os.chmod(log_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    print(f"\nRun log saved (read-only): {log_path}")


def run():
    for f in (TOPIC_INFO_FILE, TOPIC_ASSIGN_FILE):
        if not f.exists():
            print(f"ERROR: {f} not found — run step2_2_1_process_ger_berttopic_new.py first.")
            sys.exit(1)

    topic_info  = load_json(TOPIC_INFO_FILE)
    assignments = load_json(TOPIC_ASSIGN_FILE)

    real_topics = [t for t in topic_info if t["topic_id"] != -1]
    N = len(real_topics)
    fingerprint = [[t["topic_id"], t["count"]] for t in real_topics]
    decisions, doc_decisions = load_progress(fingerprint)

    members_by_topic = {}
    for entry in assignments:
        members_by_topic.setdefault(entry["topic_id"], []).append(entry)

    save = lambda: save_progress(decisions, doc_decisions, fingerprint)

    # ── phase 1: topic triage ──────────────────────────────────────────────────
    start = next((i for i in range(N) if str(i) not in decisions), N)

    if start < N:
        if start > 0:
            yes_so_far = sum(1 for v in decisions.values() if v == "y")
            print(f"Resuming from topic {start + 1}/{N}  ({yes_so_far} selected so far)")

        i = start
        while i < N:
            t = real_topics[i]
            yes_count   = sum(1 for v in decisions.values() if v == "y")
            mixed_count = sum(1 for v in decisions.values() if v == "m")
            show_topic(i, N, t, members_by_topic.get(t["topic_id"], []), yes_count, mixed_count)

            choice = ask(save)
            if choice == "q":
                save()
                yes_count = sum(1 for v in decisions.values() if v == "y")
                print(f"\nProgress saved. {yes_count} selected so far.")
                sys.exit(0)
            elif choice == "b":
                if i > 0:
                    i -= 1
                continue
            elif choice in ("y", "m"):
                decisions[str(i)] = choice
            else:
                decisions[str(i)] = "n"

            save()
            i += 1

    selected_ids = {real_topics[int(k)]["topic_id"] for k, v in decisions.items() if v == "y"}
    mixed_ids    = {real_topics[int(k)]["topic_id"] for k, v in decisions.items() if v == "m"}

    # ── phase 2: document review of mixed topics ───────────────────────────────
    review_docs = [e for tid in sorted(mixed_ids) for e in members_by_topic.get(tid, [])]
    M = len(review_docs)
    k = next((j for j in range(M) if review_docs[j]["doc"]["id"] not in doc_decisions), M)

    if k < M:
        print(f"\n{'=' * 70}")
        print(f"Document review: {M} documents in {len(mixed_ids)} mixed topics"
              + (f"  (resuming at {k + 1})" if k > 0 else ""))
        while k < M:
            entry = review_docs[k]
            n_accepted = sum(
                1 for e in review_docs if doc_decisions.get(e["doc"]["id"]) == "y"
            )
            show_doc(k, M, entry, n_accepted)

            choice = ask(save)
            if choice == "q":
                save()
                print(f"\nProgress saved. {n_accepted} documents accepted so far.")
                sys.exit(0)
            elif choice == "b":
                if k > 0:
                    k -= 1
                continue
            doc_decisions[entry["doc"]["id"]] = "y" if choice == "y" else "n"
            save()
            k += 1

    print(f"\n{'=' * 70}")
    print(f"Triage complete: {len(selected_ids)} / {N} topics selected as social policy, "
          f"{len(mixed_ids)} mixed")
    for label, ids in (("yes", selected_ids), ("mixed", mixed_ids)):
        for tid in sorted(ids):
            info = next((t for t in real_topics if t["topic_id"] == tid), {})
            print(f"  [{label:>5}] topic {tid:>3}  n={info.get('count', '?'):>4}   "
                  f"{', '.join(info.get('top_words', [])[:8])}")

    candidates, noise_pool, mixed_review = save_outputs(assignments, selected_ids, mixed_ids, doc_decisions)
    save_run_log(topic_info, selected_ids, mixed_ids, mixed_review,
                 len(candidates), len(noise_pool), len(assignments))

    print(f"\nNext: run step_pooled_union_compile.py to merge System 1 and System 2 candidates "
          f"(point it to the {RUN_TAG} files).")


if __name__ == "__main__":
    run()

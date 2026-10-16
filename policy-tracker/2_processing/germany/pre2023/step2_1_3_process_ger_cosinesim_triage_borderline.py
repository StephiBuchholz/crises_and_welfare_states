"""
interactive triage of borderline German BGBl entries (for similarity scores below the auto-accept and above the auto-decline threshold).

loads:
  - data/processed/{choose country folder}/{period folder}/{....}_cosinesim_borderline_candidates.json  (written in step2_1_2_process_ger_cosinesim_main.ipynb)
  - data/processed/{choose country folder}/{period folder}/{....}_cosinesim_auto_accepted.json          (written in step2_1_2_process_ger_cosinesim_main.ipynb)

results:
on completion, merges both into:
  - data/processed/{choose country folder}/{period folder}/{country}_{years}_cosinesim_final.json
progress is saved alongside the candidates file:
  - data/processed/{choose country folder}/{period folder}/{....}_cosinesim_borderline_candidates_triage_progress.json

controls:  y = yes   n / Enter = no   b = back   q = quit & save

instruction: run script (triage runs in terminal), final dataset will be stored automatically upon completion

"""

# imports

import hashlib
import json
import sys
from pathlib import Path

#__________________setup [ADAPT YOUR DESIRED FILES AND DESTINATIONS HERE]________________#

def _find_root(marker="CLAUDE.md"):
    for p in [Path(__file__).parent, *Path(__file__).parent.parents]:
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"project root not found (no {marker} above {Path(__file__).parent})")

BASE = _find_root() / "data" / "processed" / "germany" / "pre2023"
CANDIDATES_FILE = BASE / "germany_2016-2018_cosinesim_borderline_candidates.json" #only change country_year
AUTO_ACCEPTED_FILE = BASE / "germany_2016-2018_cosinesim_auto_accepted.json"
FINAL_OUTPUT = BASE / "germany_2016-2018_cosinesim_final.json"
# progress file is tied to the candidates file, so different datasets never share decisions
PROGRESS_FILE = CANDIDATES_FILE.with_name(CANDIDATES_FILE.stem + "_triage_progress.json")

#_________________________________________________________________________________________#

# triage loop


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint(candidates):
    # identifies the candidate list (file, length, order of titles) the decisions refer to
    titles = "\n".join(doc.get("title", "") for doc in candidates)
    return {
        "candidates_file": CANDIDATES_FILE.name,
        "n_candidates": len(candidates),
        "titles_sha256": hashlib.sha256(titles.encode("utf-8")).hexdigest(),
    }


def save_progress(decisions, fp):
    PROGRESS_FILE.write_text(
        json.dumps({"fingerprint": fp, "decisions": decisions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_progress(fp):
    if not PROGRESS_FILE.exists():
        return {}
    progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    if progress.get("fingerprint") != fp:
        sys.exit(
            f"Progress file {PROGRESS_FILE} does not match {CANDIDATES_FILE.name}.\n"
            f"  stored:  {progress.get('fingerprint')}\n"
            f"  current: {fp}\n"
            "Rename or delete the progress file to start a fresh triage."
        )
    return progress["decisions"]


def save_final(auto_accepted, triage_selected):
    combined = auto_accepted + triage_selected
    combined.sort(key=lambda x: x.get("date_published", ""))
    FINAL_OUTPUT.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nFinal dataset saved: {FINAL_OUTPUT}")
    print(f"  Auto-accepted:   {len(auto_accepted)}")
    print(f"  Triage-selected: {len(triage_selected)}")
    print(f"  Total:           {len(combined)}")


def run():
    candidates = load_json(CANDIDATES_FILE)
    auto_accepted = load_json(AUTO_ACCEPTED_FILE)
    fp = fingerprint(candidates)
    decisions = load_progress(fp)
    N = len(candidates)

    start = next((i for i in range(N) if str(i) not in decisions), N)

    if start == N:
        print("All borderline items already decided.")
    else:
        if start > 0:
            yes_so_far = sum(1 for v in decisions.values() if v == "y")
            print(f"Resuming from item {start + 1}/{N}  ({yes_so_far} selected so far)")

        i = start
        while i < N:
            doc = candidates[i]
            yes_count = sum(1 for v in decisions.values() if v == "y")
            print(f"\n{'─'*60}")
            print(
                f"[{i + 1}/{N}]  score={doc['similarity_score']:.3f}  ({yes_count} selected so far)\n"
            )
            print(f"  {doc['title']}")
            print(
                f"  {doc.get('doc_type', '')}  |  {doc.get('date_published', '')[:10]}"
            )
            print("\n  y = yes   n / Enter = no   b = back   q = quit")

            try:
                choice = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                save_progress(decisions, fp)
                print("\nInterrupted – progress saved.")
                sys.exit(0)

            if choice == "q":
                save_progress(decisions, fp)
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

            save_progress(decisions, fp)
            i += 1

    triage_selected = [
        candidates[int(k)]
        for k, v in sorted(decisions.items(), key=lambda x: int(x[0]))
        if v == "y"
    ]

    print(f"\n{'='*60}")
    print(f"Triage complete: {len(triage_selected)} / {N} borderline items selected")
    save_final(auto_accepted, triage_selected)


if __name__ == "__main__":
    run()

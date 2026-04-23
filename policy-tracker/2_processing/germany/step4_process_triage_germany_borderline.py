"""
interactive triage of borderline German BGBl entries (similarity score 0.73–0.835).

loads:
  - data/processed/germany/germany_cov_borderline_candidates.json  (written in step3 notebook)
  - data/processed/germany/germany_cov_auto_accepted.json          (written in step3 notebook)

results:
on completion, merges both into:
  - data/processed/germany/germany_cov_filtered_final.json

controls:  y = yes   n / Enter = no   b = back   q = quit & save

instruction: run script (triage runs in terminal), final dataset will be stored automatically upon completion

"""

# imports

import json
import sys
from pathlib import Path

# setup

BASE = Path(__file__).parent.parent.parent / "data" / "processed" / "germany"
CANDIDATES_FILE = BASE / "germany_cov_borderline_candidates.json"
AUTO_ACCEPTED_FILE = BASE / "germany_cov_auto_accepted.json"
FINAL_OUTPUT = BASE / "germany_cov_filtered_final.json"
PROGRESS_FILE = Path(__file__).parent / ".triage_borderline_progress.json"

# triage loop


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_progress(decisions):
    PROGRESS_FILE.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {}


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
    decisions = load_progress()
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
                save_progress(decisions)
                print("\nInterrupted – progress saved.")
                sys.exit(0)

            if choice == "q":
                save_progress(decisions)
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

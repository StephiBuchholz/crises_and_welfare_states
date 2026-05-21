"""
compile the union of System 1 (cosine similarity) and System 2 (BERTopic) candidate sets
for the pooled evaluation pipeline.

pooled evaluation design note:
    the union (not intersection) is used because the goal is completeness — both systems
    have independent failure modes, and any document missed by one may be caught by the other.
    the union becomes the candidate pool for final human triage.

reads:
    System 1  →  {OUTPUT_PREFIX}_filtered_final.json         (output of step4)
    System 2  →  {OUTPUT_PREFIX}_berttopic_candidates.json   (output of step2.2)
    Noise pool→  {OUTPUT_PREFIX}_berttopic_noise_pool.json   (optional, printed separately)

writes:
    {OUTPUT_PREFIX}_pooled_union.json   — deduplicated union, tagged by source system(s)

each document in the union carries a "system_sources" field:
    "s1_only"  — found only by cosine similarity
    "s2_only"  — found only by BERTopic (likely missed by System 1 due to unusual vocabulary)
    "both"     — found by both systems (high-confidence candidates)

usage: run this script from the terminal after both step3/step4 (System 1) and
step2.2 (System 2) are complete. inspect printed summary, then review the union JSON.
"""

import json
from pathlib import Path

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

BASE          = Path(__file__).parent.parent.parent / "data" / "processed" / "germany"
OUTPUT_PREFIX = "germany_2008-2015_2019-2022"

S1_FILE    = BASE / f"{OUTPUT_PREFIX}_filtered_final.json"
S2_FILE    = BASE / f"{OUTPUT_PREFIX}_berttopic_candidates.json"
NOISE_FILE = BASE / f"{OUTPUT_PREFIX}_berttopic_noise_pool.json"
OUT_FILE   = BASE / f"{OUTPUT_PREFIX}_pooled_union.json"

# ─────────────────────────────────────────────────────────────────────────────


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}\n"
            "Ensure the relevant pipeline step has been completed."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def title_key(doc):
    return doc["title"].strip()


def main():
    s1_docs = load_json(S1_FILE)
    s2_docs = load_json(S2_FILE)

    s1_by_title = {title_key(d): d for d in s1_docs}
    s2_by_title = {title_key(d): d for d in s2_docs}

    all_titles = sorted(set(s1_by_title) | set(s2_by_title))

    union = []
    counts = {"both": 0, "s1_only": 0, "s2_only": 0}

    for title in all_titles:
        in_s1 = title in s1_by_title
        in_s2 = title in s2_by_title

        base   = s1_by_title[title] if in_s1 else s2_by_title[title]
        source = "both" if (in_s1 and in_s2) else ("s1_only" if in_s1 else "s2_only")

        union.append({**base, "system_sources": source})
        counts[source] += 1

    union.sort(key=lambda x: x.get("date_published", ""))

    OUT_FILE.write_text(
        json.dumps(union, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{'='*60}")
    print(f"Pooled union: {len(union)} candidates total")
    print(f"  Both systems (high confidence):      {counts['both']}")
    print(f"  System 1 only (cosine similarity):   {counts['s1_only']}")
    print(f"  System 2 only (BERTopic — new finds):{counts['s2_only']}")
    print(f"{'='*60}")
    print(f"Saved: {OUT_FILE}")

    if counts["s2_only"] > 0:
        print(f"\nDocuments found only by BERTopic (System 2 only) — inspect for missed social policy:")
        s2_only_docs = [d for d in union if d["system_sources"] == "s2_only"]
        for doc in s2_only_docs:
            topic = doc.get("berttopic_topic", "?")
            words = doc.get("berttopic_top_words", [])
            print(f"  [topic {topic}]  {doc['title'][:100]}")
            if words:
                print(f"           top words: {', '.join(words)}")

    if NOISE_FILE.exists():
        noise = load_json(NOISE_FILE)
        print(f"\nBERTopic noise pool: {len(noise)} docs (topic -1, unclassified by BERTopic)")
        print("  → spot-check a sample to verify they are correctly excluded")
        print(f"    {NOISE_FILE}")
    else:
        print(f"\nNoise pool file not found: {NOISE_FILE}")


if __name__ == "__main__":
    main()

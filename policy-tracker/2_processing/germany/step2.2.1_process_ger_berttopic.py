"""
step 2.2: pooled evaluation — system 2: BERTopic clustering

implements System 2 in the pooled evaluation pipeline for filtering social-policy
legislation from a retrieved corpus. System 1 (cosine similarity) is in
step3_process_germany_main.ipynb; the union of both systems is compiled in
step_pooled_union_compile.py.

workflow:
  1. set INPUT_FILE and OUTPUT_PREFIX in the CONFIGURATION section below
  2. run this script — it loads data, computes/loads cached embeddings, fits
     BERTopic, prints the topic table to stdout, and writes the two intermediate
     data files needed by the triage tool; adjust BERTopic parameters and re-run
     until the topic count and top words look right (embeddings are cached so
     only §3 and §4 re-execute on subsequent runs)
  3. run step2.2_triage_berttopic_topics.py in a terminal to label social-policy
     topics interactively; that script handles all downstream output

outputs written by this script (to OUTPUT_DIR):
  runlogs_from_berttopic/berttopic_topics_{OUTPUT_PREFIX}_{date}.html
  {OUTPUT_PREFIX}_berttopic_topic_info.json       ← input for triage tool
  {OUTPUT_PREFIX}_berttopic_topic_assignments.json ← input for triage tool

outputs written by the triage script:
  {OUTPUT_PREFIX}_berttopic_candidates.json <- policies that are in social policy relevant topics
  {OUTPUT_PREFIX}_berttopic_noise_pool.json <- policies that could not be matched to any topic  at all
  runlogs_from_berttopic/berttopic_runlog_{OUTPUT_PREFIX}_{date}.md
"""

# pip installs (run once):
## pip install bertopic umap-learn hdbscan sentence-transformers spacy
## pip install spacy
## python -m spacy download de_core_news_lg

import gzip
import json
import datetime
import numpy as np
import nltk
import spacy
nltk.download("stopwords", quiet=True)
from nltk.corpus import stopwords
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from bertopic import BERTopic
from umap import UMAP
from hdbscan import HDBSCAN
import pandas as pd

# ── CONFIGURATION — set these before running ──────────────────────────────────

def _find_root(marker="CLAUDE.md"):
    for p in [Path(__file__).parent, *Path(__file__).parent.parents]:
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"project root not found (no {marker} above {Path(__file__).parent})")

PROJECT_ROOT = _find_root()

INPUT_FILE    = PROJECT_ROOT / "data/raw/germany/bgbl1_2008-2015_2019-2022_combined.json.gz"
OUTPUT_DIR    = PROJECT_ROOT / "data/processed/germany"
OUTPUT_PREFIX = "germany_2008-2015_2019-2022"   # must match step 3 / step 4 prefix

MODEL_NAME      = "paraphrase-multilingual-mpnet-base-v2"  # same model as System 1
SPACY_MODEL     = "de_core_news_lg"   # German lemmatizer; run: python -m spacy download de_core_news_lg
RANDOM_SEED     = 42
STOPWORDS_LANG  = "german"   # choose any language supported by nltk.corpus.stopwords

# embedding cache — set to None to always recompute
EMBEDDING_CACHE     = OUTPUT_DIR / f".embed_cache_{OUTPUT_PREFIX}.npy"
EMBEDDING_CACHE_IDX = OUTPUT_DIR / f".embed_cache_{OUTPUT_PREFIX}_titles.json"

# BERTopic parameters — adjust and re-run until topic count and top words look right:
# smaller MIN_CLUSTER_SIZE → more, finer-grained topics
# larger  MIN_CLUSTER_SIZE → fewer, broader topics
MIN_CLUSTER_SIZE = 10   # HDBSCAN: minimum docs per cluster
N_NEIGHBORS      = 50   # UMAP: neighbourhood size
N_COMPONENTS     = 2    # UMAP: dimensionality for BERTopic (not for visualisation)

# domain-specific stopwords added on top of the NLTK stopword list
EXTRA_STOPWORDS = [
   "gesetz",
    "gesetze",
    "gesetzes",
    "verordnung",
    "verordnungen",
    "änderung",
    "änderungen",
    "nderung"
    "erste",
    "erster",
    "erstes",
    "zweite",
    "zweiter",
    "zweites",
    "dritte",
    "dritter",
    "drittes",
    "bekanntmachung",
    "durchführung",
    "durchfhrung"
    "durchführungsverordnung",
    "durchfhrngsverordnung",
    "artikel",
    "satz",
    "absatz",
    "nummer",
    "teil",
    "bundesgesetzblatt",
    "jahr",
    "jahres"
]

# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"Project root: {PROJECT_ROOT}")
print(f"Output dir:   {OUTPUT_DIR}")


# ── §1 load data ──────────────────────────────────────────────────────────────

with gzip.open(INPUT_FILE, "rt", encoding="utf-8") as fh:
    raw = json.load(fh)

data   = raw if isinstance(raw, list) else list(raw.values())
titles = [doc["title"] for doc in data]
print(f"\n{len(data):>5} docs  ←  {INPUT_FILE.name}")


# ── §1b lemmatize titles ──────────────────────────────────────────────────────
# lemmatized text is used for c-TF-IDF topic keywords; embeddings (§2) still
# use the original titles so the cached vectors remain valid.

_nlp = spacy.load(SPACY_MODEL, disable=["parser", "ner"])
lemmatized_titles = [
    " ".join(
        t.lemma_.lower()
        for t in doc
        if not t.is_stop and not t.is_punct and not t.is_space
    )
    for doc in _nlp.pipe(titles, batch_size=64)
]
del _nlp   # free ~800 MB before UMAP
print(f"Lemmatization done ({SPACY_MODEL})")


# ── §2 load or compute embeddings ────────────────────────────────────────────
# uses the same model as System 1. if the embedding cache exists and matches
# the current title list it is loaded directly; otherwise embeddings are
# computed and saved for future reuse.

def _compute_and_cache(titles):
    model = SentenceTransformer(MODEL_NAME)
    emb = model.encode(titles, batch_size=16, show_progress_bar=True)
    np.save(EMBEDDING_CACHE, emb)
    EMBEDDING_CACHE_IDX.write_text(
        json.dumps(titles, ensure_ascii=False), encoding="utf-8"
    )
    return emb

if EMBEDDING_CACHE and EMBEDDING_CACHE.exists() and EMBEDDING_CACHE_IDX.exists():
    cached_titles = json.loads(EMBEDDING_CACHE_IDX.read_text(encoding="utf-8"))
    if cached_titles == titles:
        doc_embeddings = np.load(EMBEDDING_CACHE)
        print(f"Loaded cached embeddings: {doc_embeddings.shape}")
    else:
        print("Cache title mismatch — recomputing")
        doc_embeddings = _compute_and_cache(titles)
        print(f"Computed and cached: {doc_embeddings.shape}")
else:
    doc_embeddings = _compute_and_cache(titles)
    print(f"Computed and cached: {doc_embeddings.shape}")


# ── §3 fit BERTopic ───────────────────────────────────────────────────────────
# UMAP reduces embedding dimensions; HDBSCAN clusters them; c-TF-IDF produces
# top words per cluster. adjust MIN_CLUSTER_SIZE in the configuration section
# if the topic count is too high or too low.

umap_model = UMAP(
    n_neighbors=N_NEIGHBORS,
    n_components=N_COMPONENTS,
    min_dist=0.0,
    metric="cosine",
    random_state=RANDOM_SEED,
)
hdbscan_model = HDBSCAN(
    min_cluster_size=MIN_CLUSTER_SIZE,
    min_samples=5,
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
)
_stop_words = stopwords.words(STOPWORDS_LANG) + EXTRA_STOPWORDS
vectorizer = CountVectorizer(ngram_range=(1, 2), min_df=2, stop_words=_stop_words)

topic_model = BERTopic(
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    vectorizer_model=vectorizer,
    calculate_probabilities=False,
    verbose=True,
)

topics, _ = topic_model.fit_transform(lemmatized_titles, embeddings=doc_embeddings)

topic_info = topic_model.get_topic_info()
n_topics   = topic_info.shape[0] - 1   # exclude noise topic
n_noise    = int((np.array(topics) == -1).sum())

print(f"\nTopics found:          {n_topics}")
print(f"Noise docs (topic -1): {n_noise}")

# print topic table for terminal inspection
print()
for _, row in topic_info.sort_values("Topic").iterrows():
    tid   = int(row["Topic"])
    label = "[NOISE]" if tid == -1 else f"topic {tid:>3}"
    words = row["Representation"] if isinstance(row.get("Representation"), list) else []
    print(f"  {label}  n={int(row['Count']):>4}   {', '.join(words[:8])}")


# ── §4 save visualisation and intermediate data ───────────────────────────────

log_dir = OUTPUT_DIR / "runlogs_from_berttopic"
log_dir.mkdir(parents=True, exist_ok=True)

_run_date = datetime.date.today().isoformat()
_viz_path = log_dir / f"berttopic_topics_{OUTPUT_PREFIX}_{_run_date}.html"

topic_model.visualize_topics().write_html(_viz_path)
print(f"\nInteractive topic map saved: {_viz_path}")

_topic_info_path   = OUTPUT_DIR / f"{OUTPUT_PREFIX}_berttopic_topic_info.json"
_topic_assign_path = OUTPUT_DIR / f"{OUTPUT_PREFIX}_berttopic_topic_assignments.json.gz"

_topic_export = [
    {
        "topic_id": int(row["Topic"]),
        "count":    int(row["Count"]),
        "top_words": (row["Representation"] if isinstance(row.get("Representation"), list) else [])[:10],
    }
    for _, row in topic_info.sort_values("Topic").iterrows()
]

_topic_info_path.write_text(
    json.dumps(_topic_export, ensure_ascii=False, indent=2), encoding="utf-8"
)
with gzip.open(_topic_assign_path, "wt", encoding="utf-8") as _fh:
    json.dump(
        [{"topic_id": int(t), "doc": doc} for t, doc in zip(topics, data)],
        _fh,
        ensure_ascii=False,
    )

print(f"Topic info:        {_topic_info_path}")
print(f"Topic assignments: {_topic_assign_path}")
print(f"\nNext: run  step2.2_triage_berttopic_topics.py  to label social-policy topics.")

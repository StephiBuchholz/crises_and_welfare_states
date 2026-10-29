"""
step 2_2_1 (new): pooled evaluation — system 2: BERTopic clustering, revised version

revised version of step2_2_1_process_ger_berttopic.py (the original is kept unchanged).
implements System 2 in the pooled evaluation pipeline for filtering social-policy
legislation from a retrieved corpus. System 1 (cosine similarity) is in
step3_process_germany_main.ipynb; the union of both systems is compiled in
step_pooled_union_compile.py.

changes vs. the original:
  1. BERTopic(language="multilingual") — with the default "english", BERTopic strips
     every non-ASCII character (ä, ö, ü, ß) before computing topic words, which
     produced garbled words such as "prfung" or "zustndigkeit"
  2. embedding input = cleaned title + opening of the legal text:
       - formal boilerplate is removed from titles (ordinals, "Verordnung zur Änderung
         der", dates, § / Absatz references, abbreviations in parentheses)
       - the BGBl page header and the enactment line ("Vom <date>") are stripped from
         the full text; the next EMBED_BODY_CHARS characters are appended
       - corrections ("Berichtigung …") and annexes ("Anlage(band): …") are not
         clustered; they are attached to their parent law in the corpus and inherit
         its topic, or — if no parent is found — assigned via topic_model.transform()
  3. UMAP: N_COMPONENTS 2 → 5 (2 dims merges unrelated regions), N_NEIGHBORS 50 → 20
  4. per-topic representative titles (closest to the topic centroid) are saved for
     the triage tool (step2_2_2_process_ger_berttopic_triage_new.py)
  5. topic words: digit-free token pattern, max_df, larger boilerplate stopword list,
     ClassTfidfTransformer(reduce_frequent_words=True), MaximalMarginalRelevance

workflow:
  1. set INPUT_FILE, OUTPUT_PREFIX and RUN_TAG in the CONFIGURATION section below
  2. run this script — it loads data, builds embedding texts, computes/loads cached
     embeddings, fits BERTopic, prints the topic table to stdout, and writes the
     intermediate data files needed by the triage tool; adjust BERTopic parameters
     and re-run until the topic count and top words look right (embeddings are
     cached, so only §3 onwards re-executes on subsequent runs)
  3. run step2_2_2_process_ger_berttopic_triage_new.py in a terminal to label
     social-policy topics interactively; that script handles all downstream output

outputs written by this script (to OUTPUT_DIR; RUN_TAG keeps them apart from the
original version's files):
  runlogs_from_sys2_berttopic/{RUN_TAG}_topics_{OUTPUT_PREFIX}_{date}.html
  {OUTPUT_PREFIX}_{RUN_TAG}_topic_info.json          ← input for triage tool
  {OUTPUT_PREFIX}_{RUN_TAG}_topic_assignments.json.gz ← input for triage tool
  {OUTPUT_PREFIX}_{RUN_TAG}_params.json              ← parameters of this run (copied into the triage run log)

outputs written by the triage script:
  {OUTPUT_PREFIX}_{RUN_TAG}_candidates.json   <- policies in topics labelled social policy + accepted docs from mixed topics
  {OUTPUT_PREFIX}_{RUN_TAG}_noise_pool.json   <- policies that could not be matched to any topic at all
  {OUTPUT_PREFIX}_{RUN_TAG}_mixed_review.json <- document-level decisions for topics labelled "mixed"
  runlogs_from_sys2_berttopic/{RUN_TAG}_runlog_{OUTPUT_PREFIX}_{date}.md
"""

# pip installs (run once):
## pip install bertopic umap-learn hdbscan sentence-transformers spacy
## pip install spacy
## python -m spacy download de_core_news_lg

import gzip
import json
import re
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
from bertopic.vectorizers import ClassTfidfTransformer
from bertopic.representation import MaximalMarginalRelevance
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

INPUT_FILE    = PROJECT_ROOT / "data/raw/germany/bgbl1_2016-2018_20260918.json"
OUTPUT_DIR    = PROJECT_ROOT / "data/processed/germany/pre2023"
OUTPUT_PREFIX = "germany_2016-2018"   # must match step 3 / step 4 prefix
RUN_TAG       = "berttopic"        # part of every output file name; must match the triage script

MODEL_NAME      = "paraphrase-multilingual-mpnet-base-v2"  # same model as System 1
MAX_SEQ_LENGTH  = 512   # model default is 128 tokens, which would cut title + body after ~500 characters
SPACY_MODEL     = "de_core_news_lg"   # German lemmatizer; run: python -m spacy download de_core_news_lg
RANDOM_SEED     = 42
STOPWORDS_LANG  = "german"   # choose any language supported by nltk.corpus.stopwords
BERTOPIC_LANG   = "multilingual"   # anything but "english" — "english" deletes all non-ASCII characters

# embedding input: cleaned title + this many characters of the legal text after the
# enactment line; set to 0 to embed cleaned titles only
EMBED_BODY_CHARS = 1000

# corrections / annexes: minimum share of the (stemmed) words of the referenced title
# that must appear in a candidate parent title for the correction to be attached to it
PARENT_MATCH_MIN = 0.85

# embedding cache — set to None to always recompute; the cache is keyed on the
# embedding texts, model name and max sequence length
EMBEDDING_CACHE     = OUTPUT_DIR / f".embed_cache_{OUTPUT_PREFIX}_{RUN_TAG}.npy"
EMBEDDING_CACHE_IDX = OUTPUT_DIR / f".embed_cache_{OUTPUT_PREFIX}_{RUN_TAG}_texts.json"

# BERTopic parameters — adjust and re-run until topic count and top words look right:
# smaller MIN_CLUSTER_SIZE → more, finer-grained topics
# larger  MIN_CLUSTER_SIZE → fewer, broader topics
MIN_CLUSTER_SIZE = 10   # HDBSCAN: minimum docs per cluster
MIN_SAMPLES      = 5    # HDBSCAN: density required for a core point (lower → less noise)
N_NEIGHBORS      = 20   # UMAP: neighbourhood size (15–30 for ~1,000 docs)
N_COMPONENTS     = 5    # UMAP: dimensionality for clustering (5–10; 2 is only good for plots)

# topic-word extraction
MAX_DF           = 0.3   # drop words that occur in more than 30 % of topics (see note in §3)
MMR_DIVERSITY    = 0.3   # 0 = plain c-TF-IDF ranking, 1 = maximally diverse topic words
N_REPRESENTATIVE = 10    # titles closest to each topic centroid, shown in the triage tool

# domain-specific stopwords added on top of the NLTK stopword list. topic words are
# computed from spaCy lemmas in lower case, so entries are lower-case lemmas.
# (the ASCII variants "nderung", "durchfhrung" of the original version are no longer
# needed since umlauts are kept)
EXTRA_STOPWORDS = [
    # legal form
    "gesetz", "gesetze", "gesetzes", "verordnung", "verordnungen", "anordnung",
    "bekanntmachung", "rechtsverordnung", "durchführungsverordnung",
    "änderungsgesetz", "änderungsverordnung",
    # amendment vocabulary
    "änderung", "änderungen", "aufhebung", "ergänzung", "neufassung", "neuregelung",
    "berichtigung", "anpassung", "bestimmung", "regelung", "fassung", "durchführung",
    "inkrafttreten", "erlass", "ermächtigung", "vorschrift", "vorschriften",
    "weit", "weiter", "weitere", "ander", "andere", "sonstig", "sonstige",
    # ordinals that survive title cleaning
    "erste", "erster", "erstes", "zweite", "zweiter", "zweites",
    "dritte", "dritter", "drittes",
    # document structure
    "artikel", "satz", "absatz", "nummer", "buchstabe", "teil", "anlage", "anlageband",
    "bundesgesetzblatt", "buch",
    # dates
    "jahr", "jahres", "kalenderjahr", "januar", "februar", "märz", "april", "mai", "juni",
    "juli", "august", "september", "oktober", "november", "dezember",
    # federal state as such
    "bund", "bundes", "bundesministerium", "bundesrepublik", "deutschland", "deutsch",
]

# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"Project root: {PROJECT_ROOT}")
print(f"Output dir:   {OUTPUT_DIR}")


# ── §1 load data ──────────────────────────────────────────────────────────────

_opener = gzip.open if INPUT_FILE.suffix == ".gz" else open
with _opener(INPUT_FILE, "rt", encoding="utf-8") as fh:
    raw = json.load(fh)

data   = raw if isinstance(raw, list) else list(raw.values())
titles = [doc["title"] for doc in data]
print(f"\n{len(data):>5} docs  ←  {INPUT_FILE.name}")


# ── §1a tag corrections and annexes ───────────────────────────────────────────
# corrections ("Berichtigung des …") and annexes ("Anlageband: Die Anlagen zum …")
# carry no policy content of their own. they are left out of clustering and later
# inherit the topic of the law they refer to (§3b).

CORRECTION_RE = re.compile(r"^Berichtigung\s+(?:der|des)\s+(?:Bekanntmachung\s+der\s+)?(.+)$", re.I | re.S)
ANNEX_RE      = re.compile(r"^Anlage(?:band)?\s*\d*\s*:\s*(?:Die\s+)?Anlagen?\s*\d*\s+zu[mr]?\s+(.+)$", re.I | re.S)

doc_class = []   # "regular" | "correction" | "annex"
ref_title = []   # for corrections/annexes: the title of the referenced law
for t in titles:
    if m := CORRECTION_RE.match(t):
        doc_class.append("correction"); ref_title.append(m.group(1))
    elif m := ANNEX_RE.match(t):
        doc_class.append("annex"); ref_title.append(m.group(1))
    else:
        doc_class.append("regular"); ref_title.append(None)

regular_idx = [i for i, c in enumerate(doc_class) if c == "regular"]
attach_idx  = [i for i, c in enumerate(doc_class) if c != "regular"]
print(f"Corrections: {doc_class.count('correction')}   annexes: {doc_class.count('annex')}   "
      f"regular (clustered): {len(regular_idx)}")


# ── §1b clean titles ──────────────────────────────────────────────────────────
# removes formal boilerplate that otherwise dominates title embeddings and makes
# clusters form around legal form ("Verordnung über die Berufsausbildung …",
# "Anordnung zur Übertragung …") instead of policy area.

MONTHS = "Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"

# German ordinal words (Erste, Zweiten, Achtundvierzigste, Zweihundertsiebzehnten …);
# kept when followed by "Buch" so that "Zweiten Buches Sozialgesetzbuch" (SGB II) survives
_NUM_PART  = (r"(?:ein|zwei|drei|vier|fünf|sechs|sech|sieben|sieb|acht|neun|zehn|elf|zwölf|"
              r"zwanzig|dreißig|vierzig|fünfzig|sechzig|siebzig|achtzig|neunzig|hundert|tausend|und)")
ORDINAL_RE = re.compile(rf"\b(?:erst|dritt|siebt|acht|{_NUM_PART}+s?t)(?:e|er|es|en|em)\b(?!\s+Buch)", re.I)

TITLE_BOILERPLATE = [re.compile(p, re.I) for p in [
    r"^(?:Bekanntmachung\s+der\s+)?Neufassung\s+(?:der|des)\s+",
    r"\b(?:Gesetz|Verordnung|Anordnung)\s+zur\s+(?:Änderung|Aufhebung|Ergänzung|Neufassung)"
    r"(?:\s+und\s+(?:Aufhebung|Ergänzung))?\s+(?:der|des|von)\s+",
    r"\b(?:und|sowie)\s+(?:zur\s+)?Änderung\s+(?:weiterer|anderer|sonstiger)\s+(?:\w+\s+)?(?:Vorschriften|Gesetze|Verordnungen)\b",
    r"\bund\s+anderer\s+(?:\w+\s+)?(?:Gesetze|Vorschriften|Verordnungen)\b",
    rf"\b(?:vom|zum|am|bis\s+zum)\s+\d{{1,2}}\.\s*(?:{MONTHS})\s+\d{{4}}",
    r"§§?\s*\d+[a-z]?",
    r"\b(?:Absatz|Abs\.|Satz|Nummer|Nr\.|Artikel|Art\.)\s*\d+[a-z]?",
    r"\b\d+[a-z]?\b\.?",
]]


def _is_abbreviation(token):
    """True for tokens like 'BTHG', '48.', 'AnrV', 'SGB', 'IV-ÄndG', '2018/2019', '–'."""
    parts = [p for p in re.split(r"[-/–.]", token) if p]
    return all(
        p.isdigit()
        or (p[0].isupper() and (len(p) <= 3 or any(c.isupper() or c.isdigit() for c in p[1:])))
        for p in parts
    )


def _strip_abbreviations_in_parens(title):
    # keeps short names such as "(Bundesteilhabegesetz – BTHG)" → "(Bundesteilhabegesetz)"
    def repl(m):
        kept = [tok for tok in m.group(1).split() if not _is_abbreviation(tok)]
        return f"({' '.join(kept)})" if kept else ""
    return re.sub(r"\(([^()]*)\)", repl, title)


def clean_title(title):
    t = re.sub(r"[\u0080-\u009f]", " ", title)   # mis-decoded dashes in the API titles (U+0096)
    for pattern in TITLE_BOILERPLATE:
        t = pattern.sub(" ", t)
    t = _strip_abbreviations_in_parens(t)
    t = ORDINAL_RE.sub("", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    t = re.sub(r"\(\)", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,;:-–")
    return t if t else title


clean_titles = [clean_title(t) for t in titles]


# ── §1c extract body opening ──────────────────────────────────────────────────
# full_text is the text of the BGBl page(s) and may start with the end of the
# previous document. the document's own heading is located first, then everything
# up to the enactment line ("Vom 20. Juni 2016") is skipped.

PAGE_HEADER_RE = re.compile(r"^.*Bundesgesetzblatt\s+Jahrgang\s+\d{4}\s+Teil\s+I\s+Nr\..*$", re.M)
VOM_RE         = re.compile(rf"^\s*Vom\s+\d{{1,2}}\.\s*(?:{MONTHS})\s+\d{{4}}\s*$", re.M)
# "beschlos-" alone: the two-column layout often splits "beschlos-|sen:" across columns
ENACTMENT_RE   = re.compile(r"Der Bundestag hat (?:mit Zustimmung des Bundesrates )?das folgende Gesetz beschlos(?:sen:|-)\s*")


def _alnum_with_index(text):
    chars, index = [], []
    for i, c in enumerate(text):
        if c.isalnum():
            chars.append(c.lower())
            index.append(i)
    return "".join(chars), index


def extract_body(doc, n_chars):
    text = doc.get("full_text") or ""
    if not text or n_chars <= 0:
        return ""
    norm_text, index = _alnum_with_index(text)
    norm_title, _ = _alnum_with_index(doc["title"])
    pos = norm_text.find(norm_title[:40]) if norm_title else -1
    start = index[pos] if pos >= 0 else 0
    m = VOM_RE.search(text, start)
    if m and m.start() - start < 1500:   # enactment line belongs to this heading
        start = m.end()
    body = PAGE_HEADER_RE.sub(" ", text[start:start + 3 * n_chars])
    body = re.sub(r"(\w)-\n\s*([a-zäöüß])", r"\1\2", body)   # undo line-break hyphenation
    body = re.sub(r"\s+", " ", body)
    body = ENACTMENT_RE.sub("", body).strip()
    return body[:n_chars]


embed_texts = []
for doc, ct in zip(data, clean_titles):
    body = extract_body(doc, EMBED_BODY_CHARS)
    embed_texts.append(f"{ct}. {body}" if body else ct)

print(f"Embedding texts built (cleaned title + up to {EMBED_BODY_CHARS} body chars)")
for i in regular_idx[:3]:
    print(f"  e.g. {titles[i][:80]}\n    → {embed_texts[i][:160]} …")


# ── §1d lemmatize cleaned titles ──────────────────────────────────────────────
# lemmatized cleaned titles are used for c-TF-IDF topic keywords; embeddings (§2)
# use embed_texts. the body is not used for keywords — its two-column PDF layout
# makes word order unreliable.

_nlp = spacy.load(SPACY_MODEL, disable=["parser", "ner"])
lemmatized_titles = [
    " ".join(
        t.lemma_.lower()
        for t in doc
        if not t.is_stop and not t.is_punct and not t.is_space
    )
    for doc in _nlp.pipe(clean_titles, batch_size=64)
]
del _nlp   # free ~800 MB before UMAP
print(f"Lemmatization done ({SPACY_MODEL})")


# ── §2 load or compute embeddings ────────────────────────────────────────────
# uses the same model as System 1. the embedding model is always loaded because
# MaximalMarginalRelevance (§3) needs it to embed candidate topic words.

embedding_model = SentenceTransformer(MODEL_NAME)
embedding_model.max_seq_length = MAX_SEQ_LENGTH

_cache_key = {"model": MODEL_NAME, "max_seq_length": MAX_SEQ_LENGTH, "texts": embed_texts}

def _compute_and_cache(texts):
    emb = embedding_model.encode(texts, batch_size=16, show_progress_bar=True)
    if EMBEDDING_CACHE:
        np.save(EMBEDDING_CACHE, emb)
        EMBEDDING_CACHE_IDX.write_text(
            json.dumps(_cache_key, ensure_ascii=False), encoding="utf-8"
        )
    return emb

if EMBEDDING_CACHE and EMBEDDING_CACHE.exists() and EMBEDDING_CACHE_IDX.exists():
    cached_key = json.loads(EMBEDDING_CACHE_IDX.read_text(encoding="utf-8"))
    if cached_key == _cache_key:
        doc_embeddings = np.load(EMBEDDING_CACHE)
        print(f"Loaded cached embeddings: {doc_embeddings.shape}")
    else:
        print("Cache mismatch (texts, model or sequence length changed) — recomputing")
        doc_embeddings = _compute_and_cache(embed_texts)
        print(f"Computed and cached: {doc_embeddings.shape}")
else:
    doc_embeddings = _compute_and_cache(embed_texts)
    print(f"Computed and cached: {doc_embeddings.shape}")


# ── §3 fit BERTopic ───────────────────────────────────────────────────────────
# UMAP reduces embedding dimensions; HDBSCAN clusters them; c-TF-IDF produces
# top words per cluster; MMR diversifies them. only regular documents are fitted.
#
# note on min_df / max_df: BERTopic fits the vectorizer on one concatenated
# document *per topic*, so both thresholds count topics, not documents.
# min_df=2 (original version) dropped every word unique to a single topic, i.e.
# the most distinctive ones; min_df=1 keeps them. max_df=0.3 drops words that
# occur in more than 30 % of topics.

umap_model = UMAP(
    n_neighbors=N_NEIGHBORS,
    n_components=N_COMPONENTS,
    min_dist=0.0,
    metric="cosine",
    random_state=RANDOM_SEED,
)
hdbscan_model = HDBSCAN(
    min_cluster_size=MIN_CLUSTER_SIZE,
    min_samples=MIN_SAMPLES,
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
)
_stop_words = stopwords.words(STOPWORDS_LANG) + EXTRA_STOPWORDS
vectorizer = CountVectorizer(
    ngram_range=(1, 2),
    min_df=1,
    max_df=MAX_DF,
    token_pattern=r"(?u)\b[^\W\d_]{3,}\b",   # words of ≥ 3 letters; no digits, years or "22"
    stop_words=_stop_words,
)

topic_model = BERTopic(
    embedding_model=embedding_model,
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    vectorizer_model=vectorizer,
    ctfidf_model=ClassTfidfTransformer(reduce_frequent_words=True),
    representation_model=MaximalMarginalRelevance(diversity=MMR_DIVERSITY),
    language=BERTOPIC_LANG,
    calculate_probabilities=False,
    verbose=True,
)

fit_docs       = [lemmatized_titles[i] for i in regular_idx]
fit_embeddings = doc_embeddings[regular_idx]
fit_topics, _  = topic_model.fit_transform(fit_docs, embeddings=fit_embeddings)

topics       = [None] * len(data)
topic_source = [None] * len(data)   # "cluster" | "parent" | "transform"
for i, t in zip(regular_idx, fit_topics):
    topics[i], topic_source[i] = int(t), "cluster"


# ── §3b attach corrections and annexes ────────────────────────────────────────
# parent = regular document published on or before the correction whose title
# contains (nearly) all words of the referenced title, compared on crudely stemmed
# words so that genitive forms match ("Netzentgeltmodernisierungsgesetzes" →
# "Netzentgeltmodernisierungsgesetz"). corrections without a parent in the corpus
# (e.g. referring to a law from before the corpus period) are assigned by
# topic_model.transform().

_FUNCTION_WORDS = {"der", "des", "die", "das", "den", "dem", "und", "zur", "zum", "zu", "von", "vom",
                   "für", "über", "mit", "auf", "aus", "bei", "nach", "sowie", "im", "in", "an", "am"}

def _stems(text):
    text = re.sub(rf"\b\d{{1,2}}\.\s*(?:{MONTHS})\s+\d{{4}}", " ", text)   # "vom 22. September 2017"
    words = re.findall(r"[^\W\d_]+", text.lower())
    return {re.sub(r"(?:es|en|er|em|e|s|n)$", "", w) or w for w in words if w not in _FUNCTION_WORDS}

_regular_stems = {i: _stems(titles[i]) for i in regular_idx}
parent_id = [None] * len(data)
unattached = []

for i in attach_idx:
    ref = _stems(ref_title[i])
    best, best_key = None, None
    if ref:
        for j in regular_idx:
            if data[j]["date_published"] > data[i]["date_published"]:
                continue
            overlap = len(ref & _regular_stems[j]) / len(ref)
            if overlap < PARENT_MATCH_MIN:
                continue
            jaccard = len(ref & _regular_stems[j]) / len(ref | _regular_stems[j])
            key = (overlap, jaccard, data[j]["date_published"])
            if best_key is None or key > best_key:
                best, best_key = j, key
    if best is not None:
        topics[i], topic_source[i] = topics[best], "parent"
        parent_id[i] = data[best]["id"]
    else:
        unattached.append(i)

if unattached:
    pred, _ = topic_model.transform(
        [lemmatized_titles[i] for i in unattached],
        embeddings=doc_embeddings[unattached],
    )
    for i, t in zip(unattached, pred):
        topics[i], topic_source[i] = int(t), "transform"

print(f"\nCorrections/annexes attached to parent: {len(attach_idx) - len(unattached)}   "
      f"assigned via transform: {len(unattached)}")

topic_info = topic_model.get_topic_info()
n_topics   = topic_info.shape[0] - 1   # exclude noise topic
n_noise    = int((np.array(topics) == -1).sum())
counts     = pd.Series(topics).value_counts().to_dict()   # includes attached corrections/annexes

print(f"\nTopics found:          {n_topics}")
print(f"Noise docs (topic -1): {n_noise}")


# ── §3c representative titles ─────────────────────────────────────────────────
# the N_REPRESENTATIVE regular documents closest (cosine) to each topic centroid.

_norm_emb = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
representative_titles = {}
for tid in sorted(set(int(t) for t in fit_topics)):
    if tid == -1:
        representative_titles[tid] = []
        continue
    members  = [i for i in regular_idx if topics[i] == tid]
    centroid = _norm_emb[members].mean(axis=0)
    sims     = _norm_emb[members] @ (centroid / np.linalg.norm(centroid))
    order    = np.argsort(-sims)[:N_REPRESENTATIVE]
    representative_titles[tid] = [titles[members[k]] for k in order]

# print topic table for terminal inspection
print()
for _, row in topic_info.sort_values("Topic").iterrows():
    tid   = int(row["Topic"])
    label = "[NOISE]" if tid == -1 else f"topic {tid:>3}"
    words = row["Representation"] if isinstance(row.get("Representation"), list) else []
    print(f"  {label}  n={counts.get(tid, 0):>4}   {', '.join(words[:8])}")
    for rt in representative_titles.get(tid, [])[:2]:
        print(f"               · {rt[:110]}")


# ── §4 save visualisation and intermediate data ───────────────────────────────

log_dir = OUTPUT_DIR / "runlogs_from_sys2_berttopic"
log_dir.mkdir(parents=True, exist_ok=True)

_run_date = datetime.date.today().isoformat()
_viz_path = log_dir / f"{RUN_TAG}_topics_{OUTPUT_PREFIX}_{_run_date}.html"

topic_model.visualize_topics().write_html(_viz_path)
print(f"\nInteractive topic map saved: {_viz_path}")

_topic_info_path   = OUTPUT_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_topic_info.json"
_topic_assign_path = OUTPUT_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_topic_assignments.json.gz"
_params_path       = OUTPUT_DIR / f"{OUTPUT_PREFIX}_{RUN_TAG}_params.json"

_topic_export = [
    {
        "topic_id": int(row["Topic"]),
        "count":    int(counts.get(int(row["Topic"]), 0)),
        "top_words": (row["Representation"] if isinstance(row.get("Representation"), list) else [])[:10],
        "representative_titles": representative_titles.get(int(row["Topic"]), []),
    }
    for _, row in topic_info.sort_values("Topic").iterrows()
]

_topic_info_path.write_text(
    json.dumps(_topic_export, ensure_ascii=False, indent=2), encoding="utf-8"
)
with gzip.open(_topic_assign_path, "wt", encoding="utf-8") as _fh:
    json.dump(
        [
            {
                "topic_id":     int(topics[i]),
                "topic_source": topic_source[i],
                "doc_class":    doc_class[i],
                "parent_id":    parent_id[i],
                "embed_text":   embed_texts[i],
                "doc":          data[i],
            }
            for i in range(len(data))
        ],
        _fh,
        ensure_ascii=False,
    )

_params = {
    "run_date": _run_date,
    "input_file": INPUT_FILE.name,
    "model_name": MODEL_NAME,
    "max_seq_length": MAX_SEQ_LENGTH,
    "bertopic_language": BERTOPIC_LANG,
    "embed_body_chars": EMBED_BODY_CHARS,
    "parent_match_min": PARENT_MATCH_MIN,
    "min_cluster_size": MIN_CLUSTER_SIZE,
    "min_samples": MIN_SAMPLES,
    "n_neighbors": N_NEIGHBORS,
    "n_components": N_COMPONENTS,
    "max_df": MAX_DF,
    "mmr_diversity": MMR_DIVERSITY,
    "random_seed": RANDOM_SEED,
    "n_docs": len(data),
    "n_corrections": doc_class.count("correction"),
    "n_annexes": doc_class.count("annex"),
    "n_attached_to_parent": len(attach_idx) - len(unattached),
    "n_assigned_via_transform": len(unattached),
    "n_topics": n_topics,
    "n_noise": n_noise,
}
_params_path.write_text(json.dumps(_params, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Topic info:        {_topic_info_path}")
print(f"Topic assignments: {_topic_assign_path}")
print(f"Run parameters:    {_params_path}")
print(f"\nNext: run  step2_2_2_process_ger_berttopic_triage_new.py  to label social-policy topics.")

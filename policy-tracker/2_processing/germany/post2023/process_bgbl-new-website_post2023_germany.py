"""
BGBl Teil I processing (recht.bund.de, 2023 onward) → LLM-ready markdown policy set
=====================================================================================
takes the output of 1_collection/germany/fetch_bgbl-new-website_post2023_germany.py
and builds the final policy set for 2023 onward, in the same format as
data/processed/germany/germany_2008-2015_2019-2022_final_policy_set.json, so it can
be passed directly to 3_classification/step3_classify_llm.py (--input).

selection: no cosine-similarity / BERTopic step is needed here — the fetch script
already selected the welfare-relevant publications via their FNA codes
(fna_match = True). every FNA-matched publication with extractable text ends up
in the final set.

steps:
  1. pdf reading + naming
       data/raw/germany/bgbl1_newwebsite_post2023_zip/bgbl1_2023_038.zip
         └─ Regelungstext.pdf
       → read into memory as bgbl1_2023_038_regelungstext (nothing is written:
         the pdfs stay in the raw zips only)
     the ZIPs are only read, never modified. a zip can contain more than one
     file (a separate "Anlage"): every pdf is read, the "Regelungstext" is
     the main document, the others are treated as annexes.
  2. full-text extraction with pymupdf4llm → markdown
       pymupdf4llm handles reading order, paragraphs, hyphenation, headings,
       lists and tables (detected automatically, rendered as markdown tables).
       the raw markdown is cached in data/processed/germany/post2023/markdown_cache/
       (bgbl1_2023_038_regelungstext.{engine}.md), so an interrupted run
       resumes without re-extracting (use --force to redo).
     engine selection: pymupdf4llm has two engines. the layout engine
       (pymupdf-layout) gives the best tables and removes running page
       headers/footers, but occasionally drops whole lines (e.g. "1. ab
       1. Januar 2024" in the Mindestlohnanpassungsverordnung, BGBl. 2023 I
       Nr. 321). every markdown is therefore checked against the plain text of
       the pdf (pymupdf get_text, boilerplate excluded): if more than
       MAX_TOKEN_LOSS of its words are missing, the legacy engine is tried too
       and the more complete markdown is kept. engine and coverage per
       publication are listed in the run log.
     cleaning on top of pymupdf4llm (still necessary, even though pymupdf4llm does most-> very
     specific to BGBl and its format. if u run other raw data, you may need other steps):
       - page-1 masthead (Bundesgesetzblatt / Teil I / year / Ausgegeben … /
         Nr. …): it is body text on page 1, not a page header, so pymupdf4llm
         keeps it. the Nr. is kept for a consistency check against the metadata.
       - "Herausgeber: Bundesministerium der Justiz" line at the end.
       - running headers ("Bundesgesetzblatt Jahrgang … Seite x von y"): only
         needed for the legacy engine.
       - letter-spaced signatures and headings ("D e r B u n d e s k a n z l e r"):
         pymupdf4llm passes them through. they are repaired with glyph positions
         from pymupdf (word gaps are wider than letter gaps) and substituted
         into the markdown.
  3. merge + output json
       main document and annexes are merged into one full_text (annexes appended
       under a heading, see ANNEX_HEADING). one entry per publication with the
       same fields as the 2008-2015/2019-2022 final policy set.

field mapping to the final policy set format (differences to the
offenegesetze.de-based years, where BGBl I was paginated in multi-law issues):
  id              bgbl1-{year}-{issue}-1   (same pattern as before; since 2023
                  every Nr. is exactly one publication → order_in_issue = 1)
  issue_number    int (the Nr. of the publication)
  bgbl_page       None   (no continuous page numbering since 2023)
  pdf_page        1      (the publication starts on page 1 of its own pdf)
  num_pages       pages of all merged pdfs
  url_web         recht.bund.de page of the publication
  url_api         ELI uri (recht.bund.de has no api; ELI is the machine-readable id)
  url_pdf         url of the Regelungstext pdf
  date_*          normalised to the old "YYYY-MM-DDT00:00:00Z" format
  full_text       markdown (pymupdf4llm) instead of plain text
  system_sources  "fna_match" (selection system, see above)
  similarity_score is not set (no cosine-similarity step), as for the
  's2_only' entries of the earlier final policy set.

input:
  - newest data/raw/germany/bgbl1_website_{start}-{end}_{YYYYMMDD}.json(.gz)
    (or --metadata PATH)
output:
  - data/processed/germany/post2023/markdown_cache/bgbl1_{year}_{nr}_{name}.{engine}.md (markdown cache)
  - data/processed/germany/germany_{start}-{end}_final_policy_set.json
  - data/processed/germany/post2023/runlogs_from_post2023_fulltext/fulltext_runlog_germany_{start}-{end}_{date}.md

usage:
    python process_bgbl-new-website_post2023_germany.py
    python process_bgbl-new-website_post2023_germany.py --metadata path/to/file.json
    python process_bgbl-new-website_post2023_germany.py --limit 20   # test run (separate output file)
    python process_bgbl-new-website_post2023_germany.py --force      # re-extract all markdown

requirements:
    pip install pymupdf pymupdf4llm pymupdf-layout
"""

import argparse
import datetime
import gzip
import json
import os
import re
import stat
import statistics
import zipfile
from collections import Counter
from pathlib import Path

import pymupdf
import pymupdf4llm

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

def _find_root(marker="CLAUDE.md"):
    for p in [Path(__file__).parent, *Path(__file__).parent.parents]:
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"project root not found (no {marker} above {Path(__file__).parent})")

PROJECT_ROOT  = _find_root()
COUNTRY       = "germany"
RAW_DIR       = PROJECT_ROOT / "data" / "raw" / COUNTRY
ZIP_DIR       = RAW_DIR / "bgbl1_newwebsite_post2023_zip"
DATA_DIR      = PROJECT_ROOT / "data" / "processed" / COUNTRY
MD_DIR        = DATA_DIR / "post2023" / "markdown_cache"   # markdown cache, one .{engine}.md per pdf in the zips
LOG_DIR       = DATA_DIR / "post2023" / "runlogs_from_post2023_fulltext"
OUTPUT_SUFFIX = "final_policy_set"                         # → germany_{years}_final_policy_set.json
SYSTEM_SOURCE = "fna_match"                                # value of "system_sources" in the output

# pymupdf4llm extraction engines, tried in this order (see "engine selection" in the docstring)
#   "layout": pymupdf-layout (layout model) — best tables + reading order, drops running
#             headers/footers itself, but occasionally drops whole lines
#   "legacy": rule-based pymupdf4llm path — keeps those lines, weaker on complex tables
# both detect tables automatically and write them as markdown tables
ENGINES = ("layout", "legacy")
# the next engine is tried if more than this share of the words of the pdf's plain text
# (pymupdf get_text, without masthead/headers/footers) is missing from the markdown
MAX_TOKEN_LOSS  = 0.002
WARN_TOKEN_LOSS = 0.01     # warn if even the best engine misses more than this
# pymupdf4llm.to_markdown options per engine
#   header/footer=False → drop running page headers/footers (layout only)
#   use_ocr=False       → the BGBl pdfs are born-digital; OCR would need tesseract
#                         and makes the output less deterministic
ENGINE_OPTS = {
    "layout": dict(header=False, footer=False, use_ocr=False, page_chunks=False,
                   page_separators=False, write_images=False, embed_images=False, show_progress=False),
    "legacy": dict(table_strategy="lines_strict", page_chunks=False, write_images=False,
                   embed_images=False, show_progress=False),
}
# heading under which an additional pdf of the same zip is appended to full_text
ANNEX_HEADING = "\n\n---\n\n## Anlage (separate Datei: {name})\n\n"

# letter-spacing repair: a line counts as letter-spaced if it has at least
# SPACED_MIN_LETTERS letters and at least SPACED_MIN_RATIO of its neighbouring
# letters are separated by a space (kerned pairs like "Vo", "Ve" are not)
SPACED_MIN_LETTERS = 4
SPACED_MIN_RATIO   = 0.75
SPACED_WORD_GAP    = 1.5   # gap > median letter gap × this → word break

# quality flags
MIN_CHARS          = 200   # warn if the merged text is shorter
MIN_CHARS_PER_PAGE = 300   # warn if the average page has less text (extraction problem?)

# ──────────────────────────────────────────────────────────────────────────────

_TODAY     = datetime.date.today()
_META_NAME = re.compile(r"^bgbl1_website_(\d{4}-\d{4})_(\d{8})\.json(?:\.gz)?$")

# matched against a markdown line with formatting removed (see _plain)
_MASTHEAD = re.compile(
    r"^(?:Bundesgesetzblatt\s*)?(?:Teil I\s*)?(?:\d{4}\s*)?"
    r"(?:Ausgegeben zu \S+ am \d{1,2}\. \S+ \d{4}\s*)?(?:Nr\. (\d+[a-z]?))?$"
)
_DROP_LINES = [
    re.compile(r"^Herausgeber: Bundesministerium der Justiz"),
    # running header/footer — removed by the layout engine itself, kept by legacy
    re.compile(r"^Seite \d+ von \d+$"),
    re.compile(r"^Bundesgesetzblatt Jahrgang \d{4} Teil I Nr\. \S+, ausgegeben zu .+$"),
]
_RESIDUAL_SPACED = re.compile(r"(?<!\S)(?:\w ){5,}\w(?!\S)")


# ── helpers ───────────────────────────────────────────────────────────────────


def _nr_slug(number) -> str:
    """'7' → '007', '12a' → '012a' — identical to the fetch script."""
    m = re.match(r"(\d+)(.*)", str(number))
    return f"{int(m.group(1)):03d}{m.group(2)}" if m else str(number)


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _file_slug(name: str) -> str:
    """'Regelungstext.pdf' → 'regelungstext', 'Anlage 1 (zu § 3).pdf' → 'anlage_1_zu_3'"""
    stem = Path(name).stem.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        stem = stem.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_") or "document"


def _iso_z(date: str | None) -> str | None:
    """'2023-01-04' → '2023-01-04T00:00:00Z' (format of the earlier final policy set)."""
    return f"{date[:10]}T00:00:00Z" if date else None


def _plain(md_line: str) -> str:
    """markdown line without heading marks, emphasis and html tags."""
    t = re.sub(r"<[^>]+>", "", md_line)
    t = re.sub(r"^\s*(?:#+|>)\s*", "", t)
    t = t.replace("**", "").replace("*", "").replace("_", " ")
    t = re.sub(r"^[|\-: ]+$", "", t)   # table separator row ("|---|")
    t = t.replace("|", " ")            # masthead parts sometimes come as a one-cell table
    return re.sub(r"\s+", " ", t).strip()


def load_json(path: Path):
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def find_metadata(path: str | None) -> tuple[Path, str]:
    """returns (metadata path, year slug like '2023-2026')."""
    if path:
        p = Path(path)
        m = _META_NAME.match(p.name)
        return p, (m.group(1) if m else "custom")
    candidates = [(m.group(2), f.name, m.group(1)) for f in RAW_DIR.iterdir() if (m := _META_NAME.match(f.name))]
    if not candidates:
        raise SystemExit(f"No bgbl1_website_*_*.json found in {RAW_DIR}")
    _, fname, slug = max(candidates)  # newest collection date
    return RAW_DIR / fname, slug


# ── step 1: pdf reading + naming ──────────────────────────────────────────────


def read_pdfs(zip_path: Path, year: int, nr_slug: str) -> tuple[list[tuple[str, str, bytes]], list[str]]:
    """reads every pdf of the zip into memory under a unique name (nothing is written).
    returns ([(original member name, name, pdf bytes), ...], [non-pdf member names])."""
    pdfs, others, used = [], [], set()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not info.filename.lower().endswith(".pdf"):
                others.append(info.filename)
                continue
            base = f"bgbl1_{year}_{nr_slug}_{_file_slug(info.filename)}"
            name, i = base, 2
            while name in used:  # two members with the same slug
                name, i = f"{base}_{i}", i + 1
            used.add(name)
            pdfs.append((info.filename, name, zf.read(info)))
    return pdfs, others


# ── step 2: markdown extraction + cleaning ────────────────────────────────────


def _tokens(text: str) -> Counter:
    return Counter(re.findall(r"\w+", text.replace("<br>", " ")))


def scan_pdf(doc: pymupdf.Document) -> tuple[dict[str, str], Counter]:
    """one pass over the glyphs of the pdf. returns
    - fixes:    {letter-spaced line text: repaired text} ("D e r B u n d …" → "Der Bund…")
    - baseline: words of the pdf's text lines (letter-spaced lines repaired), without
                the boilerplate the cleaning removes on purpose — reference for the
                coverage check of the markdown"""
    fixes, baseline = {}, Counter()
    for page in doc:
        for block in page.get_text("rawdict")["blocks"]:
            if block["type"] != 0:  # images (e.g. the eagle)
                continue
            for line in block["lines"]:
                chars = [c for s in line["spans"] for c in s["chars"]]
                raw = re.sub(r"\s+", " ", "".join(c["c"] for c in chars)).strip()
                if not raw or _MASTHEAD.match(raw) or any(p.match(raw) for p in _DROP_LINES):
                    continue
                letters = [i for i, c in enumerate(chars) if not c["c"].isspace()]
                spaced = sum(1 for a, b in zip(letters, letters[1:]) if b > a + 1)
                if len(letters) < SPACED_MIN_LETTERS or spaced / (len(letters) - 1) < SPACED_MIN_RATIO:
                    baseline.update(_tokens(raw))
                    continue
                # letter-spaced: word gaps are visibly wider than letter gaps
                gaps = [chars[b]["bbox"][0] - chars[a]["bbox"][2] for a, b in zip(letters, letters[1:])]
                threshold = statistics.median(gaps) * SPACED_WORD_GAP
                out = chars[letters[0]]["c"]
                for gap, i in zip(gaps, letters[1:]):
                    out += (" " if gap > threshold else "") + chars[i]["c"]
                baseline.update(_tokens(out))
                if raw != out:
                    fixes[raw] = out
    return fixes, baseline


def markdown_raw(pdf: bytes, name: str, engine: str, force: bool) -> str:
    """pymupdf4llm markdown of the pdf, cached as MD_DIR/{name}.{engine}.md."""
    cache = MD_DIR / f"{name}.{engine}.md"
    if cache.exists() and not force:
        return cache.read_text(encoding="utf-8")
    pymupdf4llm.use_layout(engine == "layout")
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        md = pymupdf4llm.to_markdown(doc, **ENGINE_OPTS[engine])
    MD_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(md, encoding="utf-8")
    return md


def clean_markdown(md: str, fixes: dict[str, str]) -> tuple[str, str | None]:
    """removes masthead / Herausgeber line / running headers, repairs letter spacing
    (fixes from scan_pdf). returns (clean markdown, Nr. from the masthead or None)."""
    lines, masthead_nr, i = md.splitlines(), None, 0
    while i < len(lines):  # leading lines that consist only of masthead parts
        plain = _plain(lines[i])
        if plain:
            m = _MASTHEAD.match(plain)
            if not m:
                break
            masthead_nr = m.group(1) or masthead_nr
        i += 1
    kept = [ln for ln in lines[i:] if not any(p.match(_plain(ln)) for p in _DROP_LINES)]
    text = "\n".join(kept)
    text = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", text)  # inner space runs (list indentation kept)

    # letter-spaced lines: matched glyph by glyph with optional whitespace in between,
    # because the engines do not always keep the pdf's spaces ("Familie , Senioren"
    # in the pdf, "Familie, Senioren" in the markdown); longest first: no partial overlaps
    for raw in sorted(fixes, key=len, reverse=True):
        glyphs = raw.replace(" ", "")
        pattern = r"[ \t]?".join(map(re.escape, glyphs))
        text = re.sub(pattern, lambda m: fixes[raw] if m.group().count(" ") >= len(glyphs) // 2 else m.group(), text)

    text = re.sub(r"[ \t]+\n", "\n", text)       # trailing spaces after each block
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text, masthead_nr


def extract_document(pdf: bytes, name: str, force: bool) -> dict:
    """markdown of the first engine whose coverage is good enough (else the best one).
    returns {"text", "n_pages", "masthead_nr", "engine", "loss", "missing"}"""
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        fixes, baseline = scan_pdf(doc)
        n_pages = doc.page_count
    n_base, best = max(sum(baseline.values()), 1), None
    for engine in ENGINES:
        text, nr = clean_markdown(markdown_raw(pdf, name, engine, force), fixes)
        missing = baseline - _tokens(text)
        loss = sum(missing.values()) / n_base
        if best is None or loss < best["loss"]:
            best = {"text": text, "masthead_nr": nr, "engine": engine, "loss": loss, "missing": missing}
        if loss <= MAX_TOKEN_LOSS:
            break
    return {**best, "n_pages": n_pages}


# ── step 3: final policy set entry ────────────────────────────────────────────


def to_policy_entry(rec: dict, full_text: str, n_pages: int) -> dict:
    """metadata record of the fetch script → entry in the final policy set format."""
    nr = str(rec["issue_number"])
    issue = int(nr) if nr.isdigit() else nr
    return {
        "id":             f"bgbl1-{rec['year']}-{nr}-1",
        "year":           rec["year"],
        "issue_number":   issue,
        "order_in_issue": 1,
        "title":          rec.get("title"),
        "doc_type":       rec.get("doc_type"),
        "date_published": _iso_z(rec.get("date_published")),
        "date_law":       _iso_z(rec.get("date_law")),
        "bgbl_page":      None,
        "pdf_page":       1,
        "num_pages":      n_pages,
        "url_web":        rec.get("url_web"),
        "url_api":        rec.get("url_eli"),
        "url_pdf":        (rec.get("url_pdfs") or [None])[0],
        "full_text":      full_text,
        "system_sources": SYSTEM_SOURCE,
    }


def process_publication(rec: dict, force: bool) -> dict:
    """zip → pdfs (in memory) → merged markdown. returns a status dict with 'entry' (or None)."""
    nr_slug = _nr_slug(rec["issue_number"])
    zip_path = ZIP_DIR / f"bgbl1_{rec['year']}_{nr_slug}.zip"
    status = {"id": rec["id"], "zip": zip_path.name, "entry": None, "warnings": [],
              "n_pdfs": 0, "others": [], "n_chars": 0, "n_pages": 0, "engines": [], "loss": 0.0}
    warn = status["warnings"].append

    if not zip_path.exists():
        warn("zip missing")
        return status
    try:
        pdfs, others = read_pdfs(zip_path, rec["year"], nr_slug)
    except zipfile.BadZipFile:
        warn("zip corrupt")
        return status
    status["n_pdfs"], status["others"] = len(pdfs), others
    if others:
        warn(f"non-pdf files in zip ignored: {others}")

    main = [p for p in pdfs if "regelungstext" in p[0].lower()]
    if not main and len(pdfs) == 1:
        main = pdfs
        warn(f"no 'Regelungstext' in zip, used {pdfs[0][0]}")
    elif not main and pdfs:
        warn("no 'Regelungstext' in zip — pdfs merged in zip order")
        main = pdfs[:1]
    elif len(main) > 1:
        warn(f"{len(main)} Regelungstext pdfs — first used as main, rest appended")
    if not pdfs:
        warn("no pdf in zip")
        return status
    ordered = main[:1] + [p for p in pdfs if p != main[0]]

    parts, n_pages = [], 0
    for k, (member, name, pdf) in enumerate(ordered):
        try:
            ext = extract_document(pdf, name, force=force)
        except Exception as e:  # broken/encrypted pdf
            warn(f"text extraction failed for {member}: {e}")
            continue
        n_pages += ext["n_pages"]
        status["engines"].append(ext["engine"])
        status["loss"] = max(status["loss"], ext["loss"])
        if ext["loss"] > WARN_TOKEN_LOSS:
            top = ", ".join(f"{w}×{n}" for w, n in ext["missing"].most_common(8))
            warn(f"{member}: {ext['loss']:.1%} of plain-text words missing ({ext['engine']}): {top}")
        if k == 0:
            if ext["masthead_nr"] and ext["masthead_nr"] != str(rec["issue_number"]):
                warn(f"masthead says Nr. {ext['masthead_nr']}, metadata says {rec['issue_number']}")
            if "Ausgegeben zu" in ext["text"][:400]:
                warn("masthead possibly not fully removed")
            parts.append(ext["text"])
        elif ext["text"]:
            parts.append(ANNEX_HEADING.format(name=member).lstrip("\n") if not parts
                         else ANNEX_HEADING.format(name=member))
            parts.append(ext["text"])

    full_text = "".join(parts).strip()
    status["n_chars"], status["n_pages"] = len(full_text), n_pages
    if not full_text:
        warn("no text extracted")
        return status
    if len(full_text) < MIN_CHARS:
        warn(f"short text ({len(full_text)} chars)")
    elif len(full_text) / max(n_pages, 1) < MIN_CHARS_PER_PAGE:
        warn(f"little text per page ({len(full_text)} chars / {n_pages} pages)")
    residual = _RESIDUAL_SPACED.findall(full_text)
    if residual:
        warn(f"letter-spaced text left: {residual[:3]}")
    status["entry"] = to_policy_entry(rec, full_text, n_pages)
    return status


# ── run log ───────────────────────────────────────────────────────────────────


def save_run_log(meta_path: Path, year_slug: str, out_json: Path, statuses: list[dict],
                 corpus: list[dict], orphans: list[str], limit: int | None):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_test{limit}" if limit else ""
    log_path = LOG_DIR / f"fulltext_runlog_{COUNTRY}_{year_slug}{suffix}_{_TODAY.isoformat()}.md"
    if log_path.exists():
        os.chmod(log_path, stat.S_IWRITE)

    lengths = sorted(len(e["full_text"]) for e in corpus)
    warned = [s for s in statuses if s["warnings"]]
    excluded = [s for s in statuses if s["entry"] is None]
    longest = sorted(corpus, key=lambda e: len(e["full_text"]), reverse=True)[:5]
    n_tables = sum(1 for e in corpus if re.search(r"^\|[-:| ]+\|$", e["full_text"], re.M))
    engines = Counter("+".join(s["engines"]) for s in statuses if s["engines"])
    losses = sorted(s["loss"] for s in statuses if s["engines"])
    worst = sorted((s for s in statuses if s["engines"]), key=lambda s: s["loss"], reverse=True)[:10]

    content = f"""# BGBl I post-2023 full-text run log

| | |
|---|---|
| date | {_TODAY.isoformat()} |
| metadata | `{_rel(meta_path)}` |
| zip dir | `{_rel(ZIP_DIR)}` |
| pymupdf / pymupdf4llm | {pymupdf.__version__} / {pymupdf4llm.__version__} |
| engines (order) | {", ".join(ENGINES)} — fallback if > {MAX_TOKEN_LOSS:.1%} of plain-text words missing |
| engine options | `{ENGINE_OPTS}` |
| limit | {limit or "—"} |

## results

| metric | n |
|---|---|
| FNA-matched publications processed | {len(statuses)} |
| in final policy set | {len(corpus)} |
| excluded (no text) | {len(excluded)} |
| zips with more than one pdf (merged) | {sum(1 for s in statuses if s['n_pdfs'] > 1)} |
| publications with markdown tables | {n_tables} |
| publications with warnings | {len(warned)} |
| engine used | {", ".join(f"{k}: {v}" for k, v in engines.most_common())} |
| missing plain-text words, median / max share | {f"{statistics.median(losses):.2%} / {losses[-1]:.2%}" if losses else "—"} |
| chars min / median / max | {f"{lengths[0]} / {int(statistics.median(lengths))} / {lengths[-1]}" if lengths else "—"} |
| ≈ tokens median / max (chars/4) | {f"{int(statistics.median(lengths)) // 4} / {lengths[-1] // 4}" if lengths else "—"} |

## longest publications

| id | chars | pages | title |
|---|---|---|---|
{chr(10).join(f"| {e['id']} | {len(e['full_text'])} | {e['num_pages']} | {(e['title'] or '')[:80]} |" for e in longest)}

## lowest text coverage (share of plain-text words missing from the markdown)

| id | missing | engine |
|---|---|---|
{chr(10).join(f"| {s['id']} | {s['loss']:.2%} | {'+'.join(s['engines'])} |" for s in worst)}

## warnings

| id | zip | warnings |
|---|---|---|
{chr(10).join(f"| {s['id']} | {s['zip']} | {'; '.join(s['warnings']).replace('|', '/')} |" for s in warned)}

## zips on disk not in the FNA-matched metadata

{", ".join(orphans) if orphans else "none"}

## output files

- `{_rel(out_json)}`
- `{_rel(MD_DIR)}/` (markdown cache)
"""
    log_path.write_text(content, encoding="utf-8")
    os.chmod(log_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    return log_path


# ── main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="BGBl I post-2023: zipped PDFs → markdown final policy set")
    parser.add_argument("--metadata", metavar="PATH",
                        help="metadata json from the fetch script (default: newest in data/raw/germany)")
    parser.add_argument("--limit", type=int, help="only process the first N matched publications (testing)")
    parser.add_argument("--force", action="store_true", help="re-extract markdown even if a cached .md exists")
    args = parser.parse_args()

    meta_path, year_slug = find_metadata(args.metadata)
    metadata = load_json(meta_path)
    matched = [r for r in metadata if r.get("fna_match")]
    if args.limit:
        matched = matched[: args.limit]
    print(f"Metadata: {meta_path}")
    print(f"  {len(metadata)} publications, {len(matched)} FNA-matched → processing those\n")

    statuses = []
    for i, rec in enumerate(matched, 1):
        s = process_publication(rec, args.force)
        statuses.append(s)
        flag = f" ⚠ {'; '.join(s['warnings'])}" if s["warnings"] else ""
        print(f"  [{i}/{len(matched)}] {rec['id']}: {s['n_chars']} chars, {s['n_pages']} pages, "
              f"{s['n_pdfs']} pdf(s), {'+'.join(s['engines']) or '—'}{flag}", flush=True)

    corpus = sorted((s["entry"] for s in statuses if s["entry"]),
                    key=lambda e: (e["year"], int(re.match(r"\d+", str(e["issue_number"])).group())))

    # write json (test runs get their own file so the real policy set is never overwritten)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_test{args.limit}" if args.limit else ""
    out_json = DATA_DIR / f"{COUNTRY}_{year_slug}_{OUTPUT_SUFFIX}{suffix}.json"
    out_json.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")

    expected = {s["zip"] for s in statuses}
    orphans = sorted(f.name for f in ZIP_DIR.glob("*.zip") if f.name not in expected) \
        if ZIP_DIR.is_dir() and not args.limit else []
    log_path = save_run_log(meta_path, year_slug, out_json, statuses, corpus, orphans, args.limit)

    # summary
    warned = [s for s in statuses if s["warnings"]]
    excluded = [s for s in statuses if s["entry"] is None]
    print(f"\n{'═' * 50}\nSummary\n{'═' * 50}")
    print(f"  Output:  {out_json}")
    print(f"  Markdown cache: {MD_DIR}")
    print(f"  Run log: {log_path} (read-only)")
    print(f"  In final policy set: {len(corpus)}/{len(statuses)}")
    print(f"  Merged multi-pdf zips: {sum(1 for s in statuses if s['n_pdfs'] > 1)}")
    print(f"  Engine used: {dict(Counter('+'.join(s['engines']) for s in statuses if s['engines']))}")
    if excluded:
        print(f"\n  ✗ {len(excluded)} excluded (no text): {[s['id'] for s in excluded]}")
    if warned:
        print(f"\n  ⚠ {len(warned)} publications with warnings (details in run log)")
    if orphans:
        print(f"\n  ZIPs on disk not in the FNA-matched metadata ({len(orphans)}): {orphans[:10]}"
              f"{' …' if len(orphans) > 10 else ''}")


if __name__ == "__main__":
    main()

# phd research: automated policy-tracking, welfare states and crises

A phd research project at the university of mannheim on the automated, llm-based compilation of policy-trackers holding complex policy classifications.

---

## about this project

this research project has a technical and a substantial aim:

1. it develops a pipeline for the llm-based compilation of policy-trackers including information based on summaries, classification tasks, and information retrieval tasks. it tests prompt designs and llms in factorial experiments.

2. It provides a comprehensive collection of social policy legislation (Germany, and, in the future, other country cases) that to investigate
   the social policy developments before, during and after two major crises, that is the great recession of 2008 and Covid-19. It allows an
   investigation how welfare states operate in "crisis mode" and how and if they adapt legislative strategy as a consequence of a disruptive crisis.

---

## repository structure

| Folder            | Description                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `litrev/`         | Systematic literature review — data processing pipeline and analysis                                                                                    |
| `policy-tracker/` | pipeline that fetches raw legislative texts, filters them to social policy, classifies them with llms and evaluates the results against a gold standard |

```
policy-tracker/
├── CLAUDE.md                 # project overview and design principles
├── 1_collection/             # step 1: fetch raw legislative texts
│   ├── germany/              #   BGBl Teil I (offenegesetze.de api ≤2022, recht.bund.de ≥2023)
│   └── eurofound/            #   eurofound covid-19 policy database
├── 2_processing/germany/     # step 2: filter corpus to social policy (pooled evaluation)
├── 3_classification/         # step 3: prompt designs, llm classification, codebook
│   └── gold_standard/        #   sampling + interactive annotation tool
├── 4_analysis/               # step 4: evaluation of llm output vs. gold standard
├── data/
│   ├── raw/                  # output of step 1 (never modified manually)
│   ├── processed/            # output of step 2, incl. run logs
│   ├── gold_standard/        # sampled and hand-labelled policies
│   ├── classifications/      # llm output, one json per model × prompt variant
│   ├── analysis_results/     # evaluation tables (csv) and plots
│   └── external/             # oecd tax-ben, comparison trackers and datasets
├── docs/                     # codebook pdf, policy source scouting
├── notebooks/                # exploratory notebooks
└── old/                      # retired scripts, kept for reference
```

---

## literature review

the `litrev/` folder contains a reproducible pipeline for systematic literature review:

1. **data collection** from academic databases (scopus, web of science)
2. **keyword extraction** using nlp methods to identify relevant search terms
3. **dataset assembly** combining automated and manual searches
4. **analysis** structures the literature, deploys llms for abstract summaries

### quick start

```bash
# install dependencies
pip install pandas keybert yake openpyxl

# run the jupyter notebooks in litrev/notebooks/ sequentially
```

## policy-tracker

the `policy-tracker/` folder contains a pipeline that builds a policy-tracker from raw legislative texts. for each policy it records dates of entry into force and termination, a summary, whether it refers to a crisis, and the social policy field(s) it addresses. germany (BGBl Teil I, 2008–2015 and 2019–2022, i.e. great recession and covid-19) is the prototype; the pipeline is built to extend to further countries, crises and classification tasks.

1. **data collection** (`1_collection/`)
   - `fetch_bgbl_germany.py` fetches metadata and full texts of BGBl Teil I via the offenegesetze.de api (available until 2022)
   - `fetch_bgbl-new-website_post2023_germany.py` scrapes recht.bund.de (2023 onward, no api), filtered by FNA subject area; downloads zip packages of the policy texts
   - both scripts save progress and can be interrupted and resumed; `compress.py` gzips raw files too large for github
2. **processing** (`2_processing/germany/`) for Germany the processing steps depend on whether the policies concern pre- or post2023 due to the different raw data retrieval sources and processes.
   - processing for pre2023: filters the corpus to social policy through a pooled evaluation of two systems:
     - system 1: cosine similarity between texts and seed descriptions (derived from BMAS/BMBFSFJ sources and a list of covid legislation), with interactive triage of borderline cases
     - system 2: BERTopic clustering with interactive triage of topics
     - the union of both systems is inspected and compiled into the final policy set (`step3_process_pooled_union_eval_compile.ipynb`)
   - processing for post2023:
     - the retrieved data are already all ensured to regard social policy. the steps of the pre2023-processing are therefore obsolete for post2023.
     - using pymupdf and pmupdf4llm, policy texts are extracted from pdfs and stored in jsons of the same structure as in pre2023-processing.
3. **classification** (`3_classification/`)
   - `codebook.md` defines all variables (dates, `crisis_ref`, social policy fields)
   - `step2_promptdesigns.py` holds 16 prompt variants in a 2×2×2×2 factorial design: zero-/few-shot, batch/single task, with/without class definitions, with/without justification
   - `step3_classify_llm.py` runs every model × prompt combination (openai api and open-source models via the KISSKI SAIA api); `step3_classify_llm_hf.py` is the variant for huggingface inference providers
   - `gold_standard/` draws a random sample from the final policy set and provides an interactive terminal tool for expert annotation
4. **evaluation** (`4_analysis/`) compares llm output with the gold standard: output compliance, macro f1/precision/recall and jaccard for social policy fields, f1 for `crisis_ref`, krippendorff's alpha, confusion matrices and a decomposition by prompt dimension. results go to `data/analysis_results/`

models evaluated so far: gpt-4.1-mini, gpt-oss-120b, mistral-large-3, llama-3.3-70b, llama-3.1-8b, qwen3.6-35b, gemma-4-31b.

### quick start

```bash
# install dependencies
pip install requests beautifulsoup4 pandas numpy sentence-transformers bertopic umap-learn hdbscan spacy nltk openai huggingface_hub scikit-learn krippendorff matplotlib seaborn
python -m spacy download de_core_news_lg

# run the scripts in each step folder in order of their step prefix
# api keys are read from environment variables (e.g. SAIA_API_KEY, SAIA_API_ENDPOINT, HF_API_KEY)
```

---

## contact

For questions about this research or collaboration opportunities, please open an issue.

---

## acknowledgments

- University of Mannheim
- [KeyBERT](https://github.com/MaartenGr/KeyBERT) and [YAKE](https://github.com/LIAAD/yake) for keyword extraction

## third-party software

This pipeline's processing step for uses the following third-party libraries by Artifex Software, Inc.:

- PyMuPDF: AGPL-3.0
- PyMuPDF4LLM: AGPL-3.0
- PyMuPDF Layout: PolyForm Noncommercial 1.0.0

The libraries are not distributed with this repository, which serves academic purposes only, and are used unmodified; they are imported and called by the script only. Users install them separately: pip install pymupdf pymupdf4llm pymupdf-layout

PyMuPDF Layout is used for the default "layout" extraction engine and is licensed for non-commercial use only; commercial use requires a licence from Artifex. Licensing information: https://artifex.com/licensing

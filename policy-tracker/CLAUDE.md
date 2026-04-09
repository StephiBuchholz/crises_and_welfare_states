# crisis policy tracker — project overview

## what this project does

automated pipeline to compile a policy tracker of welfare/social policies introduced by states
in response to major crises (2008 financial crash, COVID-19). for each policy, the tracker records
metadata, a summary, and a classification of its direction relative to the pre-crisis status quo:
**retrenchment**, **expansion**, or **no change**, measured along three dimensions:
conditionality, generosity, and coverage. it further includes brief summaries of the policy.

the pipeline is designed to be reproducible and scalable to new countries, crises, and
classification tasks, also beyond welfare policy.

---

## pipeline steps

### step 1 — data collection (`1_collection/`)

fetch raw legislative texts from official APIs or scraping, one script per country/source.
scripts are named `fetch_{source}_{country}.py`.

- output goes to: `data/raw/{country}/`
- scripts save progress automatically and can be safely interrupted and resumed.

| script                     | source                             | country           | crisis period     |
| -------------------------- | ---------------------------------- | ----------------- | ----------------- |
| `fetch_bgbl_germany.py`    | OffeneGesetze.de API (BGBl Teil I) | germany           | 2019–2022 (COVID) |
| `fetch_eurofound_covid.py` | Eurofound COVID-19 database        | EU/cross-national | COVID             |

to add a new country: create a new subfolder in `1_collection/` and follow the same pattern.

### step 2 — data processing (`2_processing/`)

filter raw texts down to welfare-relevant policies. clean and structure data for LLM input.
define the pre-crisis policy baseline per country/domain.

- input: `data/raw/`
- output: `data/processed/`

### step 3 — LLM classification (`3_classification/`)

run standardized prompts against processed texts to classify each policy. classification ofccurs against a baseline, i.e. a policy-setup pre-crisis, likely through oecd tax-ben data (see data/external/oecd_taxben); to be determined. prompt templates are stored in `3_classification/prompts/` and are fixed across conditions except for the experimentally varied components.

**experimental framework:**

- varies: model family/size; prompt configuration (zero-shot vs. few-shot)
- fixed: all other prompt content, label schema, parsing logic
- primary runs: temperature = 0, fixed random seed (near-deterministic output)
- robustness checks: to be determined

- input: `data/processed/`
- output: `data/tracker/`

### step 3b — gold standard & validation (`3_classification/gold_standard/`)

to evaluate classifier quality, a random sample of policies is drawn and manually labelled
by domain experts before the automated classification . the prototype uses germany (COVID-19 period); the gold standard is
designed to be extended to additional countries over time.

- **sampling:** random draw from `data/processed/{country}/`; sampling scripts in `3_classification/gold_standard/`
- **labelling:** expert annotation using the same label schema; annotation guidelines in `docs/`
- **output:** `data/gold_standard/` — annotated samples per country
- **use:** evaluate LLM classification accuracy (precision, recall, F1, agreement) across models and prompt configurations in step 4

### step 4 — analysis (`4_analysis/`)

statistical analysis of the tracker. potential integration with survey data and
cross-national comparative datasets.

- input: `data/tracker/`, `data/external/`

---

## folder structure

```
policy-tracker/
├── CLAUDE.md
├── 1_collection/          # step 1: fetch raw legislative texts
│   ├── germany/
│   └── eurofound/
├── 2_processing/          # step 2: filter + prepare for LLM
├── 3_classification/      # step 3: LLM classification + gold standard
│   ├── prompts/
│   └── gold_standard/     # sampling scripts + annotation guidelines
├── 4_analysis/            # step 4: analysis + survey data
├── data/
│   ├── raw/               # output of step 1 — never modify manually
│   │   ├── germany/
│   │   └── eurofound/
│   ├── processed/         # output of step 2
│   ├── tracker/           # output of step 3 — the policy tracker
│   ├── gold_standard/     # expert-annotated samples per country (output of step 3b)
│   └── external/          # third-party trackers for validation/comparison
├── notebooks/             # exploratory Jupyter notebooks
└── docs/                  # source scouting notes, codebooks, documentation
```

---

## data

- raw legislative text data: retrieved per country from apis or through scraping. 
- baselines to compare to for classification: likely from oecd tax benefit `data/external/oecd_taxben` 
- validations: collection of possible data in `docs` "policy_scouting", see ipynb in `notebooks`


---

## key design principles

- **raw data is sacred:** never modify files in `data/raw/` — always derive `data/processed/` from them.
- **reproducibility:** all scripts produce dated output files; primary LLM runs use temperature = 0.
- **scalability:** adding a country = new subfolder in `1_collection/` + new subfolder in `data/raw/`.
- **transparency:** prompt templates are versioned in `3_classification/prompts/`; nothing is hardcoded outside configuration sections at the top of each script.

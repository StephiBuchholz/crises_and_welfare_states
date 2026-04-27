#!/usr/bin/env python3
"""
step3_intercoder_reliability.py

Evaluates intercoder reliability between two or more coders (human gold standard
and/or LLM output) using Krippendorff's alpha and Cohen's kappa. on measures,
see: Nili et al. 2020: https://www.sciencedirect.com/science/article/pii/S0268401219308564#bib0090 )

Supports multiple input formats via pluggable adapters:
  - "gs"  : top-level JSON array, labels stored under the key "gs_labels" [concerns manual goldstandard]
  - "llm" : {"run_metadata": {...}, "entries": [...]}, labels under "llm_labels" [concerns llm-labelled datasets]

All label variables are treated as nominal. For date variables the exact date
string (YYYY-MM-DD) is compared; "na" is a valid category (deliberate "not
applicable" code, not treated as missing data). A label key that is entirely
absent from an entry is treated as truly missing (excluded from Krippendorff's
coincidence count; Cohen's kappa is computed only over entries where both coders
provided a rating).

FOR EXTERNAL USERS
------------------
This script is designed to be used without modifying the source code. Define
your datasets, variables, and measures in a JSON config file and pass it via
--config. DEFAULT_DATASETS, VARIABLE_SCHEMA, and MEASURES at the top of this
script are the project's own defaults and do not need to be touched.

USAGE
-----
    python step3_intercoder_reliability.py                   # runs on DEFAULT_DATASETS (project's own gold standard:
                                                             # germany_cov_sample_20_labelled_sb.json vs.
                                                             # 2026-04-26_germany_cov_sample_20_llm_gpt-4.1-mini_v1_zero_shot.json;
                                                             # all 13 variables, both measures, output to data/gold_standard/)
    python step3_intercoder_reliability.py --config cfg.json # intended entry point for external users and one-off comparisons:
                                                             # cfg.json may contain any subset of:
                                                             #   "datasets"       : list of dataset dicts (replaces DEFAULT_DATASETS)
                                                             #   "variable_schema": {var_name: "date"|"nominal"} (replaces VARIABLE_SCHEMA)
                                                             #   "measures"       : list of measure names (replaces MEASURES)
                                                             #   "output_dir"     : path string (replaces OUTPUT_DIR)
                                                             # keys not present fall back to the defaults in this script.
    python step3_intercoder_reliability.py --output out.json # override output path only, keep all other defaults

EXTENDING
---------

go through --config cf.json (see above) to make different runs. no script alteration needed. script can be altered, though:

  - Add a new input format: implement load_<format>(path) -> (entries_dict, metadata)
    and register it in LOADERS.
  - Add a new measure: implement compute_<measure>(...) and add its name to
    MEASURES plus a call site in evaluate().
  - Add non-nominal Krippendorff's alpha (ordinal, interval, ratio): the formula
    α = 1 - D_o/D_e is identical across levels; only the distance function changes
    (nominal: binary 0/1; interval: (v_k-v_l)²; ratio: ((v_k-v_l)/(v_k+v_l))²;
    ordinal: rank-based). refactor krippendorff_alpha_nominal into a general
    krippendorff_alpha(data, metric="nominal") that dispatches to the right
    distance function; no changes needed elsewhere.
  - Add a new dataset to the project's default run: append an entry to DEFAULT_DATASETS.
  - Add new variable: new variable to be ICR-rated: add to VARIABLE_SCHEMA

DEPENDENCIES
------------
    pip install scikit-learn     # for Cohen's kappa
    Krippendorff's alpha is implemented inline (no extra package needed).
"""

# imports

import argparse
import json
from collections import defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

from sklearn.metrics import cohen_kappa_score

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

DEFAULT_DATASETS = [
    {
        "path": str(
            PROJECT_ROOT / "data/gold_standard/germany_cov_sample_20_labelled_sb.json"
        ),
        "format": "gs",
        "coder": "sb",
        "dataset_id": "germany_cov_gs_sb",  # choose sth close to file name
    },
    {
        "path": str(
            PROJECT_ROOT
            / "data/gold_standard/2026-04-26_germany_cov_sample_20_llm_gpt-4.1-mini_v1_zero_shot.json"
        ),
        "format": "llm",
        "coder": "gpt-4.1-mini",
        "dataset_id": "germany_cov_llm_gpt41mini_v1_zeroshot",  # choose sth close to file name
    },
]

# Which variables to evaluate and whether they are "date" or "nominal".
# Both are treated as nominal for agreement purposes; "date" only affects
# how values are normalized (date strings stripped of time components).
VARIABLE_SCHEMA: dict[str, str] = {
    "legally_effective": "date",
    "leg_eff_terminate": "date",
    "legally_effective_2": "date",
    "leg_eff_terminate_2": "date",
    "art_leg_eff_2": "nominal",
    "legally_effective_3": "date",
    "leg_eff_terminate_3": "date",
    "art_leg_eff_3": "nominal",
    "social_policy_field_1": "nominal",
    "social_policy_field_2": "nominal",
    "social_policy_field_3": "nominal",
    "social_policy_field_4": "nominal",
    "crisis_ref": "nominal",
}

# Per-format key aliases: if the canonical variable name is absent, fall back
# to the alias. Only affects lookup; the canonical name is always used in output. This results from a naming-mistake I made.
KEY_ALIASES: dict[str, dict[str, str]] = {
    "gs": {
        # Older entries store the first policy field under the legacy key.
        "social_policy_field_1": "social_policy_field",
    }
}

# Measures to compute. Remove or add names here; each must have a corresponding
# call site in evaluate().
MEASURES = ["krippendorff_alpha", "cohen_kappa"]

OUTPUT_DIR = PROJECT_ROOT / "data/classifications/germany"

# ─── SENTINEL ────────────────────────────────────────────────────────────────

_MISSING = object()  # coder did not provide any rating for this unit


# ─── LOADERS (one per format) ─────────────────────────────────────────────────


def load_gs(path: Path) -> tuple[dict, dict]:
    """Load a manual gold-standard file (top-level list, labels under gs_labels)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    entries = {}
    for item in data:
        eid = item["id"]
        raw_labels = item.get("gs_labels", {})
        entries[eid] = {
            "id": eid,
            "title": item.get("title", ""),
            "labels": {k: v["value"] for k, v in raw_labels.items()},
        }
    return entries, {"format": "gs", "path": str(path)}


def load_llm(path: Path) -> tuple[dict, dict]:
    """Load an LLM run file ({"run_metadata": ..., "entries": [...]}, labels under llm_labels)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    run_meta = data.get("run_metadata", {})
    entries = {}
    for item in data.get("entries", []):
        eid = item["id"]
        raw_labels = item.get("llm_labels", {})
        entries[eid] = {
            "id": eid,
            "title": item.get("title", ""),
            "labels": {k: v["value"] for k, v in raw_labels.items()},
        }
    return entries, {"format": "llm", "path": str(path), "run_metadata": run_meta}


LOADERS = {
    "gs": load_gs,
    "llm": load_llm,
}


# ─── LABEL RESOLUTION & NORMALIZATION ─────────────────────────────────────────


def resolve_raw(labels: dict, canonical: str, fmt: str) -> Any:
    """
    Return the raw value for canonical variable name, checking aliases if needed.
    Returns _MISSING if neither the canonical key nor any alias exists.
    """
    if canonical in labels:
        return labels[canonical]
    alias = KEY_ALIASES.get(fmt, {}).get(canonical)
    if alias and alias in labels:
        return labels[alias]
    return _MISSING


def normalize(value: Any, var_type: str) -> str | None:
    """
    Normalize a raw label value to a canonical string.
    Returns None if value is _MISSING (coder did not rate this unit at all).
    Returns "na" for deliberate not-applicable codings.
    """
    if value is _MISSING:
        return None
    if value is None:
        return "na"
    s = str(value).strip().lower()
    if s in ("", "none", "null"):
        return "na"
    if var_type == "date" and "t" in s:
        s = s.split("t")[0]
    return s


# ─── MEASURES ─────────────────────────────────────────────────────────────────


def krippendorff_alpha_nominal(reliability_data: list[list[str | None]]) -> float:
    """
    Krippendorff's alpha for nominal data.

    reliability_data: list of coders; each element is a list of values aligned
    by unit. None means the coder did not rate that unit (excluded from the
    coincidence count). String "na" is a valid category.

    Formula: α = 1 – D_o / D_e  (Krippendorff 2004, nominal metric)
    """
    n_coders = len(reliability_data)
    n_units = len(reliability_data[0]) if reliability_data else 0

    coincidence: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for i in range(n_units):
        rated = [
            reliability_data[k][i]
            for k in range(n_coders)
            if reliability_data[k][i] is not None
        ]
        m = len(rated)
        if m < 2:
            continue
        # Iterate over all ordered coder pairs (k≠l) — this correctly populates
        # both the diagonal (same-category pairs) and off-diagonal entries.
        for ki in range(m):
            for li in range(m):
                if ki != li:
                    coincidence[rated[ki]][rated[li]] += 1.0 / (m - 1)

    if not coincidence:
        return float("nan")

    categories = sorted(
        set(coincidence) | {b for row in coincidence.values() for b in row}
    )
    total = sum(coincidence[a][b] for a in categories for b in categories)
    if total == 0:
        return float("nan")

    # Observed disagreement: off-diagonal mass / total
    D_o = (
        sum(coincidence[a][b] for a in categories for b in categories if a != b) / total
    )

    # Expected disagreement from marginals
    marginals = {a: sum(coincidence[a][b] for b in categories) for a in categories}
    D_e = sum(
        marginals[a] * marginals[b] for a in categories for b in categories if a != b
    ) / (total * (total - 1))

    if D_e == 0:
        return 1.0 if D_o == 0 else float("nan")

    return 1.0 - D_o / D_e


def cohen_kappa_pair(vals_a: list[str], vals_b: list[str]) -> float:
    """
    Cohen's kappa for one pair of coders. Operates on the subset of units where
    both coders provided a non-None value. "na" is treated as a valid category.
    """
    pairs = [(a, b) for a, b in zip(vals_a, vals_b) if a is not None and b is not None]
    if len(pairs) < 2:
        return float("nan")
    a_vals, b_vals = zip(*pairs)
    if len(set(a_vals) | set(b_vals)) == 1:
        # All identical: kappa is undefined (or 1 by convention); sklearn raises
        return 1.0 if list(a_vals) == list(b_vals) else float("nan")
    try:
        return float(cohen_kappa_score(list(a_vals), list(b_vals)))
    except Exception:
        return float("nan")


# ─── CORE EVALUATION ──────────────────────────────────────────────────────────


def evaluate(
    datasets: list[dict], variable_schema: dict[str, str], measures: list[str]
) -> dict:
    """
    Run intercoder reliability evaluation.

    Parameters
    ----------
    datasets : list of dicts with keys: path, format, coder, dataset_id
    variable_schema : {variable_name: "date" | "nominal"}
    measures : list of measure names to compute

    Returns
    -------
    Full results dict (suitable for converting into json).
    """
    # ── Load datasets ──────────────────────────────────────────────────────────
    loaded = []
    for ds in datasets:
        loader = LOADERS[ds["format"]]
        entries, meta = loader(Path(ds["path"]))
        loaded.append(
            {
                "dataset_id": ds["dataset_id"],
                "coder": ds["coder"],
                "format": ds["format"],
                "path": ds["path"],
                "source_metadata": meta,
                "entries": entries,
            }
        )

    # ── Common entries ─────────────────────────────────────────────────────────
    id_sets = [set(d["entries"]) for d in loaded]
    common_ids = sorted(id_sets[0].intersection(*id_sets[1:]))
    entries_only_in = {
        d["dataset_id"]: sorted(id_sets[i] - set(common_ids))
        for i, d in enumerate(loaded)
    }

    # ── Per-variable analysis ──────────────────────────────────────────────────
    variable_results: dict[str, dict] = {}

    for var, var_type in variable_schema.items():
        # Build aligned value lists (one per coder, None = truly missing)
        coder_vals: list[list[str | None]] = []
        for d in loaded:
            vals = []
            for eid in common_ids:
                raw = resolve_raw(d["entries"][eid]["labels"], var, d["format"])
                vals.append(normalize(raw, var_type))
            coder_vals.append(vals)

        n = len(common_ids)

        # Per-coder stats
        na_counts = {
            d["coder"]: sum(1 for v in coder_vals[i] if v == "na")
            for i, d in enumerate(loaded)
        }
        missing_counts = {
            d["coder"]: sum(1 for v in coder_vals[i] if v is None)
            for i, d in enumerate(loaded)
        }

        # Agreements: over entries where all coders have a non-None value
        fully_rated = [
            j
            for j in range(n)
            if all(coder_vals[c][j] is not None for c in range(len(loaded)))
        ]
        n_fully_rated = len(fully_rated)
        n_agree = sum(
            1
            for j in fully_rated
            if len({coder_vals[c][j] for c in range(len(loaded))}) == 1
        )

        # Per-entry detail
        per_entry = []
        for j, eid in enumerate(common_ids):
            vals_by_coder = {d["coder"]: coder_vals[i][j] for i, d in enumerate(loaded)}
            rated_vals = [v for v in vals_by_coder.values() if v is not None]
            agree = len(set(rated_vals)) == 1 if len(rated_vals) > 1 else None
            per_entry.append(
                {
                    "id": eid,
                    "title": loaded[0]["entries"][eid].get("title", ""),
                    "values": vals_by_coder,
                    "agree": agree,
                }
            )

        var_res: dict[str, Any] = {
            "variable": var,
            "type": var_type,
            "n_entries": n,
            "n_fully_rated": n_fully_rated,
            "per_coder_na_count": na_counts,
            "per_coder_missing_count": missing_counts,
            "n_agreements": n_agree,
            "agreement_rate": n_agree / n_fully_rated if n_fully_rated else None,
            "per_entry": per_entry,
        }

        if "krippendorff_alpha" in measures:
            var_res["krippendorff_alpha"] = krippendorff_alpha_nominal(coder_vals)

        if "cohen_kappa" in measures:
            if len(loaded) == 2:
                var_res["cohen_kappa"] = cohen_kappa_pair(coder_vals[0], coder_vals[1])
            else:
                var_res["cohen_kappa_pairwise"] = {
                    f"{loaded[i]['coder']}_vs_{loaded[j]['coder']}": cohen_kappa_pair(
                        coder_vals[i], coder_vals[j]
                    )
                    for i, j in combinations(range(len(loaded)), 2)
                }

        variable_results[var] = var_res

    # ── Assemble output ────────────────────────────────────────────────────────
    return {
        "evaluation_date": str(date.today()),
        "measures": measures,
        "datasets": [
            {
                "dataset_id": d["dataset_id"],
                "coder": d["coder"],
                "format": d["format"],
                "path": d["path"],
                "source_metadata": d["source_metadata"],
            }
            for d in loaded
        ],
        "n_common_entries": len(common_ids),
        "common_entry_ids": common_ids,
        "entries_only_in": entries_only_in,
        "variable_results": variable_results,
    }


# ─── SUMMARY PRINT ────────────────────────────────────────────────────────────


def _fmt(val: Any, digits: int = 3) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        if val != val:  # NaN
            return "NaN"
        return f"{val:.{digits}f}"
    return str(val)


def print_summary(results: dict) -> None:
    coders = [d["coder"] for d in results["datasets"]]
    print(f"\nIntercoder reliability — {results['evaluation_date']}")
    print(f"Coders : {', '.join(coders)}")
    print(f"Entries: {results['n_common_entries']} common")
    print(f"Measures: {', '.join(results['measures'])}\n")

    header = f"{'Variable':<28} {'Type':<8} {'N':>4} {'Agree%':>7} {'α':>7} {'κ':>7}  NA counts"
    print(header)
    print("─" * len(header))

    for var, res in results["variable_results"].items():
        raw_rate = res.get("agreement_rate")
        rate_str = f"{raw_rate:.0%}" if raw_rate is not None else "—"
        alpha = _fmt(res.get("krippendorff_alpha"))
        kappa = _fmt(res.get("cohen_kappa"))
        na_str = " / ".join(str(res["per_coder_na_count"].get(c, "?")) for c in coders)
        print(
            f"{var:<28} {res['type']:<8} {res['n_fully_rated']:>4} {rate_str:>7} {alpha:>7} {kappa:>7}  na={na_str}"
        )


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Intercoder reliability evaluation.")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to a JSON config file with keys: datasets, variable_schema, measures, output_dir",
    )
    parser.add_argument(
        "--output", type=str, help="Output JSON file path (default: auto-generated)"
    )
    args = parser.parse_args()

    datasets = DEFAULT_DATASETS
    variable_schema = VARIABLE_SCHEMA
    measures = MEASURES
    output_dir = OUTPUT_DIR

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
        datasets = cfg.get("datasets", datasets)
        variable_schema = cfg.get("variable_schema", variable_schema)
        measures = cfg.get("measures", measures)
        if "output_dir" in cfg:
            output_dir = Path(cfg["output_dir"])

    results = evaluate(datasets, variable_schema, measures)

    if args.output:
        out_path = Path(args.output)
    else:
        today = date.today().isoformat()
        coder_tag = "_vs_".join(ds["coder"] for ds in datasets)
        out_path = output_dir / f"{today}_intercoder_reliability_{coder_tag}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"Results saved → {out_path}")

    print_summary(results)


if __name__ == "__main__":
    main()

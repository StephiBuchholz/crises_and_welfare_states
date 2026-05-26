#!/usr/bin/env python3
"""
step4_evaluate.py

Evaluation pipeline: LLM classification results vs. human gold standard.
Outputs CSV tables and PNG plots to 4_analysis/results/.

Steps:
    1  Compliance      — parse-ability and field-validity checks
    2  Accuracy        — multi-label SPF F1, exact match, binary crisis_ref F1
    3  Alpha           — Krippendorff's alpha (LLM vs human)
    4  Confusion       — per-model confusion-matrix heatmaps (best prompt by macro F1)
    5  Factorial       — decomposition by 4 binary prompt dimensions

Usage:
    python step4_evaluate.py               # all steps
    python step4_evaluate.py --steps 1 2   # specific steps
"""

import argparse
import json
import re
import warnings
from pathlib import Path

import krippendorff
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import MultiLabelBinarizer

# ── PATHS ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold_standard"
    / "germany_2008-2015_2019-2022_gs_sample_68_2026-05-24_labelled_sb_labelled_sb_labelled_sb.json"
)
CLASSIF_DIR = PROJECT_ROOT / "data" / "classifications" / "germany"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

# ── SCHEMA ─────────────────────────────────────────────────────────────────────
VALID_SPF = [
    "unemployment",
    "family/children",
    "housing",
    "disability",
    "retirement",
    "survivors",
    "sickness/health/care",
    "labour market",
    "taxes",
]
VALID_SPF_SET = set(VALID_SPF)
VALID_CRISIS_REF = {0, 1}

BATCH_REQUIRED = [
    "summary",
    "legally_effective",
    "leg_eff_terminate",
    "legally_effective_2",
    "leg_eff_terminate_2",
    "art_leg_eff_2",
    "legally_effective_3",
    "leg_eff_terminate_3",
    "art_leg_eff_3",
    "social_policy_field_1",
    "social_policy_field_2",
    "crisis_ref",
]
SINGLE_REQUIRED = ["social_policy_field_1", "social_policy_field_2"]

# Minimum compliance rate (0–1) required to compute accuracy/alpha metrics.
# Runs below this threshold are reported as NaN to avoid misleading numbers
# from tiny compliant subsets.
MIN_COMPLIANCE = 0.80

# ── DATA LOADING ───────────────────────────────────────────────────────────────

def load_gold(path: Path = GOLD_PATH) -> dict[str, dict]:
    """
    Load gold standard. Returns {entry_id: gs_labels_dict}.
    Skips entries that were never annotated (no gs_labels key) and prints a warning.
    """
    entries = json.loads(path.read_text(encoding="utf-8"))
    result, missing = {}, []
    for e in entries:
        if "gs_labels" in e:
            result[e["id"]] = e["gs_labels"]
        else:
            missing.append(e["id"])
    if missing:
        print(f"  WARNING: {len(missing)} entry/entries have no gs_labels and are excluded: {missing}")
    return result


_RUN_RE = re.compile(r"_llm_(.+?)_(v\d+_.+?)(?:\.partial)?\.json$")


def load_runs(classif_dir: Path = CLASSIF_DIR) -> list[dict]:
    """
    Load all classification run files, preferring complete .json over .partial.json.
    Returns a list of run dicts with keys: model, prompt_key, entries_by_id, is_partial.
    """
    runs: list[dict] = []
    seen: set[tuple] = set()

    for p in sorted(classif_dir.glob("*.json")):
        if p.name.endswith(".partial.json"):
            continue
        m = _RUN_RE.search(p.name)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        seen.add(key)
        runs.append(_load_run(p, is_partial=False))

    for p in sorted(classif_dir.glob("*.partial.json")):
        m = _RUN_RE.search(p.name)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        if key not in seen:
            runs.append(_load_run(p, is_partial=True))

    return runs


def _load_run(path: Path, is_partial: bool) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data["run_metadata"]
    return {
        "model":         meta["model"],
        "prompt_key":    meta["prompt_key"],
        "entries_by_id": {e["id"]: e.get("llm_labels") for e in data["entries"]},
        "is_partial":    is_partial,
        "filename":      path.name,
    }


# ── PROMPT DIMENSION PARSING ───────────────────────────────────────────────────

def parse_dims(prompt_key: str) -> dict[str, int]:
    """Parse the 4 binary dimensions from a prompt key string."""
    return {
        "shot":  1 if "few_shot" in prompt_key else 0,   # 0=zero-shot, 1=few-shot
        "scope": 1 if "single"   in prompt_key else 0,   # 0=batch,     1=single
        "def":   0 if "nodef"    in prompt_key else 1,   # 0=no-def,    1=def
        "jus":   0 if "nojus"    in prompt_key else 1,   # 0=no-jus,    1=jus
    }


def required_fields(prompt_key: str) -> list[str]:
    dims = parse_dims(prompt_key)
    base = SINGLE_REQUIRED.copy() if dims["scope"] else BATCH_REQUIRED.copy()
    if dims["jus"]:
        base = base + ["spf_justification"]
    return base


# ── VALUE EXTRACTION ───────────────────────────────────────────────────────────

def _val(labels: dict | None, field: str):
    """Extract the .value from a provenance-wrapped label dict, or None."""
    if not labels:
        return None
    raw = labels.get(field)
    if raw is None:
        return None
    return raw["value"] if isinstance(raw, dict) else raw


def _spf_set(labels: dict | None) -> set | None:
    """
    Return {spf1, spf2} minus 'na'. Returns None if labels are missing or
    social_policy_field_1 is not a valid category (entry is non-compliant for SPF).
    """
    f1 = _val(labels, "social_policy_field_1")
    if f1 not in VALID_SPF_SET:
        return None
    s = {f1}
    f2 = _val(labels, "social_policy_field_2")
    if f2 in VALID_SPF_SET:
        s.add(f2)
    return s


def _crisis(labels: dict | None) -> int | None:
    """Extract crisis_ref as int {0,1}, normalising int or string inputs."""
    v = _val(labels, "crisis_ref")
    if isinstance(v, int) and v in VALID_CRISIS_REF:
        return v
    if isinstance(v, str) and v in {"0", "1"}:
        return int(v)
    return None


# ── STEP 1: COMPLIANCE ─────────────────────────────────────────────────────────

def _compliance_rate(run: dict, gold_ids: list[str]) -> float:
    return sum(
        _is_compliant(run["entries_by_id"].get(gid), run["prompt_key"])
        for gid in gold_ids
    ) / len(gold_ids)


def _is_compliant(labels: dict | None, prompt_key: str) -> bool:
    """True iff labels contains all required fields with valid values."""
    if labels is None:
        return False
    for f in required_fields(prompt_key):
        if f not in labels:
            return False
    if _val(labels, "social_policy_field_1") not in VALID_SPF_SET:
        return False
    spf2 = _val(labels, "social_policy_field_2")
    if spf2 not in VALID_SPF_SET | {"na"}:
        return False
    if not parse_dims(prompt_key)["scope"]:   # batch: also validate crisis_ref
        if _crisis(labels) is None:
            return False
    return True


def step1_compliance(
    runs: list[dict], gold_ids: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
        heatmap_df:  model × prompt DataFrame of compliance rates (0–1)
        summary_df:  per-model mean/min/max across prompts
    """
    n = len(gold_ids)
    records = []
    for run in runs:
        n_valid = sum(
            _is_compliant(run["entries_by_id"].get(gid), run["prompt_key"])
            for gid in gold_ids
        )
        records.append(
            {"model": run["model"], "prompt_key": run["prompt_key"], "compliance": n_valid / n}
        )
    df = pd.DataFrame(records)
    heatmap = df.pivot(index="model", columns="prompt_key", values="compliance").round(3)
    summary = df.groupby("model")["compliance"].agg(
        mean="mean", min="min", max="max"
    ).round(3)
    return heatmap, summary


# ── STEP 2: ACCURACY ───────────────────────────────────────────────────────────

def step2_accuracy(
    runs: list[dict], gold: dict[str, dict]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns:
        macro_f1_df:    model × prompt, macro F1 on SPF multi-label
        exact_match_df: model × prompt, exact set-match rate on SPF
        crisis_f1_df:   model × prompt, binary F1 for crisis_ref (NaN for single prompts)
        per_cat_df:     per-category F1 for best prompt per model
    """
    gold_ids  = list(gold.keys())
    gold_sets = {gid: _spf_set(gls) for gid, gls in gold.items()}
    gold_cr   = {gid: _crisis(gls)  for gid, gls in gold.items()}

    mlb = MultiLabelBinarizer(classes=VALID_SPF)
    mlb.fit([[c] for c in VALID_SPF])

    records_spf  = []
    records_cr   = []
    per_cat_rows = []

    for run in runs:
        eid  = run["entries_by_id"]
        dims = parse_dims(run["prompt_key"])

        if _compliance_rate(run, gold_ids) < MIN_COMPLIANCE:
            records_spf.append(
                {"model": run["model"], "prompt_key": run["prompt_key"],
                 "macro_f1": np.nan, "exact_match": np.nan}
            )
            per_cat_rows.append(
                {"model": run["model"], "prompt_key": run["prompt_key"],
                 **{c: np.nan for c in VALID_SPF}}
            )
            records_cr.append(
                {"model": run["model"], "prompt_key": run["prompt_key"],
                 "f1": np.nan, "precision": np.nan, "recall": np.nan}
            )
            continue

        # SPF: restrict to entries where both gold and prediction are valid
        valid_spf = [
            (gold_sets[g], _spf_set(eid.get(g)))
            for g in gold_ids
            if gold_sets[g] is not None and _spf_set(eid.get(g)) is not None
        ]
        if valid_spf:
            gs, ps = zip(*valid_spf)
            yg = mlb.transform(gs)
            yp = mlb.transform(ps)
            macro_f1    = float(f1_score(yg, yp, average="macro",  zero_division=0))
            exact_match = float(np.mean([g == p for g, p in zip(gs, ps)]))
            per_cat_f1  = list(f1_score(yg, yp, average=None, zero_division=0))
        else:
            macro_f1 = exact_match = np.nan
            per_cat_f1 = [np.nan] * len(VALID_SPF)

        records_spf.append(
            {"model": run["model"], "prompt_key": run["prompt_key"],
             "macro_f1": macro_f1, "exact_match": exact_match}
        )
        per_cat_rows.append(
            {"model": run["model"], "prompt_key": run["prompt_key"],
             **dict(zip(VALID_SPF, per_cat_f1))}
        )

        # Crisis ref (batch prompts only)
        if dims["scope"] == 0:
            valid_cr = [
                (gold_cr[g], _crisis(eid.get(g)))
                for g in gold_ids
                if gold_cr[g] is not None and _crisis(eid.get(g)) is not None
            ]
            if valid_cr:
                gc, pc = zip(*valid_cr)
                cr_f1  = float(f1_score(gc, pc, zero_division=0))
                cr_pre = float(precision_score(gc, pc, zero_division=0))
                cr_rec = float(recall_score(gc, pc, zero_division=0))
            else:
                cr_f1 = cr_pre = cr_rec = np.nan
        else:
            cr_f1 = cr_pre = cr_rec = np.nan

        records_cr.append(
            {"model": run["model"], "prompt_key": run["prompt_key"],
             "f1": cr_f1, "precision": cr_pre, "recall": cr_rec}
        )

    df_spf = pd.DataFrame(records_spf)
    macro_f1_df    = df_spf.pivot(index="model", columns="prompt_key", values="macro_f1").round(3)
    exact_match_df = df_spf.pivot(index="model", columns="prompt_key", values="exact_match").round(3)
    crisis_f1_df   = pd.DataFrame(records_cr).pivot(
        index="model", columns="prompt_key", values="f1"
    ).round(3)

    # Per-category F1 for each model's best-performing prompt (by macro F1)
    df_pcat  = pd.DataFrame(per_cat_rows)
    best_idx = df_spf.groupby("model")["macro_f1"].idxmax()
    best     = df_spf.loc[best_idx][["model", "prompt_key"]]
    per_cat_df = (
        df_pcat.merge(best, on=["model", "prompt_key"])
        .set_index(["model", "prompt_key"])[VALID_SPF]
        .round(3)
    )

    return macro_f1_df, exact_match_df, crisis_f1_df, per_cat_df


# ── STEP 3: KRIPPENDORFF'S ALPHA ──────────────────────────────────────────────

def _alpha(data: np.ndarray) -> float:
    """Compute Krippendorff's alpha on a (2, n_items) array; NaN = missing."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return float(krippendorff.alpha(data, level_of_measurement="nominal"))
        except Exception:
            return np.nan


def step3_alpha(
    runs: list[dict], gold: dict[str, dict]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns:
        alpha_spf_bin_df: model × prompt, avg binary alpha across 9 SPF categories
        alpha_spf_nom_df: model × prompt, nominal alpha on social_policy_field_1 alone
        alpha_cr_df:      model × prompt, binary alpha on crisis_ref (NaN for single prompts)
    """
    gold_ids  = list(gold.keys())
    gold_sets = {gid: _spf_set(gls) for gid, gls in gold.items()}
    gold_f1   = {gid: _val(gls, "social_policy_field_1") for gid, gls in gold.items()}
    gold_cr   = {gid: _crisis(gls) for gid, gls in gold.items()}
    cat_codes = {c: float(i) for i, c in enumerate(VALID_SPF)}

    records_bin = []
    records_nom = []
    records_cr  = []

    for run in runs:
        eid  = run["entries_by_id"]
        dims = parse_dims(run["prompt_key"])

        if _compliance_rate(run, gold_ids) < MIN_COMPLIANCE:
            records_bin.append({"model": run["model"], "prompt_key": run["prompt_key"], "alpha": np.nan})
            records_nom.append({"model": run["model"], "prompt_key": run["prompt_key"], "alpha": np.nan})
            records_cr.append( {"model": run["model"], "prompt_key": run["prompt_key"], "alpha": np.nan})
            continue

        # Binary alpha per SPF category, then average
        cat_alphas = []
        for cat in VALID_SPF:
            g_row, p_row = [], []
            for gid in gold_ids:
                gs = gold_sets.get(gid)
                ps = _spf_set(eid.get(gid))
                g_row.append(1.0 if gs is not None and cat in gs else (np.nan if gs is None else 0.0))
                p_row.append(1.0 if ps is not None and cat in ps else (np.nan if ps is None else 0.0))
            cat_alphas.append(_alpha(np.array([g_row, p_row])))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            avg_bin = float(np.nanmean(cat_alphas))

        # Nominal alpha on social_policy_field_1 alone
        g_nom, p_nom = [], []
        for gid in gold_ids:
            gv = gold_f1.get(gid)
            pv = _val(eid.get(gid), "social_policy_field_1")
            g_nom.append(cat_codes.get(gv, np.nan))
            p_nom.append(cat_codes.get(pv, np.nan))
        nom_alpha = _alpha(np.array([g_nom, p_nom]))

        records_bin.append({"model": run["model"], "prompt_key": run["prompt_key"], "alpha": avg_bin})
        records_nom.append({"model": run["model"], "prompt_key": run["prompt_key"], "alpha": nom_alpha})

        # Crisis ref alpha (batch prompts only)
        if dims["scope"] == 0:
            g_cr, p_cr = [], []
            for gid in gold_ids:
                gv = gold_cr.get(gid)
                pv = _crisis(eid.get(gid))
                g_cr.append(float(gv) if gv is not None else np.nan)
                p_cr.append(float(pv) if pv is not None else np.nan)
            cr_alpha = _alpha(np.array([g_cr, p_cr]))
        else:
            cr_alpha = np.nan
        records_cr.append({"model": run["model"], "prompt_key": run["prompt_key"], "alpha": cr_alpha})

    def _pivot(recs):
        return (
            pd.DataFrame(recs)
            .pivot(index="model", columns="prompt_key", values="alpha")
            .round(3)
        )

    return _pivot(records_bin), _pivot(records_nom), _pivot(records_cr)


# ── STEP 4: CONFUSION MATRICES ─────────────────────────────────────────────────

def step4_confusion(
    macro_f1_df: pd.DataFrame,
    runs: list[dict],
    gold: dict[str, dict],
    plots_dir: Path,
) -> None:
    """Plot one confusion matrix per model using its best prompt (by macro F1)."""
    gold_ids = list(gold.keys())

    for model in macro_f1_df.index:
        row = macro_f1_df.loc[model].dropna()
        if row.empty:
            continue
        best = row.idxmax()
        run  = next((r for r in runs if r["model"] == model and r["prompt_key"] == best), None)
        if run is None:
            continue

        y_true, y_pred = [], []
        for gid in gold_ids:
            gt = _val(gold[gid], "social_policy_field_1")
            pt = _val(run["entries_by_id"].get(gid), "social_policy_field_1")
            if gt in VALID_SPF_SET and pt in VALID_SPF_SET:
                y_true.append(gt)
                y_pred.append(pt)

        if not y_true:
            continue

        cm = confusion_matrix(y_true, y_pred, labels=VALID_SPF)
        fig, ax = plt.subplots(figsize=(11, 8))
        sns.heatmap(
            cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=VALID_SPF, yticklabels=VALID_SPF, ax=ax,
        )
        safe = model.replace("/", "-")
        ax.set_title(f"{safe}\nbest prompt: {best}", fontsize=9)
        ax.set_ylabel("Gold standard")
        ax.set_xlabel("LLM prediction")
        plt.xticks(rotation=45, ha="right", fontsize=8)
        plt.yticks(rotation=0, fontsize=8)
        plt.tight_layout()
        out = plots_dir / f"confusion_{safe}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"    saved: {out.name}")


# ── STEP 5: FACTORIAL DECOMPOSITION ───────────────────────────────────────────

def step5_factorial(
    macro_f1_df: pd.DataFrame, alpha_spf_bin_df: pd.DataFrame
) -> pd.DataFrame:
    """
    For each of 4 binary prompt dimensions, compute average macro F1 and average
    SPF binary alpha across all models, split by dimension value (0 vs 1).
    Mirrors Atreja et al. (2025) Tables 4 and 5.
    """
    f1_long  = macro_f1_df.reset_index().melt(id_vars="model", var_name="prompt_key", value_name="macro_f1")
    alp_long = alpha_spf_bin_df.reset_index().melt(id_vars="model", var_name="prompt_key", value_name="alpha")
    df = f1_long.merge(alp_long, on=["model", "prompt_key"])

    for dim in ("shot", "scope", "def", "jus"):
        df[dim] = df["prompt_key"].apply(lambda k, d=dim: parse_dims(k)[d])

    dim_labels = {
        "shot":  ("zero-shot", "few-shot"),
        "scope": ("batch",     "single"),
        "def":   ("no-def",    "def"),
        "jus":   ("no-jus",    "jus"),
    }
    rows = []
    for dim, (lbl0, lbl1) in dim_labels.items():
        for val, lbl in ((0, lbl0), (1, lbl1)):
            sub = df[df[dim] == val]
            rows.append({
                "dimension":     dim,
                "value":         lbl,
                "avg_macro_f1":  round(float(sub["macro_f1"].mean()), 3),
                "avg_alpha_spf": round(float(sub["alpha"].mean()),    3),
            })
    return pd.DataFrame(rows).set_index(["dimension", "value"])


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="LLM evaluation pipeline (Steps 1–5)")
    parser.add_argument(
        "--steps", nargs="+", type=int, choices=range(1, 6),
        default=list(range(1, 6)), metavar="N",
        help="Steps to run, e.g. --steps 1 2 3",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    plots_dir = RESULTS_DIR / "plots"
    plots_dir.mkdir(exist_ok=True)

    print("Loading gold standard …")
    gold     = load_gold(GOLD_PATH)
    gold_ids = list(gold.keys())
    print(f"  {len(gold_ids)} entries")

    print("Loading classification runs …")
    runs      = load_runs(CLASSIF_DIR)
    n_partial = sum(r["is_partial"] for r in runs)
    print(f"  {len(runs)} runs  ({n_partial} partial)")

    macro_f1_df = exact_match_df = crisis_f1_df = per_cat_df = None
    alpha_spf_bin_df = alpha_spf_nom_df = alpha_cr_df = None

    if 1 in args.steps:
        print("\n--- Step 1: Compliance ---")
        heatmap, summary = step1_compliance(runs, gold_ids)
        heatmap.to_csv(RESULTS_DIR / "compliance_heatmap.csv")
        summary.to_csv(RESULTS_DIR / "compliance_summary.csv")
        print(summary.to_string())

    if 2 in args.steps:
        print("\n--- Step 2: Accuracy ---")
        macro_f1_df, exact_match_df, crisis_f1_df, per_cat_df = step2_accuracy(runs, gold)
        macro_f1_df.to_csv(RESULTS_DIR / "spf_macro_f1.csv")
        exact_match_df.to_csv(RESULTS_DIR / "spf_exact_match.csv")
        crisis_f1_df.to_csv(RESULTS_DIR / "crisis_ref_f1.csv")
        per_cat_df.to_csv(RESULTS_DIR / "spf_per_category_f1_best_prompt.csv")
        print("  Macro F1 mean across prompts, per model:")
        print(macro_f1_df.mean(axis=1).round(3).to_string())

    if 3 in args.steps:
        print("\n--- Step 3: Krippendorff's alpha ---")
        alpha_spf_bin_df, alpha_spf_nom_df, alpha_cr_df = step3_alpha(runs, gold)
        alpha_spf_bin_df.to_csv(RESULTS_DIR / "alpha_spf_binary.csv")
        alpha_spf_nom_df.to_csv(RESULTS_DIR / "alpha_spf_nominal.csv")
        alpha_cr_df.to_csv(RESULTS_DIR  / "alpha_crisis_ref.csv")
        print("  Avg binary SPF alpha across prompts, per model:")
        print(alpha_spf_bin_df.mean(axis=1).round(3).to_string())

    if 4 in args.steps:
        print("\n--- Step 4: Confusion matrices ---")
        if macro_f1_df is None:
            macro_f1_df, *_ = step2_accuracy(runs, gold)
        step4_confusion(macro_f1_df, runs, gold, plots_dir)

    if 5 in args.steps:
        print("\n--- Step 5: Factorial decomposition ---")
        if macro_f1_df is None:
            macro_f1_df, *_ = step2_accuracy(runs, gold)
        if alpha_spf_bin_df is None:
            alpha_spf_bin_df, *_ = step3_alpha(runs, gold)
        factorial = step5_factorial(macro_f1_df, alpha_spf_bin_df)
        factorial.to_csv(RESULTS_DIR / "factorial_decomposition.csv")
        print(factorial.to_string())

    print(f"\nDone. Results saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()

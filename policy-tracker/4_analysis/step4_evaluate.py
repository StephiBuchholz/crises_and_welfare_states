#!/usr/bin/env python3
"""
step4_evaluate.py

Evaluation pipeline: LLM classification results vs. human gold standard.
Outputs CSV tables and PNG plots to data/analysis_results/.

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
RESULTS_DIR = PROJECT_ROOT / "data" / "analysis_results"


def _dataset_tag(gold_path: Path) -> str:
    parts   = gold_path.stem.split("_")
    country = parts[0][:3]
    periods = [p for p in parts if re.fullmatch(r"\d{4}-\d{4}", p)]
    return "_".join([country] + periods)

DATASET_TAG = _dataset_tag(GOLD_PATH)

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
    "none",
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

# Models whose runs are excluded from load_runs() until fully ready.
# Remove entries here once a model's outputs are complete.
EXCLUDE_MODELS: set[str] = set()

# Word counts of each prompt template (system + user, excluding {full_text}).
# Computed once from step2_promptdesigns.py; hardcoded here to avoid a runtime import.
PROMPT_WORD_COUNTS: dict[str, int] = {
    "v1_zero_shot_batch_nodef_nojus":   275,
    "v2_zero_shot_single_nodef_nojus":  127,
    "v3_zero_shot_batch_def_nojus":    1069,
    "v4_zero_shot_single_def_nojus":    921,
    "v5_zero_shot_batch_nodef_jus":     330,
    "v6_zero_shot_single_nodef_jus":    182,
    "v7_zero_shot_batch_def_jus":      1124,
    "v8_zero_shot_single_def_jus":      976,
    "v9_few_shot_batch_nodef_nojus":   2864,
    "v10_few_shot_single_nodef_nojus": 2545,
    "v11_few_shot_batch_def_nojus":    3658,
    "v12_few_shot_single_def_nojus":   3339,
    "v13_few_shot_batch_nodef_jus":    2919,
    "v14_few_shot_single_nodef_jus":   2600,
    "v15_few_shot_batch_def_jus":      3713,
    "v16_few_shot_single_def_jus":     3394,
}

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
        if any(excl in p.name for excl in EXCLUDE_MODELS):
            continue
        m = _RUN_RE.search(p.name)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        seen.add(key)
        runs.append(_load_run(p, is_partial=False))

    for p in sorted(classif_dir.glob("*.partial.json")):
        if any(excl in p.name for excl in EXCLUDE_MODELS):
            continue
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


# ── STEP 1b: COMPLIANCE DIAGNOSIS ─────────────────────────────────────────────

def compliance_diagnosis(
    runs: list[dict], gold_ids: list[str], threshold: float = 0.70
) -> pd.DataFrame:
    """
    For runs with compliance < threshold, return failure-reason rates per
    (model, prompt_key): fraction of policies triggering each check.
    Checks are independent/marginal; no_output entries skip the field checks.
    invalid_crisis_ref is NaN for single-scope prompts. Sorted by compliance ascending.
    """
    n = len(gold_ids)
    records = []
    for run in runs:
        comp = _compliance_rate(run, gold_ids)
        if comp >= threshold:
            continue
        eid      = run["entries_by_id"]
        dims     = parse_dims(run["prompt_key"])
        req      = required_fields(run["prompt_key"])
        is_batch = dims["scope"] == 0

        no_output = missing_fields = invalid_spf = invalid_cr = 0
        for gid in gold_ids:
            labels = eid.get(gid)
            if labels is None:
                no_output += 1
                continue
            if any(f not in labels for f in req):
                missing_fields += 1
            spf1 = _val(labels, "social_policy_field_1")
            spf2 = _val(labels, "social_policy_field_2")
            if spf1 not in VALID_SPF_SET or spf2 not in VALID_SPF_SET | {"na"}:
                invalid_spf += 1
            if is_batch and _crisis(labels) is None:
                invalid_cr += 1

        records.append({
            "model":              run["model"],
            "prompt_key":         run["prompt_key"],
            "compliance":         round(comp, 3),
            "no_output":          round(no_output / n, 3),
            "missing_fields":     round(missing_fields / n, 3),
            "invalid_spf":        round(invalid_spf / n, 3),
            "invalid_crisis_ref": round(invalid_cr / n, 3) if is_batch else np.nan,
        })

    return (
        pd.DataFrame(records)
        .sort_values("compliance")
        .set_index(["model", "prompt_key"])
    )


# ── STEP 2: ACCURACY ───────────────────────────────────────────────────────────

_JACCARD_BUCKET_VALS = [0.0, 1 / 3, 0.5, 1.0]
_JACCARD_BUCKET_COLS = ["J=0", "J=1/3", "J=1/2", "J=1"]


def step2_accuracy(runs: list[dict], gold: dict[str, dict]) -> dict:
    """
    Returns a dict with keys:
        macro_f1_df       — model × prompt, macro F1 on SPF multi-label
        macro_prec_df     — model × prompt, macro precision on SPF
        macro_rec_df      — model × prompt, macro recall on SPF
        jaccard_df        — model × prompt, mean per-doc Jaccard similarity
        jaccard_buckets_df — model × prompt × {J=0, J=1/3, J=1/2, J=1} counts
        crisis_f1_df      — model × prompt, binary F1 for crisis_ref (NaN for single)
        per_cat_f1_df     — per-category F1 for best prompt per model
        per_cat_prec_df   — per-category precision for best prompt per model
        per_cat_rec_df    — per-category recall for best prompt per model
    """
    gold_ids  = list(gold.keys())
    gold_sets = {gid: _spf_set(gls) for gid, gls in gold.items()}
    gold_cr   = {gid: _crisis(gls)  for gid, gls in gold.items()}

    mlb = MultiLabelBinarizer(classes=VALID_SPF)
    mlb.fit([[c] for c in VALID_SPF])

    records_spf       = []
    records_cr        = []
    per_cat_rows      = []
    jaccard_bkt_rows  = []

    for run in runs:
        eid  = run["entries_by_id"]
        dims = parse_dims(run["prompt_key"])
        base = {"model": run["model"], "prompt_key": run["prompt_key"]}

        if _compliance_rate(run, gold_ids) < MIN_COMPLIANCE:
            records_spf.append({
                **base, "macro_f1": np.nan, "macro_prec": np.nan,
                "macro_rec": np.nan, "jaccard": np.nan,
            })
            per_cat_rows.append({
                **base,
                **{c: np.nan for c in VALID_SPF},
                **{f"prec_{c}": np.nan for c in VALID_SPF},
                **{f"rec_{c}":  np.nan for c in VALID_SPF},
            })
            jaccard_bkt_rows.append({**base, **{col: np.nan for col in _JACCARD_BUCKET_COLS}})
            records_cr.append({**base, "f1": np.nan, "precision": np.nan, "recall": np.nan})
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

            per_cat_f1   = f1_score(yg, yp, average=None, zero_division=np.nan)
            per_cat_prec = precision_score(yg, yp, average=None, zero_division=np.nan)
            per_cat_rec  = recall_score(yg, yp, average=None, zero_division=np.nan)

            macro_f1   = float(np.nanmean(per_cat_f1))
            macro_prec = float(np.nanmean(per_cat_prec))
            macro_rec  = float(np.nanmean(per_cat_rec))

            jac_vals = [len(g & p) / len(g | p) for g, p in zip(gs, ps)]
            jaccard  = float(np.mean(jac_vals))

            bkt = {col: 0 for col in _JACCARD_BUCKET_COLS}
            for jv in jac_vals:
                col = _JACCARD_BUCKET_COLS[
                    min(range(len(_JACCARD_BUCKET_VALS)),
                        key=lambda i: abs(_JACCARD_BUCKET_VALS[i] - jv))
                ]
                bkt[col] += 1
        else:
            macro_f1 = macro_prec = macro_rec = jaccard = np.nan
            bkt = {col: np.nan for col in _JACCARD_BUCKET_COLS}
            per_cat_f1 = per_cat_prec = per_cat_rec = [np.nan] * len(VALID_SPF)

        records_spf.append({
            **base, "macro_f1": macro_f1, "macro_prec": macro_prec,
            "macro_rec": macro_rec, "jaccard": jaccard,
        })
        per_cat_rows.append({
            **base,
            **dict(zip(VALID_SPF, per_cat_f1)),
            **{f"prec_{c}": v for c, v in zip(VALID_SPF, per_cat_prec)},
            **{f"rec_{c}":  v for c, v in zip(VALID_SPF, per_cat_rec)},
        })
        jaccard_bkt_rows.append({**base, **bkt})

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

        records_cr.append({**base, "f1": cr_f1, "precision": cr_pre, "recall": cr_rec})

    df_spf = pd.DataFrame(records_spf)

    def _pivot(col):
        return df_spf.pivot(index="model", columns="prompt_key", values=col).round(3)

    macro_f1_df   = _pivot("macro_f1")
    macro_prec_df = _pivot("macro_prec")
    macro_rec_df  = _pivot("macro_rec")
    jaccard_df    = _pivot("jaccard")

    crisis_f1_df = pd.DataFrame(records_cr).pivot(
        index="model", columns="prompt_key", values="f1"
    ).round(3)

    jaccard_buckets_df = (
        pd.DataFrame(jaccard_bkt_rows)
        .set_index(["model", "prompt_key"])
    )

    # Per-category metrics for each model's best prompt (by macro F1)
    df_pcat  = pd.DataFrame(per_cat_rows)
    best_idx = df_spf.groupby("model")["macro_f1"].idxmax()
    best     = df_spf.loc[best_idx][["model", "prompt_key"]]

    def _best_cat(cols):
        return (
            df_pcat.merge(best, on=["model", "prompt_key"])
            .set_index(["model", "prompt_key"])[cols]
            .round(3)
        )

    per_cat_f1_df   = _best_cat(VALID_SPF)
    per_cat_prec_df = _best_cat([f"prec_{c}" for c in VALID_SPF]).rename(
        columns={f"prec_{c}": c for c in VALID_SPF}
    )
    per_cat_rec_df  = _best_cat([f"rec_{c}"  for c in VALID_SPF]).rename(
        columns={f"rec_{c}": c for c in VALID_SPF}
    )

    return {
        "macro_f1_df":        macro_f1_df,
        "macro_prec_df":      macro_prec_df,
        "macro_rec_df":       macro_rec_df,
        "jaccard_df":         jaccard_df,
        "jaccard_buckets_df": jaccard_buckets_df,
        "crisis_f1_df":       crisis_f1_df,
        "per_cat_f1_df":      per_cat_f1_df,
        "per_cat_prec_df":    per_cat_prec_df,
        "per_cat_rec_df":     per_cat_rec_df,
    }


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
    file_suffix: str = "",
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
        out = plots_dir / f"confusion_{safe}{file_suffix}.png"
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


# ── STEP 2b: JACCARD BUCKET TABLE (best prompt per model) ─────────────────────

def jaccard_bucket_table(
    macro_f1_df: pd.DataFrame, runs: list[dict], gold: dict[str, dict]
) -> pd.DataFrame:
    """
    For each model's best prompt (by macro F1), compute per-document Jaccard
    similarity and return a bucket distribution table with counts and percentages.
    Possible Jaccard values for label sets of size 1–2: 0, 1/3, 1/2, 1.
    """
    gold_ids  = list(gold.keys())
    gold_sets = {gid: _spf_set(gls) for gid, gls in gold.items()}

    _BUCKET_VALS = [0.0, 1 / 3, 0.5, 1.0]
    _BUCKET_KEYS = ["no_overlap", "partial_1_3", "partial_1_2", "exact_match"]

    rows = []
    for model in macro_f1_df.index:
        row = macro_f1_df.loc[model].dropna()
        if row.empty:
            continue
        best_prompt = row.idxmax()
        run = next(
            (r for r in runs if r["model"] == model and r["prompt_key"] == best_prompt),
            None,
        )
        if run is None:
            continue

        eid = run["entries_by_id"]
        bkt = {k: 0 for k in _BUCKET_KEYS}
        n = 0
        for gid in gold_ids:
            gs = gold_sets.get(gid)
            ps = _spf_set(eid.get(gid))
            if gs is None or ps is None:
                continue
            jv  = len(gs & ps) / len(gs | ps)
            key = _BUCKET_KEYS[
                min(range(len(_BUCKET_VALS)), key=lambda i: abs(_BUCKET_VALS[i] - jv))
            ]
            bkt[key] += 1
            n += 1

        partial = bkt["partial_1_2"] + bkt["partial_1_3"]
        rows.append({
            "model":                   model,
            "best_prompt":             best_prompt,
            "n_evaluated":             n,
            "exact_match":             bkt["exact_match"],
            "partial_overlap_1_2":     bkt["partial_1_2"],
            "partial_overlap_1_3":     bkt["partial_1_3"],
            "partial_overlap":         partial,
            "no_overlap":              bkt["no_overlap"],
            "exact_match_pct":         round(bkt["exact_match"] / n * 100, 1) if n else np.nan,
            "partial_overlap_1_2_pct": round(bkt["partial_1_2"] / n * 100, 1) if n else np.nan,
            "partial_overlap_1_3_pct": round(bkt["partial_1_3"] / n * 100, 1) if n else np.nan,
            "partial_overlap_pct":     round(partial / n * 100, 1) if n else np.nan,
            "no_overlap_pct":          round(bkt["no_overlap"] / n * 100, 1) if n else np.nan,
        })

    return pd.DataFrame(rows).set_index("model")


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

    macro_f1_df = None
    alpha_spf_bin_df = alpha_spf_nom_df = alpha_cr_df = None

    if 1 in args.steps:
        print("\n--- Step 1: Compliance ---")
        heatmap, summary = step1_compliance(runs, gold_ids)
        heatmap.to_csv(RESULTS_DIR / "compliance_heatmap.csv")
        summary.to_csv(RESULTS_DIR / "compliance_summary.csv")
        print(summary.to_string())

    if 2 in args.steps:
        print("\n--- Step 2: Accuracy ---")
        acc = step2_accuracy(runs, gold)
        macro_f1_df       = acc["macro_f1_df"]
        macro_prec_df     = acc["macro_prec_df"]
        macro_rec_df      = acc["macro_rec_df"]
        jaccard_df        = acc["jaccard_df"]
        jaccard_buckets_df = acc["jaccard_buckets_df"]
        crisis_f1_df      = acc["crisis_f1_df"]
        per_cat_f1_df     = acc["per_cat_f1_df"]
        per_cat_prec_df   = acc["per_cat_prec_df"]
        per_cat_rec_df    = acc["per_cat_rec_df"]

        macro_f1_df.to_csv(RESULTS_DIR / "spf_macro_f1.csv")
        macro_prec_df.to_csv(RESULTS_DIR / "spf_macro_precision.csv")
        macro_rec_df.to_csv(RESULTS_DIR / "spf_macro_recall.csv")
        jaccard_df.to_csv(RESULTS_DIR / "spf_jaccard.csv")
        jaccard_buckets_df.to_csv(RESULTS_DIR / "spf_jaccard_buckets.csv")
        crisis_f1_df.to_csv(RESULTS_DIR / "crisis_ref_f1.csv")
        per_cat_f1_df.to_csv(RESULTS_DIR / "spf_per_category_f1_best_prompt.csv")
        per_cat_prec_df.to_csv(RESULTS_DIR / "spf_per_category_precision_best_prompt.csv")
        per_cat_rec_df.to_csv(RESULTS_DIR / "spf_per_category_recall_best_prompt.csv")

        jac_bkt = jaccard_bucket_table(macro_f1_df, runs, gold)
        jac_bkt.to_csv(RESULTS_DIR / "spf_jaccard_buckets_best_prompt.csv")

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
            macro_f1_df = step2_accuracy(runs, gold)["macro_f1_df"]
        step4_confusion(macro_f1_df, runs, gold, plots_dir)

    if 5 in args.steps:
        print("\n--- Step 5: Factorial decomposition ---")
        if macro_f1_df is None:
            macro_f1_df = step2_accuracy(runs, gold)["macro_f1_df"]
        if alpha_spf_bin_df is None:
            alpha_spf_bin_df, *_ = step3_alpha(runs, gold)
        factorial = step5_factorial(macro_f1_df, alpha_spf_bin_df)
        factorial.to_csv(RESULTS_DIR / "factorial_decomposition.csv")
        print(factorial.to_string())

    print(f"\nDone. Results saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()

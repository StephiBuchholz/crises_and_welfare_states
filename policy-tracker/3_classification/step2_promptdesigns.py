#!/usr/bin/env python3
"""
step2_promptdesigns.py

all 16 prompt variants for the 2×2×2×2 factorial classification experiment.

this script is automatically run when running step2_classify_llm.py which imports the prompt templates from here.

dimensions
----------
zero_shot / few_shot  : whether labeled examples precede the task
batch / single        : batch — all tasks (dates + social policy field + crisis_ref);
                        single — social policy field (SPF) classification only
nodef / def           : nodef — label list only; def — full class definitions
nojus / jus           : nojus — classification only; jus — + written justification

exports
-------
PROMPTS      dict[str, {"system": str, "user": str}]
               user template receives keyword args: {title}, {date_published}, {full_text}
OUTPUT_SCHEMAS dict[str, dict]
               plain JSON Schema object per prompt key (model-agnostic);
               model-specific wrapping (e.g. OpenAI response_format) is handled in step3
"""

#x ─── COUNTRY CONFIGURATION ────────────────────────────────────────────────────
#feeds into system prompt
COUNTRY_ADJECTIVE = "German"              # possessive adjective, e.g. "French", "British"
LEGISLATION_SOURCE = "Bundesgesetzblatt"  # official publication name for this country
DOCUMENT_TYPES    = "Gesetze, Verordnungen, Bekanntmachungen"  # official word for the given document types in local language
# ──────────────────────────────────────────────────────────────────────────────

# ─── SPF OPTIONS ──────────────────────────────────────────────────────────────

_SPF_OPTIONS = [
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

# ─── SPF CLASS DEFINITIONS (from codebook) ────────────────────────────────────────────────────

_SPF_CLASS_DEF = """\
Unemployment — Regards benefits, measures, and/or social security contributions that:
- replace in whole or in part income lost by a worker due to the loss of gainful employment;
- provide a subsistence (or better) income to persons entering or re-entering the labour market;
- compensate for the loss of earnings due to partial unemployment;
- replace in whole or in part income lost by an older worker who retires from gainful employment before the reference retirement age because of job reductions for economic reasons;
- contribute to the cost of training or re-training people looking for employment;
- help unemployed persons meet the cost of travelling or relocating to obtain employment;
- provide help and relief by providing appropriate goods and services;
- provide for jobseekers who do not qualify for unemployment insurance benefits, or whose entitlement to these benefits is low or has expired;
- provide for a universal basic income that substitutes or supplements unemployment protection.

Family/children — Regards benefits, measures, and/or social security contributions that:
- provide financial support to households for bringing up children;
- provide financial assistance to people who support relatives other than children;
- provide social services specifically designed to assist and protect the family, particularly children;
- expand the availability of or enhance access to child care facilities;
- regulate child alimony between parents.
Excludes: measures concretely designed as a tax cut or tax advantage for families with children or for those providing assistance to a care-dependent relative. These fall under "taxes."

Housing — Regards benefits, measures, and/or social security contributions that:
- help households meet the cost of housing, for example through rent benefits, social housing, or benefits to owner-occupiers;
- subsidise heating, water, and electricity expenditures;
- aim to end homelessness through "housing first" policies;
- increase the availability of social housing.

Disability — Regards benefits, measures, and/or social security contributions that:
- provide an income to persons whose full or partial inability to engage in economic activity or to lead a normal life, due to a physical or mental impairment that is likely to be permanent or to persist beyond a minimum prescribed period, impairs their ability to work and earn beyond a minimum level laid down by legislation;
- provide allowances designed to cover disability-related costs or needs.
Excludes: short-term sickness benefits, which fall under "sickness/health/care." Also excludes benefits for persons providing care to incapacitated individuals, which fall under "family/children."

Retirement — Regards benefits, measures, and/or social security contributions that:
- provide a replacement income when the aged person retires from the labour market;
- guarantee a certain income when a person has reached a prescribed age;
- regulate private retirement provisions.
Excludes: benefits and contributions for medical care and elderly care, which fall under "sickness/health/care."

Survivors — Regards benefits, measures, and/or social security contributions that:
- provide a temporary or permanent income to people who have suffered from the loss of a spouse or next-of-kin, usually when the latter represented the main breadwinner for the beneficiary;
- compensate survivors for funeral costs or for any hardship caused by the death of a family member;
- provide goods and services to eligible survivors.

Sickness/health/care — Regards benefits, measures, and/or social security contributions that:
- replace in whole or in part loss of earnings during temporary inability to work due to sickness or injury;
- provide medical care in the framework of social protection to maintain, restore, or improve the health of the people protected;
- provide goods or services specifically required by the personal or social circumstances of the elderly (elderly care is classified here rather than under "retirement");
- concern the institutional setup of health insurance systems, both public and private.
Excludes: long-term disability benefits, which fall under "disability." Also excludes benefits for persons providing care to incapacitated individuals, which fall under "family/children."

Labour market — Regards benefits, measures, and/or social security contributions that:
- regulate the terms and conditions of employment (wages, minimum wages, working hours, non-standard and atypical employment, employment exempt from social security contributions, illegal employment);
- actively intervene to expand labour force participation and facilitate (re-)employment — through employment services, direct job creation, start-up incentives, or hiring and wage subsidies targeted at specific groups — including by enforcing the conditionality of benefits on active job search and participation in employability measures.

Taxes — Regards all personal income taxes payable in respect of employment and self-employment earnings, including measures that alter tax rates, thresholds, deductions, or credits for these earnings.
Also includes: measures concretely designed as a tax cut or tax advantage for families with children or for those providing assistance to a care-dependent relative. These are classified here rather than under "family/children.\""""

# ─── FEW-SHOT EXAMPLES (placeholder) ─────────────────────────────────────────

# TODO: Replace with 2–3 labeled examples drawn from the gold standard.
# For batch variants (all tasks), each example must include the full JSON output
# (dates, social_policy_field_1/2, crisis_ref, and justification if applicable).
# For single variants (SPF only), each example includes only social_policy_field_1/2
# (and justification if applicable).
#
# Suggested format per example (repeat, separated by "---"):
#   Title     : <law title>
#   Published : <yyyy-mm-dd>
#
#   <abbreviated legislative text>
#
#   Classification: <JSON object>
#   ---
_FEW_SHOT_EXAMPLES = """\
──── EXAMPLES ────
[TODO: insert 2–3 labeled examples here — one per "---" separator.
 Each example: Title / Published / abbreviated text / Classification JSON.
 For batch prompts include all (!) output fields; for single prompts include SPF fields only.]
──────────────────"""

# ─── SHARED SYSTEM PROMPT ─────────────────────────────────────────────────────

_SYSTEM = (
    f"You are an expert in {COUNTRY_ADJECTIVE} social policy legislation. "
    f"You classify legislative texts ({DOCUMENT_TYPES}) from the {LEGISLATION_SOURCE} "
    "according to a structured codebook. "
    "Return your classifications as a JSON object with the exact fields specified."
)

# ─── REUSABLE TEXT SECTIONS ───────────────────────────────────────────────────

_SEC_SUM = (
    "──── SUMMARY ────\n"
    "Provide 1-2 brief sentences to pointedly summarize this legal policy text in English."
)

_SEC_DATE = """\
──── DATE EXTRACTION ────
legally_effective   : Date the law enters into force. Use the BGBl publication
                      date if no explicit date is stated. Format: yyyy-mm.
leg_eff_terminate   : Date legal effect terminates. "na" if not specified.
legally_effective_2 : Second entry-into-force date if the law specifies multiple. "na" if not applicable.
leg_eff_terminate_2 : Termination date for legally_effective_2. "na" if not applicable.
art_leg_eff_2       : Article/paragraph number that legally_effective_2 refers to
                      (first number + optional letter only, e.g. "4a"). "na" if not applicable.
legally_effective_3 : Third entry-into-force date. "na" if not applicable.
leg_eff_terminate_3 : Termination date for legally_effective_3. "na" if not applicable.
art_leg_eff_3       : Article/paragraph number for legally_effective_3. "na" if not applicable."""

_SEC_SPF_HEAD = (
    "──── SOCIAL POLICY FIELD ────\n"
    "Assign the primary social policy field that the legislative text addresses (social_policy_field_1). "
    "If the text substantively addresses a second, distinct policy field, assign it as social_policy_field_2; "
    'otherwise set social_policy_field_2 to "na".' #head and tail split for flexible combination with jus versus nojus prompts
)

_SEC_SPF_NODEF_TAIL = (
    "Valid values:\n"
    + "\n".join(f'  "{opt}"' for opt in _SPF_OPTIONS) #head and tail tail split for flexible combination with jus versus nojus prompts
)

_SEC_SPF_DEF_TAIL = (
    "Classify according to these class definitions:\n\n"
    + _SPF_CLASS_DEF #head and tail tail split for flexible combination with jus versus nojus prompts
)

_SEC_SPF_NODEF = _SEC_SPF_HEAD + "\n\n" + _SEC_SPF_NODEF_TAIL #prompts with no definitions for spf
_SEC_SPF_DEF   = _SEC_SPF_HEAD + "\n\n" + _SEC_SPF_DEF_TAIL #prompts with definitions for spf

_SEC_CRISIS = """\
──── CRISIS REFERENCE ────
crisis_ref : 1 if the text explicitly references COVID-19/the pandemic or the
             2008 financial/economic crisis; 0 otherwise."""

_SEC_JUS = """\
However, before classifying, you always reason through the social policy field options below, first, in light of the legislative text — considering both the primary field (social_policy_field_1) and, if so, which secondary field applies (social_policy_field_2).
spf_justification : Your reasoning about which social policy field(s) apply. This field precedes social_policy_field_1 and social_policy_field_2 in the output schema."""

_SEC_TEXT = """\
──── LEGISLATIVE TEXT ────
Title     : {title}
Published : {date_published}

{full_text}"""

# ─── COMPOSITION HELPERS ──────────────────────────────────────────────────────


def _join(*parts: str) -> str:
    return "\n\n".join(p for p in parts if p)


def _compose_batch(spf_sec: str, *, few_shot: bool) -> str: #function that composes the batch task prompts, used later in build-step
    return _join(
        _FEW_SHOT_EXAMPLES if few_shot else "",
        "Classify the legislative text below according to these codebook rules.",
        _SEC_SUM,
        _SEC_DATE,
        spf_sec,
        _SEC_CRISIS,
        _SEC_TEXT,
    )


def _compose_single(spf_sec: str, *, few_shot: bool) -> str: #function that composes the single task prompts, used later in build-step
    return _join(
        _FEW_SHOT_EXAMPLES if few_shot else "",
        spf_sec,
        _SEC_TEXT,
    )


# ─── OUTPUT SCHEMA BUILDER ────────────────────────────────────────────────────
# Builds plain JSON Schema objects (model-agnostic). Step 3 scripts wrap these
# in whatever format their target API requires (e.g. OpenAI response_format).


def _make_schema(*, batch: bool, jus: bool) -> dict:
    props: dict = {}
    req: list = []

    if batch:
        props["summary"] = {"type": "string", "description": "1-2 sentence English summary of the policy text"}
        req.append("summary")

        date_fields: dict[str, str] = {
            "legally_effective":   "yyyy-mm",
            "leg_eff_terminate":   "yyyy-mm or na",
            "legally_effective_2": "yyyy-mm or na",
            "leg_eff_terminate_2": "yyyy-mm or na",
            "art_leg_eff_2":       "article number or na",
            "legally_effective_3": "yyyy-mm or na",
            "leg_eff_terminate_3": "yyyy-mm or na",
            "art_leg_eff_3":       "article number or na",
        }
        for k, desc in date_fields.items():
            props[k] = {"type": "string", "description": desc}
        req.extend(date_fields)

    if jus:
        props["spf_justification"] = {
            "type": "string",
            "description": "reasoning about which social policy field(s) apply, before classifying",
        }
        req.append("spf_justification")

    props["social_policy_field_1"] = {"type": "string", "enum": _SPF_OPTIONS}
    props["social_policy_field_2"] = {"type": "string", "enum": _SPF_OPTIONS + ["na"]}
    req += ["social_policy_field_1", "social_policy_field_2"]

    if batch:
        props["crisis_ref"] = {"type": "integer", "enum": [0, 1]}
        req.append("crisis_ref")

    return {
        "type": "object",
        "properties": props,
        "required": req,
        "additionalProperties": False,
    }


# ─── BUILD ALL VARIANTS ────────────────────────────────────────────────────

# (version_prefix, few_shot, batch, use_def, jus)
_VARIANTS = [
    ("v1",  False, True,  False, False),
    ("v2",  False, False, False, False),
    ("v3",  False, True,  True,  False),
    ("v4",  False, False, True,  False),
    ("v5",  False, True,  False, True),
    ("v6",  False, False, False, True),
    ("v7",  False, True,  True,  True),
    ("v8",  False, False, True,  True),
    ("v9",  True,  True,  False, False),
    ("v10", True,  False, False, False),
    ("v11", True,  True,  True,  False),
    ("v12", True,  False, True,  False),
    ("v13", True,  True,  False, True),
    ("v14", True,  False, False, True),
    ("v15", True,  True,  True,  True),
    ("v16", True,  False, True,  True),
]


def _build_variants() -> tuple[dict, dict]: #iterates over all rows (prompt variations!) in _VARIANTS, builds individual spf_sec (with or without reasoning and with/out def) and then passes it into _compose_batch or _compose_single.
    prompts: dict = {}
    schemas: dict = {}
    for num, few_shot, batch, use_def, jus in _VARIANTS:
        shot  = "few_shot"  if few_shot else "zero_shot"
        scope = "batch"     if batch    else "single"
        defs  = "def"       if use_def  else "nodef"
        just  = "jus"       if jus      else "nojus"
        key   = f"{num}_{shot}_{scope}_{defs}_{just}"

        tail = _SEC_SPF_DEF_TAIL if use_def else _SEC_SPF_NODEF_TAIL
        spf  = _join(_SEC_SPF_HEAD, _SEC_JUS, tail) if jus else (
               _SEC_SPF_DEF if use_def else _SEC_SPF_NODEF)
        user = (
            _compose_batch(spf, few_shot=few_shot)
            if batch
            else _compose_single(spf, few_shot=few_shot)
        )
        prompts[key] = {"system": _SYSTEM, "user": user}
        schemas[key] = _make_schema(batch=batch, jus=jus)
    return prompts, schemas


PROMPTS, OUTPUT_SCHEMAS = _build_variants()


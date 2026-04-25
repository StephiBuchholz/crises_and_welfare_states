# Codebook — Crisis Policy Tracker

Covers all variables coded in the gold standard and used in LLM classification prompts.
Classification is applied at the level of individual legislative texts (laws, executive orders, announcements).

---

## Date variables

All dates are extracted verbatim from the legislative text.

| Variable              | Type           | Rule                                                                                                                                                                                |
| --------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `legally_effective`   | date           | Date the law enters into force (Inkrafttreten). Use BGBl publication date if no explicit date is stated. Format: `yyyy-mm-dd`.                                                      |
| `leg_eff_terminate`   | date or `na`   | Date the legal effect terminates (Außerkrafttreten). `na` if not specified. Format: `yyyy-mm-dd`.                                                                                   |
| `legally_effective_2` | date or `na`   | Second entry-into-force date, if the law specifies multiple. `na` if not applicable. Format: `yyyy-mm-dd`.                                                                          |
| `leg_eff_terminate_2` | date or `na`   | Termination date corresponding to `legally_effective_2`. `na` if not applicable.                                                                                                    |
| `art_leg_eff_2`       | number or `na` | Article or paragraph number that `legally_effective_2` refers to. Only highest level, mumber and letter only (ex.: "4a" for "Article 4a, 1c)"), no symbols. `na` if not applicable. |
| `legally_effective_3` | date or `na`   | Third entry-into-force date. `na` if not applicable. Format: `yyyy-mm-dd`.                                                                                                          |
| `leg_eff_terminate_3` | date or `na`   | Termination date corresponding to `legally_effective_3`. `na` if not applicable.                                                                                                    |
| `art_leg_eff_3`       | number or `na` | Article or paragraph number that `legally_effective_3` refers to. Only highest level, mumber and letter only (ex.: "4a" for "Article 4a, 1c)"), no symbols. `na` if not applicable. |

---

## Crisis reference (`crisis_ref`)

**Type:** boolean (0 / 1)

Does the law explicitly reference the crisis that motivated it?

- Code `1` (yes) if the text names COVID-19, coronavirus, pandemic etc. or the 2008 financial/economic crisis (Finanzkrise / Wirtschaftskrise) etc..
- Code `0` (no) if no such explicit reference appears.

---

## Social policy field (`social_policy_field_1` — `_4`)

**Type:** categorical

Assign the social policy domain(s) the law primarily addresses. Assign at least one (`social_policy_field_1`, mandatory). Assign up to three additional domains (`_2`–`_4`) if the law clearly addresses multiple fields. Use `na` for `_2`–`_4` when not applicable.

Use `mix` only as a last resort for large omnibus laws that cannot be meaningfully assigned to specific fields. Use parsimoneously. Use `false positive` (only available for `_1`) when the law does not address social policy or welfare at all and was incorrectly included in the sample. Use parsimoneously.

### Categories

**1. Unemploy benefits / job retention / activation**

"Unemployment insurance benefits are designed to support the income and facilitate effective job search by smoothing consumption of people who lost a previous job. Insurance benefits are typically linked to previous earnings and require previous employment record and social contribution payments. This distinguishes them from unemployment assistance benefits."

short-time work (Kurzarbeitergeld)

activation:
conditionality for eligibility, requirements of job search, measures for job market reintegration, job training programmes, targeted hiring subsidies, behavior monitoring [https://link.springer.com/article/10.1186/s40173-015-0032-y]

**2. Social assistance and housing benefits**

"Jobseekers who do not qualify for unemployment insurance benefits, or whose entitlement to these benefits are low or have expired, can claim unemployment assistance (UA) and/or social assistance or minimum-income (SA) benefits. These benefits are
usually means-tested, that is, receipt is conditional on individual and/or family income and
assets. In addition, entitlement to some UA benefits may depend on past employment or
contribution records"

housing benefit (HB) rules for people living in privately
rented accommodation. Benefit entitlements for other housing tenures are not simulated.
For example, subsidies for the construction of housing, purchases of owner-occupied
housing, favourable interest payments, or in-kind support for those in social housing, etc.
are not included." "rent assistance "
Specific cash support for housing-related expenditures other than rent,
e.g. heating and water bills, are outside the scope of the model.

universal basic income

**3. Family benefits**

- "income support programmes that are conditional on
  having children or adult dependants"
- "‘homecare’ allowances"
- "parental leave"
- "maternity or birth-related benefits"
- "benefit provisions for lone parents and state-substituted alimony"
- child care-centre fees and childcare benefits

**4. Social-security contributions**

- contributions to the following:
  - retirement insurance
  - long-term care insurance
  - health insurance
  -

**5. In-work / employ-conditional benefits**

conditional on the following key requirements:  
• Being employed on a regular basis with a standard employment contract;
• Working a certain number of hours and/or earning more than a certain minimum.

**6. Retirement benefits**

- pensions
- retirement benefits
- early-retirement benefits

**7. Sickness benefits**

- disability benefits
- long-covid?

**8. Taxes**

any tax related policy

**9. Crisis-induced one-time subsidies**

Energiekostenzuschuss

**10. Labour regulation**

- minimum wage
  .

**11. Mix** _(last resort only)_

<!-- add definition -->

**12. False positive** _(only valid for `social_policy_field_1`)_

<!-- add definition -->

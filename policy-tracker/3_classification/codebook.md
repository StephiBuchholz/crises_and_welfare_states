# Codebook — Crisis Policy Tracker

Covers all variables coded in the gold standard and used in LLM classification prompts.
Classification is applied at the level of individual legislative texts (laws, executive orders, announcements).

---

## Summary

**Type:** string

Provide 1-2 brief sentences to pointedly summarize this legal policy text in English.

## Date variables

All dates are extracted verbatim from the legislative text.

| Variable              | Type           | Rule                                                                                                                                                                                |
| --------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `legally_effective`   | date           | Date the law enters into force (Inkrafttreten). Use BGBl publication date if no explicit date is stated. Format: `yyyy-mm`.                                                         |
| `leg_eff_terminate`   | date or `na`   | Date the legal effect terminates (Außerkrafttreten). `na` if not specified. Format: `yyyy-mm`.                                                                                      |
| `legally_effective_2` | date or `na`   | Second entry-into-force date, if the law specifies multiple. `na` if not applicable. Format: `yyyy-mm`.                                                                             |
| `leg_eff_terminate_2` | date or `na`   | Termination date corresponding to `legally_effective_2`. `na` if not applicable.                                                                                                    |
| `art_leg_eff_2`       | number or `na` | Article or paragraph number that `legally_effective_2` refers to. Only highest level, number and letter only (ex.: "4a" for "Article 4a, 1c)"), no symbols. `na` if not applicable. |
| `legally_effective_3` | date or `na`   | Third entry-into-force date. `na` if not applicable. Format: `yyyy-mm`.                                                                                                             |
| `leg_eff_terminate_3` | date or `na`   | Termination date corresponding to `legally_effective_3`. `na` if not applicable.                                                                                                    |
| `art_leg_eff_3`       | number or `na` | Article or paragraph number that `legally_effective_3` refers to. Only highest level, number and letter only (ex.: "4a" for "Article 4a, 1c)"), no symbols. `na` if not applicable. |

---

## Crisis reference (`crisis_ref`)

**Type:** boolean (0 / 1)

- Code `1` if the text explicitly references COVID-19/the pandemic or the 2008 financial/economic crisis.
- Code `0` otherwise.

---

## Social policy field (`social_policy_field_1`, `social_policy_field_2`)

**Type:** categorical

Assign the primary social policy domain the law addresses (`social_policy_field_1`, mandatory). If the law substantively addresses a second, distinct domain, assign it as `social_policy_field_2`; otherwise set `social_policy_field_2` to `na`. Only assign the class "none" if the social policy does not relate to any social policy field at all. Only select "none" for social_policy_field_1 if the policy does not relate to social policy at all. In this case, you must set social_policy_field_2 to "na".

### Categories

**1. unemployment**

Regards benefits, measures, and/or social security contributions that:

- replace in whole or in part income lost by a worker due to the loss of gainful employment;
- provide a subsistence (or better) income to persons entering or re-entering the labour market;
- compensate for the loss of earnings due to partial unemployment;
- replace in whole or in part income lost by an older worker who retires from gainful employment before the reference retirement age because of job reductions for economic reasons;
- contribute to the cost of training or re-training people looking for employment;
- help unemployed persons meet the cost of travelling or relocating to obtain employment;
- provide help and relief by providing appropriate goods and services;
- provide for jobseekers who do not qualify for unemployment insurance benefits, or whose entitlement to these benefits is low or has expired;
- provide for a universal basic income that substitutes or supplements unemployment protection.

**2. family/children**

Regards benefits, measures, and/or social security contributions that:

- provide financial support to households for bringing up children;
- provide financial assistance to people who support relatives other than children;
- provide social services specifically designed to assist and protect the family, particularly children;
- expand the availability of or enhance access to child care facilities;
- regulate child alimony between parents.

Excludes: measures concretely designed as a tax cut or tax advantage for families with children or for those providing assistance to a care-dependent relative. These fall under "taxes."

**3. housing**

Regards benefits, measures, and/or social security contributions that:

- help households meet the cost of housing, for example through rent benefits, social housing, or benefits to owner-occupiers;
- subsidise heating, water, and electricity expenditures;
- aim to end homelessness through "housing first" policies;
- increase the availability of social housing.

**4. disability**

Regards benefits, measures, and/or social security contributions that:

- provide an income to persons whose full or partial inability to engage in economic activity or to lead a normal life, due to a physical or mental impairment that is likely to be permanent or to persist beyond a minimum prescribed period, impairs their ability to work and earn beyond a minimum level laid down by legislation;
- provide allowances designed to cover disability-related costs or needs.

Excludes: short-term sickness benefits, which fall under "sickness/health/care." Also excludes benefits for persons providing care to incapacitated individuals, which fall under "family/children."

**5. retirement**

Regards benefits, measures, and/or social security contributions that:

- provide a replacement income when the aged person retires from the labour market;
- guarantee a certain income when a person has reached a prescribed age;
- regulate private retirement provisions.

Excludes: benefits and contributions for medical care and elderly care, which fall under "sickness/health/care."

**6. survivors**

Regards benefits, measures, and/or social security contributions that:

- provide a temporary or permanent income to people who have suffered from the loss of a spouse or next-of-kin, usually when the latter represented the main breadwinner for the beneficiary;
- compensate survivors for funeral costs or for any hardship caused by the death of a family member;
- provide goods and services to eligible survivors.

**7. sickness/health/care**

Regards benefits, measures, and/or social security contributions that:

- replace in whole or in part loss of earnings during temporary inability to work due to sickness or injury;
- provide medical care in the framework of social protection to maintain, restore, or improve the health of the people protected;
- provide goods or services specifically required by the personal or social circumstances of the elderly (elderly care is classified here rather than under "retirement");
- concern the institutional setup of health insurance systems, both public and private.

Excludes: long-term disability benefits, which fall under "disability." Also excludes benefits for persons providing care to incapacitated individuals, which fall under "family/children."

**8. labour market**

Regards benefits, measures, and/or social security contributions that:

- regulate the terms and conditions of employment (wages, minimum wages, working hours, non-standard and atypical employment, employment exempt from social security contributions, illegal employment);
- actively intervene to expand labour force participation and facilitate (re-)employment — through employment services, direct job creation, start-up incentives, or hiring and wage subsidies targeted at specific groups — including by enforcing the conditionality of benefits on active job search and participation in employability measures.

**9. taxes**

Regards all personal income taxes payable in respect of employment and self-employment earnings, including measures that alter tax rates, thresholds, deductions, or credits for these earnings.

Also includes: measures concretely designed as a tax cut or tax advantage for families with children or for those providing assistance to a care-dependent relative. These are classified here rather than under "family/children."

**10. none**

The policy does not concern social policy at all and cannot be matched to any of the other classes.

## SPF justification (`spf_justification`)

**Type:** string

Give a brief justification for your choice on the social policy field categorization and argue why, if so, you assign a second field.

---

## New Social risks (`nsr`)

**Type:** categorical

If any, which New social risks does the policy target?
Definition: New social risks are related to the socioeconomic transformations that have brought post-industrial societies into existence: the tertiarisation of employment, the decline of the standard full-time male worker and the massive entry of women into the labour force. New social risks, as they are understood here, include the following:

Note: Definition at categories derived from Bonoli (2005): https://doi.org/10.1332/0305573054325765

**1. Reconciling work and family life**

Choose when the policy aims to enhance the reconciliation of work and family life, for example due to flexibilisation of working hours, working-from-home, subsidies for mothers providing child care or the enhancement of child care facility access.

**2. Single parenthood**

Choose when the policy targets single parents and their children.

**3. Having a frail relative**

Choose when the policy targets individuals that provide unpaid, informal care to or households with an in-house living frail elderly or disabled person.

**4. Possessing low or obsolete skills**

Choose when the policy targets individuals who are employed in low value added service sectors like retail sales, cleaning, catering or the like where there is little scope for
productivity increases. The individuals are at risk of being paid a poverty wage or being unemployed due to low or obsolete skills.

**5. Insuffiecient social security coverage**

Choose when the policy targets the risk of insufficient social security coverage and welfare due to atypical career patterns or atypical employment, part-time work, non-standard or informal employment.

**6. na**
code na if the policy does not target any new social risk.

---

## NSR justification (`nsr_justification`)

**Type:** string

Give a brief justification for your choice on the new social risk categorization in no more than one sentence.

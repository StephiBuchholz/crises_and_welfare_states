# Pooled Union Evaluation Log
Generated: 2026-10-29

## 1. Input files

| role | file |
|---|---|
| System 1 (cosine similarity) | `germany_2016-2018_cosinesim_final.json` |
| System 2 (BERTopic candidates) | `germany_2016-2018_berttopic_candidates.json` |
| System 2 noise pool | `germany_2016-2018_berttopic_noise_pool.json` |
| BERTopic topic assignments | `germany_2016-2018_berttopic_topic_assignments.json.gz` |
| BERTopic topic info | `germany_2016-2018_berttopic_topic_info.json` |

## 2. §1 — Candidate counts (raw input)

| source | n |
|---|---|
| System 1 (cosine similarity) | 157 |
| System 2 (BERTopic) | 166 |
| System 2 noise pool (topic -1) | 298 |

## 3. §3 — Pooled union overview

| group | n | share |
|---|---|---|
| Both systems (high confidence) | 59 | 23% |
| System 1 only (cosine sim) | 96 | 37% |
| System 2 only (BERTopic) | 105 | 40% |
| **Total** | **260** | **100%** |

## 4. §5a — System 1 only decision (interactive triage)

- Candidates reviewed: 96
- Decisions file (by title): `germany_2016-2018_s1_only_decisions.json`
- Still undecided: 0
- **Policies included: 46**

## 5. §6a — System 2 only decision (topic level)

- Candidates reviewed: 105 across 7 topics
- Topics kept: 7 — topic 1 (fortbildungsabschluss geprüfter, geprüfter, industriemeister, fachrichtung, ausbildungsverordnung berufsausbildung), topic 8 (behindertengleichstellungsrecht bereinigung, auslandstrennungsgeldrecht, auswärtig, ausschluss verfassungsfeindlich, auslandsumzugskostenverordnung europawahlordnung), topic 9 (finanzausgleichsgesetz, finanzausgleichsgesetz ausgleichsjahr, ausgleichsjahr festsetzung, gewerbesteuerumlage gemeindefinanzreformgesetz, festsetzung umlagesatz), topic 11 (zwölfter sozialgesetzbuch, sozialgesetzbuch, nettoentgelte kurzarbeitergeld, grundsicherungs datenabgleichsverordnung, sozialgesetzbuch maßgeblich), topic 14 (aufteilung gemeindeanteil, bekämpfung steuerumgehung, bereich kommunalinvestitionsförderungsgesetz, bundesverfassungsgericht reform, einkommensteuer einkommensteuerschlüsselzahlenermittlungsverordnung), topic 19 (frist sozialgesetzbuch, sozialgesetzbuch künstlersozialabgabe, bundesagentur arbeit, arbeit weiterleitung, anspruch ausländisch), topic 20 (rentenversicherung alterssicherung, landwirt rentenwertbestimmungsverordnung, sozialversicherungsentgeltverordnung, sozialversicherungs rechengrößenverordnung, sozialversicherung sozialversicherungs)
- **Policies included: 105**

## 6. §8 — Final policy set

| group | n |
|---|---|
| Accepted by both systems | 59 |
| Accepted from System 1 only | 46 |
| Accepted from System 2 only | 105 |
| **Final total** | **210** |

## 7. Output file

`germany_2016-2018_final_policy_set.json`

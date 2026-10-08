# Pooled Union Evaluation Log
Generated: 2026-05-24

## 1. Input files

| role | file |
|---|---|
| System 1 (cosine similarity) | `germany_2008-2015_2019-2022_cosinesim_final.json` |
| System 2 (BERTopic candidates) | `germany_2008-2015_2019-2022_berttopic_candidates.json` |
| System 2 noise pool | `germany_2008-2015_2019-2022_berttopic_noise_pool.json` |
| BERTopic topic assignments | `germany_2008-2015_2019-2022_berttopic_topic_assignments.json.gz` |
| BERTopic topic info | `germany_2008-2015_2019-2022_berttopic_topic_info.json` |

## 2. §1 — Candidate counts (raw input)

| source | n |
|---|---|
| System 1 (cosine similarity) | 593 |
| System 2 (BERTopic) | 892 |
| System 2 noise pool (topic -1) | 791 |

## 3. §3 — Pooled union overview

| group | n | share |
|---|---|---|
| Both systems (high confidence) | 345 | 33% |
| System 1 only (cosine sim) | 212 | 20% |
| System 2 only (BERTopic) | 502 | 47% |
| **Total** | **1059** | **100%** |

## 4. §5a — System 1 only decision

- Candidates reviewed: 212
- Row indices included: [0, 5, 7, 11, 13, 14, 15, 23, 24, 25, 26, 31, 33, 35, 38, 40, 46, 51, 53, 56, 61, 62, 63, 70, 74, 75, 80, 82, 83, 89, 96, 97, 100, 102, 104, 105, 107, 114, 117, 119, 123, 125, 126, 128, 129, 130, 133, 137, 140, 141, 144, 145, 148, 150, 151, 152, 153, 155, 158, 160, 161, 163, 165, 166, 168, 168, 170, 171, 172, 173, 174, 176, 178, 180, 181, 191, 195, 198, 205, 206, 207, 208, 210, 211]
- **Policies included: 84**

## 5. §6a — System 2 only decision (topic level)

- Candidates reviewed: 502 across 26 topics
- Topics kept: 14 — topic 7 (meisterprfung, meisterprfung ii, ii, fortbildungsabschluss, anerkannt fortbildungsabschluss), topic 16 (beschftigung, arbeitnehmerentsendegesetz, arbeitszeit, arbeitnehmer, instrument), topic 17 (berufsausbildung, nderung berufsausbildung, technischen, berufsausbildung technischen, technisch), topic 20 (nderung sozialversicherungsentgeltverordnung, sozialversicherungsentgeltverordnung, sozialversicherung, beitragssatz gesetzlich, gesetzlich rentenversicherung), topic 39 (kind, familie, ausbau, bundeselterngeld, elternzeitgesetz), topic 42 (nderung buch, sozialgesetzbuch nderung, buch, buch sozialgesetzbuch, sozialgesetzbuch), topic 86 (bundesausbildungsfrderungsgesetz, aufstiegsfortbildungsfrderungsgesetz, nderung bundesausbildungsfrderungsgesetz, bafgndg, nderung aufstiegsfortbildungsfrderungsgesetz), topic 100 (zwlfter, zwlfter buch, buch sozialgesetzbuch, buch, sozialgesetzbuch), topic 109 (stabilisierung, 2023, 2016, 2022, 2015), topic 121 (gesetzlich rentenversicherung, juli, alterssicherung landwirt, landwirt, alterssicherung), topic 122 (einkommen, bundesversorgungsgesetz, anrechnungsverordnung, 53, einigungsvertrag), topic 125 (nderung sonderurlaubsverordnung, sonderurlaubsverordnung, zwlft nderung, heimaturlaubsverordnung, zwlft), topic 131 (bundesbesoldungsgesetz, 77, 78, 5a, anlage iv), topic 133 (ii, trger, rente, bundesagentur arbeit, zahlung)
- **Policies included: 233**

## 6. §8 — Final policy set

| group | n |
|---|---|
| Accepted by both systems | 345 |
| Accepted from System 1 only | 84 |
| Accepted from System 2 only | 233 |
| **Final total** | **681** |

## 7. Output file

`germany_2008-2015_2019-2022_final_policy_set.json`

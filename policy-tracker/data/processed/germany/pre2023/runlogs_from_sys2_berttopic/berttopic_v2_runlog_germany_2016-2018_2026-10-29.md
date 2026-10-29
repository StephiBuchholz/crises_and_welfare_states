# BERTopic run log (berttopic_v2)

| | |
|---|---|
| date | 2026-10-29 |
| output prefix | `germany_2016-2018` |
| run tag | `berttopic_v2` |

## results

| metric | n |
|---|---|
| total documents | 1165 |
| social-policy topics labelled (yes) | 4 |
| topics labelled mixed | 3 |
| documents reviewed in mixed topics | 87 |
| documents accepted from mixed topics | 25 |
| candidates (System 2) | 166 |
| noise pool | 298 |

## labelled social-policy topics (yes)

| topic_id | count | top words |
|---|---|---|
| 1 | 82 | fortbildungsabschluss geprüfter, geprüfter, industriemeister, fachrichtung, ausbildungsverordnung berufsausbildung, fachkraft, präzisionswerkzeugmechanikerausbildungsverordnung, klavier cembalobauerausbildungsverordnung |
| 11 | 28 | zwölfter sozialgesetzbuch, sozialgesetzbuch, nettoentgelte kurzarbeitergeld, grundsicherungs datenabgleichsverordnung, sozialgesetzbuch maßgeblich, sozialgesetzbuch regelbedarfsstufen, regelbedarfsstufen fortschreibungsverordnung, fortschreibung |
| 19 | 16 | frist sozialgesetzbuch, sozialgesetzbuch künstlersozialabgabe, bundesagentur arbeit, arbeit weiterleitung, anspruch ausländisch, arbeitsschutzzuständige, bundesteilhabegesetz, bundeswehr vorstand |
| 20 | 15 | rentenversicherung alterssicherung, landwirt rentenwertbestimmungsverordnung, sozialversicherungsentgeltverordnung, sozialversicherungs rechengrößenverordnung, sozialversicherung sozialversicherungs, rechengrößenverordnung sozialversicherungsentgeltverordnung, alterssicherung landwirt, anzeige versicherungsfall |

## mixed topics (document-level review)

| topic_id | count | accepted | top words |
|---|---|---|---|
| 8 | 34 | 12 | behindertengleichstellungsrecht bereinigung, auslandstrennungsgeldrecht, auswärtig, ausschluss verfassungsfeindlich, auslandsumzugskostenverordnung europawahlordnung, beförderungsämter bundesunmittelbar, beamtenstatusgesetzes bundesbeamtengesetz, ausübung zulassungspflichtig |
| 9 | 33 | 8 | finanzausgleichsgesetz, finanzausgleichsgesetz ausgleichsjahr, ausgleichsjahr festsetzung, gewerbesteuerumlage gemeindefinanzreformgesetz, festsetzung umlagesatz, gemeindefinanzreformgesetz, bundeshaushaltsplan haushaltsjahr, rentenversicherung bundesentschädigungsgesetz |
| 14 | 20 | 5 | aufteilung gemeindeanteil, bekämpfung steuerumgehung, bereich kommunalinvestitionsförderungsgesetz, bundesverfassungsgericht reform, einkommensteuer einkommensteuerschlüsselzahlenermittlungsverordnung, einkommensteuergesetzes, familienentlastungsgesetz steuerlich, familienentlastungsgesetz |

## clustering parameters (step2_2_1_process_ger_berttopic_new.py)

| parameter | value |
|---|---|
| run_date | 2026-10-29 |
| input_file | bgbl1_2016-2018_20260918.json |
| model_name | paraphrase-multilingual-mpnet-base-v2 |
| max_seq_length | 512 |
| bertopic_language | multilingual |
| embed_body_chars | 1000 |
| parent_match_min | 0.85 |
| min_cluster_size | 10 |
| min_samples | 5 |
| n_neighbors | 20 |
| n_components | 5 |
| max_df | 0.3 |
| mmr_diversity | 0.3 |
| random_seed | 42 |
| n_docs | 1165 |
| n_corrections | 48 |
| n_annexes | 8 |
| n_attached_to_parent | 49 |
| n_assigned_via_transform | 7 |
| n_topics | 28 |
| n_noise | 298 |

## output files

- `s:\stbuchho\crises_and_welfare_states\policy-tracker\data\processed\germany\pre2023\germany_2016-2018_berttopic_v2_candidates.json`
- `s:\stbuchho\crises_and_welfare_states\policy-tracker\data\processed\germany\pre2023\germany_2016-2018_berttopic_v2_noise_pool.json`
- `s:\stbuchho\crises_and_welfare_states\policy-tracker\data\processed\germany\pre2023\germany_2016-2018_berttopic_v2_mixed_review.json`

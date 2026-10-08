# BGBl I post-2023 full-text run log

| | |
|---|---|
| date | 2026-10-07 |
| metadata | `data/raw/germany/bgbl1_website_2023-2026_20260929.json` |
| zip dir | `data/raw/germany/bgbl1_newwebsite_post2023_zip` |
| pymupdf / pymupdf4llm | 1.28.2 / 1.28.2 |
| engines (order) | layout, legacy — fallback if > 0.2% of plain-text words missing |
| engine options | `{'layout': {'header': False, 'footer': False, 'use_ocr': False, 'page_chunks': False, 'page_separators': False, 'write_images': False, 'embed_images': False, 'show_progress': False}, 'legacy': {'table_strategy': 'lines_strict', 'page_chunks': False, 'write_images': False, 'embed_images': False, 'show_progress': False}}` |
| limit | — |

## results

| metric | n |
|---|---|
| FNA-matched publications processed | 358 |
| in final policy set | 358 |
| excluded (no text) | 0 |
| zips with more than one pdf (merged) | 0 |
| publications with markdown tables | 111 |
| publications with warnings | 7 |
| engine used | legacy: 228, layout: 130 |
| missing plain-text words, median / max share | 0.00% / 4.55% |
| chars min / median / max | 414 / 12444 / 1223277 |
| ≈ tokens median / max (chars/4) | 3111 / 305819 |

## longest publications

| id | chars | pages | title |
|---|---|---|---|
| bgbl1-2024-179-1 | 1223277 | 358 | Verordnung zur Neuordnung der Ausbildung in der Bauwirtschaft |
| bgbl1-2025-24-1 | 736057 | 193 | Bekanntmachung der Neufassung der Abgabenordnung |
| bgbl1-2023-199-1 | 397898 | 142 | Verordnung zum Neuerlass der Fahrzeug-Zulassungsverordnung und zur Änderung weit |
| bgbl1-2024-400-1 | 351627 | 112 | (Krankenhausversorgungsverbesserungsgesetz — KHVVG) |
| bgbl1-2026-98-1 | 305317 | 96 | (Krankenhausreformanpassungsgesetz — KHAG) |

## lowest text coverage (share of plain-text words missing from the markdown)

| id | missing | engine |
|---|---|---|
| bgbl1_2024_188 | 4.55% | legacy |
| bgbl1_2026_112 | 1.71% | layout |
| bgbl1_2024_353 | 1.35% | layout |
| bgbl1_2025_50 | 1.19% | legacy |
| bgbl1_2026_28 | 1.07% | layout |
| bgbl1_2024_346 | 1.04% | layout |
| bgbl1_2025_373 | 0.94% | legacy |
| bgbl1_2024_411 | 0.87% | layout |
| bgbl1_2024_376 | 0.77% | layout |
| bgbl1_2023_104 | 0.64% | layout |

## warnings

| id | zip | warnings |
|---|---|---|
| bgbl1_2024_186 | bgbl1_2024_186.zip | letter-spaced text left: ['H e r s t e l l e n v o', 'o m p o n e n t e'] |
| bgbl1_2024_188 | bgbl1_2024_188.zip | regelungstext.pdf: 4.5% of plain-text words missing (legacy): für×21, des×15, z×15, B×15, zu×13, fehlende×12, die×9, Bezugspersonen×9 |
| bgbl1_2024_346 | bgbl1_2024_346.zip | regelungstext.pdf: 1.0% of plain-text words missing (layout): Berücksichtigung×3, Berufsbild×2, positionen×2, berufsprofilgebender×2, und×1, für×1, Bildung×1, Forschung×1 |
| bgbl1_2024_353 | bgbl1_2024_353.zip | regelungstext.pdf: 1.4% of plain-text words missing (layout): ELSTER×1, Online×1 |
| bgbl1_2025_50 | bgbl1_2025_050.zip | regelungstext.pdf: 1.2% of plain-text words missing (legacy): m3×2, Quarz×1, Feinstaubjahren×1 |
| bgbl1_2026_28 | bgbl1_2026_028.zip | Regelungstext.pdf: 1.1% of plain-text words missing (layout): Versicherungs×5, gewähren×4, zurückzu×4, Vertrags×3, 33×3, 66×3, Der×2, gesetzes×2 |
| bgbl1_2026_112 | bgbl1_2026_112.zip | Regelungstext.pdf: 1.7% of plain-text words missing (layout): und×4, 2024×4, gesetzes×4, des×3, Absatz×3, asyl×3, Buch×3, Flüchtlingseigenschaft×3 |

## zips on disk not in the FNA-matched metadata

none

## output files

- `data/processed/germany/germany_2023-2026_final_policy_set.json`
- `data/processed/germany/post2023/` (pdfs + markdown cache)

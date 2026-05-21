# filter run log

| | |
|---|---|
| date | 2026-05-21 |
| input file | `s:\stbuchho\crises_and_welfare_states\policy-tracker\data\raw\germany\bgbl1_2008-2015_2019-2022_combined.json.gz` |
| output dir | `s:\stbuchho\crises_and_welfare_states\policy-tracker\data\processed\germany` |
| output prefix | `germany_cov_2008-2015_2019-2022` |

## configuration

| parameter | value |
|---|---|
| AUTO_THRESHOLD | 0.779 |
| BORDERLINE_LOW | 0.74 |

## score distribution

| metric | value |
|---|---|
| min | 0.374 |
| max | 0.980 |
| mean | 0.657 |
| median | 0.651 |

![score distribution](filter_runlog_germany_cov_2008-2015_2019-2022_bgbl1_2008-2015_2019-2022_combined.json_2026-05-21_scores.png)

## filtering results

| category | n |
|---|---|
| auto-accepted (>= 0.779) | 501 |
| borderline (0.74–0.778) | 410 |
| below threshold (< 0.74) | 4137 |
| total | 5048 |

## output files

- `s:\stbuchho\crises_and_welfare_states\policy-tracker\data\processed\germany\germany_cov_2008-2015_2019-2022_auto_accepted.json`
- `s:\stbuchho\crises_and_welfare_states\policy-tracker\data\processed\germany\germany_cov_2008-2015_2019-2022_borderline_candidates.json`

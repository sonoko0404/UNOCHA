# Validation Notes

This file records checks run against the generated local outputs. It is based only on files in this repository.

## Generated Ranking Files

The following files were generated with:

```bash
python3 -m src.cli rank \
  --query "Which crises have less than 40% funding coverage?" \
  --year YEAR \
  --explain \
  --output data/processed/ranking_YEAR.csv
```

| File | Rows | Active HRP rows | `ok` rows | `no_mapped_cbpf_allocation` rows |
| --- | ---: | ---: | ---: | ---: |
| `data/processed/ranking_2024.csv` | 7 | 7 | 4 | 3 |
| `data/processed/ranking_2025.csv` | 18 | 18 | 14 | 4 |
| `data/processed/ranking_2026.csv` | 19 | 19 | 12 | 7 |

## Top 5 Results

### 2024

| Rank | Country | Score | Funding coverage | People in need | Active HRP | Data flags |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | Ethiopia | 75.8 | 28.4% | 14,162,123 | Yes | `ok` |
| 2 | Myanmar | 70.0 | 39.8% | 12,239,518 | Yes | `ok` |
| 3 | Syrian Arab Republic | 67.4 | 37.2% | 15,305,903 | Yes | `ok` |
| 4 | Venezuela (Bolivarian Republic of) | 60.7 | 28.2% | 4,425,474 | Yes | `ok` |
| 5 | Honduras | 55.2 | 32.2% | 2,800,000 | Yes | `no_mapped_cbpf_allocation` |

### 2025

| Rank | Country | Score | Funding coverage | People in need | Active HRP | Data flags |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | Colombia | 81.1 | 17.5% | 9,053,352 | Yes | `ok` |
| 2 | Venezuela (Bolivarian Republic of) | 77.5 | 20.2% | 7,943,720 | Yes | `ok` |
| 3 | Yemen | 74.1 | 29.0% | 16,989,029 | Yes | `ok` |
| 4 | Sudan | 72.5 | 39.7% | 30,440,770 | Yes | `ok` |
| 5 | Burkina Faso | 65.5 | 34.3% | 5,915,136 | Yes | `ok` |

### 2026

| Rank | Country | Score | Funding coverage | People in need | Active HRP | Data flags |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | Yemen | 87.9 | 13.1% | 23,100,000 | Yes | `no_mapped_cbpf_allocation` |
| 2 | Sudan | 84.0 | 20.8% | 33,699,770 | Yes | `ok` |
| 3 | Afghanistan | 78.6 | 14.9% | 21,889,283 | Yes | `ok` |
| 4 | Venezuela (Bolivarian Republic of) | 78.2 | 15.4% | 7,900,000 | Yes | `no_mapped_cbpf_allocation` |
| 5 | Syrian Arab Republic | 76.8 | 16.5% | 16,500,000 | Yes | `ok` |

## Enriched Baseline Files

Blank-query enriched files were generated to support the dashboard trend chart and supplemental views.

| File | Rows | Severity context matched | Sector funding matched |
| --- | ---: | ---: | ---: |
| `data/processed/ranking_2024_enriched.csv` | 24 | 19 | 24 |
| `data/processed/ranking_2025_enriched.csv` | 22 | 18 | 22 |
| `data/processed/ranking_2026_enriched.csv` | 20 | 15 | 20 |

The severity context is `HNO people_in_need / COD admin0 population baseline`. It is not an INFORM, IPC, or IDP severity indicator.

## CBPF Mapping Audit

`data/processed/unmapped_cbpf_funds.csv` currently contains:

| Pooled fund name | Year | Unmapped CBPF budget USD | Records |
| --- | ---: | ---: | ---: |
| Fiji | 2026 | 350,000.00 | 1 |
| Indonesia | 2013 | 286,034.11 | 3 |

Mapped CBPF rows use pooled-fund-name aliases and are labelled `medium_alias_table` in the output. Rows without a mapped CBPF allocation are labelled `not_applicable_no_mapped_allocation`.

## Automated Checks

The following local checks passed:

```bash
python3 -m py_compile app.py src/query.py src/normalize.py src/scoring.py
python3 -m unittest discover -s tests
```

The unit-test suite covers:

- active HRP plus no-funding query parsing
- food-insecurity query parsing to the food sector
- no-HRP query parsing
- 2025 ranking pipeline smoke test
- presence of HRP, severity-context, and CBPF mapping fields
- active-HRP plus less-than-40-percent-funding filtering

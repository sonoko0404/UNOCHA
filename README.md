# Geo-Insight: Overlooked Crisis Ranker

Geo-Insight is a UNOCHA challenge prototype for identifying crises where documented humanitarian need is high while funding coverage and mapped pooled-fund support are low. It accepts a natural-language query or geographic scope, then returns a ranked list, funding gap, map-ready country points, and top-result explanations.

This is a decision-support triage tool for humanitarian analysts and donor advisors. It is not an automated funding-allocation system.

## Data Sources

Primary public sources:

- HDX Global HPC HNO: `global-hpc-hno`
- HDX Humanitarian Response Plans: `humanitarian-response-plans`
- HDX Global Requirements and Funding Data: `global-requirements-and-funding-data`
- OCHA CBPF Project Summary API

Local supplement files used when present:

- `hpc_hno_2024.csv`, `hpc_hno_2025.csv`, `hpc_hno_2026.csv`: HNO people-in-need data.
- `humanitarian-response-plans.csv`: HRP metadata. This local file has no explicit status field, so active HRP status is inferred from year and date overlap and labelled `medium_date_inferred`.
- `fts_requirements_funding_global.csv`: FTS requirements and funding coverage.
- `fts_requirements_funding_globalcluster_global.csv`: sector funding context and lowest-funded sector.
- `fts_incoming_funding_global.csv`, `fts_outgoing_funding_global.csv`: single-country paid/commitment flow-detail context.
- `cod_population_admin0.csv`: COD admin0 population baseline for PIN/population context.

Optional source supported but not used in the current generated outputs:

- HDX INFORM Severity Index: no local INFORM file is cached in this repo. The current severity fields are therefore not INFORM, IPC, or IDP severity. They are labelled as HNO PIN / COD population proxy context.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run Commands

Generate yearly rankings:

```bash
python -m src.cli rank \
  --query "Which crises have less than 40% funding coverage?" \
  --year 2024 \
  --output data/processed/ranking_2024.csv \
  --explain

python -m src.cli rank \
  --query "Which crises have less than 40% funding coverage?" \
  --year 2025 \
  --output data/processed/ranking_2025.csv \
  --explain

python -m src.cli rank \
  --query "Which crises have less than 40% funding coverage?" \
  --year 2026 \
  --output data/processed/ranking_2026.csv \
  --explain
```

Generate enriched baseline files for dashboard trend and audit views:

```bash
python -m src.cli rank --query "" --year 2024 --min-people-in-need 0 --output data/processed/ranking_2024_enriched.csv
python -m src.cli rank --query "" --year 2025 --min-people-in-need 0 --output data/processed/ranking_2025_enriched.csv
python -m src.cli rank --query "" --year 2026 --min-people-in-need 0 --output data/processed/ranking_2026_enriched.csv
```

Test specific query intents:

```bash
python -m src.cli rank \
  --query "active HRPs with less than 40% funding coverage" \
  --year 2026 \
  --explain

python -m src.cli rank \
  --query "Show acute food insecurity hotspots with less than 10% requested funding." \
  --year 2026 \
  --explain

python -m src.cli rank \
  --query "Countries with no HRP" \
  --year 2026 \
  --explain
```

Run the dashboard:

```bash
streamlit run app.py
```

Run validation tests:

```bash
python -m py_compile app.py src/query.py src/normalize.py src/scoring.py src/cli.py
python -m unittest discover -s tests
```

## Example Results

Top 5 from `data/processed/ranking_2026.csv`, generated with `Which crises have less than 40% funding coverage?`:

| Country | Year | People in need | Funding coverage | Overlooked score | Active HRP | Short reason |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Yemen | 2026 | 23,100,000 | 13.1% | 87.9 | Yes | Very large PIN, 86.9% funding gap, no mapped CBPF allocation, and 2 of 3 recent years below 40%. |
| Sudan | 2026 | 33,699,770 | 20.8% | 84.0 | Yes | Highest PIN in the 2026 filtered set, 79.2% funding gap, and chronic underfunding signal. |
| Afghanistan | 2026 | 21,889,283 | 14.9% | 78.6 | Yes | Large PIN, 85.1% funding gap, and low mapped CBPF per person in need. |
| Venezuela (Bolivarian Republic of) | 2026 | 7,900,000 | 15.4% | 78.2 | Yes | Low funding coverage, no mapped CBPF allocation, and 3 of 3 recent years below 40%. |
| Syrian Arab Republic | 2026 | 16,500,000 | 16.5% | 76.8 | Yes | Large PIN, 83.5% funding gap, and chronic underfunding signal. |

See `docs/validation.md` for row counts, top-result checks, CBPF unmapped audit, and test status.

## Scoring Logic

```text
overlooked_score =
  0.30 * unmet_need_scale
+ 0.25 * funding_gap
+ 0.20 * need_scale
+ 0.15 * cbpf_gap_scale
+ 0.10 * chronic_underfunding_scale
```

Definitions:

- `funding_gap = 1 - funding_pct`
- `unmet_need_proxy = people_in_need * funding_gap`
- `need_scale` and `unmet_need_scale` are percentile ranks.
- `cbpf_gap_scale` is higher when mapped CBPF allocation per person in need is lower.
- `chronic_underfunding_scale` is based on years below 40 percent funding in the latest three-year window.

Supplemental fields do not necessarily change the score. They support explanation and audit:

- HRP fields: `has_active_hrp`, `hrp_status`, `hrp_plan_name`, `hrp_plan_type`, `hrp_year`, `hrp_match_confidence`, `hrp_data_quality`.
- Severity context: `severity_available`, `severity_context`, `severity_source`.
- CBPF audit: `cbpf_allocation_usd`, `cbpf_per_person_in_need`, `cbpf_gap_scale`, `cbpf_mapping_confidence`, `cbpf_country_source`.
- Sector and flow context: `worst_sector`, `worst_sector_funding_pct`, donor/recipient concentration fields.

## Limitations

- HNO sector-level PIN values can overlap, so the default country need summary uses intersectoral or plan-caseload PIN when available, otherwise the maximum reported PIN.
- Missing FTS requirements are flagged rather than hidden.
- CBPF allocations are mapped from pooled-fund names to ISO3 with a local alias table. Unmapped funds are written to `data/processed/unmapped_cbpf_funds.csv`.
- The local HRP file has no explicit status field. Active HRP status is inferred from date and year overlap and labelled as medium confidence.
- Severity is not real INFORM, IPC, or IDP severity in the current outputs. It is a transparent HNO PIN / COD population proxy.
- Food-insecurity queries are mapped to the food sector as a proxy. They do not use IPC phase data.
- Rankings are triage signals for analyst review, not funding decisions.

# Data Access Status

Checked on 2026-05-21.

## Core sources used in v1

| Source | Access path | Status | Local cache |
| --- | --- | --- | --- |
| Global HPC HNO | HDX CKAN package `global-hpc-hno` | Accessible | `data/raw/hno_2024.csv`, `data/raw/hno_2025.csv`, `data/raw/hno_2026.csv` |
| Humanitarian Response Plans | HDX CKAN package `humanitarian-response-plans` | Accessible | `data/raw/humanitarian_response_plans.csv` |
| Global Requirements and Funding Data | HDX CKAN package `global-requirements-and-funding-data` | Accessible | `data/raw/fts_requirements_funding_global.csv` |
| CBPF Project Summary | OCHA CBPF OData CSV endpoint | Accessible | `data/raw/cbpf_project_summary.csv` |

## Optional enrichment sources

| Source | Access path | Status | Current use |
| --- | --- | --- | --- |
| COD population | HDX CKAN package `cod-ps-global` | Local CSV downloaded | `cod_population_admin0.csv` supplies admin0 population baselines for PIN-share context |
| FTS global-cluster funding | HDX package `global-requirements-and-funding-data` | Local CSV downloaded | `fts_requirements_funding_globalcluster_global.csv` supplies lowest-funded sector context |
| FTS incoming flow detail | HDX package `global-requirements-and-funding-data` | Local CSV downloaded | `fts_incoming_funding_global.csv` supplies single-country donor concentration context |
| FTS outgoing flow detail | HDX package `global-requirements-and-funding-data` | Local CSV downloaded | `fts_outgoing_funding_global.csv` supplies single-country recipient concentration context |
| INFORM Severity Index | HDX CKAN package `inform-global-crisis-severity-index` | Metadata verified, no local file cached | Not used in current score or dashboard because no local INFORM/IPC/IDP data file is present |
| HDX HAPI | `https://hapi.humdata.org/` | Documentation/API reachable outside sandbox | Not used in v1; CKAN CSV downloads are simpler |

## Local supplement files used after 2026-05-21 update

| File | Role in pipeline | Notes |
| --- | --- | --- |
| `hpc_hno_2024.csv` | Need source | Preferred over `data/raw/hno_2024.csv` when present |
| `hpc_hno_2025.csv` | Need source | Preferred over `data/raw/hno_2025.csv` when present |
| `hpc_hno_2026.csv` | Need source | Preferred over `data/raw/hno_2026.csv` when present |
| `humanitarian-response-plans.csv` | HRP metadata | Preferred over `data/raw/humanitarian_response_plans.csv` when present |
| `fts_requirements_funding_global.csv` | Country plan funding coverage | Preferred over `data/raw/fts_requirements_funding_global.csv` when present |
| `fts_requirements_funding_globalcluster_global.csv` | Sector funding context | Used to compute `worst_sector` and `worst_sector_funding_pct` |
| `cod_population_admin0.csv` | Population context | Uses admin0 `T_TL`, `Gender=all`, `Age_range=all` rows only |
| `fts_incoming_funding_global.csv` | Incoming flow context | Uses `status in {paid, commitment}` and `onBoundary=single` only |
| `fts_outgoing_funding_global.csv` | Outgoing flow context | Uses `status in {paid, commitment}` and `onBoundary=single` only |

## Notes

- HDX web pages may show a browser/JavaScript challenge, but CKAN API access works and is the correct programmatic path for this prototype.
- CBPF data is large enough that it should be cached locally. The current script downloads it once and reuses the cached CSV.
- ReliefWeb links in the challenge are reference/example documents rather than required structured datasets. They are not part of the v1 scoring pipeline.
- Shared multi-country FTS flow-detail rows are excluded from concentration metrics because allocating the same regional amount to every destination would inflate country totals.
- HRP active status uses a status field when present. The local `humanitarian-response-plans.csv` file has no explicit status field, so current matches are inferred from `startDate`, `endDate`, and selected plan year and labelled `medium_date_inferred`.
- Need-intensity severity context is computed only where COD population baselines match a row. It uses `HNO people_in_need / COD admin0 population` and is labeled as proxy context, not as INFORM, IPC, or IDP severity.
- CBPF country mapping uses the pooled-fund-name alias table. Rows with mapped CBPF allocation receive `cbpf_mapping_confidence=alias_match`; detected unmapped CBPF funds are written to `data/processed/unmapped_cbpf_funds.csv`.

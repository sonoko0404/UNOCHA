# Technical Write-up: Geo-Insight Overlooked Crisis Ranker

## Objective

Geo-Insight ranks crises where documented humanitarian need is high relative to funding coverage and mapped pooled-fund support. The prototype accepts a natural-language query or geographic scope, converts supported language into reproducible filters, and returns an auditable ranking with explanations and data-quality flags.

The intended user is a humanitarian analyst, donor advisor, or coordination officer. The output should prioritize review and source inspection. It should not be treated as an automated allocation decision.

## Gap Score Definition

The score combines five transparent signals:

```text
overlooked_score =
  0.30 * unmet_need_scale
+ 0.25 * funding_gap
+ 0.20 * need_scale
+ 0.15 * cbpf_gap_scale
+ 0.10 * chronic_underfunding_scale
```

Where:

- `funding_gap = 1 - funding_pct`
- `funding_pct` is matched FTS funding divided by requirements.
- `unmet_need_scale` is the percentile rank of `log(people_in_need * funding_gap)`.
- `need_scale` is the percentile rank of `log(people_in_need)`.
- `cbpf_gap_scale` is higher where mapped CBPF allocation per person in need is lower.
- `chronic_underfunding_scale` is the share of the latest three observed years below 40 percent funding coverage.

The formula intentionally favors auditable features over opaque prediction.

## Data Handling

HNO people-in-need values are the primary need signal. The system avoids summing sector PIN because sector populations can overlap. It uses intersectoral or plan-caseload PIN when available, otherwise the maximum reported country PIN.

Rows with missing FTS requirements are retained and flagged as `missing_fts_requirements`. The ranking should surface uncertainty instead of silently dropping cases that need follow-up.

CBPF allocations are mapped from `pooledfundname` to ISO3 with the local country alias table. Successful mapped rows receive `cbpf_mapping_confidence=alias_match`; rows without mapped allocation keep zero allocation and receive `no_mapped_cbpf_allocation`. Unmapped pooled-fund records are exported to `data/processed/unmapped_cbpf_funds.csv`.

Shared multi-country FTS flow-detail rows are excluded from concentration metrics. Only `onBoundary=single` and `status in {paid, commitment}` records are used.

## Query Parser

The rule-based parser extracts:

- year
- region and country scope
- sector keyword
- funding threshold, including "less than 40%" and "no funding"
- active HRP and missing HRP filters
- food-insecurity query intent
- structural-neglect or chronic-underfunding intent
- minimum people-in-need threshold

Supported examples:

- `active HRPs with less than 40% funding coverage` maps to `hrp_filter=active` and `funding_pct_max=0.40`.
- `Countries with no HRP` maps to `hrp_filter=missing`.
- `Show acute food insecurity hotspots with less than 10% requested funding.` maps to food-sector proxy plus `funding_pct_max=0.10`.
- `Which regions are consistently underfunded across multiple years?` sets structural-neglect intent. It does not hard-code a result set.

Food-insecurity wording is a sector proxy only. No IPC phase data is used in the current prototype.

## HRP Metadata

HRP metadata is merged by selected year and country ISO3. The output includes:

- `has_active_hrp`
- `hrp_status`
- `hrp_plan_name`
- `hrp_plan_type`
- `hrp_year`
- `hrp_match_confidence`
- `hrp_data_quality`

The code prioritizes an HRP status field if one exists. The current local `humanitarian-response-plans.csv` file has no explicit status field, so active status is inferred from `startDate`, `endDate`, and `years`. Such matches are labelled `medium_date_inferred` and `matched_by_year_and_date_no_status_field`.

Countries with documented need are not removed if HRP is missing. `hrp_filter=missing` keeps rows with no active HRP match.

## Severity and Need Context

No local INFORM Severity Index, IPC, or IDP/displacement dataset is cached in this repo. The generated ranking files therefore set:

- `severity_available=False`
- `severity_source=HNO PIN / COD population proxy, not INFORM or IPC severity`

When COD admin0 population is available, `severity_context` describes people in need as a share of the population baseline. This is a need-scale context field, not a formal severity score, and it is not added to the ranking formula.

## Structural Neglect

Structural neglect is represented by chronic underfunding. The pipeline checks the selected year and two previous years, then counts how many observed years had FTS funding coverage below 40 percent. The output exposes both `chronic_underfunding_count` and `chronic_underfunding_scale`.

## Dashboard Evidence

The Streamlit dashboard exposes:

- ranked table and top-result explanation
- map-ready country points
- funding coverage and funding gap
- HRP status and match confidence
- CBPF allocation, per-person allocation, and mapping confidence
- worst-funded sector context
- chronic underfunding count
- severity context and source
- data-quality flags and confidence

Missing optional fields are handled with graceful fallbacks.

## Failure Cases and Limitations

- Funding can lag needs assessments, especially early in a year.
- Regional appeals and multi-country plans can be difficult to attribute to single countries.
- CBPF is only one pooled-fund lens, not total humanitarian financing.
- HRP active status is medium-confidence date inference when the source file lacks explicit status.
- Food-insecurity queries do not use IPC data.
- Severity context is not real INFORM, IPC, or IDP severity.
- Data gaps should trigger analyst review, not force precise decisions.

## Analyst Workflow

An analyst should use the ranking as a first-pass shortlist, inspect the source fields and flags, compare FTS/HNO/HRP context, and then validate the result with country or sector expertise before drawing operational conclusions.

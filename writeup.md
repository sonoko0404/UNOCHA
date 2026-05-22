# Technical Write-up: Geo-Insight Overlooked Crisis Ranker

## Objective

The prototype identifies countries or crises where documented humanitarian need appears high relative to funding coverage and mapped pooled-fund support. It accepts a natural-language query or geographic scope, returns an explainable ranking, and exposes the evidence behind each row so an analyst can check whether the result is a credible follow-up lead.

The tool is designed as a triage aid. It does not make automated funding recommendations.

## Data Used

The current pipeline uses these public OCHA/HDX sources and locally downloaded supplements:

- Humanitarian Needs Overview files for 2024, 2025, and 2026 people-in-need estimates.
- FTS global requirements and funding data for plan funding coverage.
- Humanitarian Response Plans metadata for plan status and active HRP checks.
- OCHA CBPF Project Summary data for mapped country-based pooled-fund allocations.
- COD admin0 population data for people-in-need share context.
- FTS global-cluster funding data for lowest-funded sector context.
- FTS incoming and outgoing flow-detail files for single-country flow concentration context.

The dashboard and CSV output now include HRP fields (`has_active_hrp`, `active_hrp_names`, `hrp_status`), CBPF mapping fields (`cbpf_mapping_confidence`, `cbpf_country_source`), and supplemental evidence fields for population, sector coverage, and flow concentration.

No local INFORM Severity Index, IPC, or IDP/displacement file is cached in this repo. Severity-related views therefore use only the transparent local proxy `HNO people_in_need / COD admin0 population baseline`, labelled as `severity_context`. It is not treated as an INFORM replacement and is not added to the scoring formula.

## Gap Definition

The score combines five auditable signals:

```text
overlooked_score =
  0.30 * percentile(log(people_in_need * funding_gap))
+ 0.25 * funding_gap
+ 0.20 * percentile(log(people_in_need))
+ 0.15 * inverse_percentile(CBPF allocation per person in need)
+ 0.10 * share of latest three years below 40 percent funding
```

Where `funding_gap = 1 - funding_pct`, and `funding_pct` comes from matched FTS funding divided by stated requirements. The score is reported with a coarse level: Watch, Moderate, High, or Very High.

Supplemental fields explain the ranking but do not alter the score. This keeps the result stable and avoids implying precision from incomplete optional sources.

## Handling Missing and Inconsistent Data

The system avoids summing sector-level people-in-need because sector PIN values can overlap. It uses an intersectoral or plan-caseload PIN when available, otherwise the maximum reported PIN for the country and year.

Rows with no matched FTS requirements are retained and flagged as `missing_fts_requirements`. Rows with no mapped CBPF allocation are flagged as `no_mapped_cbpf_allocation`.

CBPF country mapping is based on pooled-fund-name aliases, so mapped rows are labelled `medium_alias_table`. Detected unmapped pooled-fund records are exported to `data/processed/unmapped_cbpf_funds.csv`.

Shared multi-country FTS flow-detail rows are excluded from concentration metrics. Only `onBoundary=single` and `status in {paid, commitment}` records are used, which avoids assigning the same regional amount to multiple countries.

## Query Handling

The query parser remains rule-based for reproducibility. It extracts:

- year
- region or country scope
- sector keyword
- funding threshold, including phrases such as "less than 40%" and "no funding"
- active HRP, any HRP, or no HRP filters
- severity, food insecurity, and displacement query intent
- minimum people-in-need threshold

Food-insecurity wording maps to the food sector where the HNO file contains a food-related sector. Severity and displacement terms are surfaced in the query audit, but they do not create unsupported filters when no authoritative local severity or displacement dataset exists.

The dashboard includes an "Interpreted query filters" panel so users can see exactly which parts of the query became filters and which terms remained analyst context.

## Dashboard Evidence

The dashboard now has four working views:

- `Command View`: ranking table, HRP status, severity context, CBPF mapping confidence, and top-row explanations.
- `Interactive Map`: map-ready crisis points with hover details for funding coverage, PIN share, HRP status, CBPF allocation, sector stress, and data flags.
- `Comparison Board`: evidence matrix, score ladder, CBPF intensity, regional load, region-level matrix, lowest-sector coverage, PIN share, flow concentration, and a 2024-2026 funding-coverage trend chart.
- `Method & Data`: filtered result audit, guardrails, triggered data cautions, scoring formula, evidence trace, flag counts, confidence distribution, and full CSV-ready output.

## Validation Snapshot

For the query `Which crises have less than 40% funding coverage?`, the generated CSVs contain:

- 2024: 7 matched crises; top result Ethiopia; 4 `ok` rows and 3 `no_mapped_cbpf_allocation` rows.
- 2025: 18 matched crises; top result Colombia; 14 `ok` rows and 4 `no_mapped_cbpf_allocation` rows.
- 2026: 19 matched crises; top result Yemen; 12 `ok` rows and 7 `no_mapped_cbpf_allocation` rows.

All matched rows in those three query outputs have active HRP records according to the local HRP metadata and selected plan year. Detailed checks are in `docs/validation.md`.

## Failure Cases

- Funding can lag needs assessments; a low current-year funding percentage early in the year may not mean long-term neglect.
- Regional and multi-country appeals can be difficult to attribute to individual countries.
- CBPF coverage is not total humanitarian financing; it is only a pooled-fund lens.
- The local severity context is a PIN-share measure, not an external severity index.
- Data gaps should lower confidence or trigger follow-up, not force precise conclusions.

## Intended Workflow

A humanitarian coordinator, donor advisor, or analyst can use the tool to generate a first-pass list of crises that deserve deeper review. The ranked output should be followed by source inspection, operational context review, and country or sector expert validation.

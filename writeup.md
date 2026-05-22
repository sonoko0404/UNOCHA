# Technical Write-up: Geo-Insight Overlooked Crisis Ranker

## Objective

The prototype identifies countries or crises where documented humanitarian need appears high relative to funding coverage and mapped pooled fund allocations. It accepts a natural-language query or geographic scope and returns a ranked, explainable list.

## Data

The core implementation uses public OCHA/HDX sources:

- Humanitarian Needs Overview data for people in need.
- Global requirements and funding data from FTS.
- Humanitarian Response Plan metadata.
- CBPF Project Summary data for country-based pooled fund allocations.

The downloader can also fetch COD population and INFORM Severity Index files for later enrichment.

## Gap Definition

The current v1 score combines five signals:

```text
overlooked_score =
  0.30 * percentile(log(people_in_need * funding_gap))
+ 0.25 * funding_gap
+ 0.20 * percentile(log(people_in_need))
+ 0.15 * inverse_percentile(CBPF allocation per person in need)
+ 0.10 * share of latest three years below 40 percent funding
```

This deliberately favors transparent, auditable features over opaque model output. The result is reported as a score and a coarse level: Watch, Moderate, High, or Very High.

## Missing and Inconsistent Data

The system avoids summing sector-level people-in-need because sector PIN values can overlap. It uses intersectoral PIN when available; otherwise it uses the maximum reported PIN as a conservative fallback.

Rows with no matched FTS requirements are not removed. They are flagged as `missing_fts_requirements`, assigned lower confidence, and treated as needing analyst review.

CBPF allocations are mapped from fund names to ISO3 codes through a local alias table. Unmapped or absent CBPF allocations are flagged. This is sufficient for the prototype but should be replaced with an official CBPF country dimension.

## Query Handling

The query parser extracts:

- year
- region or country scope
- sector keyword
- funding threshold such as "less than 40%"
- minimum people-in-need threshold

The parser is intentionally rule-based for reproducibility. A later version can add an LLM parser that emits the same `QuerySpec` schema, with the rule parser as fallback.

## Bonus Direction

The v1 bonus feature is chronic underfunding: the number of observed years in the latest three-year window where funding coverage was below 40 percent. This distinguishes structural neglect from a single acute funding shortfall.

Future extensions:

- Add INFORM severity as a need multiplier.
- Add displacement or IDP figures.
- Add sector-level FTS flows where available.
- Add media or advocacy visibility as a separate contextual signal, not as a replacement for need data.

## Failure Cases

- Funding can lag needs assessments; a low current-year funding percentage early in the year may not mean neglect.
- Regional and multi-country appeals can be hard to attribute to individual countries.
- CBPF coverage is not total humanitarian financing. It is one pooled-fund lens.
- Data gaps should lower confidence, not force precise conclusions.

## Intended Workflow

A humanitarian coordinator or donor advisor can use the tool to generate a first-pass list of crises that deserve deeper review. The ranked output should be followed by source inspection, operational context review, and sector/country expert validation.

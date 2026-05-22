# Geo-Insight: Overlooked Crisis Ranker

Prototype for the UNOCHA challenge: rank crises where documented humanitarian need appears high relative to funding and pooled fund coverage.

## What it does

- Downloads public HDX/OCHA datasets into `data/raw/`.
- Normalizes Humanitarian Needs Overview, FTS requirements/funding, HRP metadata, CBPF project allocations, COD population baselines, FTS sector funding, and FTS flow-detail extracts.
- Parses a lightweight natural-language query into year, region, sector, funding ceiling, and minimum people-in-need filters.
- Computes an explainable `overlooked_score`.
- Returns a ranked CSV and Streamlit dashboard with briefing cards, an interactive map, and comparison charts.

## Data sources

Primary sources:

- HDX Global HPC HNO: `global-hpc-hno`
- HDX Humanitarian Response Plans: `humanitarian-response-plans`
- HDX Global Requirements and Funding Data: `global-requirements-and-funding-data`
- OCHA CBPF Project Summary API

Downloaded supplement files now used by the pipeline:

- `hpc_hno_2024.csv`, `hpc_hno_2025.csv`, `hpc_hno_2026.csv`: local HNO need files, preferred when present.
- `cod_population_admin0.csv`: COD admin0 total population baseline for `people_in_need / population` context.
- `fts_requirements_funding_globalcluster_global.csv`: FTS global-cluster funding breakdown for lowest-funded sector context.
- `fts_incoming_funding_global.csv`: single-country paid/commitment incoming flow detail for donor concentration context.
- `fts_outgoing_funding_global.csv`: single-country paid/commitment outgoing flow detail for recipient concentration context.
- `humanitarian-response-plans.csv`: local HRP metadata, preferred when present.

Optional sources supported in the downloader:

- HDX COD population: `cod-ps-global`
- HDX INFORM Severity Index: `inform-global-crisis-severity-index`

## Setup on MacBook

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the pipeline

Download the core data:

```bash
python3 -m src.cli download --years 2024 2025 2026
```

Build a ranking:

```bash
python3 -m src.cli rank \
  --query "Which crises in East Africa have less than 40% funding coverage?" \
  --year 2026 \
  --explain
```

Launch the dashboard:

```bash
streamlit run app.py
```

Dashboard views:

- `Command View`: ranked table and top-result explanations.
- `Interactive Map`: map-ready crisis points with hover details from the ranking data.
- `Comparison Board`: evidence matrix plus supplemental population, sector, and flow-detail comparison charts.
- `Method & Data`: current-query audit, data quality flags, supplemental-data coverage, scoring formula, evidence trace, and CSV-ready outputs.

## Scoring logic

The score is designed for decision support, not automated funding allocation.

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
- `unmet_need_proxy = people_in_need * funding_gap`
- `need_scale` and `unmet_need_scale` are percentile ranks
- `cbpf_gap_scale` is high when mapped CBPF allocation per person in need is low
- `chronic_underfunding_scale` counts years below 40 percent funding over the latest three-year window

Supplemental fields do not alter the score. They add explainability and audit context:

- `pin_population_share`: HNO people in need divided by COD admin0 population baseline.
- `worst_sector` and `worst_sector_funding_pct`: lowest-funded matched FTS global-cluster sector after excluding non-sector buckets such as "Not specified".
- `top_donor_share` and `top_recipient_share`: concentration measures from single-country paid/commitment FTS flow-detail rows.

## Important limitations

- HNO sector-level people-in-need values can overlap, so the default country need summary uses intersectoral PIN when available and otherwise the maximum reported sector PIN.
- Missing FTS requirements are flagged and treated as low confidence.
- CBPF allocations are mapped from pooled fund names to ISO3 with a local alias table. This is adequate for a prototype but should be replaced by an authoritative CBPF country dimension.
- Shared multi-country FTS flow-detail rows are excluded from concentration metrics to avoid double counting the same regional amount against multiple countries.
- The score is a triage signal. It should trigger analyst review, not replace it.

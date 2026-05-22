"""Gap scoring and ranking logic."""

from __future__ import annotations

from pathlib import Path
import math
from typing import Iterable

import pandas as pd

from .config import (
    DEFAULT_CHRONIC_FUNDING_THRESHOLD,
    DEFAULT_MIN_PEOPLE_IN_NEED,
    DEFAULT_YEAR,
    PROJECT_ROOT,
    RAW_DIR,
    REGION_SCOPES,
)
from .data_sources import download_core_data
from .normalize import (
    add_country_metadata,
    normalize_cbpf,
    normalize_funding_flows,
    normalize_funding,
    normalize_hno,
    normalize_hrp,
    normalize_population_admin0,
    normalize_sector_funding,
    raw_path,
    summarize_need,
)
from .query import QuerySpec, parse_query


class MissingRawDataError(RuntimeError):
    """Raised when expected raw files are not present locally."""


def _latest_hno_path(year: int) -> tuple[int, Path]:
    candidates = []
    for path in RAW_DIR.glob("hno_*.csv"):
        try:
            candidate_year = int(path.stem.split("_")[-1])
        except ValueError:
            continue
        if candidate_year <= year:
            candidates.append((candidate_year, 0, path))
    for path in PROJECT_ROOT.glob("hpc_hno_*.csv"):
        try:
            candidate_year = int(path.stem.split("_")[-1])
        except ValueError:
            continue
        if candidate_year <= year:
            candidates.append((candidate_year, 1, path))
    if not candidates:
        raise MissingRawDataError(
            "No HNO CSV files found in data/raw. Run `python3 -m src.cli download --years 2026`."
        )
    selected_year, _, selected_path = max(candidates, key=lambda item: (item[0], item[1]))
    return selected_year, selected_path


def _require_path(path: Path, label: str) -> Path:
    if not path.exists() or path.stat().st_size == 0:
        raise MissingRawDataError(f"Missing {label}: {path}")
    return path


def _existing_path(*names: str) -> Path | None:
    for name in names:
        for base in (PROJECT_ROOT, RAW_DIR):
            path = base / name
            if path.exists() and path.stat().st_size > 0:
                return path
    return None


def _require_existing(label: str, *names: str) -> Path:
    path = _existing_path(*names)
    if path is None:
        searched = ", ".join(str(base / name) for name in names for base in (PROJECT_ROOT, RAW_DIR))
        raise MissingRawDataError(f"Missing {label}. Looked for: {searched}")
    return path


def _percent_rank(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    if clean.notna().sum() <= 1:
        return pd.Series([0.5] * len(series), index=series.index)
    return clean.rank(method="average", pct=True).fillna(0.0)


def _score_level(score: float) -> str:
    if score >= 75:
        return "Very High"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Moderate"
    return "Watch"


def _quality_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if pd.isna(row.get("requirements_usd")) or row.get("requirements_usd", 0) <= 0:
        flags.append("missing_fts_requirements")
    if row.get("cbpf_budget_usd", 0) <= 0:
        flags.append("no_mapped_cbpf_allocation")
    if "subnational_aggregated" in str(row.get("need_method", "")):
        flags.append("subnational_hno_aggregation")
    if "subnational" in str(row.get("need_selection", "")):
        flags.append("subnational_hno_proxy")
    if "sector_not_found" in str(row.get("need_selection", "")):
        flags.append("sector_fallback")
    if row.get("hno_year") != row.get("year"):
        flags.append("using_latest_available_hno")
    return "; ".join(flags) if flags else "ok"


def _supplemental_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if pd.isna(row.get("population_baseline")):
        flags.append("no_cod_population_baseline")
    if pd.isna(row.get("worst_sector")):
        flags.append("no_sector_funding_breakdown")
    incoming_total = pd.to_numeric(row.get("incoming_total_usd"), errors="coerce")
    if pd.isna(incoming_total) or incoming_total <= 0:
        flags.append("no_single_country_incoming_flow_detail")
    return "; ".join(flags) if flags else "ok"


def _confidence(row: pd.Series) -> str:
    flags = str(row.get("data_quality_flags", ""))
    if "missing_fts_requirements" in flags:
        return "Low"
    if "subnational_hno_aggregation" in flags or "sector_fallback" in flags:
        return "Medium"
    return "High"


def _build_explanation(row: pd.Series) -> str:
    pin = row.get("people_in_need", 0)
    coverage = row.get("funding_pct")
    if pd.isna(coverage):
        coverage_text = "no matched FTS coverage ratio"
    else:
        coverage_text = f"{coverage:.0%} funded"

    cbpf = row.get("cbpf_budget_usd", 0)
    chronic = row.get("underfunded_years_last_3", 0)
    explanation = (
        f"{row.get('country')} ranks {row.get('overlooked_level')} because it has "
        f"{pin:,.0f} people in need, {coverage_text}, and "
        f"${cbpf:,.0f} in mapped CBPF allocations for the selected year. "
        f"It was below the chronic funding threshold in {int(chronic)} of the last "
        f"{int(row.get('observed_funding_years_last_3', 0))} observed funding years."
    )
    supplemental: list[str] = []
    if not pd.isna(row.get("pin_population_share")):
        supplemental.append(
            f"COD admin0 data puts PIN at {row.get('pin_population_share'):.1%} of the population baseline."
        )
    if not pd.isna(row.get("worst_sector")):
        supplemental.append(
            f"The lowest matched sector funding coverage is {row.get('worst_sector')} at "
            f"{row.get('worst_sector_funding_pct'):.1%}."
        )
    if not pd.isna(row.get("top_donor_share")):
        supplemental.append(
            f"The largest single-country incoming flow source accounts for "
            f"{row.get('top_donor_share'):.1%} of matched paid/commitment flow detail."
        )
    if supplemental:
        explanation = f"{explanation} " + " ".join(supplemental)
    return explanation


def _summarize_sector_stress(sector_funding: pd.DataFrame, year: int) -> pd.DataFrame:
    if sector_funding.empty:
        return pd.DataFrame(
            columns=[
                "country_iso3",
                "sector_count",
                "sector_requirements_usd",
                "sector_funding_usd",
                "sector_median_funding_pct",
                "worst_sector",
                "worst_sector_funding_pct",
                "worst_sector_gap_usd",
            ]
        )

    work = sector_funding[sector_funding["year"] == year].copy()
    if work.empty:
        return pd.DataFrame(columns=["country_iso3"])

    non_sector = {"not specified", "multiple clusters/sectors (shared)", "multi-sector"}
    work = work[~work["cluster"].fillna("").astype(str).str.lower().isin(non_sector)].copy()
    if work.empty:
        return pd.DataFrame(columns=["country_iso3"])

    summary = (
        work.groupby("country_iso3", as_index=False)
        .agg(
            sector_count=("cluster", "nunique"),
            sector_requirements_usd=("sector_requirements_usd", "sum"),
            sector_funding_usd=("sector_funding_usd", "sum"),
            sector_median_funding_pct=("sector_funding_pct", "median"),
        )
        .copy()
    )
    worst = (
        work.sort_values(
            ["country_iso3", "sector_funding_pct", "sector_requirements_usd"],
            ascending=[True, True, False],
        )
        .drop_duplicates("country_iso3")
        .copy()
    )
    worst["worst_sector_gap_usd"] = (
        worst["sector_requirements_usd"] - worst["sector_funding_usd"]
    ).clip(lower=0)
    worst = worst.rename(
        columns={
            "cluster": "worst_sector",
            "sector_funding_pct": "worst_sector_funding_pct",
        }
    )[
        [
            "country_iso3",
            "worst_sector",
            "worst_sector_funding_pct",
            "worst_sector_gap_usd",
        ]
    ]
    return summary.merge(worst, on="country_iso3", how="left")


def _summarize_incoming_flows(flows: pd.DataFrame, year: int) -> pd.DataFrame:
    if flows.empty:
        return pd.DataFrame(
            columns=[
                "country_iso3",
                "incoming_total_usd",
                "incoming_flow_records",
                "incoming_source_count",
                "top_donor",
                "top_donor_usd",
                "top_donor_share",
            ]
        )

    work = flows[flows["year"] == year].copy()
    if work.empty:
        return pd.DataFrame(columns=["country_iso3"])
    work = work[
        work["status"].isin({"paid", "commitment"})
        & work["on_boundary"].eq("single")
        & (work["amount_usd"] > 0)
    ].copy()
    if work.empty:
        return pd.DataFrame(columns=["country_iso3"])

    summary = (
        work.groupby("country_iso3", as_index=False)
        .agg(
            incoming_total_usd=("amount_usd", "sum"),
            incoming_flow_records=("amount_usd", "size"),
            incoming_source_count=("source_organization", "nunique"),
        )
        .copy()
    )
    donors = (
        work.groupby(["country_iso3", "source_organization"], as_index=False)
        .agg(top_donor_usd=("amount_usd", "sum"))
        .sort_values(["country_iso3", "top_donor_usd"], ascending=[True, False])
        .drop_duplicates("country_iso3")
        .rename(columns={"source_organization": "top_donor"})
    )
    summary = summary.merge(donors, on="country_iso3", how="left")
    summary["top_donor_share"] = summary["top_donor_usd"] / summary["incoming_total_usd"].where(
        summary["incoming_total_usd"] > 0
    )
    return summary


def _summarize_outgoing_flows(flows: pd.DataFrame, year: int) -> pd.DataFrame:
    if flows.empty:
        return pd.DataFrame(
            columns=[
                "country_iso3",
                "outgoing_total_usd",
                "outgoing_flow_records",
                "outgoing_recipient_count",
                "top_recipient",
                "top_recipient_usd",
                "top_recipient_share",
            ]
        )

    work = flows[flows["year"] == year].copy()
    if work.empty:
        return pd.DataFrame(columns=["country_iso3"])
    work = work[
        work["status"].isin({"paid", "commitment"})
        & work["on_boundary"].eq("single")
        & (work["amount_usd"] > 0)
    ].copy()
    if work.empty:
        return pd.DataFrame(columns=["country_iso3"])

    summary = (
        work.groupby("country_iso3", as_index=False)
        .agg(
            outgoing_total_usd=("amount_usd", "sum"),
            outgoing_flow_records=("amount_usd", "size"),
            outgoing_recipient_count=("dest_organization", "nunique"),
        )
        .copy()
    )
    recipients = (
        work.groupby(["country_iso3", "dest_organization"], as_index=False)
        .agg(top_recipient_usd=("amount_usd", "sum"))
        .sort_values(["country_iso3", "top_recipient_usd"], ascending=[True, False])
        .drop_duplicates("country_iso3")
        .rename(columns={"dest_organization": "top_recipient"})
    )
    summary = summary.merge(recipients, on="country_iso3", how="left")
    summary["top_recipient_share"] = summary["top_recipient_usd"] / summary[
        "outgoing_total_usd"
    ].where(summary["outgoing_total_usd"] > 0)
    return summary


def load_normalized_inputs(year: int) -> dict[str, pd.DataFrame]:
    hno_year, hno_path = _latest_hno_path(year)
    funding_path = _require_existing("FTS funding CSV", "fts_requirements_funding_global.csv")
    hrp_path = _require_existing(
        "HRP CSV", "humanitarian-response-plans.csv", "humanitarian_response_plans.csv"
    )

    hno = normalize_hno(hno_path, hno_year)
    hno["hno_year"] = hno_year
    funding = normalize_funding(funding_path)
    hrp = normalize_hrp(hrp_path)

    cbpf_path = raw_path("cbpf_project_summary.csv")
    if cbpf_path.exists() and cbpf_path.stat().st_size > 0:
        cbpf = normalize_cbpf(cbpf_path)
    else:
        cbpf = pd.DataFrame(columns=["country_iso3", "year", "cbpf_budget_usd", "cbpf_projects"])

    sector_path = _existing_path(
        "fts_requirements_funding_globalcluster_global.csv",
        "fts_requirements_funding_cluster_global.csv",
    )
    if sector_path is not None:
        sector_funding = normalize_sector_funding(sector_path)
    else:
        sector_funding = pd.DataFrame(columns=["country_iso3", "year"])

    population_path = _existing_path("cod_population_admin0.csv")
    if population_path is not None:
        population = normalize_population_admin0(population_path)
    else:
        population = pd.DataFrame(
            columns=[
                "country_iso3",
                "population_baseline",
                "population_reference_year",
                "population_source",
            ]
        )

    incoming_path = _existing_path("fts_incoming_funding_global.csv")
    if incoming_path is not None:
        incoming_flows = normalize_funding_flows(incoming_path, boundary="incoming")
    else:
        incoming_flows = pd.DataFrame(columns=["country_iso3", "year"])

    outgoing_path = _existing_path("fts_outgoing_funding_global.csv")
    if outgoing_path is not None:
        outgoing_flows = normalize_funding_flows(outgoing_path, boundary="outgoing")
    else:
        outgoing_flows = pd.DataFrame(columns=["country_iso3", "year"])

    return {
        "hno": hno,
        "funding": funding,
        "hrp": hrp,
        "cbpf": cbpf,
        "sector_funding": sector_funding,
        "population": population,
        "incoming_flows": incoming_flows,
        "outgoing_flows": outgoing_flows,
    }


def build_rankings(
    query: str | QuerySpec | None = None,
    *,
    year: int | None = None,
    min_people_in_need: int | None = None,
    auto_download: bool = False,
    download_years: Iterable[int] | None = None,
) -> pd.DataFrame:
    spec = query if isinstance(query, QuerySpec) else parse_query(query)
    if year is not None:
        spec.year = year
    if min_people_in_need is not None:
        spec.min_people_in_need = min_people_in_need
    if spec.min_people_in_need is None:
        spec.min_people_in_need = DEFAULT_MIN_PEOPLE_IN_NEED
    if spec.year is None:
        spec.year = DEFAULT_YEAR

    if auto_download:
        years = tuple(download_years or (spec.year,))
        download_core_data(years=years, include_cbpf=True)

    inputs = load_normalized_inputs(spec.year)
    need = summarize_need(inputs["hno"], sector=spec.sector)
    if need.empty:
        return need

    need = need.rename(columns={"year": "hno_year"})
    need["year"] = spec.year

    funding_year = inputs["funding"][inputs["funding"]["year"] == spec.year].copy()
    cbpf_year = inputs["cbpf"][inputs["cbpf"]["year"] == spec.year].copy()
    sector_year = _summarize_sector_stress(inputs["sector_funding"], spec.year)
    incoming_year = _summarize_incoming_flows(inputs["incoming_flows"], spec.year)
    outgoing_year = _summarize_outgoing_flows(inputs["outgoing_flows"], spec.year)

    ranked = need.merge(
        funding_year.drop(columns=["year"], errors="ignore"),
        on="country_iso3",
        how="left",
    ).merge(
        cbpf_year.drop(columns=["year"], errors="ignore"),
        on="country_iso3",
        how="left",
    ).merge(
        inputs["population"],
        on="country_iso3",
        how="left",
    ).merge(
        sector_year,
        on="country_iso3",
        how="left",
    ).merge(
        incoming_year,
        on="country_iso3",
        how="left",
    ).merge(
        outgoing_year,
        on="country_iso3",
        how="left",
    )

    ranked["requirements_usd"] = pd.to_numeric(ranked["requirements_usd"], errors="coerce")
    ranked["funding_usd"] = pd.to_numeric(ranked["funding_usd"], errors="coerce")
    ranked["funding_pct"] = pd.to_numeric(ranked["funding_pct"], errors="coerce")
    ranked["cbpf_budget_usd"] = pd.to_numeric(ranked["cbpf_budget_usd"], errors="coerce").fillna(0)
    ranked["cbpf_projects"] = pd.to_numeric(ranked["cbpf_projects"], errors="coerce").fillna(0)
    for col in (
        "population_baseline",
        "population_reference_year",
        "sector_count",
        "sector_requirements_usd",
        "sector_funding_usd",
        "sector_median_funding_pct",
        "worst_sector_funding_pct",
        "worst_sector_gap_usd",
        "incoming_total_usd",
        "incoming_flow_records",
        "incoming_source_count",
        "top_donor_usd",
        "top_donor_share",
        "outgoing_total_usd",
        "outgoing_flow_records",
        "outgoing_recipient_count",
        "top_recipient_usd",
        "top_recipient_share",
    ):
        if col in ranked.columns:
            ranked[col] = pd.to_numeric(ranked[col], errors="coerce")
    ranked["pin_population_share"] = ranked["people_in_need"] / ranked["population_baseline"].where(
        ranked["population_baseline"] > 0
    )

    ranked["funding_gap_for_score"] = 1 - ranked["funding_pct"].clip(lower=0, upper=1)
    ranked.loc[ranked["funding_gap_for_score"].isna(), "funding_gap_for_score"] = 1.0
    ranked["unmet_people_proxy"] = ranked["people_in_need"] * ranked["funding_gap_for_score"]
    ranked["cbpf_per_person_in_need"] = ranked["cbpf_budget_usd"] / ranked["people_in_need"].where(
        ranked["people_in_need"] > 0
    )

    ranked["need_scale"] = _percent_rank(
        ranked["people_in_need"].apply(lambda value: pd.NA if pd.isna(value) else math.log1p(value))
    )
    ranked["unmet_need_scale"] = _percent_rank(
        ranked["unmet_people_proxy"].apply(lambda value: pd.NA if pd.isna(value) else math.log1p(value))
    )
    ranked["cbpf_gap_scale"] = 1 - _percent_rank(ranked["cbpf_per_person_in_need"].fillna(0))

    recent_years = {spec.year - 2, spec.year - 1, spec.year}
    funding_recent = inputs["funding"][inputs["funding"]["year"].isin(recent_years)].copy()
    chronic = (
        funding_recent.assign(
            is_underfunded=funding_recent["funding_pct"] < DEFAULT_CHRONIC_FUNDING_THRESHOLD
        )
        .groupby("country_iso3", as_index=False)
        .agg(
            underfunded_years_last_3=("is_underfunded", "sum"),
            observed_funding_years_last_3=("year", "nunique"),
        )
    )
    ranked = ranked.merge(chronic, on="country_iso3", how="left")
    ranked["underfunded_years_last_3"] = ranked["underfunded_years_last_3"].fillna(0)
    ranked["observed_funding_years_last_3"] = ranked["observed_funding_years_last_3"].fillna(0)
    ranked["chronic_scale"] = ranked["underfunded_years_last_3"] / 3

    ranked["overlooked_score"] = 100 * (
        0.30 * ranked["unmet_need_scale"]
        + 0.25 * ranked["funding_gap_for_score"]
        + 0.20 * ranked["need_scale"]
        + 0.15 * ranked["cbpf_gap_scale"]
        + 0.10 * ranked["chronic_scale"]
    )

    ranked = add_country_metadata(ranked)
    ranked["data_quality_flags"] = ranked.apply(_quality_flags, axis=1)
    ranked["supplemental_data_flags"] = ranked.apply(_supplemental_flags, axis=1)
    ranked["confidence"] = ranked.apply(_confidence, axis=1)
    ranked["overlooked_level"] = ranked["overlooked_score"].apply(_score_level)

    if spec.region:
        region_countries = REGION_SCOPES.get(spec.region, set())
        ranked = ranked[ranked["country_iso3"].isin(region_countries)]
    if spec.countries:
        ranked = ranked[ranked["country_iso3"].isin(spec.countries)]
    if spec.min_people_in_need:
        ranked = ranked[ranked["people_in_need"] >= spec.min_people_in_need]
    if spec.funding_pct_max is not None:
        ranked = ranked[(ranked["funding_pct"].isna()) | (ranked["funding_pct"] <= spec.funding_pct_max)]

    ordered_cols = [
        "rank",
        "country",
        "country_iso3",
        "region",
        "year",
        "hno_year",
        "sector_label",
        "need_method",
        "need_selection",
        "source_file",
        "people_in_need",
        "requirements_usd",
        "funding_usd",
        "funding_pct",
        "appeal_names",
        "appeal_types",
        "cbpf_budget_usd",
        "cbpf_projects",
        "cbpf_per_person_in_need",
        "population_baseline",
        "population_reference_year",
        "pin_population_share",
        "population_source",
        "sector_count",
        "sector_requirements_usd",
        "sector_funding_usd",
        "sector_median_funding_pct",
        "worst_sector",
        "worst_sector_funding_pct",
        "worst_sector_gap_usd",
        "incoming_total_usd",
        "incoming_flow_records",
        "incoming_source_count",
        "top_donor",
        "top_donor_usd",
        "top_donor_share",
        "outgoing_total_usd",
        "outgoing_flow_records",
        "outgoing_recipient_count",
        "top_recipient",
        "top_recipient_usd",
        "top_recipient_share",
        "overlooked_score",
        "overlooked_level",
        "underfunded_years_last_3",
        "observed_funding_years_last_3",
        "confidence",
        "data_quality_flags",
        "supplemental_data_flags",
        "lat",
        "lon",
        "explanation",
    ]
    if ranked.empty:
        return pd.DataFrame(columns=ordered_cols)

    ranked = ranked.sort_values(["overlooked_score", "people_in_need"], ascending=[False, False]).copy()
    ranked["rank"] = range(1, len(ranked) + 1)
    ranked["explanation"] = ranked.apply(_build_explanation, axis=1)

    for col in ordered_cols:
        if col not in ranked.columns:
            ranked[col] = pd.NA
    return ranked[ordered_cols]

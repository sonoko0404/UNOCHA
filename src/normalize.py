"""Normalization functions for the public humanitarian datasets."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .config import COUNTRY_ALIASES, COUNTRY_REFERENCE, PROCESSED_DIR, RAW_DIR


def clean_column(name: object) -> str:
    text = str(name).replace("\ufeff", "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def read_csv_drop_hxl(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, low_memory=False)
    df.columns = [clean_column(col) for col in df.columns]
    if not df.empty and str(df.iloc[0, 0]).startswith("#"):
        df = df.iloc[1:].reset_index(drop=True)
    return df


def to_number(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.replace(",", "", regex=False).str.strip()
    text = text.replace({"": None, "nan": None, "None": None})
    return pd.to_numeric(text, errors="coerce")


def normalize_country_key(value: object) -> str:
    text = str(value or "").upper()
    text = re.sub(r"^\(CLOSED\)\s*", "", text)
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(
        r"\b(HUMANITARIAN|COUNTRY|BASED|POOLED|FUND|FUNDS|ERF|CHF|CBPF|OCHA)\b",
        " ",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def alias_to_iso3(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    raw = str(value).strip().upper()

    key = normalize_country_key(raw)
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]

    if re.fullmatch(r"[A-Z]{3}", raw) and raw in COUNTRY_REFERENCE:
        return raw

    for alias, iso3 in COUNTRY_ALIASES.items():
        if alias in key:
            return iso3
    return None


def split_iso_codes(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return re.findall(r"\b[A-Z]{3}\b", str(value).upper())


def normalize_hno(path: Path, year: int) -> pd.DataFrame:
    df = read_csv_drop_hxl(path)
    if df.empty:
        return pd.DataFrame()

    country_col = "country_iso3" if "country_iso3" in df.columns else "country_code"
    if country_col not in df.columns:
        raise ValueError(f"HNO file {path} is missing a country ISO3 column")

    for col in ("population", "in_need", "targeted", "affected", "reached"):
        if col in df.columns:
            df[col] = to_number(df[col])
        else:
            df[col] = pd.NA

    sector_parts = []
    for col in ("description", "sector", "cluster"):
        if col in df.columns:
            sector_parts.append(df[col].fillna("").astype(str))
    if sector_parts:
        sector_label = sector_parts[0]
        for part in sector_parts[1:]:
            sector_label = sector_label.where(sector_label.str.strip().ne(""), part)
    else:
        sector_label = pd.Series(["Unknown"] * len(df), index=df.index)

    df["country_iso3"] = df[country_col].astype(str).str.upper().str.strip()
    df["sector_label"] = sector_label.fillna("Unknown").astype(str).str.strip()
    df["sector_key"] = df["sector_label"].str.lower()
    df["year"] = year
    df["source_file"] = path.name

    admin_cols = [c for c in df.columns if re.fullmatch(r"admin_[0-9]+_(pcode|name)", c)]
    if admin_cols:
        national_mask = df[admin_cols].fillna("").astype(str).apply(
            lambda row: all(item.strip() == "" for item in row), axis=1
        )
        df["is_national_record"] = national_mask
        df["need_method"] = "subnational_record"
        df.loc[national_mask, "need_method"] = "national_hno_record"
    else:
        df["is_national_record"] = True
        df["need_method"] = "national_hno_record"

    keep_cols = [
        "country_iso3",
        "year",
        "sector_label",
        "sector_key",
        "category",
        "population",
        "in_need",
        "targeted",
        "affected",
        "reached",
        "is_national_record",
        "need_method",
        "source_file",
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = pd.NA
    return df[keep_cols].dropna(subset=["country_iso3"])


def summarize_need(hno: pd.DataFrame, *, sector: str | None = None) -> pd.DataFrame:
    """Summarize country-level need without summing sector PIN values.

    Sector PINs often overlap, so the default country summary uses an
    intersectoral row when available and otherwise the maximum reported PIN.
    """

    if hno.empty:
        return pd.DataFrame()

    work = hno.copy()
    work = work[work["in_need"].fillna(0) > 0]
    if "is_national_record" not in work.columns:
        work["is_national_record"] = True
    if sector:
        sector = sector.lower()
        sector_mask = work["sector_key"].fillna("").str.contains(sector, regex=False)
        filtered = work[sector_mask].copy()
        if not filtered.empty:
            work = filtered
            work["need_selection"] = f"sector:{sector}"
        else:
            work["need_selection"] = f"sector_not_found_fallback:{sector}"
        selected_idx = []
        selections = {}
        for _, group in work.groupby(["country_iso3", "year"]):
            national = group[group["is_national_record"].fillna(False)]
            if not national.empty:
                selected = national["in_need"].idxmax()
                selections[selected] = f"sector:{sector}:national"
            else:
                selected = group["in_need"].idxmax()
                selections[selected] = f"sector:{sector}:subnational_max_record"
            selected_idx.append(selected)
        idx = pd.Index(selected_idx)
        selection_series = pd.Series(work.index.map(selections), index=work.index)
        work["need_selection"] = selection_series.fillna(work["need_selection"])
    else:
        overall_pattern = (
            "intersectoral|inter-sector|multi sector|multi-sector|overall|total|plan caseload"
        )
        selected_idx = []
        selections = {}
        for group_key, group in work.groupby(["country_iso3", "year"]):
            national = group[group["is_national_record"].fillna(False)]
            candidate_group = national if not national.empty else group
            overall = candidate_group[
                candidate_group["sector_key"].fillna("").str.contains(overall_pattern, regex=True)
            ]
            if not overall.empty:
                selected = overall["in_need"].idxmax()
                selections[selected] = "intersectoral_or_plan_caseload_hno"
            else:
                selected = candidate_group["in_need"].idxmax()
                if national.empty:
                    selections[selected] = "subnational_max_record_no_intersectoral"
                else:
                    selections[selected] = "max_reported_pin_no_intersectoral"
            selected_idx.append(selected)
        idx = pd.Index(selected_idx)
        selection_series = pd.Series(work.index.map(selections), index=work.index)
        work["need_selection"] = selection_series.fillna("")

    summary = work.loc[idx].copy()
    summary = summary.rename(columns={"in_need": "people_in_need"})
    return summary[
        [
            "country_iso3",
            "year",
            "sector_label",
            "people_in_need",
            "population",
            "targeted",
            "affected",
            "need_method",
            "need_selection",
            "source_file",
        ]
    ]


def normalize_funding(path: Path) -> pd.DataFrame:
    df = read_csv_drop_hxl(path)
    rename = {
        "countrycode": "country_code",
        "typename": "type_name",
        "percentfunded": "percent_funded",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    required = {"country_code", "year", "requirements", "funding"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Funding file {path} missing columns: {sorted(missing)}")

    df["year"] = to_number(df["year"]).astype("Int64")
    df["requirements"] = to_number(df["requirements"]).fillna(0)
    df["funding"] = to_number(df["funding"]).fillna(0)
    if "percent_funded" in df.columns:
        df["percent_funded"] = to_number(df["percent_funded"])
    else:
        df["percent_funded"] = pd.NA

    if "name" not in df.columns:
        df["name"] = ""
    if "type_name" not in df.columns:
        df["type_name"] = ""

    # Coverage should be measured against appeals/plans with stated
    # requirements. Country-level "Not specified" flows are useful context but
    # would overstate plan coverage if added to the numerator here.
    df = df[df["requirements"] > 0].copy()

    records = []
    for _, row in df.iterrows():
        iso_codes = split_iso_codes(row.get("country_code"))
        if not iso_codes:
            continue
        for iso3 in iso_codes:
            records.append(
                {
                    "country_iso3": iso3,
                    "year": row["year"],
                    "appeal_name": row.get("name", ""),
                    "appeal_type": row.get("type_name", ""),
                    "requirements_usd": row["requirements"],
                    "funding_usd": row["funding"],
                    "reported_percent_funded": row["percent_funded"],
                }
            )
    exploded = pd.DataFrame.from_records(records)
    if exploded.empty:
        return exploded

    grouped = (
        exploded.groupby(["country_iso3", "year"], as_index=False)
        .agg(
            requirements_usd=("requirements_usd", "sum"),
            funding_usd=("funding_usd", "sum"),
            appeal_names=("appeal_name", lambda values: "; ".join(sorted(set(map(str, values)))[:5])),
            appeal_types=("appeal_type", lambda values: "; ".join(sorted(set(map(str, values)))[:5])),
        )
        .copy()
    )
    grouped["funding_pct"] = grouped["funding_usd"] / grouped["requirements_usd"].where(
        grouped["requirements_usd"] > 0
    )
    grouped.loc[grouped["funding_pct"] > 1, "funding_pct"] = 1.0
    return grouped


def normalize_sector_funding(path: Path) -> pd.DataFrame:
    """Normalize FTS cluster/global-cluster funding rows.

    The output keeps one row per country, year, and cluster. Country codes can
    contain multiple ISO3 values in regional plans, so they are exploded before
    aggregation.
    """

    df = read_csv_drop_hxl(path)
    rename = {
        "countrycode": "country_code",
        "percentfunded": "percent_funded",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    required = {"country_code", "year", "cluster", "requirements", "funding"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Sector funding file {path} missing columns: {sorted(missing)}")

    df["year"] = to_number(df["year"]).astype("Int64")
    df["requirements"] = to_number(df["requirements"]).fillna(0)
    df["funding"] = to_number(df["funding"]).fillna(0)
    df = df[df["requirements"] > 0].copy()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "country_iso3",
                "year",
                "cluster",
                "sector_requirements_usd",
                "sector_funding_usd",
                "sector_funding_pct",
            ]
        )

    records = []
    for _, row in df.iterrows():
        iso_codes = split_iso_codes(row.get("country_code"))
        if not iso_codes:
            continue
        cluster = str(row.get("cluster", "") or "").strip() or "Unknown"
        for iso3 in iso_codes:
            records.append(
                {
                    "country_iso3": iso3,
                    "year": row["year"],
                    "cluster": cluster,
                    "sector_requirements_usd": row["requirements"],
                    "sector_funding_usd": row["funding"],
                }
            )

    exploded = pd.DataFrame.from_records(records)
    if exploded.empty:
        return exploded

    grouped = (
        exploded.groupby(["country_iso3", "year", "cluster"], as_index=False)
        .agg(
            sector_requirements_usd=("sector_requirements_usd", "sum"),
            sector_funding_usd=("sector_funding_usd", "sum"),
        )
        .copy()
    )
    grouped["sector_funding_pct"] = grouped["sector_funding_usd"] / grouped[
        "sector_requirements_usd"
    ].where(grouped["sector_requirements_usd"] > 0)
    grouped["sector_funding_pct"] = grouped["sector_funding_pct"].clip(lower=0, upper=1)
    return grouped


def normalize_population_admin0(path: Path) -> pd.DataFrame:
    """Normalize COD admin0 total population baselines."""

    df = read_csv_drop_hxl(path)
    rename = {
        "iso3": "country_iso3",
        "population": "population_baseline",
        "reference_year": "population_reference_year",
        "source": "population_source",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    required = {"country_iso3", "population_baseline", "population_reference_year"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Population file {path} missing columns: {sorted(missing)}")

    for col in ("population_group", "gender", "age_range"):
        if col not in df.columns:
            df[col] = ""
    admin_cols = [col for col in df.columns if re.fullmatch(r"adm[1-4]_pcode", col)]
    if admin_cols:
        admin0_mask = df[admin_cols].fillna("").astype(str).apply(
            lambda row: all(item.strip() == "" for item in row), axis=1
        )
    else:
        admin0_mask = pd.Series([True] * len(df), index=df.index)

    total_mask = (
        df["population_group"].fillna("").astype(str).str.upper().eq("T_TL")
        & df["gender"].fillna("").astype(str).str.lower().eq("all")
        & df["age_range"].fillna("").astype(str).str.lower().eq("all")
    )
    work = df[admin0_mask & total_mask].copy()
    if work.empty:
        return pd.DataFrame(
            columns=[
                "country_iso3",
                "population_baseline",
                "population_reference_year",
                "population_source",
            ]
        )

    work["country_iso3"] = work["country_iso3"].astype(str).str.upper().str.strip()
    work["population_baseline"] = to_number(work["population_baseline"])
    work["population_reference_year"] = to_number(work["population_reference_year"]).astype("Int64")
    if "population_source" not in work.columns:
        work["population_source"] = ""
    work = work.dropna(subset=["country_iso3", "population_baseline"]).copy()
    work = work.sort_values(["country_iso3", "population_reference_year"])
    work = work.drop_duplicates(subset=["country_iso3"], keep="last")
    return work[
        [
            "country_iso3",
            "population_baseline",
            "population_reference_year",
            "population_source",
        ]
    ]


def normalize_funding_flows(path: Path, *, boundary: str | None = None) -> pd.DataFrame:
    """Normalize country-specific FTS flow details.

    Shared multi-country flows are intentionally excluded by default through
    the `onBoundary == single` rule in the scoring layer, so country totals are
    not inflated by assigning the same regional amount to every destination.
    """

    df = read_csv_drop_hxl(path)
    rename = {
        "budgetyear": "year",
        "amountusd": "amount_usd",
        "srcorganization": "source_organization",
        "srclocations": "source_locations",
        "destlocations": "dest_locations",
        "destorganization": "dest_organization",
        "destglobalclusters": "dest_global_clusters",
        "onboundary": "on_boundary",
        "flowtype": "flow_type",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    required = {"year", "amount_usd", "source_organization", "dest_locations"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Funding flow file {path} missing columns: {sorted(missing)}")

    df["year"] = to_number(df["year"]).astype("Int64")
    df["amount_usd"] = to_number(df["amount_usd"]).fillna(0)
    for col in (
        "status",
        "on_boundary",
        "flow_type",
        "boundary",
        "dest_global_clusters",
        "dest_organization",
    ):
        if col not in df.columns:
            df[col] = ""
    if boundary is not None and "boundary" in df.columns:
        df = df[df["boundary"].fillna("").astype(str).str.lower().eq(boundary.lower())].copy()

    records = []
    for _, row in df.iterrows():
        iso_codes = split_iso_codes(row.get("dest_locations"))
        if len(iso_codes) != 1:
            continue
        records.append(
            {
                "country_iso3": iso_codes[0],
                "year": row["year"],
                "amount_usd": row["amount_usd"],
                "source_organization": str(row.get("source_organization", "") or "").strip()
                or "Unspecified source",
                "source_locations": str(row.get("source_locations", "") or "").strip(),
                "dest_organization": str(row.get("dest_organization", "") or "").strip()
                or "Unspecified recipient",
                "dest_global_clusters": str(row.get("dest_global_clusters", "") or "").strip(),
                "status": str(row.get("status", "") or "").strip().lower(),
                "flow_type": str(row.get("flow_type", "") or "").strip(),
                "on_boundary": str(row.get("on_boundary", "") or "").strip().lower(),
                "boundary": str(row.get("boundary", "") or "").strip().lower(),
            }
        )
    return pd.DataFrame.from_records(records)


def normalize_hrp(path: Path) -> pd.DataFrame:
    df = read_csv_drop_hxl(path)
    if df.empty:
        return df
    if "locations" not in df.columns:
        return pd.DataFrame()

    status_candidates = [
        "status",
        "plan_status",
        "publication_status",
        "workflow_status",
        "state",
    ]

    def infer_status(row: pd.Series, year_int: int) -> tuple[bool, str, str, str]:
        raw_status = ""
        for col in status_candidates:
            if col in row.index and str(row.get(col, "") or "").strip():
                raw_status = str(row.get(col, "") or "").strip()
                break

        status_text = raw_status.lower()
        if re.search(r"\b(closed|inactive|archived|cancelled|canceled|expired)\b", status_text):
            return False, raw_status, "status_not_active", "matched_by_status_field"
        if re.search(r"\b(active|published|ongoing|current|open)\b", status_text):
            return True, raw_status, "status_active", "matched_by_status_field"

        start_date = str(row.get("startdate", "") or "")
        end_date = str(row.get("enddate", "") or "")
        start = pd.to_datetime(start_date, errors="coerce")
        end = pd.to_datetime(end_date, errors="coerce")
        if not pd.isna(start) and not pd.isna(end):
            year_start = pd.Timestamp(year_int, 1, 1)
            year_end = pd.Timestamp(year_int, 12, 31)
            is_active = bool(start <= year_end and end >= year_start)
            if is_active:
                if raw_status:
                    return True, raw_status, "active_date_overlap_status_unclear", "matched_by_date_status_unclear"
                return True, "date_overlap_no_status_field", "active_date_overlap_no_status_field", "matched_by_year_and_date_no_status_field"
            if raw_status:
                return False, raw_status, "not_active_by_date_status_unclear", "matched_by_date_status_unclear"
            return False, "date_not_overlapping_no_status_field", "not_active_by_date_no_status_field", "matched_by_year_and_date_no_status_field"

        if raw_status:
            return False, raw_status, "unknown_status_value", "status_unrecognized"
        return False, "no_status_or_dates", "unknown_status_no_dates", "no_status_or_dates"

    records = []
    for _, row in df.iterrows():
        year_values = re.findall(r"\b20\d{2}\b", str(row.get("years", "")))
        locations = split_iso_codes(row.get("locations"))
        categories = str(row.get("categories", "") or "")
        plan_type = categories.split("|")[0].strip() if categories else ""
        for iso3 in locations:
            for year in year_values:
                year_int = int(year)
                is_active, raw_status, normalized_status, quality = infer_status(row, year_int)
                records.append(
                    {
                        "country_iso3": iso3,
                        "year": year_int,
                        "hrp_year": year_int,
                        "plan_code": row.get("code", ""),
                        "plan_name": row.get("planversion", ""),
                        "plan_type": plan_type,
                        "plan_categories": categories,
                        "start_date": row.get("startdate", ""),
                        "end_date": row.get("enddate", ""),
                        "hrp_status_raw": raw_status,
                        "hrp_status_normalized": normalized_status,
                        "hrp_is_active": is_active,
                        "hrp_data_quality": quality,
                    }
                )
    return pd.DataFrame.from_records(records)


def normalize_cbpf(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, low_memory=False)
    df.columns = [clean_column(col) for col in df.columns]
    if df.empty:
        return pd.DataFrame(
            columns=[
                "country_iso3",
                "year",
                "cbpf_budget_usd",
                "cbpf_projects",
                "cbpf_mapping_confidence",
                "cbpf_country_source",
            ]
        )

    year_col = "allocationyear"
    fund_col = "pooledfundname"
    budget_col = "budget"
    if year_col not in df.columns or fund_col not in df.columns or budget_col not in df.columns:
        raise ValueError(f"CBPF file {path} is missing required columns")

    df["year"] = to_number(df[year_col]).astype("Int64")
    df["cbpf_budget_usd"] = to_number(df[budget_col]).fillna(0)
    df["country_iso3"] = df[fund_col].apply(alias_to_iso3)
    if "allocationtypecategory" in df.columns:
        management_mask = df["allocationtypecategory"].fillna("").str.contains(
            "management", case=False, regex=False
        )
        df = df[~management_mask].copy()

    unmapped = df[df["country_iso3"].isna()].copy()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if not unmapped.empty:
        unmapped_summary = (
            unmapped.groupby([fund_col, "year"], dropna=False, as_index=False)
            .agg(
                unmapped_cbpf_budget_usd=("cbpf_budget_usd", "sum"),
                unmapped_cbpf_records=(fund_col, "size"),
            )
            .sort_values(["year", "unmapped_cbpf_budget_usd"], ascending=[False, False])
        )
        unmapped_summary.to_csv(PROCESSED_DIR / "unmapped_cbpf_funds.csv", index=False)
    else:
        pd.DataFrame(
            columns=[fund_col, "year", "unmapped_cbpf_budget_usd", "unmapped_cbpf_records"]
        ).to_csv(PROCESSED_DIR / "unmapped_cbpf_funds.csv", index=False)

    mapped = df.dropna(subset=["country_iso3", "year"]).copy()
    grouped = (
        mapped.groupby(["country_iso3", "year"], as_index=False)
        .agg(cbpf_budget_usd=("cbpf_budget_usd", "sum"), cbpf_projects=(fund_col, "count"))
        .copy()
    )
    grouped["cbpf_mapping_confidence"] = "alias_match"
    grouped["cbpf_country_source"] = "pooledfundname_alias_table"
    return grouped


def add_country_metadata(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["country"] = work["country_iso3"].map(
        lambda iso3: COUNTRY_REFERENCE.get(str(iso3), {}).get("country", str(iso3))
    )
    work["region"] = work["country_iso3"].map(
        lambda iso3: COUNTRY_REFERENCE.get(str(iso3), {}).get("region", "Unknown")
    )
    work["lat"] = work["country_iso3"].map(
        lambda iso3: COUNTRY_REFERENCE.get(str(iso3), {}).get("lat", pd.NA)
    )
    work["lon"] = work["country_iso3"].map(
        lambda iso3: COUNTRY_REFERENCE.get(str(iso3), {}).get("lon", pd.NA)
    )
    return work


def raw_path(name: str) -> Path:
    return RAW_DIR / name

"""Lightweight natural-language query parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import (
    COUNTRY_ALIASES,
    DEFAULT_MIN_PEOPLE_IN_NEED,
    DEFAULT_YEAR,
    REGION_SCOPES,
    SECTOR_ALIASES,
)
from .normalize import normalize_country_key


@dataclass
class QuerySpec:
    raw_query: str = ""
    year: int = DEFAULT_YEAR
    region: str | None = None
    countries: set[str] = field(default_factory=set)
    sector: str | None = None
    funding_pct_max: float | None = None
    min_people_in_need: int = DEFAULT_MIN_PEOPLE_IN_NEED


def _parse_percent_threshold(text: str) -> float | None:
    patterns = [
        r"(?:less than|under|below|lower than|received less than)\s+(\d+(?:\.\d+)?)\s*%",
        r"<\s*(\d+(?:\.\d+)?)\s*%",
        r"fund(?:ed|ing)?\s*(?:below|under|less than)\s*(\d+(?:\.\d+)?)\s*%",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return float(match.group(1)) / 100.0
    if re.search(r"\b(absent|negligible|unfunded)\b", text, flags=re.I):
        return 0.10
    return None


def _parse_min_people_in_need(text: str) -> int:
    pattern = r"(?:at least|over|more than|minimum|min)\s+(\d+(?:\.\d+)?)\s*(million|m|thousand|k)?"
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return DEFAULT_MIN_PEOPLE_IN_NEED
    value = float(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit in {"million", "m"}:
        value *= 1_000_000
    elif unit in {"thousand", "k"}:
        value *= 1_000
    return int(value)


def _parse_year(text: str) -> int:
    years = [int(year) for year in re.findall(r"\b20\d{2}\b", text)]
    return max(years) if years else DEFAULT_YEAR


def _parse_region(text: str) -> str | None:
    lower = text.lower()
    for region in sorted(REGION_SCOPES, key=len, reverse=True):
        if region in lower:
            return region
    return None


def _parse_sector(text: str) -> str | None:
    lower = text.lower()
    for alias, sector in sorted(SECTOR_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in lower:
            return sector
    return None


def _parse_countries(text: str) -> set[str]:
    normalized = normalize_country_key(text)
    countries: set[str] = set()
    for alias, iso3 in COUNTRY_ALIASES.items():
        if alias in normalized:
            countries.add(iso3)
    explicit_iso3 = re.findall(r"\b[A-Z]{3}\b", text.upper())
    for iso3 in explicit_iso3:
        if iso3 in set(COUNTRY_ALIASES.values()):
            countries.add(iso3)
    return countries


def parse_query(raw_query: str | None) -> QuerySpec:
    text = raw_query or ""
    return QuerySpec(
        raw_query=text,
        year=_parse_year(text),
        region=_parse_region(text),
        countries=_parse_countries(text),
        sector=_parse_sector(text),
        funding_pct_max=_parse_percent_threshold(text),
        min_people_in_need=_parse_min_people_in_need(text),
    )

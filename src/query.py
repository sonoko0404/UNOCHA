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
    hrp_filter: str | None = None
    severity_requested: bool = False
    food_insecurity_requested: bool = False
    displacement_requested: bool = False
    structural_neglect_requested: bool = False
    chronic_underfunding_requested: bool = False
    unparsed_terms: list[str] = field(default_factory=list)


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
    if re.search(r"\b(absent|negligible|unfunded|no funding|without funding)\b", text, flags=re.I):
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
    if "acute food insecurity" in lower:
        return "food"
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


def _parse_hrp_filter(text: str) -> str | None:
    lower = text.lower()
    if re.search(r"\b(no|without|missing)\s+(?:active\s+)?(?:hrp|humanitarian response plan|response plan)", lower):
        return "missing"
    if re.search(r"\bactive\s+(?:hrp|humanitarian response plan|response plan)s?\b", lower):
        return "active"
    if re.search(r"\b(?:hrp|humanitarian response plan|response plan)s?\b", lower):
        return "any"
    return None


def _parse_severity_requested(text: str) -> bool:
    return bool(re.search(r"\b(severity|severe|urgent|urgency|inform)\b", text, flags=re.I))


def _parse_food_insecurity_requested(text: str) -> bool:
    return bool(re.search(r"\b(acute food insecurity|food insecurity|ipc)\b", text, flags=re.I))


def _parse_displacement_requested(text: str) -> bool:
    return bool(re.search(r"\b(displacement|displaced|idp|idps|refugee|refugees)\b", text, flags=re.I))


def _parse_structural_neglect_requested(text: str) -> bool:
    patterns = [
        r"\bstructural\s+(?:neglect|underfunding)\b",
        r"\bchronic(?:ally)?\s+underfund(?:ed|ing)?\b",
        r"\bconsistently\s+underfund(?:ed|ing)?\b",
        r"\bunderfund(?:ed|ing)?\s+across\s+multiple\s+years\b",
        r"\bmultiple\s+years\b",
        r"\bacross\s+years\b",
    ]
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def _unparsed_terms(text: str, spec: QuerySpec) -> list[str]:
    lower = text.lower()
    recognized_phrases = set(REGION_SCOPES) | set(SECTOR_ALIASES) | {
        "active",
        "hrp",
        "hrps",
        "humanitarian",
        "response",
        "plan",
        "plans",
        "less",
        "than",
        "under",
        "below",
        "funding",
        "funded",
        "coverage",
        "people",
        "need",
        "minimum",
        "min",
        "million",
        "thousand",
        "severity",
        "severe",
        "inform",
        "food",
        "insecurity",
        "acute",
        "displacement",
        "displaced",
        "idp",
        "idps",
        "refugee",
        "refugees",
        "countries",
        "country",
        "crises",
        "crisis",
        "show",
        "which",
        "with",
        "have",
        "has",
        "and",
        "or",
        "the",
        "are",
        "but",
        "not",
        "currently",
        "top",
        "gap",
        "requested",
        "cbpf",
        "high",
        "low",
        "structural",
        "neglect",
        "chronic",
        "chronically",
        "consistently",
        "underfunded",
        "underfunding",
        "multiple",
        "years",
        "regions",
        "region",
        "hotspots",
    }
    for alias in COUNTRY_ALIASES:
        recognized_phrases.update(alias.lower().split())
    for region in REGION_SCOPES:
        if region in lower:
            recognized_phrases.update(region.split())
    for alias in SECTOR_ALIASES:
        if alias in lower:
            recognized_phrases.update(alias.split())

    tokens = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", lower)
    leftovers = []
    for token in tokens:
        clean = token.replace("-", " ")
        if token not in recognized_phrases and clean not in recognized_phrases:
            leftovers.append(token)
    return sorted(set(leftovers))


def parse_query(raw_query: str | None) -> QuerySpec:
    text = raw_query or ""
    structural_neglect_requested = _parse_structural_neglect_requested(text)
    spec = QuerySpec(
        raw_query=text,
        year=_parse_year(text),
        region=_parse_region(text),
        countries=_parse_countries(text),
        sector=_parse_sector(text),
        funding_pct_max=_parse_percent_threshold(text),
        min_people_in_need=_parse_min_people_in_need(text),
        hrp_filter=_parse_hrp_filter(text),
        severity_requested=_parse_severity_requested(text),
        food_insecurity_requested=_parse_food_insecurity_requested(text),
        displacement_requested=_parse_displacement_requested(text),
        structural_neglect_requested=structural_neglect_requested,
        chronic_underfunding_requested=structural_neglect_requested,
    )
    if spec.food_insecurity_requested and spec.sector is None:
        spec.sector = "food"
    spec.unparsed_terms = _unparsed_terms(text, spec)
    return spec

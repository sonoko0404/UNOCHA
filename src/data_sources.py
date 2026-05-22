"""Dataset discovery and download helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import requests

from .config import (
    CBPF_PROJECT_SUMMARY_CSV,
    DATASET_SLUGS,
    HDX_CKAN_API,
    RAW_DIR,
)


class DataDownloadError(RuntimeError):
    """Raised when a public data source cannot be downloaded."""


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def fetch_hdx_package(slug: str) -> dict:
    response = requests.get(HDX_CKAN_API, params={"id": slug}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise DataDownloadError(f"HDX package lookup failed for {slug}: {payload}")
    return payload["result"]


def _resource_matches(resource: dict, includes: Iterable[str]) -> bool:
    haystack = " ".join(
        str(resource.get(key, ""))
        for key in ("name", "url", "download_url", "description", "format")
    ).lower()
    return all(part.lower() in haystack for part in includes)


def select_resource_url(package: dict, includes: Iterable[str]) -> str:
    for resource in package.get("resources", []):
        if _resource_matches(resource, includes):
            return resource.get("download_url") or resource.get("url")
    available = [r.get("name") for r in package.get("resources", [])]
    raise DataDownloadError(
        f"No resource in {package.get('name')} matched {list(includes)}. "
        f"Available resources: {available}"
    )


def download_file(url: str, dest: Path, *, force: bool = False, timeout: int = 180) -> Path:
    ensure_dirs()
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest

    temp_dest = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with temp_dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    temp_dest.replace(dest)
    return dest


def download_core_data(
    years: Iterable[int] = (2026,),
    *,
    include_cbpf: bool = True,
    include_optional: bool = False,
    force: bool = False,
) -> dict[str, Path]:
    """Download the public datasets used by the prototype.

    The function uses HDX CKAN package metadata to avoid hard-coding resource
    IDs that may change when HDX refreshes a dataset.
    """

    ensure_dirs()
    paths: dict[str, Path] = {}

    hno_package = fetch_hdx_package(DATASET_SLUGS["hno"])
    for year in years:
        url = select_resource_url(hno_package, [str(year), "hno"])
        paths[f"hno_{year}"] = download_file(url, RAW_DIR / f"hno_{year}.csv", force=force)

    funding_package = fetch_hdx_package(DATASET_SLUGS["funding"])
    funding_url = select_resource_url(funding_package, ["fts_requirements_funding_global", "csv"])
    paths["funding"] = download_file(
        funding_url, RAW_DIR / "fts_requirements_funding_global.csv", force=force
    )

    hrp_package = fetch_hdx_package(DATASET_SLUGS["hrp"])
    hrp_url = select_resource_url(hrp_package, ["humanitarian-response-plans", "csv"])
    paths["hrp"] = download_file(hrp_url, RAW_DIR / "humanitarian_response_plans.csv", force=force)

    if include_cbpf:
        paths["cbpf"] = download_file(
            CBPF_PROJECT_SUMMARY_CSV,
            RAW_DIR / "cbpf_project_summary.csv",
            force=force,
            timeout=600,
        )

    if include_optional:
        population_package = fetch_hdx_package(DATASET_SLUGS["population"])
        population_url = select_resource_url(population_package, ["cod_population_admin0", "csv"])
        paths["population"] = download_file(
            population_url, RAW_DIR / "cod_population_admin0.csv", force=force
        )

        inform_package = fetch_hdx_package(DATASET_SLUGS["inform"])
        inform_url = select_resource_url(inform_package, ["2026", "inform", "xlsx"])
        paths["inform"] = download_file(inform_url, RAW_DIR / "inform_severity_2026.xlsx", force=force)

    manifest = {name: str(path.relative_to(RAW_DIR.parent.parent)) for name, path in paths.items()}
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return paths

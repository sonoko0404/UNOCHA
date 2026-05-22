"""Command line entry points for the prototype."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .data_sources import download_core_data
from .scoring import MissingRawDataError, build_rankings


def _format_for_console(df: pd.DataFrame, top: int) -> pd.DataFrame:
    cols = [
        "rank",
        "country",
        "country_iso3",
        "people_in_need",
        "funding_pct",
        "cbpf_budget_usd",
        "overlooked_score",
        "overlooked_level",
        "confidence",
        "data_quality_flags",
    ]
    view = df.head(top)[cols].copy()
    if not view.empty:
        view["funding_pct"] = view["funding_pct"].map(
            lambda value: "" if pd.isna(value) else f"{value:.1%}"
        )
        view["people_in_need"] = view["people_in_need"].map(lambda value: f"{value:,.0f}")
        view["cbpf_budget_usd"] = view["cbpf_budget_usd"].map(lambda value: f"${value:,.0f}")
        view["overlooked_score"] = view["overlooked_score"].map(lambda value: f"{value:.1f}")
    return view


def cmd_download(args: argparse.Namespace) -> None:
    paths = download_core_data(
        years=args.years,
        include_cbpf=not args.skip_cbpf,
        include_optional=args.include_optional,
        force=args.force,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")


def cmd_rank(args: argparse.Namespace) -> None:
    try:
        df = build_rankings(
            args.query,
            year=args.year,
            min_people_in_need=args.min_people_in_need,
            auto_download=args.auto_download,
            download_years=args.download_years,
        )
    except MissingRawDataError as exc:
        raise SystemExit(str(exc)) from exc

    if df.empty:
        print("No crises matched the selected filters.")
        return

    print(_format_for_console(df, args.top).to_string(index=False))
    if args.explain:
        print("\nTop explanations:")
        for _, row in df.head(args.top).iterrows():
            print(f"- #{int(row['rank'])} {row['country']}: {row['explanation']}")

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        print(f"\nWrote full results to {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Geo-Insight overlooked crisis ranker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download and cache source data")
    download.add_argument("--years", nargs="+", type=int, default=[2024, 2025, 2026])
    download.add_argument("--skip-cbpf", action="store_true", help="Skip the large CBPF project file")
    download.add_argument("--include-optional", action="store_true", help="Also download COD and INFORM data")
    download.add_argument("--force", action="store_true", help="Overwrite existing cached files")
    download.set_defaults(func=cmd_download)

    rank = subparsers.add_parser("rank", help="Build crisis rankings")
    rank.add_argument("--query", default="", help="Natural-language query or scope")
    rank.add_argument("--year", type=int, default=2026)
    rank.add_argument("--min-people-in-need", type=int, default=100_000)
    rank.add_argument("--top", type=int, default=10)
    rank.add_argument("--explain", action="store_true")
    rank.add_argument("--output", default="data/processed/ranking.csv")
    rank.add_argument("--auto-download", action="store_true")
    rank.add_argument("--download-years", nargs="+", type=int, default=None)
    rank.set_defaults(func=cmd_rank)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

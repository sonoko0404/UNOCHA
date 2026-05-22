"""Streamlit dashboard for the Geo-Insight prototype."""

from __future__ import annotations

import html
import importlib
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

import src.normalize as normalize_module
import src.query as query_module
import src.scoring as scoring_module

normalize_module = importlib.reload(normalize_module)
query_module = importlib.reload(query_module)
scoring_module = importlib.reload(scoring_module)
MissingRawDataError = scoring_module.MissingRawDataError
build_rankings = scoring_module.build_rankings
parse_query = query_module.parse_query


LEVEL_ORDER = ["Very High", "High", "Moderate", "Watch"]
LEVEL_COLORS = {
    "Very High": [198, 58, 58, 190],
    "High": [221, 130, 49, 185],
    "Moderate": [207, 169, 62, 180],
    "Watch": [50, 118, 113, 175],
}
LEVEL_HEX = {
    "Very High": "#c63a3a",
    "High": "#dd8231",
    "Moderate": "#cfa93e",
    "Watch": "#327671",
}
PROJECT_ROOT = Path(__file__).resolve().parent


def fmt_num(value: float | int | None) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:,.0f}"


def fmt_money(value: float | int | None) -> str:
    if pd.isna(value):
        return "n/a"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"


def fmt_pct(value: float | None) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value:.1%}"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --ocha-blue: #005a8c;
          --ink: #182126;
          --muted: #5d6970;
          --paper: #fbfaf7;
          --line: #d9dedf;
          --high: #c63a3a;
          --amber: #dd8231;
          --teal: #327671;
        }
        .stApp {
          background: #f4f5f2;
          color: var(--ink);
        }
        .block-container {
          padding-top: 3.2rem;
          padding-bottom: 3rem;
          max-width: 1380px;
        }
        [data-testid="stSidebar"] {
          background: #eef2f2;
          border-right: 1px solid var(--line);
        }
        .stMainBlockContainer {
          padding-top: 2.35rem;
        }
        h1, h2, h3 {
          letter-spacing: 0;
        }
        .hero {
          background: #102a38;
          color: #ffffff;
          border: 1px solid #163849;
          border-radius: 8px;
          padding: 28px 30px;
          margin-bottom: 18px;
        }
        .hero-eyebrow {
          color: #8fd4e8;
          font-size: 0.82rem;
          font-weight: 700;
          letter-spacing: .08em;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        .hero-title {
          font-size: clamp(2rem, 4vw, 4.5rem);
          line-height: 1.02;
          font-weight: 800;
          margin: 0 0 10px 0;
          letter-spacing: 0;
        }
        .hero-copy {
          max-width: 860px;
          color: #d8e4e8;
          font-size: 1.03rem;
          line-height: 1.55;
        }
        .query-panel {
          background: #ffffff;
          border: 2px solid #cad6d9;
          border-radius: 8px;
          padding: 22px 24px 18px 24px;
          margin: 8px 0 14px 0;
          box-shadow: 0 12px 30px rgba(29, 45, 53, 0.08);
        }
        .query-panel-title {
          font-size: 1.42rem;
          font-weight: 850;
          color: var(--ink);
          margin-bottom: 4px;
        }
        .query-panel-copy {
          color: var(--muted);
          font-size: 1rem;
          line-height: 1.42;
          margin-bottom: 10px;
        }
        .query-panel + div [data-testid="stTextInput"] label {
          display: none;
        }
        .query-panel + div [data-testid="stTextInput"] input {
          min-height: 108px;
          border-radius: 10px;
          border: 3px solid #b7c9cf;
          background: #fbfdfd;
          font-size: 1.48rem;
          font-weight: 600;
          color: #1d2d35;
          padding-left: 28px;
          padding-right: 28px;
          margin-bottom: 26px;
        }
        .query-panel + div [data-testid="stTextInput"] input:focus {
          border-color: var(--ocha-blue);
          box-shadow: 0 0 0 5px rgba(0, 90, 140, 0.16);
        }
        .metric-strip {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          margin: 12px 0 18px 0;
        }
        .metric-card {
          background: var(--paper);
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 15px 16px;
        }
        .metric-label {
          color: var(--muted);
          font-size: 0.76rem;
          text-transform: uppercase;
          font-weight: 700;
          letter-spacing: .06em;
        }
        .metric-value {
          font-size: clamp(1.35rem, 2.1vw, 1.65rem);
          font-weight: 800;
          margin-top: 4px;
          color: var(--ink);
          overflow-wrap: anywhere;
        }
        .metric-note {
          color: var(--muted);
          font-size: 0.82rem;
          margin-top: 4px;
        }
        .briefing-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          margin: 10px 0 20px 0;
        }
        .briefing-card {
          background: #ffffff;
          border: 1px solid var(--line);
          border-left: 5px solid var(--ocha-blue);
          border-radius: 8px;
          padding: 14px 15px;
          min-height: 148px;
        }
        .briefing-card.hot { border-left-color: var(--high); }
        .briefing-card.warn { border-left-color: var(--amber); }
        .briefing-card.teal { border-left-color: var(--teal); }
        .briefing-title {
          font-weight: 800;
          margin-bottom: 7px;
          color: var(--ink);
        }
        .briefing-body {
          color: #39474e;
          font-size: 0.92rem;
          line-height: 1.45;
        }
        .method-pill {
          display: inline-block;
          padding: 6px 10px;
          margin: 0 6px 8px 0;
          border-radius: 999px;
          border: 1px solid #cad4d7;
          color: #31434b;
          background: #ffffff;
          font-size: 0.85rem;
        }
        .board-panel {
          background: #ffffff;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 18px 20px;
          margin-bottom: 16px;
          box-shadow: 0 8px 24px rgba(29, 45, 53, 0.05);
        }
        .board-kicker {
          color: var(--muted);
          font-size: 0.78rem;
          font-weight: 800;
          letter-spacing: .08em;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .board-title {
          color: var(--ink);
          font-size: 1.28rem;
          font-weight: 850;
          margin-bottom: 6px;
        }
        .board-copy {
          color: #405159;
          font-size: 0.94rem;
          line-height: 1.48;
        }
        .insight-ribbon {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
          margin: 8px 0 18px 0;
        }
        .ribbon-item {
          background: #102a38;
          color: #ffffff;
          border-radius: 8px;
          padding: 12px 14px;
          min-height: 92px;
        }
        .ribbon-item:nth-child(2) {
          background: #5d3328;
        }
        .ribbon-item:nth-child(3) {
          background: #1f4d49;
        }
        .ribbon-item:nth-child(4) {
          background: #4a4f2b;
        }
        .ribbon-label {
          color: #a8d7e4;
          font-size: 0.74rem;
          text-transform: uppercase;
          font-weight: 800;
          letter-spacing: .07em;
          margin-bottom: 5px;
        }
        .ribbon-value {
          font-size: 1.28rem;
          font-weight: 850;
          line-height: 1.16;
        }
        .ribbon-note {
          color: #d7e7ea;
          font-size: 0.82rem;
          line-height: 1.35;
          margin-top: 5px;
        }
        .method-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          margin: 12px 0 18px 0;
        }
        .method-card {
          background: #ffffff;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 14px 15px;
          min-height: 126px;
        }
        .method-card-label {
          color: var(--muted);
          font-size: 0.74rem;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: .07em;
          margin-bottom: 6px;
        }
        .method-card-value {
          color: var(--ink);
          font-size: 1.18rem;
          font-weight: 850;
          line-height: 1.22;
        }
        .method-card-note {
          color: #4b5a61;
          font-size: 0.84rem;
          line-height: 1.38;
          margin-top: 6px;
        }
        div[data-testid="stTabs"] div[role="tablist"] {
          gap: 8px;
          background: #e7eded;
          border: 1px solid #d3dcde;
          border-radius: 8px;
          padding: 8px;
          margin-top: 18px;
          margin-bottom: 18px;
        }
        div[data-testid="stTabs"] button[role="tab"] {
          min-height: 52px;
          padding: 0 18px;
          border-radius: 7px;
          border: 1px solid transparent;
          color: #31434b;
          background: transparent;
          transition: background 160ms ease, color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
        }
        div[data-testid="stTabs"] button[role="tab"] p {
          font-size: 1.04rem;
          font-weight: 800;
          white-space: nowrap;
        }
        div[data-testid="stTabs"] button[role="tab"]:hover {
          background: #f8fbfb;
          border-color: #c9d5d8;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
          background: #102a38;
          border-color: #102a38;
          color: #ffffff;
          box-shadow: 0 8px 20px rgba(16, 42, 56, 0.18);
          transform: translateY(-1px);
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
          color: #ffffff;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::after {
          background: transparent;
        }
        .small-note {
          color: var(--muted);
          font-size: 0.88rem;
          line-height: 1.45;
        }
        @media (max-width: 900px) {
          .metric-strip, .briefing-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .insight-ribbon, .method-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 620px) {
          .metric-strip, .briefing-grid {
            grid-template-columns: 1fr;
          }
          .hero {
            padding: 22px 20px;
          }
          div[data-testid="stTabs"] button[role="tab"] {
            min-height: 46px;
            padding: 0 12px;
          }
          div[data-testid="stTabs"] button[role="tab"] p {
            font-size: 0.95rem;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def prepare_display_data(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    optional_cols = [
        "population_baseline",
        "pin_population_share",
        "worst_sector",
        "worst_sector_funding_pct",
        "worst_sector_gap_usd",
        "incoming_total_usd",
        "top_donor",
        "top_donor_share",
        "outgoing_total_usd",
        "top_recipient",
        "top_recipient_share",
        "supplemental_data_flags",
        "has_active_hrp",
        "active_hrp_names",
        "hrp_status",
        "severity_scale",
        "severity_rank",
        "severity_context",
        "severity_source",
        "cbpf_mapping_confidence",
        "cbpf_country_source",
    ]
    for col in optional_cols:
        if col not in work.columns:
            work[col] = pd.NA
    work["funding_gap"] = 1 - pd.to_numeric(work["funding_pct"], errors="coerce").clip(0, 1)
    work["funding_gap"] = work["funding_gap"].fillna(1.0)
    work["unmet_people_proxy"] = work["people_in_need"] * work["funding_gap"]
    work["pin_m"] = work["people_in_need"] / 1_000_000
    work["cbpf_m"] = work["cbpf_budget_usd"] / 1_000_000
    work["funding_pct_label"] = work["funding_pct"].map(fmt_pct)
    work["people_label"] = work["people_in_need"].map(fmt_num)
    work["cbpf_label"] = work["cbpf_budget_usd"].map(fmt_money)
    work["score_label"] = work["overlooked_score"].map(lambda value: f"{value:.1f}")
    work["pin_population_share_label"] = work["pin_population_share"].map(fmt_pct)
    work["worst_sector_label"] = work["worst_sector"].fillna("n/a").astype(str)
    work["worst_sector_funding_label"] = work["worst_sector_funding_pct"].map(fmt_pct)
    work["incoming_total_label"] = work["incoming_total_usd"].map(fmt_money)
    work["top_donor_label"] = work["top_donor"].fillna("n/a").astype(str)
    work["top_donor_share_label"] = work["top_donor_share"].map(fmt_pct)
    work["outgoing_total_label"] = work["outgoing_total_usd"].map(fmt_money)
    work["top_recipient_label"] = work["top_recipient"].fillna("n/a").astype(str)
    work["top_recipient_share_label"] = work["top_recipient_share"].map(fmt_pct)
    work["active_hrp_label"] = work["has_active_hrp"].map(lambda value: "yes" if bool(value) else "no")
    work["severity_scale_label"] = work["severity_scale"].map(fmt_pct)
    work["level_color"] = work["overlooked_level"].map(lambda level: LEVEL_COLORS.get(level, [80, 80, 80, 160]))
    work["level_hex"] = work["overlooked_level"].map(lambda level: LEVEL_HEX.get(level, "#777777"))
    work["map_radius"] = (work["people_in_need"].clip(lower=100_000).pow(0.5) * 85).clip(75_000, 850_000)
    return work


def metric_card(label: str, value: str, note: str = "") -> str:
    return (
        '<div class="metric-card">'
        f'<div class="metric-label">{html.escape(label)}</div>'
        f'<div class="metric-value">{html.escape(value)}</div>'
        f'<div class="metric-note">{html.escape(note)}</div>'
        "</div>"
    )


def briefing_card(title: str, body: str, tone: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    return (
        f'<div class="briefing-card{tone_class}">'
        f'<div class="briefing-title">{html.escape(title)}</div>'
        f'<div class="briefing-body">{html.escape(body)}</div>'
        "</div>"
    )


def ribbon_item(label: str, value: str, note: str) -> str:
    return (
        '<div class="ribbon-item">'
        f'<div class="ribbon-label">{html.escape(label)}</div>'
        f'<div class="ribbon-value">{html.escape(value)}</div>'
        f'<div class="ribbon-note">{html.escape(note)}</div>'
        "</div>"
    )


def method_card(label: str, value: str, note: str) -> str:
    return (
        '<div class="method-card">'
        f'<div class="method-card-label">{html.escape(label)}</div>'
        f'<div class="method-card-value">{html.escape(value)}</div>'
        f'<div class="method-card-note">{html.escape(note)}</div>'
        "</div>"
    )


def render_query_audit(query: str, selected_year: int, min_people: int) -> None:
    spec = parse_query(query)
    hrp_filter = getattr(spec, "hrp_filter", None)
    severity_requested = bool(getattr(spec, "severity_requested", False))
    unparsed_terms = getattr(spec, "unparsed_terms", [])
    cards = [
        method_card("Parsed year", str(selected_year), f"Query text year: {spec.year}; sidebar year takes precedence."),
        method_card("Parsed region", spec.region or "All regions", "Region aliases are rule-based."),
        method_card(
            "Parsed countries",
            ", ".join(sorted(spec.countries)) if spec.countries else "All matched countries",
            "Country names and ISO3 codes are matched against the local alias table.",
        ),
        method_card("Parsed sector", spec.sector or "All sectors", "Food insecurity queries map to the food sector when present."),
        method_card(
            "Funding ceiling",
            fmt_pct(spec.funding_pct_max) if spec.funding_pct_max is not None else "None",
            "'No funding', 'unfunded', and 'negligible' are treated as <=10%.",
        ),
        method_card("Minimum PIN", fmt_num(min_people), "Sidebar minimum people-in-need takes precedence."),
        method_card("HRP filter", hrp_filter or "None", "Supports active HRP, no HRP, and response plan wording."),
        method_card(
            "Severity terms",
            "requested" if severity_requested else "not requested",
            "Local severity context uses HNO PIN / COD population; no INFORM/IPC/IDP file is cached.",
        ),
        method_card(
            "Unparsed terms",
            ", ".join(unparsed_terms) if unparsed_terms else "None",
            "These words were not converted into filters and remain analyst context.",
        ),
    ]
    with st.expander("Interpreted query filters", expanded=bool(query.strip())):
        st.markdown(f'<div class="method-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_hero(year: int, query: str, matched: int) -> None:
    scope = "All available crises" if not query.strip() else query.strip()
    st.markdown(
        f"""
        <section class="hero">
          <div class="hero-eyebrow">Humanitarian financing gap intelligence</div>
          <div class="hero-title">Where need outpaces coverage</div>
          <div class="hero-copy">
            {html.escape(str(year))} ranking for <strong>{html.escape(scope)}</strong>.
            The prototype separates documented need from financing coverage, then surfaces
            countries that merit analyst review. Matched crises: <strong>{matched}</strong>.
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(df: pd.DataFrame) -> None:
    median_funding = df["funding_pct"].median(skipna=True)
    total_pin = df["people_in_need"].sum()
    very_high = int((df["overlooked_level"] == "Very High").sum())
    chronic = int((df["underfunded_years_last_3"] >= 2).sum())
    cards = [
        metric_card("People in Need", fmt_num(total_pin), "sum across matched rows"),
        metric_card("Median Coverage", fmt_pct(median_funding), "FTS funding / requirements"),
        metric_card("Very High", str(very_high), "top overlooked level"),
        metric_card("Chronic Signals", str(chronic), "below 40% in at least two observed years"),
    ]
    st.markdown(f'<div class="metric-strip">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_briefing(df: pd.DataFrame) -> None:
    top = df.iloc[0]
    lowest = df.dropna(subset=["funding_pct"]).sort_values("funding_pct").head(1)
    lowest_text = "No matched country has a usable FTS coverage ratio."
    if not lowest.empty:
        row = lowest.iloc[0]
        lowest_text = (
            f"{row['country']} has the lowest matched coverage ratio at "
            f"{fmt_pct(row['funding_pct'])}, with {fmt_num(row['people_in_need'])} people in need."
        )

    sector_text = "No matched sector-level FTS funding breakdown is available for this selection."
    sector_df = df.dropna(subset=["worst_sector_funding_pct"]).sort_values(
        "worst_sector_funding_pct"
    )
    if not sector_df.empty:
        row = sector_df.iloc[0]
        sector_text = (
            f"{row['country']} has the lowest matched sector coverage: "
            f"{row['worst_sector']} at {fmt_pct(row['worst_sector_funding_pct'])}."
        )

    flow_text = "No single-country outgoing FTS flow detail is available for this selection."
    flow_df = df.dropna(subset=["top_recipient_share"]).sort_values("top_recipient_share", ascending=False)
    if not flow_df.empty:
        row = flow_df.iloc[0]
        flow_text = (
            f"{row['country']} has the most concentrated outgoing flow detail: "
            f"{row['top_recipient']} accounts for {fmt_pct(row['top_recipient_share'])} "
            f"of matched paid/commitment records."
        )

    no_cbpf = int((df["cbpf_budget_usd"].fillna(0) <= 0).sum())
    chronic = int((df["underfunded_years_last_3"] >= 2).sum())
    median_score = df["overlooked_score"].median()
    cards = [
        briefing_card(
            "Top overlooked signal",
            (
                f"{top['country']} ranks first with an overlooked score of "
                f"{top['overlooked_score']:.1f}, {fmt_num(top['people_in_need'])} people in need, "
                f"and {fmt_pct(top['funding_pct'])} funding coverage."
            ),
            "hot",
        ),
        briefing_card("Sharpest coverage gap", lowest_text, "warn"),
        briefing_card("Sector stress lens", sector_text, "teal"),
        briefing_card("Flow concentration", flow_text),
        briefing_card(
            "Structural neglect lens",
            (
                f"{chronic} matched crises were below 40% funding coverage in at least two "
                "of the latest three observed years."
            ),
            "teal",
        ),
        briefing_card(
            "Pooled-fund caveat",
            (
                f"{no_cbpf} matched crises have no mapped CBPF allocation in the selected year. "
                "This is a pooled-fund signal, not total humanitarian financing."
            ),
        ),
    ]
    st.markdown("**Briefing Signals**")
    st.markdown(f'<div class="briefing-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="small-note">Median overlooked score for the current selection is '
        f'{median_score:.1f}. Results are triage signals for analyst review, not automated funding decisions.</div>',
        unsafe_allow_html=True,
    )


def render_map(df: pd.DataFrame) -> None:
    map_df = df.dropna(subset=["lat", "lon"]).copy()
    if map_df.empty:
        st.info("No map-ready coordinates are available for the current selection.")
        return

    center_lat = float(map_df["lat"].mean())
    center_lon = float(map_df["lon"].mean())
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_radius="map_radius",
        get_fill_color="level_color",
        get_line_color=[26, 36, 42, 220],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )
    text_layer = pdk.Layer(
        "TextLayer",
        data=map_df.head(12),
        get_position="[lon, lat]",
        get_text="country_iso3",
        get_size=13,
        get_color=[20, 28, 32, 230],
        get_alignment_baseline="'bottom'",
        get_pixel_offset=[0, -10],
    )
    deck = pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=1.35, pitch=0),
        layers=[layer, text_layer],
        tooltip={
            "html": (
                "<b>{country}</b><br/>"
                "Rank: #{rank}<br/>"
                "People in need: {people_label}<br/>"
                "PIN / COD population: {pin_population_share_label}<br/>"
                "Active HRP: {active_hrp_label}<br/>"
                "Severity context: {severity_scale_label}<br/>"
                "Funding coverage: {funding_pct_label}<br/>"
                "Lowest sector coverage: {worst_sector_label} ({worst_sector_funding_label})<br/>"
                "CBPF allocation: {cbpf_label}<br/>"
                "Top recipient share: {top_recipient_share_label}<br/>"
                "Score: {score_label} ({overlooked_level})<br/>"
                "Confidence: {confidence}<br/>"
                "Flags: {data_quality_flags}"
            ),
            "style": {"backgroundColor": "#102a38", "color": "white", "fontSize": "12px"},
        },
    )
    st.pydeck_chart(deck, width="stretch")

    legend = " ".join(
        f'<span class="method-pill"><span style="color:{LEVEL_HEX[level]}; font-weight:900;">●</span> {level}</span>'
        for level in LEVEL_ORDER
    )
    st.markdown(legend, unsafe_allow_html=True)


def render_ranking_table(df: pd.DataFrame) -> None:
    display_cols = [
        "rank",
        "country",
        "region",
        "people_in_need",
        "has_active_hrp",
        "funding_pct",
        "pin_population_share",
        "severity_scale",
        "worst_sector",
        "worst_sector_funding_pct",
        "cbpf_budget_usd",
        "cbpf_mapping_confidence",
        "cbpf_per_person_in_need",
        "top_recipient",
        "top_recipient_share",
        "overlooked_score",
        "overlooked_level",
        "confidence",
        "data_quality_flags",
        "supplemental_data_flags",
    ]
    st.dataframe(
        df[display_cols].style.format(
            {
                "people_in_need": "{:,.0f}",
                "funding_pct": "{:.1%}",
                "pin_population_share": "{:.1%}",
                "severity_scale": "{:.1%}",
                "worst_sector_funding_pct": "{:.1%}",
                "cbpf_budget_usd": "${:,.0f}",
                "cbpf_per_person_in_need": "${:,.2f}",
                "top_recipient_share": "{:.1%}",
                "overlooked_score": "{:.1f}",
            }
        ),
        width="stretch",
        hide_index=True,
    )


@st.cache_data(show_spinner=False)
def build_country_trend(country_iso3: str) -> pd.DataFrame:
    rows = []
    for trend_year in (2024, 2025, 2026):
        cached_path = PROJECT_ROOT / "data" / "processed" / f"ranking_{trend_year}_enriched.csv"
        if cached_path.exists() and cached_path.stat().st_size > 0:
            trend = pd.read_csv(cached_path)
        else:
            trend = build_rankings("", year=trend_year, min_people_in_need=0)
        match = trend[trend["country_iso3"] == country_iso3].copy()
        if match.empty:
            rows.append({"year": trend_year, "country_iso3": country_iso3})
        else:
            row = match.iloc[0].to_dict()
            rows.append(
                {
                    "year": trend_year,
                    "country_iso3": country_iso3,
                    "country": row.get("country"),
                    "funding_pct": row.get("funding_pct"),
                    "people_in_need": row.get("people_in_need"),
                    "overlooked_score": row.get("overlooked_score"),
                    "underfunded_years_last_3": row.get("underfunded_years_last_3"),
                    "has_active_hrp": row.get("has_active_hrp"),
                }
            )
    return pd.DataFrame(rows)


def render_charts(df: pd.DataFrame, top_n: int) -> None:
    chart_df = df.head(top_n).copy()
    if chart_df.empty:
        st.info("No chart data available for the current selection.")
        return

    top = df.iloc[0]
    coverage_df = df.dropna(subset=["funding_pct"]).copy()
    lowest = coverage_df.sort_values("funding_pct").head(1)
    lowest_country = "n/a"
    lowest_note = "No matched funding coverage ratio"
    if not lowest.empty:
        lowest_row = lowest.iloc[0]
        lowest_country = str(lowest_row["country"])
        lowest_note = f"{fmt_pct(lowest_row['funding_pct'])} funding coverage"

    region_df = (
        df.groupby("region", as_index=False)
        .agg(
            countries=("country", "count"),
            people_in_need=("people_in_need", "sum"),
            median_funding=("funding_pct", "median"),
            average_score=("overlooked_score", "mean"),
        )
        .sort_values("people_in_need", ascending=False)
    )
    largest_region = region_df.iloc[0]
    population_df = df.dropna(subset=["pin_population_share"]).copy()
    if population_df.empty:
        population_value = "n/a"
        population_note = "COD admin0 population baseline not matched"
    else:
        population_row = population_df.sort_values("pin_population_share", ascending=False).iloc[0]
        population_value = str(population_row["country"])
        population_note = (
            f"PIN equals {fmt_pct(population_row['pin_population_share'])} of the COD admin0 baseline"
        )

    ribbon = [
        ribbon_item(
            "Top pressure point",
            str(top["country"]),
            f"Score {top['overlooked_score']:.1f}; {fmt_num(top['people_in_need'])} people in need",
        ),
        ribbon_item("Lowest coverage", lowest_country, lowest_note),
        ribbon_item(
            "Largest regional load",
            str(largest_region["region"]),
            f"{fmt_num(largest_region['people_in_need'])} people in need across {int(largest_region['countries'])} crises",
        ),
        ribbon_item("Highest PIN share", population_value, population_note),
    ]
    st.markdown(f'<div class="insight-ribbon">{"".join(ribbon)}</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <section class="board-panel">
          <div class="board-kicker">Evidence matrix</div>
          <div class="board-title">Need scale against funding coverage</div>
          <div class="board-copy">
            The pressure zone is the lower-right part of the chart: more people in need,
            lower funding coverage. The 40% line is the chronic-underfunding threshold
            used by this prototype.
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    scatter_df = df.dropna(subset=["funding_pct", "people_in_need"]).copy()
    if not scatter_df.empty:
        median_pin = float(scatter_df["people_in_need"].median())
        pressure = (
            alt.Chart(scatter_df)
            .mark_circle(opacity=0.78, stroke="#1f2e35", strokeWidth=0.6)
            .encode(
                x=alt.X(
                    "people_in_need:Q",
                    scale=alt.Scale(type="log"),
                    title="People in need (log scale)",
                ),
                y=alt.Y(
                    "funding_pct:Q",
                    title="Funding coverage",
                    axis=alt.Axis(format="%"),
                    scale=alt.Scale(domain=[0, max(1.0, float(scatter_df["funding_pct"].max() or 1.0))]),
                ),
                size=alt.Size("overlooked_score:Q", title="Score", scale=alt.Scale(range=[100, 1100])),
                color=alt.Color(
                    "overlooked_level:N",
                    scale=alt.Scale(domain=LEVEL_ORDER, range=[LEVEL_HEX[x] for x in LEVEL_ORDER]),
                    title="Level",
                ),
                tooltip=[
                    alt.Tooltip("country:N"),
                    alt.Tooltip("people_in_need:Q", title="People in need", format=",.0f"),
                    alt.Tooltip("funding_pct:Q", title="Funding coverage", format=".1%"),
                    alt.Tooltip("cbpf_budget_usd:Q", title="CBPF allocation", format="$,.0f"),
                    alt.Tooltip("overlooked_score:Q", title="Score", format=".1f"),
                    alt.Tooltip("data_quality_flags:N", title="Flags"),
                ],
            )
        )
        threshold_rule = (
            alt.Chart(pd.DataFrame({"funding_pct": [0.4]}))
            .mark_rule(color="#c63a3a", strokeDash=[6, 5], size=2)
            .encode(y="funding_pct:Q")
        )
        median_rule = (
            alt.Chart(pd.DataFrame({"people_in_need": [median_pin]}))
            .mark_rule(color="#327671", strokeDash=[4, 4], size=1.5)
            .encode(x="people_in_need:Q")
        )
        st.altair_chart((pressure + threshold_rule + median_rule).properties(height=430), width="stretch")
    else:
        st.info("The current selection has no usable funding coverage values for a coverage matrix.")

    rank_chart = (
        alt.Chart(chart_df)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y("country:N", sort="-x", title=None),
            x=alt.X("overlooked_score:Q", title="Overlooked score"),
            color=alt.Color(
                "overlooked_level:N",
                scale=alt.Scale(domain=LEVEL_ORDER, range=[LEVEL_HEX[x] for x in LEVEL_ORDER]),
                title="Level",
            ),
            tooltip=[
                alt.Tooltip("country:N"),
                alt.Tooltip("people_in_need:Q", format=",.0f"),
                alt.Tooltip("funding_pct:Q", format=".1%"),
                alt.Tooltip("cbpf_budget_usd:Q", format="$,.0f"),
                alt.Tooltip("overlooked_score:Q", format=".1f"),
            ],
        )
        .properties(height=max(260, min(460, 30 * len(chart_df))))
    )

    cbpf_df = chart_df.sort_values("cbpf_per_person_in_need", ascending=True).copy()
    cbpf_chart = (
        alt.Chart(cbpf_df)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y("country:N", sort="x", title=None),
            x=alt.X("cbpf_per_person_in_need:Q", title="CBPF allocation per person in need"),
            color=alt.Color(
                "overlooked_level:N",
                scale=alt.Scale(domain=LEVEL_ORDER, range=[LEVEL_HEX[x] for x in LEVEL_ORDER]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("country:N"),
                alt.Tooltip("cbpf_per_person_in_need:Q", title="CBPF per PIN", format="$,.2f"),
                alt.Tooltip("cbpf_budget_usd:Q", title="CBPF allocation", format="$,.0f"),
                alt.Tooltip("people_in_need:Q", title="People in need", format=",.0f"),
            ],
        )
        .properties(height=max(260, min(460, 30 * len(cbpf_df))))
    )

    level_counts = (
        df.groupby(["region", "overlooked_level"], as_index=False)
        .size()
        .rename(columns={"size": "crises"})
    )
    level_counts["overlooked_level"] = pd.Categorical(
        level_counts["overlooked_level"], categories=LEVEL_ORDER, ordered=True
    )
    level_matrix = (
        alt.Chart(level_counts)
        .mark_rect(cornerRadius=3)
        .encode(
            y=alt.Y("region:N", sort="-x", title=None),
            x=alt.X("overlooked_level:N", sort=LEVEL_ORDER, title="Overlooked level"),
            color=alt.Color("crises:Q", scale=alt.Scale(scheme="yelloworangered"), title="Crises"),
            tooltip=[
                alt.Tooltip("region:N"),
                alt.Tooltip("overlooked_level:N", title="Level"),
                alt.Tooltip("crises:Q", title="Crises"),
            ],
        )
        .properties(height=max(240, min(420, 34 * len(region_df))))
    )

    region_chart = (
        alt.Chart(region_df)
        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
        .encode(
            y=alt.Y("region:N", sort="-x", title=None),
            x=alt.X("people_in_need:Q", title="People in need"),
            color=alt.Color("average_score:Q", scale=alt.Scale(scheme="yelloworangered"), title="Avg score"),
            tooltip=[
                alt.Tooltip("region:N"),
                alt.Tooltip("countries:Q"),
                alt.Tooltip("people_in_need:Q", format=",.0f"),
                alt.Tooltip("median_funding:Q", format=".1%"),
                alt.Tooltip("average_score:Q", format=".1f"),
            ],
        )
        .properties(height=max(240, min(420, 34 * len(region_df))))
    )

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown("**Score Ladder**")
        st.altair_chart(rank_chart, width="stretch")
    with c2:
        st.markdown("**CBPF Intensity**")
        st.altair_chart(cbpf_chart, width="stretch")

    c3, c4 = st.columns([1, 1])
    with c3:
        st.markdown("**Regional Load**")
        st.altair_chart(region_chart, width="stretch")
    with c4:
        st.markdown("**Region x Level Matrix**")
        st.altair_chart(level_matrix, width="stretch")

    st.markdown(
        """
        <section class="board-panel">
          <div class="board-kicker">Downloaded supplement lenses</div>
          <div class="board-title">Population exposure, sector stress, and flow concentration</div>
          <div class="board-copy">
            These views use the newly downloaded COD population, FTS global-cluster funding,
            and single-country FTS flow-detail files. Shared multi-country flows are excluded
            from concentration charts to avoid double counting.
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    sector_df = chart_df.dropna(subset=["worst_sector_funding_pct"]).copy()
    pop_chart_df = chart_df.dropna(subset=["pin_population_share"]).copy()
    flow_chart_df = chart_df.dropna(subset=["top_recipient_share"]).copy()
    c5, c6 = st.columns([1, 1])
    with c5:
        st.markdown("**Lowest Sector Coverage**")
        if sector_df.empty:
            st.info("No sector-level FTS funding breakdown is available for these rows.")
        else:
            sector_chart = (
                alt.Chart(sector_df.sort_values("worst_sector_funding_pct", ascending=True))
                .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
                .encode(
                    y=alt.Y("country:N", sort="x", title=None),
                    x=alt.X(
                        "worst_sector_funding_pct:Q",
                        title="Lowest sector funding coverage",
                        axis=alt.Axis(format="%"),
                        scale=alt.Scale(domain=[0, 1]),
                    ),
                    color=alt.Color(
                        "overlooked_level:N",
                        scale=alt.Scale(domain=LEVEL_ORDER, range=[LEVEL_HEX[x] for x in LEVEL_ORDER]),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("country:N"),
                        alt.Tooltip("worst_sector:N", title="Lowest sector"),
                        alt.Tooltip("worst_sector_funding_pct:Q", title="Coverage", format=".1%"),
                        alt.Tooltip("worst_sector_gap_usd:Q", title="Sector gap", format="$,.0f"),
                    ],
                )
                .properties(height=max(250, min(430, 30 * len(sector_df))))
            )
            st.altair_chart(sector_chart, width="stretch")
    with c6:
        st.markdown("**PIN Share of COD Population**")
        if pop_chart_df.empty:
            st.info("No COD admin0 population baseline is available for these rows.")
        else:
            pop_chart = (
                alt.Chart(pop_chart_df.sort_values("pin_population_share", ascending=False))
                .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
                .encode(
                    y=alt.Y("country:N", sort="-x", title=None),
                    x=alt.X(
                        "pin_population_share:Q",
                        title="People in need / COD admin0 population",
                        axis=alt.Axis(format="%"),
                    ),
                    color=alt.Color(
                        "pin_population_share:Q",
                        scale=alt.Scale(scheme="redyellowgreen", reverse=True),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("country:N"),
                        alt.Tooltip("people_in_need:Q", title="People in need", format=",.0f"),
                        alt.Tooltip("population_baseline:Q", title="COD population", format=",.0f"),
                        alt.Tooltip("pin_population_share:Q", title="PIN share", format=".1%"),
                    ],
                )
                .properties(height=max(250, min(430, 30 * len(pop_chart_df))))
            )
            st.altair_chart(pop_chart, width="stretch")

    st.markdown("**Single-country Flow Concentration**")
    if flow_chart_df.empty:
        st.info("No single-country outgoing FTS flow detail is available for these rows.")
    else:
        flow_chart = (
            alt.Chart(flow_chart_df.sort_values("top_recipient_share", ascending=False))
            .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
            .encode(
                y=alt.Y("country:N", sort="-x", title=None),
                x=alt.X(
                    "top_recipient_share:Q",
                    title="Largest recipient share of paid/commitment outgoing detail",
                    axis=alt.Axis(format="%"),
                    scale=alt.Scale(domain=[0, 1]),
                ),
                color=alt.Color(
                    "overlooked_level:N",
                    scale=alt.Scale(domain=LEVEL_ORDER, range=[LEVEL_HEX[x] for x in LEVEL_ORDER]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("country:N"),
                    alt.Tooltip("top_recipient:N", title="Largest recipient"),
                    alt.Tooltip("top_recipient_share:Q", title="Recipient share", format=".1%"),
                    alt.Tooltip("outgoing_total_usd:Q", title="Outgoing detail total", format="$,.0f"),
                    alt.Tooltip("outgoing_recipient_count:Q", title="Recipients", format=",.0f"),
                ],
            )
            .properties(height=max(260, min(460, 30 * len(flow_chart_df))))
        )
        st.altair_chart(flow_chart, width="stretch")

    st.markdown(
        """
        <section class="board-panel">
          <div class="board-kicker">Temporal neglect check</div>
          <div class="board-title">Funding coverage trend for a selected crisis</div>
          <div class="board-copy">
            This chart compares 2024, 2025, and 2026 FTS funding coverage for one country.
            It helps distinguish a chronic underfunding pattern from a one-year coverage shock.
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    country_options = chart_df[["country_iso3", "country"]].drop_duplicates().copy()
    selected_iso = st.selectbox(
        "Trend country",
        country_options["country_iso3"].tolist(),
        format_func=lambda iso: country_options.set_index("country_iso3").loc[iso, "country"],
    )
    trend_df = build_country_trend(selected_iso)
    if trend_df["funding_pct"].notna().sum() == 0:
        st.info("No three-year FTS coverage trend is available for this country.")
    else:
        trend_chart = (
            alt.Chart(trend_df)
            .mark_line(point=True, strokeWidth=3, color="#005a8c")
            .encode(
                x=alt.X("year:O", title="Year"),
                y=alt.Y(
                    "funding_pct:Q",
                    title="Funding coverage",
                    axis=alt.Axis(format="%"),
                    scale=alt.Scale(domain=[0, max(1.0, float(trend_df["funding_pct"].max(skipna=True) or 1.0))]),
                ),
                tooltip=[
                    alt.Tooltip("year:O"),
                    alt.Tooltip("country:N"),
                    alt.Tooltip("funding_pct:Q", title="Funding coverage", format=".1%"),
                    alt.Tooltip("people_in_need:Q", title="People in need", format=",.0f"),
                    alt.Tooltip("overlooked_score:Q", title="Score", format=".1f"),
                    alt.Tooltip("has_active_hrp:N", title="Active HRP"),
                ],
            )
        )
        chronic_rule = (
            alt.Chart(pd.DataFrame({"funding_pct": [0.4]}))
            .mark_rule(color="#c63a3a", strokeDash=[6, 5], size=2)
            .encode(y="funding_pct:Q")
        )
        st.altair_chart((trend_chart + chronic_rule).properties(height=320), width="stretch")
        st.dataframe(
            trend_df[
                [
                    "year",
                    "country",
                    "funding_pct",
                    "people_in_need",
                    "overlooked_score",
                    "has_active_hrp",
                ]
            ].style.format(
                {
                    "funding_pct": "{:.1%}",
                    "people_in_need": "{:,.0f}",
                    "overlooked_score": "{:.1f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )


def flag_count(df: pd.DataFrame, flag: str) -> int:
    return int(df["data_quality_flags"].fillna("").str.contains(flag, regex=False).sum())


def explode_flags(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[str] = []
    for value in df["data_quality_flags"].fillna("ok"):
        for flag in str(value).split(";"):
            clean = flag.strip()
            if clean:
                rows.append(clean)
    if not rows:
        return pd.DataFrame({"flag": ["ok"], "rows": [0]})
    return pd.Series(rows).value_counts().rename_axis("flag").reset_index(name="rows")


def render_evidence_trace(results: pd.DataFrame, evidence_cols: list[str]) -> None:
    view = results.head(10)[evidence_cols].copy()
    money_cols = [
        "requirements_usd",
        "funding_usd",
        "cbpf_budget_usd",
        "incoming_total_usd",
        "top_donor_usd",
        "outgoing_total_usd",
        "top_recipient_usd",
    ]
    number_cols = [
        "people_in_need",
        "cbpf_projects",
        "population_baseline",
        "incoming_flow_records",
        "outgoing_flow_records",
        "active_hrp_count",
        "severity_rank",
    ]
    percent_cols = [
        "funding_pct",
        "pin_population_share",
        "worst_sector_funding_pct",
        "top_donor_share",
        "top_recipient_share",
        "severity_scale",
    ]

    for col in money_cols:
        if col in view.columns:
            view[col] = view[col].map(fmt_money)
    for col in number_cols:
        if col in view.columns:
            view[col] = view[col].map(fmt_num)
    for col in percent_cols:
        if col in view.columns:
            view[col] = view[col].map(fmt_pct)
    view = view.fillna("n/a").replace({"None": "n/a", "nan": "n/a"})
    st.dataframe(view, width="stretch", hide_index=True)


def render_method_panel(results: pd.DataFrame, raw_results: pd.DataFrame, year: int, query: str, min_people: int) -> None:
    scope = "All available crises" if not query.strip() else query.strip()
    hno_years = ", ".join(str(int(value)) for value in sorted(results["hno_year"].dropna().unique()))
    hno_files = ", ".join(str(value) for value in sorted(results["source_file"].dropna().unique()))
    coverage = results["funding_pct"].dropna()
    coverage_range = "n/a"
    if not coverage.empty:
        coverage_range = f"{fmt_pct(coverage.min())} to {fmt_pct(coverage.max())}"
    cbpf_total = results["cbpf_budget_usd"].fillna(0).sum()
    population_matched = int(results["population_baseline"].notna().sum()) if "population_baseline" in results else 0
    sector_matched = int(results["worst_sector"].notna().sum()) if "worst_sector" in results else 0
    incoming_matched = (
        int(results["incoming_total_usd"].fillna(0).gt(0).sum()) if "incoming_total_usd" in results else 0
    )
    outgoing_matched = (
        int(results["outgoing_total_usd"].fillna(0).gt(0).sum()) if "outgoing_total_usd" in results else 0
    )
    active_hrp_matched = int(results["has_active_hrp"].fillna(False).sum()) if "has_active_hrp" in results else 0
    severity_matched = int(results["severity_scale"].notna().sum()) if "severity_scale" in results else 0
    cbpf_alias_mapped = (
        int(results["cbpf_mapping_confidence"].eq("medium_alias_table").sum())
        if "cbpf_mapping_confidence" in results
        else 0
    )
    source_cards = [
        method_card("Active scope", scope, f"{len(results)} rows after dashboard filters; {len(raw_results)} before dashboard filters."),
        method_card("Need source", f"HNO {hno_years}", hno_files or "No HNO source file available in result rows."),
        method_card("Need threshold", fmt_num(min_people), "Rows below the minimum people-in-need threshold are excluded before scoring display."),
        method_card("Funding coverage range", coverage_range, "Computed from FTS funding divided by stated requirements for the selected year."),
        method_card("Active HRP match", f"{active_hrp_matched}/{len(results)} rows", "Active status is inferred from HRP metadata dates and selected plan year."),
        method_card("Mapped CBPF total", fmt_money(cbpf_total), f"{int((results['cbpf_budget_usd'].fillna(0) > 0).sum())} rows have mapped CBPF allocations."),
        method_card("CBPF mapping confidence", f"{cbpf_alias_mapped}/{len(results)} alias-mapped", "CBPF country mapping uses pooled fund name aliases and is flagged as prototype-level."),
        method_card("Quality flags", str(int((results["data_quality_flags"] != "ok").sum())), "Rows with non-ok flags remain visible so uncertainty is not hidden."),
        method_card("COD population match", f"{population_matched}/{len(results)} rows", "Admin0 total rows from cod_population_admin0.csv; used only for PIN-share context."),
        method_card("Severity context match", f"{severity_matched}/{len(results)} rows", "Local context uses HNO PIN divided by COD population; no INFORM/IPC/IDP file is cached."),
        method_card("Sector funding match", f"{sector_matched}/{len(results)} rows", "FTS global-cluster funding rows identify the lowest-funded matched sector."),
        method_card("Flow-detail match", f"{incoming_matched}/{len(results)} incoming; {outgoing_matched}/{len(results)} outgoing", "Only single-country paid/commitment flow records are used for concentration context."),
    ]
    st.markdown("**Filtered Result Set Audit**")
    st.markdown(f'<div class="method-grid">{"".join(source_cards)}</div>', unsafe_allow_html=True)

    st.markdown("**Analytical Guardrails Applied To The Filtered Result Set**")
    guardrails = [
        "Need and financing are separate signals; funding coverage does not redefine need.",
        "Sector-level PIN values are not summed across sectors because populations can overlap.",
        "CBPF is shown as a pooled-fund allocation lens, not as total humanitarian funding.",
        "HRP active status is derived from HRP metadata dates and selected plan year.",
        "Need-intensity severity context uses HNO PIN / COD population; it is not an INFORM replacement.",
        "CBPF country mapping confidence is surfaced because pooled fund name aliasing is prototype-level.",
        "COD population baselines contextualize scale; they do not replace HNO people-in-need values.",
        "Shared multi-country FTS flows are excluded from flow concentration to avoid double counting.",
        "Missing or proxy data is surfaced through flags and confidence labels.",
        "The ranking is a triage aid for briefing and follow-up analysis, not an automated allocation decision.",
    ]
    st.markdown("".join(f'<span class="method-pill">{html.escape(item)}</span>' for item in guardrails), unsafe_allow_html=True)

    triggered: list[str] = []
    missing_fts = flag_count(results, "missing_fts_requirements")
    no_cbpf = flag_count(results, "no_mapped_cbpf_allocation")
    subnational = flag_count(results, "subnational_hno_proxy")
    sector_fallback = flag_count(results, "sector_fallback")
    missing_population = int(results["population_baseline"].isna().sum()) if "population_baseline" in results else 0
    missing_sector = int(results["worst_sector"].isna().sum()) if "worst_sector" in results else 0
    missing_flow = int(results["incoming_total_usd"].fillna(0).le(0).sum()) if "incoming_total_usd" in results else 0
    missing_hrp = int((~results["has_active_hrp"].fillna(False)).sum()) if "has_active_hrp" in results else 0
    missing_severity = int(results["severity_scale"].isna().sum()) if "severity_scale" in results else 0
    if missing_fts:
        triggered.append(f"{missing_fts} rows have no matched FTS requirements and are lower-confidence funding comparisons.")
    if no_cbpf:
        triggered.append(f"{no_cbpf} rows have no mapped CBPF allocation in the selected year.")
    if subnational:
        triggered.append(f"{subnational} rows use a subnational HNO proxy because no national HNO row was available.")
    if sector_fallback:
        triggered.append(f"{sector_fallback} rows did not match the requested sector and use a fallback need selection.")
    if missing_population:
        triggered.append(f"{missing_population} rows have no COD admin0 population baseline in the downloaded population file.")
    if missing_sector:
        triggered.append(f"{missing_sector} rows have no matched FTS global-cluster funding breakdown.")
    if missing_flow:
        triggered.append(f"{missing_flow} rows have no single-country incoming paid/commitment flow detail in the downloaded FTS flow file.")
    if missing_hrp:
        triggered.append(f"{missing_hrp} rows have documented need but no matched active HRP in the selected year.")
    if missing_severity:
        triggered.append(f"{missing_severity} rows have no local severity context because no COD baseline or external severity file matched.")
    if not triggered:
        triggered.append("No non-ok data quality flags are present in the current filtered result set.")

    st.markdown("**Data Cautions Triggered By The Filtered Result Set**")
    for item in triggered:
        st.markdown(f"- {item}")

    st.markdown("**Scoring Formula Used For These Rows**")
    st.code(
        """overlooked_score =
  0.30 * percentile(log(people_in_need * funding_gap))
+ 0.25 * funding_gap
+ 0.20 * percentile(log(people_in_need))
+ 0.15 * inverse_percentile(CBPF allocation per person in need)
+ 0.10 * share of latest three years below 40% funding""",
        language="text",
    )

    evidence_cols = [
        "rank",
        "country",
        "hno_year",
        "sector_label",
        "need_selection",
        "people_in_need",
        "requirements_usd",
        "funding_usd",
        "funding_pct",
        "has_active_hrp",
        "active_hrp_names",
        "hrp_status",
        "cbpf_budget_usd",
        "cbpf_projects",
        "cbpf_mapping_confidence",
        "population_baseline",
        "pin_population_share",
        "severity_scale",
        "severity_context",
        "worst_sector",
        "worst_sector_funding_pct",
        "incoming_total_usd",
        "top_donor",
        "top_donor_share",
        "outgoing_total_usd",
        "top_recipient",
        "top_recipient_share",
        "underfunded_years_last_3",
        "confidence",
        "data_quality_flags",
        "supplemental_data_flags",
    ]
    st.markdown("**Top-row Evidence Trace**")
    render_evidence_trace(results, evidence_cols)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        st.markdown("**Data Quality Flag Counts**")
        st.dataframe(explode_flags(results), width="stretch", hide_index=True)
    with c2:
        st.markdown("**Confidence Distribution**")
        confidence_df = results["confidence"].value_counts().rename_axis("confidence").reset_index(name="rows")
        st.dataframe(confidence_df, width="stretch", hide_index=True)
    with c3:
        st.markdown("**Need Selection Methods**")
        selection_df = results["need_selection"].value_counts().rename_axis("need_selection").reset_index(name="rows")
        st.dataframe(selection_df, width="stretch", hide_index=True)


st.set_page_config(page_title="Geo-Insight Crisis Ranker", layout="wide")
inject_css()

with st.sidebar:
    st.markdown("### Scope")
    year = st.selectbox("Year", [2026, 2025, 2024], index=0)
    min_people = st.number_input(
        "Minimum people in need",
        min_value=0,
        value=100_000,
        step=100_000,
    )
    top_n = st.slider("Top results", min_value=1, max_value=25, value=10)
    auto_download = st.checkbox("Download missing data", value=False)

st.markdown(
    """
    <section class="query-panel">
      <div class="query-panel-title">Query or geographic scope</div>
      <div class="query-panel-copy">
        Enter a region, country, sector, or funding threshold. Leave blank for the full global ranking.
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)
query = st.text_input(
    "Query or geographic scope",
    value="",
    placeholder="Example: East Africa with less than 40% funding coverage",
    label_visibility="collapsed",
    key="query_input_panel",
)
render_query_audit(query, int(year), int(min_people))

try:
    raw_results = build_rankings(
        query,
        year=int(year),
        min_people_in_need=int(min_people),
        auto_download=auto_download,
        download_years=[int(year)],
    )
except MissingRawDataError as exc:
    st.warning(str(exc))
    st.stop()
except Exception as exc:  # pragma: no cover - visible in demo app
    st.error(f"Unable to build ranking: {exc}")
    st.stop()

if raw_results.empty:
    render_hero(int(year), query, 0)
    st.info("No crises matched the selected filters.")
    st.stop()

raw_results = prepare_display_data(raw_results)

with st.sidebar:
    st.markdown("### Dashboard Filters")
    available_regions = sorted([region for region in raw_results["region"].dropna().unique() if region])
    selected_regions = st.multiselect("Regions", available_regions, default=available_regions)
    available_levels = [level for level in LEVEL_ORDER if level in set(raw_results["overlooked_level"])]
    selected_levels = st.multiselect("Overlooked levels", available_levels, default=available_levels)
    confidence_filter = st.multiselect(
        "Confidence",
        sorted(raw_results["confidence"].dropna().unique()),
        default=sorted(raw_results["confidence"].dropna().unique()),
    )

results = raw_results.copy()
if selected_regions:
    results = results[results["region"].isin(selected_regions)]
if selected_levels:
    results = results[results["overlooked_level"].isin(selected_levels)]
if confidence_filter:
    results = results[results["confidence"].isin(confidence_filter)]

if results.empty:
    render_hero(int(year), query, len(raw_results))
    st.info("No crises matched the dashboard filters.")
    st.stop()

results = results.sort_values(["overlooked_score", "people_in_need"], ascending=[False, False]).copy()
results["rank"] = range(1, len(results) + 1)
top = results.head(top_n).copy()

render_hero(int(year), query, len(raw_results))
render_metrics(results)
render_briefing(results)

tabs = st.tabs(["Command View", "Interactive Map", "Comparison Board", "Method & Data"])

with tabs[0]:
    st.markdown("**Ranked Crises**")
    st.caption(f"Showing {len(top)} of {len(results)} crises after dashboard filters.")
    render_ranking_table(top)
    st.markdown("**Why the top results rank high**")
    for _, row in top.head(min(5, top_n)).iterrows():
        st.markdown(f"**#{int(row['rank'])} {row['country']}**")
        st.write(row["explanation"])

with tabs[1]:
    st.markdown("**Map-ready Gap Signals**")
    render_map(top)
    st.caption(
        "Circle size follows people in need; color follows overlooked level. "
        "Hover for sourced values and data-quality flags."
    )

with tabs[2]:
    st.markdown("**Data Comparison Board**")
    render_charts(results, top_n)

with tabs[3]:
    render_method_panel(results, raw_results, int(year), query, int(min_people))
    with st.expander("Full CSV-ready output for current filters", expanded=False):
        st.dataframe(results, width="stretch", hide_index=True)
    with st.expander("Unfiltered query output", expanded=False):
        st.dataframe(raw_results, width="stretch", hide_index=True)

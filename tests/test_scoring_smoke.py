import unittest

from src.scoring import build_rankings


class ScoringSmokeTests(unittest.TestCase):
    def test_pipeline_returns_rankings_for_2025(self) -> None:
        df = build_rankings("", year=2025, min_people_in_need=100_000)
        self.assertFalse(df.empty)
        expected = {
            "country",
            "iso3",
            "people_in_need",
            "funding_pct",
            "funding_gap",
            "overlooked_score",
        }
        self.assertTrue(expected.issubset(df.columns))

    def test_hrp_and_supplemental_fields_are_present(self) -> None:
        df = build_rankings("", year=2026, min_people_in_need=100_000)
        expected = {
            "has_active_hrp",
            "hrp_status",
            "hrp_plan_name",
            "hrp_plan_type",
            "hrp_year",
            "hrp_match_confidence",
            "hrp_data_quality",
            "severity_available",
            "severity_context",
            "severity_source",
            "cbpf_allocation_usd",
            "cbpf_mapping_confidence",
            "cbpf_country_source",
            "cbpf_gap_scale",
        }
        self.assertTrue(expected.issubset(df.columns))

    def test_active_hrp_query_runs(self) -> None:
        df = build_rankings("active HRPs with less than 40% funding coverage", year=2026)
        self.assertIn("has_active_hrp", df.columns)
        if not df.empty:
            self.assertTrue(df["has_active_hrp"].all())
            self.assertTrue((df["funding_pct"].fillna(0) <= 0.40).all())

    def test_food_insecurity_sector_proxy_query_runs(self) -> None:
        df = build_rankings(
            "Show acute food insecurity hotspots with less than 10% requested funding.",
            year=2026,
        )
        self.assertIn("sector_label", df.columns)
        self.assertIn("funding_pct", df.columns)
        if not df.empty:
            self.assertTrue((df["funding_pct"].fillna(0) <= 0.10).all())


if __name__ == "__main__":
    unittest.main()

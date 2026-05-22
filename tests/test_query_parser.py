import unittest

from src.query import parse_query


class QueryParserTests(unittest.TestCase):
    def test_active_hrp_no_funding_query(self) -> None:
        spec = parse_query("Which countries have active HRPs but no funding?")
        self.assertEqual(spec.hrp_filter, "active")
        self.assertEqual(spec.funding_pct_max, 0.10)
        self.assertIsNone(spec.sector)

    def test_active_hrp_less_than_40_percent_query(self) -> None:
        spec = parse_query("active HRPs with less than 40% funding coverage")
        self.assertEqual(spec.hrp_filter, "active")
        self.assertEqual(spec.funding_pct_max, 0.40)

    def test_food_insecurity_query_maps_to_food_sector(self) -> None:
        spec = parse_query("Show acute food insecurity hotspots with less than 10% requested funding.")
        self.assertTrue(spec.food_insecurity_requested)
        self.assertEqual(spec.sector, "food")
        self.assertEqual(spec.funding_pct_max, 0.10)

    def test_no_hrp_query(self) -> None:
        spec = parse_query("Countries with no HRP")
        self.assertEqual(spec.hrp_filter, "missing")

    def test_structural_neglect_intent(self) -> None:
        spec = parse_query("Which regions are consistently underfunded across multiple years?")
        self.assertTrue(spec.structural_neglect_requested)
        self.assertTrue(spec.chronic_underfunding_requested)


if __name__ == "__main__":
    unittest.main()

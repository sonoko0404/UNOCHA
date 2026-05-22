"""Project configuration and small reference tables.

The production version should replace these small reference tables with a
canonical country and region source. For the prototype, keeping the mapping
local makes the pipeline reproducible and avoids adding a heavy dependency.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"

HDX_CKAN_API = "https://data.humdata.org/api/3/action/package_show"

DATASET_SLUGS = {
    "hno": "global-hpc-hno",
    "hrp": "humanitarian-response-plans",
    "funding": "global-requirements-and-funding-data",
    "population": "cod-ps-global",
    "inform": "inform-global-crisis-severity-index",
}

CBPF_PROJECT_SUMMARY_CSV = (
    "https://cbpfapi.unocha.org/vo1/odata/ProjectSummary"
    "?%24format=csv&ShowAllPooledFunds=1"
)

DEFAULT_YEAR = 2026
DEFAULT_MIN_PEOPLE_IN_NEED = 100_000
DEFAULT_CHRONIC_FUNDING_THRESHOLD = 0.40

COUNTRY_REFERENCE = {
    "AFG": {"country": "Afghanistan", "lat": 33.9391, "lon": 67.7100, "region": "Asia-Pacific"},
    "BFA": {"country": "Burkina Faso", "lat": 12.2383, "lon": -1.5616, "region": "West and Central Africa"},
    "CMR": {"country": "Cameroon", "lat": 7.3697, "lon": 12.3547, "region": "West and Central Africa"},
    "CAF": {"country": "Central African Republic", "lat": 6.6111, "lon": 20.9394, "region": "West and Central Africa"},
    "TCD": {"country": "Chad", "lat": 15.4542, "lon": 18.7322, "region": "West and Central Africa"},
    "COL": {"country": "Colombia", "lat": 4.5709, "lon": -74.2973, "region": "Latin America and Caribbean"},
    "COD": {"country": "Democratic Republic of the Congo", "lat": -4.0383, "lon": 21.7587, "region": "West and Central Africa"},
    "SLV": {"country": "El Salvador", "lat": 13.7942, "lon": -88.8965, "region": "Latin America and Caribbean"},
    "ETH": {"country": "Ethiopia", "lat": 9.1450, "lon": 40.4897, "region": "East Africa"},
    "GTM": {"country": "Guatemala", "lat": 15.7835, "lon": -90.2308, "region": "Latin America and Caribbean"},
    "HTI": {"country": "Haiti", "lat": 18.9712, "lon": -72.2852, "region": "Latin America and Caribbean"},
    "HND": {"country": "Honduras", "lat": 15.2000, "lon": -86.2419, "region": "Latin America and Caribbean"},
    "MLI": {"country": "Mali", "lat": 17.5707, "lon": -3.9962, "region": "West and Central Africa"},
    "MOZ": {"country": "Mozambique", "lat": -18.6657, "lon": 35.5296, "region": "Southern Africa"},
    "MMR": {"country": "Myanmar", "lat": 21.9162, "lon": 95.9560, "region": "Asia-Pacific"},
    "NER": {"country": "Niger", "lat": 17.6078, "lon": 8.0817, "region": "West and Central Africa"},
    "NGA": {"country": "Nigeria", "lat": 9.0820, "lon": 8.6753, "region": "West and Central Africa"},
    "SOM": {"country": "Somalia", "lat": 5.1521, "lon": 46.1996, "region": "East Africa"},
    "SSD": {"country": "South Sudan", "lat": 6.8770, "lon": 31.3070, "region": "East Africa"},
    "SDN": {"country": "Sudan", "lat": 12.8628, "lon": 30.2176, "region": "East Africa"},
    "SYR": {"country": "Syrian Arab Republic", "lat": 34.8021, "lon": 38.9968, "region": "Middle East"},
    "UKR": {"country": "Ukraine", "lat": 48.3794, "lon": 31.1656, "region": "Europe"},
    "VEN": {"country": "Venezuela (Bolivarian Republic of)", "lat": 6.4238, "lon": -66.5897, "region": "Latin America and Caribbean"},
    "YEM": {"country": "Yemen", "lat": 15.5527, "lon": 48.5164, "region": "Middle East"},
    "PSE": {"country": "State of Palestine", "lat": 31.9522, "lon": 35.2332, "region": "Middle East"},
    "IRQ": {"country": "Iraq", "lat": 33.2232, "lon": 43.6793, "region": "Middle East"},
    "JOR": {"country": "Jordan", "lat": 30.5852, "lon": 36.2384, "region": "Middle East"},
    "LBN": {"country": "Lebanon", "lat": 33.8547, "lon": 35.8623, "region": "Middle East"},
    "TUR": {"country": "Turkiye", "lat": 38.9637, "lon": 35.2433, "region": "Europe"},
    "PAK": {"country": "Pakistan", "lat": 30.3753, "lon": 69.3451, "region": "Asia-Pacific"},
    "KEN": {"country": "Kenya", "lat": -0.0236, "lon": 37.9062, "region": "East Africa"},
    "UGA": {"country": "Uganda", "lat": 1.3733, "lon": 32.2903, "region": "East Africa"},
    "BDI": {"country": "Burundi", "lat": -3.3731, "lon": 29.9189, "region": "East Africa"},
    "ZWE": {"country": "Zimbabwe", "lat": -19.0154, "lon": 29.1549, "region": "Southern Africa"},
    "ZMB": {"country": "Zambia", "lat": -13.1339, "lon": 27.8493, "region": "Southern Africa"},
    "BGD": {"country": "Bangladesh", "lat": 23.6850, "lon": 90.3563, "region": "Asia-Pacific"},
}

COUNTRY_ALIASES = {
    "AFGHANISTAN": "AFG",
    "BURKINA FASO": "BFA",
    "CAMEROON": "CMR",
    "CENTRAL AFRICAN REPUBLIC": "CAF",
    "CAR": "CAF",
    "CHAD": "TCD",
    "COLOMBIA": "COL",
    "DEMOCRATIC REPUBLIC OF THE CONGO": "COD",
    "DEMOCRATIC REPUBLIC OF CONGO": "COD",
    "DRC": "COD",
    "CONGO DR": "COD",
    "EL SALVADOR": "SLV",
    "ETHIOPIA": "ETH",
    "GUATEMALA": "GTM",
    "HAITI": "HTI",
    "HONDURAS": "HND",
    "MALI": "MLI",
    "MOZAMBIQUE": "MOZ",
    "MYANMAR": "MMR",
    "NIGER": "NER",
    "NIGERIA": "NGA",
    "SOMALIA": "SOM",
    "SOUTH SUDAN": "SSD",
    "SUDAN": "SDN",
    "SYRIA": "SYR",
    "SYRIAN ARAB REPUBLIC": "SYR",
    "UKRAINE": "UKR",
    "VENEZUELA": "VEN",
    "VENEZUELA BOLIVARIAN REPUBLIC OF": "VEN",
    "YEMEN": "YEM",
    "OCCUPIED PALESTINIAN TERRITORY": "PSE",
    "OPT": "PSE",
    "STATE OF PALESTINE": "PSE",
    "PALESTINE": "PSE",
    "IRAQ": "IRQ",
    "JORDAN": "JOR",
    "LEBANON": "LBN",
    "TURKIYE": "TUR",
    "TURKEY": "TUR",
    "PAKISTAN": "PAK",
    "KENYA": "KEN",
    "UGANDA": "UGA",
    "BURUNDI": "BDI",
    "ZIMBABWE": "ZWE",
    "ZAMBIA": "ZMB",
    "BANGLADESH": "BGD",
}

REGION_SCOPES = {
    "east africa": {"ETH", "KEN", "SOM", "SSD", "SDN", "UGA", "BDI"},
    "horn of africa": {"ETH", "SOM", "SSD", "SDN", "KEN", "UGA"},
    "sahel": {"BFA", "MLI", "NER", "TCD", "NGA", "CMR"},
    "west africa": {"BFA", "MLI", "NER", "NGA"},
    "central africa": {"CAF", "CMR", "COD", "TCD"},
    "west and central africa": {"BFA", "CAF", "CMR", "COD", "MLI", "NER", "NGA", "TCD"},
    "middle east": {"IRQ", "JOR", "LBN", "PSE", "SYR", "TUR", "YEM"},
    "latin america": {"COL", "GTM", "HTI", "HND", "SLV", "VEN"},
    "latin america and caribbean": {"COL", "GTM", "HTI", "HND", "SLV", "VEN"},
    "asia": {"AFG", "BGD", "MMR", "PAK"},
    "asia-pacific": {"AFG", "BGD", "MMR", "PAK"},
    "europe": {"UKR", "TUR"},
    "southern africa": {"MOZ", "ZMB", "ZWE"},
    "africa": {
        "BFA",
        "BDI",
        "CAF",
        "CMR",
        "COD",
        "ETH",
        "KEN",
        "MLI",
        "MOZ",
        "NER",
        "NGA",
        "SDN",
        "SOM",
        "SSD",
        "TCD",
        "UGA",
        "ZMB",
        "ZWE",
    },
}

SECTOR_ALIASES = {
    "food": "food",
    "food security": "food",
    "fsl": "food",
    "acute food insecurity": "food",
    "nutrition": "nutrition",
    "health": "health",
    "wash": "wash",
    "water": "wash",
    "sanitation": "wash",
    "shelter": "shelter",
    "nfi": "shelter",
    "protection": "protection",
    "education": "education",
    "logistics": "logistics",
    "cash": "cash",
}

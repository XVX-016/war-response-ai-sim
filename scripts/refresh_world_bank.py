"""
Refresh world_bank_cache.json from live World Bank API.
Run: python scripts/refresh_world_bank.py
Requires: requests (pip install requests)

World Bank API is free, no key required.
Endpoint: https://api.worldbank.org/v2/country/{iso}/indicator/{code}?format=json
"""

import json
import time
from datetime import date
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    raise

INDICATORS = {
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "military_pct_gdp": "MS.MIL.XPND.GD.ZS",
    "population": "SP.POP.TOTL",
    "resource_rents": "NY.GDP.TOTL.RT.ZS",
    "forest_area": "AG.LND.FRST.ZS",
    "trade_pct_gdp": "NE.TRD.GNFS.ZS",
}

ISO3_MAP = {
    "United States": "USA",
    "Germany": "DEU",
    "France": "FRA",
    "United Kingdom": "GBR",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Australia": "AUS",
    "Russia": "RUS",
    "China": "CHN",
    "North Korea": "PRK",
    "Saudi Arabia": "SAU",
    "Iran": "IRN",
    "Norway": "NOR",
    "UAE": "ARE",
    "India": "IND",
    "Brazil": "BRA",
    "Nigeria": "NGA",
    "Indonesia": "IDN",
    "Pakistan": "PAK",
    "Ukraine": "UKR",
    "Syria": "SYR",
    "Afghanistan": "AFG",
    "Yemen": "YEM",
    "Cuba": "CUB",
    "Venezuela": "VEN",
    "Israel": "ISR",
    "Singapore": "SGP",
    "Switzerland": "CHE",
    "Ethiopia": "ETH",
    "South Africa": "ZAF",
}


def fetch_indicator(iso3, indicator_code):
    """Fetch latest non-null value for one indicator from World Bank API."""
    url = (
        f"https://api.worldbank.org/v2/country/{iso3}"
        f"/indicator/{indicator_code}?format=json&mrv=5"
    )
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if len(data) < 2 or not data[1]:
            return None
        for entry in data[1]:
            if entry.get("value") is not None:
                return float(entry["value"])
    except Exception as exc:
        print(f"  Warning: {iso3} {indicator_code}: {exc}")
    return None


def normalise(value, min_val, max_val):
    """Normalise value to [0, 1] with clamping."""
    if value is None:
        return None
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def refresh():
    cache_path = Path("data/countries/world_bank_cache.json")
    with open(cache_path, "r", encoding="utf-8") as handle:
        cache = json.load(handle)

    ranges = {
        "gdp_per_capita": (500, 85000),
        "military_pct_gdp": (0, 8),
        "population": (1e6, 1.5e9),
        "resource_rents": (0, 50),
        "forest_area": (0, 90),
        "trade_pct_gdp": (20, 400),
    }

    print(f"Refreshing {len(ISO3_MAP)} countries from World Bank API...")
    updated = {}

    for country_name, iso3 in ISO3_MAP.items():
        print(f"  Fetching {country_name} ({iso3})...")
        raw = {}
        for key, code in INDICATORS.items():
            raw[key] = fetch_indicator(iso3, code)
            time.sleep(0.2)

        gdp_norm = normalise(raw["gdp_per_capita"], *ranges["gdp_per_capita"])
        mil_norm = normalise(raw["military_pct_gdp"], *ranges["military_pct_gdp"])
        pop_raw = raw["population"] / 1e6 if raw["population"] else None
        res_norm = normalise(raw["resource_rents"], *ranges["resource_rents"])
        ter_norm = normalise(raw["forest_area"], *ranges["forest_area"])
        ali_norm = normalise(raw["trade_pct_gdp"], *ranges["trade_pct_gdp"])

        existing = cache["countries"].get(country_name, {})
        entry = {
            "gdp_index": gdp_norm or existing.get("gdp_index", 0.5),
            "military_strength": mil_norm or existing.get("military_strength", 0.5),
            "population_millions": pop_raw or existing.get("population_millions", 10),
            "resource_richness": res_norm or existing.get("resource_richness", 0.5),
            "terrain_difficulty": ter_norm or existing.get("terrain_difficulty", 0.5),
            "alliance_strength": ali_norm or existing.get("alliance_strength", 0.5),
            "region": existing.get("region", "Unknown"),
            "flag": existing.get("flag", "🏳"),
        }
        for key, value in entry.items():
            if isinstance(value, float):
                entry[key] = round(value, 2)
        updated[country_name] = entry

    cache["countries"] = updated
    cache["last_updated"] = str(date.today())
    with open(cache_path, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)
    print(f"Done. Cache updated: {cache_path}")


if __name__ == "__main__":
    refresh()

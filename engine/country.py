from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

import config
from schemas import ScenarioState


class CountryProfile(BaseModel):
    nation: str
    display_name: str
    flag_emoji: str = "??"
    lore: str = ""

    gdp_index: float = 0.5
    military_strength: float = 0.5
    population_millions: float = 5.0
    resource_richness: float = 0.5
    terrain_difficulty: float = 0.5
    alliance_strength: float = 0.5

    def gdp_label(self) -> str:
        if self.gdp_index < 0.25:
            return "Low"
        if self.gdp_index < 0.50:
            return "Medium"
        if self.gdp_index < 0.75:
            return "High"
        return "Very High"

    def military_label(self) -> str:
        if self.military_strength < 0.25:
            return "Limited"
        if self.military_strength < 0.50:
            return "Moderate"
        if self.military_strength < 0.75:
            return "Strong"
        return "Elite"

    def terrain_label(self) -> str:
        if self.terrain_difficulty < 0.25:
            return "Flat / Urban"
        if self.terrain_difficulty < 0.50:
            return "Mixed"
        if self.terrain_difficulty < 0.75:
            return "Mountainous"
        return "Extreme"

    def alliance_label(self) -> str:
        if self.alliance_strength < 0.25:
            return "Isolated"
        if self.alliance_strength < 0.50:
            return "Neutral"
        if self.alliance_strength < 0.75:
            return "Allied"
        return "Major Alliance"

    @field_validator(
        "gdp_index",
        "military_strength",
        "resource_richness",
        "terrain_difficulty",
        "alliance_strength",
    )
    @classmethod
    def must_be_normalised(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Factor must be in [0.0, 1.0], got {value}")
        return round(value, 3)

    @field_validator("population_millions")
    @classmethod
    def must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("population_millions must be > 0")
        return round(value, 2)


def load_country_profile(nation: str, countries_dir: "Path | None" = None) -> CountryProfile:
    """
    Load a CountryProfile from data/countries/{nation_lower}.json.
    Returns a default profile (all factors = 0.5) if no file is found.
    Never raises on missing file ? logs a warning instead.
    """
    import json
    from pathlib import Path as P

    from loguru import logger

    countries_dir = P(countries_dir) if countries_dir is not None else (config.DATA_DIR / "countries")
    path = countries_dir / f"{nation.lower()}.json"
    if not path.exists():
        logger.warning(f"No country profile found for '{nation}' at {path} - using defaults")
        return CountryProfile(nation=nation, display_name=nation)
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return CountryProfile(**data)


def apply_profile_to_state(
    state: ScenarioState,
    profiles: dict[str, CountryProfile],
) -> ScenarioState:
    """
    Apply country profile multipliers to a freshly loaded ScenarioState.
    Call this once after load_scenario(), before any simulation turns.
    Returns the mutated state (mutates in place for efficiency at load time).
    """
    base_meta = state.metadata.setdefault("_profile_base", {})

    if "resources" not in base_meta:
        base_meta["resources"] = {
            nation: dict(stock.stocks)
            for nation, stock in state.resources.items()
        }
    if "zone_populations" not in base_meta:
        base_meta["zone_populations"] = {
            zone.id: int(zone.population)
            for zone in state.zones
        }
    if "transport_health" not in base_meta:
        base_meta["transport_health"] = {
            asset.id: float(asset.health)
            for asset in state.assets
            if asset.asset_type == "transport_hub"
        }

    for nation in state.nations:
        profile = profiles.get(nation) or CountryProfile(nation=nation, display_name=nation)
        nation_meta = state.metadata.setdefault(nation, {})

        base_stocks = dict(base_meta["resources"].get(nation, {}))
        if nation in state.resources:
            state.resources[nation].stocks = dict(base_stocks)
            stocks = state.resources[nation].stocks

            g = profile.gdp_index
            stocks["repair_crews"] = base_stocks.get("repair_crews", 0.0) * (0.5 + g)
            stocks["medical_supplies"] = base_stocks.get("medical_supplies", 0.0) * (0.5 + g)
            stocks["food_rations"] = base_stocks.get("food_rations", 0.0) * (0.5 + g)

            m = profile.military_strength
            stocks["repair_crews"] *= (0.7 + m * 0.6)
            nation_meta["military_strength"] = m

            r = profile.resource_richness
            richness_multiplier = 0.4 + r * 1.2
            stocks["fuel"] = base_stocks.get("fuel", 0.0) * richness_multiplier
            stocks["generators"] = base_stocks.get("generators", 0.0) * richness_multiplier
            stocks["water_purifiers"] = base_stocks.get("water_purifiers", 0.0) * richness_multiplier

        p = profile.population_millions
        for zone in state.get_zones_for(nation):
            base_population = int(base_meta["zone_populations"].get(zone.id, zone.population))
            zone.population = int(base_population * (p / 5.0))

        t = profile.terrain_difficulty
        for asset in state.get_assets_for(nation):
            if asset.asset_type != "transport_hub":
                continue
            base_health = float(base_meta["transport_health"].get(asset.id, asset.health))
            asset.health = max(base_health * (1.0 - t * 0.4), 10.0)
            asset.is_destroyed = asset.health <= 0
        nation_meta["terrain_difficulty"] = t

        nation_meta["alliance_strength"] = profile.alliance_strength

    return state

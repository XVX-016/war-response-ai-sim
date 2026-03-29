from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import config
from agents.rule_agent import select_actions
from engine.country import CountryProfile, apply_profile_to_state, load_country_profile
from engine.turn_engine import step_simulation
from engine.world import load_scenario


SCENARIO_PATH = Path("data/scenarios/cascade_crisis.json")


def _neutral_profile(nation: str) -> CountryProfile:
    return CountryProfile(nation=nation, display_name=nation)


def _profile(**overrides) -> CountryProfile:
    data = {
        "nation": overrides.pop("nation", "Auria"),
        "display_name": overrides.pop("display_name", "Auria"),
        "gdp_index": 0.5,
        "military_strength": 0.5,
        "population_millions": 5.0,
        "resource_richness": 0.5,
        "terrain_difficulty": 0.5,
        "alliance_strength": 0.5,
    }
    data.update(overrides)
    return CountryProfile(**data)


class TestCountryProfileSchema:
    def test_valid_profile_loads(self):
        profile = load_country_profile("Auria")
        assert profile.gdp_index is not None
        assert profile.military_strength is not None
        assert profile.population_millions is not None
        assert profile.resource_richness is not None
        assert profile.terrain_difficulty is not None
        assert profile.alliance_strength is not None

    def test_out_of_range_factor_raises(self):
        with pytest.raises(ValidationError):
            CountryProfile(nation="X", display_name="X", gdp_index=1.5)

    def test_negative_population_raises(self):
        with pytest.raises(ValidationError):
            CountryProfile(nation="X", display_name="X", population_millions=-1)

    def test_default_profile_is_neutral(self):
        profile = CountryProfile(nation="X", display_name="X")
        assert profile.gdp_index == 0.5
        assert profile.military_strength == 0.5
        assert profile.resource_richness == 0.5
        assert profile.terrain_difficulty == 0.5
        assert profile.alliance_strength == 0.5

    def test_gdp_labels_correct(self):
        assert CountryProfile(nation="X", display_name="X", gdp_index=0.1).gdp_label() == "Low"
        assert CountryProfile(nation="X", display_name="X", gdp_index=0.3).gdp_label() == "Medium"
        assert CountryProfile(nation="X", display_name="X", gdp_index=0.6).gdp_label() == "High"
        assert CountryProfile(nation="X", display_name="X", gdp_index=0.9).gdp_label() == "Very High"

    def test_military_labels_correct(self):
        assert CountryProfile(nation="X", display_name="X", military_strength=0.1).military_label() == "Limited"
        assert CountryProfile(nation="X", display_name="X", military_strength=0.9).military_label() == "Elite"

    def test_terrain_label_correct(self):
        assert CountryProfile(nation="X", display_name="X", terrain_difficulty=0.1).terrain_label() == "Flat / Urban"
        assert CountryProfile(nation="X", display_name="X", terrain_difficulty=0.9).terrain_label() == "Extreme"

    def test_alliance_label_correct(self):
        assert CountryProfile(nation="X", display_name="X", alliance_strength=0.1).alliance_label() == "Isolated"
        assert CountryProfile(nation="X", display_name="X", alliance_strength=0.9).alliance_label() == "Major Alliance"


class TestLoadCountryProfile:
    def test_loads_auria_json(self):
        profile = load_country_profile("Auria")
        assert profile.display_name == "Republic of Auria"

    def test_loads_boros_json(self):
        profile = load_country_profile("Boros")
        assert "resource-rich" in profile.lore.lower()

    def test_missing_file_returns_defaults(self, tmp_path):
        profile = load_country_profile("Nonexistent", countries_dir=tmp_path)
        assert profile.nation == "Nonexistent"
        assert profile.gdp_index == 0.5
        assert profile.military_strength == 0.5
        assert profile.resource_richness == 0.5
        assert profile.terrain_difficulty == 0.5
        assert profile.alliance_strength == 0.5

    def test_case_insensitive_load(self):
        upper = load_country_profile("AURIA")
        normal = load_country_profile("Auria")
        assert upper.display_name == normal.display_name


class TestApplyProfileToState:
    def test_high_gdp_increases_medical_supplies(self):
        base_state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        high_state = base_state.model_copy(deep=True)
        low_state = base_state.model_copy(deep=True)
        profiles_high = {nation: _neutral_profile(nation) for nation in high_state.nations}
        profiles_low = {nation: _neutral_profile(nation) for nation in low_state.nations}
        profiles_high["Auria"] = _profile(gdp_index=0.9)
        profiles_low["Auria"] = _profile(gdp_index=0.1)
        apply_profile_to_state(high_state, profiles_high)
        apply_profile_to_state(low_state, profiles_low)
        assert high_state.resources["Auria"].stocks["medical_supplies"] > low_state.resources["Auria"].stocks["medical_supplies"]

    def test_high_resource_richness_increases_fuel(self):
        base_state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        high_state = base_state.model_copy(deep=True)
        low_state = base_state.model_copy(deep=True)
        profiles_high = {nation: _neutral_profile(nation) for nation in high_state.nations}
        profiles_low = {nation: _neutral_profile(nation) for nation in low_state.nations}
        profiles_high["Auria"] = _profile(resource_richness=0.9)
        profiles_low["Auria"] = _profile(resource_richness=0.1)
        apply_profile_to_state(high_state, profiles_high)
        apply_profile_to_state(low_state, profiles_low)
        assert high_state.resources["Auria"].stocks["fuel"] > low_state.resources["Auria"].stocks["fuel"]

    def test_high_population_scales_zones(self):
        base_state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        high_state = base_state.model_copy(deep=True)
        low_state = base_state.model_copy(deep=True)
        profiles_high = {nation: _neutral_profile(nation) for nation in high_state.nations}
        profiles_low = {nation: _neutral_profile(nation) for nation in low_state.nations}
        profiles_high["Auria"] = _profile(population_millions=10.0)
        profiles_low["Auria"] = _profile(population_millions=2.0)
        apply_profile_to_state(high_state, profiles_high)
        apply_profile_to_state(low_state, profiles_low)
        assert high_state.get_zones_for("Auria")[0].population > low_state.get_zones_for("Auria")[0].population

    def test_high_terrain_reduces_transport_health(self):
        base_state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        high_state = base_state.model_copy(deep=True)
        low_state = base_state.model_copy(deep=True)
        profiles_high = {nation: _neutral_profile(nation) for nation in high_state.nations}
        profiles_low = {nation: _neutral_profile(nation) for nation in low_state.nations}
        profiles_high["Auria"] = _profile(terrain_difficulty=0.9)
        profiles_low["Auria"] = _profile(terrain_difficulty=0.1)
        apply_profile_to_state(high_state, profiles_high)
        apply_profile_to_state(low_state, profiles_low)
        high_transport = next(asset for asset in high_state.get_assets_for("Auria") if asset.asset_type == "transport_hub")
        low_transport = next(asset for asset in low_state.get_assets_for("Auria") if asset.asset_type == "transport_hub")
        assert high_transport.health < low_transport.health

    def test_alliance_stored_in_metadata(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        profiles = {nation: _neutral_profile(nation) for nation in state.nations}
        profiles["Auria"] = _profile(alliance_strength=0.8)
        apply_profile_to_state(state, profiles)
        assert state.metadata["Auria"]["alliance_strength"] == 0.8

    def test_military_stored_in_metadata(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        profiles = {nation: _neutral_profile(nation) for nation in state.nations}
        profiles["Auria"] = _profile(military_strength=0.8)
        apply_profile_to_state(state, profiles)
        assert state.metadata["Auria"]["military_strength"] == 0.8

    def test_idempotent(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        profiles = {nation: _neutral_profile(nation) for nation in state.nations}
        profiles["Auria"] = _profile(gdp_index=0.8, resource_richness=0.7, terrain_difficulty=0.4)
        apply_profile_to_state(state, profiles)
        once = state.model_copy(deep=True)
        apply_profile_to_state(state, profiles)
        assert state.resources["Auria"].stocks == once.resources["Auria"].stocks
        assert [zone.population for zone in state.get_zones_for("Auria")] == [zone.population for zone in once.get_zones_for("Auria")]

    def test_all_stocks_remain_positive(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        profiles = {
            nation: CountryProfile(
                nation=nation,
                display_name=nation,
                gdp_index=0.0,
                military_strength=0.0,
                population_millions=1.0,
                resource_richness=0.0,
                terrain_difficulty=0.0,
                alliance_strength=0.0,
            )
            for nation in state.nations
        }
        apply_profile_to_state(state, profiles)
        for resource_stock in state.resources.values():
            assert all(value >= 0 for value in resource_stock.stocks.values())


class TestEngineIntegration:
    def test_load_scenario_applies_profiles_by_default(self):
        profiled, _ = load_scenario(SCENARIO_PATH)
        raw, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        assert profiled.resources["Auria"].stocks["fuel"] != raw.resources["Auria"].stocks["fuel"]

    def test_load_scenario_skip_profiles_flag(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        for nation in state.nations:
            for resource_type, spec in config.RESOURCE_TYPES.items():
                assert state.resources[nation].stocks[resource_type] == spec["starting"]

    def test_alliance_resupply_appears_in_turn_result(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        profiles = {nation: _neutral_profile(nation) for nation in state.nations}
        profiles["Auria"] = _profile(alliance_strength=0.9)
        apply_profile_to_state(state, profiles)
        result = step_simulation(state, [])
        assert any(event.event_type == "alliance_resupply" for event in result.new_state.event_log)

    def test_military_strength_affects_action_count(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        high_state = state.model_copy(deep=True)
        low_state = state.model_copy(deep=True)
        high_state.metadata.setdefault("Auria", {})["military_strength"] = 0.9
        low_state.metadata.setdefault("Auria", {})["military_strength"] = 0.1
        for candidate in (high_state, low_state):
            cmd = next(asset for asset in candidate.get_assets_for("Auria") if asset.asset_type == "command_center")
            cmd.health = cmd.max_health
            cmd.is_destroyed = False
        assert len(select_actions(high_state, "Auria")) > len(select_actions(low_state, "Auria"))

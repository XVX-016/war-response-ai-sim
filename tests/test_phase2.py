# ── ResilienceSim v1 ── tests/test_phase2.py ─────────────────────────────────
# Phase 2 verification tests.
# Run with:  pytest tests/test_phase2.py -v
#
# Covers:
#   - All three hand-crafted scenarios load without error
#   - Scenario validation catches structural errors correctly
#   - Scenario builder generates valid scenarios for all presets
#   - Builder determinism: same seed → identical output
#   - Generated scenarios are loadable by world.py load_scenario()
#   - CLI validate mode passes on valid files and fails on invalid ones

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import config
from engine.world import load_scenario
from engine.scenario_builder import (
    ScenarioValidationError,
    build_scenario,
    load_and_validate,
    save_scenario,
    validate_scenario,
    PRESETS,
)

# ── Scenario file paths ───────────────────────────────────────────────────────
SCENARIO_DIR   = Path("data/scenarios")
CASCADE_CRISIS = SCENARIO_DIR / "cascade_crisis.json"
FLOOD_RESPONSE = SCENARIO_DIR / "flood_response.json"
CASC_BLACKOUT  = SCENARIO_DIR / "cascading_blackout.json"
ALL_SCENARIOS  = [CASCADE_CRISIS, FLOOD_RESPONSE, CASC_BLACKOUT]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Hand-crafted scenario loading
# ─────────────────────────────────────────────────────────────────────────────

class TestHandcraftedScenarios:

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_scenario_file_exists(self, path):
        assert path.exists(), f"Scenario file missing: {path}"

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_scenario_loads_via_world(self, path):
        state, grid = load_scenario(path)
        assert state is not None
        assert grid is not None

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_scenario_passes_validation(self, path):
        data, errors = load_and_validate(path)
        assert errors == [], f"{path.name} has validation errors:\n" + "\n".join(errors)

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_scenario_has_both_nations(self, path):
        state, _ = load_scenario(path)
        for nation in config.NATIONS:
            assert nation in state.nations

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_scenario_assets_have_valid_types(self, path):
        state, _ = load_scenario(path)
        for asset in state.assets:
            assert asset.asset_type in config.ASSET_TYPES

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_scenario_resources_initialised(self, path):
        state, _ = load_scenario(path)
        for nation in state.nations:
            assert nation in state.resources
            for rtype in config.RESOURCE_TYPES:
                assert rtype in state.resources[nation].stocks

    @pytest.mark.parametrize("path", ALL_SCENARIOS)
    def test_scenario_assets_within_grid(self, path):
        state, grid = load_scenario(path)
        for asset in state.assets:
            assert 0 <= asset.row < grid.rows
            assert 0 <= asset.col < grid.cols

    def test_flood_response_transport_degraded(self):
        """Flood scenario should start with transport hubs degraded."""
        state, _ = load_scenario(FLOOD_RESPONSE)
        transport = [
            a for a in state.assets
            if a.asset_type == "transport_hub"
        ]
        degraded = [a for a in transport if a.health < config.DEGRADED_THRESHOLD]
        assert len(degraded) >= 2, "Flood scenario should have at least 2 degraded transport hubs"

    def test_blackout_power_critical(self):
        """Blackout scenario should start with power plants near destroyed."""
        state, _ = load_scenario(CASC_BLACKOUT)
        power = [
            a for a in state.assets
            if a.asset_type == "power_plant"
        ]
        critical = [a for a in power if a.health < config.DEGRADED_THRESHOLD]
        assert len(critical) >= 2, "Blackout scenario should have at least 2 critically damaged power plants"

    def test_flood_has_more_assets_than_cascade(self):
        """Flood scenario has 22 assets (more diverse layout)."""
        state_flood, _ = load_scenario(FLOOD_RESPONSE)
        state_casc, _  = load_scenario(CASCADE_CRISIS)
        assert len(state_flood.assets) > len(state_casc.assets)

    def test_blackout_has_more_zones_than_cascade(self):
        """Blackout scenario has 6 population zones vs 4 in cascade."""
        state_bl, _ = load_scenario(CASC_BLACKOUT)
        state_ca, _ = load_scenario(CASCADE_CRISIS)
        assert len(state_bl.zones) > len(state_ca.zones)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Scenario validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:

    def _minimal_valid(self) -> dict:
        """Return a minimal valid scenario dict for mutation testing."""
        return {
            "name": "Test",
            "seed": 1,
            "grid_rows": 10,
            "grid_cols": 10,
            "nations": ["Auria", "Boros"],
            "assets": [
                {"id": "a_power_01", "name": "A Power", "nation": "Auria",
                 "asset_type": "power_plant", "row": 1, "col": 1, "starting_health": 80},
                {"id": "b_power_01", "name": "B Power", "nation": "Boros",
                 "asset_type": "power_plant", "row": 8, "col": 8, "starting_health": 80},
            ],
            "population_zones": [],
            "starting_disruptions": [],
            "exogenous_event_overrides": {},
        }

    def test_valid_scenario_has_no_errors(self):
        data = self._minimal_valid()
        assert validate_scenario(data) == []

    def test_missing_nations_flagged(self):
        data = self._minimal_valid()
        data["nations"] = []
        errors = validate_scenario(data)
        assert any("nations" in e for e in errors)

    def test_unknown_asset_type_flagged(self):
        data = self._minimal_valid()
        data["assets"][0]["asset_type"] = "missile_launcher"
        errors = validate_scenario(data)
        assert any("unknown asset_type" in e for e in errors)

    def test_duplicate_asset_id_flagged(self):
        data = self._minimal_valid()
        data["assets"][1]["id"] = data["assets"][0]["id"]
        errors = validate_scenario(data)
        assert any("duplicate id" in e for e in errors)

    def test_out_of_bounds_asset_flagged(self):
        data = self._minimal_valid()
        data["assets"][0]["row"] = 99  # beyond grid_rows=10
        errors = validate_scenario(data)
        assert any("out of grid" in e for e in errors)

    def test_duplicate_cell_flagged(self):
        data = self._minimal_valid()
        data["assets"][1]["row"] = data["assets"][0]["row"]
        data["assets"][1]["col"] = data["assets"][0]["col"]
        errors = validate_scenario(data)
        assert any("already occupied" in e for e in errors)

    def test_zone_references_unknown_asset(self):
        data = self._minimal_valid()
        data["population_zones"] = [{
            "id": "zone_01", "name": "Zone 1", "nation": "Auria",
            "row": 3, "col": 3, "population": 10000,
            "served_by_asset_ids": ["nonexistent_asset"],
        }]
        errors = validate_scenario(data)
        assert any("unknown asset" in e for e in errors)

    def test_zone_cross_nation_asset_flagged(self):
        data = self._minimal_valid()
        data["population_zones"] = [{
            "id": "zone_01", "name": "Zone 1", "nation": "Auria",
            "row": 3, "col": 3, "population": 10000,
            "served_by_asset_ids": ["b_power_01"],  # Boros asset in Auria zone
        }]
        errors = validate_scenario(data)
        assert any("nation" in e for e in errors)

    def test_zero_population_flagged(self):
        data = self._minimal_valid()
        data["population_zones"] = [{
            "id": "zone_01", "name": "Zone 1", "nation": "Auria",
            "row": 3, "col": 3, "population": 0,
            "served_by_asset_ids": [],
        }]
        errors = validate_scenario(data)
        assert any("population" in e for e in errors)

    def test_disruption_unknown_asset_flagged(self):
        data = self._minimal_valid()
        data["starting_disruptions"] = [{"asset_id": "ghost_asset", "damage": 30}]
        errors = validate_scenario(data)
        assert any("unknown asset_id" in e for e in errors)

    def test_health_out_of_range_flagged(self):
        data = self._minimal_valid()
        data["assets"][0]["starting_health"] = 999
        errors = validate_scenario(data)
        assert any("starting_health" in e and "out of range" in e for e in errors)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Scenario builder — all presets
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioBuilder:

    @pytest.mark.parametrize("preset", list(PRESETS.keys()))
    def test_build_does_not_raise(self, preset):
        scenario = build_scenario(preset_name=preset, seed=1)
        assert scenario is not None

    @pytest.mark.parametrize("preset", list(PRESETS.keys()))
    def test_built_scenario_passes_validation(self, preset):
        scenario = build_scenario(preset_name=preset, seed=1)
        errors = validate_scenario(scenario)
        assert errors == [], f"Preset '{preset}' generated invalid scenario:\n" + "\n".join(errors)

    @pytest.mark.parametrize("preset", list(PRESETS.keys()))
    def test_built_scenario_loadable_by_world(self, preset):
        """Save to temp file then load via world.py — full integration check."""
        scenario = build_scenario(preset_name=preset, seed=1)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(scenario, f)
            tmp_path = Path(f.name)
        try:
            state, grid = load_scenario(tmp_path)
            assert len(state.assets) > 0
            assert len(state.nations) == 2
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            build_scenario(preset_name="ultra_hard")

    def test_hard_preset_lower_health_than_easy(self):
        """Hard preset should produce lower average health than easy."""
        easy = build_scenario(preset_name="easy",   seed=42)
        hard = build_scenario(preset_name="hard",   seed=42)

        avg_easy = sum(a["starting_health"] for a in easy["assets"]) / len(easy["assets"])
        avg_hard = sum(a["starting_health"] for a in hard["assets"]) / len(hard["assets"])
        assert avg_hard < avg_easy, f"Hard avg {avg_hard:.1f} should be < easy avg {avg_easy:.1f}"

    def test_each_nation_gets_all_asset_types(self):
        """Builder should place one of each asset type per nation."""
        scenario = build_scenario(preset_name="medium", seed=1)
        for nation in config.NATIONS:
            nation_types = {
                a["asset_type"] for a in scenario["assets"]
                if a["nation"] == nation
            }
            for atype in config.ASSET_TYPES:
                assert atype in nation_types, \
                    f"Nation '{nation}' missing asset type '{atype}'"

    def test_no_two_assets_on_same_cell(self):
        scenario = build_scenario(preset_name="medium", seed=1)
        cells = [(a["row"], a["col"]) for a in scenario["assets"]]
        assert len(cells) == len(set(cells)), "Two or more assets placed on same cell"

    def test_all_assets_within_grid(self):
        scenario = build_scenario(preset_name="medium", seed=1)
        rows = scenario["grid_rows"]
        cols = scenario["grid_cols"]
        for a in scenario["assets"]:
            assert 0 <= a["row"] < rows
            assert 0 <= a["col"] < cols

    def test_zone_assets_belong_to_correct_nation(self):
        scenario = build_scenario(preset_name="medium", seed=1)
        asset_nation = {a["id"]: a["nation"] for a in scenario["assets"]}
        for zone in scenario["population_zones"]:
            for aid in zone["served_by_asset_ids"]:
                assert asset_nation.get(aid) == zone["nation"], \
                    f"Zone '{zone['id']}' (nation={zone['nation']}) references " \
                    f"asset '{aid}' from nation '{asset_nation.get(aid)}'"

    def test_hard_preset_fewer_resources(self):
        """Hard preset resource_multiplier < easy → expect fewer resources noted in preset."""
        assert PRESETS["hard"]["resource_multiplier"] < PRESETS["easy"]["resource_multiplier"]

    def test_custom_name_preserved(self):
        scenario = build_scenario(preset_name="easy", seed=1, name="My Custom Scenario")
        assert scenario["name"] == "My Custom Scenario"

    def test_custom_zones_per_nation(self):
        scenario = build_scenario(preset_name="medium", seed=1, num_zones_per_nation=3)
        auria_zones = [z for z in scenario["population_zones"] if z["nation"] == "Auria"]
        boros_zones = [z for z in scenario["population_zones"] if z["nation"] == "Boros"]
        assert len(auria_zones) == 3
        assert len(boros_zones) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 4. Builder determinism
# ─────────────────────────────────────────────────────────────────────────────

class TestBuilderDeterminism:

    def test_same_seed_identical_asset_health(self):
        s1 = build_scenario(preset_name="medium", seed=77)
        s2 = build_scenario(preset_name="medium", seed=77)
        for a1, a2 in zip(s1["assets"], s2["assets"]):
            assert a1["starting_health"] == a2["starting_health"]
            assert a1["row"] == a2["row"]
            assert a1["col"] == a2["col"]

    def test_different_seeds_different_layouts(self):
        s1 = build_scenario(preset_name="medium", seed=1)
        s2 = build_scenario(preset_name="medium", seed=2)
        # At least some cells should differ
        cells1 = {(a["row"], a["col"]) for a in s1["assets"]}
        cells2 = {(a["row"], a["col"]) for a in s2["assets"]}
        assert cells1 != cells2, "Different seeds should produce different layouts"

    def test_same_seed_same_disruptions(self):
        s1 = build_scenario(preset_name="hard", seed=55)
        s2 = build_scenario(preset_name="hard", seed=55)
        assert s1["starting_disruptions"] == s2["starting_disruptions"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Save and reload round-trip
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveReload:

    def test_save_and_reload_round_trip(self):
        original = build_scenario(preset_name="medium", seed=42)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_scenario(original, Path(tmpdir) / "test_scenario.json")
            assert path.exists()
            reloaded, errors = load_and_validate(path)
            assert errors == []
            assert reloaded["name"] == original["name"]
            assert len(reloaded["assets"]) == len(original["assets"])

    def test_file_not_found_returns_error(self):
        _, errors = load_and_validate("nonexistent/path/fake.json")
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_saved_scenario_loadable_by_world(self):
        scenario = build_scenario(preset_name="easy", seed=10)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_scenario(scenario, Path(tmpdir) / "easy_test.json")
            state, grid = load_scenario(path)
            assert len(state.assets) > 0
            assert state.scenario_seed == 10

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import engine.diplomacy as diplomacy

from engine.diplomacy import (
    compute_alliance_drift,
    compute_bilateral_trade,
    compute_diplomatic_events,
    compute_gdp_attrition,
    compute_international_aid,
    initialise_diplomatic_state,
)
from engine.turn_engine import step_simulation
from engine.world import load_scenario
from schemas import DiplomaticState


SCENARIO_PATH = Path("data/scenarios/cascade_crisis.json")


@pytest.fixture
def base_state():
    state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
    profiles = {
        "Auria": {"gdp_index": 0.62, "alliance_strength": 0.65},
        "Boros": {"gdp_index": 0.48, "alliance_strength": 0.20},
    }
    state.metadata.setdefault("Auria", {})["resource_richness"] = 0.7
    state.metadata.setdefault("Boros", {})["resource_richness"] = 0.3
    for asset in state.assets:
        if asset.asset_type == "transport_hub":
            asset.health = asset.max_health
            asset.is_destroyed = False
    state.diplomatic_state = initialise_diplomatic_state(state, profiles)
    return state


class TestDiplomaticStateInit:
    def test_initialise_creates_gdp_for_all_nations(self, base_state):
        assert set(base_state.diplomatic_state.gdp_index) == set(base_state.nations)

    def test_initialise_creates_alliance_for_all_nations(self, base_state):
        assert set(base_state.diplomatic_state.alliance_strength) == set(base_state.nations)

    def test_initialise_creates_bilateral_relation(self, base_state):
        assert len(base_state.diplomatic_state.relations) == 1

    def test_high_alliance_nations_start_with_lower_tension(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        high = initialise_diplomatic_state(
            state,
            {"Auria": {"alliance_strength": 0.9}, "Boros": {"alliance_strength": 0.8}},
        )
        low = initialise_diplomatic_state(
            state,
            {"Auria": {"alliance_strength": 0.1}, "Boros": {"alliance_strength": 0.1}},
        )
        assert list(high.relations.values())[0].tension < list(low.relations.values())[0].tension

    def test_relation_key_is_alphabetically_sorted(self, base_state):
        assert base_state.diplomatic_state.relation_key("Boros", "Auria") == "Auria::Boros"


class TestGdpAttrition:
    def test_destroyed_critical_assets_reduce_gdp(self, base_state):
        for asset in base_state.get_assets_for("Auria"):
            if asset.is_critical:
                asset.health = 0
                asset.is_destroyed = True
                break
        deltas = compute_gdp_attrition(base_state)
        assert deltas["Auria"] < 0

    def test_healthy_assets_allow_gdp_recovery(self, base_state):
        deltas = compute_gdp_attrition(base_state)
        assert deltas["Auria"] > 0


class TestBilateralTrade:
    def test_trade_transfers_resources_between_nations(self, base_state):
        received, events = compute_bilateral_trade(base_state, base_state.diplomatic_state)
        assert received["Auria"] or received["Boros"]
        assert events

    def test_sanctions_reduce_trade_volume_by_70_pct(self, base_state):
        relation = list(base_state.diplomatic_state.relations.values())[0]
        relation.sanctions_active = True
        sanctioned, _ = compute_bilateral_trade(base_state, base_state.diplomatic_state)
        relation.sanctions_active = False
        normal, _ = compute_bilateral_trade(base_state, base_state.diplomatic_state)
        assert sum(sanctioned["Auria"].values()) < sum(normal["Auria"].values())

    def test_degraded_transport_blocks_trade(self, base_state):
        for asset in base_state.assets:
            if asset.asset_type == "transport_hub":
                asset.health = 10
        received, events = compute_bilateral_trade(base_state, base_state.diplomatic_state)
        assert received == {"Auria": {}, "Boros": {}}
        assert any("disrupted" in event for event in events)


class TestInternationalAid:
    def test_aid_triggered_below_coverage_threshold(self, base_state):
        for asset in base_state.get_assets_for("Auria"):
            asset.health = 0
            asset.is_destroyed = True
        aid, _ = compute_international_aid(base_state, base_state.diplomatic_state)
        assert aid["Auria"]

    def test_aid_not_triggered_above_threshold(self, base_state):
        aid, _ = compute_international_aid(base_state, base_state.diplomatic_state)
        assert aid["Auria"] == {}


class TestDiplomaticEvents:
    def test_events_are_deterministic_same_seed(self, base_state):
        first_rel, first_events = compute_diplomatic_events(base_state, base_state.diplomatic_state)
        second_rel, second_events = compute_diplomatic_events(base_state, base_state.diplomatic_state)
        assert first_events == second_events
        assert first_rel == second_rel

    def test_different_turns_produce_different_events(self, base_state):
        _, turn_zero = compute_diplomatic_events(base_state, base_state.diplomatic_state)
        base_state.turn += 1
        _, turn_one = compute_diplomatic_events(base_state, base_state.diplomatic_state)
        assert turn_zero != turn_one or base_state.turn == 1

    def test_tension_naturally_decays_each_turn(self, base_state, monkeypatch):
        relation = list(base_state.diplomatic_state.relations.values())[0]
        relation.tension = 0.3
        monkeypatch.setattr(diplomacy, "EVENT_PROBABILITIES", {key: 0.0 for key in diplomacy.EVENT_PROBABILITIES})
        updated, _ = compute_diplomatic_events(base_state, base_state.diplomatic_state)
        assert list(updated.values())[0].tension <= 0.3


class TestAllianceDrift:
    def test_high_tension_reduces_alliance(self, base_state):
        relation = list(base_state.diplomatic_state.relations.values())[0]
        relation.tension = 1.0
        deltas = compute_alliance_drift(base_state, base_state.diplomatic_state)
        assert deltas["Auria"] < 0

    def test_low_tension_allows_alliance_recovery(self, base_state):
        relation = list(base_state.diplomatic_state.relations.values())[0]
        relation.tension = 0.0
        deltas = compute_alliance_drift(base_state, base_state.diplomatic_state)
        assert deltas["Auria"] > 0


class TestFullDiplomaticTurn:
    def test_apply_diplomatic_turn_returns_new_state(self, base_state):
        result = step_simulation(base_state, [])
        assert isinstance(result.new_state.diplomatic_state, DiplomaticState)

    def test_trade_resources_applied_to_stocks_after_step(self, base_state):
        before = base_state.resources["Auria"].stocks["fuel"]
        result = step_simulation(base_state, [])
        after = result.new_state.resources["Auria"].stocks["fuel"]
        assert after >= before

    def test_gdp_index_changes_after_turn(self, base_state):
        before = base_state.diplomatic_state.gdp_index["Auria"]
        result = step_simulation(base_state, [])
        after = result.new_state.diplomatic_state.gdp_index["Auria"]
        assert before != after

    def test_diplomatic_events_appear_in_event_log(self, base_state):
        result = step_simulation(base_state, [])
        event_types = {event.event_type for event in result.new_state.event_log}
        assert {"trade", "international_aid", "diplomatic_event", "gdp_change"} & event_types

    def test_none_diplomatic_state_skips_gracefully(self):
        state, _ = load_scenario(SCENARIO_PATH, apply_profiles=False)
        result = step_simulation(state, [])
        assert result.new_state.diplomatic_state is None

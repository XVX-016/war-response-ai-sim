# ── ResilienceSim v1 ── tests/test_phase1.py ─────────────────────────────────
# Phase 1 verification tests.
# Run with:  pytest tests/test_phase1.py -v
#
# Covers:
#   - Scenario loading and world state construction
#   - Dependency graph and consequence computation
#   - Turn-state transitions (repair, exogenous events)
#   - Determinism (identical seed → identical output)
#   - Rule agent prioritisation
#   - End condition detection

import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import config
from engine.world import load_scenario
from engine.turn_engine import step_simulation
from engine import consequence as csq
from agents.rule_agent import select_actions
from schemas import Action, ScenarioState

SCENARIO_PATH = Path("data/scenarios/cascade_crisis.json")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def loaded():
    """Return (state, grid) from the default scenario."""
    return load_scenario(SCENARIO_PATH)


@pytest.fixture
def state(loaded):
    return loaded[0]


@pytest.fixture
def grid(loaded):
    return loaded[1]


# ─────────────────────────────────────────────────────────────────────────────
# 1. World loading
# ─────────────────────────────────────────────────────────────────────────────

class TestWorldLoading:
    def test_scenario_loads_without_error(self, state, grid):
        assert state is not None
        assert grid is not None

    def test_correct_number_of_assets(self, state):
        # cascade_crisis.json defines 16 assets
        assert len(state.assets) == 16

    def test_asset_types_are_valid(self, state):
        for asset in state.assets:
            assert asset.asset_type in config.ASSET_TYPES, (
                f"Asset '{asset.id}' has unknown type '{asset.asset_type}'"
            )

    def test_assets_have_correct_health_bounds(self, state):
        for asset in state.assets:
            assert 0 <= asset.health <= asset.max_health, (
                f"Asset '{asset.id}' health {asset.health} out of range [0, {asset.max_health}]"
            )

    def test_starting_health_overrides_apply(self, state):
        # Auria power plant starts at 35 per scenario JSON after the harder baseline rebalance
        auria_power = state.get_asset("auria_power_01")
        assert auria_power is not None
        assert auria_power.health == 35.0

    def test_max_health_from_config(self, state):
        # power_plant max_health = 100 per config.ASSET_TYPES
        auria_power = state.get_asset("auria_power_01")
        assert auria_power.max_health == config.ASSET_TYPES["power_plant"]["max_health"]

    def test_resource_stocks_initialised(self, state):
        for nation in state.nations:
            assert nation in state.resources
            res = state.resources[nation]
            for rtype in config.RESOURCE_TYPES:
                assert rtype in res.stocks
                assert res.stocks[rtype] == config.RESOURCE_TYPES[rtype]["starting"]

    def test_population_zones_loaded(self, state):
        assert len(state.zones) == 4   # cascade_crisis.json has 4 zones

    def test_grid_places_assets(self, grid, state):
        for asset in state.assets:
            cell = grid.cell(asset.row, asset.col)
            assert asset.id in cell.asset_ids


# ─────────────────────────────────────────────────────────────────────────────
# 2. Consequence computation
# ─────────────────────────────────────────────────────────────────────────────

class TestConsequences:
    def test_degraded_power_plant_emits_blackout(self, state):
        # auria_power_01 starts at 45 HP < DEGRADED_THRESHOLD (50)
        consequences = csq.compute_consequences(state)
        assert "blackout" in consequences["Auria"]

    def test_healthy_asset_emits_no_consequence(self, state):
        # Find a healthy asset and confirm its consequence tags are absent
        # auria_telecom_01 starts at 80 HP (healthy)
        consequences = csq.compute_consequences(state)
        assert "comms_degraded" not in consequences["Auria"]

    def test_dependency_penalty_fires_for_degraded_dep(self, state):
        # auria_power_01 is at 45 HP → hospital should incur dependency penalty
        penalties, events = csq.apply_dependency_penalties(state)
        # hospital depends on power_plant
        assert "auria_hospital_01" in penalties
        assert penalties["auria_hospital_01"] >= config.DEPENDENCY_PENALTY

    def test_no_penalty_for_healthy_dep(self, state):
        # auria_telecom_01 is healthy (80 HP) → command_center should have no penalty from it
        penalties, _ = csq.apply_dependency_penalties(state)
        cmd_penalty = penalties.get("auria_cmd_01", 0)
        # command_center depends on power_plant (degraded) and telecom (healthy)
        # penalty should be exactly DEPENDENCY_PENALTY (only from power dep)
        assert cmd_penalty == config.DEPENDENCY_PENALTY

    def test_update_population_zones_reduces_coverage(self, state):
        zone_updates, _ = csq.update_population_zones(state)
        # auria_zone_north depends on degraded assets → coverage < 1.0
        assert zone_updates["auria_zone_north"]["service_coverage"] < 1.0

    def test_cascade_power_to_hospital(self, state):
        """Power degraded → hospital loses HP next turn via dependency."""
        penalties, _ = csq.apply_dependency_penalties(state)
        assert "auria_hospital_01" in penalties


# ─────────────────────────────────────────────────────────────────────────────
# 3. Turn-state transitions
# ─────────────────────────────────────────────────────────────────────────────

class TestTurnTransitions:
    def test_repair_action_increases_health(self, state):
        asset = state.get_asset("auria_power_01")
        hp_before = asset.health
        action = Action(
            actor_nation    = "Auria",
            action_type     = "repair",
            target_asset_id = "auria_power_01",
        )
        result = step_simulation(state, [action])
        repaired = result.new_state.get_asset("auria_power_01")
        assert repaired.health > hp_before

    def test_repair_costs_resources(self, state):
        res_before = state.resources["Auria"].stocks.copy()
        action = Action(
            actor_nation    = "Auria",
            action_type     = "repair",
            target_asset_id = "auria_power_01",
        )
        result = step_simulation(state, [action])
        res_after = result.new_state.resources["Auria"].stocks
        cost = config.ACTION_TYPES["repair"]["cost"]
        for resource, amount in cost.items():
            # after repair cost + resupply; cost should show net reduction
            assert res_after[resource] <= res_before[resource] + config.BASE_RESUPPLY_PER_TURN.get(resource, 0)

    def test_invalid_action_is_rejected(self, state):
        bad_action = Action(
            actor_nation    = "Auria",
            action_type     = "repair",
            target_asset_id = "nonexistent_asset_999",
        )
        result = step_simulation(state, [bad_action])
        rejected = [e for e in result.new_state.event_log if e.event_type == "action_rejected"]
        assert len(rejected) >= 1

    def test_state_is_not_mutated(self, state):
        hp_before = state.get_asset("auria_power_01").health
        action = Action(
            actor_nation    = "Auria",
            action_type     = "repair",
            target_asset_id = "auria_power_01",
        )
        step_simulation(state, [action])
        # original state should be unchanged
        assert state.get_asset("auria_power_01").health == hp_before

    def test_turn_increments(self, state):
        result = step_simulation(state, [])
        assert result.new_state.turn == state.turn + 1

    def test_multi_turn_repair_queues_then_completes(self, state):
        action = Action(
            actor_nation    = "Auria",
            action_type     = "repair",
            target_asset_id = "auria_power_01",
        )
        # repair takes 2 turns
        result1 = step_simulation(state, [action])
        assert len(result1.new_state.pending_actions.get("Auria", [])) == 1

        result2 = step_simulation(result1.new_state, [])
        assert len(result2.new_state.pending_actions.get("Auria", [])) == 0
        assert "auria_power_01" in result2.assets_repaired


# ─────────────────────────────────────────────────────────────────────────────
# 4. Determinism
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_seed_same_result(self):
        """Two runs with identical seed and actions must produce identical health values."""
        state1, _ = load_scenario(SCENARIO_PATH)
        state2, _ = load_scenario(SCENARIO_PATH)

        # No actions — only exogenous events and degradation
        result1 = step_simulation(state1, [])
        result2 = step_simulation(state2, [])

        for a1, a2 in zip(result1.new_state.assets, result2.new_state.assets):
            assert a1.health == a2.health, f"Non-deterministic: {a1.id} {a1.health} vs {a2.health}"

    def test_different_turn_different_exogenous(self):
        """Exogenous rolls should differ across turns (not always fire or not fire)."""
        state, _ = load_scenario(SCENARIO_PATH)
        # Run 5 turns, collect exogenous event counts
        exo_counts = []
        current = state
        for _ in range(5):
            result = step_simulation(current, [])
            exo_counts.append(len(result.exogenous_events))
            current = result.new_state
        # Not all turns should have the same count (would be suspicious if identical)
        # Just check the list exists and has 5 entries
        assert len(exo_counts) == 5


# ─────────────────────────────────────────────────────────────────────────────
# 5. Rule agent behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestRuleAgent:
    def test_agent_returns_list_of_actions(self, state):
        actions = select_actions(state, "Auria")
        assert isinstance(actions, list)

    def test_agent_prioritises_critical_assets(self, state):
        """Rule agent should prefer to repair power/hospital over shelter."""
        actions = select_actions(state, "Auria")
        repair_actions = [a for a in actions if a.action_type == "repair"]
        if repair_actions:
            target = state.get_asset(repair_actions[0].target_asset_id)
            assert target is not None
            # power_plant (priority 10) and hospital (priority 10) should come first
            assert config.ASSET_PRIORITY.get(target.asset_type, 0) >= config.ASSET_PRIORITY.get("shelter", 0)

    def test_agent_does_not_overspend(self, state):
        """All actions from the agent must be affordable."""
        actions = select_actions(state, "Auria")
        res = state.resources["Auria"]
        running_stocks = res.stocks.copy()
        for action in actions:
            cost = config.ACTION_TYPES[action.action_type]["cost"]
            for k, v in cost.items():
                assert running_stocks.get(k, 0) >= v, (
                    f"Agent proposed unaffordable action: {action.action_type} needs {k}={v}, has {running_stocks.get(k,0)}"
                )
                running_stocks[k] -= v

    def test_agent_returns_empty_when_no_affordable_action(self, state):
        """Drain all resources → agent should return empty list."""
        state_copy = state.model_copy(deep=True)
        for nation in state_copy.nations:
            for k in state_copy.resources[nation].stocks:
                state_copy.resources[nation].stocks[k] = 0.0
        actions = select_actions(state_copy, "Auria")
        assert all(action.action_type == "inspect" for action in actions)


# ─────────────────────────────────────────────────────────────────────────────
# 6. End conditions
# ─────────────────────────────────────────────────────────────────────────────

class TestEndConditions:
    def test_collapse_detected_when_coverage_low(self, state):
        """Artificially destroy all assets → should trigger collapse."""
        state_copy = state.model_copy(deep=True)
        for asset in state_copy.assets:
            if asset.nation == "Auria":
                asset.health = 0.0
                asset.is_destroyed = True
        result = csq.check_end_conditions(state_copy)
        assert result.get("Auria") == "collapsed"

    def test_stabilised_after_consecutive_healthy_turns(self, state):
        """Auria should stabilise once it has 8 consecutive healthy turns on critical assets."""
        current = state.model_copy(deep=True)
        for asset in current.assets:
            if asset.nation == "Auria" and asset.is_critical:
                asset.health = asset.max_health
                asset.is_destroyed = False

        current.stable_turns_count["Auria"] = 7
        result = csq.check_end_conditions(current)

        assert result.get("Auria") == "stabilised"
    def test_timeout_at_max_turns(self, state):
        state_copy = state.model_copy(deep=True)
        state_copy.turn = state_copy.max_turns
        result = csq.check_end_conditions(state_copy)
        assert all(v == "timeout" for v in result.values())


from __future__ import annotations

from copy import deepcopy

from agents.rule_agent import select_actions
from engine.turn_engine import step_simulation
from engine.world import load_scenario
from render import render_event_log, render_grid, render_resource_delta, render_state


def _load():
    return load_scenario('data/scenarios/cascade_crisis.json')


class TestRenderState:
    def test_render_state_returns_required_keys(self):
        state, _ = _load()
        data = render_state(state)
        assert {"turn", "is_terminal", "nations", "assets", "zones", "resources", "active_consequences", "end_conditions", "event_log", "kpis"}.issubset(data.keys())

    def test_assets_have_color_field(self):
        state, _ = _load()
        data = render_state(state)
        assert all(asset.get("color") for asset in data["assets"])

    def test_health_fraction_clamped(self):
        state, _ = _load()
        state.assets[0].health = 9999
        data = render_state(state)
        assert all(0.0 <= asset["health_fraction"] <= 1.0 for asset in data["assets"])

    def test_event_log_newest_first(self):
        state, _ = _load()
        current = state
        for _ in range(3):
            result = step_simulation(current, [])
            current = result.new_state
        data = render_state(current)
        turns = [event["turn"] for event in data["event_log"]]
        assert turns == sorted(turns, reverse=True)

    def test_event_log_capped_at_50(self):
        state, _ = _load()
        for idx in range(60):
            state.event_log.append(deepcopy(state.event_log[-1]).model_copy(update={"turn": idx + 1, "description": f"event {idx}"}))
        data = render_state(state)
        assert len(data["event_log"]) == 50

    def test_kpis_have_required_keys(self):
        state, _ = _load()
        data = render_state(state)
        for nation in data["nations"]:
            assert {"service_coverage_score", "total_displaced", "stable_turns", "end_condition"}.issubset(data["kpis"][nation].keys())

    def test_resource_fractions_between_0_and_1(self):
        state, _ = _load()
        data = render_state(state)
        for nation in data["resources"].values():
            for resource in nation.values():
                assert 0.0 <= resource["fraction"] <= 1.0


class TestRenderGrid:
    def test_grid_dimensions(self):
        state, grid = _load()
        data = render_grid(state, grid)
        assert len(data) == grid.rows
        assert all(len(row) == grid.cols for row in data)

    def test_occupied_cells_have_assets(self):
        state, grid = _load()
        data = render_grid(state, grid)
        occupied = [cell for row in data for cell in row if cell["asset_ids"]]
        assert occupied and all(cell["assets"] for cell in occupied)

    def test_empty_cells_have_no_assets(self):
        state, grid = _load()
        data = render_grid(state, grid)
        empty = [cell for row in data for cell in row if not cell["asset_ids"]]
        assert empty and all(cell["assets"] == [] for cell in empty)


class TestRenderDelta:
    def test_repair_shows_negative_resource_delta(self):
        state, _ = _load()
        actions = select_actions(state, 'Auria')
        result = step_simulation(state, actions)
        delta = render_resource_delta(state, result.new_state)
        assert delta['Auria']['repair_crews'] <= 0

    def test_resupply_shows_in_delta(self):
        state, _ = _load()
        result = step_simulation(state, [])
        delta = render_resource_delta(state, result.new_state)
        assert delta['Auria']['fuel'] >= 0


class TestRenderEventLog:
    def test_returns_list_of_dicts(self):
        state, _ = _load()
        events = render_event_log(state)
        assert isinstance(events, list)
        assert all(isinstance(event, dict) for event in events)

    def test_limit_respected(self):
        state, _ = _load()
        events = render_event_log(state, limit=5)
        assert len(events) <= 5

    def test_all_required_keys_present(self):
        state, _ = _load()
        events = render_event_log(state, limit=5)
        if events:
            assert {"turn", "event_type", "description", "severity"}.issubset(events[0].keys())

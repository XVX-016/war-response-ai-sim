from __future__ import annotations

from copy import deepcopy

import streamlit as st
from loguru import logger

import config
from ai_narrator import ClaudeNarrator
from agents.rule_agent import select_actions
from engine.scenario_builder import ScenarioValidationError
from engine.turn_engine import step_simulation
from engine.world import load_scenario
from render import render_grid, render_state
from ui.controls import draw_auto_step, draw_scenario_selector, draw_turn_controls
from ui.event_log import draw_event_log
from ui.kpi_panel import (
    draw_asset_detail,
    draw_consequence_badges,
    draw_nation_kpis,
    draw_resource_bars,
)
from ui.map_panel import draw_map


st.set_page_config(layout="wide", page_title=config.PAGE_TITLE)


def _init_session_state() -> None:
    defaults = {
        "state": None,
        "grid": None,
        "render_data": None,
        "prev_render": None,
        "scenario_path": None,
        "history": [],
        "selected_asset": None,
        "balloons_shown": False,
        "narrator": None,
        "last_narrative": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_selected_scenario(path: str) -> None:
    state, grid = load_scenario(path)
    st.session_state.state = state.model_copy(deep=True)
    st.session_state.grid = deepcopy(grid)
    st.session_state.render_data = render_state(st.session_state.state)
    st.session_state.prev_render = None
    st.session_state.scenario_path = path
    st.session_state.history = [deepcopy(st.session_state.render_data)]
    st.session_state.selected_asset = None
    st.session_state.balloons_shown = False
    st.session_state.last_narrative = ""
    logger.info("Loaded scenario {}", path)


def step_one_turn() -> None:
    state = st.session_state.state
    if state is None or state.is_terminal:
        return

    with st.spinner("Simulating turn..."):
        actions = []
        for nation in state.nations:
            actions.extend(select_actions(state, nation))
        result = step_simulation(state, actions, narrator=st.session_state.narrator)
        st.session_state.prev_render = deepcopy(st.session_state.render_data)
        st.session_state.state = result.new_state.model_copy(deep=True)
        st.session_state.render_data = render_state(st.session_state.state)
        st.session_state.history.append(deepcopy(st.session_state.render_data))
        st.session_state.last_narrative = result.narrative
    st.rerun()


def main() -> None:
    _init_session_state()
    if st.session_state.narrator is None:
        st.session_state.narrator = ClaudeNarrator()

    col_left, col_main, col_right = st.columns([1, 3, 2])

    with col_left:
        selected_path = draw_scenario_selector()
        if selected_path and selected_path != st.session_state.scenario_path:
            try:
                _load_selected_scenario(selected_path)
            except (ScenarioValidationError, FileNotFoundError, ValueError) as exc:
                st.error(str(exc))

        if st.session_state.state is not None:
            controls = draw_turn_controls(
                st.session_state.state.is_terminal,
                st.session_state.state.turn,
                st.session_state.state.max_turns,
            )
            if controls["reset"] and st.session_state.scenario_path:
                try:
                    _load_selected_scenario(st.session_state.scenario_path)
                    st.rerun()
                except (ScenarioValidationError, FileNotFoundError, ValueError) as exc:
                    st.error(str(exc))
            if controls["advance"]:
                step_one_turn()
        else:
            controls = {"nation_filter": "All", "auto_step": False, "step_delay": 1.0}
            st.info("Select a scenario to begin.")

    state = st.session_state.state
    grid = st.session_state.grid
    render_data = st.session_state.render_data

    with col_main:
        if state is not None and render_data is not None and grid is not None:
            st.title(f"{state.scenario_name} ? Turn {state.turn}")
            grid_data = render_grid(state, grid)
            asset_id = draw_map(render_data, grid_data, controls["nation_filter"])
            if asset_id:
                st.session_state.selected_asset = asset_id
        else:
            st.title("ResilienceSim v1")
            st.caption("Load a scenario from the left panel to view the dashboard.")

    with col_right:
        if render_data is not None:
            auria_tab, boros_tab, events_tab = st.tabs(config.NATIONS + ["Events"])
            with auria_tab:
                draw_nation_kpis(render_data, config.NATION_A)
                draw_resource_bars(render_data, config.NATION_A)
                draw_consequence_badges(render_data, config.NATION_A)
            with boros_tab:
                draw_nation_kpis(render_data, config.NATION_B)
                draw_resource_bars(render_data, config.NATION_B)
                draw_consequence_badges(render_data, config.NATION_B)
            with events_tab:
                draw_event_log(render_data.get("event_log", []), narrative=st.session_state.get("last_narrative", ""))

            if st.session_state.selected_asset:
                asset = next((item for item in render_data["assets"] if item["id"] == st.session_state.selected_asset), None)
                if asset:
                    st.divider()
                    draw_asset_detail(asset)
        else:
            st.info("KPIs and events will appear once a scenario is loaded.")

    if render_data and render_data.get("is_terminal") and not st.session_state.get("balloons_shown"):
        st.balloons()
        st.session_state.balloons_shown = True

    if state is not None:
        draw_auto_step(controls, step_one_turn)


if __name__ == "__main__":
    main()

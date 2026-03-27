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
from ui.timeline import draw_timeline


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
        "theme_css_injected": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _inject_theme_css() -> None:
    if st.session_state.get("theme_css_injected"):
        return
    st.markdown(
        """
        <style>
        :root {
          --bg-main: #0f172a;
          --bg-card: #1e293b;
          --bg-card-soft: #172236;
          --border: #334155;
          --text-main: #e2e8f0;
          --text-muted: #94a3b8;
          --accent: #3b82f6;
          --accent-amber: #f59e0b;
          --good: #22c55e;
          --warn: #f59e0b;
          --bad: #ef4444;
        }

        .stApp {
          background:
            radial-gradient(circle at top left, rgba(59, 130, 246, 0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(245, 158, 11, 0.14), transparent 24%),
            linear-gradient(180deg, #0b1220 0%, var(--bg-main) 24%, #111b30 100%);
          color: var(--text-main);
        }

        [data-testid="stAppViewContainer"] > .main {
          padding-top: 0.8rem;
        }

        [data-testid="stHeader"] {
          background: rgba(15, 23, 42, 0);
        }

        #MainMenu, header [data-testid="stToolbar"] {
          visibility: hidden;
          height: 0;
        }

        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, #1e293b 0%, #172033 100%);
          border-right: 1px solid rgba(148, 163, 184, 0.12);
        }

        [data-testid="stSidebar"] * {
          color: var(--text-main);
        }

        [data-testid="stMetric"] {
          background: rgba(15, 23, 42, 0.32);
          border: 1px solid rgba(148, 163, 184, 0.14);
          border-radius: 10px;
          padding: 0.7rem 0.8rem;
        }

        [data-testid="stMetricLabel"] {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: var(--text-muted);
        }

        [data-testid="stMetricValue"] {
          color: var(--text-main);
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
          gap: 0.35rem;
        }

        [data-testid="stTabs"] [data-baseweb="tab"] {
          background: rgba(15, 23, 42, 0.5);
          border: 1px solid rgba(148, 163, 184, 0.12);
          border-radius: 999px;
          color: var(--text-muted);
          padding: 0.4rem 0.9rem;
        }

        [data-testid="stTabs"] [aria-selected="true"] {
          background: rgba(59, 130, 246, 0.16);
          border-color: rgba(59, 130, 246, 0.55);
          color: #dbeafe;
        }

        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          gap: 1rem;
          margin-bottom: 0.45rem;
        }

        .dashboard-header-left {
          min-width: 0;
        }

        .dashboard-eyebrow {
          font-size: 0.72rem;
          letter-spacing: 0.22em;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 0.35rem;
        }

        .dashboard-title {
          font-size: 2rem;
          line-height: 1.1;
          font-weight: 700;
          color: #f8fafc;
        }

        .dashboard-subtitle {
          color: #cbd5e1;
          opacity: 0.95;
        }

        .dashboard-header-right {
          display: flex;
          align-items: center;
          gap: 0.65rem;
          background: rgba(15, 23, 42, 0.55);
          border: 1px solid rgba(148, 163, 184, 0.12);
          border-radius: 999px;
          padding: 0.55rem 0.9rem;
          white-space: nowrap;
        }

        .status-dot {
          width: 0.7rem;
          height: 0.7rem;
          border-radius: 999px;
          display: inline-block;
          box-shadow: 0 0 14px currentColor;
        }

        .dashboard-rule {
          border: none;
          border-top: 1px solid var(--border);
          margin: 0 0 1rem 0;
        }

        .kpi-card {
          background: linear-gradient(180deg, rgba(30, 41, 59, 0.96) 0%, rgba(15, 23, 42, 0.96) 100%);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
          border: 1px solid rgba(148, 163, 184, 0.12);
          border-left: 3px solid var(--accent);
        }

        .section-label {
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: var(--text-muted);
          margin-bottom: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.theme_css_injected = True


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


def _status_tone(render_data: dict) -> tuple[str, str]:
    if render_data.get("end_conditions"):
        if any(value == "collapsed" for value in render_data["end_conditions"].values()):
            return ("#ef4444", "Critical")
        if all(value == "stabilised" for value in render_data["end_conditions"].values()):
            return ("#22c55e", "Stable")
    coverage_values = [
        float(data.get("service_coverage_score", 0.0))
        for data in render_data.get("kpis", {}).values()
    ]
    if not coverage_values:
        return ("#3b82f6", "Monitoring")
    min_coverage = min(coverage_values)
    if min_coverage < 0.4:
        return ("#ef4444", "Critical")
    if min_coverage < 0.7:
        return ("#f59e0b", "Active")
    return ("#22c55e", "Stable")


def _draw_header(state, render_data: dict | None) -> None:
    if state is None or render_data is None:
        st.markdown(
            """
            <div class="dashboard-header">
              <div class="dashboard-header-left">
                <div class="dashboard-eyebrow">ResilienceSim</div>
                <div class="dashboard-title">Civil Protection Dashboard</div>
                <div class="dashboard-subtitle">Load a scenario to begin the response simulation.</div>
              </div>
            </div>
            <hr class="dashboard-rule" />
            """,
            unsafe_allow_html=True,
        )
        return

    status_color, status_label = _status_tone(render_data)
    st.markdown(
        f"""
        <div class="dashboard-header">
          <div class="dashboard-header-left">
            <div class="dashboard-eyebrow">ResilienceSim</div>
            <div class="dashboard-title">{state.scenario_name}</div>
            <div class="dashboard-subtitle">Civil protection monitoring and response operations</div>
          </div>
          <div class="dashboard-header-right">
            <span class="status-dot" style="color:{status_color}; background:{status_color};"></span>
            <span>Turn {state.turn} / {state.max_turns}</span>
            <span style="color:#94a3b8;">{status_label}</span>
          </div>
        </div>
        <hr class="dashboard-rule" />
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _init_session_state()
    _inject_theme_css()
    if st.session_state.narrator is None:
        st.session_state.narrator = ClaudeNarrator()

    state = st.session_state.state
    render_data = st.session_state.render_data
    _draw_header(state, render_data)

    col_left, col_main, col_right = st.columns([1.2, 2.8, 2.0])

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
            grid_data = render_grid(state, grid)
            asset_id = draw_map(render_data, grid_data, controls["nation_filter"])
            if asset_id:
                st.session_state.selected_asset = asset_id
            draw_timeline(st.session_state.history)
        else:
            st.markdown('<div class="section-label">Situation View</div>', unsafe_allow_html=True)
            st.caption("Load a scenario from the left panel to view the dashboard.")

    with col_right:
        if render_data is not None:
            nations_with_assets = [
                nation for nation in config.NATIONS
                if any(asset["nation"] == nation for asset in render_data.get("assets", []))
            ]
            tab_labels = nations_with_assets + ["Events"]
            tabs = st.tabs(tab_labels)
            for tab, label in zip(tabs, tab_labels):
                with tab:
                    if label == "Events":
                        draw_event_log(render_data.get("event_log", []), narrative=st.session_state.get("last_narrative", ""))
                    else:
                        draw_nation_kpis(render_data, label)
                        draw_resource_bars(render_data, label)
                        draw_consequence_badges(render_data, label)

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

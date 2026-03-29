from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import streamlit as st
from loguru import logger

import config
from ai_narrator import ClaudeNarrator
from agents.rule_agent import select_actions
from engine.country import apply_profile_to_state, load_country_profile
from engine.scenario_builder import (
    ScenarioValidationError,
    build_scenario_from_vision,
    load_and_validate,
    merge_vision_assets,
    save_scenario,
)
from engine.turn_engine import step_simulation
from engine.world import load_scenario
from render import render_grid, render_state
from ui.controls import draw_auto_step, draw_scenario_selector, draw_turn_controls
from ui.country_setup import draw_country_setup
from ui.event_log import draw_event_log
from ui.kpi_panel import (
    draw_asset_detail,
    draw_consequence_badges,
    draw_country_profile_summary,
    draw_nation_kpis,
    draw_resource_bars,
)
from ui.map_panel import draw_map
from ui.timeline import draw_timeline
from ui.vision_panel import draw_vision_panel


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
        "setup_complete": False,
        "country_profiles": {},
        "detector": None,
        "pending_vision_assets": [],
        "vision_status_message": "",
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
          --bg-base: #0f172a;
          --bg-surface: #1e293b;
          --bg-raised: #253347;
          --border: #334155;
          --accent: #3b82f6;
          --accent-dim: #1d4ed8;
          --text-primary: #f1f5f9;
          --text-secondary: #94a3b8;
          --text-muted: #475569;
          --green: #22c55e;
          --amber: #f59e0b;
          --red: #ef4444;
          --purple: #a855f7;
        }

        [data-testid="stAppViewContainer"] { background: #0f172a; }
        [data-testid="stAppViewContainer"] > .main { padding-top: 0.75rem; }
        .stApp { background: #0f172a; color: #f1f5f9; }
        [data-testid="stSidebar"] { background: #1e293b; border-right: 1px solid #334155; }
        [data-testid="stSidebar"] * { color: #f1f5f9; }
        .kpi-card, .panel-card, .map-panel { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 16px; }
        .dashboard-header { background: #1e293b; border-bottom: 1px solid #334155; padding: 12px 24px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; gap: 16px; }
        .dashboard-title { font-size: 18px; font-weight: 600; color: #f1f5f9; }
        .dashboard-turn { font-size: 13px; font-family: monospace; color: #94a3b8; }
        [data-testid="stMetric"] { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 16px; }
        [data-testid="stMetricLabel"] { color: #94a3b8; }
        [data-testid="stMetricValue"] { font-family: monospace; font-size: 28px; color: #f1f5f9; }
        [data-testid="stMetricDelta"] { font-family: monospace; }
        button[kind], .stButton > button, [data-testid="stBaseButton-secondary"] { background: #1e293b; border: 1px solid #334155; color: #f1f5f9; border-radius: 4px; box-shadow: none; }
        [data-testid="stBaseButton-primary"] { background: #3b82f6; border: 1px solid #3b82f6; color: #f1f5f9; border-radius: 6px; box-shadow: none; }
        button[kind]:hover, .stButton > button:hover, [data-testid="stBaseButton-secondary"]:hover { background: #253347; border-color: #3b82f6; color: #f1f5f9; }
        [data-testid="stBaseButton-primary"]:hover { background: #1d4ed8; border-color: #1d4ed8; color: #f1f5f9; }
        button[kind]:disabled, .stButton > button:disabled, [data-testid="stBaseButton-secondary"]:disabled, [data-testid="stBaseButton-primary"]:disabled { opacity: 0.4; cursor: not-allowed; }
        .event-row { background: transparent; padding: 8px 12px; margin-bottom: 4px; }
        .event-row:hover { background: #253347; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.theme_css_injected = True


def _load_selected_scenario(path: str) -> None:
    state, grid = load_scenario(path, apply_profiles=False)
    profiles = st.session_state.get("country_profiles", {})
    if profiles:
        apply_profile_to_state(state, profiles)
        state.metadata["_profiles_applied"] = True
    st.session_state.state = state.model_copy(deep=True)
    st.session_state.grid = deepcopy(grid)
    st.session_state.render_data = render_state(st.session_state.state)
    st.session_state.prev_render = None
    st.session_state.scenario_path = path
    st.session_state.history = [deepcopy(st.session_state.render_data)]
    st.session_state.selected_asset = None
    st.session_state.balloons_shown = False
    st.session_state.last_narrative = ""
    logger.info(f"Loaded scenario {path}")


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
    coverage_values = [float(data.get("service_coverage_score", 0.0)) for data in render_data.get("kpis", {}).values()]
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
        st.markdown('<div class="dashboard-header"><div class="dashboard-title">ResilienceSim</div><div class="dashboard-turn">Awaiting scenario</div></div>', unsafe_allow_html=True)
        return
    status_color, status_label = _status_tone(render_data)
    st.markdown(f'<div class="dashboard-header"><div class="dashboard-title">ResilienceSim - {state.scenario_name}</div><div class="dashboard-turn"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{status_color};margin-right:8px;vertical-align:middle;"></span>Turn {state.turn} / {state.max_turns} - {status_label}</div></div>', unsafe_allow_html=True)


def draw_simulation() -> None:
    state = st.session_state.state
    render_data = st.session_state.render_data
    _draw_header(state, render_data)
    col_left, col_main, col_right = st.columns([1.2, 2.8, 2.0])

    with col_left:
        if st.button("Back to Setup", use_container_width=True):
            st.session_state.setup_complete = False
            st.rerun()
        selected_path = draw_scenario_selector()
        if selected_path and selected_path != st.session_state.scenario_path:
            try:
                _load_selected_scenario(selected_path)
            except (ScenarioValidationError, FileNotFoundError, ValueError) as exc:
                st.error(str(exc))
        if st.session_state.state is not None:
            controls = draw_turn_controls(st.session_state.state.is_terminal, st.session_state.state.turn, st.session_state.state.max_turns)
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
            st.caption("Load a scenario from the left panel to view the dashboard.")

    with col_right:
        if render_data is not None:
            nations_with_assets = [nation for nation in config.NATIONS if any(asset["nation"] == nation for asset in render_data.get("assets", []))]
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
                        profile = st.session_state.get("country_profiles", {}).get(label)
                        if profile is not None:
                            with st.expander("Country Profile"):
                                draw_country_profile_summary(profile)
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


def _draw_vision_merge_ui(patch: list[dict]) -> None:
    st.download_button("Download vision patch JSON", data=json.dumps(patch, indent=2), file_name="vision_patch.json", mime="application/json")
    with st.expander("Merge into Scenario"):
        if st.session_state.state is None or not st.session_state.scenario_path:
            st.warning("Load a scenario first, then merge vision assets into it.")
            if st.button("Create new scenario from vision detections", key="vision_create_scenario"):
                scenario = build_scenario_from_vision(patch, nations=config.NATIONS)
                out_path = save_scenario(scenario, config.SCENARIOS_DIR / "vision_generated.json")
                st.session_state.vision_status_message = f"Saved to {out_path}"
            if st.session_state.vision_status_message:
                st.success(st.session_state.vision_status_message)
                out_path = config.SCENARIOS_DIR / "vision_generated.json"
                if out_path.exists():
                    st.download_button("Download generated scenario JSON", data=out_path.read_text(encoding="utf-8"), file_name=out_path.name, mime="application/json")
            return

        st.info(f"Will merge {len(patch)} detected assets into '{st.session_state.state.scenario_name}'")
        preview_rows = [{"asset_type": item["asset_type"], "row": item["row"], "col": item["col"]} for item in patch]
        st.dataframe(preview_rows, use_container_width=True, hide_index=True)
        if st.button("Merge and reload scenario", key="vision_merge_reload"):
            scenario_dict, errors = load_and_validate(st.session_state.scenario_path)
            if errors:
                st.error("Current scenario failed validation before merge")
                return
            merged_scenario, merged_ids, skipped_reasons = merge_vision_assets(scenario_dict, patch)
            save_scenario(merged_scenario, st.session_state.scenario_path)
            st.session_state.pending_vision_assets = []
            st.session_state.vision_status_message = f"Scenario updated with vision assets ({len(merged_ids)} merged)"
            st.session_state._vision_merge_details = {"merged_ids": merged_ids, "skipped_reasons": skipped_reasons}
            _load_selected_scenario(st.session_state.scenario_path)
            st.rerun()

        details = st.session_state.get("_vision_merge_details")
        if details:
            with st.expander("Details"):
                st.write({"merged_ids": details.get("merged_ids", []), "skipped_reasons": details.get("skipped_reasons", [])})


def main() -> None:
    _init_session_state()
    _inject_theme_css()
    if st.session_state.narrator is None:
        st.session_state.narrator = ClaudeNarrator()
    if st.session_state.detector is None:
        from vision import YOLOv8Detector

        st.session_state.detector = YOLOv8Detector()
    if not st.session_state.country_profiles:
        st.session_state.country_profiles = {nation: load_country_profile(nation, config.DATA_DIR / "countries") for nation in config.NATIONS}

    setup_tab, sim_tab, vision_tab = st.tabs(["Country Setup", "Simulation", "Vision"])

    with setup_tab:
        profiles = draw_country_setup(nations=config.NATIONS, countries_dir=config.DATA_DIR / "countries")
        st.session_state.country_profiles = profiles

    with sim_tab:
        if not st.session_state.setup_complete:
            st.info("Complete country setup and click Start Simulation to enter the simulation view.")
        else:
            draw_simulation()

    with vision_tab:
        patch = draw_vision_panel(st.session_state.detector)
        if patch is not None and st.session_state.state is not None:
            st.info(f"{len(patch)} assets ready to merge into current scenario")
        pending_patch = patch or st.session_state.get("pending_vision_assets", [])
        if pending_patch:
            _draw_vision_merge_ui(pending_patch)
        if st.session_state.vision_status_message:
            st.success(st.session_state.vision_status_message)


if __name__ == "__main__":
    main()

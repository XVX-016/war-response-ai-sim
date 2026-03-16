from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import config


def draw_scenario_selector(scenario_dir: str = "data/scenarios") -> Optional[str]:
    import streamlit as st

    directory = Path(scenario_dir)
    files = sorted(directory.glob("*.json"))
    if not files:
        st.warning("No scenarios found.")
        return None

    name_to_path: dict[str, str] = {}
    options = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            name = data.get("name", path.stem)
        except Exception:
            name = path.stem
        options.append(name)
        name_to_path[name] = str(path)

    current_path = st.session_state.get("scenario_path")
    current_name = next((name for name, path in name_to_path.items() if path == current_path), options[0])
    selected_name = st.selectbox("Scenario", options, index=options.index(current_name) if current_name in options else 0)
    return name_to_path[selected_name]


def draw_turn_controls(state_is_terminal: bool, turn: int, max_turns: int) -> dict:
    import streamlit as st

    st.markdown(f"**Turn {turn} / {max_turns}**")
    render_data = st.session_state.get("render_data") or {}
    end_conditions = render_data.get("end_conditions", {})
    if state_is_terminal:
        if any(value == "stabilised" for value in end_conditions.values()):
            st.success("STABILISED")
        elif any(value == "collapsed" for value in end_conditions.values()):
            st.error("COLLAPSED")
        else:
            st.info("Simulation complete")

    advance = st.button("Advance Turn", disabled=state_is_terminal)
    reset = st.button("Reset Scenario")
    auto_step = st.checkbox("Auto-step", value=False)
    step_delay = st.slider("Step delay (seconds)", min_value=0.5, max_value=3.0, value=1.0, step=0.5)
    nation_filter = st.radio("Nation filter", ["All", *config.NATIONS], horizontal=False)
    return {
        "advance": advance,
        "auto_step": auto_step,
        "step_delay": float(step_delay),
        "reset": reset,
        "nation_filter": nation_filter,
    }


def draw_auto_step(controls: dict, callback) -> None:
    import streamlit as st

    if not controls.get("auto_step"):
        return
    render_data = st.session_state.get("render_data") or {}
    if render_data.get("is_terminal"):
        return
    time.sleep(float(controls.get("step_delay", 1.0)))
    callback()

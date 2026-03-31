from __future__ import annotations

from typing import List

from ui.components import card


def _event_row(event: dict) -> str:
    severity = event.get("severity", "info")
    colours = {"critical": "#EF4444", "warning": "#F59E0B", "info": "#3B82F6"}
    type_bg = {
        "action_complete": "#1E3A5F", "action_queued": "#1E3A5F",
        "action_rejected": "#3B0000", "consequence": "#3B2500",
        "exogenous": "#2D1B69", "alliance_resupply": "#14292A",
        "end_condition": "#14291A",
    }
    border_colour = colours.get(severity, "#333333")
    evt_type = event.get("event_type", "")
    tag_bg = type_bg.get(evt_type, "#1A1A1A")
    turn = event.get("turn", 0)
    desc = event.get("description", "")

    return f"""
    <div style="
        border-left: 3px solid {border_colour};
        padding: 7px 10px 7px 12px;
        margin-bottom: 3px;
        background: #0A0A0A;
        border-radius: 0 3px 3px 0;
        transition: background {150}ms ease;
    ">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:3px;">
            <span style="font-family:monospace; font-size:10px; color:#525252; min-width:36px;">T{turn:02d}</span>
            <span style="font-size:10px; font-weight:500; background:{tag_bg}; color:#A3A3A3; padding:1px 5px; border-radius:2px; text-transform:uppercase; letter-spacing:0.05em;">{evt_type.replace("_"," ")}</span>
        </div>
        <span style="font-size:12px; color:#D4D4D4; line-height:1.4;">{desc}</span>
    </div>
    """


def draw_event_log(events: List[dict], max_rows: int = 30, narrative: str = "") -> None:
    import streamlit as st

    filter_key = "event_log_filter"
    if filter_key not in st.session_state:
        st.session_state[filter_key] = "All"

    labels = ["All", "Critical", "Warnings", "Actions"]
    if hasattr(st, "pills"):
        selection = st.pills("Event filter", labels, selection_mode="single", default=st.session_state[filter_key])
        if selection:
            st.session_state[filter_key] = selection
    else:
        st.session_state[filter_key] = st.radio("Event filter", labels, horizontal=True, index=labels.index(st.session_state[filter_key]))

    current_filter = st.session_state[filter_key]
    filtered = list(events)
    if current_filter == "Critical":
        filtered = [event for event in events if event.get("severity") == "critical"]
    elif current_filter == "Warnings":
        filtered = [event for event in events if event.get("severity") == "warning"]
    elif current_filter == "Actions":
        filtered = [event for event in events if event.get("event_type") in {"action_complete", "action_queued", "action_rejected"}]

    if narrative:
        def _narrative() -> None:
            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:var(--text-secondary);margin-bottom:6px;">AI Summary</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="color:var(--text-primary);font-style:italic;">{narrative}</div>', unsafe_allow_html=True)
        card(_narrative, border_left_colour="#3B82F6")

    if not filtered:
        st.caption("No events to display.")
        return

    with st.container(height=520):
        for event in filtered[:max_rows]:
            st.markdown(_event_row(event), unsafe_allow_html=True)

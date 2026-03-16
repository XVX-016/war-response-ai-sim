from __future__ import annotations

from typing import List


def draw_event_log(events: List[dict], max_rows: int = 30, narrative: str = "") -> None:
    import streamlit as st

    filter_key = "event_log_filter"
    if filter_key not in st.session_state:
        st.session_state[filter_key] = "All"

    labels = ["All", "Critical", "Warnings", "Actions"]
    cols = st.columns(len(labels))
    for idx, label in enumerate(labels):
        if cols[idx].button(label, key=f"event_log_button_{label}"):
            st.session_state[filter_key] = label

    current_filter = st.session_state[filter_key]
    filtered = list(events)
    if current_filter == "Critical":
        filtered = [event for event in events if event.get("severity") == "critical"]
    elif current_filter == "Warnings":
        filtered = [event for event in events if event.get("severity") == "warning"]
    elif current_filter == "Actions":
        filtered = [event for event in events if event.get("event_type") in {"action_complete", "action_queued", "action_rejected"}]

    if narrative:
        st.info(f"?? Turn Summary\n\n*{narrative}*")

    if not filtered:
        st.empty()
        st.caption("No events to display.")
        return

    severity_colors = {
        "critical": "#e74c3c",
        "warning": "#f39c12",
        "info": "#94A3B8",
    }

    with st.container(height=520):
        for event in filtered[:max_rows]:
            badge = event.get("severity", "info").upper()
            badge_color = severity_colors.get(event.get("severity", "info"), "#94A3B8")
            tags = event.get("tags") or []
            suffix = f" ? {tags[0]}" if event.get("event_type") == "consequence" and tags else ""
            st.markdown(
                f"<div style='margin-bottom:0.35rem;'>"
                f"<span style='color:#475569;'>[Turn {event.get('turn', 0)}]</span> "
                f"<span style='display:inline-block;padding:0.15rem 0.45rem;border-radius:999px;background:{badge_color};color:white;font-size:0.75rem;'>{badge}</span> "
                f"<span>{event.get('description', '')}</span>"
                f"<span style='color:#64748B;font-size:0.8rem;'>{suffix}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

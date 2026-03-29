from __future__ import annotations

from typing import List


def _event_type_color(event_type: str, severity: str) -> tuple[str, str]:
    if event_type in {"action_complete", "action_queued", "action_rejected"}:
        return ("#1d4ed8", "#93c5fd")
    if event_type == "exogenous":
        return ("#a855f7", "#f3e8ff")
    if event_type == "end_condition":
        return ("#7f1d1d" if severity == "critical" else "#1e3a5f", "#fca5a5" if severity == "critical" else "#93c5fd")
    return ("#78350f", "#fcd34d")


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
        st.markdown(
            f"""
            <div class="kpi-card" style="border-left:3px solid #3b82f6;">
              <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:#94a3b8;margin-bottom:6px;">AI Summary</div>
              <div style="color:#f1f5f9;font-style:italic;">{narrative}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not filtered:
        st.caption("No events to display.")
        return

    severity_colors = {
        "critical": "#ef4444",
        "warning": "#f59e0b",
        "info": "#3b82f6",
    }

    with st.container(height=520):
        for event in filtered[:max_rows]:
            severity = event.get("severity", "info")
            border_color = severity_colors.get(severity, "#3b82f6")
            event_type = event.get("event_type", "event")
            tag_bg, tag_fg = _event_type_color(event_type, severity)
            st.markdown(
                f"""
                <div class="event-row" style="border-left:3px solid {border_color};">
                  <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:4px;">
                    <span style="padding:2px 8px;border-radius:3px;background:#334155;color:#f1f5f9;font-size:11px;font-family:monospace;">T{event.get('turn', 0)}</span>
                    <span style="padding:2px 8px;border-radius:3px;background:{tag_bg};color:{tag_fg};font-size:11px;font-weight:500;letter-spacing:0.03em;">{event_type.replace('_', ' ')}</span>
                  </div>
                  <div style="color:#f1f5f9;font-size:13px;line-height:1.45;">{event.get('description', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

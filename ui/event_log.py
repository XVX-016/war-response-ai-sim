from __future__ import annotations

from typing import List


def _event_type_color(event_type: str, severity: str) -> tuple[str, str]:
    if event_type in {"action_complete", "action_queued", "action_rejected"}:
        return ("#1d4ed8", "#dbeafe")
    if event_type == "exogenous":
        return ("#6b21a8", "#f3e8ff")
    if event_type == "end_condition":
        return ("#166534" if severity != "critical" else "#7f1d1d", "#dcfce7" if severity != "critical" else "#fecaca")
    return ("#78350f", "#fde68a")


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
            <div style="margin:0.55rem 0 0.9rem 0;">
              <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.12em;color:#93c5fd;margin-bottom:0.35rem;">AI Summary</div>
              <div style="border-left:3px solid #3b82f6;background:rgba(30,41,59,0.85);padding:0.8rem 0.9rem;border-radius:10px;color:#dbeafe;font-style:italic;">
                {narrative}
              </div>
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
        "info": "#64748b",
    }

    with st.container(height=520):
        for event in filtered[:max_rows]:
            severity = event.get("severity", "info")
            border_color = severity_colors.get(severity, "#64748b")
            event_type = event.get("event_type", "event")
            tag_bg, tag_fg = _event_type_color(event_type, severity)
            st.markdown(
                f"""
                <div style="margin-bottom:0.6rem;padding:0.7rem 0.8rem;border-left:3px solid {border_color};border-radius:8px;background:rgba(15,23,42,0.5);border-top:1px solid rgba(148,163,184,0.1);border-right:1px solid rgba(148,163,184,0.1);border-bottom:1px solid rgba(148,163,184,0.1);">
                  <div style="display:flex;flex-wrap:wrap;gap:0.45rem;align-items:center;margin-bottom:0.35rem;">
                    <span style="padding:0.15rem 0.45rem;border-radius:999px;background:#334155;color:#e2e8f0;font-size:10px;">T{event.get('turn', 0)}</span>
                    <span style="padding:0.15rem 0.45rem;border-radius:999px;background:{tag_bg};color:{tag_fg};font-size:10px;text-transform:uppercase;letter-spacing:0.06em;">{event_type.replace('_', ' ')}</span>
                  </div>
                  <div style="color:#e2e8f0;font-size:13px;line-height:1.45;">{event.get('description', '')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

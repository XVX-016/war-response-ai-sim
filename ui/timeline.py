from __future__ import annotations

from typing import List

import config


def draw_timeline(history: List[dict]) -> None:
    import streamlit as st

    if len(history) < 2:
        return

    st.markdown('<div class="section-label">Service Coverage Timeline</div>', unsafe_allow_html=True)

    try:
        import plotly.graph_objects as go
    except ImportError:
        st.info("Install `plotly` to enable the service coverage timeline chart.")
        return

    turns = [snapshot.get("turn", idx) for idx, snapshot in enumerate(history)]
    auria = [100 * snapshot.get("kpis", {}).get(config.NATION_A, {}).get("service_coverage_score", 0.0) for snapshot in history]
    boros = [100 * snapshot.get("kpis", {}).get(config.NATION_B, {}).get("service_coverage_score", 0.0) for snapshot in history]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=turns,
            y=auria,
            mode="lines+markers",
            name=config.NATION_A,
            line={"color": "#3b82f6", "width": 3},
            marker={"size": 6},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=turns,
            y=boros,
            mode="lines+markers",
            name=config.NATION_B,
            line={"color": "#f59e0b", "width": 3},
            marker={"size": 6},
        )
    )
    for threshold, color in ((50, "#ef4444"), (70, "#22c55e")):
        fig.add_hline(y=threshold, line_dash="dash", line_color=color, opacity=0.55)

    fig.update_layout(
        height=180,
        margin={"l": 18, "r": 18, "t": 10, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.42)",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0, "title": {"text": ""}},
        xaxis={"title": "", "showgrid": False, "color": "#cbd5e1"},
        yaxis={"title": "", "range": [0, 100], "gridcolor": "rgba(148,163,184,0.14)", "color": "#cbd5e1"},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

from __future__ import annotations

from typing import List

import config


def draw_timeline(history: List[dict]) -> None:
    import streamlit as st

    if len(history) < 2:
        return

    st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:var(--text-secondary);margin-bottom:8px;">Service Coverage Timeline</div>', unsafe_allow_html=True)

    try:
        import plotly.graph_objects as go
    except ImportError:
        st.info("Install `plotly` to enable the service coverage timeline chart.")
        return

    turns = [snapshot.get("turn", idx) for idx, snapshot in enumerate(history)]
    auria = [100 * snapshot.get("kpis", {}).get(config.NATION_A, {}).get("service_coverage_score", 0.0) for snapshot in history]
    boros = [100 * snapshot.get("kpis", {}).get(config.NATION_B, {}).get("service_coverage_score", 0.0) for snapshot in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=turns, y=auria, mode="lines+markers", name=config.NATION_A, line={"color": "#3B82F6", "width": 3}, marker={"size": 6}))
    fig.add_trace(go.Scatter(x=turns, y=boros, mode="lines+markers", name=config.NATION_B, line={"color": "#F59E0B", "width": 3}, marker={"size": 6}))
    for threshold, color in ((50, "#EF4444"), (70, "#22C55E")):
        fig.add_hline(y=threshold, line_dash="dash", line_color=color, opacity=0.55)

    fig.update_layout(
        height=180,
        margin={"l": 18, "r": 18, "t": 10, "b": 20},
        paper_bgcolor="#0A0A0A",
        plot_bgcolor="#212020",
        font={"color": "#F5F5F5", "family": "Inter, system-ui, sans-serif"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0, "title": {"text": ""}, "bgcolor": "rgba(33,32,32,0.8)", "bordercolor": "#333333", "borderwidth": 1, "font": {"color": "#F5F5F5"}},
        xaxis={"title": "", "showgrid": False, "linecolor": "#333333", "tickfont": {"color": "#A3A3A3"}},
        yaxis={"title": "", "range": [0, 100], "gridcolor": "#333333", "linecolor": "#333333", "tickfont": {"color": "#A3A3A3"}},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

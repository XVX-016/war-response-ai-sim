from __future__ import annotations

import config


def _delta(prev_render: dict | None, nation: str, key: str) -> float | None:
    if not prev_render:
        return None
    prev = prev_render.get("kpis", {}).get(nation, {})
    if key not in prev:
        return None
    return prev.get(key)


def _coverage_color(value: float) -> str:
    if value > 0.7:
        return "#22c55e"
    if value >= 0.4:
        return "#f59e0b"
    return "#ef4444"


def _resource_color(value: float) -> str:
    if value > 0.5:
        return "#22c55e"
    if value >= 0.2:
        return "#f59e0b"
    return "#ef4444"


def draw_nation_kpis(render_data: dict, nation: str) -> None:
    import streamlit as st

    prev_render = st.session_state.get("prev_render")
    kpis = render_data["kpis"][nation]

    prev_service = _delta(prev_render, nation, "service_coverage_score")
    prev_displaced = _delta(prev_render, nation, "total_displaced")
    prev_stable = _delta(prev_render, nation, "stable_turns")

    delta_service = None if prev_service is None else f"{(kpis['service_coverage_score'] - prev_service):+.1%}"
    delta_displaced = None if prev_displaced is None else f"{int(kpis['total_displaced'] - prev_displaced):+d}"
    delta_stable = None if prev_stable is None else f"{int(kpis['stable_turns'] - prev_stable):+d}"
    coverage_color = _coverage_color(float(kpis["service_coverage_score"]))

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-label">{nation} Overview</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:0.85rem;">
          <div>
            <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.12em;color:#94a3b8;">Service coverage</div>
            <div style="display:flex;align-items:center;gap:0.75rem;margin-top:0.4rem;">
              <span style="display:inline-flex;align-items:center;justify-content:center;width:88px;height:88px;border-radius:999px;border:5px solid {coverage_color};color:{coverage_color};font-size:1.55rem;font-weight:700;background:rgba(15,23,42,0.45);">
                {kpis['service_coverage_score']:.0%}
              </span>
              <div style="color:#94a3b8;font-size:12px;">
                Delta<br /><span style="color:#e2e8f0;font-size:14px;">{delta_service or 'n/a'}</span>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(2)
    with metric_cols[0]:
        st.metric("Displaced persons", f"{kpis['total_displaced']:,}", delta_displaced, delta_color="inverse")
    with metric_cols[1]:
        st.metric("Stable turns", str(kpis["stable_turns"]), delta_stable)

    end_condition = kpis.get("end_condition")
    if end_condition == "stabilised":
        st.success("STABILISED")
    elif end_condition == "collapsed":
        st.error("COLLAPSED")
    elif end_condition == "timeout":
        st.info("TIMEOUT")
    st.markdown("</div>", unsafe_allow_html=True)


def draw_resource_bars(render_data: dict, nation: str) -> None:
    import streamlit as st

    prev_render = st.session_state.get("prev_render")
    current_resources = render_data["resources"][nation]
    previous_resources = prev_render.get("resources", {}).get(nation, {}) if prev_render else {}

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Resource Stocks</div>', unsafe_allow_html=True)
    for resource_type, spec in config.RESOURCE_TYPES.items():
        resource = current_resources[resource_type]
        previous = previous_resources.get(resource_type)
        delta_amount = 0.0 if previous is None else resource["amount"] - previous.get("amount", resource["amount"])
        bar_color = _resource_color(float(resource["fraction"]))
        st.markdown(
            f"""
            <div style="margin-bottom:0.8rem;">
              <div style="display:flex;justify-content:space-between;gap:1rem;font-size:12px;color:#cbd5e1;margin-bottom:0.3rem;">
                <span>{resource_type.replace('_', ' ').title()}</span>
                <span>{resource['amount']:.0f} {resource['unit']} ({delta_amount:+.0f})</span>
              </div>
              <div style="height:9px;background:rgba(15,23,42,0.72);border-radius:999px;overflow:hidden;border:1px solid rgba(148,163,184,0.14);">
                <div style="width:{resource['fraction'] * 100:.1f}%;height:100%;background:{bar_color};"></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def draw_consequence_badges(render_data: dict, nation: str) -> None:
    import streamlit as st

    tags = render_data.get("active_consequences", {}).get(nation, [])
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Active Consequences</div>', unsafe_allow_html=True)

    if not tags:
        st.markdown(
            "<div style='color:#86efac;font-size:13px;'>All systems nominal</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    pills = []
    for tag in tags:
        lower = tag.lower()
        if "risk" in lower or "mortality" in lower:
            color = "#7f1d1d"
            text = "#fecaca"
        elif "degraded" in lower or "impaired" in lower or "shortage" in lower:
            color = "#78350f"
            text = "#fde68a"
        else:
            color = "#1e3a5f"
            text = "#bfdbfe"
        pills.append(
            f"<span style='display:inline-flex;align-items:center;padding:0.3rem 0.6rem;border-radius:999px;"
            f"background:{color};color:{text};font-size:10px;letter-spacing:0.05em;text-transform:uppercase;'>{tag.replace('_', ' ')}</span>"
        )
    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;gap:0.45rem;'>{''.join(pills)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def draw_asset_detail(asset_dict: dict) -> None:
    import streamlit as st

    status = asset_dict["status"]
    color = config.MAP_COLORMAP[status]
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.subheader(asset_dict["name"])
    st.caption(f"{asset_dict['asset_type'].replace('_', ' ').title()} - {asset_dict['nation']}")
    st.markdown(
        f"""
        <div style="height:10px;background:rgba(15,23,42,0.72);border-radius:999px;overflow:hidden;border:1px solid rgba(148,163,184,0.14);margin:0.5rem 0;">
          <div style="width:{asset_dict['health_fraction'] * 100:.1f}%;height:100%;background:{color};"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Health: {asset_dict['health']:.0f}/{asset_dict['max_health']:.0f}")
    st.markdown(
        f"<span style='display:inline-block;padding:0.25rem 0.6rem;border-radius:999px;background:{color};color:white;font-size:0.85rem;'>{status.upper()}</span>",
        unsafe_allow_html=True,
    )
    st.checkbox("Critical asset", value=bool(asset_dict["is_critical"]), disabled=True)
    st.checkbox("Reinforced", value=bool(asset_dict["is_reinforced"]), disabled=True)
    if asset_dict["is_reinforced"]:
        st.info("Reinforced protection is active.")
    st.markdown("</div>", unsafe_allow_html=True)

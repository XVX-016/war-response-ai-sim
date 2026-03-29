from __future__ import annotations

import config
from engine.country import CountryProfile


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
    if value > 0.6:
        return "#22c55e"
    if value >= 0.3:
        return "#f59e0b"
    return "#ef4444"


def _mini_bar_row(label: str, value: float, pill: str) -> str:
    color = "#22c55e" if value > 0.66 else "#f59e0b" if value > 0.33 else "#ef4444"
    return f"""
    <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px;">
      <div style="width:110px;font-size:12px;color:#94a3b8;">{label}</div>
      <div style="flex:1;height:6px;background:#334155;border-radius:3px;overflow:hidden;">
        <div style="width:{max(0.0, min(1.0, value)) * 100:.1f}%;height:100%;background:{color};"></div>
      </div>
      <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;white-space:nowrap;">{pill}</div>
    </div>
    """


def draw_country_profile_summary(profile: CountryProfile) -> None:
    import streamlit as st

    population_norm = min(profile.population_millions / 20.0, 1.0)
    terrain_ease = 1.0 - profile.terrain_difficulty
    rows = [
        _mini_bar_row("GDP", profile.gdp_index, profile.gdp_label()),
        _mini_bar_row("Military", profile.military_strength, profile.military_label()),
        _mini_bar_row("Population", population_norm, f"{profile.population_millions:.1f}M"),
        _mini_bar_row("Resources", profile.resource_richness, "Rich" if profile.resource_richness >= 0.65 else "Moderate" if profile.resource_richness >= 0.35 else "Scarce"),
        _mini_bar_row("Terrain", terrain_ease, profile.terrain_label()),
        _mini_bar_row("Alliance", profile.alliance_strength, profile.alliance_label()),
    ]

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown(f"#### {profile.flag_emoji} {profile.display_name}")
    if profile.lore:
        st.caption(profile.lore)
    st.markdown(''.join(rows), unsafe_allow_html=True)
    st.divider()
    st.markdown('</div>', unsafe_allow_html=True)


def draw_nation_kpis(render_data: dict, nation: str) -> None:
    import streamlit as st

    prev_render = st.session_state.get("prev_render")
    kpis = render_data["kpis"][nation]

    prev_service = _delta(prev_render, nation, "service_coverage_score")
    delta_service = None if prev_service is None else f"{(kpis['service_coverage_score'] - prev_service):+.1%}"
    coverage_color = _coverage_color(float(kpis["service_coverage_score"]))

    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#94a3b8;margin-bottom:8px;">{nation} Overview</div>
        <div style="margin-bottom:12px;">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#94a3b8;margin-bottom:4px;">Service Coverage</div>
          <div style="font-family:monospace;font-size:36px;color:{coverage_color};line-height:1;">{kpis['service_coverage_score']:.0%}</div>
          <div style="font-family:monospace;font-size:13px;color:#94a3b8;margin-top:4px;">{delta_service or 'n/a'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    prev_displaced = _delta(prev_render, nation, "total_displaced")
    prev_stable = _delta(prev_render, nation, "stable_turns")
    delta_displaced = None if prev_displaced is None else f"{int(kpis['total_displaced'] - prev_displaced):+d}"
    delta_stable = None if prev_stable is None else f"{int(kpis['stable_turns'] - prev_stable):+d}"

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
    st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#94a3b8;margin-bottom:8px;">Resource Stocks</div>', unsafe_allow_html=True)
    for resource_type, spec in config.RESOURCE_TYPES.items():
        resource = current_resources[resource_type]
        previous = previous_resources.get(resource_type)
        delta_amount = 0.0 if previous is None else resource["amount"] - previous.get("amount", resource["amount"])
        bar_color = _resource_color(float(resource["fraction"]))
        st.markdown(
            f"""
            <div style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;gap:12px;font-size:12px;color:#f1f5f9;margin-bottom:4px;">
                <span>{resource_type.replace('_', ' ').title()}</span>
                <span style="font-family:monospace;">{resource['amount']:.0f} {resource['unit']} ({delta_amount:+.0f})</span>
              </div>
              <div style="height:9px;background:#334155;border-radius:4px;overflow:hidden;">
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
    st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#94a3b8;margin-bottom:8px;">Active Consequences</div>', unsafe_allow_html=True)

    if not tags:
        st.markdown(
            "<div style='color:#94a3b8;font-size:13px;'>All systems nominal</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    badges = []
    for tag in tags:
        lower = tag.lower()
        if "risk" in lower or "mortality" in lower:
            color = "#7f1d1d"
            text = "#fca5a5"
        elif "degraded" in lower or "impaired" in lower or "shortage" in lower:
            color = "#78350f"
            text = "#fcd34d"
        else:
            color = "#1e3a5f"
            text = "#93c5fd"
        badges.append(
            f"<span style='display:inline-block;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:500;letter-spacing:0.03em;background:{color};color:{text};margin:0 6px 6px 0;'>{tag.replace('_', ' ')}</span>"
        )
    st.markdown("".join(badges), unsafe_allow_html=True)
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
        <div style="height:10px;background:#334155;border-radius:4px;overflow:hidden;margin:8px 0;">
          <div style="width:{asset_dict['health_fraction'] * 100:.1f}%;height:100%;background:{color};"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Health: {asset_dict['health']:.0f}/{asset_dict['max_health']:.0f}")
    st.markdown(
        f"<span style='display:inline-block;padding:2px 8px;border-radius:3px;background:{color};color:#f1f5f9;font-size:11px;font-weight:500;letter-spacing:0.03em;'>{status.upper()}</span>",
        unsafe_allow_html=True,
    )
    st.checkbox("Critical asset", value=bool(asset_dict["is_critical"]), disabled=True)
    st.checkbox("Reinforced", value=bool(asset_dict["is_reinforced"]), disabled=True)
    if asset_dict["is_reinforced"]:
        st.info("Reinforced protection is active.")
    st.markdown("</div>", unsafe_allow_html=True)

from __future__ import annotations

import config
from engine.country import CountryProfile
from ui.components import card


def _delta(prev_render: dict | None, nation: str, key: str) -> float | None:
    if not prev_render:
        return None
    prev = prev_render.get("kpis", {}).get(nation, {})
    if key not in prev:
        return None
    return prev.get(key)


def _coverage_color(value: float) -> str:
    if value > 0.7:
        return "var(--green)"
    if value >= 0.4:
        return "var(--amber)"
    return "var(--red)"


def _mini_bar_row(label: str, value: float, pill: str) -> str:
    color = "var(--green)" if value > 0.66 else "var(--amber)" if value > 0.33 else "var(--red)"
    return f"""
    <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px;">
      <div style="width:110px;font-size:12px;color:var(--text-secondary);">{label}</div>
      <div style="flex:1;height:6px;background:var(--bg-input);border-radius:3px;overflow:hidden;">
        <div style="width:{max(0.0, min(1.0, value)) * 100:.1f}%;height:100%;background:{color};"></div>
      </div>
      <div style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;white-space:nowrap;">{pill}</div>
    </div>
    """


def _resource_bar(label: str, value: float, unit: str, amount: float, delta: float) -> str:
    if value > 0.6:
        colour = "#22C55E"
    elif value > 0.3:
        colour = "#F59E0B"
    else:
        colour = "#EF4444"

    delta_str = ""
    if delta != 0:
        sign = "+" if delta > 0 else ""
        dcolor = "#22C55E" if delta > 0 else "#EF4444"
        delta_str = f'<span style="font-size:11px; color:{dcolor}; font-family:monospace;">{sign}{delta:.0f}</span>'

    pct = max(0, min(100, int(value * 100)))
    return f"""
    <div style="margin-bottom:10px;">
      <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px;">
        <span style="font-size:12px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">{label}</span>
        <span style="font-family:monospace; font-size:13px; color:var(--text-primary);">
          {amount:.0f}
          <span style="color:var(--text-muted); font-size:11px;">{unit}</span>
          &nbsp;{delta_str}
        </span>
      </div>
      <div style="background:var(--bg-input); border-radius:2px; height:4px; overflow:hidden;">
        <div style="width:{pct}%; height:100%; background:{colour}; border-radius:2px; transition:width 300ms ease;"></div>
      </div>
    </div>
    """


def _consequence_badge(tag: str) -> str:
    """Returns an HTML badge string for one consequence tag."""
    tag_lower = tag.lower()
    if any(w in tag_lower for w in ("risk", "mortality", "collapse")):
        bg, fg = "#3B0000", "#FCA5A5"
    elif any(w in tag_lower for w in ("degraded", "impaired", "reduced")):
        bg, fg = "#3B2500", "#FCD34D"
    elif any(w in tag_lower for w in ("disrupted", "blocked", "shortage")):
        bg, fg = "#1C1A3B", "#C4B5FD"
    else:
        bg, fg = "#1A1A1A", "#A3A3A3"

    return (
        f'<span style="display:inline-block; margin:2px 3px 2px 0; padding:2px 7px; background:{bg}; color:{fg}; border-radius:3px; font-size:10px; font-weight:500; letter-spacing:0.04em; text-transform:uppercase;">{tag.replace("_", " ")}</span>'
    )


def draw_country_profile_summary(profile: CountryProfile) -> None:
    import streamlit as st

    def _content() -> None:
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
        st.markdown(f"### {profile.display_name}")
        if profile.lore:
            st.caption(profile.lore)
        st.markdown("".join(rows), unsafe_allow_html=True)
        st.divider()

    card(_content)


def draw_nation_kpis(render_data: dict, nation: str) -> None:
    import streamlit as st

    prev_render = st.session_state.get("prev_render")
    kpis = render_data["kpis"][nation]
    prev_service = _delta(prev_render, nation, "service_coverage_score")
    delta_service = None if prev_service is None else f"{(kpis['service_coverage_score'] - prev_service):+.1%}"
    coverage_color = _coverage_color(float(kpis["service_coverage_score"]))
    prev_displaced = _delta(prev_render, nation, "total_displaced")
    prev_stable = _delta(prev_render, nation, "stable_turns")
    delta_displaced = None if prev_displaced is None else f"{int(kpis['total_displaced'] - prev_displaced):+d}"
    delta_stable = None if prev_stable is None else f"{int(kpis['stable_turns'] - prev_stable):+d}"

    def _content() -> None:
        st.markdown(f"""
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:var(--text-secondary);margin-bottom:8px;">{nation} Overview</div>
        <div style="margin-bottom:12px;">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:var(--text-secondary);margin-bottom:4px;">Service Coverage</div>
          <div style="font-family:ui-monospace, monospace;font-size:36px;color:{coverage_color};line-height:1;">{kpis['service_coverage_score']:.0%}</div>
          <div style="font-family:ui-monospace, monospace;font-size:13px;color:var(--text-secondary);margin-top:4px;">{delta_service or 'n/a'}</div>
        </div>
        """, unsafe_allow_html=True)
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

    card(_content, border_left_colour="#3B82F6")


def draw_resource_bars(render_data: dict, nation: str) -> None:
    import streamlit as st

    prev_render = st.session_state.get("prev_render")
    current_resources = render_data["resources"][nation]
    previous_resources = prev_render.get("resources", {}).get(nation, {}) if prev_render else {}

    def _content() -> None:
        st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:var(--text-secondary);margin-bottom:8px;">Resource Stocks</div>', unsafe_allow_html=True)
        for resource_type, spec in config.RESOURCE_TYPES.items():
            resource = current_resources[resource_type]
            previous = previous_resources.get(resource_type)
            delta_amount = 0.0 if previous is None else resource["amount"] - previous.get("amount", resource["amount"])
            st.markdown(_resource_bar(resource_type.replace("_", " ").title(), float(resource["fraction"]), resource["unit"], float(resource["amount"]), float(delta_amount)), unsafe_allow_html=True)

    card(_content)


def draw_consequence_badges(render_data: dict, nation: str) -> None:
    import streamlit as st

    tags = render_data.get("active_consequences", {}).get(nation, [])

    def _content() -> None:
        st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:var(--text-secondary);margin-bottom:8px;">Active Consequences</div>', unsafe_allow_html=True)
        if not tags:
            st.markdown("<div style='color:var(--text-secondary);font-size:13px;'>All systems nominal</div>", unsafe_allow_html=True)
            return
        st.markdown("".join(_consequence_badge(tag) for tag in tags), unsafe_allow_html=True)

    card(_content)


def draw_asset_detail(asset_dict: dict) -> None:
    import streamlit as st

    status = asset_dict["status"]
    color = config.MAP_COLORMAP[status]

    def _content() -> None:
        st.subheader(asset_dict["name"])
        st.caption(f"{asset_dict['asset_type'].replace('_', ' ').title()} - {asset_dict['nation']}")
        st.markdown(f"""
        <div style="height:10px;background:var(--bg-input);border-radius:2px;overflow:hidden;margin:8px 0;">
          <div style="width:{asset_dict['health_fraction'] * 100:.1f}%;height:100%;background:{color};"></div>
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"Health: {asset_dict['health']:.0f}/{asset_dict['max_health']:.0f}")
        st.markdown(f"<span style='display:inline-block;padding:2px 7px;border-radius:3px;background:{color};color:var(--text-primary);font-size:10px;font-weight:500;letter-spacing:0.04em;text-transform:uppercase;'>{status}</span>", unsafe_allow_html=True)
        st.checkbox("Critical asset", value=bool(asset_dict["is_critical"]), disabled=True)
        st.checkbox("Reinforced", value=bool(asset_dict["is_reinforced"]), disabled=True)
        if asset_dict["is_reinforced"]:
            st.info("Reinforced protection is active.")

    card(_content)

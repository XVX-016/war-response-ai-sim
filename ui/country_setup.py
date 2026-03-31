from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import streamlit as st

from engine.country import CountryProfile, load_country_profile


def _profile_key(nation: str, factor: str) -> str:
    return f"{nation}_{factor}"


def _load_default_profiles(nations: List[str], countries_dir: Path | None) -> Dict[str, CountryProfile]:
    defaults = st.session_state.setdefault("country_profile_defaults", {})
    for nation in nations:
        if nation not in defaults:
            defaults[nation] = load_country_profile(nation, countries_dir)
    return defaults


def _ensure_slider_defaults(profile: CountryProfile) -> None:
    values = {
        "gdp_index": profile.gdp_index,
        "military_strength": profile.military_strength,
        "population_millions": profile.population_millions,
        "resource_richness": profile.resource_richness,
        "terrain_difficulty": profile.terrain_difficulty,
        "alliance_strength": profile.alliance_strength,
    }
    for factor, value in values.items():
        st.session_state.setdefault(_profile_key(profile.nation, factor), value)


def _profile_from_session(default_profile: CountryProfile) -> CountryProfile:
    return CountryProfile(
        nation=default_profile.nation,
        display_name=default_profile.display_name,
        flag_emoji=default_profile.flag_emoji,
        lore=default_profile.lore,
        gdp_index=float(st.session_state[_profile_key(default_profile.nation, "gdp_index")]),
        military_strength=float(st.session_state[_profile_key(default_profile.nation, "military_strength")]),
        population_millions=float(st.session_state[_profile_key(default_profile.nation, "population_millions")]),
        resource_richness=float(st.session_state[_profile_key(default_profile.nation, "resource_richness")]),
        terrain_difficulty=float(st.session_state[_profile_key(default_profile.nation, "terrain_difficulty")]),
        alliance_strength=float(st.session_state[_profile_key(default_profile.nation, "alliance_strength")]),
    )


def _factor_label(profile: CountryProfile, factor: str) -> str:
    if factor == "GDP":
        return profile.gdp_label()
    if factor == "Military":
        return profile.military_label()
    if factor == "Resources":
        return "Rich" if profile.resource_richness >= 0.65 else "Moderate" if profile.resource_richness >= 0.35 else "Scarce"
    if factor == "Population":
        return f"{profile.population_millions:.1f}M"
    if factor == "Alliance":
        return profile.alliance_label()
    if factor == "Terrain Ease":
        return profile.terrain_label()
    return ""


def _save_profile(profile: CountryProfile, countries_dir: Path | None) -> Path:
    target_dir = Path(countries_dir) if countries_dir is not None else Path("data/countries")
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{profile.nation.lower()}.json"
    payload = {
        "nation": profile.nation,
        "display_name": profile.display_name,
        "flag_emoji": profile.flag_emoji,
        "lore": profile.lore,
        "gdp_index": profile.gdp_index,
        "military_strength": profile.military_strength,
        "population_millions": profile.population_millions,
        "resource_richness": profile.resource_richness,
        "terrain_difficulty": profile.terrain_difficulty,
        "alliance_strength": profile.alliance_strength,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def draw_radar_chart(profiles: Dict[str, CountryProfile]) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.info("Install `plotly` to enable the country comparison radar chart.")
        return

    axes = ["GDP", "Military", "Resources", "Population*", "Alliance", "Terrain Ease"]
    colors = {
        "Auria": ("#3B82F6", "rgba(59,130,246,0.15)"),
        "Boros": ("#F59E0B", "rgba(245,158,11,0.15)"),
    }

    fig = go.Figure()
    for nation, profile in profiles.items():
        line_color, fill_color = colors.get(nation, ("#3B82F6", "rgba(59,130,246,0.15)"))
        values = [
            profile.gdp_index,
            profile.military_strength,
            profile.resource_richness,
            min(profile.population_millions / 20.0, 1.0),
            profile.alliance_strength,
            1.0 - profile.terrain_difficulty,
        ]
        fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=axes + [axes[0]], fill="toself", name=profile.display_name, line={"color": line_color, "width": 2}, fillcolor=fill_color))

    fig.update_layout(
        height=380,
        margin={"l": 60, "r": 60, "t": 40, "b": 40},
        paper_bgcolor="#0A0A0A",
        plot_bgcolor="#212020",
        font={"color": "#F5F5F5", "family": "Inter, system-ui, sans-serif"},
        legend={"bgcolor": "rgba(33,32,32,0.8)", "bordercolor": "#333333", "borderwidth": 1, "font": {"color": "#F5F5F5"}},
        polar={
            "bgcolor": "#212020",
            "radialaxis": {"range": [0, 1], "gridcolor": "#333333", "linecolor": "#333333", "tickfont": {"color": "#525252"}, "tickvals": [0.25, 0.5, 0.75, 1.0]},
            "angularaxis": {"gridcolor": "#333333", "linecolor": "#333333", "tickfont": {"color": "#F5F5F5", "size": 12}},
        },
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def draw_country_setup(nations: List[str], countries_dir: Path = None) -> Dict[str, CountryProfile]:
    st.markdown("## Country Configuration")
    st.caption("Configure each nation's profile before starting the simulation. These parameters scale starting resources, agent capability, and simulation dynamics.")

    defaults = _load_default_profiles(nations, countries_dir)
    for profile in defaults.values():
        _ensure_slider_defaults(profile)

    columns = st.columns(len(nations)) if nations else []
    profiles: Dict[str, CountryProfile] = {}

    for column, nation in zip(columns, nations):
        default_profile = defaults[nation]
        with column:
            badge_bg = "var(--accent)" if nation == "Auria" else "#92400e"
            badge_text = "A" if nation == "Auria" else "B"
            st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                  <span style="display:inline-block;padding:2px 8px;border-radius:4px;background:{badge_bg};color:var(--text-primary);font-size:12px;font-weight:600;">{badge_text}</span>
                  <span style="font-size:1.5rem;font-weight:600;color:var(--text-primary);">{default_profile.display_name}</span>
                </div>
                """, unsafe_allow_html=True)
            if default_profile.lore:
                st.caption(default_profile.lore)
            st.divider()
            st.slider("GDP Index", min_value=0.0, max_value=1.0, step=0.05, key=_profile_key(nation, "gdp_index"), help="Economic output. Scales repair crew stocks, medical and food resupply.")
            st.slider("Military Strength", min_value=0.0, max_value=1.0, step=0.05, key=_profile_key(nation, "military_strength"), help="Logistics and engineering capacity. Unlocks extra agent actions per turn.")
            st.slider("Population (millions)", min_value=0.5, max_value=50.0, step=0.5, key=_profile_key(nation, "population_millions"), help="Total national population. Scales zone populations and displacement KPIs.")
            st.slider("Resource Richness", min_value=0.0, max_value=1.0, step=0.05, key=_profile_key(nation, "resource_richness"), help="Natural resource endowment. Scales fuel, generators and water purifier stocks.")
            st.slider("Terrain Difficulty", min_value=0.0, max_value=1.0, step=0.05, key=_profile_key(nation, "terrain_difficulty"), help="Geographic obstacle level. Reduces transport hub health and increases transport dependency penalties.")
            st.slider("Alliance Strength", min_value=0.0, max_value=1.0, step=0.05, key=_profile_key(nation, "alliance_strength"), help="External support network. Provides bonus resupply per turn and reduces surprise event probability.")
            current_profile = _profile_from_session(default_profile)
            profiles[nation] = current_profile
            st.markdown((
                    '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;margin-bottom:12px;">'
                    f'<span style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;">GDP: {current_profile.gdp_label()}</span>'
                    f'<span style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;">Military: {current_profile.military_label()}</span>'
                    f'<span style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;">Terrain: {current_profile.terrain_label()}</span>'
                    f'<span style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;">Alliance: {current_profile.alliance_label()}</span>'
                    '</div>'
                ), unsafe_allow_html=True)
            reset_col, save_col = st.columns(2)
            with reset_col:
                if st.button("Reset to defaults", key=f"reset_{nation}", use_container_width=True):
                    for factor in ("gdp_index", "military_strength", "population_millions", "resource_richness", "terrain_difficulty", "alliance_strength"):
                        st.session_state[_profile_key(nation, factor)] = getattr(default_profile, factor)
                    st.rerun()
            with save_col:
                if st.button("Save profile", key=f"save_{nation}", use_container_width=True):
                    _save_profile(current_profile, countries_dir)
                    st.session_state.setdefault("country_profile_defaults", {})[nation] = current_profile
                    st.success("Saved.")

    st.markdown("### Country Comparison")
    draw_radar_chart(profiles)

    comparison_rows = []
    if len(nations) >= 2:
        left = profiles[nations[0]]
        right = profiles[nations[1]]
        factors = [
            ("GDP", left.gdp_index, right.gdp_index),
            ("Military", left.military_strength, right.military_strength),
            ("Resources", left.resource_richness, right.resource_richness),
            ("Population", left.population_millions, right.population_millions),
            ("Alliance", left.alliance_strength, right.alliance_strength),
            ("Terrain Ease", 1.0 - left.terrain_difficulty, 1.0 - right.terrain_difficulty),
        ]
        for factor, left_value, right_value in factors:
            if abs(left_value - right_value) <= 0.05:
                advantage = "Equal"
            else:
                advantage = nations[0] if left_value > right_value else nations[1]
            comparison_rows.append({"Factor": factor, f"{nations[0]} value": round(left_value, 2), f"{nations[0]} label": _factor_label(left, factor), f"{nations[1]} value": round(right_value, 2), f"{nations[1]} label": _factor_label(right, factor), "Advantage": advantage})

    st.dataframe(comparison_rows, use_container_width=True, hide_index=True)

    if st.button("Start Simulation", type="primary", use_container_width=True):
        st.session_state.setup_complete = True
        st.session_state.country_profiles = profiles
        st.rerun()

    return profiles

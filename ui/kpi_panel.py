from __future__ import annotations

import config


def _delta(prev_render: dict | None, nation: str, key: str) -> float | None:
    if not prev_render:
        return None
    prev = prev_render.get("kpis", {}).get(nation, {})
    if key not in prev:
        return None
    return prev.get(key)


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

    st.metric("Service coverage", f"{kpis['service_coverage_score']:.0%}", delta_service)
    st.metric("Displaced persons", f"{kpis['total_displaced']:,}", delta_displaced, delta_color="inverse")
    st.metric("Stable turns", str(kpis['stable_turns']), delta_stable)

    end_condition = kpis.get("end_condition")
    if end_condition == "stabilised":
        st.success("STABILISED")
    elif end_condition == "collapsed":
        st.error("COLLAPSED")
    elif end_condition == "timeout":
        st.info("TIMEOUT")


def draw_resource_bars(render_data: dict, nation: str) -> None:
    import streamlit as st

    prev_render = st.session_state.get("prev_render")
    current_resources = render_data["resources"][nation]
    previous_resources = prev_render.get("resources", {}).get(nation, {}) if prev_render else {}

    for resource_type, spec in config.RESOURCE_TYPES.items():
        resource = current_resources[resource_type]
        previous = previous_resources.get(resource_type)
        delta_text = ""
        if previous is not None:
            delta_amount = resource["amount"] - previous.get("amount", resource["amount"])
            delta_text = f" ({delta_amount:+.0f})"
        st.caption(f"{resource_type} ({resource['unit']}): {resource['amount']:.0f}{delta_text}")
        st.progress(float(resource["fraction"]))


def draw_consequence_badges(render_data: dict, nation: str) -> None:
    import streamlit as st

    tags = render_data.get("active_consequences", {}).get(nation, [])
    if not tags:
        st.success("All systems nominal")
        return

    for tag in tags:
        lower = tag.lower()
        if "risk" in lower or "mortality" in lower:
            color = "#e74c3c"
        elif "degraded" in lower or "impaired" in lower:
            color = "#f39c12"
        else:
            color = "#64748B"
        st.markdown(
            f"<span style='display:inline-block;margin:0 6px 6px 0;padding:0.25rem 0.6rem;border-radius:999px;background:{color};color:white;font-size:0.85rem;'>{tag}</span>",
            unsafe_allow_html=True,
        )


def draw_asset_detail(asset_dict: dict) -> None:
    import streamlit as st

    status = asset_dict["status"]
    color = config.MAP_COLORMAP[status]
    st.subheader(asset_dict["name"])
    st.caption(f"{asset_dict['asset_type']} ? {asset_dict['nation']}")
    st.progress(float(asset_dict["health_fraction"]))
    st.caption(f"Health: {asset_dict['health']:.0f}/{asset_dict['max_health']:.0f}")
    st.markdown(
        f"<span style='display:inline-block;padding:0.25rem 0.6rem;border-radius:999px;background:{color};color:white;font-size:0.85rem;'>{status.upper()}</span>",
        unsafe_allow_html=True,
    )
    st.checkbox("Critical asset", value=bool(asset_dict["is_critical"]), disabled=True)
    st.checkbox("Reinforced", value=bool(asset_dict["is_reinforced"]), disabled=True)
    if asset_dict["is_reinforced"]:
        st.info("Reinforced protection is active.")

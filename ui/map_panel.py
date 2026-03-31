from __future__ import annotations

from html import escape
from typing import Optional

import config
from loguru import logger

ASSET_ABBREV = {
    "power_plant": "P",
    "water_treatment": "W",
    "hospital": "H",
    "telecom_tower": "T",
    "transport_hub": "X",
    "fuel_depot": "F",
    "shelter": "S",
    "command_center": "C",
}

TYPE_LABELS = {
    "power_plant": "Power",
    "water_treatment": "Water",
    "hospital": "Hospital",
    "telecom_tower": "Telecom",
    "transport_hub": "Transport",
    "fuel_depot": "Fuel",
    "shelter": "Shelter",
    "command_center": "Command",
}

NATION_BORDER = {config.NATION_A: "#3B82F6", config.NATION_B: "#F59E0B"}


def _tooltip_markup(asset: dict) -> str:
    hp_pct = max(0.0, min(100.0, float(asset["health_fraction"]) * 100.0))
    status_color = config.MAP_COLORMAP.get(asset["status"], "var(--text-secondary)")
    asset_type = asset["asset_type"]
    abbrev = ASSET_ABBREV.get(asset_type, "?")
    if abbrev == "?":
        logger.warning("Missing asset abbreviation for asset_type '{}'", asset_type)
    reinforced = "<div style='margin-top:6px;color:var(--text-secondary);'>Reinforced</div>" if asset["is_reinforced"] else ""
    return ("<div style='min-width:220px;'>"
        f"<div style='font-weight:700;font-size:14px;color:var(--text-primary);margin-bottom:4px;'>{escape(asset['name'])}</div>"
        f"<div style='font-size:12px;color:var(--text-secondary);margin-bottom:8px;'>{escape(abbrev)} &mdash; {escape(TYPE_LABELS.get(asset_type, asset_type.replace('_', ' ').title()))}</div>"
        "<div style='height:7px;background:var(--bg-input);border-radius:2px;overflow:hidden;'>"
        f"<div style='width:{hp_pct:.1f}%;height:100%;background:{status_color};'></div></div>"
        f"<div style='font-size:12px;color:var(--text-primary);font-family:monospace;margin-top:6px;'>HP {asset['health']:.0f}/{asset['max_health']:.0f}</div>"
        f"<div style='font-size:12px;color:var(--text-secondary);margin-top:3px;'>{escape(asset['nation'])}</div>{reinforced}</div>")


def draw_map(render_data: dict, grid_data: list, selected_nation: str = "All") -> Optional[str]:
    import streamlit as st
    import streamlit.components.v1 as components

    cell_size = 32
    gap = 2
    rows = len(grid_data)
    cols = len(grid_data[0]) if rows else 0
    width = cols * (cell_size + gap) + gap
    height = rows * (cell_size + gap) + gap
    cells = []
    occupied_assets = []
    assets_by_nation = {nation: [asset for asset in render_data.get("assets", []) if asset.get("nation") == nation] for nation in config.NATIONS}

    for row in grid_data:
        for cell in row:
            x = cell["col"] * (cell_size + gap) + gap
            y = cell["row"] * (cell_size + gap) + gap
            assets = cell.get("assets", [])
            primary = assets[0] if assets else None
            cell_fill = primary["color"] if primary else "var(--bg-raised)"
            opacity = 1.0
            if primary and selected_nation != "All" and primary["nation"] != selected_nation:
                opacity = 0.2
            if primary:
                occupied_assets.append(primary)
            label = ""
            stroke = "var(--border)"
            stroke_width = 1.25
            overlay = ""
            tooltip = escape(f"Cell {cell['row']},{cell['col']} | empty")
            if primary:
                stroke = NATION_BORDER.get(primary["nation"], "var(--border)")
                stroke_width = 2
                if primary["is_reinforced"]:
                    overlay += f"<rect x=\"{x + 3}\" y=\"{y + 3}\" width=\"{cell_size - 6}\" height=\"{cell_size - 6}\" rx=\"4\" fill=\"none\" stroke=\"var(--text-primary)\" stroke-width=\"1.2\" />"
                if primary["status"] == "destroyed":
                    overlay += f"<rect x=\"{x}\" y=\"{y}\" width=\"{cell_size}\" height=\"{cell_size}\" rx=\"4\" fill=\"var(--bg-base)\" />"
                    label = "&#10005;"
                else:
                    label = escape(ASSET_ABBREV.get(primary["asset_type"], "?"))
                    if label == "?":
                        logger.warning("Missing asset abbreviation for asset_type '{}'", primary["asset_type"])
                tooltip = escape(_tooltip_markup(primary))
            cells.append(f"""
                <g class="map-cell" opacity="{opacity}" data-tooltip="{tooltip}">
                  <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="4" fill="{cell_fill}" stroke="{stroke}" stroke-width="{stroke_width}" />
                  {overlay}
                  <text x="{x + cell_size/2}" y="{y + 21}" text-anchor="middle" font-size="15" font-family="monospace" font-weight="700" fill="var(--text-primary)">{label}</text>
                </g>
                """)

    divider_y = (rows / 2) * (cell_size + gap) + gap / 2
    overlays = []
    if not assets_by_nation.get(config.NATION_A):
        overlays.append(f"<text x=\"{width / 2}\" y=\"{height / 4}\" text-anchor=\"middle\" font-size=\"24\" font-family=\"sans-serif\" fill=\"var(--text-muted)\">No assets</text>")
    if not assets_by_nation.get(config.NATION_B):
        overlays.append(f"<text x=\"{width / 2}\" y=\"{height * 3 / 4}\" text-anchor=\"middle\" font-size=\"24\" font-family=\"sans-serif\" fill=\"var(--text-muted)\">No assets</text>")

    svg = f"""
    <div id="map-wrap" style="--bg-base:#0A0A0A;--bg-surface:#212020;--bg-raised:#2D2C2C;--bg-input:#1A1A1A;--border:#333333;--text-primary:#F5F5F5;--text-secondary:#A3A3A3;--text-muted:#525252;--green:#22C55E;--amber:#F59E0B;--red:#EF4444;position:relative;overflow:auto;background:var(--bg-surface);border:1px solid var(--border);border-radius:4px;padding:12px;">
      <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <line x1="0" y1="{divider_y}" x2="{width}" y2="{divider_y}" stroke="var(--border)" stroke-dasharray="6 6" stroke-width="1.4" />
        {''.join(cells)}
        {''.join(overlays)}
      </svg>
      <div id="map-tooltip" style="position:absolute;display:none;pointer-events:none;z-index:10;background:var(--bg-surface);border:1px solid var(--border);border-radius:4px;padding:10px 12px;"></div>
    </div>
    <script>
    const wrap = document.getElementById("map-wrap");
    const tip = document.getElementById("map-tooltip");
    const cells = wrap.querySelectorAll(".map-cell");
    cells.forEach((cell) => {{
      cell.addEventListener("mouseenter", () => {{ tip.innerHTML = cell.dataset.tooltip || ""; tip.style.display = "block"; }});
      cell.addEventListener("mousemove", (event) => {{
        const bounds = wrap.getBoundingClientRect();
        tip.style.left = `${{event.clientX - bounds.left + 16}}px`;
        tip.style.top = `${{event.clientY - bounds.top + 16}}px`;
      }});
      cell.addEventListener("mouseleave", () => {{ tip.style.display = "none"; }});
    }});
    </script>
    """
    components.html(svg, height=min(max(height + 34, 260), 760), scrolling=True)

    st.markdown("""
        <div style="margin-top:12px;background:var(--bg-surface);border:1px solid var(--border);border-radius:4px;padding:12px;">
          <div style="display:flex;flex-wrap:wrap;gap:12px 16px;align-items:center;margin-bottom:8px;">
            <span style="display:flex;align-items:center;gap:6px;"><span style="width:12px;height:12px;background:var(--green);display:inline-block;"></span>Healthy</span>
            <span style="display:flex;align-items:center;gap:6px;"><span style="width:12px;height:12px;background:var(--amber);display:inline-block;"></span>Degraded</span>
            <span style="display:flex;align-items:center;gap:6px;"><span style="width:12px;height:12px;background:var(--red);display:inline-block;"></span>Critical</span>
            <span style="display:flex;align-items:center;gap:6px;"><span style="width:12px;height:12px;background:var(--text-muted);display:inline-block;"></span>Destroyed</span>
          </div>
          <div style="font-size:12px;color:var(--text-secondary);">P=Power W=Water H=Hospital T=Telecom X=Transport F=Fuel S=Shelter C=Command</div>
        </div>
        """, unsafe_allow_html=True)

    options = ["None"] + [f"{asset['id']} - {asset['name']}" for asset in occupied_assets]
    current = st.session_state.get("selected_asset")
    current_label = next((option for option in options if option.startswith(f"{current} - ")), "None") if current else "None"
    selected_label = st.selectbox("Inspect asset", options, index=options.index(current_label) if current_label in options else 0, key="map_asset_selector")
    selected_asset = None if selected_label == "None" else selected_label.split(" - ", 1)[0]
    st.session_state.selected_asset = selected_asset
    return selected_asset

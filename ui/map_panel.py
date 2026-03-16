from __future__ import annotations

from html import escape
from typing import Optional


ASSET_ABBREVIATIONS = {
    "power_plant": "P",
    "water_treatment": "W",
    "hospital": "H",
    "telecom_tower": "T",
    "transport_hub": "X",
    "fuel_depot": "F",
    "shelter": "S",
    "command_center": "C",
}


def draw_map(render_data: dict, grid_data: list, selected_nation: str = "All") -> Optional[str]:
    import streamlit as st
    import streamlit.components.v1 as components

    cell_size = 28
    gap = 1
    rows = len(grid_data)
    cols = len(grid_data[0]) if rows else 0
    width = cols * (cell_size + gap) + gap
    height = rows * (cell_size + gap) + gap

    cells = []
    occupied_assets = []

    for row in grid_data:
        for cell in row:
            x = cell["col"] * (cell_size + gap) + gap
            y = cell["row"] * (cell_size + gap) + gap
            assets = cell.get("assets", [])
            primary = assets[0] if assets else None
            cell_fill = primary["color"] if primary else "#F1F5F9"
            opacity = 1.0
            if primary and selected_nation != "All" and primary["nation"] != selected_nation:
                opacity = 0.25
            if primary:
                occupied_assets.append(primary)
            label = ""
            stroke = "none"
            stroke_width = 0
            if primary:
                if primary["is_reinforced"]:
                    stroke = "#FFFFFF"
                    stroke_width = 2
                label = "?" if primary["status"] == "destroyed" else ASSET_ABBREVIATIONS.get(primary["asset_type"], "?")
                tooltip = escape(f"{primary['name']} | {primary['health']:.0f}/{primary['max_health']:.0f} | {primary['status']} | {primary['nation']}")
            else:
                tooltip = escape(f"Cell {cell['row']},{cell['col']} | empty")
            cells.append(f"""
            <g opacity=\"{opacity}\">
              <rect x=\"{x}\" y=\"{y}\" width=\"{cell_size}\" height=\"{cell_size}\" rx=\"3\" fill=\"{cell_fill}\" stroke=\"{stroke}\" stroke-width=\"{stroke_width}\">
                <title>{tooltip}</title>
              </rect>
              <text x=\"{x + cell_size/2}\" y=\"{y + 18}\" text-anchor=\"middle\" font-size=\"14\" font-family=\"monospace\" fill=\"#0F172A\">{escape(label)}</text>
            </g>
            """)

    divider_y = 10 * (cell_size + gap)
    svg = f"""
    <div style=\"overflow:auto;border:1px solid #CBD5E1;border-radius:12px;padding:8px;background:#FFFFFF;\">
      <svg width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\" xmlns=\"http://www.w3.org/2000/svg\">
        <line x1=\"0\" y1=\"{divider_y}\" x2=\"{width}\" y2=\"{divider_y}\" stroke=\"#64748B\" stroke-dasharray=\"4 4\" stroke-width=\"1\" />
        {''.join(cells)}
      </svg>
    </div>
    """
    components.html(svg, height=min(max(height + 24, 200), 700), scrolling=True)

    options = ["None"] + [f"{asset['id']} ? {asset['name']}" for asset in occupied_assets]
    current = st.session_state.get("selected_asset")
    current_label = next((option for option in options if option.startswith(f"{current} ")) , "None") if current else "None"
    selected_label = st.selectbox("Inspect asset", options, index=options.index(current_label) if current_label in options else 0, key="map_asset_selector")
    selected_asset = None if selected_label == "None" else selected_label.split(" ? ", 1)[0]
    st.session_state.selected_asset = selected_asset
    return selected_asset

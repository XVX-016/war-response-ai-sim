from __future__ import annotations

from typing import Callable

import streamlit as st


def card(content_fn: Callable[[], None], border_left_colour: str = None) -> None:
    """
    Renders content_fn() inside a styled card div.
    border_left_colour: optional accent colour for the left border,
                        e.g. "#3B82F6" for active panels.
    """
    border_left = (
        f"border-left: 3px solid {border_left_colour};"
        if border_left_colour else
        "border-left: 1px solid #333333;"
    )
    st.markdown(f"""
    <div style="
        background-color: #212020;
        border: 1px solid #333333;
        {border_left}
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 12px;
    ">
    """, unsafe_allow_html=True)
    content_fn()
    st.markdown("</div>", unsafe_allow_html=True)

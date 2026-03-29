from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List, Optional

import config
from vision.annotate import draw_detections, suggestions_to_scenario_patch


def draw_vision_panel(detector: "YOLOv8Detector") -> Optional[List[dict]]:
    """Render the vision analyser panel and optionally return a patch list."""
    import streamlit as st

    st.markdown("## Infrastructure Vision Analyser")

    if detector.is_available():
        if getattr(detector, "using_pretrained", False):
            st.warning("Model loaded - pretrained YOLOv8n (reduced accuracy)")
        else:
            st.info("Model loaded - fine-tuned on xView civilian infrastructure classes")
    else:
        st.error("Vision module unavailable - install ultralytics or add model weights")
        st.code("pip install ultralytics")

    uploaded = st.file_uploader(
        "Upload aerial or satellite image",
        type=["jpg", "jpeg", "png", "tif"],
        help="Upload an overhead image of infrastructure to detect civilian assets.",
        key="vision_upload",
    )

    if uploaded is None:
        st.caption(
            "Upload an aerial image to detect power plants, water facilities, hospitals, transport hubs, fuel depots, shelters, telecom towers, and command centres."
        )
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / uploaded.name
        tmp_path.write_bytes(uploaded.getvalue())

        detection_result = detector.detect(tmp_path)
        suggestions = detector.suggest_scenario_assets(tmp_path)
        detection_result = detection_result.model_copy(update={"suggested_assets": suggestions})

        if not detector.is_available():
            st.warning("Model unavailable in this environment, so no detections can be produced yet.")
            return None

        if not detection_result.detections:
            st.warning("No civilian infrastructure detected in this image.")
            st.caption("Try an overhead or aerial image with visible buildings, roads, or industrial facilities.")
            return None

        annotated_path = draw_detections(tmp_path, detection_result)
        left, right = st.columns([0.6, 0.4])
        with left:
            st.image(str(annotated_path), use_column_width=True)
            st.caption(f"Detected {len(detection_result.detections)} civilian infrastructure objects")
        with right:
            table_rows = []
            for suggestion in sorted(suggestions, key=lambda item: item["confidence"], reverse=True):
                confidence = float(suggestion["confidence"])
                if confidence >= 0.7:
                    confidence_label = f"HIGH {confidence:.0%}"
                elif confidence >= 0.5:
                    confidence_label = f"MED {confidence:.0%}"
                else:
                    confidence_label = f"LOW {confidence:.0%}"
                table_rows.append({
                    "Class": suggestion["class_name"],
                    "Asset Type": suggestion["asset_type"],
                    "Confidence": confidence_label,
                    "Grid Position": f"row {suggestion['row']}, col {suggestion['col']}",
                })
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

        metric_cols = st.columns(3)
        metric_cols[0].metric("Objects detected", len(detection_result.detections))
        metric_cols[1].metric("Asset types found", len({item["asset_type"] for item in suggestions}))
        mean_conf = sum(item["confidence"] for item in suggestions) / max(len(suggestions), 1)
        metric_cols[2].metric("Mean confidence", f"{mean_conf:.0%}")

        selected_nation = st.selectbox("Assign detections to nation:", options=config.NATIONS, key="vision_nation")

        if st.button("Add to Scenario", key="vision_add_patch"):
            patch = suggestions_to_scenario_patch(suggestions, selected_nation)
            st.session_state.pending_vision_assets = patch
            st.success(f"Added {len(patch)} assets to pending patch")
            return patch

    return None

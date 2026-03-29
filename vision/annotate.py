from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from schemas import DetectionResult


_COLOR_MAP = {
    "power_plant": (0, 165, 255),
    "water_treatment": (255, 165, 0),
    "hospital": (0, 255, 0),
    "telecom_tower": (255, 0, 255),
    "transport_hub": (0, 255, 255),
    "fuel_depot": (0, 0, 255),
    "shelter": (200, 200, 200),
    "command_center": (255, 255, 0),
    "default": (128, 128, 128),
}


def draw_detections(
    image_path: str | Path,
    detection_result: DetectionResult,
    output_path: str | Path = None,
) -> Path:
    """Draw detection boxes and labels on an image and return the saved path."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise ImportError("opencv-python is required for draw_detections(); install with `pip install opencv-python`") from exc

    image = cv2.imread(str(image_path))
    for detection in detection_result.detections:
        x1, y1, x2, y2 = [int(v) for v in detection.bbox_xyxy]
        color = _COLOR_MAP.get(detection.mapped_asset_type or "default", _COLOR_MAP["default"])
        label = f"{detection.class_name} -> {detection.mapped_asset_type} ({detection.confidence:.0%})"
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image, label, (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    if output_path is None:
        output_path = image_path.with_name(f"{image_path.stem}_annotated{image_path.suffix}")
    output_path = Path(output_path)
    cv2.imwrite(str(output_path), image)
    return output_path


def suggestions_to_scenario_patch(
    suggestions: List[Dict[str, Any]],
    nation: str,
    existing_cells: set = None,
) -> List[Dict[str, Any]]:
    """Convert suggestion dicts into scenario asset entries."""
    existing_cells = set(existing_cells or set())
    counts: Dict[str, int] = {}
    patch: List[Dict[str, Any]] = []

    for suggestion in suggestions:
        row, col = suggestion["row"], suggestion["col"]
        if (row, col) in existing_cells:
            continue
        asset_type = suggestion["asset_type"]
        counts[asset_type] = counts.get(asset_type, 0) + 1
        idx = counts[asset_type]
        patch.append({
            "id": f"{nation.lower()}_{asset_type}_{idx:02d}",
            "name": f"{nation} {asset_type.replace('_', ' ').title()} {idx:02d}",
            "nation": nation,
            "asset_type": asset_type,
            "row": row,
            "col": col,
            "starting_health": 100,
        })
        existing_cells.add((row, col))

    return patch

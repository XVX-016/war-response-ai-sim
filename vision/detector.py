from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List, Optional

from loguru import logger

import config
from schemas import Detection, DetectionResult


class YOLOv8Detector:
    def __init__(self, weights_path: Optional[str | Path] = None) -> None:
        self._available = False
        self._model = None
        self._ultralytics = None

        try:
            import ultralytics  # type: ignore
        except ImportError:
            logger.warning("YOLOv8Detector unavailable: ultralytics is not installed")
            return

        self._ultralytics = ultralytics

        candidate_weights = None
        if weights_path is not None and Path(weights_path).exists():
            candidate_weights = str(Path(weights_path))
        elif Path(config.YOLO_WEIGHTS).exists():
            candidate_weights = str(config.YOLO_WEIGHTS)
        elif config.USE_PRETRAINED_YOLO:
            candidate_weights = config.YOLO_PRETRAINED
        else:
            logger.warning("YOLOv8Detector unavailable: no weights configured")
            return

        try:
            self._model = ultralytics.YOLO(candidate_weights)
            self._available = True
            logger.info("YOLOv8Detector loaded with weights {}", candidate_weights)
        except Exception as exc:
            logger.warning("YOLOv8Detector model load failed: {}", exc)
            self._model = None
            self._available = False

    def is_available(self) -> bool:
        return bool(self._available and self._model is not None)

    def detect(self, image_path: str | Path) -> DetectionResult:
        image_path = Path(image_path)
        if not self.is_available() or not image_path.exists():
            return DetectionResult(image_path=str(image_path), detections=[], suggested_assets=[])

        try:
            results = self._model(
                str(image_path),
                conf=config.YOLO_CONF_THRESHOLD,
                iou=config.YOLO_IOU_THRESHOLD,
                imgsz=config.YOLO_IMG_SIZE,
            )
        except Exception as exc:
            logger.warning("YOLO detection failed for {}: {}", image_path, exc)
            return DetectionResult(image_path=str(image_path), detections=[], suggested_assets=[])

        detections: list[Detection] = []
        mapped_types: list[str] = []
        for result in results:
            names = getattr(result, 'names', getattr(self._model, 'names', {}))
            boxes = getattr(result, 'boxes', None)
            if boxes is None:
                continue
            classes = getattr(boxes, 'cls', [])
            confidences = getattr(boxes, 'conf', [])
            xyxy_values = getattr(boxes, 'xyxy', [])
            for cls_id, confidence, bbox in zip(classes, confidences, xyxy_values):
                class_index = int(cls_id.item() if hasattr(cls_id, 'item') else cls_id)
                score = float(confidence.item() if hasattr(confidence, 'item') else confidence)
                bbox_list = [float(value.item() if hasattr(value, 'item') else value) for value in bbox]
                class_name = names[class_index] if isinstance(names, dict) else names[class_index]
                mapped_asset_type = config.YOLO_CLASS_MAP.get(class_name)
                if mapped_asset_type is None:
                    continue
                mapped_types.append(mapped_asset_type)
                detections.append(
                    Detection(
                        class_name=class_name,
                        confidence=score,
                        bbox_xyxy=bbox_list,
                        mapped_asset_type=mapped_asset_type,
                    )
                )

        inferred = Counter(mapped_types).most_common(1)[0][0] if mapped_types else None
        return DetectionResult(
            image_path=str(image_path),
            detections=detections,
            suggested_assets=[],
        ).model_copy(update={"suggested_assets": [], "image_path": str(image_path), "detections": detections})

    def detect_batch(self, image_paths: List[str | Path]) -> List[DetectionResult]:
        return [self.detect(path) for path in image_paths]

    def suggest_scenario_assets(self, image_path: str | Path, grid_rows: int, grid_cols: int) -> List[dict]:
        image_path = Path(image_path)
        result = self.detect(image_path)
        if not result.detections:
            return []

        try:
            from PIL import Image
            with Image.open(image_path) as image:
                width, height = image.size
        except Exception as exc:
            logger.warning("Unable to read image dimensions for {}: {}", image_path, exc)
            return []

        suggestions_by_cell: dict[tuple[int, int], dict] = {}
        for detection in result.detections:
            if detection.mapped_asset_type is None:
                continue
            x1, y1, x2, y2 = detection.bbox_xyxy
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            col = min(max(int((center_x / max(width, 1)) * grid_cols), 0), grid_cols - 1)
            row = min(max(int((center_y / max(height, 1)) * grid_rows), 0), grid_rows - 1)
            suggestion = {
                "asset_type": detection.mapped_asset_type,
                "row": row,
                "col": col,
                "confidence": float(detection.confidence),
                "source_bbox": list(detection.bbox_xyxy),
            }
            key = (row, col)
            existing = suggestions_by_cell.get(key)
            if existing is None or suggestion["confidence"] > existing["confidence"]:
                suggestions_by_cell[key] = suggestion

        return list(suggestions_by_cell.values())

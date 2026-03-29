from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

import config
from schemas import Detection, DetectionResult


class YOLOv8Detector:
    def __init__(self, weights_path: Optional[str | Path] = None):
        """
        Load model weights with fallback priority while remaining optional-safe.
        """
        self._available = False
        self._model = None
        self._loaded_weights: Optional[str] = None
        self._using_pretrained = False

        candidate: Optional[Path | str] = None
        if weights_path is not None and Path(weights_path).exists():
            candidate = Path(weights_path)
            self._using_pretrained = False
        elif Path(config.YOLO_WEIGHTS).exists():
            candidate = Path(config.YOLO_WEIGHTS)
            self._using_pretrained = False
        elif config.USE_PRETRAINED_YOLO:
            candidate = config.YOLO_PRETRAINED
            self._using_pretrained = True
        else:
            logger.warning(
                "YOLOv8Detector unavailable: no fine-tuned weights found and pretrained fallback disabled"
            )
            return

        try:
            from ultralytics import YOLO  # type: ignore
        except ImportError:
            logger.warning("YOLOv8Detector unavailable: ultralytics is not installed")
            return
        except Exception as exc:
            logger.warning(f"YOLOv8Detector unavailable: ultralytics failed to import: {exc}")
            return

        try:
            self._model = YOLO(str(candidate))
            self._loaded_weights = str(candidate)
            self._available = True
            logger.info(f"YOLOv8Detector loaded weights: {self._loaded_weights}")
        except Exception as exc:
            logger.warning(f"YOLOv8Detector model load failed: {exc}")
            self._available = False
            self._model = None
            self._loaded_weights = None

    def is_available(self) -> bool:
        return bool(self._available and self._model is not None)

    @property
    def using_pretrained(self) -> bool:
        return bool(self._using_pretrained and self.is_available())

    @property
    def loaded_weights(self) -> Optional[str]:
        return self._loaded_weights

    def detect(self, image_path: str | Path) -> DetectionResult:
        """Run inference on one image and return civilian-only detections."""
        image_path = Path(image_path)
        empty = DetectionResult(image_path=str(image_path), detections=[], inferred_asset_type=None, suggested_assets=[])
        if not self.is_available():
            return empty

        try:
            results = self._model(
                str(image_path),
                conf=config.YOLO_CONF_THRESHOLD,
                iou=config.YOLO_IOU_THRESHOLD,
                imgsz=config.YOLO_IMG_SIZE,
                verbose=False,
            )
            detections: List[Detection] = []
            best_mapped: Optional[str] = None
            best_conf = -1.0

            for result in results:
                boxes = getattr(result, "boxes", None)
                if boxes is None:
                    continue
                names = getattr(self._model, "names", getattr(result, "names", {}))
                for box in boxes:
                    class_name = names[int(box.cls)]
                    confidence = float(box.conf)
                    bbox_xyxy = [float(v) for v in box.xyxy[0].tolist()]
                    mapped = config.YOLO_CLASS_MAP.get(class_name)
                    if mapped is None:
                        continue
                    detections.append(
                        Detection(
                            class_name=class_name,
                            confidence=confidence,
                            bbox_xyxy=bbox_xyxy,
                            mapped_asset_type=mapped,
                        )
                    )
                    if confidence > best_conf:
                        best_conf = confidence
                        best_mapped = mapped

            return DetectionResult(
                image_path=str(image_path),
                detections=detections,
                inferred_asset_type=best_mapped,
                suggested_assets=[],
            )
        except Exception as exc:
            logger.warning(f"YOLO detection failed for {image_path}: {exc}")
            return empty

    def detect_batch(
        self,
        image_paths: List[str | Path],
        progress: bool = False,
    ) -> List[DetectionResult]:
        """Detect on multiple images without raising on individual failures."""
        iterator = image_paths
        if progress:
            try:
                from tqdm import tqdm  # type: ignore

                iterator = tqdm(image_paths)
            except ImportError:
                logger.info("tqdm not installed; continuing without progress bar")

        results: List[DetectionResult] = []
        for image_path in iterator:
            try:
                results.append(self.detect(image_path))
            except Exception as exc:
                logger.warning(f"Batch detection failed for {image_path}: {exc}")
                results.append(DetectionResult(image_path=str(Path(image_path)), detections=[], inferred_asset_type=None, suggested_assets=[]))
        return results

    def suggest_scenario_assets(
        self,
        image_path: str | Path,
        grid_rows: int = config.GRID_ROWS,
        grid_cols: int = config.GRID_COLS,
    ) -> List[Dict[str, Any]]:
        """Convert detections into deduplicated grid cell placement suggestions."""
        image_path = Path(image_path)
        detection_result = self.detect(image_path)
        if not detection_result.detections:
            return []

        try:
            from PIL import Image

            with Image.open(image_path) as image:
                img_w, img_h = image.size
        except Exception as exc:
            logger.warning(f"Unable to open image for scenario suggestions {image_path}: {exc}")
            return []

        by_cell: Dict[tuple[int, int], Dict[str, Any]] = {}
        for detection in detection_result.detections:
            if detection.mapped_asset_type is None:
                continue
            x1, y1, x2, y2 = detection.bbox_xyxy
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            row = int(cy / img_h * grid_rows)
            col = int(cx / img_w * grid_cols)
            row = max(0, min(grid_rows - 1, row))
            col = max(0, min(grid_cols - 1, col))
            suggestion = {
                "asset_type": detection.mapped_asset_type,
                "row": row,
                "col": col,
                "confidence": float(detection.confidence),
                "class_name": detection.class_name,
                "bbox_xyxy": list(detection.bbox_xyxy),
            }
            key = (row, col)
            existing = by_cell.get(key)
            if existing is None or suggestion["confidence"] > existing["confidence"]:
                by_cell[key] = suggestion

        return list(by_cell.values())

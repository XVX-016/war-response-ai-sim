from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import config
from engine.scenario_builder import build_scenario_from_vision, merge_vision_assets, validate_scenario
from schemas import DetectionResult
from vision.annotate import suggestions_to_scenario_patch
from vision.detector import YOLOv8Detector


def _blank_image(tmp_path: Path) -> Path:
    path = tmp_path / "blank.png"
    Image.new("RGB", (128, 128), color=(30, 30, 30)).save(path)
    return path


class TestYOLOv8DetectorGraceful:
    def test_import_without_ultralytics(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "ultralytics":
                raise ImportError("mocked missing ultralytics")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        detector = YOLOv8Detector()
        assert detector.is_available() is False

    def test_is_available_false_without_weights(self, monkeypatch):
        monkeypatch.setattr(config, "USE_PRETRAINED_YOLO", False)
        detector = YOLOv8Detector(weights_path=Path("does_not_exist.pt"))
        assert detector.is_available() is False

    def test_detect_returns_empty_when_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USE_PRETRAINED_YOLO", False)
        detector = YOLOv8Detector(weights_path=tmp_path / "missing.pt")
        result = detector.detect(tmp_path / "image.png")
        assert result.detections == []

    def test_detect_batch_returns_correct_length(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USE_PRETRAINED_YOLO", False)
        detector = YOLOv8Detector(weights_path=tmp_path / "missing.pt")
        results = detector.detect_batch([tmp_path / "a.png", tmp_path / "b.png", tmp_path / "c.png"])
        assert len(results) == 3

    def test_suggest_assets_returns_empty_when_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USE_PRETRAINED_YOLO", False)
        detector = YOLOv8Detector(weights_path=tmp_path / "missing.pt")
        assert detector.suggest_scenario_assets(tmp_path / "image.png") == []

    def test_detection_result_schema(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config, "USE_PRETRAINED_YOLO", False)
        detector = YOLOv8Detector(weights_path=tmp_path / "missing.pt")
        result = detector.detect(tmp_path / "image.png")
        assert isinstance(result, DetectionResult)
        assert hasattr(result, "image_path")
        assert hasattr(result, "detections")
        assert hasattr(result, "inferred_asset_type")


class TestYOLOv8DetectorWithModel:
    def _detector_or_skip(self):
        if not Path(config.YOLO_WEIGHTS).exists():
            pytest.skip("Fine-tuned model weights unavailable in local environment")
        detector = YOLOv8Detector(weights_path=config.YOLO_WEIGHTS)
        if not detector.is_available():
            pytest.skip("Model unavailable in local environment")
        return detector

    def test_detect_returns_detection_result(self, tmp_path):
        detector = self._detector_or_skip()
        result = detector.detect(_blank_image(tmp_path))
        assert isinstance(result, DetectionResult)

    def test_all_mapped_types_in_config(self, tmp_path):
        detector = self._detector_or_skip()
        result = detector.detect(_blank_image(tmp_path))
        assert all(det.mapped_asset_type is None or det.mapped_asset_type in config.ASSET_TYPES for det in result.detections)

    def test_confidence_in_range(self, tmp_path):
        detector = self._detector_or_skip()
        result = detector.detect(_blank_image(tmp_path))
        assert all(0.0 <= det.confidence <= 1.0 for det in result.detections)

    def test_bbox_has_four_values(self, tmp_path):
        detector = self._detector_or_skip()
        result = detector.detect(_blank_image(tmp_path))
        assert all(len(det.bbox_xyxy) == 4 for det in result.detections)

    def test_suggest_assets_valid_grid_positions(self, tmp_path):
        detector = self._detector_or_skip()
        suggestions = detector.suggest_scenario_assets(_blank_image(tmp_path))
        assert all(0 <= item["row"] < config.GRID_ROWS and 0 <= item["col"] < config.GRID_COLS for item in suggestions)

    def test_suggest_assets_no_duplicate_cells(self, tmp_path):
        detector = self._detector_or_skip()
        suggestions = detector.suggest_scenario_assets(_blank_image(tmp_path))
        cells = [(item["row"], item["col"]) for item in suggestions]
        assert len(cells) == len(set(cells))


class TestAnnotate:
    def test_suggestions_to_scenario_patch_generates_ids(self):
        patch = suggestions_to_scenario_patch([{"asset_type": "power_plant", "row": 4, "col": 7, "confidence": 0.8}], "Auria")
        assert patch[0]["id"].startswith("auria_power_plant_")

    def test_suggestions_to_scenario_patch_strips_confidence_key(self):
        patch = suggestions_to_scenario_patch([{"asset_type": "power_plant", "row": 4, "col": 7, "confidence": 0.8}], "Auria")
        assert "_confidence" not in patch[0]

    def test_suggestions_to_scenario_patch_avoids_existing_cells(self):
        patch = suggestions_to_scenario_patch([{"asset_type": "power_plant", "row": 4, "col": 7, "confidence": 0.8}], "Auria", existing_cells={(4, 7)})
        assert patch == []

    def test_suggestions_to_scenario_patch_unique_ids(self):
        patch = suggestions_to_scenario_patch([
            {"asset_type": "power_plant", "row": 4, "col": 7, "confidence": 0.8},
            {"asset_type": "power_plant", "row": 5, "col": 7, "confidence": 0.7},
        ], "Auria")
        ids = [item["id"] for item in patch]
        assert len(ids) == len(set(ids))


class TestMergeVisionAssets:
    def test_merge_adds_assets(self):
        scenario = build_scenario_from_vision([], name="Base Vision Scenario")
        original_count = len(scenario["assets"])
        merged, added, skipped = merge_vision_assets(scenario, [{
            "id": "auria_extra_01",
            "name": "Auria Extra 01",
            "nation": "Auria",
            "asset_type": "power_plant",
            "row": 19,
            "col": 19,
            "starting_health": 100,
            "_confidence": 0.82,
        }])
        assert len(merged["assets"]) > original_count
        assert added

    def test_merge_skips_occupied_cell(self):
        scenario = build_scenario_from_vision([], name="Occupied Vision Scenario")
        occupied = scenario["assets"][0]
        merged, added, skipped = merge_vision_assets(scenario, [{
            "id": "auria_overlap_01",
            "name": "Auria Overlap 01",
            "nation": "Auria",
            "asset_type": "power_plant",
            "row": occupied["row"],
            "col": occupied["col"],
            "starting_health": 100,
        }])
        assert not added
        assert skipped

    def test_merge_skips_invalid_asset_type(self):
        scenario = build_scenario_from_vision([], name="Invalid Type Scenario")
        merged, added, skipped = merge_vision_assets(scenario, [{
            "id": "auria_invalid_01",
            "name": "Auria Invalid 01",
            "nation": "Auria",
            "asset_type": "unknown_thing",
            "row": 18,
            "col": 19,
            "starting_health": 100,
        }])
        assert not added
        assert skipped

    def test_merge_returns_valid_scenario(self):
        scenario = build_scenario_from_vision([], name="Valid Merge Scenario")
        merged, added, skipped = merge_vision_assets(scenario, [{
            "id": "auria_valid_01",
            "name": "Auria Valid 01",
            "nation": "Auria",
            "asset_type": "power_plant",
            "row": 19,
            "col": 18,
            "starting_health": 100,
        }])
        assert validate_scenario(merged) == []

    def test_merge_strips_metadata_fields(self):
        scenario = build_scenario_from_vision([], name="Metadata Strip Scenario")
        merged, added, skipped = merge_vision_assets(scenario, [{
            "id": "auria_meta_01",
            "name": "Auria Meta 01",
            "nation": "Auria",
            "asset_type": "power_plant",
            "row": 19,
            "col": 17,
            "starting_health": 100,
            "_confidence": 0.91,
        }])
        merged_asset = next(asset for asset in merged["assets"] if asset["id"] == "auria_meta_01")
        assert "_confidence" not in merged_asset

    def test_build_scenario_from_vision_is_valid(self):
        fake_assets = [
            {
                "id": "auria_power_plant_v01",
                "name": "Auria Power Plant V01",
                "nation": "Auria",
                "asset_type": "power_plant",
                "row": 3,
                "col": 3,
                "starting_health": 100,
                "_confidence": 0.82,
            }
        ]
        scenario = build_scenario_from_vision(fake_assets, nations=config.NATIONS)
        assert validate_scenario(scenario) == []

from __future__ import annotations

import sys
import types
from pathlib import Path

from PIL import Image

import config
from vision import YOLOv8Detector


class _FakeScalar:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


class _FakeBoxes:
    def __init__(self):
        self.cls = [_FakeScalar(0), _FakeScalar(1), _FakeScalar(3)]
        self.conf = [_FakeScalar(0.91), _FakeScalar(0.87), _FakeScalar(0.75)]
        self.xyxy = [
            [_FakeScalar(10), _FakeScalar(20), _FakeScalar(50), _FakeScalar(60)],
            [_FakeScalar(100), _FakeScalar(110), _FakeScalar(160), _FakeScalar(170)],
            [_FakeScalar(105), _FakeScalar(115), _FakeScalar(165), _FakeScalar(175)],
        ]


class _FakeResult:
    names = {0: 'building', 1: 'hospital', 3: 'tower'}

    def __init__(self):
        self.boxes = _FakeBoxes()


class _FakeYOLO:
    names = {0: 'building', 1: 'hospital', 3: 'tower'}

    def __init__(self, weights):
        self.weights = weights

    def __call__(self, *args, **kwargs):
        return [_FakeResult()]


def test_detector_graceful_skip_without_ultralytics(monkeypatch):
    monkeypatch.setitem(sys.modules, 'ultralytics', None)
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == 'ultralytics':
            raise ImportError('missing ultralytics')
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr('builtins.__import__', fake_import)
    detector = YOLOv8Detector()
    assert detector.is_available() is False
    result = detector.detect('nonexistent.jpg')
    assert result.detections == []


def test_detector_with_fake_model(monkeypatch, tmp_path):
    fake_module = types.SimpleNamespace(YOLO=_FakeYOLO)
    monkeypatch.setitem(sys.modules, 'ultralytics', fake_module)
    monkeypatch.setattr(config, 'USE_PRETRAINED_YOLO', True)
    detector = YOLOv8Detector()
    assert detector.is_available() is True

    image_path = tmp_path / 'sample.png'
    Image.new('RGB', (200, 200), color='white').save(image_path)

    result = detector.detect(image_path)
    assert len(result.detections) == 3
    assert all(d.mapped_asset_type in config.YOLO_CLASS_MAP.values() for d in result.detections)

    batch = detector.detect_batch([image_path, image_path])
    assert len(batch) == 2

    suggestions = detector.suggest_scenario_assets(image_path, grid_rows=20, grid_cols=20)
    assert len(suggestions) >= 1
    assert all(0 <= item['row'] < 20 and 0 <= item['col'] < 20 for item in suggestions)

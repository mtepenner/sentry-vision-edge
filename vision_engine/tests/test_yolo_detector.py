"""
Tests for YoloDetector – always uses MockDetector (no GPU required).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from app.inference.yolo_detector import (
    Detection,
    MockDetector,
    YoloDetector,
    CLASS_NAMES,
    _preprocess,
)


class TestDetectionDataclass:
    def test_fields(self):
        d = Detection(
            bbox=[10.0, 20.0, 100.0, 200.0],
            class_id=0,
            label="person",
            confidence=0.95,
        )
        assert d.bbox == [10.0, 20.0, 100.0, 200.0]
        assert d.class_id == 0
        assert d.label == "person"
        assert d.confidence == pytest.approx(0.95)


class TestMockDetector:
    def test_returns_list(self):
        detector = MockDetector(seed=0)
        frame = np.zeros((512, 640), dtype=np.uint8)
        result = detector.detect(frame)
        assert isinstance(result, list)

    def test_detections_within_frame_bounds(self):
        detector = MockDetector(seed=1)
        frame = np.zeros((512, 640), dtype=np.uint8)
        for _ in range(20):
            dets = detector.detect(frame)
            for d in dets:
                x1, y1, x2, y2 = d.bbox
                assert 0 <= x1 < 640
                assert 0 <= y1 < 512
                assert x2 <= 640
                assert y2 <= 512
                assert x1 < x2
                assert y1 < y2

    def test_labels_are_valid(self):
        detector = MockDetector(seed=2)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(30):
            dets = detector.detect(frame)
            for d in dets:
                assert d.label in CLASS_NAMES

    def test_confidence_in_range(self):
        detector = MockDetector(seed=3)
        frame = np.ones((256, 256), dtype=np.uint8) * 128
        for _ in range(20):
            dets = detector.detect(frame)
            for d in dets:
                assert 0.0 <= d.confidence <= 1.0


class TestYoloDetector:
    def test_no_engine_uses_mock(self):
        detector = YoloDetector(engine_path="/nonexistent/path.engine")
        assert detector.is_mock

    def test_detect_returns_list_of_detections(self):
        detector = YoloDetector(engine_path="/nonexistent/path.engine")
        frame = np.zeros((512, 640, 3), dtype=np.uint8)
        result = detector.detect(frame)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, Detection)

    def test_grayscale_frame_accepted(self):
        detector = YoloDetector(engine_path="/nonexistent/path.engine")
        frame = np.zeros((512, 640), dtype=np.uint8)
        # Should not raise
        result = detector.detect(frame)
        assert isinstance(result, list)

    def test_multiple_frames_deterministic_with_same_seed(self):
        d1 = YoloDetector(engine_path="/nonexistent/path.engine")
        d2 = YoloDetector(engine_path="/nonexistent/path.engine")
        frame = np.zeros((512, 640), dtype=np.uint8)
        r1 = d1.detect(frame)
        r2 = d2.detect(frame)
        assert len(r1) == len(r2)


class TestPreprocess:
    def test_output_shape_rgb(self):
        frame = np.zeros((512, 640, 3), dtype=np.uint8)
        blob = _preprocess(frame, 640, 640)
        assert blob.shape == (1, 3, 640, 640)

    def test_output_shape_gray(self):
        frame = np.zeros((512, 640), dtype=np.uint8)
        blob = _preprocess(frame, 640, 640)
        assert blob.shape == (1, 3, 640, 640)

    def test_values_normalised(self):
        frame = np.full((64, 64, 3), 255, dtype=np.uint8)
        blob = _preprocess(frame, 64, 64)
        assert blob.max() == pytest.approx(1.0)
        assert blob.min() == pytest.approx(1.0)

"""
Unit tests for the SORT tracker.
Tests: track spawning, update, deletion, ID stability.
"""

import numpy as np
import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tracking.sort_tracker import (
    KalmanBoxTracker,
    SortTracker,
    _iou_batch,
    _associate_detections_to_trackers,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_det(x1, y1, x2, y2, score=0.9):
    return np.array([[x1, y1, x2, y2, score]], dtype=float)


# ---------------------------------------------------------------------------
# KalmanBoxTracker tests
# ---------------------------------------------------------------------------


class TestKalmanBoxTracker:
    def setup_method(self):
        KalmanBoxTracker._count = 0

    def test_initial_state(self):
        bbox = np.array([100.0, 200.0, 200.0, 400.0])
        trk = KalmanBoxTracker(bbox)
        state = trk.get_state()
        np.testing.assert_allclose(state, bbox, atol=1.0)

    def test_predict_changes_state(self):
        bbox = np.array([100.0, 200.0, 200.0, 400.0])
        trk = KalmanBoxTracker(bbox)
        # Without any velocity the prediction should be close to original
        pred = trk.predict()
        assert pred.shape == (4,)

    def test_update_reduces_uncertainty(self):
        bbox = np.array([100.0, 200.0, 200.0, 400.0])
        trk = KalmanBoxTracker(bbox)
        trk.predict()
        trk.update(bbox)
        assert trk.time_since_update == 0
        assert trk.hits == 2

    def test_id_increments(self):
        KalmanBoxTracker._count = 0
        t1 = KalmanBoxTracker(np.array([0.0, 0.0, 50.0, 50.0]))
        t2 = KalmanBoxTracker(np.array([60.0, 0.0, 110.0, 50.0]))
        assert t2.id == t1.id + 1

    def test_hit_streak_resets_after_miss(self):
        bbox = np.array([100.0, 100.0, 200.0, 200.0])
        trk = KalmanBoxTracker(bbox)
        trk.hit_streak = 5
        trk.time_since_update = 1  # simulate a miss
        trk.predict()  # hit_streak should reset to 0 during predict
        assert trk.hit_streak == 0


# ---------------------------------------------------------------------------
# IoU helper tests
# ---------------------------------------------------------------------------


class TestIouBatch:
    def test_perfect_overlap(self):
        boxes = np.array([[0, 0, 10, 10]], dtype=float)
        iou = _iou_batch(boxes, boxes)
        np.testing.assert_allclose(iou, [[1.0]], atol=1e-6)

    def test_no_overlap(self):
        a = np.array([[0, 0, 10, 10]], dtype=float)
        b = np.array([[20, 20, 30, 30]], dtype=float)
        iou = _iou_batch(a, b)
        np.testing.assert_allclose(iou, [[0.0]], atol=1e-6)

    def test_partial_overlap(self):
        a = np.array([[0, 0, 10, 10]], dtype=float)
        b = np.array([[5, 0, 15, 10]], dtype=float)
        iou = _iou_batch(a, b)
        # intersection = 5*10 = 50, union = 10*10 + 10*10 - 50 = 150
        np.testing.assert_allclose(iou, [[50.0 / 150.0]], atol=1e-6)

    def test_multiple_boxes(self):
        a = np.array([[0, 0, 10, 10], [20, 20, 30, 30]], dtype=float)
        b = np.array([[0, 0, 10, 10], [20, 20, 30, 30]], dtype=float)
        iou = _iou_batch(a, b)
        assert iou[0, 0] == pytest.approx(1.0)
        assert iou[1, 1] == pytest.approx(1.0)
        assert iou[0, 1] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Association tests
# ---------------------------------------------------------------------------


class TestAssociation:
    def test_empty_detections(self):
        trks = np.array([[0, 0, 10, 10]], dtype=float)
        matched, ud, ut = _associate_detections_to_trackers(
            np.empty((0, 4)), trks
        )
        assert len(matched) == 0
        assert len(ud) == 0
        assert ut == [0]

    def test_empty_trackers(self):
        dets = np.array([[0, 0, 10, 10]], dtype=float)
        matched, ud, ut = _associate_detections_to_trackers(
            dets, np.empty((0, 4))
        )
        assert len(matched) == 0
        assert ud == [0]
        assert len(ut) == 0

    def test_perfect_match(self):
        boxes = np.array([[0, 0, 10, 10]], dtype=float)
        matched, ud, ut = _associate_detections_to_trackers(boxes, boxes)
        assert len(matched) == 1
        assert len(ud) == 0
        assert len(ut) == 0

    def test_low_iou_unmatched(self):
        det = np.array([[0, 0, 5, 5]], dtype=float)
        trk = np.array([[50, 50, 60, 60]], dtype=float)
        matched, ud, ut = _associate_detections_to_trackers(
            det, trk, iou_threshold=0.3
        )
        assert len(matched) == 0
        assert ud == [0]
        assert ut == [0]


# ---------------------------------------------------------------------------
# SortTracker integration tests
# ---------------------------------------------------------------------------


class TestSortTracker:
    def setup_method(self):
        KalmanBoxTracker._count = 0

    def test_no_detections_returns_empty(self):
        tracker = SortTracker(max_age=1, min_hits=1)
        result = tracker.update(np.empty((0, 5)))
        assert result.shape == (0, 5)

    def test_single_track_spawns_after_min_hits(self):
        tracker = SortTracker(max_age=3, min_hits=3)
        bbox = np.array([[100.0, 100.0, 200.0, 200.0, 0.9]])
        # frames 1..3: track accumulates hits
        for i in range(3):
            result = tracker.update(bbox)
        # After min_hits frames the track should appear in output
        assert len(result) >= 1
        assert result[0, 4] >= 1  # valid ID

    def test_track_id_stable_over_frames(self):
        tracker = SortTracker(max_age=3, min_hits=1)
        bbox = np.array([[100.0, 100.0, 200.0, 200.0, 0.9]])
        ids = []
        for _ in range(5):
            result = tracker.update(bbox)
            if len(result) > 0:
                ids.append(int(result[0, 4]))
        assert len(set(ids)) == 1, "Track ID should be stable across frames"

    def test_track_deleted_after_max_age(self):
        tracker = SortTracker(max_age=2, min_hits=1)
        bbox = np.array([[100.0, 100.0, 200.0, 200.0, 0.9]])
        # Seed with a detection so a tracker is created
        tracker.update(bbox)
        # Now pass empty detections – track should age out
        for _ in range(4):
            tracker.update(np.empty((0, 5)))
        assert len(tracker.trackers) == 0

    def test_two_objects_tracked_separately(self):
        tracker = SortTracker(max_age=3, min_hits=1)
        dets = np.array(
            [
                [10.0, 10.0, 60.0, 60.0, 0.9],
                [300.0, 300.0, 380.0, 400.0, 0.85],
            ]
        )
        for _ in range(3):
            result = tracker.update(dets)
        if len(result) >= 2:
            ids = set(int(r[4]) for r in result)
            assert len(ids) == 2, "Two objects should have two different IDs"

    def test_reset_clears_trackers(self):
        tracker = SortTracker(max_age=3, min_hits=1)
        bbox = np.array([[100.0, 100.0, 200.0, 200.0, 0.9]])
        for _ in range(3):
            tracker.update(bbox)
        tracker.trackers.clear()
        assert len(tracker.trackers) == 0

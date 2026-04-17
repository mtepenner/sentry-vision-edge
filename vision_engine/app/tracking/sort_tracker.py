"""
SORT (Simple Online and Realtime Tracking) implementation from scratch.
Uses Kalman filter for state estimation and the Hungarian algorithm
(via scipy.optimize.linear_sum_assignment) for data association.

Reference:
  Bewley et al., "Simple Online and Realtime Tracking", ICIP 2016.
"""

import numpy as np
from scipy.optimize import linear_sum_assignment


# ---------------------------------------------------------------------------
# Kalman filter for a single bounding box
# ---------------------------------------------------------------------------


class KalmanBoxTracker:
    """
    Represents a single tracked object with a Kalman filter.

    State vector: [cx, cy, s, r, dcx, dcy, ds]
      cx, cy  – centre of bounding box
      s       – scale (area)
      r       – aspect ratio (width / height, kept constant)
      dcx, dcy, ds – velocities
    """

    _count: int = 0

    def __init__(self, bbox: np.ndarray) -> None:
        """
        bbox: [x1, y1, x2, y2]
        """
        KalmanBoxTracker._count += 1
        self.id: int = KalmanBoxTracker._count
        self.hits: int = 1
        self.hit_streak: int = 1
        self.age: int = 0
        self.time_since_update: int = 0

        # Convert bbox to [cx, cy, s, r]
        x = self._bbox_to_state(bbox)

        # --- Kalman filter matrices (7×7 state, 4×7 observation) ---
        dt = 1.0

        # Transition matrix F
        self.F = np.eye(7)
        self.F[0, 4] = dt
        self.F[1, 5] = dt
        self.F[2, 6] = dt

        # Observation matrix H
        self.H = np.zeros((4, 7))
        self.H[:4, :4] = np.eye(4)

        # Measurement noise covariance R
        self.R = np.eye(4)
        self.R[2, 2] = 10.0
        self.R[3, 3] = 10.0

        # Process noise covariance Q
        self.Q = np.eye(7)
        self.Q[4, 4] = 0.01
        self.Q[5, 5] = 0.01
        self.Q[6, 6] = 0.0001

        # State estimate and covariance
        self.x = np.zeros((7, 1))
        self.x[:4, 0] = x

        self.P = np.eye(7)
        self.P[4, 4] = 1000.0
        self.P[5, 5] = 1000.0
        self.P[6, 6] = 1000.0

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bbox_to_state(bbox: np.ndarray) -> np.ndarray:
        """[x1,y1,x2,y2] -> [cx,cy,s,r]"""
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = bbox[0] + w / 2.0
        y = bbox[1] + h / 2.0
        s = w * h          # scale = area
        r = w / float(h) if h > 0 else 1.0
        return np.array([x, y, s, r])

    @staticmethod
    def _state_to_bbox(x: np.ndarray) -> np.ndarray:
        """[cx,cy,s,r,...] -> [x1,y1,x2,y2]"""
        w = np.sqrt(abs(x[2]) * abs(x[3]))
        h = abs(x[2]) / w if w > 0 else 1.0
        return np.array(
            [
                x[0] - w / 2.0,
                x[1] - h / 2.0,
                x[0] + w / 2.0,
                x[1] + h / 2.0,
            ]
        )

    # ------------------------------------------------------------------
    # Kalman predict / update
    # ------------------------------------------------------------------

    def predict(self) -> np.ndarray:
        """Advance state one step and return predicted bbox [x1,y1,x2,y2]."""
        if self.time_since_update > 0:
            self.hit_streak = 0

        self.age += 1
        self.time_since_update += 1

        # Predict
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

        return self._state_to_bbox(self.x[:4, 0])

    def update(self, bbox: np.ndarray) -> None:
        """Update state with new observed bbox [x1,y1,x2,y2]."""
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1

        z = self._bbox_to_state(bbox).reshape(4, 1)

        # Innovation
        y = z - self.H @ self.x

        # Innovation covariance
        S = self.H @ self.P @ self.H.T + self.R

        # Kalman gain
        K = self.P @ self.H.T @ np.linalg.inv(S)

        # State update
        self.x = self.x + K @ y

        # Covariance update (Joseph form for numerical stability)
        I_KH = np.eye(7) - K @ self.H
        self.P = I_KH @ self.P

    def get_state(self) -> np.ndarray:
        """Return current bbox estimate [x1,y1,x2,y2]."""
        return self._state_to_bbox(self.x[:4, 0])


# ---------------------------------------------------------------------------
# IoU and matching
# ---------------------------------------------------------------------------


def _iou_batch(bb_test: np.ndarray, bb_gt: np.ndarray) -> np.ndarray:
    """
    Compute IoU between each row of bb_test and each row of bb_gt.
    Returns matrix of shape (len(bb_test), len(bb_gt)).
    """
    bb_gt = bb_gt[np.newaxis, :, :]   # (1, G, 4)
    bb_test = bb_test[:, np.newaxis, :]  # (T, 1, 4)

    xx1 = np.maximum(bb_test[..., 0], bb_gt[..., 0])
    yy1 = np.maximum(bb_test[..., 1], bb_gt[..., 1])
    xx2 = np.minimum(bb_test[..., 2], bb_gt[..., 2])
    yy2 = np.minimum(bb_test[..., 3], bb_gt[..., 3])

    w = np.maximum(0.0, xx2 - xx1)
    h = np.maximum(0.0, yy2 - yy1)
    inter = w * h

    area_test = (bb_test[..., 2] - bb_test[..., 0]) * (
        bb_test[..., 3] - bb_test[..., 1]
    )
    area_gt = (bb_gt[..., 2] - bb_gt[..., 0]) * (
        bb_gt[..., 3] - bb_gt[..., 1]
    )
    union = area_test + area_gt - inter

    return np.where(union == 0, 0.0, inter / union)


def _associate_detections_to_trackers(
    detections: np.ndarray,
    trackers: np.ndarray,
    iou_threshold: float = 0.3,
):
    """
    Assign detections to tracked objects (both represented as bounding boxes).

    Returns:
      matched        – (N,2) array of [det_idx, trk_idx]
      unmatched_dets – indices of unmatched detections
      unmatched_trks – indices of unmatched trackers
    """
    if len(trackers) == 0:
        return (
            np.empty((0, 2), dtype=int),
            list(range(len(detections))),
            [],
        )
    if len(detections) == 0:
        return (
            np.empty((0, 2), dtype=int),
            [],
            list(range(len(trackers))),
        )

    iou_matrix = _iou_batch(detections, trackers)

    # Maximise total IoU → minimise negative IoU
    row_ind, col_ind = linear_sum_assignment(-iou_matrix)

    matched_indices = np.stack([row_ind, col_ind], axis=1)

    unmatched_dets = [
        d for d in range(len(detections)) if d not in matched_indices[:, 0]
    ]
    unmatched_trks = [
        t for t in range(len(trackers)) if t not in matched_indices[:, 1]
    ]

    # Filter low-IoU matches
    matched: list = []
    for m in matched_indices:
        if iou_matrix[m[0], m[1]] < iou_threshold:
            unmatched_dets.append(m[0])
            unmatched_trks.append(m[1])
        else:
            matched.append(m)

    if len(matched) == 0:
        return np.empty((0, 2), dtype=int), unmatched_dets, unmatched_trks

    return np.array(matched, dtype=int), unmatched_dets, unmatched_trks


# ---------------------------------------------------------------------------
# SortTracker
# ---------------------------------------------------------------------------


class SortTracker:
    """
    SORT multi-object tracker.

    Parameters
    ----------
    max_age     : how many frames a track can go unmatched before deletion
    min_hits    : minimum detections before a track is considered confirmed
    iou_threshold: IoU threshold for the Hungarian matching step
    """

    def __init__(
        self,
        max_age: int = 3,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
    ) -> None:
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers: list[KalmanBoxTracker] = []
        self.frame_count: int = 0
        # Reset global ID counter for reproducible tests
        KalmanBoxTracker._count = 0

    def update(self, detections: np.ndarray) -> np.ndarray:
        """
        Update the tracker with new detections.

        Parameters
        ----------
        detections: np.ndarray of shape (N, 5) – [x1, y1, x2, y2, score]
                    Pass empty array (shape (0,5)) for frames with no detections.

        Returns
        -------
        np.ndarray of shape (M, 5) – [x1, y1, x2, y2, track_id]
          Only confirmed tracks (hit_streak >= min_hits or frame_count <=
          min_hits) are included.
        """
        self.frame_count += 1

        # 1. Predict new positions for all trackers
        predicted_boxes = np.zeros((len(self.trackers), 4))
        dead: list[int] = []
        for i, trk in enumerate(self.trackers):
            bbox = trk.predict()
            if np.any(np.isnan(bbox)):
                dead.append(i)
            else:
                predicted_boxes[i] = bbox

        for i in sorted(dead, reverse=True):
            self.trackers.pop(i)
        predicted_boxes = np.delete(predicted_boxes, dead, axis=0)

        # 2. Associate detections with predictions
        det_boxes = (
            detections[:, :4] if len(detections) > 0 else np.empty((0, 4))
        )
        matched, unmatched_dets, unmatched_trks = _associate_detections_to_trackers(
            det_boxes, predicted_boxes, self.iou_threshold
        )

        # 3. Update matched trackers
        for m in matched:
            self.trackers[m[1]].update(detections[m[0], :4])

        # 4. Create new trackers for unmatched detections
        for i in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(detections[i, :4]))

        # 5. Collect results and remove dead tracks
        results = []
        survivors = []
        for trk in self.trackers:
            if trk.time_since_update <= self.max_age:
                survivors.append(trk)
                if trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits:
                    bbox = trk.get_state()
                    results.append([*bbox, float(trk.id)])

        self.trackers = survivors

        if results:
            return np.array(results, dtype=float)
        return np.empty((0, 5), dtype=float)

"""
Main entry point for the Vision Engine.

Ties together:
  - ThermalStream (camera capture)
  - YoloDetector (inference)
  - SortTracker (multi-object tracking)

Sends track metadata to the Go Behavioral Brain via HTTP POST.
"""

import json
import logging
import os
import time

import numpy as np
import requests

from app.camera.thermal_stream import ThermalStream
from app.inference.yolo_detector import YoloDetector
from app.tracking.sort_tracker import SortTracker

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------

BRAIN_URL = os.environ.get("BRAIN_URL", "http://localhost:8080/tracks")
DEVICE = os.environ.get("THERMAL_DEVICE", "/dev/video0")
FRAME_WIDTH = int(os.environ.get("THERMAL_WIDTH", "640"))
FRAME_HEIGHT = int(os.environ.get("THERMAL_HEIGHT", "512"))
FPS = int(os.environ.get("THERMAL_FPS", "30"))
ENGINE_PATH = os.environ.get("ENGINE_PATH", "models/custom_sentry_n.engine")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
MAX_AGE = int(os.environ.get("SORT_MAX_AGE", "3"))
MIN_HITS = int(os.environ.get("SORT_MIN_HITS", "3"))
IOU_THRESHOLD = float(os.environ.get("SORT_IOU_THRESHOLD", "0.3"))
POST_TIMEOUT = float(os.environ.get("POST_TIMEOUT", "0.5"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_payload(tracks: np.ndarray, timestamp: float) -> dict:
    """Convert tracker output array to JSON-serialisable dict."""
    track_list = []
    for row in tracks:
        x1, y1, x2, y2, tid = row
        track_list.append(
            {
                "id": int(tid),
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
            }
        )
    return {"timestamp": timestamp, "tracks": track_list}


def _post_tracks(url: str, payload: dict, timeout: float) -> None:
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            logger.warning("Brain returned HTTP %d", resp.status_code)
    except requests.exceptions.ConnectionError:
        logger.debug("Brain not reachable at %s – skipping post.", url)
    except requests.exceptions.Timeout:
        logger.warning("POST to brain timed out.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error posting tracks: %s", exc)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run() -> None:
    """Main processing loop. Runs until interrupted."""
    logger.info("Starting Vision Engine…")

    detector = YoloDetector(engine_path=ENGINE_PATH)
    tracker = SortTracker(
        max_age=MAX_AGE, min_hits=MIN_HITS, iou_threshold=IOU_THRESHOLD
    )
    stream = ThermalStream(
        device=DEVICE, width=FRAME_WIDTH, height=FRAME_HEIGHT, fps=FPS
    )

    with stream:
        for frame in stream.frames():
            t_start = time.monotonic()

            # Inference
            detections = detector.detect(frame)

            # Convert to ndarray for tracker  [x1,y1,x2,y2,score]
            if detections:
                det_array = np.array(
                    [[*d.bbox, d.confidence] for d in detections], dtype=float
                )
            else:
                det_array = np.empty((0, 5), dtype=float)

            # Tracking
            tracks = tracker.update(det_array)

            # Send to Go brain
            if len(tracks) > 0:
                payload = _build_payload(tracks, time.time())
                _post_tracks(BRAIN_URL, payload, POST_TIMEOUT)

            elapsed = time.monotonic() - t_start
            logger.debug(
                "Frame processed in %.1f ms – %d tracks", elapsed * 1000, len(tracks)
            )


if __name__ == "__main__":
    run()

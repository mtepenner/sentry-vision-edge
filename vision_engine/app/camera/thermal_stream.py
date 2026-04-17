"""
Thermal camera interface using V4L2 / OpenCV.
On systems without a real thermal camera, falls back to a synthetic frame generator.
"""

import os
import logging
from typing import Generator

import cv2
import numpy as np

logger = logging.getLogger(__name__)

DEVICE_PATH = os.environ.get("THERMAL_DEVICE", "/dev/video0")
FRAME_WIDTH = int(os.environ.get("THERMAL_WIDTH", "640"))
FRAME_HEIGHT = int(os.environ.get("THERMAL_HEIGHT", "512"))
FPS = int(os.environ.get("THERMAL_FPS", "30"))


class ThermalStream:
    """
    Opens a V4L2 thermal camera device and yields grayscale frames.
    Falls back to synthetic noise frames when the device is unavailable.
    """

    def __init__(
        self,
        device: str = DEVICE_PATH,
        width: int = FRAME_WIDTH,
        height: int = FRAME_HEIGHT,
        fps: int = FPS,
    ) -> None:
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: cv2.VideoCapture | None = None

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "ThermalStream":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open(self) -> bool:
        """Open the V4L2 device. Returns True on success."""
        cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            self._cap = cap
            logger.info("Opened thermal device: %s", self.device)
            return True

        logger.warning(
            "Could not open %s – falling back to synthetic frames.", self.device
        )
        cap.release()
        self._cap = None
        return False

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def frames(self) -> Generator[np.ndarray, None, None]:
        """
        Yield frames indefinitely.
        Each frame is a uint8 numpy array shaped (H, W) or (H, W, 3).
        """
        if self._cap is not None and self._cap.isOpened():
            yield from self._capture_frames()
        else:
            yield from self._synthetic_frames()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _capture_frames(self) -> Generator[np.ndarray, None, None]:
        assert self._cap is not None
        while True:
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Frame capture failed – stopping stream.")
                break
            yield frame

    def _synthetic_frames(self) -> Generator[np.ndarray, None, None]:
        """Generate synthetic thermal-like noise frames for testing / demo."""
        rng = np.random.default_rng(seed=42)
        while True:
            base = rng.integers(60, 100, size=(self.height, self.width), dtype=np.uint8)
            # simulate warm blobs
            for _ in range(rng.integers(1, 4)):
                cx = int(rng.integers(50, self.width - 50))
                cy = int(rng.integers(50, self.height - 50))
                cv2.circle(base, (cx, cy), int(rng.integers(15, 40)), 200, -1)
            frame = cv2.GaussianBlur(base, (5, 5), 0)
            yield frame

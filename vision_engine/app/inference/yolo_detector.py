"""
YOLOv8/v10 detector using TensorRT (with mock fallback for non-GPU environments).
"""

import logging
import os
import random
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

ENGINE_PATH = os.environ.get("ENGINE_PATH", "models/custom_sentry_n.engine")
CONF_THRESHOLD = float(os.environ.get("CONF_THRESHOLD", "0.35"))
NMS_THRESHOLD = float(os.environ.get("NMS_THRESHOLD", "0.45"))
INPUT_WIDTH = int(os.environ.get("YOLO_INPUT_WIDTH", "640"))
INPUT_HEIGHT = int(os.environ.get("YOLO_INPUT_HEIGHT", "640"))

CLASS_NAMES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "truck",
    "bus",
    "unknown",
]


@dataclass
class Detection:
    """A single detection result."""

    bbox: List[float]   # [x1, y1, x2, y2] in pixel coords
    class_id: int
    label: str
    confidence: float


def _try_import_tensorrt():
    """Attempt to import TensorRT modules; return None if unavailable."""
    try:
        import tensorrt as trt  # type: ignore
        import pycuda.autoinit  # type: ignore  # noqa: F401
        import pycuda.driver as cuda  # type: ignore
        return trt, cuda
    except ImportError:
        return None, None


class TensorRTEngine:
    """Thin wrapper around a TensorRT .engine file."""

    def __init__(self, engine_path: str) -> None:
        trt, cuda = _try_import_tensorrt()
        if trt is None or cuda is None:
            raise RuntimeError("TensorRT / PyCUDA not available")

        self._trt = trt
        self._cuda = cuda
        self._logger = trt.Logger(trt.Logger.WARNING)

        runtime = trt.Runtime(self._logger)
        with open(engine_path, "rb") as f:
            self._engine = runtime.deserialize_cuda_engine(f.read())

        self._context = self._engine.create_execution_context()
        self._allocate_buffers()

    def _allocate_buffers(self):
        import pycuda.driver as cuda  # type: ignore

        self.inputs, self.outputs, self.bindings = [], [], []
        self.stream = cuda.Stream()
        for binding in self._engine:
            size = (
                abs(self._trt.volume(self._engine.get_binding_shape(binding)))
                * self._engine.max_batch_size
            )
            dtype = self._trt.nptype(self._engine.get_binding_dtype(binding))
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            self.bindings.append(int(device_mem))
            if self._engine.binding_is_input(binding):
                self.inputs.append({"host": host_mem, "device": device_mem})
            else:
                self.outputs.append({"host": host_mem, "device": device_mem})

    def infer(self, input_array: np.ndarray) -> List[np.ndarray]:
        import pycuda.driver as cuda  # type: ignore

        np.copyto(self.inputs[0]["host"], input_array.ravel())
        cuda.memcpy_htod_async(
            self.inputs[0]["device"], self.inputs[0]["host"], self.stream
        )
        self._context.execute_async_v2(
            bindings=self.bindings, stream_handle=self.stream.handle
        )
        for out in self.outputs:
            cuda.memcpy_dtoh_async(out["host"], out["device"], self.stream)
        self.stream.synchronize()
        return [out["host"] for out in self.outputs]


def _preprocess(frame: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """Resize and normalise frame for YOLO input."""
    import cv2

    resized = cv2.resize(frame, (target_w, target_h))
    if len(resized.shape) == 2:
        # Grayscale – replicate to 3 channels
        resized = np.stack([resized] * 3, axis=-1)
    blob = resized.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))  # HWC -> CHW
    return np.expand_dims(blob, 0)  # add batch dim


def _postprocess(
    output: np.ndarray,
    orig_w: int,
    orig_h: int,
    conf_thresh: float,
    nms_thresh: float,
) -> List[Detection]:
    """Parse raw YOLO output into Detection objects."""
    import cv2

    # output shape: [1, 85+, num_anchors] or similar
    # Flatten to [num_detections, 85]
    predictions = output.reshape(-1, output.shape[-1])
    boxes, scores, class_ids = [], [], []

    for pred in predictions:
        obj_conf = float(pred[4])
        if obj_conf < conf_thresh:
            continue
        class_scores = pred[5:]
        cid = int(np.argmax(class_scores))
        confidence = obj_conf * float(class_scores[cid])
        if confidence < conf_thresh:
            continue

        cx, cy, bw, bh = pred[0], pred[1], pred[2], pred[3]
        x1 = int((cx - bw / 2) * orig_w / INPUT_WIDTH)
        y1 = int((cy - bh / 2) * orig_h / INPUT_HEIGHT)
        bw_px = int(bw * orig_w / INPUT_WIDTH)
        bh_px = int(bh * orig_h / INPUT_HEIGHT)
        boxes.append([x1, y1, bw_px, bh_px])
        scores.append(float(confidence))
        class_ids.append(cid)

    indices = cv2.dnn.NMSBoxes(boxes, scores, conf_thresh, nms_thresh)
    detections: List[Detection] = []
    for i in (indices.flatten() if len(indices) > 0 else []):
        x1, y1, w, h = boxes[i]
        cid = class_ids[i]
        detections.append(
            Detection(
                bbox=[float(x1), float(y1), float(x1 + w), float(y1 + h)],
                class_id=cid,
                label=CLASS_NAMES[cid] if cid < len(CLASS_NAMES) else "unknown",
                confidence=scores[i],
            )
        )
    return detections


class MockDetector:
    """Returns randomised detections – used when TensorRT is not available."""

    def __init__(self, seed: int = 0) -> None:
        random.seed(seed)
        self._rng = np.random.default_rng(seed)

    def detect(self, frame: np.ndarray) -> List[Detection]:
        h, w = frame.shape[:2]
        n = int(self._rng.integers(0, 4))
        detections: List[Detection] = []
        for _ in range(n):
            x1 = int(self._rng.integers(0, w - 60))
            y1 = int(self._rng.integers(0, h - 60))
            x2 = x1 + int(self._rng.integers(30, 120))
            y2 = y1 + int(self._rng.integers(40, 160))
            cid = int(self._rng.integers(0, len(CLASS_NAMES)))
            conf = float(self._rng.uniform(CONF_THRESHOLD, 1.0))
            detections.append(
                Detection(
                    bbox=[float(x1), float(y1), float(min(x2, w)), float(min(y2, h))],
                    class_id=cid,
                    label=CLASS_NAMES[cid],
                    confidence=conf,
                )
            )
        return detections


class YoloDetector:
    """
    Main detector class.
    Uses TensorRT if available and the engine file exists, otherwise falls back
    to MockDetector.
    """

    def __init__(
        self,
        engine_path: str = ENGINE_PATH,
        conf_threshold: float = CONF_THRESHOLD,
        nms_threshold: float = NMS_THRESHOLD,
    ) -> None:
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self._engine: Optional[TensorRTEngine] = None
        self._mock: Optional[MockDetector] = None

        if os.path.isfile(engine_path):
            try:
                self._engine = TensorRTEngine(engine_path)
                logger.info("TensorRT engine loaded from %s", engine_path)
            except Exception as exc:
                logger.warning("TensorRT load failed (%s) – using mock detector.", exc)
                self._mock = MockDetector()
        else:
            logger.info(
                "Engine file %s not found – using mock detector.", engine_path
            )
            self._mock = MockDetector()

    @property
    def is_mock(self) -> bool:
        return self._mock is not None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run detection on a frame and return a list of Detection objects."""
        if self._engine is not None:
            return self._detect_trt(frame)
        assert self._mock is not None
        return self._mock.detect(frame)

    def _detect_trt(self, frame: np.ndarray) -> List[Detection]:
        assert self._engine is not None
        orig_h, orig_w = frame.shape[:2]
        blob = _preprocess(frame, INPUT_WIDTH, INPUT_HEIGHT)
        outputs = self._engine.infer(blob)
        return _postprocess(
            outputs[0],
            orig_w,
            orig_h,
            self.conf_threshold,
            self.nms_threshold,
        )

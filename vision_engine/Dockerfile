# ---------- build stage ----------
FROM python:3.10-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- runtime stage ----------
FROM python:3.10-slim

# ARM64 / Jetson note:
# When running on a Jetson, replace this base with a JetPack-compatible
# image (e.g. nvcr.io/nvidia/l4t-ml) that provides TensorRT and CUDA.

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "app.main"]

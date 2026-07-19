# nammadashcam

Python-first hackathon bootstrap for a collaboration-ready pothole detection pipeline on Arduino UNO Q Linux side.

## Objective
Build a modular service flow for:

- accelerometer-triggered event intake,
- camera frame retrieval,
- pothole inference,
- evidence upload.

The current commit provides contracts and stubs so teammates can work in parallel without blocking each other.

## High-Level Architecture

```text
Accel Event Producer -> Event Consumer -> Camera Service -> Inference Service -> Upload Service
```

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pytest -q
PYTHONPATH=src python -m pothole_dashcam.main --camera-backend stub
```

## Team Workflow

- Branch naming: `feat/<module>-<name>`
- Open PRs early and keep them small.
- Run lint and smoke tests before pushing.

### Informal module ownership

- Teammate A: accelerometer integration contract
- Teammate B: camera pipeline
- Teammate C: inference
- Teammate D: cloud upload

## Current Status

- Lean bootstrap scaffold complete.
- Interface contracts and placeholder implementations present.
- Fixed-window `CameraBufferService` (SQLite index + file retention) implemented.
- USB camera capture service (`UsbCameraService`) integrated for Linux-side smoke capture.
- CI baseline configured for lint + tests.

## Hardware Run (UNO Q Linux side)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=src python -m pothole_dashcam.main \
  --camera-backend usb \
  --camera-device-index 0 \
  --inference-backend onnx \
  --onnx-model-path models/best.onnx \
  --inference-threshold 0.5
```

Use stub backends when hardware/model is not connected:

```bash
PYTHONPATH=src python -m pothole_dashcam.main \
  --camera-backend stub \
  --inference-backend stub
```

If `--inference-backend onnx` is selected but model file is missing, runtime
automatically falls back to stub inference and logs a warning.

Current bootstrap initializes:

- `runtime/frames/` directory
- `runtime/frame_index.db` SQLite index
- selected camera backend (`stub` or `usb`)
- selected inference backend (`stub` or `onnx`)

## Inference Tests

Default test run remains hardware/model independent:

```bash
pytest -q
```

Optional real ONNX test (requires `models/best.onnx` locally):

```bash
RUN_ONNX_REAL_TEST=1 pytest -q tests/test_inference_service.py
```

Bundled pothole sample image is available at:

- `tests/assets/pothole_sample.jpg`

## Next Milestones

1. Add continuous 1 FPS capture loop for full 10-minute soak.
2. Replace accelerometer adapter stub with teammate implementation.
3. Integrate event-timestamp retrieval from frame buffer for inference.
4. Connect upload backend.

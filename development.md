# Development Guide

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Quality Checks

```bash
ruff check .
pytest -q
```

## Runtime Commands

### Stub-only run (no hardware/model needed)

```bash
PYTHONPATH=src python -m pothole_dashcam.main \
  --camera-backend stub \
  --inference-backend stub \
  --capture-max-frames 10
```

### UNO Q hardware run (USB camera + ONNX)

```bash
PYTHONPATH=src python -m pothole_dashcam.main \
  --camera-backend usb \
  --camera-device-index 0 \
  --inference-backend onnx \
  --onnx-model-path models/best.onnx \
  --inference-threshold 0.5 \
  --capture-interval-s 1.0 \
  --capture-max-seconds 600
```

## Inference Tests

Default test run remains hardware/model independent:

```bash
pytest -q
```

Run real ONNX tests (uses committed model at `models/best.onnx`):

```bash
RUN_ONNX_REAL_TEST=1 INFERENCE_CONF=0.5 pytest -q tests/test_inference_service.py
```

Adjust threshold:

```bash
RUN_ONNX_REAL_TEST=1 INFERENCE_CONF=0.6 pytest -q tests/test_inference_service.py
```

Bundled sample images:

- `tests/assets/pothole_sample.jpg`
- `tests/assets/non_pothole_sample.jpg`

## Model Location

The ONNX model is now stored in-repo at:

- `models/best.onnx`

This is the default model path used by the runtime CLI (`--onnx-model-path models/best.onnx`), so non-stub inference can run immediately without additional model download steps.

## Runtime Behavior

Current runtime:

- initializes `runtime/frames/` directory
- initializes `runtime/frame_index.db` SQLite index
- starts selected camera backend (`stub` or `usb`)
- starts selected inference backend (`stub` or `onnx`)
- runs continuous capture loop into `CameraBufferService`
- enforces retention automatically via buffer policy (10 min / 600 frames)

Capture loop controls:

- `--capture-interval-s` (default `1.0`)
- `--capture-max-frames` (default `0`, unbounded)
- `--capture-max-seconds` (default `0`, unbounded)

## Notes

- If `--inference-backend onnx` is selected but model file is missing, runtime falls back to stub inference and logs a warning.
- Runtime artifacts are ignored via `.gitignore` under `runtime/`.

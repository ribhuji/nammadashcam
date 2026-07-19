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
- supports motion backends: `stub`, `serial` (interim), `bridge` (UNO Q internal recommended)
- runs continuous capture loop into `CameraBufferService`
- enforces retention automatically via buffer policy (10 min / 600 frames)

Capture loop controls:

- `--capture-interval-s` (default `1.0`)
- `--capture-max-frames` (default `0`, unbounded)
- `--capture-max-seconds` (default `0`, unbounded)

## Firmware (UNO Q MCU)

MCU-side firmware now lives under:

- `firmware/unoq_dashcam_mcu/unoq_dashcam_mcu.ino`
- `firmware/README.md` (build/flash instructions)

Install MCU dependencies once:

```bash
arduino-cli core update-index
arduino-cli core install arduino:zephyr
arduino-cli lib update-index
arduino-cli lib install "Arduino_Modulino"
arduino-cli lib install "Arduino_RouterBridge"
```

Build firmware:

```bash
arduino-cli compile --fqbn arduino:zephyr:unoq firmware/unoq_dashcam_mcu
```

### UNO Q Bridge motion run (recommended on-device)

Run the Linux service with Bridge backend enabled:

```bash
PYTHONPATH=src python -m pothole_dashcam.main \
  --camera-backend stub \
  --inference-backend stub \
  --motion-backend bridge \
  --motion-monitor-seconds 30
```

This path consumes MCU `motion_sample` bridge callbacks and logs `MAYBE_POTHOLE ...` when thresholds are exceeded.

### Legacy serial motion run (interim only)

```bash
PYTHONPATH=src python -m pothole_dashcam.main \
  --camera-backend stub \
  --inference-backend stub \
  --motion-backend serial \
  --motion-port /dev/ttyUSB0 \
  --motion-baud 115200 \
  --motion-monitor-seconds 30
```

## Notes

- Arduino libraries are not vendored in this repo; install them via Arduino CLI for reproducible team setup.
- If `--inference-backend onnx` is selected but model file is missing, runtime falls back to stub inference and logs a warning.
- Runtime artifacts are ignored via `.gitignore` under `runtime/`.

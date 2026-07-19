# Namma Dashcam

Namma Dashcam is a split-runtime pothole detection system for the Arduino UNO Q.

- **MCU side (`mcu/`)**: samples the Modulino Movement IMU, estimates speed, detects candidate pothole events, and emits compact event packets.
- **Linux side (`linux/`)**: buffers webcam frames, aligns them with MCU events, verifies pothole evidence, persists bundles, and uploads verified incidents to an API.

## Architecture at a glance

1. Modulino Movement IMU streams accel/gyro samples on the MCU.
2. The MCU maintains a rolling motion window and computes candidate pothole features.
3. When the heuristic detector fires, the MCU emits a candidate event with timestamps, motion peaks, and speed context.
4. The Linux service receives that event over the bridge ingress path, picks nearby webcam frames, and runs lightweight visual rejection / confirmation rules.
5. Verified incidents are stored locally and uploaded with retry protection.

## Repository layout

```text
namma-dashcam/
  docs/
    architecture.md
    event-contract.md
    api-payload.md
    tuning-notes.md
  mcu/
    namma_dashcam.ino
    src/
      calibration.h
      debug_log.h
      event_packet.h
      filters.h
      gps.h
      gps.cpp
      motion_buffer.h
      pothole_detector.h
      pothole_detector.cpp
      pothole_features.h
      speed_estimator.h
      speed_estimator.cpp
      time_sync.h
  linux/
    pyproject.toml
    .python-version
    src/namma_dashcam/
      __init__.py
      alignment.py
      bridge.py
      camera.py
      config.py
      frame_buffer.py
      logging.py
      main.py
      storage.py
      time_sync.py
      upload_queue.py
      uploader.py
      verifier.py
    tests/
    systemd/
      namma-dashcam.service
  testdata/
    road-tests/
```

## What runs where

### MCU responsibilities

- deterministic IMU sampling
- startup calibration and gravity-baseline removal
- short-window speed estimation with optional GPS fusion
- rolling motion buffer maintenance
- candidate pothole detection and debounce logic
- event packet serialization for Linux handoff

### Linux responsibilities

- webcam capture and rolling frame buffer
- bridge ingress and event parsing
- Arduino-to-Linux time alignment
- visual verification / rejection heuristics
- evidence persistence and debug bundles
- upload queue and API retries

## Linux quick start

```bash
cd linux
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check src/
```

Configure the service with environment variables:

- `NAMMA_DASHCAM_API_BASE_URL`
- `NAMMA_DASHCAM_API_TOKEN`
- `NAMMA_DASHCAM_WEBCAM_DEVICE`
- `NAMMA_DASHCAM_BRIDGE_EVENT_PATH`
- `NAMMA_DASHCAM_STORAGE_DIR`

For local development without hardware, append newline-delimited JSON candidate events to the configured bridge event path.

## MCU bring-up

1. Connect the Modulino Movement over Qwiic/I2C.
2. Open `mcu/namma_dashcam.ino` in the Arduino IDE / CLI for UNO Q.
3. Keep the board stationary during startup calibration.
4. Watch serial logs for baseline acquisition and emitted candidate event packets.

## Current implementation status

This repository implements the V1 structure and software pipeline from the plan. Physical road tests, UNO Q bridge integration details, and camera tuning remain field-validation tasks.

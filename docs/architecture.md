# Namma Dashcam Architecture

## Split-runtime design

The Arduino UNO Q is used as a two-part system:

- **STM32U585 MCU** for deterministic sensing and event detection.
- **Linux MPU** for camera, storage, verification, and networking.

That split keeps sensor capture predictable while moving variable-latency work to Linux.

## Data flow

```text
Modulino Movement IMU
        |
        v
  MCU sampling loop
        |
        v
 motion ring buffer + filters + speed estimator
        |
        v
 heuristic pothole detector
        |
        v
  event packet serialization
        |
        v
 Bridge/RPC ingress on Linux
        |
        v
 frame alignment + verification heuristics
        |
        +--> rejected event bundle (saved for tuning)
        |
        v
 verified incident bundle
        |
        v
 upload queue --> custom API
```

## MCU modules

- `calibration.h`: startup baseline acquisition.
- `motion_buffer.h`: fixed-size rolling sample storage.
- `filters.h`: low-pass filtering, jerk estimation, and constrained integration.
- `speed_estimator.*`: IMU-only estimate with optional GPS correction.
- `pothole_features.h`: feature extraction from the rolling window.
- `pothole_detector.*`: thresholding, scoring, and debounce.
- `event_packet.h`: Linux handoff contract serializer.

## Linux modules

- `config.py`: typed settings sourced from env vars.
- `camera.py` + `frame_buffer.py`: webcam capture and rolling frame store.
- `bridge.py`: candidate-event ingestion from a bridge landing path.
- `time_sync.py` + `alignment.py`: Arduino timestamp alignment to Linux monotonic time.
- `verifier.py`: visual confirmation and explicit rejection reasons.
- `storage.py`: incident bundle persistence.
- `uploader.py` + `upload_queue.py`: API upload and offline retry.
- `main.py`: service orchestration.

## Event lifecycle

1. MCU samples accel/gyro and maintains a motion history window.
2. A shock-like pattern is turned into `PotholeFeatures`.
3. `PotholeDetector` enforces threshold + debounce rules.
4. The event packet is serialized to JSON and handed to Linux.
5. Linux estimates the MCU→Linux time offset, picks nearby frames, and scores the event.
6. Verification returns either:
   - `verified=true` with an evidence frame, or
   - `verified=false` with a rejection reason such as `no_frames`, `low_light`, `blurred`, or `speed_breaker_profile`.
7. Verified incidents are uploaded immediately; failures are queued on disk.

## Operational notes

- Accelerometer-only speed is treated as approximate.
- GPS is optional but authoritative when present.
- The bridge receiver uses a newline-delimited JSON landing file for development and testing; UNO Q bridge/RPC plumbing can write the same payloads into that path without changing the verifier pipeline.
- Every event, including rejected ones, can be persisted locally for tuning and replay.

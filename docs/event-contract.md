# MCU to Linux Candidate Event Contract

The MCU emits one JSON object per suspected pothole event.

## Payload

```json
{
  "event_id": 102,
  "arduino_timestamp_ms": 91827364,
  "event_type": "suspected_pothole",
  "speed_mps": 8.4,
  "gps_speed_mps": 8.9,
  "gps_available": true,
  "gps_latitude": 12.9716,
  "gps_longitude": 77.5946,
  "severity": 0.78,
  "confidence": 0.66,
  "vertical_peak_g": 2.3,
  "vertical_valley_g": -1.1,
  "jerk_peak_gps": 11.8,
  "gyro_peak_dps": 34.0,
  "event_duration_ms": 180.0,
  "window_pre_ms": 500,
  "window_post_ms": 700
}
```

## Required fields

- `event_id`: monotonically increasing MCU event identifier.
- `arduino_timestamp_ms`: `millis()` value captured at event detection time.
- `event_type`: currently `suspected_pothole`.
- `speed_mps`: fused MCU speed estimate.
- `gps_available`: whether a valid GPS fix was present.
- `severity`: normalized 0..1 event severity score.
- `confidence`: normalized 0..1 classifier confidence.
- `vertical_peak_g`: strongest upward vertical spike in the event window.
- `jerk_peak_gps`: maximum jerk magnitude across the window.
- `gyro_peak_dps`: strongest angular-rate spike in the window.
- `window_pre_ms` / `window_post_ms`: how much context the Linux verifier should fetch around the event time.

## Optional fields

- `gps_speed_mps`
- `gps_latitude`
- `gps_longitude`
- `vertical_valley_g`
- `event_duration_ms`

## Transport notes

- Development mode: newline-delimited JSON in the Linux bridge event path.
- Production mode: UNO Q bridge/RPC handler should emit the exact same JSON payload shape into the Linux ingress path.
- The Linux service treats the payload as append-only and backward-compatible: new optional fields may be added without breaking the verifier.

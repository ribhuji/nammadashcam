# Verified Incident API Payload

Only verified incidents are uploaded.

## JSON shape

```json
{
  "event_id": 102,
  "arduino_timestamp_ms": 91827364,
  "captured_at": "2026-07-19T10:20:30Z",
  "speed_mps": 10.1,
  "gps": {
    "available": true,
    "latitude": 12.9716,
    "longitude": 77.5946,
    "speed_mps": 9.8
  },
  "severity": 0.82,
  "verification_score": 0.91,
  "image_path": "evidence/event-102.jpg",
  "features": {
    "vertical_peak_g": 2.3,
    "vertical_valley_g": -1.1,
    "jerk_peak_gps": 11.8,
    "gyro_peak_dps": 34.0,
    "event_duration_ms": 180.0
  }
}
```

## Upload behavior

- If an evidence image exists, the Linux uploader sends multipart form data:
  - `metadata`: JSON payload
  - `image`: JPEG evidence file
- If no image exists, the payload is sent as plain JSON.
- Failed uploads are written to the local retry queue under `storage_dir/pending_uploads/`.

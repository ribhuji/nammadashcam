# Tuning Notes

## Initial MCU thresholds

- `speed_mps > 2.0`
- `vertical_peak_g > 1.8`
- `jerk_peak_gps > 8.0`
- `20ms < event_duration_ms < 250ms`
- `MIN_EVENT_GAP_MS = 1500`

## Initial Linux rejection rules

- reject `low_light` if road ROI brightness `< 40`
- reject `blurred` if Laplacian variance `< 55`
- reject `speed_breaker_profile` if horizontal edge dominance `> 0.72` and edge density `> 0.08`
- verify only when overall score `>= 0.55` and center darkening `>= 6`

## Field-tuning checklist

1. capture true pothole, speed breaker, braking, and rough-road examples
2. compare MCU event packet features against the saved evidence bundle
3. inspect rejection reasons in `verification.json`
4. adjust one threshold at a time and replay saved cases
5. prefer GPS-informed runs when validating speed-dependent logic

## Known V1 limitations

- IMU-only speed is approximate.
- Camera heuristics are conservative and can reject valid events in low light.
- The development bridge ingress uses JSONL; production bridge/RPC plumbing should preserve the same payload format.

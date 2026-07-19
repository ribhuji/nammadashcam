#include "pothole_detector.h"

#include "filters.h"

namespace {
float computeSeverity(const PotholeFeatures& features) {
  const float vertical_component = clampf(features.vertical_peak_g / 3.0f, 0.0f, 1.0f);
  const float jerk_component = clampf(features.jerk_peak_gps / 16.0f, 0.0f, 1.0f);
  const float gyro_component = clampf(features.gyro_peak_dps / 80.0f, 0.0f, 1.0f);
  return 0.5f * vertical_component + 0.35f * jerk_component + 0.15f * gyro_component;
}

float computeConfidence(const PotholeFeatures& features) {
  const float duration_component =
      1.0f - clampf((features.event_duration_ms - 120.0f) / 250.0f, 0.0f, 1.0f);
  const float speed_component = clampf(features.speed_mps / 12.0f, 0.0f, 1.0f);
  const float rebound_component = clampf(
      (features.vertical_peak_g - features.vertical_valley_g) / 3.5f,
      0.0f,
      1.0f);
  return 0.45f * duration_component + 0.2f * speed_component +
         0.35f * rebound_component;
}
}

bool PotholeDetector::isSuspectedPothole(const PotholeFeatures& features) {
  return features.speed_mps > 2.0f && features.vertical_peak_g > 1.8f &&
         features.jerk_peak_gps > 8.0f &&
         features.event_duration_ms > 20.0f &&
         features.event_duration_ms < 250.0f;
}

DetectionDecision PotholeDetector::evaluate(
    const PotholeFeatures& features,
    uint32_t now_ms) {
  DetectionDecision decision;
  decision.severity = computeSeverity(features);
  decision.confidence = computeConfidence(features);

  if (!isSuspectedPothole(features)) {
    return decision;
  }

  if (last_event_ms_ != 0 && (now_ms - last_event_ms_) < MIN_EVENT_GAP_MS) {
    return decision;
  }

  decision.triggered = true;
  last_event_ms_ = now_ms;
  return decision;
}

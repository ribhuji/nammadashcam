#pragma once

#include <Arduino.h>

#include "pothole_features.h"

const uint32_t MIN_EVENT_GAP_MS = 1500;

struct DetectionDecision {
  bool triggered = false;
  float severity = 0.0f;
  float confidence = 0.0f;
};

class PotholeDetector {
 public:
  DetectionDecision evaluate(const PotholeFeatures& features, uint32_t now_ms);
  static bool isSuspectedPothole(const PotholeFeatures& features);

 private:
  uint32_t last_event_ms_ = 0;
};

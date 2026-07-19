#pragma once

#include <math.h>

#include "filters.h"
#include "motion_buffer.h"

struct PotholeFeatures {
  float vertical_peak_g = 0.0f;
  float vertical_valley_g = 0.0f;
  float jerk_peak_gps = 0.0f;
  float gyro_peak_dps = 0.0f;
  float event_duration_ms = 0.0f;
  float speed_mps = 0.0f;
};

template <size_t Capacity>
PotholeFeatures extractPotholeFeatures(
    const MotionBuffer<Capacity>& buffer,
    size_t lookback_samples,
    float speed_mps) {
  PotholeFeatures features;
  features.speed_mps = speed_mps;

  if (buffer.empty()) {
    return features;
  }

  const size_t samples_to_scan =
      lookback_samples < buffer.size() ? lookback_samples : buffer.size();
  const size_t start = buffer.size() - samples_to_scan;
  const MotionSample& first = buffer.at(start);
  const MotionSample& last = buffer.at(buffer.size() - 1);
  features.vertical_peak_g = first.az_g;
  features.vertical_valley_g = first.az_g;

  MotionSample previous = first;
  for (size_t index = start; index < buffer.size(); ++index) {
    const MotionSample& sample = buffer.at(index);
    if (sample.az_g > features.vertical_peak_g) {
      features.vertical_peak_g = sample.az_g;
    }
    if (sample.az_g < features.vertical_valley_g) {
      features.vertical_valley_g = sample.az_g;
    }

    const float dt_s = (sample.t_ms - previous.t_ms) / 1000.0f;
    const float jerk_gps = fabsf(computeJerk(sample.az_g, previous.az_g, dt_s));
    if (jerk_gps > features.jerk_peak_gps) {
      features.jerk_peak_gps = jerk_gps;
    }

    const float gyro_magnitude = sqrtf(
        sample.gx_dps * sample.gx_dps +
        sample.gy_dps * sample.gy_dps +
        sample.gz_dps * sample.gz_dps);
    if (gyro_magnitude > features.gyro_peak_dps) {
      features.gyro_peak_dps = gyro_magnitude;
    }

    previous = sample;
  }

  features.event_duration_ms = static_cast<float>(last.t_ms - first.t_ms);
  return features;
}

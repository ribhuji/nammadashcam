#include "speed_estimator.h"

namespace {
constexpr float kGravityMps2 = 9.80665f;
}

SpeedEstimate SpeedEstimator::update(
    float longitudinal_accel_g,
    float dt_s,
    const GpsFix& gps) {
  const float bias_g = longitudinal_bias_.update(longitudinal_accel_g);
  const float dynamic_accel_mps2 =
      (longitudinal_accel_g - bias_g) * kGravityMps2;
  const float imu_speed = integrator_.updateLongitudinalSpeed(
      dynamic_accel_mps2,
      dt_s);

  SpeedEstimate estimate;
  estimate.imu_speed_mps = imu_speed;

  if (gps.available) {
    estimate.gps_used = true;
    estimate.fused_speed_mps = 0.8f * gps.speed_mps + 0.2f * imu_speed;
    integrator_.nudgeTo(estimate.fused_speed_mps, 0.35f);
  } else {
    estimate.gps_used = false;
    estimate.fused_speed_mps = imu_speed;
  }

  return estimate;
}

void SpeedEstimator::reset() {
  longitudinal_bias_.reset();
  integrator_.reset();
}

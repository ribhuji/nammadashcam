#pragma once

#include "filters.h"
#include "gps.h"

struct SpeedEstimate {
  float imu_speed_mps = 0.0f;
  float fused_speed_mps = 0.0f;
  bool gps_used = false;
};

class SpeedEstimator {
 public:
  SpeedEstimate update(float longitudinal_accel_g, float dt_s, const GpsFix& gps);
  void reset();

 private:
  LowPassFilter longitudinal_bias_{0.01f};
  ConstrainedIntegrator integrator_{0.05f};
};

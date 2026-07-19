#pragma once

#include <Arduino.h>

inline float clampf(float value, float minimum, float maximum) {
  if (value < minimum) {
    return minimum;
  }
  if (value > maximum) {
    return maximum;
  }
  return value;
}

class LowPassFilter {
 public:
  explicit LowPassFilter(float alpha = 0.02f) : alpha_(alpha) {}

  float update(float input) {
    if (!initialized_) {
      value_ = input;
      initialized_ = true;
      return value_;
    }

    value_ = value_ + alpha_ * (input - value_);
    return value_;
  }

  float value() const { return value_; }
  void reset(float value = 0.0f) {
    value_ = value;
    initialized_ = false;
  }

 private:
  float alpha_;
  bool initialized_ = false;
  float value_ = 0.0f;
};

class ConstrainedIntegrator {
 public:
  explicit ConstrainedIntegrator(float drag = 0.02f) : drag_(drag) {}

  float updateLongitudinalSpeed(float longitudinal_accel_mps2, float dt_s) {
    const float integrated = speed_mps_ + longitudinal_accel_mps2 * dt_s;
    speed_mps_ = integrated * (1.0f - drag_ * dt_s);
    speed_mps_ = clampf(speed_mps_, 0.0f, 55.0f);
    return speed_mps_;
  }

  void nudgeTo(float target_speed_mps, float blend_factor) {
    speed_mps_ = (1.0f - blend_factor) * speed_mps_ + blend_factor * target_speed_mps;
    speed_mps_ = clampf(speed_mps_, 0.0f, 55.0f);
  }

  void reset(float value = 0.0f) { speed_mps_ = value; }
  float value() const { return speed_mps_; }

 private:
  float drag_;
  float speed_mps_ = 0.0f;
};

inline float computeJerk(float current_g, float previous_g, float dt_s) {
  if (dt_s <= 0.0f) {
    return 0.0f;
  }
  return (current_g - previous_g) / dt_s;
}

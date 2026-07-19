#pragma once

#include <Arduino.h>
#include <math.h>

struct ImuReading {
  float ax;
  float ay;
  float az;
  float gx;
  float gy;
  float gz;
};

struct ImuBaseline {
  float ax = 0.0f;
  float ay = 0.0f;
  float az = 1.0f;
  float gx = 0.0f;
  float gy = 0.0f;
  float gz = 0.0f;
};

class CalibrationState {
 public:
  explicit CalibrationState(size_t required_samples = 200)
      : required_samples_(required_samples) {}

  void reset() {
    sample_count_ = 0;
    sums_[0] = sums_[1] = sums_[2] = 0.0f;
    sums_[3] = sums_[4] = sums_[5] = 0.0f;
    still_counter_ = 0;
    ready_ = false;
    baseline_ = ImuBaseline{};
  }

  bool update(const ImuReading& reading) {
    sums_[0] += reading.ax;
    sums_[1] += reading.ay;
    sums_[2] += reading.az;
    sums_[3] += reading.gx;
    sums_[4] += reading.gy;
    sums_[5] += reading.gz;
    sample_count_ += 1;

    if (sample_count_ < required_samples_) {
      return false;
    }

    const float denominator = static_cast<float>(sample_count_);
    baseline_.ax = sums_[0] / denominator;
    baseline_.ay = sums_[1] / denominator;
    baseline_.az = sums_[2] / denominator;
    baseline_.gx = sums_[3] / denominator;
    baseline_.gy = sums_[4] / denominator;
    baseline_.gz = sums_[5] / denominator;
    ready_ = true;
    return true;
  }

  bool ready() const { return ready_; }

  const ImuBaseline& baseline() const { return baseline_; }

  ImuReading apply(const ImuReading& reading) const {
    ImuReading corrected = reading;
    corrected.ax -= baseline_.ax;
    corrected.ay -= baseline_.ay;
    corrected.az -= baseline_.az - 1.0f;
    corrected.gx -= baseline_.gx;
    corrected.gy -= baseline_.gy;
    corrected.gz -= baseline_.gz;
    return corrected;
  }

  bool maybeRezero(
      const ImuReading& reading,
      float accel_threshold_g = 0.05f,
      float gyro_threshold_dps = 2.0f,
      size_t still_samples_required = 50) {
    const bool mostly_still = fabsf(reading.ax - baseline_.ax) < accel_threshold_g &&
                              fabsf(reading.ay - baseline_.ay) < accel_threshold_g &&
                              fabsf(reading.az - baseline_.az) < accel_threshold_g &&
                              fabsf(reading.gx - baseline_.gx) < gyro_threshold_dps &&
                              fabsf(reading.gy - baseline_.gy) < gyro_threshold_dps &&
                              fabsf(reading.gz - baseline_.gz) < gyro_threshold_dps;

    if (!mostly_still) {
      still_counter_ = 0;
      return false;
    }

    still_counter_ += 1;
    if (still_counter_ < still_samples_required) {
      return false;
    }

    baseline_.ax = 0.98f * baseline_.ax + 0.02f * reading.ax;
    baseline_.ay = 0.98f * baseline_.ay + 0.02f * reading.ay;
    baseline_.az = 0.98f * baseline_.az + 0.02f * reading.az;
    baseline_.gx = 0.95f * baseline_.gx + 0.05f * reading.gx;
    baseline_.gy = 0.95f * baseline_.gy + 0.05f * reading.gy;
    baseline_.gz = 0.95f * baseline_.gz + 0.05f * reading.gz;
    still_counter_ = 0;
    return true;
  }

 private:
  size_t required_samples_;
  size_t sample_count_ = 0;
  size_t still_counter_ = 0;
  float sums_[6] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
  bool ready_ = false;
  ImuBaseline baseline_;
};

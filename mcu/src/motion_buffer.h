#pragma once

#include <Arduino.h>
#include <array>

struct MotionSample {
  uint32_t t_ms;
  float ax_g;
  float ay_g;
  float az_g;
  float gx_dps;
  float gy_dps;
  float gz_dps;
};

template <size_t Capacity>
class MotionBuffer {
 public:
  void clear() {
    head_ = 0;
    size_ = 0;
  }

  void push(const MotionSample& sample) {
    samples_[head_] = sample;
    head_ = (head_ + 1) % Capacity;
    if (size_ < Capacity) {
      size_ += 1;
    }
  }

  size_t size() const { return size_; }
  bool empty() const { return size_ == 0; }
  bool full() const { return size_ == Capacity; }
  constexpr size_t capacity() const { return Capacity; }

  const MotionSample& at(size_t index_from_oldest) const {
    const size_t start = (head_ + Capacity - size_) % Capacity;
    const size_t physical_index = (start + index_from_oldest) % Capacity;
    return samples_[physical_index];
  }

  const MotionSample& latest() const {
    const size_t latest_index = (head_ + Capacity - 1) % Capacity;
    return samples_[latest_index];
  }

 private:
  std::array<MotionSample, Capacity> samples_{};
  size_t head_ = 0;
  size_t size_ = 0;
};

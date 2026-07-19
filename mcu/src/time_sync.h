#pragma once

#include <Arduino.h>

struct TimeSyncSample {
  uint32_t arduino_ms;
  uint64_t linux_ms;
};

#pragma once

#include <Arduino.h>

inline void debugLogLine(const String& message) {
  Serial.println(message);
}

inline void debugLogValue(const String& label, float value, uint8_t decimals = 3) {
  Serial.print(label);
  Serial.print(':');
  Serial.println(value, decimals);
}

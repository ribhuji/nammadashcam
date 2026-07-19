#pragma once

#include <Arduino.h>

#include "gps.h"
#include "pothole_features.h"

struct EventPacket {
  uint32_t event_id = 0;
  uint32_t arduino_timestamp_ms = 0;
  float speed_mps = 0.0f;
  bool gps_available = false;
  float gps_speed_mps = 0.0f;
  double gps_latitude = 0.0;
  double gps_longitude = 0.0;
  float severity = 0.0f;
  float confidence = 0.0f;
  PotholeFeatures features;
  uint16_t window_pre_ms = 500;
  uint16_t window_post_ms = 700;

  String toJson() const {
    String json = "{";
    json += "\"event_id\":" + String(event_id);
    json += ",\"arduino_timestamp_ms\":" + String(arduino_timestamp_ms);
    json += ",\"event_type\":\"suspected_pothole\"";
    json += ",\"speed_mps\":" + String(speed_mps, 3);
    json += ",\"gps_speed_mps\":" + String(gps_speed_mps, 3);
    json += ",\"gps_available\":" + String(gps_available ? "true" : "false");
    json += ",\"gps_latitude\":" + String(gps_latitude, 6);
    json += ",\"gps_longitude\":" + String(gps_longitude, 6);
    json += ",\"severity\":" + String(severity, 3);
    json += ",\"confidence\":" + String(confidence, 3);
    json += ",\"vertical_peak_g\":" + String(features.vertical_peak_g, 3);
    json += ",\"vertical_valley_g\":" + String(features.vertical_valley_g, 3);
    json += ",\"jerk_peak_gps\":" + String(features.jerk_peak_gps, 3);
    json += ",\"gyro_peak_dps\":" + String(features.gyro_peak_dps, 3);
    json += ",\"event_duration_ms\":" + String(features.event_duration_ms, 1);
    json += ",\"window_pre_ms\":" + String(window_pre_ms);
    json += ",\"window_post_ms\":" + String(window_post_ms);
    json += "}";
    return json;
  }
};

inline EventPacket buildEventPacket(
    uint32_t event_id,
    uint32_t timestamp_ms,
    float speed_mps,
    const GpsFix& gps,
    float severity,
    float confidence,
    const PotholeFeatures& features) {
  EventPacket packet;
  packet.event_id = event_id;
  packet.arduino_timestamp_ms = timestamp_ms;
  packet.speed_mps = speed_mps;
  packet.gps_available = gps.available;
  packet.gps_speed_mps = gps.available ? gps.speed_mps : speed_mps;
  packet.gps_latitude = gps.latitude;
  packet.gps_longitude = gps.longitude;
  packet.severity = severity;
  packet.confidence = confidence;
  packet.features = features;
  return packet;
}

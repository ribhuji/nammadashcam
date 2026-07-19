#include "Modulino.h"

#include "src/calibration.h"
#include "src/debug_log.h"
#include "src/event_packet.h"
#include "src/gps.h"
#include "src/motion_buffer.h"
#include "src/pothole_detector.h"
#include "src/pothole_features.h"
#include "src/speed_estimator.h"

namespace {
constexpr uint32_t kSampleIntervalMs = 20;
constexpr size_t kMotionBufferCapacity = 160;
constexpr size_t kFeatureLookbackSamples = 24;
}

ModulinoMovement movement;
CalibrationState calibration(150);
MotionBuffer<kMotionBufferCapacity> motion_buffer;
NullGpsProvider gps_provider;
SpeedEstimator speed_estimator;
PotholeDetector pothole_detector;

uint32_t next_sample_ms = 0;
uint32_t last_loop_ms = 0;
uint32_t next_event_id = 1;

ImuReading readMovementSample() {
  movement.update();

  ImuReading reading;
  reading.ax = movement.getX();
  reading.ay = movement.getY();
  reading.az = movement.getZ();
  reading.gx = movement.getRoll();
  reading.gy = movement.getPitch();
  reading.gz = movement.getYaw();
  return reading;
}

void emitCandidateEvent(const EventPacket& packet) {
  Serial.println(packet.toJson());
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  Modulino.begin();
  movement.begin();
  calibration.reset();
  speed_estimator.reset();
  debugLogLine("namma-dashcam: startup");
  debugLogLine("hold vehicle steady for IMU calibration");
}

void loop() {
  const uint32_t now_ms = millis();
  if (now_ms < next_sample_ms) {
    return;
  }
  next_sample_ms = now_ms + kSampleIntervalMs;

  const ImuReading raw = readMovementSample();

  if (!calibration.ready()) {
    if (calibration.update(raw)) {
      debugLogLine("calibration complete");
      debugLogValue("baseline.ax", calibration.baseline().ax);
      debugLogValue("baseline.ay", calibration.baseline().ay);
      debugLogValue("baseline.az", calibration.baseline().az);
    }
    return;
  }

  calibration.maybeRezero(raw);

  const ImuReading corrected = calibration.apply(raw);
  MotionSample sample;
  sample.t_ms = now_ms;
  sample.ax_g = corrected.ax;
  sample.ay_g = corrected.ay;
  sample.az_g = corrected.az;
  sample.gx_dps = corrected.gx;
  sample.gy_dps = corrected.gy;
  sample.gz_dps = corrected.gz;
  motion_buffer.push(sample);

  float dt_s = 0.02f;
  if (last_loop_ms != 0) {
    dt_s = (now_ms - last_loop_ms) / 1000.0f;
  }
  last_loop_ms = now_ms;

  const GpsFix gps = gps_provider.currentFix();
  const SpeedEstimate speed = speed_estimator.update(corrected.ax, dt_s, gps);
  const PotholeFeatures features = extractPotholeFeatures(
      motion_buffer,
      kFeatureLookbackSamples,
      speed.fused_speed_mps);
  const DetectionDecision decision = pothole_detector.evaluate(features, now_ms);

  if (!decision.triggered) {
    return;
  }

  const EventPacket packet = buildEventPacket(
      next_event_id++,
      now_ms,
      speed.fused_speed_mps,
      gps,
      decision.severity,
      decision.confidence,
      features);

  debugLogLine("candidate pothole detected");
  debugLogValue("severity", decision.severity);
  debugLogValue("confidence", decision.confidence);
  emitCandidateEvent(packet);
}

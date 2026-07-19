#include <Arduino.h>
#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

/*
 * UNO Q MCU motion publisher.
 *
 * Reads acceleration/gyro data via Arduino_Modulino and publishes each sample to
 * Linux-side Python over Arduino Router Bridge RPC.
 */

ModulinoMovement movement;

static const uint32_t kBridgeBootDelayMs = 1000UL;
static const uint32_t kSamplePeriodMs = 100UL;

float g_ax = 0.0F;
float g_ay = 0.0F;
float g_az = 0.0F;
float g_roll = 0.0F;
float g_pitch = 0.0F;
float g_yaw = 0.0F;

void setup() {
  Serial.begin(115200);
  const uint32_t serial_start_ms = millis();
  while ((!Serial) && ((millis() - serial_start_ms) < 2000UL)) {
    delay(1U);
  }

  /* Router Bridge handshake: initialize MCU<->Linux RPC transport. */
  Bridge.begin();
  delay(kBridgeBootDelayMs);

  Modulino.begin();
  movement.begin();

  Serial.println("MODULINO_MOVEMENT_BRIDGE_READY");
}

void loop() {
  movement.update();

  g_ax = movement.getX();
  g_ay = movement.getY();
  g_az = movement.getZ();

  g_roll = movement.getRoll();
  g_pitch = movement.getPitch();
  g_yaw = movement.getYaw();

  const uint32_t now_ms = millis();

  /* Bridge RPC publish: send normalized raw motion sample to Linux callback. */
  Bridge.call("motion_sample", g_ax, g_ay, g_az, g_roll, g_pitch, g_yaw, now_ms);

  delay(kSamplePeriodMs);
}

#include <Arduino.h>
#include <Arduino_Modulino.h>

/*
 * Bring-up sketch to validate Modulino Movement visibility on UNO Q MCU side.
 * Uses official Arduino_Modulino API exactly as intended for this hardware.
 */

ModulinoMovement movement;

float g_ax = 0.0F;
float g_ay = 0.0F;
float g_az = 0.0F;
float g_roll = 0.0F;
float g_pitch = 0.0F;
float g_yaw = 0.0F;

void setup() {
  Serial.begin(115200);
  const uint32_t start_ms = millis();
  while ((!Serial) && ((millis() - start_ms) < 2000UL)) {
    delay(1U);
  }

  Modulino.begin();
  movement.begin();

  Serial.println("MODULINO_MOVEMENT_READY");
}

void loop() {
  movement.update();

  g_ax = movement.getX();
  g_ay = movement.getY();
  g_az = movement.getZ();

  g_roll = movement.getRoll();
  g_pitch = movement.getPitch();
  g_yaw = movement.getYaw();

  Serial.print("A:");
  Serial.print(g_ax, 3);
  Serial.print(",");
  Serial.print(g_ay, 3);
  Serial.print(",");
  Serial.print(g_az, 3);
  Serial.print("|G:");
  Serial.print(g_roll, 1);
  Serial.print(",");
  Serial.print(g_pitch, 1);
  Serial.print(",");
  Serial.println(g_yaw, 1);

  delay(200U);
}

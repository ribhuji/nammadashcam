# Firmware (UNO Q MCU Side)

This folder contains Arduino firmware used on the UNO Q microcontroller side for sensor acquisition.

## Layout

- `unoq_dashcam_mcu/unoq_dashcam_mcu.ino` — Modulino Movement publisher that sends raw motion samples to Linux via Arduino Router Bridge RPC.

## Dependencies

This project does **not** vendor Arduino libraries in git. Team members should install them with Arduino CLI.

Required components:

- Board core: `arduino:zephyr`
- Board FQBN: `arduino:zephyr:unoq`
- Library: `Arduino_Modulino` (pulls required transitive sensor libraries)
- Library: `Arduino_RouterBridge`

## One-time setup (Arduino CLI)

```bash
arduino-cli core update-index
arduino-cli core install arduino:zephyr
arduino-cli lib update-index
arduino-cli lib install "Arduino_Modulino"
arduino-cli lib install "Arduino_RouterBridge"
```

## Build

```bash
arduino-cli compile --fqbn arduino:zephyr:unoq firmware/unoq_dashcam_mcu
```

## Flash (USB)

First list ports:

```bash
arduino-cli board list
```

Then upload (replace port as needed):

```bash
arduino-cli upload -p /dev/cu.usbmodemXXXX --fqbn arduino:zephyr:unoq firmware/unoq_dashcam_mcu
```

## Optional USB serial monitor (debug only)

```bash
arduino-cli monitor -p /dev/cu.usbmodemXXXX -c baudrate=115200
```

Expected startup log:

- `MODULINO_MOVEMENT_BRIDGE_READY`

Motion samples are sent over Router Bridge RPC (`motion_sample`) rather than USB serial text lines.

## UNO Q Bridge runtime handshake

1. Flash MCU firmware from this directory.
2. On Linux side, run Python with `--motion-backend bridge`.
3. MCU publishes `motion_sample` callbacks with argument order:
   - `ax_g, ay_g, az_g, roll_dps, pitch_dps, yaw_dps, timestamp_ms`
4. Python receives callbacks and applies pothole heuristics.

## Notes for contributors

- Use the official `Arduino_Modulino` API for UNO Q + Modulino Movement compatibility.
- Use `Arduino_RouterBridge` for MCU→Linux communication on UNO Q internal path.
- Keep firmware deterministic (fixed update cadence, no dynamic allocation in hot paths).
- Keep Linux-side Python runtime and MCU firmware responsibilities separate.

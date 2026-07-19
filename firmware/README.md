# Firmware (UNO Q MCU Side)

This folder contains Arduino firmware used on the UNO Q microcontroller side for sensor acquisition.

## Layout

- `unoq_dashcam_mcu/unoq_dashcam_mcu.ino` — Modulino Movement bring-up sketch using the official Arduino Modulino library.

## Dependencies

This project does **not** vendor Arduino libraries in git. Team members should install them with Arduino CLI.

Required components:

- Board core: `arduino:zephyr`
- Board FQBN: `arduino:zephyr:unoq`
- Library: `Arduino_Modulino` (pulls required transitive sensor libraries)

## One-time setup (Arduino CLI)

```bash
arduino-cli core update-index
arduino-cli core install arduino:zephyr
arduino-cli lib update-index
arduino-cli lib install "Arduino_Modulino"
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

## Serial monitor

```bash
arduino-cli monitor -p /dev/cu.usbmodemXXXX -c baudrate=115200
```

Expected output format:

- `MODULINO_MOVEMENT_READY`
- `A:<ax>,<ay>,<az>|G:<roll>,<pitch>,<yaw>`

## Notes for contributors

- Use the official `Arduino_Modulino` API for UNO Q + Modulino Movement compatibility.
- Keep firmware deterministic (fixed update cadence, no dynamic allocation in hot paths).
- Keep Linux-side Python runtime and MCU firmware responsibilities separate.

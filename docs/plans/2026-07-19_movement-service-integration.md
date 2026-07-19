# Movement Service Integration Plan

## Overview
Integrate the additive movement serial sidecar into `/home/dookie/nammadashcam` while keeping the movement code alongside the repo's existing service modules under `src/pothole_dashcam/services/`.

## Mismatch from Original Plan
The original movement-service plan targeted a different repo layout (`linux/tools/movement_service/`) and an existing bridge-file verifier pipeline. This repo instead exposes modular Python services under `src/pothole_dashcam/services/` and does not yet include the verifier runtime.

Implementation in this repo should preserve the original plan's intent while fitting the current structure:
- keep the movement code with the other service modules
- keep a dedicated movement entrypoint
- avoid changing the current camera/inference bootstrap flow
- avoid adding third-party serial dependencies by using stdlib serial handling

## Phase 1: Add service-local movement skeleton
- [x] Add a dedicated movement entrypoint at `src/pothole_dashcam/movement_main.py`.
- [x] Add movement-specific service modules under `src/pothole_dashcam/services/`.
- [x] Add a movement event model under `src/pothole_dashcam/models/`.
- [x] Existing bootstrap entrypoint in `src/pothole_dashcam/main.py` remains untouched.

## Phase 2: Add parsing and bridge-file writing
- [x] Plain-text serial lines are ignored safely.
- [x] Valid MCU JSON lines normalize into a slim `MovementEvent`.
- [x] Bridge sink writes one compact JSON object per line.
- [x] Compatibility payload preserves required and extra raw fields.

## Phase 3: Add stdlib serial source and runtime loop
- [x] Serial source reads from the configured device and timestamps lines.
- [x] Service reconnects after disconnects or read failures.
- [x] Configuration is loaded from movement-specific environment variables.
- [x] Existing repo services remain usable without movement sidecar changes.

## Phase 4: Tests, docs, and service definition
- [x] Tests cover parser, sink, and reconnect behavior.
- [x] README documents movement sidecar usage.
- [x] A dedicated systemd unit is added.
- [x] Lint and tests pass.

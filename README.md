# nammadashcam

Python-first hackathon bootstrap for a collaboration-ready pothole detection pipeline on Arduino UNO Q Linux side.

## Objective
Build a modular service flow for:

- accelerometer-triggered event intake,
- camera frame retrieval,
- pothole inference,
- evidence upload.

The current commit provides contracts and stubs so teammates can work in parallel without blocking each other.

## High-Level Architecture

```text
Accel Event Producer -> Event Consumer -> Camera Service -> Inference Service -> Upload Service
```

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
pytest -q
PYTHONPATH=src python -m pothole_dashcam.main
```

## Team Workflow

- Branch naming: `feat/<module>-<name>`
- Open PRs early and keep them small.
- Run lint and smoke tests before pushing.

### Informal module ownership

- Teammate A: accelerometer integration contract
- Teammate B: camera pipeline
- Teammate C: inference
- Teammate D: cloud upload

## Current Status

- Lean bootstrap scaffold complete.
- Interface contracts and placeholder implementations present.
- CI baseline configured for lint + smoke tests.

## Next Milestones

1. Implement one end-to-end vertical slice with mock data.
2. Replace accelerometer adapter stub with teammate implementation.
3. Integrate camera capture path and select best frame.
4. Connect inference model and upload backend.

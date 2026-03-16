# ResilienceSim

ResilienceSim is a Python-based civil protection infrastructure simulator for two fictional countries under cascading crises. It models disruption, recovery, resource allocation, consequence propagation, optional humanitarian narration, and an optional vision adapter for scenario annotation.

## What It Demonstrates

- Dependency-driven infrastructure simulation
- Multi-agent recovery logic with resource constraints
- Streamlit dashboard for scenario playback and KPI monitoring
- Optional AI narration for humanitarian turn summaries
- Optional YOLOv8 adapter for civilian infrastructure annotation

## Current Status

- Phase 1: Core engine complete
- Phase 2: Scenario builder complete
- Phase 3: Dashboard code complete
- Phase 4: Vision adapter complete as an optional module
- Phase 5: Narrator complete as an optional module
- Phase 6: RL environment and wrapper scaffolded

## Project Structure

- `engine/`: world loading, turn engine, consequences, scenario builder
- `agents/`: rule agent, PettingZoo environment, RL wrapper
- `ui/`: dashboard panels and controls
- `vision/`: optional YOLOv8 detector
- `ai_narrator/`: optional Claude narrator
- `data/scenarios/`: hand-authored and generated scenarios
- `tests/`: phase-based test suites

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Test Suite

```bash
python -m pytest -q tests/test_phase1.py tests/test_phase2.py tests/test_phase3.py tests/test_phase4.py tests/test_phase5.py tests/test_phase6.py
```

## Safety Framing

This project is a fictional civil-protection and resilience simulator. It does not model weapons, targeting, strike planning, or real-world military operations.

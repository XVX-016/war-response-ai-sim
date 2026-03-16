# ResilienceSim v1 — System Architecture

> **Read this file before writing any code.**
> It defines module responsibilities, data flow, contracts, and rules every module must follow.

---

## What This System Is

ResilienceSim is a **civil protection / infrastructure resilience simulator**.
Two fictional nations (Auria and Boros) each manage a set of civilian assets
(power, water, hospitals, etc.) under disruption. Rule-based agents take
non-weaponised actions (repair, evacuate, reinforce) to stabilise their nation.
A consequence engine models cascading failures. A Streamlit dashboard shows
live KPIs, the grid map, and a turn event log.

**This system does not model weapons, targeting, combat, or military operations.**

---

## Module Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    app.py  (Streamlit UI)                        │
│  Left: scenario picker + turn controls                           │
│  Main: grid map with asset overlays + disruption heat colours    │
│  Right: KPI panels, resource bars, event log, consequence badges │
└───────────────────────────┬─────────────────────────────────────┘
                            │  reads ScenarioState, calls step_simulation()
              ┌─────────────▼──────────────┐
              │   engine/turn_engine.py    │
              │   step_simulation()        │
              │   Orchestrates one turn:   │
              │   actions → damage →       │
              │   consequences → KPIs →    │
              │   end-condition check      │
              └──┬──────────┬─────────────┘
                 │          │
       ┌─────────▼──┐  ┌────▼──────────────────────┐
       │ engine/    │  │  engine/consequence.py     │
       │ world.py   │  │  compute_consequences()    │
       │            │  │  update_population_zones() │
       │ load_scen- │  │  check_end_conditions()    │
       │ ario()     │  └────────────────────────────┘
       │ WorldGrid  │
       └────────────┘
                 │
       ┌─────────▼──────────────────────────────────┐
       │          agents/rule_agent.py               │
       │  select_actions(state, actor_id)            │
       │  Returns List[Action] each turn             │
       │  Priority: config.ASSET_PRIORITY order      │
       └─────────────────────────────────────────────┘

       ┌──────────────────────────┐
       │  vision/detector.py      │  ← Optional, standalone adapter
       │  detect(image) →         │    used only for scenario building
       │  DetectionResult         │    NOT called during simulation turns
       └──────────────────────────┘

       ┌──────────────────────────┐
       │  ai_narrator/narrator.py │  ← Optional, standalone adapter
       │  generate_narrative()    │    called by turn_engine if API key set
       └──────────────────────────┘
```

---

## Data Flow — One Turn

```
1.  app.py (or test) calls:
      turn_result = step_simulation(state, actions)

2.  turn_engine.step_simulation(state, actions):
      a. Validate all Action objects (schemas.Action)
      b. Check each action's resource cost (ResourceStock.can_afford)
      c. Deduct resources (ResourceStock.deduct)
      d. Apply immediate effects (repair hp, reinforce flag, evacuate)
      e. Tick pending multi-turn actions (PendingAction.turns_remaining -= 1)
      f. Complete any actions that reached turns_remaining == 0
      g. Apply exogenous events (random, per config.EXOGENOUS_EVENTS)
      h. Propagate dependency penalties (consequence.apply_dependency_penalties)
      i. Apply degradation_rate to applicable assets (config.ASSET_TYPES)
      j. Recompute resource resupply (reduced if transport_hub degraded)
      k. Call consequence.compute_consequences → active_consequences dict
      l. Call consequence.update_population_zones → zone service_coverage, displaced
      m. Call consequence.check_end_conditions → end_condition string or None
      n. Compute KPI snapshots (service_coverage_score, total_displaced)
      o. Optionally call narrator.generate_narrative → TurnResult.narrative
      p. Emit all SimEvents into state.event_log
      q. Return TurnResult (schemas.TurnResult)

3.  app.py reads TurnResult.new_state to re-render UI
4.  rule_agent.select_actions(new_state, nation) → List[Action] for next turn
```

---

## Public Interface (the 4 functions every module outside engine should use)

```python
# engine/world.py
state: ScenarioState = load_scenario(path: str | Path) -> ScenarioState

# engine/turn_engine.py
result: TurnResult = step_simulation(state: ScenarioState, actions: List[Action]) -> TurnResult

# agents/rule_agent.py
actions: List[Action] = select_actions(state: ScenarioState, actor_id: str) -> List[Action]

# app.py / ui serialisation
render_data: dict = render_state(state: ScenarioState) -> dict
```

---

## Module Contracts

### engine/world.py
- **Exports:** `load_scenario(path) -> ScenarioState`, `WorldGrid` class
- Reads scenario JSON from `data/scenarios/`
- Auto-fills `health`, `max_health`, `is_civilian`, `is_critical` from `config.ASSET_TYPES`
- Auto-fills `ResourceStock.stocks` from `config.RESOURCE_TYPES["starting"]`
- **Never** calls agents, narrator, or consequence directly
- `WorldGrid` holds the 2D grid array; each cell stores terrain tag + list of asset IDs

### engine/turn_engine.py
- **Exports:** `step_simulation(state, actions) -> TurnResult`
- Receives a **copy** of state (use `state.model_copy(deep=True)` at entry)
- Mutates the copy, never the original
- Injects consequence and narrator as optional dependencies (pass `None` to disable)
- Sequence must follow step 2a–2q above exactly

### engine/consequence.py
- **Exports:**
  - `apply_dependency_penalties(state) -> List[SimEvent]`
  - `compute_consequences(state) -> Dict[str, List[str]]`
  - `update_population_zones(state) -> List[SimEvent]`
  - `check_end_conditions(state) -> Dict[str, str]`
- **All functions are pure** — they receive state and return values/events
- They do NOT mutate state; turn_engine applies returned values
- Uses `config.DEPENDENCY_GRAPH`, `config.CONSEQUENCE_MAP`, `config.END_CONDITIONS`

### agents/rule_agent.py
- **Exports:** `select_actions(state, actor_id) -> List[Action]`
- Ranks degraded assets by `config.ASSET_PRIORITY`
- Checks `ResourceStock.can_afford` before emitting any action
- Returns empty list if no affordable action is available
- Never imports turn_engine or consequence (read-only access to state)

### vision/detector.py
- **Exports:** `YOLOv8Detector` class with `detect(image_path) -> DetectionResult`
- Used **only** for scenario building / map annotation
- Never called during simulation turns
- Falls back gracefully to pretrained weights if fine-tuned not found
- Maps YOLO class names → `config.ASSET_TYPES` keys via `config.YOLO_CLASS_MAP`

### ai_narrator/narrator.py
- **Exports:** `ClaudeNarrator` class with `generate_narrative(turn_result) -> str`
- Returns `""` silently if `ANTHROPIC_API_KEY` not set or `DISABLE_NARRATOR=true`
- Prompt must instruct model to describe humanitarian/recovery framing only
- Max 3 sentences per turn

---

## Scenario JSON Format  (`data/scenarios/*.json`)

```json
{
  "name": "Scenario Name",
  "description": "Short description of the crisis",
  "seed": 42,
  "grid_rows": 20,
  "grid_cols": 20,
  "nations": ["Auria", "Boros"],
  "assets": [
    {
      "id": "auria_hospital_01",
      "name": "Central Hospital",
      "nation": "Auria",
      "asset_type": "hospital",
      "row": 4,
      "col": 5,
      "starting_health": 60
    }
  ],
  "population_zones": [
    {
      "id": "auria_zone_north",
      "name": "Northern Districts",
      "nation": "Auria",
      "row": 3, "col": 4,
      "population": 120000,
      "served_by_asset_ids": ["auria_hospital_01", "auria_power_01"]
    }
  ],
  "starting_disruptions": [
    { "asset_id": "auria_power_01", "damage": 50 },
    { "asset_id": "boros_transport_01", "damage": 35 }
  ],
  "exogenous_event_overrides": {
    "earthquake": { "probability": 0.0 }
  }
}
```

Fields `health`, `max_health`, `is_civilian`, `is_critical` are auto-filled from
`config.ASSET_TYPES` — do NOT put them in JSON. `starting_health` overrides the
auto-fill only if explicitly set.

---

## Dependency Graph (quick reference)

See `config.DEPENDENCY_GRAPH` for the full definition.
Key chains:

```
power_plant ──► hospital (if power degraded → hospital loses 5HP/turn)
power_plant ──► water_treatment
power_plant ──► telecom_tower
power_plant ──► shelter
water_treatment ──► hospital
telecom_tower ──► command_center
transport_hub ──► water_treatment (pumping chemicals)
transport_hub ──► fuel_depot (deliveries)
fuel_depot ──► transport_hub (vehicles need fuel — circular, capped)
```

---

## End Conditions

| Condition | Trigger | Per-nation |
|-----------|---------|-----------|
| `stabilised` | All critical assets ≥ 50 HP for 3 consecutive turns | Yes |
| `collapsed` | Nation-wide service_coverage_score < 0.20 | Yes |
| `timeout` | `turn == MAX_TURNS` | Both |

The simulation stops when **both** nations have an end condition, or on timeout.

---

## Key Rules for All Code

1. **Import config, not hardcode.** Never write `max_health = 100` — use `config.ASSET_TYPES[t]["max_health"]`.
2. **Use schemas.** Any data crossing a module boundary must be a Pydantic model from `schemas.py`.
3. **No circular imports.** Dependency order: `config → schemas → world → consequence → turn_engine → agents → app`.
4. **consequence.py is pure.** It returns values and events; turn_engine applies them.
5. **step_simulation works on a deep copy.** The caller's state object is never mutated.
6. **Vision is optional.** The entire simulation must run without `models/` directory.
7. **Narrator is optional.** The entire simulation must run without `ANTHROPIC_API_KEY`.
8. **Log with loguru.** `from loguru import logger` everywhere except app.py (use `st.write`).
9. **Determinism.** Given the same `scenario_seed` and action sequence, state history must be identical. Use `random.seed(state.scenario_seed + state.turn)` for exogenous events.
10. **Never model weapons or targeting.** All asset types and actions must remain civilian/humanitarian.

# ── ResilienceSim v1 ── engine/turn_engine.py ────────────────────────────────
# Responsibilities:
#   - step_simulation(state, actions) -> TurnResult
#   - Orchestrates steps 2a–2q from ARCHITECTURE.md in order
#   - Works on a deep copy of state; never mutates the caller's object
#
# Import order: config → schemas → consequence (no agents, no narrator direct import)

from __future__ import annotations

import random
from typing import Dict, List, Optional

from loguru import logger

import config
from schemas import (
    Action,
    PendingAction,
    ScenarioState,
    SimEvent,
    TurnResult,
)
from engine import consequence as csq


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _validate_action(action: Action, state: ScenarioState) -> Optional[str]:
    """
    Returns an error string if the action is invalid, else None.
    Checks: action_type exists, target exists, resource affordability.
    """
    if action.action_type not in config.ACTION_TYPES:
        return f"Unknown action_type '{action.action_type}'"

    if action.actor_nation not in state.nations:
        return f"Unknown actor_nation '{action.actor_nation}'"

    act_cfg = config.ACTION_TYPES[action.action_type]
    resources = state.resources.get(action.actor_nation)

    # Target asset check
    if action.target_asset_id:
        target = state.get_asset(action.target_asset_id)
        if target is None:
            return f"Target asset '{action.target_asset_id}' not found"
        if target.is_destroyed and action.action_type not in ("inspect",):
            return f"Target asset '{action.target_asset_id}' is destroyed — cannot act on it"
        if target.asset_type not in act_cfg["valid_targets"]:
            return (
                f"Action '{action.action_type}' not valid on asset type "
                f"'{target.asset_type}'. Valid: {act_cfg['valid_targets']}"
            )

    # Resource affordability
    if resources and not resources.can_afford(act_cfg["cost"]):
        return (
            f"Insufficient resources for '{action.action_type}': "
            f"need {act_cfg['cost']}, have {resources.stocks}"
        )

    return None


def _apply_immediate_action(
    action: Action,
    state: ScenarioState,
    events: List[SimEvent],
) -> None:
    """
    Apply the immediate effect of a completed action to state.
    Called both for instant actions (turns_to_complete=1) and on multi-turn completion.
    Mutates state in-place (state is already a deep copy inside step_simulation).
    """
    act_cfg = config.ACTION_TYPES[action.action_type]
    nation  = action.actor_nation

    if action.action_type == "repair":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            hp_before = asset.health
            asset.apply_repair(float(act_cfg["hp_restored"]))
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "action_complete",
                nation      = nation,
                asset_id    = asset.id,
                description = (
                    f"Repair complete: {asset.name} restored "
                    f"{asset.health - hp_before:.0f} HP (→ {asset.health:.0f})"
                ),
                tags        = ["repair"],
                severity    = "info",
            ))

    elif action.action_type == "reinforce":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            asset.is_reinforced = True
            asset.reinforced_turns_remaining = 3
            # Also update state.reinforcements tracker
            state.reinforcements.setdefault(nation, {})[asset.id] = 3
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "action_complete",
                nation      = nation,
                asset_id    = asset.id,
                description = f"Reinforcement applied: {asset.name} hardened for 3 turns",
                tags        = ["reinforce"],
                severity    = "info",
            ))

    elif action.action_type == "restore_power":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            hp_before = asset.health
            asset.apply_repair(float(act_cfg["hp_restored"]))
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "action_complete",
                nation      = nation,
                asset_id    = asset.id,
                description = (
                    f"Generator deployed: {asset.name} power restored "
                    f"+{asset.health - hp_before:.0f} HP (→ {asset.health:.0f})"
                ),
                tags        = ["restore_power"],
                severity    = "info",
            ))

    elif action.action_type == "evacuate":
        zone = state.get_zone(action.target_zone_id)
        if zone:
            moved = min(int(zone.population * 0.10), zone.population - zone.displaced)
            zone.displaced = max(zone.displaced - moved, 0)   # evacuation REDUCES displacement
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "action_complete",
                nation      = nation,
                zone_id     = zone.id,
                description = (
                    f"Evacuation: {moved:,} people moved to safety from "
                    f"{zone.name} (displaced now {zone.displaced:,})"
                ),
                tags        = ["evacuate"],
                severity    = "info",
            ))

    elif action.action_type == "allocate_supplies":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            hp_gain = 10.0   # supplies improve effective capacity
            asset.apply_repair(hp_gain)
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "action_complete",
                nation      = nation,
                asset_id    = asset.id,
                description = f"Supplies allocated to {asset.name} (+{hp_gain:.0f} HP → {asset.health:.0f})",
                tags        = ["allocate_supplies"],
                severity    = "info",
            ))

    elif action.action_type == "reroute":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            asset.apply_repair(15.0)
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "action_complete",
                nation      = nation,
                asset_id    = asset.id,
                description = f"Reroute established: {asset.name} partial connectivity restored (+15 HP → {asset.health:.0f})",
                tags        = ["reroute"],
                severity    = "info",
            ))

    elif action.action_type == "inspect":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            revealed = asset.hidden_damage
            asset.hidden_damage = 0.0
            asset.last_inspected_turn = state.turn
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "action_complete",
                nation      = nation,
                asset_id    = asset.id,
                description = (
                    f"Inspection complete: {asset.name} — health {asset.health:.0f}, "
                    f"hidden damage revealed: {revealed:.0f}"
                ),
                tags        = ["inspect"],
                severity    = "info",
            ))


def _apply_exogenous_events(
    state: ScenarioState,
    events: List[SimEvent],
    event_overrides: Dict[str, dict],
) -> List[str]:
    """
    Roll exogenous events for this turn using deterministic seeding.
    Returns list of event names that fired.
    """
    # Deterministic seed: same scenario + turn always produces same rolls
    random.seed(state.scenario_seed + state.turn * 997)
    fired = []

    for evt_name, evt_cfg in config.EXOGENOUS_EVENTS.items():
        # Check for per-scenario probability override
        prob = event_overrides.get(evt_name, {}).get("probability", evt_cfg["probability"])
        if random.random() > prob:
            continue

        fired.append(evt_name)
        logger.info(f"Exogenous event fired: {evt_name}")

        # Apply damage to affected asset types
        damage = float(evt_cfg.get("damage", 0))
        if damage > 0:
            affected_types = evt_cfg.get("affects", [])
            # Pick one random asset of each affected type (per nation)
            for nation in state.nations:
                for atype in affected_types:
                    candidates = [
                        a for a in state.get_assets_for(nation)
                        if a.asset_type == atype and not a.is_destroyed
                    ]
                    if not candidates:
                        continue
                    target = random.choice(candidates)
                    target.apply_damage(damage)
                    events.append(SimEvent(
                        turn        = state.turn,
                        event_type  = "exogenous",
                        nation      = nation,
                        asset_id    = target.id,
                        description = f"{evt_name.title()}: {target.name} took {damage:.0f} damage (→ {target.health:.0f} HP)",
                        tags        = [evt_name],
                        severity    = "warning" if target.health > 30 else "critical",
                    ))

        # Resource cut (e.g. supply_delay)
        resource_cut = float(evt_cfg.get("resource_cut", 0))
        if resource_cut > 0:
            for nation in state.nations:
                res = state.resources.get(nation)
                if res:
                    cut_amounts = {
                        k: v * resource_cut
                        for k, v in config.BASE_RESUPPLY_PER_TURN.items()
                        if v > 0
                    }
                    # Deduct from current stocks (best-effort)
                    for k, v in cut_amounts.items():
                        res.stocks[k] = max(0.0, res.stocks.get(k, 0) - v)
                    events.append(SimEvent(
                        turn        = state.turn,
                        event_type  = "exogenous",
                        nation      = nation,
                        description = f"{evt_name.title()}: resupply cut by {resource_cut:.0%} this turn",
                        tags        = [evt_name, "resource_cut"],
                        severity    = "warning",
                    ))

    return fired


def _tick_reinforcements(state: ScenarioState, events: List[SimEvent]) -> None:
    """Decrement reinforcement counters; remove flag when expired."""
    for nation in state.nations:
        expired = []
        for asset_id, turns_left in state.reinforcements.get(nation, {}).items():
            new_count = turns_left - 1
            asset = state.get_asset(asset_id)
            if new_count <= 0:
                expired.append(asset_id)
                if asset:
                    asset.is_reinforced = False
                    asset.reinforced_turns_remaining = 0
                    events.append(SimEvent(
                        turn        = state.turn,
                        event_type  = "reinforce_expired",
                        nation      = nation,
                        asset_id    = asset_id,
                        description = f"Reinforcement on {asset.name} has expired",
                        severity    = "info",
                    ))
            else:
                state.reinforcements[nation][asset_id] = new_count
                if asset:
                    asset.reinforced_turns_remaining = new_count
        for aid in expired:
            del state.reinforcements[nation][aid]


def _apply_resupply(state: ScenarioState, events: List[SimEvent]) -> None:
    """
    Add per-turn resupply to each nation's ResourceStock.
    Reduce by 50% if transport_hub is degraded.
    """
    for nation in state.nations:
        transport_ok = any(
            a.asset_type == "transport_hub"
            and not a.is_destroyed
            and a.health >= config.DEGRADED_THRESHOLD
            for a in state.get_assets_for(nation)
        )
        factor = 1.0 if transport_ok else (1.0 - config.RESUPPLY_REDUCTION_IF_TRANSPORT_DEGRADED)
        res = state.resources.get(nation)
        if not res:
            continue
        gains = {k: v * factor for k, v in config.BASE_RESUPPLY_PER_TURN.items() if v > 0}
        if "supply_lines_disrupted" in state.active_consequences.get(nation, []):
            gains["repair_crews"] = max(0.0, gains.get("repair_crews", 0.0) - 1.0)
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "resupply_reduced",
                nation      = nation,
                description = f"{nation}: repair crew resupply reduced by 1 due to supply lines disruption",
                tags        = ["supply_lines_disrupted", "repair_crews_penalty"],
                severity    = "warning",
            ))
        res.add(gains)
        if factor < 1.0:
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "resupply_reduced",
                nation      = nation,
                description = f"{nation}: resupply reduced to {factor:.0%} — transport hub degraded",
                tags        = ["supply_lines_disrupted"],
                severity    = "warning",
            ))


def _update_stable_turns(state: ScenarioState) -> None:
    """
    Increment stable_turns_count for nations where all critical assets are healthy.
    Reset to 0 otherwise.
    Mutates state (already deep-copied).
    """
    for nation in state.nations:
        if nation in state.end_conditions_met:
            continue
        critical = [
            a for a in state.get_assets_for(nation)
            if a.is_critical and not a.is_destroyed
        ]
        all_healthy = all(a.health >= config.DEGRADED_THRESHOLD for a in critical)
        if all_healthy and critical:
            state.stable_turns_count[nation] = state.stable_turns_count.get(nation, 0) + 1
        else:
            state.stable_turns_count[nation] = 0


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def step_simulation(
    state: ScenarioState,
    actions: List[Action],
    narrator=None,              # optional ClaudeNarrator instance
    exogenous_overrides: Optional[Dict[str, dict]] = None,
) -> TurnResult:
    """
    Advance the simulation by one turn following ARCHITECTURE.md steps 2a–2q.

    Args:
        state     : Current ScenarioState (not mutated — deep copy is made).
        actions   : List of Action objects from agents this turn.
        narrator  : Optional ClaudeNarrator; skipped if None.
        exogenous_overrides : Per-scenario event probability overrides.

    Returns:
        TurnResult with new_state and full change summary.
    """
    if state.is_terminal:
        logger.warning("step_simulation called on terminal state — returning unchanged")
        return TurnResult(
            turn      = state.turn,
            new_state = state,
            end_condition = next(iter(state.end_conditions_met.values()), "terminal"),
        )

    # ── Deep copy ─────────────────────────────────────────────────────────────
    s = state.model_copy(deep=True)
    s.turn += 1
    exogenous_overrides = exogenous_overrides or {}

    # Collect all events for this turn
    turn_events: List[SimEvent] = []

    # Track result fields
    actions_processed: List[Action]  = []
    actions_completed: List[Action]  = []
    assets_repaired:   List[str]     = []
    assets_degraded:   List[str]     = []
    zones_evacuated:   List[str]     = []
    exogenous_fired:   List[str]     = []

    logger.info(f"── Turn {s.turn} ──────────────────────────────────────")

    # ── 2a. Validate actions ──────────────────────────────────────────────────
    valid_actions: List[Action] = []
    for action in actions:
        err = _validate_action(action, s)
        if err:
            logger.warning(f"Action rejected: {err}")
            turn_events.append(SimEvent(
                turn        = s.turn,
                event_type  = "action_rejected",
                nation      = action.actor_nation,
                description = f"Action rejected: {err}",
                severity    = "warning",
            ))
        else:
            valid_actions.append(action)

    # ── 2b+2c. Check affordability and deduct resources ───────────────────────
    affordable_actions: List[Action] = []
    for action in valid_actions:
        act_cfg = config.ACTION_TYPES[action.action_type]
        res = s.resources.get(action.actor_nation)
        if res and res.can_afford(act_cfg["cost"]):
            res.deduct(act_cfg["cost"])
            affordable_actions.append(action)
            actions_processed.append(action)
        else:
            logger.warning(f"Action unaffordable after re-check: {action.action_type} for {action.actor_nation}")

    # ── 2d. Apply immediate and queue multi-turn actions ──────────────────────
    for action in affordable_actions:
        turns_needed = config.ACTION_TYPES[action.action_type]["turns_to_complete"]

        if turns_needed <= 1:
            # Instant action — apply now
            _apply_immediate_action(action, s, turn_events)
            actions_completed.append(action)
            if action.target_asset_id and action.action_type in ("repair", "restore_power", "allocate_supplies", "reroute"):
                assets_repaired.append(action.target_asset_id)
            if action.target_zone_id and action.action_type == "evacuate":
                zones_evacuated.append(action.target_zone_id)
        else:
            # Queue multi-turn action
            pending = PendingAction(
                action=action,
                turns_remaining=turns_needed,
                started_turn=s.turn,
            )
            s.pending_actions.setdefault(action.actor_nation, []).append(pending)

            # Repair work begins immediately even if full completion takes multiple turns.
            if action.action_type == "repair" and action.target_asset_id:
                queued_asset = s.get_asset(action.target_asset_id)
                if queued_asset:
                    hp_before = queued_asset.health
                    queued_asset.apply_repair(5.0)
                    if queued_asset.health > hp_before and action.target_asset_id not in assets_repaired:
                        assets_repaired.append(action.target_asset_id)
            turn_events.append(SimEvent(
                turn        = s.turn,
                event_type  = "action_queued",
                nation      = action.actor_nation,
                asset_id    = action.target_asset_id,
                description = (
                    f"{action.action_type} queued on "
                    f"{action.target_asset_id or action.target_zone_id} "
                    f"— completes in {turns_needed} turns"
                ),
                severity    = "info",
            ))

    # ── 2e+2f. Tick pending multi-turn actions ────────────────────────────────
    for nation in s.nations:
        still_pending: List[PendingAction] = []
        for pa in s.pending_actions.get(nation, []):
            pa.turns_remaining -= 1
            if pa.turns_remaining <= 0:
                _apply_immediate_action(pa.action, s, turn_events)
                actions_completed.append(pa.action)
                if pa.action.target_asset_id and pa.action.action_type in ("repair", "reroute"):
                    assets_repaired.append(pa.action.target_asset_id)
            else:
                still_pending.append(pa)
        s.pending_actions[nation] = still_pending

    # ── 2g. Exogenous events ──────────────────────────────────────────────────
    exogenous_fired = _apply_exogenous_events(s, turn_events, exogenous_overrides)

    # ── 2h. Dependency penalties ──────────────────────────────────────────────
    penalties, dep_events = csq.apply_dependency_penalties(s)
    turn_events.extend(dep_events)
    for asset_id, penalty in penalties.items():
        asset = s.get_asset(asset_id)
        if asset:
            asset.apply_damage(penalty)
            if asset.id not in assets_degraded:
                assets_degraded.append(asset.id)

    # ?? 2h2. Active consequence penalties ??????????????????
    penalties2, events2 = csq.apply_active_consequence_effects(s)
    turn_events.extend(events2)
    for asset_id, penalty in penalties2.items():
        asset = s.get_asset(asset_id)
        if asset:
            asset.apply_damage(penalty)
            if asset.id not in assets_degraded:
                assets_degraded.append(asset.id)

    # ── 2i. Apply degradation_rate ────────────────────────────────────────────
    for asset in s.assets:
        if asset.is_destroyed:
            continue
        deg_rate = float(config.ASSET_TYPES.get(asset.asset_type, {}).get("degradation_rate", 0))
        if deg_rate > 0:
            asset.apply_damage(deg_rate)
            if asset.id not in assets_degraded:
                assets_degraded.append(asset.id)

    # ── 2j. Resource resupply ─────────────────────────────────────────────────
    _apply_resupply(s, turn_events)

    # ── 2k. Compute consequences ──────────────────────────────────────────────
    new_consequences = csq.compute_consequences(s)
    s.active_consequences = new_consequences

    # Emit consequence-change events
    for nation, tags in new_consequences.items():
        for tag in tags:
            turn_events.append(SimEvent(
                turn        = s.turn,
                event_type  = "consequence",
                nation      = nation,
                description = f"{nation}: consequence active — {tag.replace('_', ' ')}",
                tags        = [tag],
                severity    = "warning" if "risk" not in tag else "critical",
            ))

    # ── 2l. Update population zones ───────────────────────────────────────────
    zone_updates, zone_events = csq.update_population_zones(s)
    turn_events.extend(zone_events)
    for zone_id, updates in zone_updates.items():
        zone = s.get_zone(zone_id)
        if zone:
            zone.service_coverage = updates["service_coverage"]
            zone.displaced        = updates["displaced"]
            zone.mortality_risk   = updates["mortality_risk"]

    # ── 2m. Check end conditions ──────────────────────────────────────────────
    _update_stable_turns(s)
    newly_terminal = csq.check_end_conditions(s)
    s.end_conditions_met.update(newly_terminal)

    end_condition_this_turn: Optional[str] = None
    for nation, cond in newly_terminal.items():
        end_condition_this_turn = cond
        turn_events.append(SimEvent(
            turn        = s.turn,
            event_type  = "end_condition",
            nation      = nation,
            description = f"{nation}: {config.END_CONDITIONS[cond]['description']}",
            tags        = [cond],
            severity    = "critical" if cond == "collapsed" else "info",
        ))

    # Terminal if all nations have end conditions
    if set(s.nations).issubset(set(s.end_conditions_met.keys())):
        s.is_terminal = True

    # ── 2n. KPI snapshots ─────────────────────────────────────────────────────
    service_coverage  = csq.compute_service_coverage_scores(s)
    total_displaced   = csq.compute_total_displaced(s)
    resource_summary  = {
        n: s.resources[n].summary()
        for n in s.nations
        if n in s.resources
    }

    # ── 2o. Narrator (optional) ───────────────────────────────────────────────
    narrative = ""
    if narrator is not None and not config.DISABLE_NARRATOR:
        try:
            from schemas import TurnResult as _TR  # avoid circular at module level
            proto = _TR(turn=s.turn, new_state=s)
            narrative = narrator.generate_narrative(proto)
        except Exception as exc:
            logger.warning(f"Narrator failed (non-fatal): {exc}")

    # ── 2p. Commit events to log ──────────────────────────────────────────────
    s.event_log.extend(turn_events)

    # ── 2q. Build and return TurnResult ──────────────────────────────────────
    result = TurnResult(
        turn               = s.turn,
        new_state          = s,
        actions_processed  = actions_processed,
        actions_completed  = actions_completed,
        assets_repaired    = list(set(assets_repaired)),
        assets_degraded    = list(set(assets_degraded)),
        zones_evacuated    = zones_evacuated,
        new_consequences   = new_consequences,
        exogenous_events   = exogenous_fired,
        narrative          = narrative,
        service_coverage   = service_coverage,
        total_displaced    = total_displaced,
        resource_summary   = resource_summary,
        end_condition      = end_condition_this_turn,
    )

    logger.info(
        f"Turn {s.turn} complete — "
        f"coverage: { {n: f'{v:.0%}' for n,v in service_coverage.items()} } | "
        f"displaced: {total_displaced} | "
        f"end: {end_condition_this_turn or 'none'}"
    )

    return result

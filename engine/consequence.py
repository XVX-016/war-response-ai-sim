# ── ResilienceSim v1 ── engine/consequence.py ─────────────────────────────────
# Responsibilities:
#   - apply_dependency_penalties(state) -> List[SimEvent]   — HP loss from broken deps
#   - compute_consequences(state)       -> Dict[str, List[str]]  — active consequence tags
#   - update_population_zones(state)    -> List[SimEvent]   — zone coverage + displacement
#   - check_end_conditions(state)       -> Dict[str, str]   — terminal state per nation
#
# PURE FUNCTIONS — none of these mutate state.
# turn_engine reads the return values and applies them to the state copy.
#
# Import order: config → schemas only

from __future__ import annotations

from typing import Dict, List, Tuple

from loguru import logger

import config
from schemas import Asset, PopulationZone, ScenarioState, SimEvent


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dependency penalties
# ─────────────────────────────────────────────────────────────────────────────

def apply_dependency_penalties(state: ScenarioState) -> Tuple[Dict[str, float], List[SimEvent]]:
    """
    For each asset, check its upstream dependencies (config.DEPENDENCY_GRAPH).
    If a dependency is degraded, the dependent asset loses DEPENDENCY_PENALTY HP.

    Returns:
        penalties : Dict[asset_id, total_penalty_hp]   — turn_engine applies these
        events    : List[SimEvent]                      — one event per affected asset
    """
    penalties: Dict[str, float] = {}
    events: List[SimEvent] = []

    asset_map = {a.id: a for a in state.assets}

    for asset in state.assets:
        if asset.is_destroyed:
            continue

        dep_types = config.DEPENDENCY_GRAPH.get(asset.asset_type, [])
        if not dep_types:
            continue

        # Find same-nation assets that satisfy each dependency type
        for dep_type in dep_types:
            # Find all same-nation assets of this dependency type
            dep_assets = [
                a for a in state.assets
                if a.nation == asset.nation
                and a.asset_type == dep_type
                and not a.is_destroyed
            ]

            if not dep_assets:
                # Dependency type entirely destroyed → full penalty
                penalty = config.DEPENDENCY_PENALTY
                penalties[asset.id] = penalties.get(asset.id, 0) + penalty
                events.append(SimEvent(
                    turn        = state.turn,
                    event_type  = "dependency_penalty",
                    nation      = asset.nation,
                    asset_id    = asset.id,
                    description = (
                        f"{asset.name} loses {penalty:.0f} HP — "
                        f"dependency '{dep_type}' is entirely destroyed"
                    ),
                    tags        = [f"missing_dep:{dep_type}"],
                    severity    = "warning",
                ))
                continue

            # Check if the best available dep is degraded
            best_dep = max(dep_assets, key=lambda a: a.health)
            if best_dep.health < config.DEGRADED_THRESHOLD:
                penalty = config.DEPENDENCY_PENALTY
                penalties[asset.id] = penalties.get(asset.id, 0) + penalty
                events.append(SimEvent(
                    turn        = state.turn,
                    event_type  = "dependency_penalty",
                    nation      = asset.nation,
                    asset_id    = asset.id,
                    description = (
                        f"{asset.name} loses {penalty:.0f} HP — "
                        f"dependency '{dep_type}' ({best_dep.name}) is degraded "
                        f"(health {best_dep.health:.0f})"
                    ),
                    tags        = [f"degraded_dep:{dep_type}"],
                    severity    = "warning",
                ))

    return penalties, events


# ─────────────────────────────────────────────────────────────────────────────
# 2. Consequence computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_consequences(state: ScenarioState) -> Dict[str, List[str]]:
    """
    Compute the set of active consequence tags for each nation this turn.
    An asset emits its consequence tags when health < DEGRADED_THRESHOLD.

    Returns:
        Dict[nation, List[consequence_tag]]
    """
    result: Dict[str, List[str]] = {n: [] for n in state.nations}

    for asset in state.assets:
        if asset.health >= config.DEGRADED_THRESHOLD and not asset.is_destroyed:
            continue  # healthy asset — no consequences

        tags = config.CONSEQUENCE_MAP.get(asset.asset_type, [])
        for tag in tags:
            if tag not in result[asset.nation]:
                result[asset.nation].append(tag)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 3. Population zone updates
# ─────────────────────────────────────────────────────────────────────────────

def _compute_zone_service_coverage(
    zone: PopulationZone,
    asset_map: Dict[str, Asset],
) -> float:
    """
    Weighted average health fraction of assets serving this zone.
    If a serving asset is destroyed or missing, it contributes 0.
    Returns a value in [0, 1].
    """
    if not zone.served_by_asset_ids:
        return 1.0   # no dependency defined → assume fully served

    total_weight = 0.0
    weighted_sum = 0.0

    for asset_id in zone.served_by_asset_ids:
        asset = asset_map.get(asset_id)
        # Weight by service_coverage_weight of asset_type; default 0.1
        weight = config.SERVICE_COVERAGE_WEIGHTS.get(
            asset.asset_type if asset else "", 0.1
        )
        coverage = asset.health_fraction() if (asset and not asset.is_destroyed) else 0.0
        weighted_sum += weight * coverage
        total_weight += weight

    if total_weight == 0:
        return 0.0
    return min(1.0, weighted_sum / total_weight)


def update_population_zones(
    state: ScenarioState,
) -> Tuple[Dict[str, dict], List[SimEvent]]:
    """
    Recompute service_coverage and displaced counts for every zone.

    Returns:
        zone_updates : Dict[zone_id, {"service_coverage": float, "displaced": int, "mortality_risk": float}]
        events       : List[SimEvent]
    """
    zone_updates: Dict[str, dict] = {}
    events: List[SimEvent] = []
    asset_map = {a.id: a for a in state.assets}

    for zone in state.zones:
        coverage = _compute_zone_service_coverage(zone, asset_map)

        # Displacement: if coverage < trigger, a fraction displaces each turn
        new_displaced = zone.displaced
        if coverage < config.DISPLACEMENT_TRIGGER:
            shortage        = config.DISPLACEMENT_TRIGGER - coverage
            displacement    = min(
                int(zone.population * config.MAX_DISPLACEMENT_RATE * (shortage / config.DISPLACEMENT_TRIGGER)),
                zone.population - zone.displaced,
            )
            new_displaced = zone.displaced + displacement

            if displacement > 0:
                events.append(SimEvent(
                    turn        = state.turn,
                    event_type  = "displacement",
                    nation      = zone.nation,
                    zone_id     = zone.id,
                    description = (
                        f"{zone.name}: {displacement:,} people displaced "
                        f"(coverage {coverage:.0%}, total displaced {new_displaced:,})"
                    ),
                    tags        = ["displacement"],
                    severity    = "warning" if coverage > 0.2 else "critical",
                ))

        # Mortality risk: high if both hospital and power are degraded
        mortality_risk = 0.0
        if coverage < config.MORTALITY_RISK_THRESHOLD:
            mortality_risk = min(1.0, (config.MORTALITY_RISK_THRESHOLD - coverage) / config.MORTALITY_RISK_THRESHOLD)
            events.append(SimEvent(
                turn        = state.turn,
                event_type  = "mortality_risk",
                nation      = zone.nation,
                zone_id     = zone.id,
                description = (
                    f"{zone.name}: mortality risk elevated at {mortality_risk:.0%} "
                    f"— service coverage critically low ({coverage:.0%})"
                ),
                tags        = ["mortality_risk"],
                severity    = "critical",
            ))

        zone_updates[zone.id] = {
            "service_coverage": coverage,
            "displaced":        new_displaced,
            "mortality_risk":   mortality_risk,
        }

    return zone_updates, events


# ─────────────────────────────────────────────────────────────────────────────
# 4. End condition checks
# ─────────────────────────────────────────────────────────────────────────────

def check_end_conditions(state: ScenarioState) -> Dict[str, str]:
    """
    Evaluate end conditions for each nation that doesn't yet have one.

    Returns:
        Dict[nation, end_condition_key]  — only includes nations newly terminal this turn.
        e.g. {"Boros": "collapsed"}
    """
    newly_terminal: Dict[str, str] = {}
    cfg_end = config.END_CONDITIONS

    # Timeout: both nations get "timeout" simultaneously
    if state.turn >= state.max_turns:
        for nation in state.nations:
            if nation not in state.end_conditions_met:
                newly_terminal[nation] = "timeout"
        return newly_terminal

    for nation in state.nations:
        if nation in state.end_conditions_met:
            continue   # already resolved

        # ── Collapsed ─────────────────────────────────────────────────────────
        coverage = state.service_coverage_score(nation)
        collapse_threshold = cfg_end["collapsed"]["service_coverage_threshold"]
        if coverage < collapse_threshold:
            newly_terminal[nation] = "collapsed"
            logger.warning(f"{nation} has COLLAPSED — service coverage {coverage:.1%}")
            continue

        # ── Stabilised ────────────────────────────────────────────────────────
        required_turns = cfg_end["stabilised"]["consecutive_turns_required"]
        critical_assets = [
            a for a in state.get_assets_for(nation)
            if a.is_critical and not a.is_destroyed
        ]
        all_critical_healthy = all(
            a.health >= config.DEGRADED_THRESHOLD for a in critical_assets
        )

        if all_critical_healthy and critical_assets:
            if state.stable_turns_count.get(nation, 0) + 1 >= required_turns:
                newly_terminal[nation] = "stabilised"
                logger.success(f"{nation} has STABILISED after {required_turns} consecutive healthy turns")
        # Note: stable_turns_count is incremented by turn_engine, not here (pure function)

    return newly_terminal


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service coverage KPI (convenience — also used by turn_engine for snapshots)
# ─────────────────────────────────────────────────────────────────────────────

def compute_service_coverage_scores(state: ScenarioState) -> Dict[str, float]:
    """Return nation → service_coverage_score (0–1) for all nations."""
    return {n: state.service_coverage_score(n) for n in state.nations}


def compute_total_displaced(state: ScenarioState) -> Dict[str, int]:
    """Return nation → total displaced persons across all zones."""
    result: Dict[str, int] = {n: 0 for n in state.nations}
    for zone in state.zones:
        result[zone.nation] = result.get(zone.nation, 0) + zone.displaced
    return result

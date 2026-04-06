"""
ResilienceSim v1 - engine/diplomacy.py
Pure functions for dynamic diplomatic and economic simulation.
All functions receive state and return changes - they do NOT mutate state.
Turn engine applies the returned values.

Import order: config -> schemas only.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

import config
from schemas import BilateralRelation, DiplomaticState, ScenarioState, SimEvent


GDP_ATTRITION_PER_DESTROYED = 0.002
GDP_RECOVERY_PER_TURN = 0.001
ALLIANCE_DRIFT_PER_TENSION = 0.005
ALLIANCE_RECOVERY_PER_TURN = 0.002
TRADE_BASE_FUEL = 8.0
TRADE_BASE_MEDICAL = 3.0
TRADE_BASE_FOOD = 4.0
TRADE_BASE_REPAIR_CREWS = 0.2
AID_TRIGGER_COVERAGE = 0.35
AID_BASE_FUEL = 15.0
AID_BASE_MEDICAL = 8.0
AID_BASE_FOOD = 10.0
AID_ALLIANCE_MULTIPLIER = 1.5
SANCTION_TRADE_REDUCTION = 0.70
SANCTION_TRIGGER_TENSION = 0.75

EVENT_PROBABILITIES = {
    "trade_agreement": 0.04,
    "diplomatic_incident": 0.03,
    "humanitarian_crisis": 0.02,
    "sanctions_imposed": 0.02,
    "sanctions_lifted": 0.03,
    "alliance_strengthened": 0.03,
    "border_dispute": 0.02,
}


def _profile_value(profile: Any, key: str, default: float = 0.5) -> float:
    if hasattr(profile, key):
        return float(getattr(profile, key, default))
    if isinstance(profile, dict):
        return float(profile.get(key, default))
    return float(default)


def initialise_diplomatic_state(
    state: ScenarioState,
    profiles: Dict[str, Any],
) -> DiplomaticState:
    """Build the initial DiplomaticState from country profiles."""
    dip = DiplomaticState()

    for nation in state.nations:
        profile = profiles.get(nation, {})
        dip.gdp_index[nation] = _profile_value(profile, "gdp_index", 0.5)
        dip.alliance_strength[nation] = _profile_value(profile, "alliance_strength", 0.5)

    for index, nation_a in enumerate(state.nations):
        for nation_b in state.nations[index + 1 :]:
            key = dip.relation_key(nation_a, nation_b)
            combined_alliance = (
                dip.alliance_strength.get(nation_a, 0.5)
                + dip.alliance_strength.get(nation_b, 0.5)
            ) / 2.0
            initial_tension = max(0.0, 0.3 - combined_alliance * 0.3)
            initial_trade = min(1.0, combined_alliance * 0.6 + 0.1)
            dip.relations[key] = BilateralRelation(
                nation_a=nation_a,
                nation_b=nation_b,
                trade_volume=round(initial_trade, 2),
                tension=round(initial_tension, 2),
            )

    return dip


def compute_gdp_attrition(state: ScenarioState) -> Dict[str, float]:
    """GDP drops when critical assets are destroyed or severely degraded."""
    deltas: Dict[str, float] = {}

    for nation in state.nations:
        assets = state.get_assets_for(nation)
        destroyed_critical = sum(1 for asset in assets if asset.is_critical and asset.is_destroyed)
        degraded_critical = sum(
            1
            for asset in assets
            if asset.is_critical
            and not asset.is_destroyed
            and asset.health < config.DEGRADED_THRESHOLD * 0.5
        )
        attrition = (
            destroyed_critical * GDP_ATTRITION_PER_DESTROYED
            + degraded_critical * GDP_ATTRITION_PER_DESTROYED * 0.5
        )
        deltas[nation] = round(GDP_RECOVERY_PER_TURN - attrition, 4)

    return deltas


def compute_bilateral_trade(
    state: ScenarioState,
    dip: DiplomaticState,
) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
    """Compute resource flows from bilateral trade this turn."""
    received: Dict[str, Dict[str, float]] = {nation: {} for nation in state.nations}
    events: List[str] = []

    def transport_ok(nation: str) -> bool:
        return any(
            asset.asset_type == "transport_hub"
            and not asset.is_destroyed
            and asset.health >= config.DEGRADED_THRESHOLD
            for asset in state.get_assets_for(nation)
        )

    for index, nation_a in enumerate(state.nations):
        for nation_b in state.nations[index + 1 :]:
            relation = dip.get_relation(nation_a, nation_b)
            effective_volume = (
                relation.trade_volume * (1 - SANCTION_TRADE_REDUCTION)
                if relation.sanctions_active
                else relation.trade_volume
            )
            if effective_volume < 0.05:
                continue

            if not transport_ok(nation_a) or not transport_ok(nation_b):
                events.append(
                    f"Trade between {nation_a} and {nation_b} disrupted - transport hubs degraded"
                )
                continue

            for sender, receiver in ((nation_a, nation_b), (nation_b, nation_a)):
                sender_gdp = dip.gdp_index.get(sender, 0.5)
                sender_resources = state.metadata.get(sender, {}).get("resource_richness", 0.5)
                volume = effective_volume * sender_gdp
                transfer = {
                    "fuel": round(TRADE_BASE_FUEL * volume * sender_resources, 1),
                    "medical_supplies": round(TRADE_BASE_MEDICAL * volume, 1),
                    "food_rations": round(TRADE_BASE_FOOD * volume, 1),
                    "repair_crews": 1 if (TRADE_BASE_REPAIR_CREWS * volume) > 0.5 else 0,
                }
                for resource, amount in transfer.items():
                    if amount > 0:
                        received[receiver][resource] = received[receiver].get(resource, 0) + amount

            if effective_volume > 0.2:
                note = ", SANCTIONED" if relation.sanctions_active else ""
                events.append(
                    f"Trade active: {nation_a} <-> {nation_b} "
                    f"(volume {effective_volume:.0%}{note})"
                )

    return received, events


def compute_international_aid(
    state: ScenarioState,
    dip: DiplomaticState,
) -> Tuple[Dict[str, Dict[str, float]], List[str]]:
    """High-alliance nations send aid when a nation's coverage drops critically."""
    aid: Dict[str, Dict[str, float]] = {nation: {} for nation in state.nations}
    events: List[str] = []

    for nation in state.nations:
        coverage = state.service_coverage_score(nation)
        if coverage >= AID_TRIGGER_COVERAGE:
            continue

        alliance = dip.alliance_strength.get(nation, 0.5)
        if alliance < 0.3:
            continue

        severity = max(0.0, AID_TRIGGER_COVERAGE - coverage) / AID_TRIGGER_COVERAGE
        aid_multiplier = alliance * AID_ALLIANCE_MULTIPLIER * severity
        package = {
            "fuel": round(AID_BASE_FUEL * aid_multiplier, 1),
            "medical_supplies": round(AID_BASE_MEDICAL * aid_multiplier, 1),
            "food_rations": round(AID_BASE_FOOD * aid_multiplier, 1),
            "repair_crews": 1 if aid_multiplier > 0.4 else 0,
        }
        for resource, amount in package.items():
            if amount > 0:
                aid[nation][resource] = aid[nation].get(resource, 0) + amount

        events.append(
            f"International aid to {nation}: +{package['fuel']:.0f} fuel, "
            f"+{package['medical_supplies']:.0f} medical "
            f"(alliance {alliance:.0%}, coverage {coverage:.0%})"
        )

    return aid, events


def compute_diplomatic_events(
    state: ScenarioState,
    dip: DiplomaticState,
) -> Tuple[Dict[str, BilateralRelation], List[str]]:
    """Roll deterministic diplomatic events for each bilateral relation."""
    updated: Dict[str, BilateralRelation] = {}
    events: List[str] = []
    pairs = [
        (nation_a, nation_b)
        for index, nation_a in enumerate(state.nations)
        for nation_b in state.nations[index + 1 :]
    ]

    for index, (nation_a, nation_b) in enumerate(pairs):
        rng = random.Random(state.scenario_seed + state.turn * 31 + index * 7)
        relation = dip.get_relation(nation_a, nation_b)
        new_relation = relation.model_copy(deep=True)

        for event_type, probability in EVENT_PROBABILITIES.items():
            if rng.random() > probability:
                continue

            if event_type == "trade_agreement":
                new_relation.trade_volume = min(1.0, relation.trade_volume + 0.10)
                new_relation.tension = max(0.0, relation.tension - 0.05)
                events.append(f"Trade agreement: {nation_a} <-> {nation_b} (trade volume +10%)")
            elif event_type == "diplomatic_incident":
                new_relation.tension = min(1.0, relation.tension + 0.12)
                new_relation.trade_volume = max(0.0, relation.trade_volume - 0.05)
                events.append(f"Diplomatic incident: {nation_a} - {nation_b} (tension +12%)")
            elif event_type == "humanitarian_crisis":
                new_relation.aid_active = True
                events.append(
                    f"Humanitarian crisis declared: {nation_a} - {nation_b} corridor (aid routes opened)"
                )
            elif event_type == "sanctions_imposed":
                if relation.tension >= SANCTION_TRIGGER_TENSION and not relation.sanctions_active:
                    new_relation.sanctions_active = True
                    events.append(
                        f"Sanctions imposed: {nation_a} <-> {nation_b} "
                        f"(trade volume reduced {SANCTION_TRADE_REDUCTION:.0%})"
                    )
                else:
                    continue
            elif event_type == "sanctions_lifted":
                if relation.sanctions_active and relation.tension < 0.5:
                    new_relation.sanctions_active = False
                    events.append(f"Sanctions lifted: {nation_a} <-> {nation_b} (trade normalising)")
                else:
                    continue
            elif event_type == "alliance_strengthened":
                average_alliance = (
                    dip.alliance_strength.get(nation_a, 0.5)
                    + dip.alliance_strength.get(nation_b, 0.5)
                ) / 2
                if average_alliance > 0.5:
                    new_relation.trade_volume = min(1.0, relation.trade_volume + 0.05)
                    new_relation.tension = max(0.0, relation.tension - 0.08)
                    events.append(f"Alliance strengthened: {nation_a} <-> {nation_b}")
                else:
                    continue
            elif event_type == "border_dispute":
                new_relation.tension = min(1.0, relation.tension + 0.08)
                new_relation.trade_volume = max(0.0, relation.trade_volume - 0.08)
                events.append(
                    f"Border dispute: {nation_a} - {nation_b} (tension +8%, trade -8%)"
                )

            new_relation.last_event_turn = state.turn
            new_relation.last_event_type = event_type
            break

        new_relation.tension = max(0.0, round(new_relation.tension - 0.005, 3))
        key = dip.relation_key(nation_a, nation_b)
        if new_relation != relation:
            updated[key] = new_relation

    return updated, events


def compute_alliance_drift(
    state: ScenarioState,
    dip: DiplomaticState,
) -> Dict[str, float]:
    """Alliance strength drifts based on bilateral tensions."""
    deltas: Dict[str, float] = {}

    for nation in state.nations:
        tensions = [dip.get_relation(nation, other).tension for other in state.nations if other != nation]
        average_tension = sum(tensions) / len(tensions) if tensions else 0.0
        delta = ALLIANCE_RECOVERY_PER_TURN - ALLIANCE_DRIFT_PER_TENSION * average_tension
        deltas[nation] = round(delta, 4)

    return deltas


def apply_diplomatic_turn(
    state: ScenarioState,
) -> Tuple[Optional[DiplomaticState], List[SimEvent]]:
    """Orchestrate all diplomatic computations for one turn."""
    if state.diplomatic_state is None:
        logger.warning("No diplomatic_state on state - skipping diplomacy")
        return None, []

    dip = state.diplomatic_state.model_copy(deep=True)
    events: List[SimEvent] = []
    dip.events_this_turn = []
    dip.trade_received = {nation: {} for nation in state.nations}
    dip.aid_received = {nation: {} for nation in state.nations}
    dip.sanctions_penalty = {}

    for nation, delta in compute_gdp_attrition(state).items():
        old_gdp = dip.gdp_index.get(nation, 0.5)
        new_gdp = max(0.01, min(1.0, old_gdp + delta))
        dip.gdp_index[nation] = round(new_gdp, 3)
        if abs(delta) > 0.001:
            severity = "warning" if delta < 0 else "info"
            sign = "+" if delta >= 0 else ""
            events.append(
                SimEvent(
                    turn=state.turn,
                    event_type="gdp_change",
                    nation=nation,
                    description=f"{nation} GDP index: {sign}{delta:.3f} (-> {new_gdp:.3f})",
                    severity=severity,
                )
            )

    trade_received, trade_events = compute_bilateral_trade(state, dip)
    dip.trade_received = trade_received
    for message in trade_events:
        events.append(SimEvent(turn=state.turn, event_type="trade", description=message, severity="info"))
    dip.events_this_turn.extend(trade_events)

    aid_received, aid_events = compute_international_aid(state, dip)
    dip.aid_received = aid_received
    for message in aid_events:
        events.append(
            SimEvent(turn=state.turn, event_type="international_aid", description=message, severity="info")
        )
    dip.events_this_turn.extend(aid_events)

    updated_relations, diplomatic_events = compute_diplomatic_events(state, dip)
    dip.relations.update(updated_relations)
    for message in diplomatic_events:
        events.append(
            SimEvent(turn=state.turn, event_type="diplomatic_event", description=message, severity="warning")
        )
    dip.events_this_turn.extend(diplomatic_events)

    for nation, delta in compute_alliance_drift(state, dip).items():
        old_value = dip.alliance_strength.get(nation, 0.5)
        dip.alliance_strength[nation] = round(max(0.0, min(1.0, old_value + delta)), 3)

    return dip, events

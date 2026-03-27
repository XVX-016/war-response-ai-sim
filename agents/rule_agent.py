# ?? ResilienceSim v1 ?? agents/rule_agent.py ?????????????????
# Responsibilities:
#   - select_actions(state, actor_id) -> List[Action]
#
# Strategy (priority order):
#   1. Repair the most critical degraded asset the nation can afford
#   2. Restore power to a dependent hospital/shelter if power is down
#   3. Evacuate the most threatened population zone
#   4. Allocate supplies to hospitals below 60 HP
#   5. Reinforce the lowest-health critical asset if all others are stable
#   6. Pass (return empty list) if nothing affordable
#
# Rules:
#   - Never imports turn_engine or consequence
#   - Always calls ResourceStock.can_afford before emitting an action
#   - Read-only access to state

from __future__ import annotations

from typing import List

from loguru import logger

import config
from schemas import Action, Asset, ScenarioState


def _can_afford(state: ScenarioState, nation: str, action_type: str) -> bool:
    res = state.resources.get(nation)
    if not res:
        return False
    cost = config.ACTION_TYPES[action_type]["cost"]
    return res.can_afford(cost)


def _degraded_assets_by_priority(
    state: ScenarioState,
    nation: str,
) -> List[Asset]:
    """
    Return non-destroyed assets below DEGRADED_THRESHOLD,
    sorted descending by config.ASSET_PRIORITY then by health (most urgent first).
    """
    assets = [
        a for a in state.get_assets_for(nation)
        if not a.is_destroyed
        and a.health < config.DEGRADED_THRESHOLD
    ]
    return sorted(
        assets,
        key=lambda a: (
            -config.ASSET_PRIORITY.get(a.asset_type, 0),
            a.health,
        ),
    )


def _most_threatened_zone(state: ScenarioState, nation: str):
    """Return the zone with lowest service_coverage that has room for evacuation."""
    zones = [
        z for z in state.get_zones_for(nation)
        if z.service_coverage < config.DISPLACEMENT_TRIGGER
        and z.displaced < z.population
    ]
    if not zones:
        return None
    return min(zones, key=lambda z: z.service_coverage)


def _command_center_supports_full_budget(state: ScenarioState, nation: str) -> bool:
    command_centers = [
        asset for asset in state.get_assets_for(nation)
        if asset.asset_type == "command_center" and not asset.is_destroyed
    ]
    return any(asset.health >= config.DEGRADED_THRESHOLD for asset in command_centers)


def _repairable_assets_by_priority(state: ScenarioState, nation: str) -> List[Asset]:
    return [
        asset for asset in _degraded_assets_by_priority(state, nation)
        if asset.is_critical or asset.last_inspected_turn is not None
    ]


def _inspection_targets_by_priority(state: ScenarioState, nation: str) -> List[Asset]:
    return [
        asset for asset in _degraded_assets_by_priority(state, nation)
        if not asset.is_critical and asset.last_inspected_turn is None
    ]


def select_actions(state: ScenarioState, actor_id: str) -> List[Action]:
    """
    Select actions for the given nation using rule-based priority and command-budget limits.

    Args:
        state    : Current ScenarioState (read-only).
        actor_id : Nation name (config.NATION_A or NATION_B).

    Returns:
        List[Action] ? 0, 1, or 2 actions depending on command-center health.
    """
    if actor_id not in state.nations:
        logger.error(f"select_actions: unknown actor_id '{actor_id}'")
        return []

    if state.is_terminal:
        return []

    chosen: List[Action] = []
    max_actions = 2 if _command_center_supports_full_budget(state, actor_id) else 1

    # ?? 1. Repair most urgent degraded asset ?????????????????
    if len(chosen) < max_actions and _can_afford(state, actor_id, "repair"):
        targets = _repairable_assets_by_priority(state, actor_id)
        for asset in targets:
            if asset.asset_type in config.ACTION_TYPES["repair"]["valid_targets"]:
                chosen.append(Action(
                    actor_nation=actor_id,
                    action_type="repair",
                    target_asset_id=asset.id,
                ))
                logger.debug(f"{actor_id} -> repair {asset.name} (health {asset.health:.0f})")
                break

    # ?? 1b. Inspect degraded non-critical assets before repairing them ?????????????????
    if len(chosen) < max_actions and _can_afford(state, actor_id, "inspect"):
        inspection_targets = _inspection_targets_by_priority(state, actor_id)
        if inspection_targets:
            target = inspection_targets[0]
            chosen.append(Action(
                actor_nation=actor_id,
                action_type="inspect",
                target_asset_id=target.id,
            ))
            logger.debug(f"{actor_id} -> inspect {target.name} before repair")

    # ?? 2. Restore power to hospital/shelter if power plant is degraded ???????
    if len(chosen) < max_actions and _can_afford(state, actor_id, "restore_power"):
        power_assets = [
            a for a in state.get_assets_for(actor_id)
            if a.asset_type == "power_plant"
            and (a.is_destroyed or a.health < config.DEGRADED_THRESHOLD)
        ]
        if power_assets:
            candidates = [
                a for a in state.get_assets_for(actor_id)
                if a.asset_type in config.ACTION_TYPES["restore_power"]["valid_targets"]
                and not a.is_destroyed
                and a.health < config.DEGRADED_THRESHOLD
            ]
            if candidates:
                target = max(candidates, key=lambda a: config.ASSET_PRIORITY.get(a.asset_type, 0))
                chosen.append(Action(
                    actor_nation=actor_id,
                    action_type="restore_power",
                    target_asset_id=target.id,
                ))
                logger.debug(f"{actor_id} -> restore_power to {target.name}")

    # ?? 3. Evacuate most threatened zone ?????????????????????
    if len(chosen) < max_actions and _can_afford(state, actor_id, "evacuate"):
        zone = _most_threatened_zone(state, actor_id)
        if zone:
            chosen.append(Action(
                actor_nation=actor_id,
                action_type="evacuate",
                target_zone_id=zone.id,
            ))
            logger.debug(f"{actor_id} -> evacuate {zone.name} (coverage {zone.service_coverage:.0%})")

    # ?? 4. Allocate supplies to hospital ?????????????????????
    if len(chosen) < max_actions and _can_afford(state, actor_id, "allocate_supplies"):
        hospitals = [
            a for a in state.get_assets_for(actor_id)
            if a.asset_type == "hospital"
            and not a.is_destroyed
            and a.health < 60.0
        ]
        if hospitals:
            target = min(hospitals, key=lambda a: a.health)
            chosen.append(Action(
                actor_nation=actor_id,
                action_type="allocate_supplies",
                target_asset_id=target.id,
            ))
            logger.debug(f"{actor_id} -> allocate_supplies to {target.name}")

    # ?? 5. Reinforce lowest-health critical asset if no urgent repairs ?????????
    if len(chosen) < max_actions and _can_afford(state, actor_id, "reinforce"):
        already_targeting = {a.target_asset_id for a in chosen if a.target_asset_id}
        reinforce_candidates = [
            a for a in state.get_assets_for(actor_id)
            if a.is_critical
            and not a.is_destroyed
            and not a.is_reinforced
            and a.id not in already_targeting
            and a.health < 80.0
        ]
        if reinforce_candidates:
            target = min(reinforce_candidates, key=lambda a: a.health)
            chosen.append(Action(
                actor_nation=actor_id,
                action_type="reinforce",
                target_asset_id=target.id,
            ))
            logger.debug(f"{actor_id} -> reinforce {target.name}")

    if not chosen:
        logger.debug(f"{actor_id} -> pass (no affordable action this turn)")

    return chosen

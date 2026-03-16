from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

import config
from engine.world import WorldGrid
from schemas import Asset, ScenarioState, SimEvent


def _clamp_fraction(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _asset_to_dict(asset: Asset) -> dict[str, Any]:
    status = asset.status()
    return {
        "id": asset.id,
        "name": asset.name,
        "nation": asset.nation,
        "asset_type": asset.asset_type,
        "row": asset.row,
        "col": asset.col,
        "health": asset.health,
        "max_health": asset.max_health,
        "health_fraction": _clamp_fraction(asset.health_fraction()),
        "status": status,
        "is_critical": asset.is_critical,
        "is_reinforced": asset.is_reinforced,
        "color": config.MAP_COLORMAP[status],
    }


def _zone_to_dict(zone) -> dict[str, Any]:
    return {
        "id": zone.id,
        "name": zone.name,
        "nation": zone.nation,
        "row": zone.row,
        "col": zone.col,
        "population": zone.population,
        "displaced": zone.displaced,
        "displacement_fraction": _clamp_fraction(zone.displacement_fraction()),
        "service_coverage": _clamp_fraction(zone.service_coverage),
        "mortality_risk": _clamp_fraction(zone.mortality_risk),
    }


def _resource_to_dict(state: ScenarioState) -> dict[str, dict[str, Any]]:
    resources: dict[str, dict[str, Any]] = {}
    for nation in state.nations:
        nation_resources: dict[str, Any] = {}
        stock = state.resources.get(nation)
        for resource_type, spec in config.RESOURCE_TYPES.items():
            starting = float(spec["starting"])
            amount = float(stock.stocks.get(resource_type, 0.0)) if stock else 0.0
            nation_resources[resource_type] = {
                "amount": amount,
                "unit": spec["unit"],
                "fraction": _clamp_fraction(amount / starting) if starting > 0 else 0.0,
            }
        resources[nation] = nation_resources
    return resources


def _kpis_for_state(state: ScenarioState) -> dict[str, dict[str, Any]]:
    kpis: dict[str, dict[str, Any]] = {}
    for nation in state.nations:
        total_displaced = sum(zone.displaced for zone in state.get_zones_for(nation))
        kpis[nation] = {
            "service_coverage_score": _clamp_fraction(state.service_coverage_score(nation)),
            "total_displaced": total_displaced,
            "stable_turns": int(state.stable_turns_count.get(nation, 0)),
            "end_condition": state.end_conditions_met.get(nation),
        }
    return kpis


def _event_to_dict(event: SimEvent) -> dict[str, Any]:
    return {
        "turn": event.turn,
        "event_type": event.event_type,
        "nation": event.nation,
        "asset_id": event.asset_id,
        "zone_id": event.zone_id,
        "description": event.description,
        "severity": event.severity,
        "tags": list(event.tags),
    }


def render_event_log(state: ScenarioState, limit: int = 100) -> List[dict]:
    logger.debug("Rendering event log with limit {}", limit)
    events = sorted(state.event_log, key=lambda event: (event.turn, state.event_log.index(event)), reverse=True)
    return [_event_to_dict(event) for event in events[:limit]]


def render_resource_delta(before: ScenarioState, after: ScenarioState) -> Dict[str, Dict[str, float]]:
    logger.debug("Rendering resource delta between turns {} and {}", before.turn, after.turn)
    delta: Dict[str, Dict[str, float]] = {}
    nations = sorted(set(before.nations) | set(after.nations))
    for nation in nations:
        nation_delta: Dict[str, float] = {}
        for resource_type in config.RESOURCE_TYPES:
            before_amount = float(before.resources.get(nation).stocks.get(resource_type, 0.0)) if before.resources.get(nation) else 0.0
            after_amount = float(after.resources.get(nation).stocks.get(resource_type, 0.0)) if after.resources.get(nation) else 0.0
            nation_delta[resource_type] = after_amount - before_amount
        delta[nation] = nation_delta
    return delta


def render_grid(state: ScenarioState, grid: WorldGrid) -> List[List[dict]]:
    logger.debug("Rendering grid for scenario '{}' turn {}", state.scenario_name, state.turn)
    asset_map = {asset.id: _asset_to_dict(asset) for asset in state.assets}
    base_grid = grid.to_render_grid()
    rendered: List[List[dict]] = []
    for row in base_grid:
        rendered_row: List[dict] = []
        for cell in row:
            asset_ids = list(cell.get("asset_ids", []))
            rendered_row.append({
                "row": cell["row"],
                "col": cell["col"],
                "terrain": cell.get("terrain", "plains"),
                "nation": cell.get("nation"),
                "asset_ids": asset_ids,
                "assets": [asset_map[asset_id] for asset_id in asset_ids if asset_id in asset_map],
            })
        rendered.append(rendered_row)
    return rendered


def render_state(state: ScenarioState) -> dict:
    logger.debug("Rendering full state for scenario '{}' turn {}", state.scenario_name, state.turn)
    assets = [_asset_to_dict(asset) for asset in state.assets]
    zones = [_zone_to_dict(zone) for zone in state.zones]
    return {
        "turn": state.turn,
        "is_terminal": state.is_terminal,
        "nations": list(state.nations),
        "assets": assets,
        "zones": zones,
        "resources": _resource_to_dict(state),
        "active_consequences": {nation: list(state.active_consequences.get(nation, [])) for nation in state.nations},
        "end_conditions": dict(state.end_conditions_met),
        "event_log": render_event_log(state, limit=50),
        "kpis": _kpis_for_state(state),
    }

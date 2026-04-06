from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

import config
from schemas import Asset, PopulationZone, ResourceStock, ScenarioState, SimEvent


@dataclass
class GridCell:
    row: int
    col: int
    terrain: str = "plains"
    nation: Optional[str] = None
    asset_ids: List[str] = field(default_factory=list)


class WorldGrid:
    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self._cells: Dict[Tuple[int, int], GridCell] = {
            (r, c): GridCell(row=r, col=c)
            for r in range(rows)
            for c in range(cols)
        }

    def cell(self, row: int, col: int) -> GridCell:
        if (row, col) not in self._cells:
            raise IndexError(f"Cell ({row},{col}) out of grid bounds ({self.rows}x{self.cols})")
        return self._cells[(row, col)]

    def place_asset(self, asset_id: str, row: int, col: int) -> None:
        self.cell(row, col).asset_ids.append(asset_id)

    def assets_at(self, row: int, col: int) -> List[str]:
        return self.cell(row, col).asset_ids

    def set_terrain(self, row: int, col: int, terrain: str) -> None:
        self.cell(row, col).terrain = terrain

    def set_nation(self, row: int, col: int, nation: str) -> None:
        self.cell(row, col).nation = nation

    def neighbours(self, row: int, col: int, radius: int = 1) -> List[GridCell]:
        result = []
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    result.append(self._cells[(r, c)])
        return result

    def to_render_grid(self) -> List[List[dict]]:
        return [
            [
                {
                    "row": r,
                    "col": c,
                    "terrain": self._cells[(r, c)].terrain,
                    "nation": self._cells[(r, c)].nation,
                    "asset_ids": self._cells[(r, c)].asset_ids,
                }
                for c in range(self.cols)
            ]
            for r in range(self.rows)
        ]


def _build_asset(raw: dict) -> Asset:
    asset_type = raw["asset_type"]
    if asset_type not in config.ASSET_TYPES:
        raise ValueError(f"Unknown asset_type '{asset_type}'. Valid: {list(config.ASSET_TYPES.keys())}")

    cfg = config.ASSET_TYPES[asset_type]
    max_hp = float(cfg["max_health"])
    start_hp = min(float(raw.get("starting_health", max_hp)), max_hp)

    return Asset(
        id=raw["id"],
        name=raw["name"],
        nation=raw["nation"],
        asset_type=asset_type,
        row=int(raw["row"]),
        col=int(raw["col"]),
        health=start_hp,
        max_health=max_hp,
        is_civilian=bool(cfg["civilian"]),
        is_critical=bool(cfg["critical"]),
        is_destroyed=start_hp <= 0,
        lat=raw.get("lat"),
        lon=raw.get("lon"),
        geo_name=raw.get("geo_name"),
    )


def _build_zone(raw: dict) -> PopulationZone:
    return PopulationZone(
        id=raw["id"],
        name=raw["name"],
        nation=raw["nation"],
        row=int(raw["row"]),
        col=int(raw["col"]),
        population=int(raw["population"]),
        displaced=int(raw.get("displaced", 0)),
        served_by_asset_ids=list(raw.get("served_by_asset_ids", [])),
        lat=raw.get("lat"),
        lon=raw.get("lon"),
    )


def _build_resource_stock(nation: str) -> ResourceStock:
    stocks = {rtype: float(rdata["starting"]) for rtype, rdata in config.RESOURCE_TYPES.items()}
    return ResourceStock(nation=nation, stocks=stocks)


def load_geo_coordinates(country_name: str) -> Optional[dict]:
    geo_path = config.DATA_DIR / "countries" / "geo_coordinates.json"
    if not geo_path.exists():
        return None
    with open(geo_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("countries", {}).get(country_name)


def _apply_starting_disruptions(assets: List[Asset], disruptions: List[dict]) -> List[SimEvent]:
    events: List[SimEvent] = []
    asset_map = {asset.id: asset for asset in assets}

    for disruption in disruptions:
        asset_id = disruption["asset_id"]
        damage = float(disruption["damage"])
        asset = asset_map.get(asset_id)
        if asset is None:
            logger.warning(f"starting_disruption references unknown asset '{asset_id}' - skipped")
            continue
        asset.apply_damage(damage)
        events.append(
            SimEvent(
                turn=0,
                event_type="starting_disruption",
                nation=asset.nation,
                asset_id=asset_id,
                description=f"Scenario start: {asset.name} took {damage:.0f} damage (health -> {asset.health:.0f})",
                severity="warning",
            )
        )
        logger.debug(f"Starting disruption: {asset_id} -{damage} HP -> {asset.health:.0f}")

    return events


def _assign_grid_ownership(grid: WorldGrid, assets: List[Asset]) -> None:
    for asset in assets:
        grid.set_nation(asset.row, asset.col, asset.nation)
        grid.place_asset(asset.id, asset.row, asset.col)


def _apply_geo_coordinates(state: ScenarioState, geo_nations: Optional[Dict[str, str]]) -> None:
    if not geo_nations:
        return

    has_geo = False
    for nation, country_name in geo_nations.items():
        if not country_name:
            continue
        geo_data = load_geo_coordinates(country_name)
        if not geo_data:
            continue

        asset_lookup = geo_data.get("assets", {})
        for asset in state.assets:
            if asset.nation != nation:
                continue
            entry = asset_lookup.get(asset.asset_type)
            if not entry:
                continue
            asset.lat = entry.get("lat")
            asset.lon = entry.get("lon")
            asset.geo_name = entry.get("name")
            has_geo = True

        population_zones = geo_data.get("population_zones", [])
        nation_zones = [zone for zone in state.zones if zone.nation == nation]
        for index, zone in enumerate(nation_zones):
            if index >= len(population_zones):
                break
            entry = population_zones[index]
            zone.lat = entry.get("lat")
            zone.lon = entry.get("lon")
            if entry.get("name"):
                zone.name = entry["name"]
            has_geo = True

        state.metadata.setdefault(nation, {})
        state.metadata[nation]["map_center"] = geo_data.get("map_center")
        state.metadata[nation]["map_zoom"] = geo_data.get("map_zoom")

    if has_geo:
        state.metadata["_has_geo"] = True


def load_scenario(
    path: str | Path,
    apply_profiles: bool = True,
    countries_dir: str | Path = None,
    geo_nations: Dict[str, str] = None,
) -> tuple[ScenarioState, WorldGrid]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    logger.info(f"Loading scenario: {path.name}")

    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    rows = int(raw.get("grid_rows", config.GRID_ROWS))
    cols = int(raw.get("grid_cols", config.GRID_COLS))
    grid = WorldGrid(rows=rows, cols=cols)

    nations = list(raw.get("nations", config.NATIONS))
    assets: List[Asset] = [_build_asset(entry) for entry in raw.get("assets", [])]
    zones: List[PopulationZone] = [_build_zone(entry) for entry in raw.get("population_zones", [])]
    resources: Dict[str, ResourceStock] = {nation: _build_resource_stock(nation) for nation in nations}

    active_consequences = {nation: [] for nation in nations}
    pending_actions = {nation: [] for nation in nations}
    reinforcements = {nation: {} for nation in nations}
    stable_turns_count = {nation: 0 for nation in nations}
    end_conditions_met = {}
    setup_events = _apply_starting_disruptions(assets, raw.get("starting_disruptions", []))
    exogenous_overrides = raw.get("exogenous_event_overrides", {})

    state = ScenarioState(
        scenario_name=raw.get("name", path.stem),
        scenario_seed=int(raw.get("seed", 42)),
        turn=0,
        max_turns=config.MAX_TURNS,
        nations=nations,
        assets=assets,
        zones=zones,
        resources=resources,
        active_consequences=active_consequences,
        pending_actions=pending_actions,
        reinforcements=reinforcements,
        stable_turns_count=stable_turns_count,
        end_conditions_met=end_conditions_met,
        metadata={
            "_scenario": {
                "exogenous_event_overrides": exogenous_overrides,
            }
        },
        is_terminal=False,
        event_log=setup_events,
    )

    if apply_profiles:
        from engine.country import apply_profile_to_state, load_country_profile

        profiles = {nation: load_country_profile(nation, countries_dir) for nation in state.nations}
        apply_profile_to_state(state, profiles)
        state.metadata["_profiles_applied"] = True

    _apply_geo_coordinates(state, geo_nations)
    _assign_grid_ownership(grid, assets)

    logger.success(
        f"Scenario '{state.scenario_name}' loaded. "
        f"Seed={state.scenario_seed}, Nations={nations}, "
        f"Assets={len(assets)}, Zones={len(zones)}"
    )

    return state, grid


def reset_scenario(state: ScenarioState, path: str | Path) -> tuple[ScenarioState, WorldGrid]:
    logger.info(f"Resetting scenario from {path}")
    return load_scenario(path)

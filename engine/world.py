# ── ResilienceSim v1 ── engine/world.py ──────────────────────────────────────
# Responsibilities:
#   - load_scenario(path) -> ScenarioState
#   - WorldGrid: 2D grid holding terrain + asset placement
#
# Rules:
#   - Never calls agents, narrator, or consequence
#   - Auto-fills asset fields from config.ASSET_TYPES
#   - Auto-fills ResourceStock from config.RESOURCE_TYPES
#   - Import order: config → schemas only

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger

import config
from schemas import (
    Asset,
    PopulationZone,
    ResourceStock,
    ScenarioState,
    SimEvent,
)


# ─────────────────────────────────────────────────────────────────────────────
# WorldGrid
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GridCell:
    """One cell in the world grid."""
    row: int
    col: int
    terrain: str = "plains"          # plains | urban | water | forest | mountain
    nation: Optional[str] = None     # which nation owns/controls this cell
    asset_ids: List[str] = field(default_factory=list)


class WorldGrid:
    """
    2D grid of GridCell objects.
    Provides spatial lookup helpers used by the UI and scenario loader.
    Does NOT hold simulation state — assets live in ScenarioState.assets.
    """

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
            raise IndexError(f"Cell ({row},{col}) out of grid bounds ({self.rows}×{self.cols})")
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
        """Return all cells within Manhattan radius (excludes the cell itself)."""
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
        """
        Serialise to a 2D list of dicts for the Streamlit UI renderer.
        Returns rows × cols list of {"row", "col", "terrain", "nation", "asset_ids"}.
        """
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


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_asset(raw: dict) -> Asset:
    """
    Construct an Asset from a scenario JSON entry.
    Auto-fills health / max_health / is_civilian / is_critical from config.ASSET_TYPES.
    `starting_health` in the JSON overrides the default max_health.
    """
    asset_type = raw["asset_type"]
    if asset_type not in config.ASSET_TYPES:
        raise ValueError(f"Unknown asset_type '{asset_type}'. Valid: {list(config.ASSET_TYPES.keys())}")

    cfg = config.ASSET_TYPES[asset_type]
    max_hp    = float(cfg["max_health"])
    start_hp  = min(float(raw.get("starting_health", max_hp)), max_hp)

    return Asset(
        id            = raw["id"],
        name          = raw["name"],
        nation        = raw["nation"],
        asset_type    = asset_type,
        row           = int(raw["row"]),
        col           = int(raw["col"]),
        health        = start_hp,
        max_health    = max_hp,
        is_civilian   = bool(cfg["civilian"]),
        is_critical   = bool(cfg["critical"]),
        is_destroyed  = start_hp <= 0,
    )


def _build_zone(raw: dict) -> PopulationZone:
    """Construct a PopulationZone from a scenario JSON entry."""
    return PopulationZone(
        id                   = raw["id"],
        name                 = raw["name"],
        nation               = raw["nation"],
        row                  = int(raw["row"]),
        col                  = int(raw["col"]),
        population           = int(raw["population"]),
        displaced            = int(raw.get("displaced", 0)),
        served_by_asset_ids  = list(raw.get("served_by_asset_ids", [])),
    )


def _build_resource_stock(nation: str) -> ResourceStock:
    """Initialise a ResourceStock from config.RESOURCE_TYPES starting values."""
    stocks = {
        rtype: float(rdata["starting"])
        for rtype, rdata in config.RESOURCE_TYPES.items()
    }
    return ResourceStock(nation=nation, stocks=stocks)


def _apply_starting_disruptions(assets: List[Asset], disruptions: List[dict]) -> List[SimEvent]:
    """Apply scenario-defined starting damage to assets. Returns setup events."""
    events: List[SimEvent] = []
    asset_map = {a.id: a for a in assets}

    for d in disruptions:
        asset_id = d["asset_id"]
        damage   = float(d["damage"])
        asset    = asset_map.get(asset_id)
        if asset is None:
            logger.warning(f"starting_disruption references unknown asset '{asset_id}' — skipped")
            continue
        asset.apply_damage(damage)
        events.append(SimEvent(
            turn        = 0,
            event_type  = "starting_disruption",
            nation      = asset.nation,
            asset_id    = asset_id,
            description = f"Scenario start: {asset.name} took {damage:.0f} damage (health → {asset.health:.0f})",
            severity    = "warning",
        ))
        logger.debug(f"Starting disruption: {asset_id} -{damage} HP → {asset.health:.0f}")

    return events


def _assign_grid_ownership(grid: WorldGrid, assets: List[Asset]) -> None:
    """
    Simple heuristic: mark each cell with the nation that owns an asset there.
    Cells with no asset stay nation=None.
    """
    for asset in assets:
        grid.set_nation(asset.row, asset.col, asset.nation)
        grid.place_asset(asset.id, asset.row, asset.col)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_scenario(path: str | Path) -> tuple[ScenarioState, WorldGrid]:
    """
    Load a scenario JSON file and return (ScenarioState, WorldGrid).

    Args:
        path: Path to a scenario JSON in data/scenarios/.

    Returns:
        (ScenarioState, WorldGrid) — state is ready for step_simulation().
        WorldGrid is a spatial helper for the UI; it is NOT part of ScenarioState.

    Raises:
        FileNotFoundError: if path does not exist.
        ValueError: if JSON references unknown asset_types or missing required fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    logger.info(f"Loading scenario: {path.name}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    # ── Grid ──────────────────────────────────────────────────────────────────
    rows    = int(raw.get("grid_rows", config.GRID_ROWS))
    cols    = int(raw.get("grid_cols", config.GRID_COLS))
    grid    = WorldGrid(rows=rows, cols=cols)

    # ── Nations ───────────────────────────────────────────────────────────────
    nations = list(raw.get("nations", config.NATIONS))

    # ── Assets ────────────────────────────────────────────────────────────────
    assets: List[Asset] = [_build_asset(a) for a in raw.get("assets", [])]
    logger.info(f"Loaded {len(assets)} assets across {nations}")

    # ── Population zones ──────────────────────────────────────────────────────
    zones: List[PopulationZone] = [_build_zone(z) for z in raw.get("population_zones", [])]
    logger.info(f"Loaded {len(zones)} population zones")

    # ── Resources ─────────────────────────────────────────────────────────────
    resources: Dict[str, ResourceStock] = {n: _build_resource_stock(n) for n in nations}

    # ── Starting state containers ─────────────────────────────────────────────
    active_consequences  = {n: [] for n in nations}
    pending_actions      = {n: [] for n in nations}
    reinforcements       = {n: {} for n in nations}
    stable_turns_count   = {n: 0  for n in nations}
    end_conditions_met   = {}

    # ── Apply starting disruptions ────────────────────────────────────────────
    setup_events = _apply_starting_disruptions(assets, raw.get("starting_disruptions", []))

    # ── Exogenous event probability overrides ─────────────────────────────────
    # Stored in scenario metadata (used by turn_engine when seeding exogenous events)
    exogenous_overrides = raw.get("exogenous_event_overrides", {})

    # ── Build ScenarioState ───────────────────────────────────────────────────
    state = ScenarioState(
        scenario_name       = raw.get("name", path.stem),
        scenario_seed       = int(raw.get("seed", 42)),
        turn                = 0,
        max_turns           = config.MAX_TURNS,
        nations             = nations,
        assets              = assets,
        zones               = zones,
        resources           = resources,
        active_consequences = active_consequences,
        pending_actions     = pending_actions,
        reinforcements      = reinforcements,
        stable_turns_count  = stable_turns_count,
        end_conditions_met  = end_conditions_met,
        is_terminal         = False,
        event_log           = setup_events,
    )

    # Stash overrides in metadata so turn_engine can read them
    # (ScenarioState has no metadata field; we attach to the first event's tags)
    if exogenous_overrides:
        state.event_log.append(SimEvent(
            turn        = 0,
            event_type  = "scenario_meta",
            description = f"Exogenous overrides: {exogenous_overrides}",
            tags        = [f"{k}:{v}" for k, v in exogenous_overrides.items()],
            severity    = "info",
        ))

    # ── Build WorldGrid ───────────────────────────────────────────────────────
    _assign_grid_ownership(grid, assets)

    logger.success(f"Scenario '{state.scenario_name}' loaded. "
                   f"Seed={state.scenario_seed}, Nations={nations}, "
                   f"Assets={len(assets)}, Zones={len(zones)}")

    return state, grid


def reset_scenario(state: ScenarioState, path: str | Path) -> tuple[ScenarioState, WorldGrid]:
    """
    Reload a scenario from disk, discarding all current state.
    Convenience wrapper around load_scenario for the Streamlit UI reset button.
    """
    logger.info(f"Resetting scenario from {path}")
    return load_scenario(path)

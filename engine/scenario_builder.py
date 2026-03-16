# ── ResilienceSim v1 ── engine/scenario_builder.py ───────────────────────────
# Responsibilities:
#   - Generate valid scenario JSONs programmatically
#   - Provide difficulty presets: easy / medium / hard / custom
#   - Validate scenario JSON structure against config contracts
#   - CLI: python -m engine.scenario_builder --preset hard --seed 99 --out data/scenarios/
#
# Rules:
#   - Output must be loadable by engine/world.py load_scenario() without errors
#   - Asset placement never puts two assets on the same cell
#   - Every zone references only assets that exist in the same nation
#   - Import order: config → schemas only

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

import config


# ─────────────────────────────────────────────────────────────────────────────
# Difficulty presets
# ─────────────────────────────────────────────────────────────────────────────

PRESETS: Dict[str, Dict[str, Any]] = {
    "easy": {
        "description": "Minor equipment faults. Most assets start healthy. Good resource stocks.",
        "health_range":        (75, 100),   # (min%, max%) of max_health at start
        "critical_health_min": 80,          # critical assets never start below this
        "resource_multiplier": 1.5,         # starting stocks × multiplier
        "starting_damage_assets": 2,        # number of assets to pre-damage
        "starting_damage_range": (10, 25),  # HP of pre-damage
        "exogenous_scale":     0.5,         # multiply all exogenous probabilities
        "seed_default":        1,
    },
    "medium": {
        "description": "Multiple asset failures. Mixed health. Standard resources.",
        "health_range":        (50, 95),
        "critical_health_min": 55,
        "resource_multiplier": 1.0,
        "starting_damage_assets": 4,
        "starting_damage_range": (20, 45),
        "exogenous_scale":     1.0,
        "seed_default":        42,
    },
    "hard": {
        "description": "Critical infrastructure severely degraded. Scarce resources. Active aftershocks.",
        "health_range":        (20, 75),
        "critical_health_min": 25,
        "resource_multiplier": 0.6,
        "starting_damage_assets": 6,
        "starting_damage_range": (30, 65),
        "exogenous_scale":     1.5,
        "seed_default":        99,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _nation_grid_region(
    nation: str,
    rows: int,
    cols: int,
) -> Tuple[int, int, int, int]:
    """
    Divide the grid into two halves — one per nation.
    Auria gets the top half, Boros gets the bottom half.
    Returns (row_min, row_max, col_min, col_max) inclusive.
    """
    mid = rows // 2
    if nation == config.NATION_A:
        return 0, mid - 1, 0, cols - 1
    else:
        return mid, rows - 1, 0, cols - 1


def _pick_unique_cell(
    used: set,
    rng: random.Random,
    row_min: int, row_max: int,
    col_min: int, col_max: int,
    max_attempts: int = 200,
) -> Tuple[int, int]:
    """Pick a (row, col) not already in `used`. Raises RuntimeError if grid is full."""
    for _ in range(max_attempts):
        r = rng.randint(row_min, row_max)
        c = rng.randint(col_min, col_max)
        if (r, c) not in used:
            used.add((r, c))
            return r, c
    raise RuntimeError(
        f"Could not place asset in region ({row_min},{col_min})–({row_max},{col_max}): grid too full"
    )


def _starting_health(
    asset_type: str,
    preset: Dict[str, Any],
    rng: random.Random,
) -> int:
    """
    Compute starting health for an asset.
    Critical assets are clamped to preset["critical_health_min"] as a floor.
    """
    max_hp  = config.ASSET_TYPES[asset_type]["max_health"]
    is_crit = config.ASSET_TYPES[asset_type]["critical"]
    lo_pct, hi_pct = preset["health_range"]

    pct   = rng.randint(lo_pct, hi_pct) / 100.0
    hp    = int(max_hp * pct)

    if is_crit:
        floor = int(max_hp * preset["critical_health_min"] / 100)
        hp    = max(hp, floor)

    return min(hp, max_hp)


def _build_assets_for_nation(
    nation: str,
    preset: Dict[str, Any],
    rng: random.Random,
    rows: int,
    cols: int,
    used_cells: set,
    asset_index: Dict[int, int],    # nation_index → count, for unique IDs
) -> List[Dict[str, Any]]:
    """
    Place one asset of each type in the nation's grid region.
    Returns list of asset dicts ready for scenario JSON.
    """
    row_min, row_max, col_min, col_max = _nation_grid_region(nation, rows, cols)
    nation_key = nation.lower()
    assets     = []

    for asset_type, cfg in config.ASSET_TYPES.items():
        row, col = _pick_unique_cell(
            used_cells, rng, row_min, row_max, col_min, col_max
        )
        health = _starting_health(asset_type, preset, rng)
        idx    = asset_index.get(asset_type, 1)
        asset_index[asset_type] = idx + 1

        assets.append({
            "id":              f"{nation_key}_{asset_type}_01",
            "name":            f"{nation} {cfg['description'].split()[0]} {asset_type.replace('_', ' ').title()}",
            "nation":          nation,
            "asset_type":      asset_type,
            "row":             row,
            "col":             col,
            "starting_health": health,
        })

    return assets


def _build_zones_for_nation(
    nation: str,
    assets: List[Dict[str, Any]],
    rng: random.Random,
    rows: int,
    cols: int,
    used_cells: set,
    num_zones: int = 2,
) -> List[Dict[str, Any]]:
    """
    Create population zones for a nation.
    Each zone is placed near a cluster of that nation's assets and references
    a random subset of them as serving assets.
    """
    nation_key  = nation.lower()
    own_assets  = [a for a in assets if a["nation"] == nation]
    asset_ids   = [a["id"] for a in own_assets]

    row_min, row_max, col_min, col_max = _nation_grid_region(nation, rows, cols)

    # Population bands sized to the requested number of zones.
    pop_bands = [
        rng.randint(50_000, 250_000) if i == 0 else rng.randint(30_000, 100_000)
        for i in range(num_zones)
    ]

    zones = []
    for i in range(num_zones):
        row, col = _pick_unique_cell(
            used_cells, rng, row_min, row_max, col_min, col_max
        )
        # Each zone served by 3–5 randomly chosen assets
        n_served = min(rng.randint(3, 5), len(asset_ids))
        served   = rng.sample(asset_ids, n_served)
        # Ensure at least one critical asset type is represented
        critical_ids = [
            a["id"] for a in own_assets
            if config.ASSET_TYPES[a["asset_type"]]["critical"]
        ]
        if critical_ids and not any(s in served for s in critical_ids):
            served[0] = rng.choice(critical_ids)

        zones.append({
            "id":                  f"{nation_key}_zone_{i+1:02d}",
            "name":                f"{nation} Zone {chr(65+i)}",
            "nation":              nation,
            "row":                 row,
            "col":                 col,
            "population":          pop_bands[i],
            "served_by_asset_ids": served,
        })

    return zones


def _build_starting_disruptions(
    assets: List[Dict[str, Any]],
    preset: Dict[str, Any],
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Pre-damage a random subset of assets per the preset.
    Never damages an asset already below DEGRADED_THRESHOLD.
    """
    n_damage    = preset["starting_damage_assets"]
    dmg_lo, dmg_hi = preset["starting_damage_range"]
    disruptions = []

    # Prefer non-critical assets for pre-damage (more interesting gameplay)
    non_critical = [
        a for a in assets
        if not config.ASSET_TYPES[a["asset_type"]]["critical"]
        and a["starting_health"] > config.DEGRADED_THRESHOLD
    ]
    critical = [
        a for a in assets
        if config.ASSET_TYPES[a["asset_type"]]["critical"]
        and a["starting_health"] > config.DEGRADED_THRESHOLD
    ]

    candidates = non_critical + critical   # prefer non-critical first
    chosen     = rng.sample(candidates, min(n_damage, len(candidates)))

    for asset in chosen:
        dmg = rng.randint(dmg_lo, dmg_hi)
        disruptions.append({
            "asset_id": asset["id"],
            "damage":   dmg,
        })

    return disruptions


def _build_exogenous_overrides(preset: Dict[str, Any]) -> Dict[str, Any]:
    """Scale all exogenous event probabilities by preset["exogenous_scale"]."""
    scale    = preset["exogenous_scale"]
    overrides = {}
    for evt_name, evt_cfg in config.EXOGENOUS_EVENTS.items():
        scaled = round(evt_cfg["probability"] * scale, 4)
        overrides[evt_name] = {"probability": scaled}
    return overrides


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

class ScenarioValidationError(ValueError):
    pass


def validate_scenario(data: Dict[str, Any]) -> List[str]:
    """
    Validate a scenario dict against config contracts.
    Returns list of error strings. Empty list = valid.
    """
    errors: List[str] = []
    rows = data.get("grid_rows", config.GRID_ROWS)
    cols = data.get("grid_cols", config.GRID_COLS)
    nations = data.get("nations", [])
    assets  = data.get("assets", [])
    zones   = data.get("population_zones", [])

    # ── Nations ───────────────────────────────────────────────────────────────
    if not nations:
        errors.append("'nations' list is empty")

    # ── Assets ────────────────────────────────────────────────────────────────
    if not assets:
        errors.append("'assets' list is empty")

    asset_ids   = set()
    used_cells  = set()

    for i, a in enumerate(assets):
        ref = f"assets[{i}] id='{a.get('id','?')}'"

        # Required fields
        for field in ("id", "name", "nation", "asset_type", "row", "col"):
            if field not in a:
                errors.append(f"{ref}: missing required field '{field}'")

        asset_id = a.get("id")
        if asset_id:
            if asset_id in asset_ids:
                errors.append(f"{ref}: duplicate id '{asset_id}'")
            asset_ids.add(asset_id)

        # Asset type valid
        atype = a.get("asset_type")
        if atype and atype not in config.ASSET_TYPES:
            errors.append(f"{ref}: unknown asset_type '{atype}'")

        # Nation valid
        nation = a.get("nation")
        if nation and nation not in nations:
            errors.append(f"{ref}: nation '{nation}' not in nations list {nations}")

        # Grid bounds
        row, col = a.get("row", -1), a.get("col", -1)
        if not (0 <= row < rows and 0 <= col < cols):
            errors.append(f"{ref}: position ({row},{col}) out of grid {rows}x{cols}")

        # Unique cells
        cell = (row, col)
        if cell in used_cells:
            errors.append(f"{ref}: cell ({row},{col}) already occupied by another asset")
        used_cells.add(cell)

        # Health bounds
        hp = a.get("starting_health")
        if hp is not None:
            max_hp = config.ASSET_TYPES.get(atype, {}).get("max_health", 100)
            if not (0 <= hp <= max_hp):
                errors.append(f"{ref}: starting_health {hp} out of range [0, {max_hp}]")

    # ── Zones ─────────────────────────────────────────────────────────────────
    zone_ids = set()
    for i, z in enumerate(zones):
        ref = f"population_zones[{i}] id='{z.get('id','?')}'"

        for field in ("id", "name", "nation", "row", "col", "population"):
            if field not in z:
                errors.append(f"{ref}: missing required field '{field}'")

        zid = z.get("id")
        if zid:
            if zid in zone_ids:
                errors.append(f"{ref}: duplicate id '{zid}'")
            zone_ids.add(zid)

        # Nation valid
        znation = z.get("nation")
        if znation and znation not in nations:
            errors.append(f"{ref}: nation '{znation}' not in nations list")

        # Grid bounds
        zrow, zcol = z.get("row", -1), z.get("col", -1)
        if not (0 <= zrow < rows and 0 <= zcol < cols):
            errors.append(f"{ref}: position ({zrow},{zcol}) out of grid {rows}x{cols}")

        # Population positive
        pop = z.get("population", 0)
        if pop <= 0:
            errors.append(f"{ref}: population must be > 0")

        # served_by_asset_ids references must exist and belong to same nation
        for aid in z.get("served_by_asset_ids", []):
            if aid not in asset_ids:
                errors.append(f"{ref}: served_by_asset_ids references unknown asset '{aid}'")
            else:
                # Check nation match
                matched = next((a for a in assets if a.get("id") == aid), None)
                if matched and matched.get("nation") != znation:
                    errors.append(
                        f"{ref}: served_by_asset_ids '{aid}' belongs to "
                        f"nation '{matched.get('nation')}', not '{znation}'"
                    )

    # ── Starting disruptions ──────────────────────────────────────────────────
    for d in data.get("starting_disruptions", []):
        if d.get("asset_id") not in asset_ids:
            errors.append(
                f"starting_disruptions: references unknown asset_id '{d.get('asset_id')}'"
            )
        dmg = d.get("damage", 0)
        if not (0 < dmg <= 100):
            errors.append(f"starting_disruptions: damage {dmg} must be in (0, 100]")

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_scenario(
    preset_name: str = "medium",
    seed: Optional[int] = None,
    name: Optional[str] = None,
    rows: int = config.GRID_ROWS,
    cols: int = config.GRID_COLS,
    nations: Optional[List[str]] = None,
    num_zones_per_nation: int = 2,
) -> Dict[str, Any]:
    """
    Generate a complete scenario dict ready to save as JSON or pass to load_scenario().

    Args:
        preset_name : "easy" | "medium" | "hard"
        seed        : Random seed. Uses preset default if None.
        name        : Scenario name. Auto-generated if None.
        rows, cols  : Grid dimensions.
        nations     : Nation names. Defaults to config.NATIONS.
        num_zones_per_nation: Zones per nation (default 2).

    Returns:
        dict — valid scenario JSON structure.

    Raises:
        ValueError: if preset_name is unknown or validation fails.
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset '{preset_name}'. Choose from: {list(PRESETS.keys())}")

    preset  = PRESETS[preset_name]
    nations = nations or list(config.NATIONS)
    seed    = seed if seed is not None else preset["seed_default"]
    name    = name or f"Generated Scenario ({preset_name.title()}, seed={seed})"

    rng         = random.Random(seed)
    used_cells: set = set()
    asset_index: Dict[str, int] = {}
    all_assets: List[Dict[str, Any]] = []

    logger.info(f"Building scenario: preset={preset_name}, seed={seed}, nations={nations}")

    # ── Place assets ──────────────────────────────────────────────────────────
    for nation in nations:
        nation_assets = _build_assets_for_nation(
            nation, preset, rng, rows, cols, used_cells, asset_index
        )
        all_assets.extend(nation_assets)

    # ── Place zones ───────────────────────────────────────────────────────────
    all_zones: List[Dict[str, Any]] = []
    for nation in nations:
        zones = _build_zones_for_nation(
            nation, all_assets, rng, rows, cols, used_cells, num_zones_per_nation
        )
        all_zones.extend(zones)

    # ── Starting disruptions ──────────────────────────────────────────────────
    disruptions = _build_starting_disruptions(all_assets, preset, rng)

    # ── Exogenous overrides ───────────────────────────────────────────────────
    exogenous_overrides = _build_exogenous_overrides(preset)

    scenario = {
        "name":                      name,
        "description":               preset["description"],
        "seed":                      seed,
        "grid_rows":                 rows,
        "grid_cols":                 cols,
        "nations":                   nations,
        "assets":                    all_assets,
        "population_zones":          all_zones,
        "starting_disruptions":      disruptions,
        "exogenous_event_overrides": exogenous_overrides,
    }

    # ── Validate before returning ─────────────────────────────────────────────
    errors = validate_scenario(scenario)
    if errors:
        msg = f"Generated scenario failed validation ({len(errors)} errors):\n" + \
              "\n".join(f"  - {e}" for e in errors)
        raise ScenarioValidationError(msg)

    logger.success(f"Scenario '{name}' built and validated. "
                   f"Assets: {len(all_assets)}, Zones: {len(all_zones)}, "
                   f"Disruptions: {len(disruptions)}")

    return scenario


def save_scenario(scenario: Dict[str, Any], path: str | Path) -> Path:
    """
    Save a scenario dict to a JSON file.

    Args:
        scenario : Output of build_scenario().
        path     : Destination file path (.json).

    Returns:
        Resolved Path of written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(scenario, fh, indent=2)
    logger.info(f"Scenario saved to {path}")
    return path


def load_and_validate(path: str | Path) -> Tuple[Dict[str, Any], List[str]]:
    """
    Load a scenario JSON from disk and validate it.

    Returns:
        (scenario_dict, errors) — errors is empty list if valid.
    """
    path = Path(path)
    if not path.exists():
        return {}, [f"File not found: {path}"]
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    errors = validate_scenario(data)
    return data, errors


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="ResilienceSim v1 — Scenario Builder CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m engine.scenario_builder --preset medium --seed 42
  python -m engine.scenario_builder --preset hard --seed 7 --name "Stress Test Alpha" --out data/scenarios/
  python -m engine.scenario_builder --validate data/scenarios/cascade_crisis.json
        """,
    )
    parser.add_argument(
        "--preset", choices=list(PRESETS.keys()), default="medium",
        help="Difficulty preset (default: medium)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed (default: preset default)",
    )
    parser.add_argument(
        "--name", type=str, default=None,
        help="Scenario name (default: auto-generated)",
    )
    parser.add_argument(
        "--out", type=str, default="data/scenarios/",
        help="Output directory (default: data/scenarios/)",
    )
    parser.add_argument(
        "--validate", type=str, default=None, metavar="PATH",
        help="Validate an existing scenario JSON and exit",
    )
    parser.add_argument(
        "--print", action="store_true",
        help="Print generated scenario JSON to stdout instead of saving",
    )
    parser.add_argument(
        "--zones", type=int, default=2,
        help="Population zones per nation (default: 2)",
    )

    args = parser.parse_args()

    # ── Validate mode ─────────────────────────────────────────────────────────
    if args.validate:
        data, errors = load_and_validate(args.validate)
        if errors:
            print(f"INVALID — {len(errors)} error(s):")
            for e in errors:
                print(f"  ✗ {e}")
            sys.exit(1)
        else:
            print(f"VALID — {args.validate}")
            print(f"  Assets : {len(data.get('assets', []))}")
            print(f"  Zones  : {len(data.get('population_zones', []))}")
            print(f"  Nations: {data.get('nations', [])}")
            sys.exit(0)

    # ── Generate mode ─────────────────────────────────────────────────────────
    try:
        scenario = build_scenario(
            preset_name=args.preset,
            seed=args.seed,
            name=args.name,
            num_zones_per_nation=args.zones,
        )
    except (ValueError, ScenarioValidationError) as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    if args.print:
        print(json.dumps(scenario, indent=2))
        sys.exit(0)

    # ── Save ──────────────────────────────────────────────────────────────────
    safe_name = scenario["name"].lower().replace(" ", "_").replace(",", "").replace("=", "")
    filename  = f"{safe_name}.json"
    out_path  = Path(args.out) / filename

    try:
        saved = save_scenario(scenario, out_path)
        print(f"Saved: {saved}")
        print(f"  Preset    : {args.preset}")
        print(f"  Seed      : {scenario['seed']}")
        print(f"  Assets    : {len(scenario['assets'])}")
        print(f"  Zones     : {len(scenario['population_zones'])}")
        print(f"  Disruptions: {len(scenario['starting_disruptions'])}")
    except Exception as exc:
        print(f"ERROR saving: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    _cli()

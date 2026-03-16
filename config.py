# ── ResilienceSim v1 ── config.py ────────────────────────────────────────────
# ALL constants, enumerations, and tuning parameters live here.
# Every other module imports from this file — never hardcode values elsewhere.

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).parent
DATA_DIR      = ROOT_DIR / "data"
MAPS_DIR      = DATA_DIR / "maps"
SCENARIOS_DIR = DATA_DIR / "scenarios"
MODELS_DIR    = ROOT_DIR / "models"
YOLO_WEIGHTS  = MODELS_DIR / "yolo_civilian" / "best.pt"
YOLO_PRETRAINED = "yolov8n.pt"

# ── API Keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 512
DISABLE_NARRATOR  = os.getenv("DISABLE_NARRATOR", "false").lower() == "true"

# ── Grid ──────────────────────────────────────────────────────────────────────
GRID_ROWS    = 20
GRID_COLS    = 20
CELL_SIZE_KM = 5

# ── Nations ───────────────────────────────────────────────────────────────────
NATION_A = "Auria"
NATION_B = "Boros"
NATIONS  = [NATION_A, NATION_B]

# ── Simulation pacing ─────────────────────────────────────────────────────────
MAX_TURNS          = 60      # hard episode limit
TURN_DURATION_HOURS = 6     # each turn represents 6 real hours

# ── Asset types (civilian/societal only) ──────────────────────────────────────
# Keys used throughout engine and scenario JSON.
# degradation_rate: HP lost per turn when no repair action is applied
# repair_cost: resources consumed by a single Repair action (see ACTION_COSTS)
ASSET_TYPES = {
    "power_plant": {
        "max_health": 100, "degradation_rate": 0,
        "critical": True,  "civilian": True,
        "description": "Primary electricity generation and distribution hub",
    },
    "water_treatment": {
        "max_health": 100, "degradation_rate": 0,
        "critical": True,  "civilian": True,
        "description": "Potable water purification and pumping station",
    },
    "hospital": {
        "max_health": 100, "degradation_rate": 0,
        "critical": True,  "civilian": True,
        "description": "Medical facility providing emergency and routine care",
    },
    "telecom_tower": {
        "max_health": 80,  "degradation_rate": 0,
        "critical": False, "civilian": True,
        "description": "Communications relay for civilian and emergency services",
    },
    "transport_hub": {
        "max_health": 90,  "degradation_rate": 0,
        "critical": False, "civilian": True,
        "description": "Road/rail interchange enabling supply movement",
    },
    "fuel_depot": {
        "max_health": 80,  "degradation_rate": 2,
        "critical": False, "civilian": True,
        "description": "Fuel storage and distribution point",
    },
    "shelter": {
        "max_health": 70,  "degradation_rate": 0,
        "critical": False, "civilian": True,
        "description": "Emergency shelter for displaced population",
    },
    "command_center": {
        "max_health": 90,  "degradation_rate": 0,
        "critical": True,  "civilian": True,
        "description": "Civil emergency coordination and logistics hub",
    },
}

# Health threshold below which an asset is considered "degraded" (not destroyed)
DEGRADED_THRESHOLD  = 50.0
DESTROYED_THRESHOLD =  0.0

# ── Dependency graph ──────────────────────────────────────────────────────────
# Maps asset_type → list of asset_types it depends on.
# If a dependency's health < DEGRADED_THRESHOLD the dependent suffers a
# DEPENDENCY_PENALTY per turn (applied by consequence.py).
DEPENDENCY_GRAPH = {
    "hospital":       ["power_plant", "water_treatment", "telecom_tower"],
    "water_treatment":["power_plant", "transport_hub"],
    "telecom_tower":  ["power_plant"],
    "fuel_depot":     ["transport_hub"],
    "shelter":        ["power_plant", "water_treatment", "transport_hub"],
    "command_center": ["power_plant", "telecom_tower"],
    "transport_hub":  ["fuel_depot"],
    "power_plant":    [],            # primary — no upstream dependency
}

# HP lost per degraded dependency per turn
DEPENDENCY_PENALTY = 5.0

# ── Cascade consequence map ───────────────────────────────────────────────────
# Maps asset_type → list of consequence tags emitted when health < DEGRADED_THRESHOLD.
# Used by consequence.py to populate TurnResult.events.
CONSEQUENCE_MAP = {
    "power_plant":    ["blackout", "telecom_degraded", "hospital_on_backup"],
    "water_treatment":["water_shortage", "disease_risk_elevated"],
    "hospital":       ["medical_capacity_reduced", "mortality_risk_elevated"],
    "telecom_tower":  ["comms_degraded", "coordination_impaired"],
    "transport_hub":  ["supply_lines_disrupted", "repair_slowdown", "evacuation_blocked"],
    "fuel_depot":     ["fuel_shortage", "generator_runtime_limited"],
    "shelter":        ["displacement_pressure", "exposure_risk"],
    "command_center": ["response_coordination_impaired", "resource_misallocation_risk"],
}

# ── Population zones ──────────────────────────────────────────────────────────
# Displacement triggers when service_coverage drops below DISPLACEMENT_TRIGGER.
# Mortality risk rises when both hospital and power are degraded simultaneously.
DISPLACEMENT_TRIGGER     = 0.40   # service_coverage fraction (0–1)
MORTALITY_RISK_THRESHOLD = 0.25   # service_coverage fraction below which mortality risk activates
MAX_DISPLACEMENT_RATE    = 0.05   # max 5 % of zone population displaced per turn

# ── Resource stocks ───────────────────────────────────────────────────────────
# Starting stock per nation. Keys match ResourceStock.stocks dict.
RESOURCE_TYPES = {
    "repair_crews":     {"unit": "teams",   "starting": 10},
    "fuel":             {"unit": "tons",    "starting": 500},
    "medical_supplies": {"unit": "kits",    "starting": 300},
    "generators":       {"unit": "units",   "starting": 20},
    "food_rations":     {"unit": "pallets", "starting": 400},
    "water_purifiers":  {"unit": "units",   "starting": 15},
}

# Resources replenished each turn via supply lines (reduced if transport_hub degraded)
BASE_RESUPPLY_PER_TURN = {
    "repair_crews":     1,
    "fuel":             20,
    "medical_supplies": 10,
    "generators":       0,
    "food_rations":     15,
    "water_purifiers":  0,
}

RESUPPLY_REDUCTION_IF_TRANSPORT_DEGRADED = 0.50   # 50 % reduction

# ── Action definitions ────────────────────────────────────────────────────────
# All non-weaponized actor actions.
# cost: dict of resource_type → amount consumed per use
# hp_restored: health points restored to target asset (where applicable)
# turns_to_complete: 1 = instant, >1 = multi-turn (engine queues it)
ACTION_TYPES = {
    "repair": {
        "description": "Deploy repair crew to restore asset health",
        "cost": {"repair_crews": 1, "fuel": 10},
        "hp_restored": 30,
        "turns_to_complete": 2,
        "valid_targets": list(ASSET_TYPES.keys()),
    },
    "reinforce": {
        "description": "Harden asset against further degradation for 3 turns",
        "cost": {"repair_crews": 1, "fuel": 5},
        "hp_restored": 0,
        "turns_to_complete": 1,
        "valid_targets": list(ASSET_TYPES.keys()),
    },
    "evacuate": {
        "description": "Move population from a zone to nearest shelter",
        "cost": {"fuel": 20, "food_rations": 10},
        "hp_restored": 0,
        "turns_to_complete": 1,
        "valid_targets": ["shelter"],       # target = destination shelter
    },
    "restore_power": {
        "description": "Deploy generator to restore partial power to a dependent asset",
        "cost": {"generators": 1, "fuel": 15},
        "hp_restored": 20,
        "turns_to_complete": 1,
        "valid_targets": ["hospital", "water_treatment", "shelter", "command_center"],
    },
    "allocate_supplies": {
        "description": "Send medical or food supplies to a zone or hospital",
        "cost": {"medical_supplies": 30, "food_rations": 20},
        "hp_restored": 0,
        "turns_to_complete": 1,
        "valid_targets": ["hospital", "shelter"],
    },
    "reroute": {
        "description": "Establish alternate supply/transport corridor bypassing damaged hub",
        "cost": {"fuel": 25, "repair_crews": 1},
        "hp_restored": 0,
        "turns_to_complete": 2,
        "valid_targets": ["transport_hub"],
    },
    "inspect": {
        "description": "Assess asset damage; reveals hidden degradation; no resource cost",
        "cost": {},
        "hp_restored": 0,
        "turns_to_complete": 1,
        "valid_targets": list(ASSET_TYPES.keys()),
    },
}

# ── Exogenous event types (randomly injected disruptions) ────────────────────
# probability: chance per turn this event fires (can be overridden per scenario)
EXOGENOUS_EVENTS = {
    "earthquake":      {"probability": 0.02, "damage": 40, "affects": ["power_plant", "transport_hub", "hospital"]},
    "flood":           {"probability": 0.03, "damage": 30, "affects": ["water_treatment", "shelter", "transport_hub"]},
    "equipment_fault": {"probability": 0.05, "damage": 20, "affects": list(ASSET_TYPES.keys())},
    "supply_delay":    {"probability": 0.04, "damage": 0,  "affects": [],   "resource_cut": 0.5},
    "aftershock":      {"probability": 0.01, "damage": 15, "affects": ["power_plant", "telecom_tower"]},
}

# ── End / victory conditions ──────────────────────────────────────────────────
# Simulation ends (per nation) when ANY end condition is met.
END_CONDITIONS = {
    # Stabilisation: all critical assets above DEGRADED_THRESHOLD for 3 consecutive turns
    "stabilised": {
        "description": "All critical assets operational for 3 consecutive turns",
        "consecutive_turns_required": 3,
    },
    # Collapse: service_coverage drops below collapse threshold nation-wide
    "collapsed": {
        "description": "National service coverage fell below collapse threshold",
        "service_coverage_threshold": 0.20,
    },
    # Turn limit exhausted without stabilisation
    "timeout": {
        "description": "Simulation reached maximum turn limit",
    },
}

# Overall service coverage weight per asset type (used for KPI scoring 0–100)
SERVICE_COVERAGE_WEIGHTS = {
    "power_plant":    0.25,
    "water_treatment":0.20,
    "hospital":       0.20,
    "telecom_tower":  0.05,
    "transport_hub":  0.10,
    "fuel_depot":     0.05,
    "shelter":        0.05,
    "command_center": 0.10,
}

# ── Rule agent priorities ─────────────────────────────────────────────────────
# Higher = more urgent. Used by agents/rule_agent.py to rank repair targets.
ASSET_PRIORITY = {
    "power_plant":    10,
    "hospital":       10,
    "water_treatment": 9,
    "command_center":  8,
    "telecom_tower":   7,
    "transport_hub":   7,
    "fuel_depot":      5,
    "shelter":         4,
}

# ── Vision (optional) ─────────────────────────────────────────────────────────
USE_PRETRAINED_YOLO  = os.getenv("USE_PRETRAINED_YOLO", "true").lower() == "true"
YOLO_CONF_THRESHOLD  = 0.40
YOLO_IOU_THRESHOLD   = 0.45
YOLO_IMG_SIZE        = 640

# Maps YOLO/xView class names → ASSET_TYPES keys (civilian infrastructure only)
YOLO_CLASS_MAP = {
    "building":           "shelter",
    "hospital":           "hospital",
    "storage_tank":       "fuel_depot",
    "tower":              "telecom_tower",
    "vehicle":            "transport_hub",
    "utility_plant":      "power_plant",
    "water_tower":        "water_treatment",
}

# ── Streamlit UI ──────────────────────────────────────────────────────────────
PAGE_TITLE   = "ResilienceSim v1 — Civil Protection Dashboard"
REFRESH_MS   = 600
MAP_COLORMAP = {
    "healthy":   "#2ecc71",   # green  — health >= 80
    "degraded":  "#f39c12",   # amber  — health 50–79
    "critical":  "#e74c3c",   # red    — health < 50
    "destroyed": "#7f8c8d",   # grey   — health == 0
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"

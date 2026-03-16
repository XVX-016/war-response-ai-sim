# ── ResilienceSim v1 ── schemas.py ───────────────────────────────────────────
# Pydantic schemas = the data contract between ALL modules.
# Rule: any data that crosses a module boundary must match one of these models.
# Import these everywhere — never invent ad-hoc dicts.

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# 1. ASSET
# ─────────────────────────────────────────────────────────────────────────────

class Asset(BaseModel):
    """One piece of infrastructure on the grid."""
    id: str                     # unique e.g. "auria_hospital_01"
    name: str                   # human-readable e.g. "Central Hospital"
    nation: str                 # config.NATION_A or NATION_B
    asset_type: str             # key in config.ASSET_TYPES
    row: int                    # grid row  0 … GRID_ROWS-1
    col: int                    # grid col  0 … GRID_COLS-1
    health: float               # current HP
    max_health: float
    is_civilian: bool
    is_critical: bool
    is_destroyed: bool = False
    is_reinforced: bool = False         # True while Reinforce action is active
    reinforced_turns_remaining: int = 0
    hidden_damage: float = 0.0          # revealed only after Inspect action
    last_inspected_turn: Optional[int] = None

    # Derived helpers — call these instead of reading health directly
    def health_fraction(self) -> float:
        return self.health / self.max_health if self.max_health > 0 else 0.0

    def status(self) -> Literal["healthy", "degraded", "critical", "destroyed"]:
        from config import DEGRADED_THRESHOLD
        if self.is_destroyed or self.health <= 0:
            return "destroyed"
        if self.health < DEGRADED_THRESHOLD * 0.5:
            return "critical"
        if self.health < DEGRADED_THRESHOLD:
            return "degraded"
        return "healthy"

    def apply_damage(self, dmg: float) -> None:
        if self.is_reinforced:
            dmg *= 0.5                  # reinforcement halves incoming damage
        self.health = max(0.0, self.health - dmg)
        if self.health <= 0:
            self.is_destroyed = True

    def apply_repair(self, hp: float) -> None:
        self.health = min(self.max_health, self.health + hp)
        if self.health > 0:
            self.is_destroyed = False


# ─────────────────────────────────────────────────────────────────────────────
# 2. POPULATION ZONE
# ─────────────────────────────────────────────────────────────────────────────

class PopulationZone(BaseModel):
    """A civilian population cluster associated with a grid region."""
    id: str                         # e.g. "auria_zone_north"
    name: str
    nation: str
    row: int
    col: int
    population: int                 # total persons in zone
    displaced: int = 0              # persons currently displaced
    mortality_risk: float = 0.0     # 0–1 risk score this turn
    service_coverage: float = 1.0   # 0–1 weighted fraction of services available
    # IDs of assets that serve this zone
    served_by_asset_ids: List[str] = Field(default_factory=list)

    def displacement_fraction(self) -> float:
        return self.displaced / self.population if self.population > 0 else 0.0

    def at_risk_population(self) -> int:
        """Population currently without adequate service coverage."""
        from config import DISPLACEMENT_TRIGGER
        if self.service_coverage < DISPLACEMENT_TRIGGER:
            return int(self.population * (1 - self.service_coverage))
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. RESOURCE STOCK
# ─────────────────────────────────────────────────────────────────────────────

class ResourceStock(BaseModel):
    """All consumable resources held by one nation."""
    nation: str
    stocks: Dict[str, float] = Field(default_factory=dict)
    # Keys must match config.RESOURCE_TYPES keys:
    #   repair_crews, fuel, medical_supplies, generators, food_rations, water_purifiers

    def can_afford(self, cost: Dict[str, float]) -> bool:
        return all(self.stocks.get(k, 0) >= v for k, v in cost.items())

    def deduct(self, cost: Dict[str, float]) -> None:
        """Raises ValueError if insufficient. Check can_afford() first."""
        if not self.can_afford(cost):
            raise ValueError(f"Insufficient resources: need {cost}, have {self.stocks}")
        for k, v in cost.items():
            self.stocks[k] = self.stocks.get(k, 0) - v

    def add(self, gains: Dict[str, float]) -> None:
        for k, v in gains.items():
            self.stocks[k] = self.stocks.get(k, 0) + v

    def summary(self) -> str:
        return ", ".join(f"{k}={v:.0f}" for k, v in self.stocks.items())


# ─────────────────────────────────────────────────────────────────────────────
# 4. ACTION
# ─────────────────────────────────────────────────────────────────────────────

class Action(BaseModel):
    """One action submitted by an actor for a single turn."""
    actor_nation: str
    action_type: str            # key in config.ACTION_TYPES
    target_asset_id: Optional[str] = None
    target_zone_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self) -> "Action":
        requires_asset = {"repair", "reinforce", "restore_power", "reroute", "inspect"}
        requires_zone  = {"evacuate"}
        if self.action_type in requires_asset and not self.target_asset_id:
            raise ValueError(f"action_type '{self.action_type}' requires target_asset_id")
        if self.action_type in requires_zone and not self.target_zone_id:
            raise ValueError(f"action_type '{self.action_type}' requires target_zone_id")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# 5. PENDING ACTION (multi-turn)
# ─────────────────────────────────────────────────────────────────────────────

class PendingAction(BaseModel):
    """An action that takes multiple turns to complete (queued in ScenarioState)."""
    action: Action
    turns_remaining: int
    started_turn: int


# ─────────────────────────────────────────────────────────────────────────────
# 6. EVENT
# ─────────────────────────────────────────────────────────────────────────────

class SimEvent(BaseModel):
    """A structured event emitted during a turn (for log and UI)."""
    turn: int
    event_type: str             # e.g. "consequence", "action_complete", "exogenous", "end_condition"
    nation: Optional[str] = None
    asset_id: Optional[str] = None
    zone_id: Optional[str] = None
    description: str            # human-readable
    tags: List[str] = Field(default_factory=list)   # consequence tags from config.CONSEQUENCE_MAP
    severity: Literal["info", "warning", "critical"] = "info"


# ─────────────────────────────────────────────────────────────────────────────
# 7. SCENARIO STATE  (the central simulation state object)
# ─────────────────────────────────────────────────────────────────────────────

class ScenarioState(BaseModel):
    """
    Complete, serialisable state of the simulation at any point in time.
    This is the object passed between engine, agents, and UI.
    """
    scenario_name: str
    scenario_seed: int = 42
    turn: int = 0
    max_turns: int = 60

    # Nations
    nations: List[str] = Field(default_factory=list)

    # Infrastructure
    assets: List[Asset] = Field(default_factory=list)

    # Population
    zones: List[PopulationZone] = Field(default_factory=list)

    # Resources (one ResourceStock per nation)
    resources: Dict[str, ResourceStock] = Field(default_factory=dict)

    # Active consequence tags (nation → set of active consequence strings)
    active_consequences: Dict[str, List[str]] = Field(default_factory=dict)

    # Multi-turn actions in progress (nation → list)
    pending_actions: Dict[str, List[PendingAction]] = Field(default_factory=dict)

    # Reinforced asset tracking (nation → {asset_id: turns_remaining})
    reinforcements: Dict[str, Dict[str, int]] = Field(default_factory=dict)

    # Per-nation stability tracking for end conditions
    stable_turns_count: Dict[str, int] = Field(default_factory=dict)

    # End state
    end_conditions_met: Dict[str, str] = Field(default_factory=dict)
    # e.g. {"Auria": "stabilised", "Boros": "collapsed"}

    is_terminal: bool = False

    # Event log (all turns)
    event_log: List[SimEvent] = Field(default_factory=list)

    # Convenience helpers
    def get_asset(self, asset_id: str) -> Optional[Asset]:
        return next((a for a in self.assets if a.id == asset_id), None)

    def get_assets_for(self, nation: str) -> List[Asset]:
        return [a for a in self.assets if a.nation == nation]

    def get_zone(self, zone_id: str) -> Optional[PopulationZone]:
        return next((z for z in self.zones if z.id == zone_id), None)

    def get_zones_for(self, nation: str) -> List[PopulationZone]:
        return [z for z in self.zones if z.nation == nation]

    def service_coverage_score(self, nation: str) -> float:
        """Weighted service coverage 0–1 for a nation."""
        from config import SERVICE_COVERAGE_WEIGHTS
        score = 0.0
        assets = self.get_assets_for(nation)
        for asset in assets:
            w = SERVICE_COVERAGE_WEIGHTS.get(asset.asset_type, 0.0)
            score += w * asset.health_fraction()
        return min(1.0, score)


# ─────────────────────────────────────────────────────────────────────────────
# 8. TURN RESULT
# ─────────────────────────────────────────────────────────────────────────────

class TurnResult(BaseModel):
    """
    Output of TurnEngine.step_simulation().
    Contains the new state plus a structured summary of what changed.
    """
    turn: int
    new_state: ScenarioState

    # What actions were processed this turn
    actions_processed: List[Action] = Field(default_factory=list)
    actions_completed: List[Action] = Field(default_factory=list)   # multi-turn completions

    # Changes
    assets_repaired: List[str] = Field(default_factory=list)        # asset IDs
    assets_degraded: List[str] = Field(default_factory=list)
    zones_evacuated: List[str] = Field(default_factory=list)        # zone IDs
    new_consequences: Dict[str, List[str]] = Field(default_factory=dict)  # nation → tags

    # Exogenous events that fired this turn
    exogenous_events: List[str] = Field(default_factory=list)

    # Narrative (optional — filled by ClaudeNarrator)
    narrative: str = ""

    # KPI snapshots after this turn
    service_coverage: Dict[str, float] = Field(default_factory=dict)  # nation → 0–1
    total_displaced: Dict[str, int] = Field(default_factory=dict)     # nation → count
    resource_summary: Dict[str, str] = Field(default_factory=dict)    # nation → summary str

    # End condition if triggered this turn
    end_condition: Optional[str] = None   # "stabilised" | "collapsed" | "timeout" | None


# ─────────────────────────────────────────────────────────────────────────────
# 9. AGENT OBSERVATION (for rule agent / future RL)
# ─────────────────────────────────────────────────────────────────────────────

class AgentObservation(BaseModel):
    """
    Structured observation passed to agents each turn.
    Flat enough to convert to a numpy array for RL later.
    All float values normalised 0–1.
    """
    turn_normalised: float
    nation: str

    # Asset health fractions in config.ASSET_TYPES order
    own_asset_health: List[float]

    # Population
    zone_service_coverage: List[float]         # per zone, 0–1
    zone_displacement_fraction: List[float]    # per zone, 0–1

    # Resources (normalised by starting stock)
    resource_fractions: Dict[str, float]       # resource_type → current/starting

    # Active consequence flags (sorted by config.CONSEQUENCE_MAP key order)
    active_consequence_flags: List[int]        # binary 0/1

    # End condition proximity
    stable_turns_count: int
    service_coverage_score: float              # nation-wide, 0–1


# ─────────────────────────────────────────────────────────────────────────────
# 10. VISION DETECTION (optional adapter)
# ─────────────────────────────────────────────────────────────────────────────

class Detection(BaseModel):
    """Single bounding-box detection from YOLOv8."""
    class_name: str
    confidence: float
    bbox_xyxy: List[float]          # [x1, y1, x2, y2] pixels
    mapped_asset_type: Optional[str] = None   # from config.YOLO_CLASS_MAP

class DetectionResult(BaseModel):
    """All detections for one image, used for scenario annotation."""
    image_path: str
    detections: List[Detection]
    suggested_assets: List[Dict[str, Any]] = Field(default_factory=list)
    # each dict: {"asset_type": str, "row": int, "col": int, "confidence": float}

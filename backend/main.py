"""
ResilienceSim FastAPI backend.
Run: uvicorn backend.main:app --reload --port 8000
All endpoints are stateless - ScenarioState travels with every request.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from agents.rule_agent import select_actions
from engine.country import CountryProfile, apply_profile_to_state, load_country_profile
from engine.diplomacy import initialise_diplomatic_state
from engine.scenario_builder import PRESETS, build_scenario, load_and_validate, validate_scenario
from engine.turn_engine import step_simulation
from engine.world import load_scenario
from schemas import Action, ScenarioState


app = FastAPI(title="ResilienceSim API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoadScenarioRequest(BaseModel):
    path: str
    apply_profiles: bool = True
    profiles: Optional[Dict[str, Any]] = None
    geo_nations: Optional[Dict[str, str]] = None


class StepRequest(BaseModel):
    state: Dict[str, Any]
    actions: str | List[Dict[str, Any]]


class BuildScenarioRequest(BaseModel):
    preset: str = "medium"
    seed: int = 42
    name: Optional[str] = None
    num_zones: int = 2


class SaveProfileRequest(BaseModel):
    nation: str
    profile: Dict[str, Any]


def _deserialise_state(raw: Dict[str, Any]) -> ScenarioState:
    try:
        return ScenarioState(**raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid state: {exc}") from exc


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/scenarios")
def list_scenarios() -> Dict[str, List[Dict[str, Any]]]:
    scenarios: List[Dict[str, Any]] = []
    for path in sorted(config.SCENARIOS_DIR.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            scenarios.append(
                {
                    "path": str(path),
                    "name": data.get("name", path.stem),
                    "description": data.get("description", ""),
                    "nations": data.get("nations", []),
                    "assets": len(data.get("assets", [])),
                    "seed": data.get("seed", 42),
                }
            )
        except Exception:
            continue
    return {"scenarios": scenarios}


@app.post("/api/scenario/load")
def api_load_scenario(req: LoadScenarioRequest) -> Dict[str, Any]:
    path = Path(req.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Scenario not found: {req.path}")
    try:
        state, _ = load_scenario(path, apply_profiles=False, geo_nations=req.geo_nations)
        if req.apply_profiles and req.profiles:
            profiles = {nation: CountryProfile(**pdata) for nation, pdata in req.profiles.items()}
            apply_profile_to_state(state, profiles)
        elif req.apply_profiles:
            profiles = {nation: load_country_profile(nation) for nation in state.nations}
            apply_profile_to_state(state, profiles)
        return {"state": state.model_dump(), "turn": state.turn}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scenario/step")
def api_step(req: StepRequest) -> Dict[str, Any]:
    state = _deserialise_state(req.state)
    if req.actions == "auto":
        actions: List[Action] = []
        for nation in state.nations:
            actions.extend(select_actions(state, nation))
    else:
        try:
            actions = [Action(**item) for item in req.actions]
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid actions: {exc}") from exc

    try:
        result = step_simulation(state, actions)
        return {
            "turn": result.turn,
            "state": result.new_state.model_dump(),
            "service_coverage": result.service_coverage,
            "total_displaced": result.total_displaced,
            "resource_summary": result.resource_summary,
            "assets_repaired": result.assets_repaired,
            "assets_degraded": result.assets_degraded,
            "new_consequences": result.new_consequences,
            "exogenous_events": result.exogenous_events,
            "narrative": result.narrative,
            "end_condition": result.end_condition,
            "is_terminal": result.new_state.is_terminal,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scenario/init-diplomacy")
def api_init_diplomacy(req: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialise diplomatic state after scenario load.
    """
    state = _deserialise_state(req["state"])
    profiles = req.get("profiles", {})
    state.diplomatic_state = initialise_diplomatic_state(state, profiles)
    return {"state": state.model_dump()}


def _explain_action(action: Action, state: ScenarioState) -> str:
    from config import ASSET_PRIORITY

    if action.action_type == "repair":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            return f"Repairing {asset.name} (health {asset.health:.0f}/{asset.max_health:.0f}) - priority {ASSET_PRIORITY.get(asset.asset_type, 0)}/10"
    elif action.action_type == "restore_power":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            return f"Deploying generator to {asset.name} - power dependency broken"
    elif action.action_type == "evacuate":
        zone = state.get_zone(action.target_zone_id) if action.target_zone_id else None
        if zone:
            return f"Evacuating {zone.name} - coverage at {zone.service_coverage:.0%}"
    elif action.action_type == "reinforce":
        asset = state.get_asset(action.target_asset_id)
        if asset:
            return f"Reinforcing {asset.name} - protecting against further damage"
    return f"{action.action_type} action"


@app.post("/api/scenario/propose")
def api_propose_actions(req: Dict[str, Any]) -> Dict[str, Any]:
    state = _deserialise_state(req["state"])
    actions: List[Action] = []
    for nation in state.nations:
        actions.extend(select_actions(state, nation))
    return {
        "proposed_actions": [action.model_dump() for action in actions],
        "reasoning": [
            {
                "nation": action.actor_nation,
                "action_type": action.action_type,
                "target": action.target_asset_id or action.target_zone_id,
                "reason": _explain_action(action, state),
            }
            for action in actions
        ],
    }


@app.get("/api/geo/countries")
def api_geo_countries() -> Dict[str, Any]:
    geo_path = Path("data/countries/geo_coordinates.json")
    if not geo_path.exists():
        return {"countries": []}
    with open(geo_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {
        "countries": [
            {
                "name": name,
                "map_center": entry.get("map_center"),
                "map_zoom": entry.get("map_zoom"),
                "asset_count": len(entry.get("assets", {})),
            }
            for name, entry in data.get("countries", {}).items()
        ]
    }


@app.get("/api/country/profiles")
def api_get_profiles() -> Dict[str, Dict[str, Any]]:
    profiles = {}
    for nation in config.NATIONS:
        profile = load_country_profile(nation)
        profiles[nation] = profile.model_dump()
    return {"profiles": profiles}


@app.post("/api/country/profile")
def api_save_profile(req: SaveProfileRequest) -> Dict[str, Any]:
    try:
        profile = CountryProfile(**req.profile)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    path = config.DATA_DIR / "countries" / f"{req.nation.lower()}.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(profile.model_dump(), handle, indent=2)
    return {"saved": True, "path": str(path)}


@app.post("/api/scenario/build")
def api_build_scenario(req: BuildScenarioRequest) -> Dict[str, Any]:
    if req.preset not in PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {req.preset}")
    try:
        scenario = build_scenario(
            preset_name=req.preset,
            seed=req.seed,
            name=req.name,
            num_zones_per_nation=req.num_zones,
        )
        return {"scenario": scenario}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scenario/validate")
def api_validate(scenario: Dict[str, Any]) -> Dict[str, Any]:
    errors = validate_scenario(scenario)
    return {"valid": len(errors) == 0, "errors": errors}


@app.post("/api/vision/detect")
async def api_vision_detect(file: UploadFile = File(...)) -> Dict[str, Any]:
    try:
        from vision import YOLOv8Detector

        detector = YOLOv8Detector()
        if not detector.is_available():
            return {"available": False, "detections": [], "suggestions": []}

        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)

        result = detector.detect(tmp_path)
        suggestions = detector.suggest_scenario_assets(tmp_path)
        tmp_path.unlink(missing_ok=True)
        return {
            "available": True,
            "detections": [d.model_dump() for d in result.detections],
            "suggestions": suggestions,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

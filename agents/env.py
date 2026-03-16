from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from loguru import logger

import config
from engine.turn_engine import step_simulation
from engine.world import WorldGrid, load_scenario
from schemas import Action, AgentObservation, ScenarioState, TurnResult

try:
    from gymnasium.spaces import Box, Discrete
except ImportError:  # pragma: no cover - optional dependency
    Box = None
    Discrete = None

try:
    from pettingzoo import AECEnv
    from pettingzoo.utils import agent_selector
except ImportError:  # pragma: no cover - optional dependency
    AECEnv = object
    agent_selector = None


@dataclass
class _ActionSlot:
    action: Optional[Action]


class WarEnv(AECEnv):
    metadata = {"render_modes": ["human", "rgb_array"], "name": "resiliencesim_v1"}

    def __init__(self, scenario_path: str, render_mode: str = None):
        if Box is None or Discrete is None or agent_selector is None or AECEnv is object:
            raise RuntimeError(
                "WarEnv requires pettingzoo and gymnasium to be installed."
            )
        super().__init__()
        self.scenario_path = scenario_path
        self.render_mode = render_mode
        self.possible_agents = list(config.NATIONS)
        self.agents: List[str] = []
        self._state: ScenarioState | None = None
        self._grid: WorldGrid | None = None
        self._pending_actions: Dict[str, Optional[Action]] = {}
        self._action_slots: Dict[str, List[_ActionSlot]] = {}
        self._last_result: TurnResult | None = None
        self._agent_selector = None
        self.agent_selection: str | None = None
        self.rewards: Dict[str, float] = {}
        self._cumulative_rewards: Dict[str, float] = {}
        self.terminations: Dict[str, bool] = {}
        self.truncations: Dict[str, bool] = {}
        self.infos: Dict[str, dict] = {}
        self._observation_spaces: Dict[str, Box] = {}
        self._action_spaces: Dict[str, Discrete] = {}

    def observation_space(self, agent: str):
        return self._observation_spaces[agent]

    def action_space(self, agent: str):
        return self._action_spaces[agent]

    def reset(self, seed=None, options=None) -> None:
        del seed, options
        self._state, self._grid = load_scenario(self.scenario_path)
        self.agents = self.possible_agents[:]
        self._pending_actions = {agent: None for agent in self.agents}
        self._last_result = None
        self.rewards = {agent: 0.0 for agent in self.agents}
        self._cumulative_rewards = {agent: 0.0 for agent in self.agents}
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}
        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.reset()
        self._refresh_spaces()

    def step(self, action: int) -> None:
        if self.agent_selection is None or self._state is None:
            raise RuntimeError("WarEnv.reset() must be called before step().")

        agent = self.agent_selection
        if self.terminations.get(agent) or self.truncations.get(agent):
            self._was_dead_step(action)
            return

        decoded_action = self.decode_action(agent, action)
        self._pending_actions[agent] = decoded_action
        self._cumulative_rewards[agent] = 0.0

        if self._agent_selector.is_last():
            submitted_actions = [
                pending
                for pending in self._pending_actions.values()
                if pending is not None
            ]
            self._last_result = step_simulation(self._state, submitted_actions)
            self._state = self._last_result.new_state
            self._pending_actions = {name: None for name in self.agents}
            self._refresh_spaces()
            self._update_rewards()
            self._update_dones()
            self.infos = {
                nation: {"end_condition": self._state.end_conditions_met.get(nation)}
                for nation in self.agents
            }
        else:
            self._clear_rewards()

        self.agent_selection = self._agent_selector.next()

    def observe(self, agent: str) -> np.ndarray:
        if self._state is None:
            raise RuntimeError("WarEnv.reset() must be called before observe().")
        own_assets = sorted(self._state.get_assets_for(agent), key=lambda asset: asset.id)
        own_zones = sorted(self._state.get_zones_for(agent), key=lambda zone: zone.id)
        resource_fractions = {}
        stock = self._state.resources.get(agent)
        for resource_type, spec in config.RESOURCE_TYPES.items():
            amount = float(stock.stocks.get(resource_type, 0.0)) if stock else 0.0
            starting = float(spec["starting"])
            resource_fractions[resource_type] = min(max(amount / starting, 0.0), 1.0) if starting > 0 else 0.0

        consequence_order = sorted(
            {tag for tags in config.CONSEQUENCE_MAP.values() for tag in tags}
        )
        active_tags = set(self._state.active_consequences.get(agent, []))
        observation = AgentObservation(
            turn_normalised=min(max(self._state.turn / max(self._state.max_turns, 1), 0.0), 1.0),
            nation=agent,
            own_asset_health=[min(max(asset.health_fraction(), 0.0), 1.0) for asset in own_assets],
            zone_service_coverage=[min(max(zone.service_coverage, 0.0), 1.0) for zone in own_zones],
            zone_displacement_fraction=[
                min(max(zone.displacement_fraction(), 0.0), 1.0) for zone in own_zones
            ],
            resource_fractions=resource_fractions,
            active_consequence_flags=[1 if tag in active_tags else 0 for tag in consequence_order],
            stable_turns_count=int(self._state.stable_turns_count.get(agent, 0)),
            service_coverage_score=min(max(self._state.service_coverage_score(agent), 0.0), 1.0),
        )
        flat = [
            observation.turn_normalised,
            *observation.own_asset_health,
            *observation.zone_service_coverage,
            *observation.zone_displacement_fraction,
            *[observation.resource_fractions[key] for key in config.RESOURCE_TYPES],
            *observation.active_consequence_flags,
            min(observation.stable_turns_count / 3.0, 1.0),
            observation.service_coverage_score,
        ]
        return np.asarray(flat, dtype=np.float32)

    def render(self):
        if self._state is None:
            return None
        if self.render_mode == "rgb_array":
            height = self._grid.rows if self._grid else config.GRID_ROWS
            width = self._grid.cols if self._grid else config.GRID_COLS
            return np.zeros((height, width, 3), dtype=np.uint8)
        logger.info(
            "WarEnv render turn {} terminal={}",
            self._state.turn,
            self._state.is_terminal,
        )
        return None

    def close(self) -> None:
        self._state = None
        self._grid = None
        self.agents = []

    def decode_action(self, agent: str, action_int: int) -> Optional[Action]:
        slots = self._build_action_slots(agent)
        if action_int < 0 or action_int >= len(slots):
            return None
        return slots[action_int].action

    def _build_action_slots(self, agent: str) -> List[_ActionSlot]:
        if self._state is None:
            return [_ActionSlot(None)]

        own_assets = sorted(self._state.get_assets_for(agent), key=lambda asset: asset.id)
        own_zones = sorted(self._state.get_zones_for(agent), key=lambda zone: zone.id)
        stock = self._state.resources.get(agent)
        slots: List[_ActionSlot] = [_ActionSlot(None)]

        for action_type, action_cfg in config.ACTION_TYPES.items():
            if stock and not stock.can_afford(action_cfg["cost"]):
                continue

            if action_type == "evacuate":
                for zone in own_zones:
                    if zone.displaced < zone.population:
                        slots.append(
                            _ActionSlot(
                                Action(
                                    actor_nation=agent,
                                    action_type=action_type,
                                    target_zone_id=zone.id,
                                )
                            )
                        )
                continue

            for asset in own_assets:
                if asset.asset_type not in action_cfg["valid_targets"]:
                    continue
                slots.append(
                    _ActionSlot(
                        Action(
                            actor_nation=agent,
                            action_type=action_type,
                            target_asset_id=asset.id,
                        )
                    )
                )

        self._action_slots[agent] = slots
        return slots

    def _refresh_spaces(self) -> None:
        if self._state is None:
            return

        consequence_order = sorted(
            {tag for tags in config.CONSEQUENCE_MAP.values() for tag in tags}
        )
        for agent in self.agents:
            own_asset_count = len(self._state.get_assets_for(agent))
            own_zone_count = len(self._state.get_zones_for(agent))
            obs_size = (
                1
                + own_asset_count
                + own_zone_count
                + own_zone_count
                + len(config.RESOURCE_TYPES)
                + len(consequence_order)
                + 1
                + 1
            )
            self._observation_spaces[agent] = Box(
                low=0.0,
                high=1.0,
                shape=(obs_size,),
                dtype=np.float32,
            )
            action_slots = self._build_action_slots(agent)
            self._action_spaces[agent] = Discrete(len(action_slots))

    def _update_rewards(self) -> None:
        if self._state is None or self._last_result is None:
            return
        rewards = {agent: 0.0 for agent in self.agents}
        for asset_id in self._last_result.assets_repaired:
            asset = self._state.get_asset(asset_id)
            if asset and asset.is_critical:
                rewards[asset.nation] += 1.0
        for nation in self.agents:
            displaced = sum(zone.displaced for zone in self._state.get_zones_for(nation))
            rewards[nation] -= 0.001 * displaced
            condition = self._state.end_conditions_met.get(nation)
            if condition == "stabilised":
                rewards[nation] += 10.0
            elif condition == "collapsed":
                rewards[nation] -= 10.0
        self.rewards = rewards

    def _update_dones(self) -> None:
        if self._state is None:
            return
        for nation in self.agents:
            condition = self._state.end_conditions_met.get(nation)
            self.terminations[nation] = condition in {"stabilised", "collapsed"}
            self.truncations[nation] = condition == "timeout"

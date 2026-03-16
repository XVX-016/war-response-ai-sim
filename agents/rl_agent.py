from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

try:
    import supersuit as ss
except ImportError:  # pragma: no cover - optional dependency
    ss = None

try:
    from stable_baselines3 import PPO
except ImportError:  # pragma: no cover - optional dependency
    PPO = None

from agents.env import WarEnv


class RLAgent:
    def __init__(self, nation: str, model_path: Optional[str] = None):
        self.nation = nation
        self._model = None
        self._trained = False
        if model_path and Path(model_path).exists():
            self.load(model_path)

    def train(
        self,
        scenario_path: str,
        total_timesteps: int = 500_000,
        opponent: str = "rule",
    ) -> None:
        del opponent
        if PPO is None or ss is None:
            raise RuntimeError(
                "RLAgent.train requires stable-baselines3 and supersuit to be installed."
            )

        env = WarEnv(scenario_path)
        vec_env = ss.pettingzoo_env_to_vec_env_v1(env)
        self._model = PPO(
            "MlpPolicy",
            vec_env,
            verbose=1,
            tensorboard_log="logs/rl_training/",
        )
        logger.info(
            "Training RLAgent for nation {} on {} timesteps={}",
            self.nation,
            scenario_path,
            total_timesteps,
        )
        self._model.learn(total_timesteps=total_timesteps, progress_bar=False)
        self._trained = True

    def predict(self, obs: np.ndarray) -> int:
        if not self.is_trained():
            return 0
        action, _ = self._model.predict(obs, deterministic=True)
        return int(action)

    def save(self, path: str) -> None:
        if not self.is_trained():
            raise RuntimeError("Cannot save an untrained RLAgent.")
        self._model.save(path)

    def load(self, path: str) -> None:
        if PPO is None:
            raise RuntimeError("RLAgent.load requires stable-baselines3 to be installed.")
        self._model = PPO.load(path)
        self._trained = True

    def is_trained(self) -> bool:
        return bool(self._trained and self._model is not None)


if __name__ == "__main__":  # pragma: no cover - manual training entrypoint
    agent = RLAgent(nation="Auria")
    agent.train(
        scenario_path="data/scenarios/cascade_crisis.json",
        total_timesteps=500_000,
    )
    agent.save("models/rl_auria_ppo")
    print("Training complete")

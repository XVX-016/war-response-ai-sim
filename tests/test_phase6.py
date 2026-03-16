from __future__ import annotations

import numpy as np

from agents.rl_agent import RLAgent


class TestRLAgent:
    def test_untrained_predict_returns_pass(self):
        agent = RLAgent(nation="Auria")
        obs = np.zeros(30, dtype=np.float32)
        assert agent.predict(obs) == 0


class TestWarEnvImport:
    def test_env_module_imports(self):
        import agents.env as env_module

        assert hasattr(env_module, "WarEnv")

    def test_env_init_requires_optional_dependencies_or_constructs(self):
        import agents.env as env_module

        try:
            env = env_module.WarEnv("data/scenarios/cascade_crisis.json")
        except RuntimeError as exc:
            assert "pettingzoo" in str(exc).lower() or "gymnasium" in str(exc).lower()
        else:
            env.reset()
            assert env.observe("Auria").dtype == np.float32

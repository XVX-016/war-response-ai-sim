from __future__ import annotations

import config
from ai_narrator import ClaudeNarrator
from agents.rule_agent import select_actions
from engine.turn_engine import step_simulation
from engine.world import load_scenario


class _FakeText:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeText(text)]


class _FakeMessages:
    def create(self, **kwargs):
        return _FakeResponse("Emergency teams restore partial services while displaced residents continue to need shelter support.")


class _FakeClient:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


class TestClaudeNarrator:
    def test_missing_key_returns_unavailable(self, monkeypatch):
        monkeypatch.setattr(config, 'ANTHROPIC_API_KEY', '')
        narrator = ClaudeNarrator()
        assert narrator.is_available() is False

    def test_missing_key_generate_returns_empty(self, monkeypatch):
        monkeypatch.setattr(config, 'ANTHROPIC_API_KEY', '')
        monkeypatch.setattr(config, 'DISABLE_NARRATOR', False)
        narrator = ClaudeNarrator()
        state, _ = load_scenario('data/scenarios/cascade_crisis.json')
        result = step_simulation(state, [])
        assert narrator.generate_narrative(result) == ''

    def test_generate_narrative_with_fake_client(self, monkeypatch):
        monkeypatch.setattr(config, 'ANTHROPIC_API_KEY', 'test-key')
        monkeypatch.setattr(config, 'DISABLE_NARRATOR', False)
        narrator = ClaudeNarrator()
        narrator._available = True
        narrator._client = _FakeClient()
        state, _ = load_scenario('data/scenarios/cascade_crisis.json')
        actions = select_actions(state, 'Auria') + select_actions(state, 'Boros')
        result = step_simulation(state, actions)
        text = narrator.generate_narrative(result)
        assert isinstance(text, str)
        assert len(text) > 0

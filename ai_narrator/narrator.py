from __future__ import annotations

from typing import Any

from loguru import logger

import config
from schemas import TurnResult


class ClaudeNarrator:
    def __init__(self) -> None:
        self._available = False
        self._client = None
        if not config.ANTHROPIC_API_KEY:
            logger.warning("ClaudeNarrator unavailable: ANTHROPIC_API_KEY is not set")
            return
        try:
            import anthropic
        except ImportError:
            logger.warning("ClaudeNarrator unavailable: anthropic package is not installed")
            return
        try:
            self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            self._available = True
        except Exception as exc:
            logger.warning("ClaudeNarrator client init failed: {}", exc)
            self._client = None
            self._available = False

    def is_available(self) -> bool:
        return bool(self._available and config.ANTHROPIC_API_KEY)

    def _asset_names(self, ids: list[str], turn_result: TurnResult) -> list[str]:
        names = []
        for asset_id in ids:
            asset = turn_result.new_state.get_asset(asset_id)
            names.append(asset.name if asset else asset_id)
        return names

    def _build_prompt(self, turn_result: TurnResult) -> str:
        repaired = ", ".join(self._asset_names(turn_result.assets_repaired, turn_result)) or "none"
        degraded = ", ".join(self._asset_names(turn_result.assets_degraded, turn_result)) or "none"
        consequences = []
        for nation, tags in turn_result.new_consequences.items():
            if tags:
                consequences.append(f"{nation}: {', '.join(tags)}")
        consequence_text = "; ".join(consequences) or "none"
        exogenous = ", ".join(turn_result.exogenous_events) or "none"
        coverage = ", ".join(f"{nation}={score:.0%}" for nation, score in turn_result.service_coverage.items()) or "none"
        displaced = ", ".join(f"{nation}={count:,}" for nation, count in turn_result.total_displaced.items()) or "none"
        end_condition = turn_result.end_condition or "none"
        return (
            f"Turn: {turn_result.turn}\n"
            f"Service coverage: {coverage}\n"
            f"Displaced persons: {displaced}\n"
            f"Assets repaired: {repaired}\n"
            f"Assets degraded: {degraded}\n"
            f"Active consequences: {consequence_text}\n"
            f"Exogenous events: {exogenous}\n"
            f"End condition: {end_condition}\n"
        )

    def generate_narrative(self, turn_result: TurnResult) -> str:
        if not self.is_available() or config.DISABLE_NARRATOR:
            return ""

        system_prompt = (
            "You write exactly 2-3 sentences in present tense with humanitarian and civil-protection framing only. "
            "Never mention weapons, military, or combat. Focus on civilian impact, infrastructure status, "
            "and recovery progress in a neutral tone."
        )
        user_prompt = self._build_prompt(turn_result)
        try:
            response: Any = self._client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=config.CLAUDE_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            parts = getattr(response, 'content', []) or []
            text = " ".join(getattr(part, 'text', '') for part in parts).strip()
            return text
        except Exception as exc:
            logger.warning("ClaudeNarrator generation failed: {}", exc)
            return ""

"""Market Radar — AI Fallback Interpreter (Signal Spine v1).

Core pipeline logic MUST NOT depend on AI/ML model availability.
This module:

  1. Provides a pluggable AI interpreter interface for observations
     that require natural language interpretation.
  2. When AI is unavailable, generates deterministic template-based
     interpretations from structured data.
  3. All dedup, threshold, state, and numeric logic remains
     deterministic regardless of AI availability.

The fallback interpreter ensures the pipeline never blocks on
an external model API. Template explanations are clearly marked
as "template_generated" vs "ai_generated".
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.shared.models import (
    Observation,
    Signal,
    china_now,
    sha256_short,
    SIGNAL_SPINE_VERSION,
)


class InterpretationResult:
    """Result of interpreting an observation, whether by AI or template.

    Attributes:
        event_title: Human-readable event title.
        direction: bullish / bearish / neutral.
        confidence: 0.0-1.0 estimated confidence.
        event_type: Classified event type.
        explanation: Human-readable explanation.
        interpretation_method: "ai_generated" | "template_generated".
        assets_affected: List of asset tickers identified.
        risk_notes: Safety notes about the interpretation.
        raw: The original interpretation data.
    """
    def __init__(
        self,
        event_title: str,
        direction: str,
        confidence: float,
        event_type: str,
        explanation: str,
        interpretation_method: str,
        assets_affected: list[str],
        risk_notes: Optional[list[str]] = None,
        raw: Optional[dict[str, Any]] = None,
    ):
        self.event_title = event_title
        self.direction = direction
        self.confidence = max(0.0, min(1.0, confidence))
        self.event_type = event_type
        self.explanation = explanation
        self.interpretation_method = interpretation_method
        self.assets_affected = list(assets_affected)
        self.risk_notes = risk_notes or []
        self.raw = raw or {}

    def to_dict(self) -> dict:
        return {
            "event_title": self.event_title,
            "direction": self.direction,
            "confidence": self.confidence,
            "event_type": self.event_type,
            "explanation": self.explanation,
            "interpretation_method": self.interpretation_method,
            "assets_affected": self.assets_affected,
            "risk_notes": self.risk_notes,
        }


# ── Template-Based Explanation Generator ─────────────────────────────────


def _intensity_to_direction(intensity: str) -> str:
    """Map event intensity to a directional bias.

    High intensity → more likely directional.
    Low intensity → neutral by default.
    """
    mapping = {
        "high": "bullish",
        "medium": "neutral",
        "low": "neutral",
        "critical": "bearish",
    }
    return mapping.get(intensity, "neutral")


def _intensity_to_confidence(intensity: str) -> float:
    """Map intensity to a heuristic confidence score."""
    mapping = {"high": 0.65, "medium": 0.45, "low": 0.25, "critical": 0.60}
    return mapping.get(intensity, 0.3)


def _asset_count_to_relevance(asset_count: int) -> str:
    """Heuristic: more assets → broader relevance."""
    if asset_count >= 3:
        return "high"
    elif asset_count >= 1:
        return "medium"
    return "low"


def generate_template_interpretation(observation: Observation) -> InterpretationResult:
    """Generate a deterministic template-based interpretation.

    Used when AI interpretation is unavailable. All logic is
    rule-based and deterministic. Template outputs are clearly
    marked with interpretation_method="template_generated".

    This function NEVER fabricates data — it only transforms
    what's available in the observation into a structured
    interpretation.
    """
    payload = observation.normalized_payload

    # Extract available data
    title = payload.get("title", "")
    event_type = payload.get("event_type", "unknown")
    intensity = payload.get("intensity", "unknown")
    source_name = payload.get("source_name", observation.source)
    assets = observation.affected_assets

    # If no title, attempt to build one from data
    if not title:
        if assets:
            title = f"{event_type.replace('_', ' ').title()} event affecting {', '.join(assets[:3])}"
        else:
            title = f"{event_type.replace('_', ' ').title()} event from {source_name}"

    # Direction and confidence from intensity
    direction = _intensity_to_direction(intensity)
    confidence = _intensity_to_confidence(intensity)

    # Relevance from asset count
    trading_relevance = _asset_count_to_relevance(len(assets))

    # Generate explanation
    explanation_parts = [
        f"[Template Interpretation — No AI available]",
        f"Event: {title}",
        f"Type: {event_type}",
        f"Source: {source_name}",
    ]

    if intensity != "unknown":
        explanation_parts.append(f"Intensity: {intensity}")

    if assets:
        explanation_parts.append(f"Assets: {', '.join(assets[:5])}")

    if confidence > 0:
        explanation_parts.append(f"Heuristic confidence: {confidence:.2f}")

    explanation_parts.append(
        "Interpretation generated by deterministic template — "
        "does not represent AI analysis or market advice."
    )

    explanation = "\n".join(explanation_parts)

    # Risk notes
    risk_notes = [
        "template_generated: no AI model was consulted for this interpretation",
        "confidence is heuristic based on event intensity, not market analysis",
        "direction is a best-guess from event metadata, not a trading signal",
    ]

    if trading_relevance == "low":
        risk_notes.append("low trading relevance: limited asset coverage")

    return InterpretationResult(
        event_title=title,
        direction=direction,
        confidence=confidence,
        event_type=event_type,
        explanation=explanation,
        interpretation_method="template_generated",
        assets_affected=assets,
        risk_notes=risk_notes,
    )


# ── AI Interpreter Interface (Pluggable) ──────────────────────────────────


class AIInterpreter:
    """Pluggable AI interpreter for observation text.

    This class provides the INTERFACE for AI-powered interpretation.
    When AI is unavailable, it falls back to template generation.

    The interface is preserved so that future AI integration can
    plug in without changing the orchestrator. When AI is connected,
    set `self._available = True`.
    """

    def __init__(self, available: bool = False):
        self._available = available
        self._version = SIGNAL_SPINE_VERSION
        self._fallback_count = 0

    @property
    def is_available(self) -> bool:
        return self._available

    def set_available(self, available: bool) -> None:
        self._available = available

    def interpret(self, observation: Observation) -> InterpretationResult:
        """Interpret an observation.

        If AI is available, this would call the AI model.
        If AI is NOT available (default), generates a template interpretation.

        The orchestrator calls this method — it never blocks on AI.
        """
        if self._available:
            # AI is available — call the model interface
            # (Stub: actual AI integration would go here)
            return self._ai_interpret(observation)

        # AI not available — deterministic fallback
        self._fallback_count += 1
        return generate_template_interpretation(observation)

    def _ai_interpret(self, observation: Observation) -> InterpretationResult:
        """Stub for AI model integration.

        When an actual AI model is connected, this method would:
          1. Prepare the observation text for the model
          2. Call the model API
          3. Parse the response into InterpretationResult
          4. Set interpretation_method = "ai_generated"

        For now, falls back to template to keep the pipeline running.
        """
        # In production, this is where the AI API call would go.
        # Returning template to NOT block the pipeline.
        self._fallback_count += 1
        result = generate_template_interpretation(observation)
        # Override to indicate AI was available but not yet implemented
        result.interpretation_method = "template_generated"
        return result


def create_ai_interpreter(available: bool = False) -> AIInterpreter:
    """Factory: create an AI interpreter with fallback."""
    return AIInterpreter(available=available)

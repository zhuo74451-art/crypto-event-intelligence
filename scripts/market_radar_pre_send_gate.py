"""
Market Radar v1.10-G — pre_send_gate 通用发送前安全接口

Abstracts SignalTrustGate + payload validation into a single reusable entry point
that any TG sender can call before sending. Designed to prevent:
  - Sends without gate check
  - Sends with empty/missing payload
  - Inconsistent gate→payload validation ordering

Usage:
    from scripts.market_radar_pre_send_gate import pre_send_gate

    precheck = pre_send_gate(signal, payload, target_env="test")
    if not precheck["allowed"]:
        print(f"Blocked: {precheck['blocked_reason']}")
        return  # stop before send

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

from typing import Any

from scripts.market_radar_signal_trust_gate import (
    SignalTrustGate,
    GATE_VERSION,
    build_signal_hash,
)


def pre_send_gate(signal: dict, payload: dict, target_env: str = "test") -> dict:
    """Universal pre-send safety gate for TG card delivery.

    Combines two layers of pre-send checks:
      1. SignalTrustGate.check(signal, target_env) — source trust + TTL + signal validity
      2. Payload validation — text must be present and non-empty, parse_mode must be present

    Args:
        signal: The signal dict (must have at minimum: signal_type or inferrable fields,
                source_type, and a time field like generated_at / observed_at).
        payload: The rendered payload dict from render_card_payload().
                 Must contain at minimum: "text" (non-empty str) and "parse_mode".
        target_env: "test" or "prod". Default "test".

    Returns:
        Dict with keys:
          - allowed: bool — True only if BOTH gate and payload checks pass
          - target_env: str — the target_env that was checked
          - gate_result: dict — full gate check result from SignalTrustGate
          - payload_ok: bool — True if payload text is non-empty and parse_mode present
          - blocked_reason: str | None — why it was blocked (None if allowed)
          - signal_hash: str — deterministic 16-char hash for tracking
          - gate_version: str — Gate version string

    Security: No credentials are read, printed, or saved.
    """
    gate = SignalTrustGate()
    gate_result = gate.check(signal, target_env=target_env)
    signal_hash = gate_result.get("signal_hash", build_signal_hash(signal))

    # ── Payload checks ──
    payload_ok = True
    blocked_reason = None

    # Check payload is a dict with expected keys
    if not isinstance(payload, dict):
        payload_ok = False
        blocked_reason = "Payload is not a dict"
    elif "text" not in payload:
        payload_ok = False
        blocked_reason = "Payload missing 'text' field"
    elif not payload.get("text") or not isinstance(payload["text"], str) or not payload["text"].strip():
        payload_ok = False
        blocked_reason = "Payload text is empty or whitespace-only"
    elif "parse_mode" not in payload:
        payload_ok = False
        blocked_reason = "Payload missing 'parse_mode' field"
    elif not gate_result["allowed"]:
        payload_ok = True  # gate already blocked, payload might be fine
        blocked_reason = gate_result.get("blocked_reason", "Gate blocked")
    else:
        # Both gate and payload pass
        payload_ok = True
        blocked_reason = None

    # If gate blocked and we didn't already set blocked_reason
    if not gate_result["allowed"] and blocked_reason is None:
        blocked_reason = gate_result.get("blocked_reason", "Gate blocked")

    allowed = gate_result["allowed"] and payload_ok

    return {
        "allowed": allowed,
        "target_env": target_env,
        "gate_result": gate_result,
        "payload_ok": payload_ok,
        "blocked_reason": blocked_reason,
        "signal_hash": signal_hash,
        "gate_version": GATE_VERSION,
    }

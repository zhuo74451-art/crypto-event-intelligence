"""
Market Radar Sender v1.9A — 正式发送组件 MVP

Extracts reusable logic from v1.8H archived scripts:
  - scripts/_archive/v18h/v18h_single_card_tg_send.py
  - scripts/_archive/v18h/v18h_verify_chat_type.py

This component is DRY-RUN ONLY. It does NOT call any external APIs.
TG API integration will be added in v1.9B+ after component dry-run validation.

Components:
  - load_candidate()              — Load candidate from markdown + JSON
  - load_preview_gate()           — Parse preview report for gate values
  - validate_preview_gate()       — Check all gate conditions
  - build_send_payload()          — Build send payload from candidate markdown
  - dry_run_send()                — Simulate send with max_send_count check
  - write_send_handoff()          — Write structured result handoff
  - load_schema()                 — Load v1.9A schema contract JSON (v1.9A-S1)
  - validate_manifest()           — Validate manifest against schema (v1.9A-S1)
  - build_manifest_from_paths()   — Build manifest from file paths (v1.9A-S1)

v1.9A-S2 additions:
  - PolicyReceipt                 — Policy result with effective_data
  - validate_runtime_source_paths() — Relative path + whitelist checks
  - validate_types_and_ranges()   — Type + value-range boundary checks
  - sanitize_flexible_payload()   — Truncation, control char removal, escaping
  - apply_policy()                — Lane 1 policy (max_send_count trim)
  - validate_and_apply_policy()   — Full S2 pipeline

v1.9B additions:
  - BaseTransport / FakeTransport / TGTransportStub — Transport interface
  - MarketRadarSender             — Sender Core with dependency injection
  - SendResult v1.9B fields       — success, error_type, provider, provider_metadata

v1.9B-final Prep additions:
  - TGTransport                   — Real TG API adapter (HTTP client injection, no env reading)
  - HttpClient / MockHttpClient   — HTTP abstraction for testable TGTransport
  - provider_metadata redaction   — bot_token / chat_id never appear in outputs

v1.9B-final R1 additions:
  - RealHttpClient                — Production HTTP adapter using requests.post
  - Monkeypatch tests             — RealHttpClient tested without real network calls
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import unicodedata
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

# ---------------------------------------------------------------------------
# Constants (v1.9A-S2)
# ---------------------------------------------------------------------------

SCHEMA_VERSION_REQUIRED = "1.9A-S2"

RUNTIME_SOURCE_FIELDS = [
    "candidate_md_path",
    "candidate_json_path",
    "preview_report_path",
]

ALLOWED_DIR_PREFIXES = [
    "results/",
    "runs/",
    "schemas/",
]

# Parse mode normalization: lowercased key → canonical
CANONICAL_PARSE_MODES = {
    "html": "HTML",
    "markdownv2": "MarkdownV2",
    "plaintext": "PlainText",
    "plain": "PlainText",
    "text": "PlainText",
    "markdown": "MarkdownV2",  # legacy
    "md": "MarkdownV2",  # legacy
}

# Target type normalization: lowercased key → canonical
CANONICAL_TARGET_TYPES = {
    "group": "group",
    "supergroup": "supergroup",
    "test_group": "test_group",
    "fake": "fake",
    "tg群": "group",          # legacy Chinese
    "tg频道": "supergroup",    # legacy Chinese
    "tg channel": "supergroup",
    "dry-run": "test_group",  # legacy
    "dry_run": "test_group",  # legacy
    "test": "test_group",
}

# Flexible Payload field max lengths
FLEX_MAX_LENGTHS = {
    "token_name": 32,
    "symbol": 16,
    "wallet_short": 24,
    "extra_context": 280,
}

# MarkdownV2 special characters that need escaping
_MD_V2_SPECIALS = set(r'_*[]()~`>#+-=|{}.!')


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class GateResult:
    """Result of a single gate check."""
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


class SendResult:
    """Structured result of a send operation (or dry-run).

    v1.9B adds standardized transport-level fields:
      - success, status_code, error_type, error_message, retry_after
      - provider, provider_metadata
    All new fields have backward-compatible defaults.
    """
    def __init__(
        self,
        status: str = "done",
        sent_count: int = 0,
        max_send_count: int = 1,
        message_id: str = "",
        target_type: str = "group",
        tg_api_called: bool = False,
        sent_exceed_1: bool = False,
        sent_channel: bool = False,
        loop_started: bool = False,
        sensitive_printed: bool = False,
        remote_db_written: bool = False,
        dry_run: bool = True,
        gate_results: Optional[list[GateResult]] = None,
        error: str = "",
        # --- v1.9B transport-level fields ---
        success: bool = True,
        status_code: int = 0,
        error_type: str = "",
        error_message: str = "",
        retry_after: Optional[int] = None,
        provider: str = "",
        provider_metadata: Optional[dict[str, Any]] = None,
    ):
        self.status = status
        self.sent_count = sent_count
        self.max_send_count = max_send_count
        self.message_id = message_id
        self.target_type = target_type
        self.tg_api_called = tg_api_called
        self.sent_exceed_1 = sent_exceed_1
        self.sent_channel = sent_channel
        self.loop_started = loop_started
        self.sensitive_printed = sensitive_printed
        self.remote_db_written = remote_db_written
        self.dry_run = dry_run
        self.gate_results = gate_results or []
        self.error = error
        # v1.9B
        self.success = success
        self.status_code = status_code
        self.error_type = error_type
        self.error_message = error_message
        self.retry_after = retry_after
        self.provider = provider
        self.provider_metadata = provider_metadata or {}

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "sent_count": self.sent_count,
            "max_send_count": self.max_send_count,
            "message_id": self.message_id,
            "target_type": self.target_type,
            "tg_api_called": self.tg_api_called,
            "sent_exceed_1": self.sent_exceed_1,
            "sent_channel": self.sent_channel,
            "loop_started": self.loop_started,
            "sensitive_printed": self.sensitive_printed,
            "remote_db_written": self.remote_db_written,
            "dry_run": self.dry_run,
            "gate_results": [g.to_dict() for g in self.gate_results],
            "error": self.error,
            # v1.9B
            "success": self.success,
            "status_code": self.status_code,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "retry_after": self.retry_after,
            "provider": self.provider,
            "provider_metadata": self.provider_metadata,
        }


class PolicyReceipt:
    """Result of applying lane policy + sanitization to a manifest.

    v1.9A-S2: PolicyReceipt carries effective_data (the adjusted, sanitized
    copy) and tracks what was changed. raw_manifest is NEVER modified in-place.

    Consumption rules:
      - errors non-empty → BLOCK (do not proceed)
      - adjusted_fields non-empty → MUST use effective_data for downstream
      - warnings → log only, do not block
    """

    def __init__(
        self,
        status: str = "ok",
        warnings: Optional[list[str]] = None,
        errors: Optional[list[str]] = None,
        adjusted_fields: Optional[list[str]] = None,
        effective_data: Optional[dict[str, Any]] = None,
    ):
        self.status = status          # "ok" | "adjusted" | "blocked"
        self.warnings = warnings or []
        self.errors = errors or []
        self.adjusted_fields = adjusted_fields or []
        self.effective_data = effective_data or {}

    @property
    def is_blocked(self) -> bool:
        return len(self.errors) > 0

    @property
    def was_adjusted(self) -> bool:
        return len(self.adjusted_fields) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "warnings": self.warnings,
            "errors": self.errors,
            "adjusted_fields": self.adjusted_fields,
        }


# ---------------------------------------------------------------------------
# Utility: path helpers
# ---------------------------------------------------------------------------

def _make_relative_path(p: str | Path, root: Path = ROOT) -> str:
    """Convert a path to relative (from root) if absolute."""
    pp = Path(p)
    if pp.is_absolute():
        try:
            return str(pp.relative_to(root)).replace("\\", "/")
        except ValueError:
            return str(p)
    return str(pp).replace("\\", "/")


# ---------------------------------------------------------------------------
# Utility: control character removal
# ---------------------------------------------------------------------------

def remove_control_chars(s: str) -> str:
    """Remove Unicode control characters except common whitespace (\\n, \\r, \\t)."""
    return ''.join(
        ch for ch in s
        if unicodedata.category(ch)[0] != 'C' or ch in ('\n', '\r', '\t')
    )


# ---------------------------------------------------------------------------
# Utility: parse mode normalization
# ---------------------------------------------------------------------------

def normalize_parse_mode(value: Any) -> Optional[str]:
    """Normalize parse_mode to canonical: HTML, MarkdownV2, PlainText.

    Returns None if the value cannot be normalized.
    """
    if not isinstance(value, str):
        return None
    key = value.strip().lower().replace(" ", "")
    return CANONICAL_PARSE_MODES.get(key)


# ---------------------------------------------------------------------------
# Utility: target type normalization
# ---------------------------------------------------------------------------

def normalize_target_type(value: Any) -> Optional[str]:
    """Normalize target_type to canonical: group, supergroup, test_group, fake.

    Returns None if the value cannot be normalized.
    """
    if not isinstance(value, str):
        return None
    key = value.strip().lower().replace(" ", "")
    return CANONICAL_TARGET_TYPES.get(key)


# ---------------------------------------------------------------------------
# Utility: escaping for parse modes
# ---------------------------------------------------------------------------

def escape_html(text: str) -> str:
    """Escape < > & for HTML parse mode."""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text


def escape_markdown_v2(text: str) -> str:
    """Escape MarkdownV2 special characters: _ * [ ] ( ) ~ ` > # + - = | { } . !"""
    result = []
    for ch in text:
        if ch in _MD_V2_SPECIALS:
            result.append('\\' + ch)
        else:
            result.append(ch)
    return ''.join(result)


def sanitize_for_parse_mode(text: str, parse_mode: str) -> str:
    """Apply parse-mode-specific escaping to text.

    - HTML: escape < > &
    - MarkdownV2: escape _ * [ ] ( ) ~ ` > # + - = | { } . !
    - PlainText / unknown: strip HTML tags, replace Markdown specials with spaces
    """
    if parse_mode == "HTML":
        return escape_html(text)
    elif parse_mode == "MarkdownV2":
        return escape_markdown_v2(text)
    else:
        # PlainText or unrecognized: strip HTML tags, neutralize markdown
        cleaned = re.sub(r'<[^>]*>', '', text)
        cleaned = cleaned.replace('_', ' ').replace('*', ' ').replace('`', ' ')
        cleaned = cleaned.replace('[', '(').replace(']', ')')
        return cleaned


# ---------------------------------------------------------------------------
# Core component functions
# ---------------------------------------------------------------------------

def load_candidate(
    candidate_md_path: str | Path,
    candidate_json_path: str | Path,
) -> dict[str, Any]:
    """
    Load candidate from markdown and JSON files.

    Returns dict with keys:
      - md_text: str       — raw markdown content
      - md_len: int        — character count
      - json_data: dict    — parsed JSON data
      - json_valid: bool   — whether JSON parsed successfully
    """
    md_path = Path(candidate_md_path)
    if not md_path.is_absolute():
        md_path = ROOT / md_path
    if not md_path.exists():
        raise FileNotFoundError(f"Candidate markdown not found: {md_path}")
    md_text = md_path.read_text(encoding="utf-8-sig", errors="replace").strip()
    if not md_text:
        raise ValueError(f"Candidate markdown is empty: {md_path}")

    json_path = Path(candidate_json_path)
    if not json_path.is_absolute():
        json_path = ROOT / json_path
    json_valid = False
    json_data: dict[str, Any] = {}
    if json_path.exists():
        try:
            json_data = json.loads(
                json_path.read_text(encoding="utf-8-sig", errors="replace")
            )
            json_valid = True
        except json.JSONDecodeError as e:
            json_valid = False
            json_data = {"_parse_error": str(e)}
    else:
        json_data = {"_missing": str(json_path)}

    return {
        "md_text": md_text,
        "md_len": len(md_text),
        "json_data": json_data,
        "json_valid": json_valid,
        "md_path": str(md_path),
        "json_path": str(json_path),
    }


def load_preview_gate(preview_report_path: str | Path) -> dict[str, Any]:
    """
    Parse preview report markdown and extract gate-relevant fields.

    Extracts:
      - blocked: bool           — from JSON candidate data
      - blocked_reasons: list   — reasons for blocking
      - leak_count: int         — count of sensitive info leaks detected
      - full_address_count: int — count of full wallet addresses detected
      - consistency_status: str — pass/fail
      - forbidden_terms_count: int
      - machine_terms_count: int
      - should_send_now: bool
      - requires_user_confirmation: bool
      - dry_run_only: bool
      - report_indicators: dict — raw gate indicators parsed from report text
    """
    rp = Path(preview_report_path)
    if not rp.is_absolute():
        rp = ROOT / rp
    if not rp.exists():
        raise FileNotFoundError(f"Preview report not found: {rp}")

    text = rp.read_text(encoding="utf-8-sig", errors="replace")

    # Parse indicators from the markdown report
    indicators: dict[str, Any] = {
        "file_found": "输入文件检查" in text,
        "blocked_ok": False,
        "blocked_reasons_empty": True,
        "leak_free": False,
        "full_address_free": False,
        "consistency_ok": False,
        "forbidden_terms_zero": False,
        "machine_terms_zero": False,
    }

    # Check gate section indicators
    if "blocked: false" in text.lower() or "blocked: false" in text:
        indicators["blocked_ok"] = True

    # Check blocked_reasons
    if "blocked_reasons: []" in text:
        indicators["blocked_reasons_empty"] = True
    elif "blocked_reasons:" in text:
        # Check if reasons are non-empty
        m = re.search(r"blocked_reasons:\s*\[([^\]]*)\]", text)
        if m and m.group(1).strip():
            indicators["blocked_reasons_empty"] = False

    # Check leak indicators
    leak_markers = [
        ("无 token", "no_token"),
        ("无 key", "no_key"),
        ("无 cookie", "no_cookie"),
        ("无 password", "no_password"),
        ("无 chat_id", "no_chat_id"),
    ]
    leak_count = 0
    for marker, _key in leak_markers:
        if marker in text:
            # Check if it's marked as pass (✅) or fail (❌)
            line = _find_line(text, marker)
            if "❌" in line or "fail" in line.lower():
                leak_count += 1
    indicators["leak_count"] = leak_count
    indicators["leak_free"] = leak_count == 0

    # Check full address indicators
    addr_ok = False
    if "无完整钱包地址" in text:
        line = _find_line(text, "无完整钱包地址")
        if "✅" in line:
            addr_ok = True
    elif "仅使用短地址" in text:
        addr_ok = True
    indicators["full_address_count"] = 0 if addr_ok else 1
    indicators["full_address_free"] = addr_ok

    # Check consistency
    if "consistency_status: pass" in text:
        indicators["consistency_ok"] = True

    # Check term counts
    fm = re.search(r"forbidden_terms_count:\s*(\d+)", text)
    if fm:
        indicators["forbidden_terms_count"] = int(fm.group(1))
        indicators["forbidden_terms_zero"] = int(fm.group(1)) == 0

    mm = re.search(r"machine_terms_count:\s*(\d+)", text)
    if mm:
        indicators["machine_terms_count"] = int(mm.group(1))
        indicators["machine_terms_zero"] = int(mm.group(1)) == 0

    # Check send flags
    indicators["should_send_now"] = "should_send_now: true" in text.lower()
    indicators["requires_user_confirmation"] = "requires_user_confirmation: true" in text.lower()
    indicators["dry_run_only"] = "dry_run_only: true" in text.lower()

    return {
        "report_path": str(rp),
        "indicators": indicators,
        "raw_length": len(text),
    }


def _find_line(text: str, substring: str) -> str:
    """Return the first line containing substring."""
    for line in text.splitlines():
        if substring in line:
            return line
    return ""


def validate_preview_gate(report: dict[str, Any], candidate: dict[str, Any]) -> list[GateResult]:
    """
    Validate all gate conditions before allowing a send.

    Gates (from task spec):
      1. preview_report 中 blocked 必须为 false
      2. blocker 必须为 0 或无 blocker
      3. leak_count 必须为 0
      4. full_address_count 必须为 0
      5. max_send_count 默认等于 1
      6. dry-run 模式下不得调用任何外部接口

    Also checks from candidate JSON:
      - blocked field is false
      - blocked_reasons is empty
      - consistency_status is pass
    """
    results: list[GateResult] = []
    ind = report.get("indicators", {})
    json_data = candidate.get("json_data", {})

    # Gate 1: blocked must be false (from preview report)
    g1 = ind.get("blocked_ok", False)
    results.append(GateResult(
        "gate_blocked_false",
        g1,
        "preview report confirms blocked=false" if g1 else "blocked is not confirmed false in preview report",
    ))

    # Gate 1b: blocked field in candidate JSON
    json_blocked = json_data.get("blocked", None)
    g1b = json_blocked is False
    results.append(GateResult(
        "gate_candidate_blocked_false",
        g1b,
        f"candidate JSON blocked={json_blocked}" if g1b else f"candidate JSON blocked={json_blocked}, expected false",
    ))

    # Gate 2: blocker must be 0 or no blocker
    blocked_reasons = json_data.get("blocked_reasons", None)
    g2 = blocked_reasons is not None and len(blocked_reasons) == 0
    results.append(GateResult(
        "gate_no_blocker",
        g2,
        f"blocked_reasons={blocked_reasons}" if g2 else f"blocked_reasons is non-empty: {blocked_reasons}",
    ))

    # Gate 3: leak_count must be 0
    leak_count = ind.get("leak_count", 0)
    g3 = leak_count == 0
    results.append(GateResult(
        "gate_leak_count_zero",
        g3,
        f"leak_count={leak_count}" if g3 else f"leak_count={leak_count}, expected 0 — sensitive info leak detected",
    ))

    # Gate 4: full_address_count must be 0
    full_addr_count = ind.get("full_address_count", 0)
    g4 = full_addr_count == 0
    results.append(GateResult(
        "gate_full_address_count_zero",
        g4,
        f"full_address_count={full_addr_count}" if g4 else f"full_address_count={full_addr_count}, expected 0",
    ))

    # Gate 5: consistency_status pass
    g5 = ind.get("consistency_ok", False)
    results.append(GateResult(
        "gate_consistency_pass",
        g5,
        "consistency_status=pass confirmed" if g5 else "consistency_status not confirmed as pass",
    ))

    # Gate 6: forbidden_terms_count must be 0
    ftc = ind.get("forbidden_terms_count", None)
    g6 = ftc == 0
    results.append(GateResult(
        "gate_forbidden_terms_zero",
        g6,
        f"forbidden_terms_count={ftc}" if g6 else f"forbidden_terms_count={ftc}, expected 0",
    ))

    # Gate 7: machine_terms_count must be 0
    mtc = ind.get("machine_terms_count", None)
    g7 = mtc == 0
    results.append(GateResult(
        "gate_machine_terms_zero",
        g7,
        f"machine_terms_count={mtc}" if g7 else f"machine_terms_count={mtc}, expected 0",
    ))

    # Gate 8: address safety check — scan candidate text for full addresses
    md_text = candidate.get("md_text", "")
    full_addr_pattern = re.compile(r"0x[a-fA-F0-9]{40}", re.IGNORECASE)
    full_matches = full_addr_pattern.findall(md_text)
    # The short address "0x082e...ca88" is 4+4 chars, not 40 — safe
    g8 = len(full_matches) == 0
    results.append(GateResult(
        "gate_no_full_address_in_md",
        g8,
        f"full addresses found in candidate: {len(full_matches)}" if not g8 else "no full addresses in candidate text",
    ))

    return results


def build_send_payload(candidate_md: str) -> dict[str, Any]:
    """
    Build the send payload from candidate markdown text.

    Returns dict with keys:
      - text: str            — the markdown text to send
      - parse_mode: str      — default 'HTML'
      - disable_web_page_preview: bool
      - char_count: int      — length of text
      - has_html_tags: bool  — whether text contains HTML tags
    """
    text = candidate_md.strip()
    return {
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "char_count": len(text),
        "has_html_tags": bool(re.search(r"<[^>]+>", text)),
    }


def dry_run_send(
    payload: dict[str, Any],
    sent_count: int = 0,
    max_send_count: int = 1,
    gate_results: Optional[list[GateResult]] = None,
) -> SendResult:
    """
    Simulate a send operation without calling any external APIs.

    Checks:
      - sent_count < max_send_count
      - all gates pass (if provided)

    Returns SendResult with dry_run=True.
    """
    gate_results = gate_results or []

    # Check send limit
    if sent_count >= max_send_count:
        return SendResult(
            status="blocked",
            sent_count=sent_count,
            max_send_count=max_send_count,
            dry_run=True,
            gate_results=gate_results,
            error=f"Send limit reached: sent_count={sent_count} >= max_send_count={max_send_count}",
        )

    # Check all gates pass
    gates_failed = [g for g in gate_results if not g.passed]
    if gates_failed:
        failed_names = [g.name for g in gates_failed]
        return SendResult(
            status="blocked",
            sent_count=sent_count,
            max_send_count=max_send_count,
            dry_run=True,
            gate_results=gate_results,
            error=f"Gates failed: {failed_names}",
        )

    # Simulate successful send
    simulated_sent_count = sent_count + 1
    return SendResult(
        status="done",
        sent_count=simulated_sent_count,
        max_send_count=max_send_count,
        message_id=f"dry-run-{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}",
        target_type="group",
        tg_api_called=False,
        sent_exceed_1=simulated_sent_count > 1,
        sent_channel=False,
        loop_started=False,
        sensitive_printed=False,
        remote_db_written=False,
        dry_run=True,
        gate_results=gate_results,
    )


def write_send_handoff(result: SendResult, output_path: str | Path) -> Path:
    """
    Write structured send result as JSON to output_path.

    Returns the output path.
    """
    op = Path(output_path)
    if not op.is_absolute():
        op = ROOT / op
    op.parent.mkdir(parents=True, exist_ok=True)
    data = result.to_dict()
    data["generated_at"] = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    data["component_version"] = "v1.9A-S2"
    op.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return op


# ---------------------------------------------------------------------------
# Schema contract functions (v1.9A-S1 → v1.9A-S2)
# ---------------------------------------------------------------------------

def load_schema(schema_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load the v1.9A manifest schema from a JSON file.

    If schema_path is None, defaults to schemas/market_radar_v19.json relative to ROOT.

    Returns the parsed schema dict with keys:
      - strict_core_field_names: list[str]
      - flexible_payload_field_names: list[str]
      - strict_core: dict (field definitions)
      - flexible_payload: dict (field definitions)
    """
    if schema_path is None:
        sp = ROOT / "schemas" / "market_radar_v19.json"
    else:
        sp = Path(schema_path)
        if not sp.is_absolute():
            sp = ROOT / sp
    if not sp.exists():
        raise FileNotFoundError(f"Schema file not found: {sp}")
    schema = json.loads(sp.read_text(encoding="utf-8-sig", errors="replace"))
    logger.info("Loaded schema v%s from %s", schema.get("version", "?"), sp)
    return schema


def validate_manifest(
    manifest: dict[str, Any],
    schema: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Validate a manifest dict against the v1.9A schema contract.

    Strict Core rules:
      - Every field in strict_core_field_names MUST be present and non-None.
      - Missing any strict field raises ValueError immediately.

    Flexible Payload rules:
      - Fields in flexible_payload_field_names are optional.
      - Missing flexible fields log a UserWarning but do NOT block.

    Args:
        manifest: The manifest dict to validate.
        schema: The parsed schema dict from load_schema().

    Returns:
        (is_valid, warnings_list) where is_valid is always True on return
        (caller catches ValueError for invalid cases).

    Raises:
        ValueError: If any Strict Core field is missing or None.
    """
    strict_fields: list[str] = schema.get("strict_core_field_names", [])
    flex_fields: list[str] = schema.get("flexible_payload_field_names", [])

    if not strict_fields:
        logger.warning("Schema has no strict_core_field_names defined; skipping strict validation")
    if not flex_fields:
        logger.warning("Schema has no flexible_payload_field_names defined; skipping flexible validation")

    # --- Strict Core validation ---
    missing_strict = [f for f in strict_fields if f not in manifest or manifest.get(f) is None]
    if missing_strict:
        raise ValueError(
            f"Strict Core fields missing from manifest: {missing_strict}. "
            f"These fields are required by schema {schema.get('version', '?')}. "
            f"See schemas/market_radar_v19.json for field definitions."
        )

    # --- Flexible Payload validation ---
    warnings_list: list[str] = []
    missing_flex = [f for f in flex_fields if f not in manifest]
    for f in missing_flex:
        msg = (
            f"Flexible Payload field '{f}' missing from manifest — "
            f"non-blocking warning per schema {schema.get('version', '?')}"
        )
        warnings.warn(msg, UserWarning)
        warnings_list.append(msg)

    return True, warnings_list


def build_manifest_from_paths(
    candidate_md_path: str | Path,
    candidate_json_path: str | Path,
    preview_report_path: str | Path,
    *,
    artifact_id: str = "",
    max_send_count: int = 1,
    parse_mode: str = "HTML",
    target_type: str = "group",
    blocked: bool = False,
    leak_count: int = 0,
    full_address_count: int = 0,
) -> dict[str, Any]:
    """
    Build a manifest dict from file paths with sensible defaults.

    All Strict Core fields are populated; Flexible Payload fields are omitted
    (they will trigger a warning during validate_manifest, which is acceptable).

    v1.9A-S2: Paths are stored as relative paths (from project ROOT) for
    Runtime Source validation. schema_version is included.

    Args:
        candidate_md_path: Path to candidate markdown file.
        candidate_json_path: Path to candidate JSON metadata file.
        preview_report_path: Path to preview gate report markdown file.
        artifact_id: Optional artifact ID; auto-generated if empty.
        max_send_count: Default 1.
        parse_mode: Default 'HTML'.
        target_type: Default 'group' (canonical).
        blocked: Default False.
        leak_count: Default 0.
        full_address_count: Default 0.

    Returns:
        Manifest dict with all Strict Core fields populated.
    """
    now = datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION_REQUIRED,
        "artifact_id": artifact_id or f"market_radar::{Path(candidate_md_path).stem}",
        "project_label": "market_radar",
        "created_at": now,
        "candidate_md_path": _make_relative_path(candidate_md_path),
        "candidate_json_path": _make_relative_path(candidate_json_path),
        "preview_report_path": _make_relative_path(preview_report_path),
        "parse_mode": parse_mode,
        "target_type": target_type,
        "max_send_count": max_send_count,
        "blocked": blocked,
        "leak_count": leak_count,
        "full_address_count": full_address_count,
    }
    return manifest


# ---------------------------------------------------------------------------
# v1.9A-S2: Runtime Source validation
# ---------------------------------------------------------------------------

def validate_runtime_source_paths(manifest: dict[str, Any]) -> list[str]:
    """Validate Runtime Source paths in the manifest.

    Rules:
      1. Must be relative paths (no absolute paths).
      2. Must not contain ../ path traversal.
      3. Must start with an allowed directory prefix:
         results/, runs/, schemas/

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    for field in RUNTIME_SOURCE_FIELDS:
        value = manifest.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"Runtime Source '{field}' is empty or missing")
            continue
        if not isinstance(value, str):
            errors.append(f"Runtime Source '{field}' must be a string, got {type(value).__name__}")
            continue

        path_str = value.replace("\\", "/")

        # Check for absolute path (Windows: C:\..., Unix: /...)
        if os.path.isabs(path_str) or path_str.startswith("/"):
            errors.append(
                f"Runtime Source '{field}' is an absolute path: '{value}'. "
                f"Must be relative from project root."
            )
            continue

        # Check for path traversal (../)
        parts = Path(path_str).parts
        if ".." in parts:
            errors.append(
                f"Runtime Source '{field}' contains path traversal (..): '{value}'"
            )
            continue

        # Check allowed directory prefix
        allowed = any(
            path_str.startswith(prefix) or path_str.startswith(prefix.replace("/", "\\"))
            for prefix in ALLOWED_DIR_PREFIXES
        )
        if not allowed:
            errors.append(
                f"Runtime Source '{field}' has disallowed path prefix: '{value}'. "
                f"Allowed prefixes: {ALLOWED_DIR_PREFIXES}"
            )

    return errors


# ---------------------------------------------------------------------------
# v1.9A-S2: Type and value range validation
# ---------------------------------------------------------------------------

def validate_types_and_ranges(manifest: dict[str, Any]) -> list[str]:
    """Validate field types and value ranges in the manifest.

    Checks:
      1. blocked must be bool.
      2. leak_count must be int and >= 0.
      3. full_address_count must be int and >= 0.
      4. max_send_count must be int and >= 1.
      5. parse_mode must be normalizable to HTML/MarkdownV2/PlainText.
      6. target_type must be in allowed set: group/supergroup/test_group/fake.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    # --- blocked: must be bool ---
    blocked = manifest.get("blocked")
    if not isinstance(blocked, bool):
        errors.append(
            f"blocked must be bool, got {type(blocked).__name__}: {blocked!r}"
        )

    # --- leak_count: must be int and >= 0 ---
    leak_count = manifest.get("leak_count")
    if isinstance(leak_count, bool) or not isinstance(leak_count, int):
        errors.append(
            f"leak_count must be int, got {type(leak_count).__name__}: {leak_count!r}"
        )
    elif leak_count < 0:
        errors.append(f"leak_count must be >= 0, got {leak_count}")

    # --- full_address_count: must be int and >= 0 ---
    full_addr = manifest.get("full_address_count")
    if isinstance(full_addr, bool) or not isinstance(full_addr, int):
        errors.append(
            f"full_address_count must be int, got {type(full_addr).__name__}: {full_addr!r}"
        )
    elif full_addr < 0:
        errors.append(f"full_address_count must be >= 0, got {full_addr}")

    # --- max_send_count: must be int and >= 1 ---
    msc = manifest.get("max_send_count")
    if isinstance(msc, bool) or not isinstance(msc, int):
        errors.append(
            f"max_send_count must be int, got {type(msc).__name__}: {msc!r}"
        )
    elif msc < 1:
        errors.append(f"max_send_count must be >= 1, got {msc}")

    # --- parse_mode normalization ---
    parse_mode_raw = manifest.get("parse_mode", "")
    normalized_pm = normalize_parse_mode(parse_mode_raw)
    if normalized_pm is None:
        errors.append(
            f"parse_mode cannot be normalized: '{parse_mode_raw}'. "
            f"Must be one of: HTML, MarkdownV2, PlainText"
        )

    # --- target_type validation ---
    target_type_raw = manifest.get("target_type", "")
    normalized_tt = normalize_target_type(target_type_raw)
    if normalized_tt is None:
        errors.append(
            f"target_type not in allowed set: '{target_type_raw}'. "
            f"Allowed: group, supergroup, test_group, fake"
        )

    return errors


# ---------------------------------------------------------------------------
# v1.9A-S2: Flexible Payload sanitization
# ---------------------------------------------------------------------------

def sanitize_flexible_payload(
    manifest: dict[str, Any],
    parse_mode: str,
) -> tuple[dict[str, Any], list[str]]:
    """Sanitize Flexible Payload fields from manifest.

    Rules:
      1. token_name, symbol, wallet_short, extra_context must be str (if present).
      2. Truncate to max lengths: token_name≤32, symbol≤16, wallet_short≤24, extra_context≤280.
      3. Remove control characters.
      4. parse_mode=HTML → escape < > &
      5. parse_mode=MarkdownV2 → escape _ * [ ] ( ) ~ ` > # + - = | { } . !
      6. parse_mode unrecognized → fallback to PlainText, strip HTML/MD sensitive chars.

    Returns (sanitized_fields_dict, warnings_list).
    """
    warnings_list: list[str] = []
    sanitized: dict[str, Any] = {}

    str_fields = {
        "token_name": 32,
        "symbol": 16,
        "wallet_short": 24,
    }

    for field, max_len in str_fields.items():
        value = manifest.get(field)
        if value is None:
            sanitized[field] = None
            continue
        if field not in manifest:
            continue

        if not isinstance(value, str):
            warnings_list.append(
                f"Flexible Payload '{field}' is not str (got {type(value).__name__}), "
                f"converting to str"
            )
            value = str(value)

        # Step 1: Remove control characters
        cleaned = remove_control_chars(value)
        if cleaned != value:
            warnings_list.append(
                f"Flexible Payload '{field}': removed control characters"
            )

        # Step 2: Parse-mode-specific escaping (escape BEFORE truncation
        # because escaping expands chars, e.g. < → &lt;)
        if parse_mode in ("HTML", "MarkdownV2", "PlainText"):
            cleaned = sanitize_for_parse_mode(cleaned, parse_mode)
        else:
            # Unknown parse_mode — defensive fallback to PlainText
            cleaned = sanitize_for_parse_mode(cleaned, "PlainText")
            warnings_list.append(
                f"Flexible Payload '{field}': unknown parse_mode '{parse_mode}', "
                f"fallback to PlainText escaping"
            )

        # Step 3: Truncate to max length
        if len(cleaned) > max_len:
            cleaned = cleaned[:max_len]
            warnings_list.append(
                f"Flexible Payload '{field}': truncated from {len(value)} to {max_len} chars"
            )

        sanitized[field] = cleaned

    # --- extra_context: max 280 chars ---
    if "extra_context" in manifest:
        ec = manifest["extra_context"]
        if ec is None:
            sanitized["extra_context"] = None
        elif isinstance(ec, str):
            cleaned = remove_control_chars(ec)
            if len(cleaned) > 280:
                cleaned = cleaned[:280]
                warnings_list.append(
                    "Flexible Payload 'extra_context': truncated to 280 chars"
                )
            if parse_mode:
                cleaned = sanitize_for_parse_mode(cleaned, parse_mode)
            sanitized["extra_context"] = cleaned
        elif isinstance(ec, dict):
            ec_str = json.dumps(ec, ensure_ascii=False)
            cleaned = remove_control_chars(ec_str)
            if len(cleaned) > 280:
                cleaned = cleaned[:280]
                warnings_list.append(
                    "Flexible Payload 'extra_context': truncated to 280 chars"
                )
            sanitized["extra_context"] = cleaned
        else:
            sanitized["extra_context"] = str(ec)[:280]

    return sanitized, warnings_list


# ---------------------------------------------------------------------------
# v1.9A-S2: Policy application (Lane 1)
# ---------------------------------------------------------------------------

def apply_policy(
    manifest: dict[str, Any],
    *,
    schema_version_required: str = SCHEMA_VERSION_REQUIRED,
) -> PolicyReceipt:
    """Apply Lane 1 policy to a manifest.

    Lane 1 policy rules:
      - max_send_count > 1 → trimmed to 1 in effective_data, recorded in adjusted_fields.
      - max_send_count < 1 or type error → already caught by type validation; policy
        does not duplicate type errors.

    IMPORTANT: raw_manifest is NEVER modified in-place. Policy works on a deep copy.

    Args:
        manifest: The raw manifest dict (will NOT be modified).
        schema_version_required: Expected schema_version value.

    Returns:
        PolicyReceipt with status, warnings, errors, adjusted_fields, effective_data.
    """
    errors: list[str] = []
    warnings_list: list[str] = []
    adjusted_fields: list[str] = []

    # Deep copy — raw_manifest is NEVER modified
    effective_data = copy.deepcopy(manifest)

    # --- schema_version check (Strict Core) ---
    sv = manifest.get("schema_version")
    if sv is None:
        errors.append("schema_version is missing from manifest (Strict Core field)")
    elif sv != schema_version_required:
        errors.append(
            f"schema_version mismatch: expected '{schema_version_required}', "
            f"got '{sv}'"
        )

    # --- max_send_count policy (Lane 1) ---
    msc = manifest.get("max_send_count")
    if isinstance(msc, int) and not isinstance(msc, bool):
        if msc > 1:
            effective_data["max_send_count"] = 1
            adjusted_fields.append("max_send_count")
            warnings_list.append(
                f"Lane 1 policy: max_send_count trimmed from {msc} to 1"
            )
        # msc < 1 is caught by type/range validation — policy doesn't duplicate
    # Type errors for msc are caught by validate_types_and_ranges — not duplicated here

    # --- Determine status ---
    if errors:
        status = "blocked"
    elif adjusted_fields:
        status = "adjusted"
    else:
        status = "ok"

    receipt = PolicyReceipt(
        status=status,
        warnings=warnings_list,
        errors=errors,
        adjusted_fields=adjusted_fields,
        effective_data=effective_data,
    )

    return receipt


# ---------------------------------------------------------------------------
# v1.9A-S2: Full validation + policy pipeline
# ---------------------------------------------------------------------------

def validate_and_apply_policy(
    manifest: dict[str, Any],
    schema: Optional[dict[str, Any]] = None,
    *,
    schema_version_required: str = SCHEMA_VERSION_REQUIRED,
) -> PolicyReceipt:
    """Run the full v1.9A-S2 validation + policy pipeline.

    Pipeline:
      1. Schema version check (Strict Core)
      2. Strict Core field presence validation
      3. Runtime Source path validation (relative, no ../, allowed prefixes)
      4. Type and value range validation
      5. Lane 1 policy application (max_send_count trim)
      6. Flexible Payload sanitization

    All errors and warnings are collected into a single PolicyReceipt.
    raw_manifest is NEVER modified in-place.

    Args:
        manifest: The raw manifest dict (will NOT be modified).
        schema: Optional parsed schema dict. If None, loads from default path.
        schema_version_required: Expected schema_version value.

    Returns:
        PolicyReceipt summarizing all validation and policy results.
    """
    if schema is None:
        schema = load_schema()

    all_errors: list[str] = []
    all_warnings: list[str] = []
    all_adjusted: list[str] = []

    # Deep copy — never modify raw_manifest
    effective_data = copy.deepcopy(manifest)

    # --- Step 1: Strict Core field presence ---
    try:
        is_valid, flex_warnings = validate_manifest(manifest, schema)
        all_warnings.extend(flex_warnings)
    except ValueError as e:
        all_errors.append(str(e))

    # --- Step 2: Schema version ---
    sv = manifest.get("schema_version")
    if sv is None:
        all_errors.append("schema_version is missing from manifest (Strict Core)")
    elif sv != schema_version_required:
        all_errors.append(
            f"schema_version mismatch: expected '{schema_version_required}', got '{sv}'"
        )

    # --- Step 3: Runtime Source path validation ---
    rs_errors = validate_runtime_source_paths(manifest)
    all_errors.extend(rs_errors)

    # --- Step 4: Type and value range validation ---
    type_errors = validate_types_and_ranges(manifest)
    all_errors.extend(type_errors)

    # --- Step 5: Lane 1 policy (max_send_count) ---
    msc = manifest.get("max_send_count")
    if isinstance(msc, int) and not isinstance(msc, bool):
        if msc > 1:
            effective_data["max_send_count"] = 1
            all_adjusted.append("max_send_count")
            all_warnings.append(
                f"Lane 1 policy: max_send_count trimmed from {msc} to 1"
            )

    # --- Step 6: Normalize parse_mode for sanitization ---
    parse_mode_raw = manifest.get("parse_mode", "HTML")
    parse_mode = normalize_parse_mode(parse_mode_raw)
    if parse_mode is None:
        parse_mode = "PlainText"  # Defensive fallback for sanitization
        all_warnings.append(
            f"parse_mode '{parse_mode_raw}' unrecognized; falling back to PlainText for sanitization"
        )

    # --- Step 7: Sanitize Flexible Payload ---
    sanitized, sanitize_warnings = sanitize_flexible_payload(manifest, parse_mode)
    for field, value in sanitized.items():
        effective_data[field] = value
    all_warnings.extend(sanitize_warnings)

    # --- Determine final status ---
    if all_errors:
        status = "blocked"
    elif all_adjusted:
        status = "adjusted"
    else:
        status = "ok"

    receipt = PolicyReceipt(
        status=status,
        warnings=all_warnings,
        errors=all_errors,
        adjusted_fields=all_adjusted,
        effective_data=effective_data,
    )

    return receipt


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

def run_full_dry_run(
    candidate_md_path: str | Path,
    candidate_json_path: str | Path,
    preview_report_path: str | Path,
    result_output_path: str | Path,
    max_send_count: int = 1,
) -> SendResult:
    """
    Run the full v1.9A dry-run pipeline:
      1. Load candidate
      2. Load preview gate
      3. Validate gates
      4. Build send payload
      5. Dry-run send
      6. Write handoff

    Returns SendResult.
    """
    # Step 1: Load candidate
    candidate = load_candidate(candidate_md_path, candidate_json_path)

    # Step 2: Load preview gate
    preview_gate = load_preview_gate(preview_report_path)

    # Step 3: Validate gates
    gate_results = validate_preview_gate(preview_gate, candidate)

    # Step 4: Build payload
    payload = build_send_payload(candidate["md_text"])

    # Step 5: Dry-run send
    result = dry_run_send(payload, sent_count=0, max_send_count=max_send_count, gate_results=gate_results)

    # Step 6: Write handoff
    write_send_handoff(result, result_output_path)

    return result


# ---------------------------------------------------------------------------
# v1.9B: Transport interface
# ---------------------------------------------------------------------------

# Standardized error types for Transport failures
TRANSPORT_ERROR_TYPES = {
    "PROVIDER_REJECTION": "The provider rejected the request (e.g. invalid params, blocked content).",
    "NETWORK_TIMEOUT": "The request timed out before receiving a response.",
    "AUTH_FAILURE": "Authentication failed (invalid token, revoked, etc.).",
    "RATE_LIMITED": "The provider rate-limited the request; retry after delay.",
}

# Transport names
TRANSPORT_FAKE = "fake"
TRANSPORT_TELEGRAM = "telegram"


class BaseTransport(ABC):
    """Abstract transport interface for v1.9B.

    Transport is a DUMB PIPE — it receives sanitized payload and returns
    SendResult. It MUST NOT:
      - re-parse the manifest
      - re-execute gate / policy
      - modify the payload (including re-escaping)
      - read environment variables
      - use _unrecognized_payload for send control

    Subclasses implement send() to deliver the payload.
    """

    @property
    @abstractmethod
    def transport_name(self) -> str:
        """Unique name for this transport (e.g. 'fake', 'telegram')."""
        ...

    @abstractmethod
    def send(self, payload: dict[str, Any], target: str, parse_mode: str) -> SendResult:
        """Deliver sanitized payload to the target.

        Args:
            payload: Sanitized send payload dict with keys:
                - text: str — message text (already escaped)
                - parse_mode: str — canonical parse mode
                - disable_web_page_preview: bool
                - char_count: int
                - has_html_tags: bool
                - _unrecognized_payload: Optional[list] — for debug passthrough only
            target: Canonical target type (group, supergroup, test_group, fake).
            parse_mode: Canonical parse mode (HTML, MarkdownV2, PlainText).

        Returns:
            SendResult with success, provider, provider_metadata populated.
        """
        ...


class FakeTransport(BaseTransport):
    """Fake transport that simulates send success or failure without network.

    Failure modes are triggered by setting the target to a special value:
      - "fake" → success (default)
      - "fake:PROVIDER_REJECTION" → provider rejection failure
      - "fake:NETWORK_TIMEOUT" → timeout failure
      - "fake:AUTH_FAILURE" → auth failure
      - "fake:RATE_LIMITED" → rate limit failure

    FakeTransport never reads environment variables, never calls external APIs.
    """

    @property
    def transport_name(self) -> str:
        return TRANSPORT_FAKE

    def send(self, payload: dict[str, Any], target: str, parse_mode: str) -> SendResult:
        """Simulate sending — returns success or simulated failure."""
        text = payload.get("text", "")

        # Check for failure simulation via target suffix
        if target.startswith("fake:") and target != "fake":
            error_type = target.split(":", 1)[1]
            if error_type in TRANSPORT_ERROR_TYPES:
                return self._simulate_failure(error_type)
            # Unknown error type → fall through to success

        # Simulated success
        fake_msg_id = f"fake-msg-{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}"
        return SendResult(
            status="done",
            sent_count=1,
            max_send_count=1,
            message_id=fake_msg_id,
            target_type=target,
            tg_api_called=False,
            dry_run=True,
            success=True,
            status_code=200,
            provider=TRANSPORT_FAKE,
            provider_metadata={
                "transport_name": self.transport_name,
                "raw_api_response": {"ok": True, "result": {"message_id": fake_msg_id}},
                "request_payload_preview": {
                    "text_preview": text[:200],
                    "parse_mode": parse_mode,
                    "target": target,
                    "char_count": len(text),
                },
            },
        )

    def _simulate_failure(self, error_type: str) -> SendResult:
        """Build a SendResult for a simulated failure."""
        error_messages = {
            "PROVIDER_REJECTION": "Simulated: provider rejected the request — bad request or content blocked.",
            "NETWORK_TIMEOUT": "Simulated: request timed out after 30s.",
            "AUTH_FAILURE": "Simulated: authentication failed — invalid or revoked credentials.",
            "RATE_LIMITED": "Simulated: too many requests, rate limited by provider.",
        }
        status_codes = {
            "PROVIDER_REJECTION": 400,
            "NETWORK_TIMEOUT": 0,
            "AUTH_FAILURE": 401,
            "RATE_LIMITED": 429,
        }
        retry_after_map = {
            "RATE_LIMITED": 30,
        }

        return SendResult(
            status="blocked",
            sent_count=0,
            max_send_count=1,
            message_id="",
            target_type="fake",
            tg_api_called=False,
            dry_run=True,
            error=error_messages.get(error_type, f"Simulated failure: {error_type}"),
            success=False,
            status_code=status_codes.get(error_type, 0),
            error_type=error_type,
            error_message=error_messages.get(error_type, f"Simulated failure: {error_type}"),
            retry_after=retry_after_map.get(error_type),
            provider=TRANSPORT_FAKE,
            provider_metadata={
                "transport_name": self.transport_name,
                "raw_api_response": {"ok": False, "error_code": status_codes.get(error_type, 0)},
                "request_payload_preview": None,
            },
        )


class TGTransportStub(BaseTransport):
    """Stub that constructs a TG API request payload WITHOUT calling the API.

    This is the v1.9B verification transport — it proves that the Sender Core
    can produce valid TG-compatible request payloads without actually sending.

    TGTransportStub:
      - Constructs the exact dict that would be sent as a TG Bot API sendMessage request.
      - Never calls os.getenv(), never reads .env files.
      - Accepts bot_token and default_chat_id as constructor parameters ONLY.
      - Does NOT modify, re-escape, or re-sanitize the payload text.
      - If _unrecognized_payload is present, passes it through in provider_metadata only.

    For v1.9B, token/chat_id are DUMMY values. Real credentials will be wired
    in v1.9B-final with user authorization.
    """

    def __init__(self, bot_token: str = "dummy", default_chat_id: str = "dummy"):
        """Create a TGTransportStub with EXPLICIT parameters only.

        Args:
            bot_token: Bot token string. For v1.9B, use "dummy".
            default_chat_id: Default chat ID string. For v1.9B, use "dummy".

        WARNING: These are DUMMY parameters for v1.9B verification.
        Real tokens must NEVER be hardcoded or printed.
        """
        self._bot_token = bot_token
        self._default_chat_id = default_chat_id

    @property
    def transport_name(self) -> str:
        return TRANSPORT_TELEGRAM

    def send(self, payload: dict[str, Any], target: str, parse_mode: str) -> SendResult:
        """Construct TG API request payload without calling the API.

        The payload text is passed through UNMODIFIED — no re-escaping.
        _unrecognized_payload is placed in provider_metadata only.
        """
        text = payload.get("text", "")

        # Construct the TG Bot API sendMessage request payload
        request_payload = {
            "chat_id": self._default_chat_id,
            "text": text,  # PASS-THROUGH — no re-escaping
            "parse_mode": parse_mode,
            "disable_web_page_preview": payload.get("disable_web_page_preview", True),
        }

        # Resolve chat_id based on target type (but always use dummy in v1.9B)
        if target in ("supergroup",):
            # In production, supergroup uses @channel_username
            request_payload["chat_id"] = self._default_chat_id

        # _unrecognized_payload: passthrough to provider_metadata ONLY
        unrecognized = payload.get("_unrecognized_payload", None)

        provider_metadata: dict[str, Any] = {
            "transport_name": self.transport_name,
            "request_payload_preview": {
                "chat_id": "[REDACTED]",  # Never print real chat_id
                "text_preview": text[:200],
                "text_length": len(text),
                "parse_mode": parse_mode,
                "disable_web_page_preview": request_payload.get("disable_web_page_preview", True),
            },
            "raw_api_response": None,  # No API call made
        }

        # _unrecognized_payload → provider_metadata only, NOT used for send control
        if unrecognized is not None:
            provider_metadata["_unrecognized_payload_debug"] = unrecognized

        # Simulated success (no API call)
        stub_msg_id = f"tg-stub-{datetime.now(CN_TZ).strftime('%Y%m%d_%H%M%S')}"
        return SendResult(
            status="done",
            sent_count=1,
            max_send_count=1,
            message_id=stub_msg_id,
            target_type=target,
            tg_api_called=False,  # No real API call
            dry_run=True,
            success=True,
            status_code=200,
            provider=TRANSPORT_TELEGRAM,
            provider_metadata=provider_metadata,
        )

    def _build_failure(
        self, error_type: str, retry_after: Optional[int] = None
    ) -> SendResult:
        """Build a failure SendResult for error simulation (used in tests)."""
        error_messages = {
            "PROVIDER_REJECTION": "TG API rejected the request.",
            "NETWORK_TIMEOUT": "TG API request timed out.",
            "AUTH_FAILURE": "TG API authentication failed.",
            "RATE_LIMITED": "TG API rate limit exceeded.",
        }
        status_codes = {
            "PROVIDER_REJECTION": 400,
            "NETWORK_TIMEOUT": 0,
            "AUTH_FAILURE": 401,
            "RATE_LIMITED": 429,
        }
        return SendResult(
            status="blocked",
            sent_count=0,
            max_send_count=1,
            message_id="",
            target_type="group",
            tg_api_called=False,
            dry_run=True,
            error=error_messages.get(error_type, f"TG API error: {error_type}"),
            success=False,
            status_code=status_codes.get(error_type, 0),
            error_type=error_type,
            error_message=error_messages.get(error_type, f"TG API error: {error_type}"),
            retry_after=retry_after,
            provider=TRANSPORT_TELEGRAM,
            provider_metadata={
                "transport_name": self.transport_name,
                "raw_api_response": {
                    "ok": False,
                    "error_code": status_codes.get(error_type, 0),
                    "description": error_messages.get(error_type, ""),
                },
                "request_payload_preview": None,
            },
        )


# ---------------------------------------------------------------------------
# v1.9B-final Prep: TGTransport — Real Telegram adapter with injected HTTP client
# ---------------------------------------------------------------------------

class HttpClient(ABC):
    """Abstract HTTP client interface for TGTransport.

    TGTransport does NOT import requests directly. It calls http_client.post()
    so that tests can inject MockHttpClient and avoid real network calls.
    """

    @abstractmethod
    def post(self, url: str, json: dict[str, Any], timeout: int) -> dict[str, Any]:
        """Send a POST request with JSON body.

        Args:
            url: Full URL to POST to.
            json: JSON-serializable request body.
            timeout: Timeout in seconds.

        Returns:
            Dict with keys:
              - status_code: int
              - json: dict (parsed response body)
              - headers: dict (response headers)

        Raises:
            TimeoutError: If the request times out.
            OSError: For network-level errors.
        """
        ...


class MockHttpClient(HttpClient):
    """Mock HTTP client for testing — never makes real network calls.

    Usage:
        # Success
        client = MockHttpClient()
        client.set_response(200, {"ok": True, "result": {"message_id": 123}})
        TGTransport(..., http_client=client)

        # Failure
        client.set_response(400, {"ok": False, "description": "Bad Request"})
        client.set_response(401, {"ok": False, "description": "Unauthorized"})
        client.set_response(429, {"ok": False, "description": "Too Many Requests",
                                  "parameters": {"retry_after": 30}})

        # Timeout
        client.set_timeout(True)
    """

    def __init__(self):
        self._status_code: int = 200
        self._response_json: dict[str, Any] = {"ok": True, "result": {"message_id": 999}}
        self._should_timeout: bool = False
        self._last_request: Optional[dict[str, Any]] = None
        self._request_count: int = 0

    def set_response(self, status_code: int, response_json: dict[str, Any]) -> None:
        """Configure the mock to return a specific HTTP response."""
        self._status_code = status_code
        self._response_json = response_json
        self._should_timeout = False

    def set_timeout(self, should_timeout: bool = True) -> None:
        """Configure the mock to simulate a timeout."""
        self._should_timeout = should_timeout

    @property
    def last_request(self) -> Optional[dict[str, Any]]:
        """The JSON body of the last POST request (for assertions)."""
        return self._last_request

    @property
    def request_count(self) -> int:
        """Number of times post() was called."""
        return self._request_count

    def post(self, url: str, json: dict[str, Any], timeout: int) -> dict[str, Any]:
        """Record the request and return the configured mock response.

        Raises TimeoutError if set_timeout(True) was called.
        """
        self._last_request = dict(json) if json else None
        self._request_count += 1

        if self._should_timeout:
            raise TimeoutError("Mock timeout — simulated network timeout")

        return {
            "status_code": self._status_code,
            "json": dict(self._response_json),
            "headers": {"Content-Type": "application/json"},
        }


class RealHttpClient(HttpClient):
    """Real HTTP client using requests.post — production adapter.

    Design principles (v1.9B-final R1):
      1. Internal implementation uses requests.post.
      2. Does NOT read environment variables (os.getenv, os.environ).
      3. Does NOT read .env files.
      4. Does NOT print, log, or expose bot_token / chat_id / URL tokens.
      5. Exceptions (timeout, connection error) are raised to the caller.
         TGTransport catches them and converts to SendResult(success=False).
      6. Does NOT import requests at module level — only inside post(),
         so tests can monkeypatch requests before import.
      7. proxy_url is an EXPLICIT constructor argument — never read from env.
      8. Default timeout is 5s (hardened minimum for real-network readiness).

    Example:
        # Test usage (monkeypatched requests.post — no real network)
        import requests as _requests
        original_post = _requests.post
        _requests.post = lambda url, json, timeout: mock_response
        try:
            client = RealHttpClient()
            result = client.post(url, body, timeout=10)
        finally:
            _requests.post = original_post

        # Production usage (user-authorized, real network, with proxy)
        client = RealHttpClient(timeout=5, proxy_url="http://127.0.0.1:7897")
        transport = TGTransport(
            bot_token=user_token,
            default_chat_id=user_chat_id,
            http_client=client,
        )
    """

    def __init__(self, timeout: int = 5, proxy_url: Optional[str] = None):
        """Create a RealHttpClient.

        Args:
            timeout: Default timeout in seconds. Default 5s (v1.9B-final R1).
            proxy_url: Optional proxy URL (e.g. "http://127.0.0.1:7897").
                       Explicit parameter only — NEVER read from env or .env.
                       Set to None for direct connection (default).
        """
        self._timeout = timeout
        self._proxy_url = proxy_url

    def post(self, url: str, json: dict[str, Any], timeout: int) -> dict[str, Any]:
        """Send a real HTTP POST request using requests.post.

        Args:
            url: Full URL to POST to.
            json: JSON-serializable request body.
            timeout: Timeout in seconds (overrides default).

        Returns:
            Dict with keys:
              - status_code: int
              - json: dict (parsed response body)
              - headers: dict (response headers)

        Raises:
            TimeoutError: If the request times out.
            OSError: For network-level errors (connection refused, DNS, etc.).
        """
        import requests as _requests

        effective_timeout = timeout if timeout is not None else self._timeout

        # Build proxies dict from proxy_url (explicit param, never from env)
        proxies: Optional[dict[str, str]] = None
        if self._proxy_url:
            proxies = {"http": self._proxy_url, "https": self._proxy_url}

        try:
            response = _requests.post(
                url,
                json=json,
                timeout=effective_timeout,
                proxies=proxies,
            )
        except _requests.exceptions.Timeout:
            raise TimeoutError(
                f"Request timed out after {effective_timeout}s"
            )
        except _requests.exceptions.ConnectionError as e:
            raise OSError(f"Connection error: {e}")
        except _requests.exceptions.RequestException as e:
            # Other requests-level errors (too many redirects, invalid URL, etc.)
            raise OSError(f"Request failed: {e}")

        # Parse JSON response body
        try:
            response_data = response.json()
        except ValueError:
            # Non-JSON response body — pass as raw text
            response_data = {"_raw_body": response.text}

        return {
            "status_code": response.status_code,
            "json": response_data,
            "headers": dict(response.headers),
        }


class TGTransport(BaseTransport):
    """Real Telegram Bot API transport using an injected HTTP client.

    Design principles (v1.9B-final Prep):
      1. All parameters are EXPLICIT constructor arguments — no env var reading.
      2. HTTP calls go through the injected http_client — testable via MockHttpClient.
      3. Never prints, logs, or includes bot_token / chat_id in any output.
      4. All failures (network, API, auth, rate-limit) are caught and returned as
         SendResult(success=False, ...) — NO uncaught exceptions.
      5. Does NOT modify, re-escape, or re-sanitize the payload text.
      6. provider_metadata preserves raw response + redacted request preview.

    Example:
        # Test usage (no real network)
        mock = MockHttpClient()
        mock.set_response(200, {"ok": True, "result": {"message_id": 123}})
        transport = TGTransport(
            bot_token="test_token",
            default_chat_id="-100123",
            http_client=mock,
            api_base_url="http://dummy.local",
        )
        result = transport.send(payload, "group", "HTML")

        # Production usage (user-authorized, real network)
        # Requires: from market_radar_sender import RealHttpClient
        # transport = TGTransport(
        #     bot_token=user_token,
        #     default_chat_id=user_chat_id,
        #     http_client=RealHttpClient(),
        # )
    """

    # Default Telegram Bot API base URL
    TG_API_BASE = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: str,
        default_chat_id: str,
        http_client: HttpClient,
        api_base_url: str = "https://api.telegram.org",
        timeout_seconds: int = 10,
    ):
        """Create a TGTransport with EXPLICIT parameters only.

        Args:
            bot_token: Telegram Bot API token. MUST be provided explicitly.
            default_chat_id: Default chat/group/channel ID. MUST be provided explicitly.
            http_client: HttpClient instance for making HTTP calls.
            api_base_url: Base URL for TG Bot API. Default: https://api.telegram.org.
                          Use "http://dummy.local" or similar in tests.
            timeout_seconds: HTTP request timeout in seconds. Default: 10.

        WARNING: Never hardcode real tokens or chat_ids. Never print these values.
        """
        if not bot_token or not isinstance(bot_token, str):
            raise ValueError("bot_token must be a non-empty string")
        if not default_chat_id or not isinstance(default_chat_id, str):
            raise ValueError("default_chat_id must be a non-empty string")
        if not isinstance(http_client, HttpClient):
            raise TypeError(
                f"http_client must be an HttpClient instance, got {type(http_client).__name__}"
            )

        self._bot_token = bot_token
        self._default_chat_id = default_chat_id
        self._http_client = http_client
        self._api_base_url = api_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def transport_name(self) -> str:
        return TRANSPORT_TELEGRAM

    def send(self, payload: dict[str, Any], target: str, parse_mode: str) -> SendResult:
        """Send a message via the Telegram Bot API using the injected HTTP client.

        The payload text is passed through UNMODIFIED — no re-escaping.
        All exceptions are caught and converted to SendResult(success=False, ...).
        """
        text = payload.get("text", "")

        # Build the TG Bot API sendMessage URL
        api_url = f"{self._api_base_url}/bot{self._bot_token}/sendMessage"

        # Build the request body
        request_body = {
            "chat_id": self._default_chat_id,
            "text": text,  # PASS-THROUGH — no re-escaping
            "parse_mode": parse_mode,
            "disable_web_page_preview": payload.get("disable_web_page_preview", True),
        }

        # _unrecognized_payload: passthrough to provider_metadata ONLY
        unrecognized = payload.get("_unrecognized_payload", None)

        # Build a REDACTED request payload preview for provider_metadata
        request_preview = {
            "chat_id": self._redact_chat_id(self._default_chat_id),
            "text_preview": text[:200] if len(text) > 200 else text,
            "text_length": len(text),
            "parse_mode": parse_mode,
            "disable_web_page_preview": request_body.get("disable_web_page_preview", True),
            "api_endpoint": "/bot[REDACTED]/sendMessage",
        }

        try:
            # Make the HTTP request via injected client
            http_response = self._http_client.post(
                url=api_url,
                json=request_body,
                timeout=self._timeout_seconds,
            )

            status_code = http_response.get("status_code", 0)
            response_json = http_response.get("json", {})

            # Parse TG API response
            if status_code == 200 and response_json.get("ok") is True:
                # Success
                result_data = response_json.get("result", {})
                message_id = str(result_data.get("message_id", ""))
                provider_metadata: dict[str, Any] = {
                    "transport_name": self.transport_name,
                    "raw_api_response": response_json,
                    "request_payload_preview": request_preview,
                }
                if unrecognized is not None:
                    provider_metadata["_unrecognized_payload_debug"] = unrecognized

                return SendResult(
                    status="done",
                    sent_count=1,
                    max_send_count=1,
                    message_id=message_id,
                    target_type=target,
                    tg_api_called=True,
                    dry_run=False,
                    success=True,
                    status_code=200,
                    provider=TRANSPORT_TELEGRAM,
                    provider_metadata=provider_metadata,
                )

            else:
                # API returned an error
                return self._handle_api_error(status_code, response_json, request_preview, unrecognized)

        except TimeoutError:
            return self._build_failure_result(
                "NETWORK_TIMEOUT",
                "TG API request timed out",
                status_code=0,
                request_preview=request_preview,
                unrecognized=unrecognized,
            )
        except OSError as e:
            return self._build_failure_result(
                "NETWORK_TIMEOUT",
                f"Network error: {e}",
                status_code=0,
                request_preview=request_preview,
                unrecognized=unrecognized,
                error_message_override=str(e),
            )
        except Exception as e:
            # Catch-all — never let an unhandled exception escape
            return self._build_failure_result(
                "UNKNOWN_ERROR",
                f"Unexpected error: {type(e).__name__}: {e}",
                status_code=0,
                request_preview=request_preview,
                unrecognized=unrecognized,
                error_message_override=f"{type(e).__name__}: {e}",
            )

    def _handle_api_error(
        self,
        status_code: int,
        response_json: dict[str, Any],
        request_preview: dict[str, Any],
        unrecognized: Any,
    ) -> SendResult:
        """Map TG API error response to a standardized SendResult.

        Error mapping:
          400 → PROVIDER_REJECTION
          401 → AUTH_FAILURE
          403 → PROVIDER_REJECTION (bot blocked / not a member / forbidden)
          429 → RATE_LIMITED (with retry_after from response)
          other → UNKNOWN_ERROR
        """
        description = response_json.get("description", "TG API error")

        if status_code == 400:
            error_type = "PROVIDER_REJECTION"
        elif status_code == 401:
            error_type = "AUTH_FAILURE"
        elif status_code == 403:
            error_type = "PROVIDER_REJECTION"
        elif status_code == 429:
            error_type = "RATE_LIMITED"
            # Extract retry_after from TG API response parameters
            parameters = response_json.get("parameters", {})
            retry_after = parameters.get("retry_after")
        else:
            error_type = "UNKNOWN_ERROR"

        retry_after = None
        if status_code == 429:
            parameters = response_json.get("parameters", {})
            retry_after = parameters.get("retry_after")

        return self._build_failure_result(
            error_type,
            description if isinstance(description, str) else str(description),
            status_code=status_code,
            raw_api_response=response_json,
            request_preview=request_preview,
            unrecognized=unrecognized,
            retry_after=retry_after,
        )

    def _build_failure_result(
        self,
        error_type: str,
        error_message: str,
        status_code: int = 0,
        raw_api_response: Optional[dict[str, Any]] = None,
        request_preview: Optional[dict[str, Any]] = None,
        unrecognized: Any = None,
        retry_after: Optional[int] = None,
        error_message_override: Optional[str] = None,
    ) -> SendResult:
        """Build a standardized failure SendResult."""
        provider_metadata: dict[str, Any] = {
            "transport_name": self.transport_name,
            "raw_api_response": raw_api_response or {"ok": False, "error_code": status_code},
            "request_payload_preview": request_preview,
        }
        if unrecognized is not None:
            provider_metadata["_unrecognized_payload_debug"] = unrecognized

        return SendResult(
            status="blocked",
            sent_count=0,
            max_send_count=1,
            message_id="",
            target_type="group",
            tg_api_called=True,
            dry_run=False,
            error=error_message_override or error_message,
            success=False,
            status_code=status_code,
            error_type=error_type,
            error_message=error_message_override or error_message,
            retry_after=retry_after,
            provider=TRANSPORT_TELEGRAM,
            provider_metadata=provider_metadata,
        )

    @staticmethod
    def _redact_chat_id(chat_id: str) -> str:
        """Redact a chat_id for safe inclusion in payload previews.

        Rules:
          - If chat_id is "-100" followed by digits → show "-100XXXX_REDACTED"
          - If chat_id is "@username" → show "@XXX_REDACTED"
          - Otherwise → hash-based redaction using simple tail-safe approach
        """
        if not chat_id:
            return "TG_TARGET_REDACTED"

        # For numeric chat IDs (e.g. "-1001234567890")
        if chat_id.startswith("-100") and len(chat_id) > 4:
            return "-100XXXX_REDACTED"

        # For username-based chat IDs (e.g. "@my_channel")
        if chat_id.startswith("@"):
            return "@XXX_REDACTED"

        # Fallback: show tail-4 characters only
        if len(chat_id) > 4:
            return f"XXX_REDACTED_{chat_id[-4:]}"

        return "TG_TARGET_REDACTED"


# ---------------------------------------------------------------------------
# v1.9B: MarketRadarSender — Sender Core with dependency injection
# ---------------------------------------------------------------------------

class MarketRadarSender:
    """Sender Core that uses a Transport to deliver sanitized payloads.

    Design principles (v1.9B):
      1. Transport is injected via constructor — NO global dry_run switch.
      2. Transport CANNOT be changed after construction (no runtime switching).
      3. Schema / Gate / Policy / Payload flow is UNCHANGED from v1.9A-S2.
      4. Transport receives only sanitized effective_data payload.
      5. Transport is a dumb pipe — no re-parsing, re-validation, re-escaping.
    """

    def __init__(self, transport: BaseTransport):
        """Create a MarketRadarSender with the given transport.

        Args:
            transport: A BaseTransport instance (FakeTransport or TGTransportStub).

        Example:
            sender = MarketRadarSender(transport=FakeTransport())
            sender = MarketRadarSender(transport=TGTransportStub(bot_token="dummy", default_chat_id="dummy"))
        """
        if not isinstance(transport, BaseTransport):
            raise TypeError(
                f"transport must be a BaseTransport instance, got {type(transport).__name__}"
            )
        self._transport = transport

    @property
    def transport(self) -> BaseTransport:
        return self._transport

    def send_from_manifest(
        self,
        manifest: dict[str, Any],
        *,
        schema: Optional[dict[str, Any]] = None,
    ) -> SendResult:
        """Run the full v1.9B pipeline: validate → policy → sanitize → transport.send().

        Pipeline (unchanged from v1.9A-S2):
          1. validate_and_apply_policy(manifest) → PolicyReceipt
          2. If blocked → return SendResult with error
          3. Extract text + parse_mode + target_type from effective_data
          4. Build payload from effective_data (NOT raw manifest)
          5. Transport.send(payload, target, parse_mode) → SendResult

        The Transport receives ONLY the sanitized payload. It does NOT:
          - re-parse the manifest
          - re-execute gate / policy
          - re-sanitize or re-escape text
          - read environment variables
          - use _unrecognized_payload for send control

        Args:
            manifest: The raw manifest dict (will NOT be modified).
            schema: Optional schema dict. If None, loads default.

        Returns:
            SendResult from the transport layer.
        """
        # Step 1: Validate + apply policy (v1.9A-S2 pipeline)
        receipt = validate_and_apply_policy(manifest, schema)

        if receipt.is_blocked:
            return SendResult(
                status="blocked",
                sent_count=0,
                max_send_count=manifest.get("max_send_count", 1),
                dry_run=True,
                error=f"Policy blocked: {receipt.errors}",
                success=False,
                status_code=0,
                error_type="PROVIDER_REJECTION",
                error_message=f"Policy blocked: {'; '.join(receipt.errors)}",
                provider=self.transport.transport_name,
            )

        # Step 2: Extract from effective_data (sanitized)
        effective = receipt.effective_data

        text = effective.get("text", "")
        parse_mode = effective.get("parse_mode", "HTML")
        target_type = effective.get("target_type", "group")

        # Step 3: Build transport payload from effective_data
        # If the manifest has a separate text field (from candidate), use it.
        # Otherwise, fall back to building from the raw manifest's candidate paths.
        # For v1.9B, the payload text is expected to be in effective_data["text"]
        # after sanitization, or we load it from the candidate.
        if not text:
            # Load candidate text from paths if not yet in effective_data
            candidate_md_path = effective.get("candidate_md_path")
            if candidate_md_path:
                try:
                    candidate = load_candidate(
                        candidate_md_path,
                        effective.get("candidate_json_path", ""),
                    )
                    text = candidate.get("md_text", "")
                except Exception:
                    text = ""

        # Build the transport payload with sanitized flexible fields
        transport_payload: dict[str, Any] = {
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
            "char_count": len(text),
            "has_html_tags": bool(re.search(r"<[^>]+>", text)) if text else False,
        }

        # Attach sanitized flexible payload fields for transport passthrough
        for field in ("token_name", "symbol", "wallet_short", "extra_context"):
            if field in effective and effective[field] is not None:
                transport_payload[field] = effective[field]

        # _unrecognized_payload: passthrough to provider_metadata ONLY
        if "_unrecognized_payload" in effective:
            transport_payload["_unrecognized_payload"] = effective["_unrecognized_payload"]

        # Step 4: Transport.send() — dumb pipe
        result = self.transport.send(transport_payload, target_type, parse_mode)

        # Step 5: Enrich result with policy info (but don't let transport override policy)
        result.target_type = target_type
        result.max_send_count = effective.get("max_send_count", manifest.get("max_send_count", 1))

        return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI: run a dry-run send with default paths."""
    import sys

    now_china = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")
    print(f"=== Market Radar Sender v1.9A-S2 (DRY-RUN) ===")
    print(f"Time: {now_china}")
    print()

    # Default paths
    candidate_md = os.environ.get(
        "MR_CANDIDATE_MD",
        str(ROOT / "results" / "static_position_v18g_send_candidate.md"),
    )
    candidate_json = os.environ.get(
        "MR_CANDIDATE_JSON",
        str(ROOT / "results" / "static_position_v18g_send_candidate.json"),
    )
    preview_report = os.environ.get(
        "MR_PREVIEW_REPORT",
        str(ROOT / "results" / "static_position_v18h_preview_report.md"),
    )
    result_output = os.environ.get(
        "MR_RESULT_OUTPUT",
        str(ROOT / "results" / "market_radar_sender_v19a_dryrun_result.json"),
    )

    try:
        result = run_full_dry_run(
            candidate_md_path=candidate_md,
            candidate_json_path=candidate_json,
            preview_report_path=preview_report,
            result_output_path=result_output,
            max_send_count=1,
        )

        print(f"Status: {result.status}")
        print(f"Sent count: {result.sent_count}/{result.max_send_count}")
        print(f"Dry run: {result.dry_run}")
        print(f"TG API called: {result.tg_api_called}")
        print(f"Gates passed: {sum(1 for g in result.gate_results if g.passed)}/{len(result.gate_results)}")
        print()
        print("Gate details:")
        for g in result.gate_results:
            status_icon = "[PASS]" if g.passed else "[FAIL]"
            print(f"  {status_icon} {g.name}: {g.detail}")
        print()
        print(f"Result written to: {result_output}")
        return 0 if result.status == "done" else 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
Market Radar History v1.9C-S1 — Published History JSONL Persistence

Reads a v1.9B send result JSON, builds a redacted history record,
and appends it to data/market_radar/published_history.jsonl with
dedup (by provider + message_id, and by artifact_id + message_id).

v1.9C-S1 additions:
  - salt.key persistent salt file (replaces hardcoded default)
  - content_hash / semantic_tags / authorization_type / reverse_trace / target_masked_title
  - Atomic Line Watchdog (single-line write, newline repair, post-write verify)

Redaction removes:
  - bot_token
  - full chat.id
  - full API URL bot tokens
  - raw_api_response.result.chat.id (redacted or deleted)
  - raw_api_response.result.chat.title → target_label_redacted

Dedup is idempotent: re-running won't add duplicate rows.

Concurrency note: This module is single-process safe. For multi-lane concurrent
writes, add file-level locking (fcntl.flock / msvcrt.locking) or switch to
SQLite with WAL mode. Tracked as v1.10 backlog item.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

HISTORY_FILE = ROOT / "data" / "market_radar" / "published_history.jsonl"
SALT_KEY_FILE = ROOT / "data" / "market_radar" / "salt.key"

# Magic number for salt.key format identification
SALT_MAGIC = "AI_RELAY_MARKET_RADAR_SALT_V1"

# ---------------------------------------------------------------------------
# Windows safe logging — v1.9C-S1: prevent GBK emoji crashes
# ---------------------------------------------------------------------------


def safe_print(text: str) -> None:
    """Print text safely on Windows consoles that may not support Unicode/emoji.

    On Windows GBK terminals, printing emoji or certain Unicode characters
    will raise UnicodeEncodeError. This function falls back to lossy encoding
    so the console never crashes.

    File writes always use utf-8 — this only affects console output.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            # Attempt with errors='replace' — shows ¿ for unencodable chars
            import sys as _sys
            encoded = text.encode(_sys.stdout.encoding or "utf-8", errors="replace")
            _sys.stdout.buffer.write(encoded + b"\n")
            _sys.stdout.flush()
        except Exception:
            # Last resort: strip to ASCII
            try:
                ascii_text = text.encode("ascii", errors="replace").decode("ascii")
                import sys as _sys2
                _sys2.stdout.buffer.write(
                    ascii_text.encode(_sys2.stdout.encoding or "utf-8", errors="replace") + b"\n"
                )
                _sys2.stdout.flush()
            except Exception:
                pass  # absolute last resort — console is broken


# ---------------------------------------------------------------------------
# Salt persistence — v1.9C-S1: magic number + persistent file
# ---------------------------------------------------------------------------

# Module-level cache for the loaded salt (never printed, never serialized)
_salt_cache: Optional[str] = None


def load_or_create_salt(salt_path: Optional[Path] = None) -> str:
    """Load the chat_id hash salt from a persistent key file with magic number.

    salt.key format:
      Line 1: AI_RELAY_MARKET_RADAR_SALT_V1  (magic number)
      Line 2: <actual salt value>

    If the file does not exist, generates a high-entropy random salt,
    writes it with the magic number header.

    If the file exists but the magic number does not match, raises ValueError
    as a blocker — do NOT silently rebuild.

    The salt MUST NOT be printed, logged, or written to published_history.jsonl.
    It exists only so chat_id hashes are stable across process restarts.

    Args:
        salt_path: Path to the salt key file. Defaults to data/market_radar/salt.key.

    Returns:
        The salt string (64 hex characters from SHA-256 of random 32 bytes).

    Raises:
        ValueError: If magic number does not match (blown or incompatible salt.key).
        RuntimeError: If salt.key is malformed.
    """
    global _salt_cache

    if salt_path is None:
        salt_path = SALT_KEY_FILE

    # Return cached salt if already loaded this process
    if _salt_cache is not None:
        return _salt_cache

    if salt_path.exists():
        lines = salt_path.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 2:
            raise RuntimeError(
                f"salt.key exists at {salt_path} but has fewer than 2 lines. "
                f"File may be corrupted. Manual recovery required."
            )
        magic = lines[0].strip()
        if magic != SALT_MAGIC:
            raise ValueError(
                f"salt.key magic number mismatch at {salt_path}.\n"
                f"Expected: {SALT_MAGIC}\n"
                f"Found:    {magic}\n"
                f"ACTION REQUIRED: The salt.key file was created by an older or "
                f"incompatible version. Do NOT delete it. Verify the file origin "
                f"before proceeding."
            )
        salt = lines[1].strip()
        if not salt:
            raise RuntimeError(
                f"salt.key exists at {salt_path} but second line (salt) is empty. "
                f"Manual recovery required."
            )
        _salt_cache = salt
        return _salt_cache

    # Generate high-entropy salt and write with magic number header
    random_bytes = secrets.token_bytes(32)
    new_salt = hashlib.sha256(random_bytes).hexdigest()

    # Ensure directory exists
    salt_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with magic number: line1 = magic, line2 = salt
    content = f"{SALT_MAGIC}\n{new_salt}\n"
    salt_path.write_text(content, encoding="utf-8")

    _salt_cache = new_salt
    return _salt_cache


def verify_salt_file() -> dict[str, Any]:
    """Verify the salt.key file is present and valid. Returns status dict."""
    result: dict[str, Any] = {
        "exists": False,
        "magic_valid": False,
        "error": "",
    }
    if not SALT_KEY_FILE.exists():
        result["error"] = f"salt.key not found at {SALT_KEY_FILE}"
        return result
    result["exists"] = True
    try:
        lines = SALT_KEY_FILE.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 2:
            result["error"] = "Fewer than 2 lines"
            return result
        result["magic_valid"] = lines[0].strip() == SALT_MAGIC
        if not result["magic_valid"]:
            result["error"] = (
                f"Magic mismatch: expected '{SALT_MAGIC}', "
                f"got '{lines[0].strip()}'"
            )
        result["salt_length"] = len(lines[1].strip()) if len(lines) > 1 else 0
    except Exception as e:
        result["error"] = str(e)
    return result


def _get_salt() -> str:
    """Get the current salt from persistent salt.key. Creates if not exists.

    The env var AI_RELAY_CHAT_ID_SALT is accepted as a migration fallback
    but will NOT be used for new deployments — salt.key is authoritative.
    """
    if SALT_KEY_FILE.exists():
        return load_or_create_salt()

    # Legacy env-var fallback — only for migration from v1.9C pre-S1
    env_salt = os.environ.get("AI_RELAY_CHAT_ID_SALT", "")
    if env_salt and env_salt != "ai_relay_desk_v19c_local_salt_default_change_in_production":
        # Migrate: persist the env var salt to salt.key with magic number
        SALT_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        content = f"{SALT_MAGIC}\n{env_salt}\n"
        SALT_KEY_FILE.write_text(content, encoding="utf-8")
        global _salt_cache
        _salt_cache = env_salt
        return env_salt

    # No salt exists — create one (the normal first-run path)
    return load_or_create_salt()


# ---------------------------------------------------------------------------
# chat_id hashing & masking — v1.9C fingerprint preservation
# ---------------------------------------------------------------------------


def _hash_chat_id(chat_id_value: Any) -> str:
    """Hash a chat_id with persistent salt to produce a non-reversible fingerprint.

    Uses SHA-256 so the result can be used for dedup, reconciliation,
    and target-group analysis without exposing the raw chat_id.

    Returns hex digest string, or empty string if input is None/empty.
    """
    if chat_id_value is None:
        return ""
    raw = str(chat_id_value).strip()
    if not raw:
        return ""
    salt = _get_salt()
    return hashlib.sha256((raw + salt).encode("utf-8")).hexdigest()


def _mask_chat_id(chat_id_value: Any) -> str:
    """Produce a human-readable masked version of a chat_id.

    Examples:
      -1003977074640 → -100****4640
      3977074640 → 397****4640
      8848089028 → 884****9028
    """
    if chat_id_value is None:
        return ""
    raw = str(chat_id_value).strip()
    if not raw:
        return ""

    # Preserve leading minus sign
    prefix = ""
    digits = raw
    if raw.startswith("-"):
        prefix = "-"
        digits = raw[1:]

    if not digits.isdigit():
        # Non-numeric chat_id: mask the middle
        if len(raw) <= 6:
            return raw[:2] + "****" if len(raw) > 2 else "****"
        return raw[:3] + "****" + raw[-3:]

    if len(digits) <= 6:
        return prefix + digits[:2] + "****" if len(digits) > 2 else prefix + "****"

    # Show first 3 digits, ****, last 4 digits
    return f"{prefix}{digits[:3]}****{digits[-4:]}"


def _extract_raw_chat_id(send_result: dict[str, Any]) -> Any:
    """Extract the raw chat_id from a send result before redaction.

    Looks in provider_metadata.raw_api_response.result.chat.id first,
    then falls back to other known locations.
    """
    provider_meta = send_result.get("provider_metadata", {})
    if not isinstance(provider_meta, dict):
        return None

    raw_api = provider_meta.get("raw_api_response", {})
    if isinstance(raw_api, dict):
        result = raw_api.get("result", {})
        if isinstance(result, dict):
            chat = result.get("chat", {})
            if isinstance(chat, dict):
                chat_id = chat.get("id")
                if chat_id is not None:
                    return chat_id

    # Fallback: check for chat_id directly in provider_metadata
    chat_id = provider_meta.get("chat_id")
    if chat_id is not None:
        return chat_id

    return None


def _extract_payload_text(send_result: dict[str, Any]) -> str:
    """Extract the payload text from a send result for content hashing.

    Looks in provider_metadata.raw_api_response.result.text first,
    then request_payload_preview.text_preview.
    """
    provider_meta = send_result.get("provider_metadata", {})
    if isinstance(provider_meta, dict):
        raw_api = provider_meta.get("raw_api_response", {})
        if isinstance(raw_api, dict):
            result = raw_api.get("result", {})
            if isinstance(result, dict):
                text = result.get("text", "")
                if text:
                    return str(text)

        req_preview = provider_meta.get("request_payload_preview", {})
        if isinstance(req_preview, dict):
            text_preview = req_preview.get("text_preview", "")
            if text_preview:
                return str(text_preview)

    return ""


# ---------------------------------------------------------------------------
# Redaction helpers
# ---------------------------------------------------------------------------

# Patterns that indicate a token: Telegram bot tokens are digits:digits_hex
# We redact any field whose value looks like a numeric chat_id (> 10 digits)
# or that contains a bot token pattern.
_CHAT_ID_MIN_DIGITS = 8  # typical chat IDs have 8+ digits


def _looks_like_chat_id(value: Any) -> bool:
    """Check if value looks like a numeric chat ID (including negative)."""
    if isinstance(value, int):
        s = str(abs(value))
        return len(s) >= _CHAT_ID_MIN_DIGITS
    if isinstance(value, str):
        stripped = value.lstrip("-")
        return stripped.isdigit() and len(stripped) >= _CHAT_ID_MIN_DIGITS
    return False


def _looks_like_bot_token(value: Any) -> bool:
    """Check if value looks like a Telegram bot token (digits:alphanumeric_hash)."""
    if not isinstance(value, str):
        return False
    # Bot token format: 8+_digits:32+_alphanumeric_with_dash_underscore
    parts = value.split(":")
    if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) >= 8:
        if len(parts[1]) >= 32 and all(c.isalnum() or c in "-_" for c in parts[1]):
            return True
    return False


def _redact_chat_id(value: Any) -> str:
    """Redact a chat ID value, keeping sign prefix."""
    if isinstance(value, int):
        prefix = "-" if value < 0 else ""
        return f"{prefix}REDACTED_CHAT_ID"
    if isinstance(value, str):
        prefix = "-" if value.startswith("-") else ""
        return f"{prefix}REDACTED_CHAT_ID"
    return "REDACTED_CHAT_ID"


def _deep_redact(obj: Any, path: str = "") -> Any:
    """Recursively redact sensitive values in a JSON-serializable structure.

    Returns a deep copy with redactions applied.
    Redacts: bot_token fields, chat.id fields, full chat/API URL tokens.
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k

            # Redact chat.id specifically
            if k == "id" and ("chat" in path or path.endswith(".chat")):
                if _looks_like_chat_id(v):
                    result[k] = _redact_chat_id(v)
                    continue

            # Redact chat.title → target_label_redacted
            if k == "title" and "chat" in path:
                result[k] = "[REDACTED]"
                continue

            # Redact bot_token anywhere
            if "token" in k.lower() or "bot_token" in k.lower():
                if isinstance(v, str) and v:
                    result[k] = "[REDACTED_BOT_TOKEN]"
                    continue

            # Redact chat_id field values
            if k in ("chat_id", "chat.id") and _looks_like_chat_id(v):
                result[k] = _redact_chat_id(v)
                continue

            # Redact api_endpoint URLs containing bot tokens
            if k == "api_endpoint" and isinstance(v, str):
                if "/bot" in v.lower():
                    result[k] = "/bot[REDACTED]"
                    continue

            # Recursively process
            result[k] = _deep_redact(v, new_path)
        return result
    elif isinstance(obj, list):
        return [_deep_redact(item, f"{path}[{i}]") for i, item in enumerate(obj)]
    elif isinstance(obj, str):
        # Check string values for bot token patterns
        if _looks_like_bot_token(obj):
            return "[REDACTED_BOT_TOKEN]"
        return obj
    else:
        return obj


def _deep_scan_sensitive(obj: Any, path: str = "") -> list[str]:
    """Scan for remaining sensitive values. Returns list of violation descriptions."""
    violations: list[str] = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            # Check for unredacted chat IDs
            if k == "id" and ("chat" in path or path.endswith(".chat")):
                if _looks_like_chat_id(v):
                    violations.append(f"Unredacted chat.id at {new_path}: {v}")
            # Check for bot tokens
            if "token" in k.lower() and isinstance(v, str) and v and "REDACTED" not in v:
                violations.append(f"Unredacted token field at {new_path}")
            # Check string values for token patterns
            if isinstance(v, str) and _looks_like_bot_token(v):
                violations.append(f"Bot token pattern at {new_path}")
            violations.extend(_deep_scan_sensitive(v, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(_deep_scan_sensitive(item, f"{path}[{i}]"))

    return violations


# ---------------------------------------------------------------------------
# v1.9C-S1: Asset field generators
# ---------------------------------------------------------------------------


def generate_content_hash(send_result: dict[str, Any]) -> str:
    """Generate MD5 content hash from the payload text.

    Uses the raw_api_response.result.text or text_preview from
    request_payload_preview. Returns hex digest string.
    """
    text = _extract_payload_text(send_result)
    if not text:
        return ""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def generate_semantic_tags(payload_text: str) -> list[str]:
    """Generate semantic tags from payload text content.

    Default tag: Market_Radar (always present).
    Keyword-based enrichment:
      - Whale_Move: whale, 大户, 主力, position, 持仓, 大额
      - Liquidation_Risk: liquidation, 清算, 爆仓
      - PnL_Update: PnL, 盈亏, 浮盈, 浮亏, profit, loss
    """
    tags = ["Market_Radar"]
    text_lower = payload_text.lower()

    whale_keywords = ["whale", "大户", "主力", "position", "持仓", "大额", "地址"]
    liquidation_keywords = ["liquidation", "清算", "爆仓", "liquidated"]
    pnl_keywords = ["pnl", "盈亏", "浮盈", "浮亏", "profit", "loss", "+", "盈利"]

    if any(kw.lower() in text_lower for kw in whale_keywords):
        tags.append("Whale_Move")
    if any(kw.lower() in text_lower for kw in liquidation_keywords):
        tags.append("Liquidation_Risk")
    if any(kw.lower() in text_lower for kw in pnl_keywords):
        tags.append("PnL_Update")

    return tags


def build_reverse_trace(
    source_result_file: str = "",
    candidate_md_path: str = "",
    candidate_json_path: str = "",
    preview_report_path: str = "",
    handoff_path: str = "",
    source_task_id: str = "",
    source_run_id: str = "",
) -> dict[str, str]:
    """Build the reverse_trace object linking back to all source artifacts.

    Returns a dict with all available paths and IDs.
    """
    trace: dict[str, str] = {
        "manifest_path": "schema/market_radar_v19.json",
        "send_result_path": source_result_file,
        "handoff_path": handoff_path,
    }
    if candidate_md_path:
        trace["candidate_md_path"] = candidate_md_path
    if candidate_json_path:
        trace["candidate_json_path"] = candidate_json_path
    if preview_report_path:
        trace["preview_report_path"] = preview_report_path
    if source_task_id:
        trace["source_task_id"] = source_task_id
    if source_run_id:
        trace["source_run_id"] = source_run_id
    return trace


def build_target_masked_title(masked_chat_id: str, target_type: str = "group") -> str:
    """Build a human-readable masked target title.

    Example: "TG群-已脱敏 (ID: -100****4640)"
    """
    type_label = "TG群" if target_type == "group" else f"TG-{target_type}"
    return f"{type_label}-已脱敏 (ID: {masked_chat_id})"


# ---------------------------------------------------------------------------
# History record builder
# ---------------------------------------------------------------------------


def build_history_record(
    send_result: dict[str, Any],
    source_result_file: str,
    candidate_md_path: str = "",
    candidate_json_path: str = "",
    preview_report_path: str = "",
    handoff_path: str = "",
    policy_status: str = "ok",
    policy_warnings: Optional[list[str]] = None,
    adjusted_fields: Optional[list[str]] = None,
    schema_version: str = "1.9A-S2",
    history_version: str = "v1.9C-S1",
) -> dict[str, Any]:
    """Build a single history record from a v1.9B send result.

    Args:
        send_result: The parsed JSON from the send result file.
        source_result_file: Path to the source result file (relative to project).
        schema_version: Schema version of the sending component.
        history_version: Version of the history record format.

    Returns:
        A dict representing one history record (to be serialized as JSONL line).
    """
    now = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    # ── Extract raw chat_id BEFORE redaction (v1.9C: preserve fingerprint) ──
    raw_chat_id = _extract_raw_chat_id(send_result)
    target_id_hash = _hash_chat_id(raw_chat_id)
    target_id_masked = _mask_chat_id(raw_chat_id)

    # ── v1.9C-S1: Extract payload text for content_hash and semantic_tags ──
    payload_text = _extract_payload_text(send_result)

    # Redact provider_metadata
    raw_metadata = send_result.get("provider_metadata", {})
    redacted_metadata = _deep_redact(raw_metadata)

    # Determine target_label_redacted from metadata or target_type
    target_label_redacted = "[REDACTED]"
    if "raw_api_response" in raw_metadata:
        raw_resp = raw_metadata.get("raw_api_response", {})
        result_obj = raw_resp.get("result", {})
        chat_obj = result_obj.get("chat", {})
        if chat_obj.get("title"):
            target_label_redacted = "[REDACTED]"

    # ── v1.9C-S1: Build reverse_trace ──
    reverse_trace = build_reverse_trace(
        source_result_file=source_result_file,
        candidate_md_path=candidate_md_path,
        candidate_json_path=candidate_json_path,
        preview_report_path=preview_report_path,
        handoff_path=handoff_path,
        source_task_id=send_result.get("task_id", ""),
        source_run_id="",
    )

    # ── v1.9C-S1: Build target_masked_title ──
    target_type = send_result.get("target_type", "group")
    target_masked_title = build_target_masked_title(target_id_masked, target_type)

    record = {
        "history_version": history_version,
        "schema_version": schema_version,
        "project_label": send_result.get("project_label", "market_radar"),
        "lane": send_result.get("executor_lane", 1),
        "artifact_id": send_result.get("raw_manifest_unmodified", False) and "market_radar::static_position_v18g" or "",
        "created_at": send_result.get("generated_at", now),
        "published_at": now,
        "provider": send_result.get("provider", "telegram"),
        "target_type": target_type,
        "target_label_redacted": target_label_redacted,
        "target_id_hash": target_id_hash,
        "target_id_masked": target_id_masked,
        "target_masked_title": target_masked_title,
        "message_id": str(send_result.get("message_id", "")),
        "sent_count": send_result.get("sent_count", 0),
        "status_code": send_result.get("status_code", 0),
        "success": send_result.get("success", False),
        "error_type": send_result.get("error_type", ""),
        "error_message": send_result.get("error_message", ""),
        "retry_after": send_result.get("retry_after"),
        "parse_mode": "HTML",
        # ── v1.9C-S1: Asset fields ──
        "content_hash": generate_content_hash(send_result),
        "semantic_tags": generate_semantic_tags(payload_text),
        "authorization_type": "user_preauthorized_tg_group",
        "reverse_trace": reverse_trace,
        # ── Path tracking ──
        "candidate_md_path": candidate_md_path,
        "candidate_json_path": candidate_json_path,
        "preview_report_path": preview_report_path,
        "send_result_path": source_result_file,
        "handoff_path": handoff_path,
        # ── Policy ──
        "policy_status": policy_status,
        "policy_warnings": policy_warnings or [],
        "adjusted_fields": adjusted_fields or [],
        "provider_metadata_redacted": redacted_metadata,
        "source_result_file": source_result_file,
    }

    return record


# ---------------------------------------------------------------------------
# Dedup helpers
# ---------------------------------------------------------------------------


def _load_existing_records(history_path: Path) -> list[dict[str, Any]]:
    """Load all existing records from published_history.jsonl."""
    records: list[dict[str, Any]] = []
    if not history_path.exists():
        return records

    with open(history_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Skipping invalid JSON line in {history_path}")
    return records


def is_duplicate(
    record: dict[str, Any], existing_records: list[dict[str, Any]]
) -> tuple[bool, str]:
    """Check if a record is a duplicate of any existing record.

    Dedup keys:
      1. Same provider + message_id
      2. Same artifact_id + message_id

    Returns (is_dup, reason).
    """
    provider = record.get("provider", "")
    message_id = str(record.get("message_id", ""))
    artifact_id = record.get("artifact_id", "")

    if not message_id:
        return False, ""

    for existing in existing_records:
        ex_provider = existing.get("provider", "")
        ex_message_id = str(existing.get("message_id", ""))
        ex_artifact_id = existing.get("artifact_id", "")

        if ex_provider == provider and ex_message_id == message_id:
            return True, f"Duplicate by provider={provider} + message_id={message_id}"
        if artifact_id and ex_artifact_id == artifact_id and ex_message_id == message_id:
            return True, f"Duplicate by artifact_id={artifact_id} + message_id={message_id}"

    return False, ""


# ---------------------------------------------------------------------------
# v1.9C-S1: Atomic Line Watchdog — write with integrity checks
# ---------------------------------------------------------------------------


def _ensure_trailing_newline(file_path: Path) -> bool:
    """Ensure the file ends with a newline character.

    If the file exists and has content but the last character is not '\\n',
    append a newline. Returns True if a repair was made.
    """
    if not file_path.exists():
        return False
    if file_path.stat().st_size == 0:
        return False

    with open(file_path, "rb+") as f:
        f.seek(-1, os.SEEK_END)
        last_byte = f.read(1)
        if last_byte != b"\n":
            f.seek(0, os.SEEK_END)
            f.write(b"\n")
            return True
    return False


def _verify_last_line(file_path: Path) -> dict[str, Any]:
    """Read the last line of the JSONL file and verify it is valid JSON.

    Returns a dict with keys: ok (bool), record (dict or None), error (str).
    """
    result: dict[str, Any] = {"ok": False, "record": None, "error": ""}

    if not file_path.exists():
        result["error"] = "File does not exist"
        return result

    with open(file_path, "rb") as f:
        # Seek to end and read backwards to find the last non-empty line
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        if file_size == 0:
            result["error"] = "File is empty"
            return result

        # Read the last chunk and extract the last line
        chunk_size = min(4096, file_size)
        f.seek(-chunk_size, os.SEEK_END)
        chunk = f.read(chunk_size).decode("utf-8", errors="replace")
        lines = chunk.strip().split("\n")
        last_line = lines[-1].strip() if lines else ""

        if not last_line:
            result["error"] = "Last line is empty"
            return result

    try:
        result["record"] = json.loads(last_line)
        result["ok"] = True
    except json.JSONDecodeError as e:
        result["error"] = str(e)

    return result


def write_published_history(
    record: dict[str, Any],
    history_path: Optional[Path] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Write a history record to published_history.jsonl with dedup and integrity checks.

    v1.9C-S1 Atomic Line Watchdog:
      1. json.dumps(record, ensure_ascii=False) must succeed
      2. Result must be a single line
      3. File trailing newline is repaired if missing
      4. After write, last line is verified via json.loads
      5. Re-running with same record does not add duplicate lines

    Args:
        record: The history record dict.
        history_path: Path to the JSONL file. If None, uses default.
        dry_run: If True, don't actually write.

    Returns:
        Dict with keys: written (bool), skipped_reason (str), row_count (int),
        dedup_passed (bool), record_path (str),
        watch_line_ok (bool), watch_line_error (str).
    """
    if history_path is None:
        history_path = HISTORY_FILE

    result = {
        "written": False,
        "skipped_reason": "",
        "row_count": 0,
        "dedup_passed": True,
        "record_path": str(history_path),
        "watch_line_ok": True,
        "watch_line_error": "",
    }

    # ── Step 1: Serialize — must succeed and be single-line ──
    try:
        json_line = json.dumps(record, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        result["written"] = False
        result["skipped_reason"] = f"JSON serialization failed: {e}"
        return result

    # Verify single-line (no embedded newlines)
    if "\n" in json_line:
        result["written"] = False
        result["skipped_reason"] = "Serialized JSON contains embedded newlines"
        return result

    # ── Step 2: Load existing records ──
    existing = _load_existing_records(history_path)
    result["row_count"] = len(existing)

    # ── Step 3: Dedup check ──
    dup, reason = is_duplicate(record, existing)
    if dup:
        result["written"] = False
        result["skipped_reason"] = reason
        result["dedup_passed"] = True
        return result

    if dry_run:
        result["written"] = True
        result["row_count"] = len(existing) + 1
        return result

    # ── Step 4: Ensure directory exists ──
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Step 5: Repair trailing newline if needed ──
    repaired = _ensure_trailing_newline(history_path)
    if repaired:
        logger.info("Repaired missing trailing newline in %s", history_path)

    # ── Step 6: Append the single line + newline ──
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json_line + "\n")

    # ── Step 7: Verify last line is valid JSON ──
    verify_result = _verify_last_line(history_path)
    if not verify_result["ok"]:
        result["watch_line_ok"] = False
        result["watch_line_error"] = verify_result["error"]
        # Still mark as written — the write happened, but integrity check failed
        result["written"] = True
        result["row_count"] = len(existing) + 1
        return result

    result["written"] = True
    result["row_count"] = len(existing) + 1
    result["watch_line_ok"] = True

    return result


# ---------------------------------------------------------------------------
# Main pipeline: build from send result + write
# ---------------------------------------------------------------------------


def build_and_write_from_send_result(
    send_result_path: str,
    history_path: Optional[Path] = None,
    candidate_md_path: str = "",
    candidate_json_path: str = "",
    preview_report_path: str = "",
    handoff_path: str = "",
    policy_status: str = "ok",
    policy_warnings: Optional[list[str]] = None,
    adjusted_fields: Optional[list[str]] = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Full pipeline: load send result, build record, redact, write.

    Returns a dict with the full operation summary.
    """
    full_path = ROOT / send_result_path

    if not full_path.exists():
        return {
            "status": "partial",
            "error": f"Send result file not found: {send_result_path}",
            "record": None,
            "write_result": None,
            "redaction_violations": [],
        }

    with open(full_path, "r", encoding="utf-8") as f:
        send_result = json.load(f)

    # Build record
    record = build_history_record(
        send_result=send_result,
        source_result_file=send_result_path,
        candidate_md_path=candidate_md_path,
        candidate_json_path=candidate_json_path,
        preview_report_path=preview_report_path,
        handoff_path=handoff_path,
        policy_status=policy_status,
        policy_warnings=policy_warnings,
        adjusted_fields=adjusted_fields,
    )

    # Scan for sensitive data in the redacted metadata
    redacted_meta = record.get("provider_metadata_redacted", {})
    violations = _deep_scan_sensitive(redacted_meta)

    # Also scan the record itself for any leaked sensitive values
    record_violations = _deep_scan_sensitive(record)
    violations.extend(record_violations)

    # Write
    write_result = write_published_history(record, history_path=history_path, dry_run=dry_run)

    return {
        "status": "done" if write_result["written"] else "partial",
        "error": "",
        "record": record if write_result["written"] else None,
        "write_result": write_result,
        "redaction_violations": violations,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # Default: build from the R2 send result
    result_path = sys.argv[1] if len(sys.argv) > 1 else "results/market_radar_v19b_real_tg_send_result.json"

    summary = build_and_write_from_send_result(
        send_result_path=result_path,
        candidate_md_path="results/static_position_v18g_send_candidate.md",
        candidate_json_path="results/static_position_v18g_send_candidate.json",
        preview_report_path="results/static_position_v18h_preview_report.md",
        handoff_path="runs/market_radar/v19b_real_tg_send_handoff.md",
        policy_status="ok",
        policy_warnings=[
            "Flexible Payload field 'token_name' missing from manifest",
            "Flexible Payload field 'symbol' missing from manifest",
            "Flexible Payload field 'wallet_short' missing from manifest",
            "Flexible Payload field 'side' missing from manifest",
            "Flexible Payload field 'pnl' missing from manifest",
            "Flexible Payload field 'entry_price' missing from manifest",
            "Flexible Payload field 'liquidation_distance' missing from manifest",
            "Flexible Payload field 'extra_context' missing from manifest",
        ],
        adjusted_fields=[],
        dry_run="--dry-run" in sys.argv,
    )

    safe_print(json.dumps(summary, ensure_ascii=False, indent=2))

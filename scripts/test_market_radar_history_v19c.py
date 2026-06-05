"""
Market Radar v1.9C-S1 -- Published History JSONL Persistence Tests

Tests for the market_radar_history module.
v1.9C-S1 adds: salt persistence, asset fields, Atomic Line Watchdog, safe_print.
"""

import json, os, sys, tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from market_radar_history import (
    build_history_record, write_published_history, is_duplicate,
    _deep_redact, _deep_scan_sensitive, _load_existing_records,
    _hash_chat_id, _mask_chat_id, _extract_raw_chat_id,
    _extract_payload_text, _ensure_trailing_newline, _verify_last_line,
    build_and_write_from_send_result, generate_content_hash,
    generate_semantic_tags, build_reverse_trace,
    build_target_masked_title, load_or_create_salt,
    verify_salt_file, _get_salt,
    HISTORY_FILE, SALT_KEY_FILE, SALT_MAGIC, ROOT,
)

# Fixtures
_R2_SEND_RESULT = {
    "status": "done", "sent_count": 1, "max_send_count": 1,
    "message_id": "2195", "target_type": "group",
    "tg_api_called": True, "sent_exceed_1": False, "sent_channel": False,
    "loop_started": False, "sensitive_printed": False,
    "remote_db_written": False, "dry_run": False, "gate_results": [],
    "error": "", "success": True, "status_code": 200,
    "error_type": "", "error_message": "", "retry_after": None,
    "provider": "telegram",
    "provider_metadata": {
        "transport_name": "telegram",
        "raw_api_response": {
            "ok": True,
            "result": {
                "message_id": 2195,
                "from": {"id": 9999999999, "is_bot": True, "first_name": "TestBot", "username": "TestNewsPushBot"},
                "chat": {"id": -1003977074640, "title": "test_group_title", "type": "supergroup"},
                "date": 1780547300,
                "text": "test payload with whale position and PnL +87.5% data",
            }
        },
        "request_payload_preview": {
            "chat_id": "-100XXXX_REDACTED", "parse_mode": "HTML",
            "api_endpoint": "/bot[REDACTED]/sendMessage"
        }
    },
    "generated_at": "2026-06-04 12:28:20 UTC+8",
    "component_version": "v1.9B-final-R2",
    "executor_lane": 1, "project_label": "market_radar",
    "task_id": "20260604_121532.r02",
    "raw_manifest_unmodified": True, "effective_data_used": True,
    "component_chain": ["schema/market_radar_v19.json"]
}

def _make_temp_jsonl():
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="test_history_")
    os.close(fd)
    return Path(path)

def _make_temp_salt_key():
    fd, path = tempfile.mkstemp(suffix=".key", prefix="test_salt_")
    os.close(fd)
    Path(path).unlink(missing_ok=True)
    return Path(path)


# ============================================================
# Original v1.9C Tests (updated for v1.9C-S1)
# ============================================================

def test_build_history_record_from_r2():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    assert record["history_version"] == "v1.9C-S1"
    assert record["message_id"] == "2195"
    assert record["provider"] == "telegram"
    for f in ["content_hash", "semantic_tags", "authorization_type", "reverse_trace", "target_masked_title"]:
        assert f in record, f"Missing field: {f}"
    print("PASS test_build_history_record_from_r2")

def test_chat_id_redacted():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    redacted_meta = record.get("provider_metadata_redacted", {})
    chat_id = redacted_meta["raw_api_response"]["result"]["chat"]["id"]
    assert chat_id != -1003977074640
    assert "REDACTED" in str(chat_id).upper()
    assert redacted_meta["raw_api_response"]["result"]["chat"]["title"] == "[REDACTED]"
    print("PASS test_chat_id_redacted")

def test_no_token_or_chat_id_leak():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    redacted_meta = record.get("provider_metadata_redacted", {})
    violations = _deep_scan_sensitive(redacted_meta)
    assert len(violations) == 0, f"Redaction violations: {violations}"
    record_violations = _deep_scan_sensitive(record)
    assert len(record_violations) == 0, f"Record violations: {record_violations}"
    record_str = json.dumps(record, ensure_ascii=False)
    assert "-1003977074640" not in record_str
    print("PASS test_no_token_or_chat_id_leak")

def test_write_history_succeeds():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    temp_path = _make_temp_jsonl()
    try:
        wr = write_published_history(record, history_path=temp_path)
        assert wr["written"] is True
        assert wr["watch_line_ok"] is True
        records = _load_existing_records(temp_path)
        assert len(records) == 1
        assert records[0]["message_id"] == "2195"
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_write_history_succeeds")

def test_dedup_same_message_id():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    temp_path = _make_temp_jsonl()
    try:
        r1 = write_published_history(record, history_path=temp_path)
        assert r1["written"] is True and r1["row_count"] == 1
        r2 = write_published_history(record, history_path=temp_path)
        assert r2["written"] is False
        assert r2["row_count"] == 1
        records = _load_existing_records(temp_path)
        assert len(records) == 1
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_dedup_same_message_id")

def test_different_records_coexist():
    r1 = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    r2_result = dict(_R2_SEND_RESULT); r2_result["message_id"] = "9999"
    r2 = build_history_record(send_result=r2_result, source_result_file="results/test2.json")
    temp_path = _make_temp_jsonl()
    try:
        assert write_published_history(r1, history_path=temp_path)["written"] is True
        assert write_published_history(r2, history_path=temp_path)["written"] is True
        records = _load_existing_records(temp_path)
        assert len(records) == 2
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_different_records_coexist")

def test_dedup_by_artifact_message_id():
    r1 = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    r1["artifact_id"] = "market_radar::test_artifact"
    r2 = dict(r1); r2["provider"] = "other"
    temp_path = _make_temp_jsonl()
    try:
        assert write_published_history(r1, history_path=temp_path)["written"] is True
        wr2 = write_published_history(r2, history_path=temp_path)
        assert wr2["written"] is False
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_dedup_by_artifact_message_id")

def test_deep_redact_nested():
    nested = {"result": {"chat": {"id": -1001234567890, "title": "Secret"}}}
    r = _deep_redact(nested)
    assert "REDACTED" in str(r["result"]["chat"]["id"])
    assert r["result"]["chat"]["title"] == "[REDACTED]"
    print("PASS test_deep_redact_nested")

def test_redact_bot_token_strings():
    token = "8888888888888:" + "TEST_DUMMY_TOKEN_REDACTED_abcdefghijklmnopqr"
    assert _deep_redact(token) == "[REDACTED_BOT_TOKEN]"
    assert _deep_redact({"bot_token": token})["bot_token"] == "[REDACTED_BOT_TOKEN]"
    print("PASS test_redact_bot_token_strings")

def test_is_duplicate():
    r = {"provider": "telegram", "message_id": "2195", "artifact_id": "test::v1"}
    existing = [{"provider": "telegram", "message_id": "2195", "artifact_id": "test::v1"}]
    dup, _ = is_duplicate(r, existing)
    assert dup is True
    assert is_duplicate({"provider": "x", "message_id": "9999", "artifact_id": ""}, existing)[0] is False
    print("PASS test_is_duplicate")

def test_requirements():
    req_path = ROOT / "requirements.txt"
    lines = [l.strip() for l in req_path.read_text().splitlines() if l.strip() and not l.startswith("#")]
    rl = [l for l in lines if l.startswith("requests")]
    assert len(rl) == 1, f"requests lines: {rl}"
    assert rl[0] == "requests>=2.28.0"
    print("PASS test_requirements")

def test_hash_chat_id_deterministic():
    h1, h2, h3 = _hash_chat_id(-1003977074640), _hash_chat_id(-1003977074640), _hash_chat_id(-1001234567890)
    assert h1 == h2 and h1 != h3 and len(h1) == 64
    assert _hash_chat_id(None) == "" and _hash_chat_id("") == ""
    print("PASS test_hash_chat_id_deterministic")

def test_mask_chat_id():
    m = _mask_chat_id(-1003977074640)
    assert m.startswith("-") and "****" in m and "100" in m and "4640" in m
    assert _mask_chat_id(None) == "" and _mask_chat_id("") == ""
    print("PASS test_mask_chat_id")

def test_record_has_hash_and_masked():
    r1 = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    r2 = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    assert len(r1["target_id_hash"]) == 64
    assert "****" in r1["target_id_masked"]
    assert r1["target_id_hash"] == r2["target_id_hash"]
    print("PASS test_record_has_hash_and_masked")

def test_raw_chat_id_not_leaked():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    rs = json.dumps(record, ensure_ascii=False)
    assert "-1003977074640" not in rs
    assert record["target_id_hash"] in rs
    print("PASS test_raw_chat_id_not_leaked")

def test_extract_raw_chat_id():
    assert _extract_raw_chat_id(_R2_SEND_RESULT) == -1003977074640
    assert _extract_raw_chat_id({}) is None
    print("PASS test_extract_raw_chat_id")


# ============================================================
# v1.9C-S1 New Tests
# ============================================================

def test_salt_key_created():
    import market_radar_history as mh
    mh._salt_cache = None
    temp_salt = _make_temp_salt_key()
    try:
        assert not temp_salt.exists()
        salt = load_or_create_salt(salt_path=temp_salt)
        assert len(salt) == 64
        assert temp_salt.exists()
        lines = temp_salt.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert lines[0] == SALT_MAGIC
        assert lines[1] == salt
    finally:
        mh._salt_cache = None
        if temp_salt.exists(): temp_salt.unlink()
    print("PASS test_salt_key_created")

def test_salt_key_reused():
    import market_radar_history as mh
    mh._salt_cache = None
    temp_salt = _make_temp_salt_key()
    try:
        salt1 = load_or_create_salt(salt_path=temp_salt)
        mh._salt_cache = None
        salt2 = load_or_create_salt(salt_path=temp_salt)
        assert salt1 == salt2
        lines = temp_salt.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
    finally:
        mh._salt_cache = None
        if temp_salt.exists(): temp_salt.unlink()
    print("PASS test_salt_key_reused")

def test_chat_id_hash_stable():
    import market_radar_history as mh
    mh._salt_cache = None
    temp_salt = _make_temp_salt_key()
    try:
        load_or_create_salt(salt_path=temp_salt)
        orig = mh.SALT_KEY_FILE
        mh.SALT_KEY_FILE = temp_salt
        h1 = _hash_chat_id(-1003977074640)
        mh._salt_cache = None
        h2 = _hash_chat_id(-1003977074640)
        assert h1 == h2 and len(h1) == 64
        mh.SALT_KEY_FILE = orig
    finally:
        mh._salt_cache = None
        if temp_salt.exists(): temp_salt.unlink()
    print("PASS test_chat_id_hash_stable")

def test_target_masked_title():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    title = record.get("target_masked_title", "")
    assert title and "****" in title
    assert build_target_masked_title("-100****4640", "group") == "TG群-已脱敏 (ID: -100****4640)"
    print("PASS test_target_masked_title")

def test_content_hash():
    r1 = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    r2 = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    assert len(r1["content_hash"]) == 32
    assert r1["content_hash"] == r2["content_hash"]
    assert generate_content_hash({}) == ""
    print("PASS test_content_hash")

def test_semantic_tags():
    text = _extract_payload_text(_R2_SEND_RESULT)
    tags = generate_semantic_tags(text)
    assert "Market_Radar" in tags
    assert "Whale_Move" in tags
    assert "PnL_Update" in tags
    assert generate_semantic_tags("") == ["Market_Radar"]
    assert "Liquidation_Risk" in generate_semantic_tags("清算爆仓liquidation")
    print("PASS test_semantic_tags")

def test_authorization_type():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    assert record.get("authorization_type") == "user_preauthorized_tg_group"
    print("PASS test_authorization_type")

def test_reverse_trace():
    record = build_history_record(
        send_result=_R2_SEND_RESULT, source_result_file="results/test.json",
        candidate_md_path="results/x.md", handoff_path="runs/y.md"
    )
    trace = record.get("reverse_trace", {})
    for k in ["manifest_path", "send_result_path", "handoff_path", "source_task_id"]:
        assert k in trace, f"Missing {k} in reverse_trace: {trace}"
    t2 = build_reverse_trace(source_result_file="a.json", handoff_path="b.md",
                              source_task_id="task_1", source_run_id="run_2")
    assert t2["source_task_id"] == "task_1" and t2["source_run_id"] == "run_2"
    print("PASS test_reverse_trace")

def test_atomic_watchdog_normal():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    temp_path = _make_temp_jsonl()
    try:
        wr = write_published_history(record, history_path=temp_path)
        assert wr["written"] and wr["watch_line_ok"]
        v = _verify_last_line(temp_path)
        assert v["ok"] and v["record"]["message_id"] == "2195"
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_atomic_watchdog_normal")

def test_atomic_watchdog_newline_repair():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    temp_path = _make_temp_jsonl()
    try:
        assert write_published_history(record, history_path=temp_path)["written"]
        content = temp_path.read_text(encoding="utf-8").rstrip("\n")
        temp_path.write_text(content, encoding="utf-8")
        with open(temp_path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            assert f.read(1) != b"\n"
        r2r = dict(_R2_SEND_RESULT); r2r["message_id"] = "9998"
        r2 = build_history_record(send_result=r2r, source_result_file="results/t2.json")
        wr2 = write_published_history(r2, history_path=temp_path)
        assert wr2["written"] and wr2["watch_line_ok"]
        records = _load_existing_records(temp_path)
        assert len(records) == 2
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_atomic_watchdog_newline_repair")

def test_atomic_watchdog_single_line():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    assert "\n" not in json.dumps(record, ensure_ascii=False)
    print("PASS test_atomic_watchdog_single_line")

def test_atomic_watchdog_no_dupes():
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    temp_path = _make_temp_jsonl()
    try:
        for i in range(3):
            wr = write_published_history(record, history_path=temp_path)
            assert wr["written"] == (i == 0)
        assert len(_load_existing_records(temp_path)) == 1
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_atomic_watchdog_no_dupes")

def test_salt_not_leaked():
    salt = _get_salt()
    record = build_history_record(send_result=_R2_SEND_RESULT, source_result_file="results/test.json")
    rs = json.dumps(record, ensure_ascii=False)
    assert salt not in rs, "CRITICAL: Salt leaked!"
    for k, v in record.items():
        if isinstance(v, str):
            assert salt not in v, f"Salt in field {k}"
        elif isinstance(v, dict):
            assert salt not in json.dumps(v, ensure_ascii=False), f"Salt in dict field {k}"
    print("PASS test_salt_not_leaked")

def test_ensure_trailing_newline():
    temp_path = _make_temp_jsonl()
    try:
        assert _ensure_trailing_newline(temp_path) is False
        temp_path.write_text('{"test": 1}', encoding="utf-8")
        assert _ensure_trailing_newline(temp_path) is True
        assert temp_path.read_text(encoding="utf-8").endswith("\n")
        assert _ensure_trailing_newline(temp_path) is False
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_ensure_trailing_newline")

def test_verify_last_line():
    temp_path = _make_temp_jsonl()
    try:
        assert _verify_last_line(temp_path)["ok"] is False
        temp_path.write_text('{"msg": 1}\n{"msg": 2}\n', encoding="utf-8")
        v = _verify_last_line(temp_path)
        assert v["ok"] and v["record"]["msg"] == 2
        temp_path.write_text('{"msg": 1}\nbad json\n', encoding="utf-8")
        assert _verify_last_line(temp_path)["ok"] is False
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("PASS test_verify_last_line")

def test_verify_salt_file():
    import market_radar_history as mh
    mh._salt_cache = None
    temp_salt = _make_temp_salt_key()
    try:
        orig = mh.SALT_KEY_FILE
        mh.SALT_KEY_FILE = temp_salt
        assert verify_salt_file()["exists"] is False
        load_or_create_salt(salt_path=temp_salt)
        r = verify_salt_file()
        assert r["exists"] and r["magic_valid"]
        mh.SALT_KEY_FILE = orig
    finally:
        mh._salt_cache = None
        if temp_salt.exists(): temp_salt.unlink()
    print("PASS test_verify_salt_file")


# ============================================================
# Main runner
# ============================================================

def run_all_tests():
    tests = [
        ("Build history record", test_build_history_record_from_r2),
        ("Chat ID redacted", test_chat_id_redacted),
        ("No token/chat_id leak", test_no_token_or_chat_id_leak),
        ("Write succeeds", test_write_history_succeeds),
        ("Dedup same message_id", test_dedup_same_message_id),
        ("Different records coexist", test_different_records_coexist),
        ("Dedup by artifact+message", test_dedup_by_artifact_message_id),
        ("Deep redact nested", test_deep_redact_nested),
        ("Redact bot token strings", test_redact_bot_token_strings),
        ("is_duplicate logic", test_is_duplicate),
        ("requirements.txt", test_requirements),
        ("Hash deterministic", test_hash_chat_id_deterministic),
        ("Mask chat_id", test_mask_chat_id),
        ("Record has hash+masked", test_record_has_hash_and_masked),
        ("Raw chat_id not leaked", test_raw_chat_id_not_leaked),
        ("Extract raw chat_id", test_extract_raw_chat_id),
        ("salt.key created", test_salt_key_created),
        ("salt.key reused", test_salt_key_reused),
        ("chat_id_hash stable", test_chat_id_hash_stable),
        ("target_masked_title", test_target_masked_title),
        ("content_hash", test_content_hash),
        ("semantic_tags", test_semantic_tags),
        ("authorization_type", test_authorization_type),
        ("reverse_trace", test_reverse_trace),
        ("Atomic Watchdog: normal", test_atomic_watchdog_normal),
        ("Atomic Watchdog: newline repair", test_atomic_watchdog_newline_repair),
        ("Atomic Watchdog: single-line", test_atomic_watchdog_single_line),
        ("Atomic Watchdog: no dupes", test_atomic_watchdog_no_dupes),
        ("salt not leaked", test_salt_not_leaked),
        ("ensure trailing newline", test_ensure_trailing_newline),
        ("verify last line", test_verify_last_line),
        ("verify_salt_file", test_verify_salt_file),
    ]
    passed = failed = 0
    failures = []
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            failures.append((name, str(e)))
            print(f"FAIL {name}: {e}")
        except Exception as e:
            failed += 1
            failures.append((name, f"ERROR: {e}"))
            print(f"ERROR {name}: {e}")
    return {"total": len(tests), "passed": passed, "failed": failed, "failures": failures}

if __name__ == "__main__":
    results = run_all_tests()
    print(f"\nTotal: {results['total']}, Passed: {results['passed']}, Failed: {results['failed']}")
    if results["failures"]:
        for name, err in results["failures"]:
            print(f"  - {name}: {err}")
    sys.exit(0 if results["failed"] == 0 else 1)

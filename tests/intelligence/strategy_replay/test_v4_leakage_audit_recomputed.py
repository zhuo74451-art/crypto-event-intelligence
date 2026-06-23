"""Test V4 leakage audit is recomputed correctly and detects injected faults."""
import json, subprocess, sys, pathlib, hashlib, shutil, tempfile

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "strategy_replay"
BASE = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def _audit_run(script, args_list):
    cmd = [sys.executable, "-X", "utf8", str(script)] + args_list
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        out = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        out = {}
    return result.returncode, out


class TestV4LeakageAuditRecomputed:

    def test_audit_passes_on_clean_data(self):
        exitcode, result = _audit_run(
            SD / "audit_replay_leakage.py",
            ["--results", str(BASE / "strategy_replay_results_v2.jsonl"),
             "--hypotheses", str(BASE / "strategy_hypotheses_v2.jsonl"),
             "--decision-inputs", str(BASE / "decision_inputs_v1.jsonl"),
             "--horizon-windows", str(BASE / "upstream" / "lane_b_horizon_windows_v3.jsonl"),
             "--decision-seal", str(BASE / "decision_seal_v1.json"),
             "--evaluation-outcomes", str(BASE / "evaluation_outcomes_v1.jsonl")])
        assert exitcode == 0, f"Audit failed: {result}"
        assert result.get("results_checked") == 28
        assert result.get("hypotheses_checked") == 32
        assert result.get("decision_inputs_checked") == 16
        assert result.get("horizon_windows_indexed") == 72
        assert result.get("evaluation_outcomes_checked") == 32
        assert result.get("violation_count") == 0

    def test_audit_detects_4h_window_reference(self):
        """Inject a 4h future window reference into a hypothesis's supporting_evidence_refs."""
        # Read original
        with open(BASE / "strategy_hypotheses_v2.jsonl") as f:
            hyps = [json.loads(l) for l in f if l.strip()]

        orig = hyps[0]
        modified = dict(orig)
        modified["supporting_evidence_refs"] = orig.get("supporting_evidence_refs", []) + ["4h_target_window_xyz"]

        # Write to temp and run audit
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as tf:
            for h in hyps[1:]:
                tf.write(json.dumps(h) + "\n")
            tf.write(json.dumps(modified) + "\n")
            tmp_path = tf.name

        try:
            exitcode, result = _audit_run(
                SD / "audit_replay_leakage.py",
                ["--results", str(BASE / "strategy_replay_results_v2.jsonl"),
                 "--hypotheses", tmp_path,
                 "--decision-inputs", str(BASE / "decision_inputs_v1.jsonl"),
                 "--horizon-windows", str(BASE / "upstream" / "lane_b_horizon_windows_v3.jsonl"),
                 "--decision-seal", str(BASE / "decision_seal_v1.json")])
            assert exitcode != 0, "Audit should have failed with 4h reference"
            assert len(result.get("violations", {}).get("future_window_references", [])) > 0
        finally:
            pathlib.Path(tmp_path).unlink(missing_ok=True)

    def test_audit_detects_decision_seal_mismatch(self):
        """Modify decision seal hash and verify audit fails."""
        with open(BASE / "decision_seal_v1.json") as f:
            seal = json.load(f)

        tampered = dict(seal)
        tampered["decision_inputs_sha256"] = "0" * 64

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(tampered, tf)
            tmp_path = tf.name

        try:
            exitcode, result = _audit_run(
                SD / "audit_replay_leakage.py",
                ["--results", str(BASE / "strategy_replay_results_v2.jsonl"),
                 "--hypotheses", str(BASE / "strategy_hypotheses_v2.jsonl"),
                 "--decision-inputs", str(BASE / "decision_inputs_v1.jsonl"),
                 "--horizon-windows", str(BASE / "upstream" / "lane_b_horizon_windows_v3.jsonl"),
                 "--decision-seal", tmp_path])
            assert exitcode != 0, "Audit should have failed with seal mismatch"
            assert result.get("decision_seal_checks", {}).get("failures", 0) > 0
        finally:
            pathlib.Path(tmp_path).unlink(missing_ok=True)

    def test_audit_integrity_v4_file_exists(self):
        assert (BASE / "pilot_integrity_audit_v4.json").exists()
        with open(BASE / "pilot_integrity_audit_v4.json") as f:
            audit = json.load(f)
        assert audit["overall_verdict"] == "pass"
        assert audit["leakage_audit"]["results_checked"] == 28
        assert audit["leakage_audit"]["hypotheses_checked"] == 32

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a local Markdown/CSV project dashboard.")
    parser.add_argument("--output", default=str(ROOT / "docs" / "PROJECT_DASHBOARD.md"))
    parser.add_argument("--metrics-output", default=str(ROOT / "results" / "project_dashboard_metrics.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def first_row(path: Path) -> dict:
    df = read_csv(path)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def count_rows(path: Path) -> int | str:
    df = read_csv(path)
    if df.empty:
        return 0 if path.exists() else "missing"
    return int(len(df))


def value_counts(path: Path, column: str) -> dict[str, int]:
    df = read_csv(path)
    if df.empty or column not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df[column].value_counts().to_dict().items()}


def file_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        updated = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return f"{path.stat().st_size} bytes, updated {updated}"
    except Exception:
        return "present"


def claude_question_count(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 20
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Current Count:\s*(\d+)\s*/\s*(\d+)", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    open_count = len(re.findall(r"\|\s*\d+\s*\|.*?\|\s*open\s*\|", text))
    return open_count, 20


def metric_rows() -> list[dict]:
    relevance = first_row(ROOT / "results" / "v06_relevance_filter_summary.csv")
    time_audit = first_row(ROOT / "results" / "v043_time_provenance_summary.csv")
    label_eval = first_row(ROOT / "results" / "v06_manual_label_eval_summary.csv")
    label_sheet = first_row(ROOT / "results" / "v06_manual_label_sheet_summary.csv")
    auto_label = first_row(ROOT / "results" / "v06_auto_label_summary.csv")
    auto_verify = first_row(ROOT / "results" / "v06_auto_verify_summary.csv")
    auto_close = first_row(ROOT / "results" / "v06_auto_close_summary.csv")
    auto_fill = first_row(ROOT / "results" / "v06_auto_fill_unlabeled_summary.csv")
    label_batch = first_row(ROOT / "results" / "v06_labeling_batch_summary.csv")
    review_required_summary = first_row(ROOT / "results" / "v06_manual_review_required_summary.csv")
    suggestion = first_row(ROOT / "results" / "v043_older_review_suggestion_summary.csv")
    mature = first_row(ROOT / "results" / "v043_older_mature_filter_summary.csv")
    selected = first_row(ROOT / "results" / "v043_older_stratified_selection_summary.csv")
    strat_diag = read_csv(ROOT / "results" / "v043_stratified_selection_diagnostics.csv")
    selection_v06_audit = first_row(ROOT / "results" / "v043_selection_vs_v06_relevance_summary.csv")
    v06_filtered_preview = first_row(ROOT / "results" / "v06_filtered_mature_sample_preview_summary.csv")
    v06_asset_audit = first_row(ROOT / "results" / "v06_filtered_preview_asset_attribution_summary.csv")
    v06_clean_preview = first_row(ROOT / "results" / "v06_clean_low_risk_preview_summary.csv")
    v06_low_risk_backfill_counts = value_counts(ROOT / "results" / "v06_clean_low_risk_preview_event_price_backfill.csv", "status")
    v06_low_risk_quality_counts = value_counts(ROOT / "results" / "v06_clean_low_risk_preview_event_quality_report.csv", "quality_status")
    backtest_readiness = first_row(ROOT / "results" / "backtest_readiness_summary.csv")
    tg_feedback = first_row(ROOT / "results" / "tg_draft_feedback_summary.csv")
    tg_validation = first_row(ROOT / "results" / "tg_draft_validation_summary.csv")
    daily_pilot = first_row(ROOT / "results" / "daily_private_pilot_summary.csv")
    other_review_summary = first_row(ROOT / "results" / "v06_other_review_reason_summary.csv")
    fix_plan = read_csv(ROOT / "results" / "v06_asset_attribution_fix_plan_summary.csv")
    entity_packet = read_csv(ROOT / "results" / "v06_entity_rule_review_packet_summary.csv")
    tg_gate = read_csv(ROOT / "results" / "v06_tg_pilot_gate_report.csv")
    claude_index = read_csv(ROOT / "results" / "claude_response_index.csv")
    claude_decisions = read_csv(ROOT / "data" / "claude_decision_review_queue.csv")
    secret_summary = first_row(ROOT / "results" / "secret_leak_summary.csv")
    project_os_validation = read_csv(ROOT / "results" / "project_os_validation_report.csv")
    command_registry = first_row(ROOT / "results" / "command_registry_summary.csv")
    review_actions = first_row(ROOT / "results" / "project_review_action_summary.csv")
    environment_summary = first_row(ROOT / "results" / "local_environment_summary.csv")
    artifact_manifest = first_row(ROOT / "results" / "artifact_manifest_summary.csv")
    claude_open, claude_threshold = claude_question_count(ROOT / "docs" / "CLAUDE_QUESTION_BACKLOG.md")
    sheet_df = read_csv(ROOT / "data" / "v06_manual_label_sheet.csv")
    if not sheet_df.empty:
        manual_review_required_now = int(
            sheet_df.get("manual_review_required", pd.Series("", index=sheet_df.index))
            .astype(str)
            .str.lower()
            .eq("true")
            .sum()
        )
    else:
        manual_review_required_now = "missing"
    if not strat_diag.empty:
        selected_diag_count = int(pd.to_numeric(strat_diag.get("selected_count", pd.Series(dtype=str)), errors="coerce").fillna(0).sum())
        capped_event_types = int(strat_diag.get("cap_binding", pd.Series(dtype=str)).astype(str).str.lower().eq("true").sum())
        unused_eligible_after_cap = int(
            pd.to_numeric(strat_diag.get("unused_eligible_after_cap", pd.Series(dtype=str)), errors="coerce").fillna(0).sum()
        )
    else:
        selected_diag_count = "missing"
        capped_event_types = "missing"
        unused_eligible_after_cap = "missing"
    if not fix_plan.empty and "recommended_action" in fix_plan.columns:
        fix_counts = dict(zip(fix_plan["recommended_action"].astype(str), fix_plan["count"].astype(str)))
    else:
        fix_counts = {}
    if not entity_packet.empty and "entity_review_type" in entity_packet.columns:
        entity_counts = dict(zip(entity_packet["entity_review_type"].astype(str), entity_packet["count"].astype(str)))
    else:
        entity_counts = {}
    if not tg_gate.empty and {"gate", "actual", "status"}.issubset(tg_gate.columns):
        tg_gate_values = {str(row["gate"]): (str(row["actual"]), str(row["status"])) for _, row in tg_gate.iterrows()}
    else:
        tg_gate_values = {}
    if not claude_decisions.empty and "decision_status" in claude_decisions.columns:
        pending_claude_decisions = int(claude_decisions["decision_status"].astype(str).eq("pending").sum())
    else:
        pending_claude_decisions = "missing"
    if not project_os_validation.empty and "status" in project_os_validation.columns:
        project_os_fail_count = int(project_os_validation["status"].astype(str).str.lower().isin(["fail", "blocked"]).sum())
        project_os_review_count = int(project_os_validation["status"].astype(str).str.lower().eq("review").sum())
    else:
        project_os_fail_count = "missing"
        project_os_review_count = "missing"

    rows = [
        {
            "area": "project_os",
            "metric": "project_os_validation_fail_count",
            "value": project_os_fail_count,
            "target": "0",
            "status": "pass" if project_os_fail_count == 0 else "fail",
        },
        {
            "area": "environment",
            "metric": "local_environment_fail_count",
            "value": environment_summary.get("fail_count", "missing"),
            "target": "0",
            "status": "pass" if environment_summary.get("overall_status") == "pass" else "fail",
        },
        {
            "area": "project_os",
            "metric": "command_registry_missing_scripts",
            "value": command_registry.get("missing_script_count", "missing"),
            "target": "0",
            "status": "pass" if command_registry.get("status") == "pass" else "fail",
        },
        {
            "area": "project_os",
            "metric": "review_action_unknown_rules",
            "value": review_actions.get("unknown_rule_count", "missing"),
            "target": "0",
            "status": "pass" if review_actions.get("unknown_rule_count") == "0" else "review",
        },
        {
            "area": "project_os",
            "metric": "artifact_missing_required_count",
            "value": artifact_manifest.get("missing_required_count", "missing"),
            "target": "0",
            "status": "pass" if artifact_manifest.get("missing_required_count") == "0" else "fail",
        },
        {
            "area": "project_os",
            "metric": "artifact_stale_required_count",
            "value": artifact_manifest.get("stale_required_count", "missing"),
            "target": "0",
            "status": "pass" if artifact_manifest.get("stale_required_count") == "0" else "fail",
        },
        {
            "area": "project_os",
            "metric": "open_review_actions",
            "value": review_actions.get("open_action_count", "missing"),
            "target": "tracked",
            "status": "info",
        },
        {
            "area": "project_os",
            "metric": "project_os_validation_review_count",
            "value": project_os_review_count,
            "target": "tracked",
            "status": "review" if project_os_review_count not in {"missing", 0} else "pass",
        },
        {"area": "data", "metric": "older500_candidates", "value": count_rows(ROOT / "data" / "event_candidates_real_500_older_review.csv"), "target": "", "status": "info"},
        {"area": "data", "metric": "v06_publish_review_rows", "value": count_rows(ROOT / "data" / "event_candidates_v06_publish_review_queue.csv"), "target": "", "status": "info"},
        {"area": "data", "metric": "v06_other_review_rows", "value": count_rows(ROOT / "data" / "event_candidates_v06_other_review_queue.csv"), "target": "", "status": "info"},
        {"area": "data", "metric": "v06_discard_audit_rows", "value": count_rows(ROOT / "data" / "event_candidates_v06_discard_audit_sample.csv"), "target": "", "status": "info"},
        {
            "area": "relevance",
            "metric": "other_review_auto_discard_candidate_count",
            "value": other_review_summary.get("auto_discard_candidate_count", "missing"),
            "target": "taxonomy cleanup candidate",
            "status": "info",
        },
        {
            "area": "relevance",
            "metric": "other_review_keep_review_count",
            "value": other_review_summary.get("keep_review_count", "missing"),
            "target": "small manual queue",
            "status": "review" if other_review_summary.get("keep_review_count", "0") not in {"", "0"} else "pass",
        },
        {"area": "relevance", "metric": "auto_publish_count", "value": relevance.get("auto_publish_count", "missing"), "target": "0", "status": "pass" if relevance.get("auto_publish_count") == "0" else "review"},
        {"area": "relevance", "metric": "human_review_count", "value": relevance.get("human_review_count", "missing"), "target": "", "status": "info"},
        {"area": "relevance", "metric": "discard_count", "value": relevance.get("discard_count", "missing"), "target": "", "status": "info"},
        {"area": "time", "metric": "time_audit_fail_count", "value": time_audit.get("fail_count", "missing"), "target": "0", "status": "pass" if time_audit.get("fail_count") == "0" else "fail"},
        {"area": "time", "metric": "price_kline_lag_out_of_range_count", "value": time_audit.get("price_kline_lag_out_of_range_count", "missing"), "target": "0", "status": "pass" if time_audit.get("price_kline_lag_out_of_range_count") == "0" else "fail"},
        {
            "area": "security",
            "metric": "secret_leak_count",
            "value": secret_summary.get("leak_count", "missing"),
            "target": "0",
            "status": "pass" if secret_summary.get("status") == "pass" else "fail",
        },
        {"area": "labels", "metric": "manual_label_rows", "value": label_sheet.get("total_label_rows", "missing"), "target": ">=200", "status": "pass" if int(label_sheet.get("total_label_rows", "0") or 0) >= 200 else "fail"},
        {
            "area": "labels",
            "metric": "manual_labeled_rows",
            "value": label_eval.get("labeled_rows", "missing"),
            "target": ">=200 before TG",
            "status": "pass" if int(label_eval.get("labeled_rows", "0") or 0) >= 200 else ("blocked" if label_eval.get("labeled_rows", "0") == "0" else "review"),
        },
        {"area": "labels", "metric": "auto_prefilled_rows", "value": label_eval.get("auto_prefilled_rows", "missing"), "target": "increase", "status": "info"},
        {"area": "labels", "metric": "auto_label_suggest_ready_rows", "value": auto_label.get("suggest_ready_rows", "missing"), "target": "", "status": "info"},
        {"area": "labels", "metric": "manual_review_required_rows", "value": manual_review_required_now, "target": "decrease by batch review", "status": "info"},
        {
            "area": "labels",
            "metric": "manual_review_required_rate",
            "value": review_required_summary.get("manual_review_required_rate", "missing"),
            "target": "<=0.085 before TG drafts",
            "status": "pass" if review_required_summary.get("status") == "pass" else "review",
        },
        {"area": "labels", "metric": "auto_verified_rows_in_run", "value": auto_verify.get("auto_verified_rows_in_run", "missing"), "target": ">=0", "status": "info"},
        {"area": "labels", "metric": "provisional_remaining", "value": auto_verify.get("provisional_remaining_after_run", "missing"), "target": "decrease", "status": "info"},
        {"area": "labels", "metric": "auto_closed_rows_in_run", "value": auto_close.get("auto_closed_rows_in_run", "missing"), "target": ">=0", "status": "info"},
        {"area": "labels", "metric": "auto_filled_rows_in_run", "value": auto_fill.get("auto_filled_rows_in_run", "missing"), "target": ">=0", "status": "info"},
        {"area": "labels", "metric": "next_label_batch_size", "value": label_batch.get("selected_batch_size", "missing"), "target": "30", "status": "info"},
        {"area": "labels", "metric": "next_batch_review_required", "value": label_batch.get("selected_manual_review_required", "missing"), "target": "", "status": "info"},
        {
            "area": "tg_gate",
            "metric": "review_failure_modes_doc",
            "value": tg_gate_values.get("review_failure_modes_doc", ("missing", "fail"))[0],
            "target": "required sections",
            "status": tg_gate_values.get("review_failure_modes_doc", ("missing", "fail"))[1],
        },
        {
            "area": "tg_gate",
            "metric": "rollback_workflow_doc",
            "value": tg_gate_values.get("rollback_workflow_doc", ("missing", "fail"))[0],
            "target": "required sections",
            "status": tg_gate_values.get("rollback_workflow_doc", ("missing", "fail"))[1],
        },
        {
            "area": "tg_draft",
            "metric": "private_pilot_draft_count",
            "value": tg_feedback.get("total_drafts", "missing"),
            "target": "10-20",
            "status": "pass" if tg_feedback.get("total_drafts") in {str(i) for i in range(10, 21)} else "review",
        },
        {
            "area": "tg_draft",
            "metric": "private_pilot_reviewed_count",
            "value": tg_feedback.get("reviewed_count", "missing"),
            "target": "review before any posting",
            "status": "info",
        },
        {
            "area": "tg_draft",
            "metric": "private_pilot_auto_send_enabled_count",
            "value": tg_feedback.get("auto_send_enabled_count", "missing"),
            "target": "0",
            "status": "pass" if tg_feedback.get("auto_send_enabled_count") == "0" else "fail",
        },
        {
            "area": "tg_draft",
            "metric": "private_pilot_validation_fail_count",
            "value": tg_validation.get("fail_count", "missing"),
            "target": "0",
            "status": "pass" if tg_validation.get("fail_count") == "0" else "fail",
        },
        {
            "area": "tg_draft",
            "metric": "private_pilot_validation_warning_count",
            "value": tg_validation.get("warning_count", "missing"),
            "target": "0 preferred",
            "status": "info" if tg_validation.get("warning_count", "0") == "0" else "review",
        },
        {
            "area": "tg_draft",
            "metric": "daily_private_pilot_status",
            "value": daily_pilot.get("status", "missing"),
            "target": "ready_for_review or better",
            "status": "pass"
            if daily_pilot.get("status") in {"ready_for_review", "pilot_signal_ready"}
            else ("review" if daily_pilot.get("status") == "needs_rule_cleanup" else "fail"),
        },
        {"area": "backtest", "metric": "mature_72h_count", "value": mature.get("mature_72h_count", "missing"), "target": "", "status": "info"},
        {"area": "backtest", "metric": "stratified_selected_count", "value": selected.get("selected_count", "missing"), "target": "50 desired", "status": "review" if selected.get("selected_count") and selected.get("selected_count") != "50" else "pass"},
        {"area": "backtest", "metric": "stratified_diagnostic_selected", "value": selected_diag_count, "target": "explain underfill", "status": "info"},
        {"area": "backtest", "metric": "stratified_capped_event_types", "value": capped_event_types, "target": "review caps with Claude", "status": "info"},
        {"area": "backtest", "metric": "stratified_unused_eligible_after_cap", "value": unused_eligible_after_cap, "target": "do not relax automatically", "status": "info"},
        {
            "area": "backtest",
            "metric": "v043_selected_v06_discard_rows",
            "value": selection_v06_audit.get("v06_discard_rows", "missing"),
            "target": "0 for clean current sample",
            "status": "review" if selection_v06_audit.get("v06_discard_rows", "0") not in {"", "0"} else "pass",
        },
        {
            "area": "backtest",
            "metric": "v043_selected_v06_discard_rate",
            "value": selection_v06_audit.get("v06_discard_rate", "missing"),
            "target": "historical baseline only",
            "status": "review" if selection_v06_audit.get("v06_discard_rows", "0") not in {"", "0"} else "pass",
        },
        {
            "area": "backtest",
            "metric": "v043_safe_as_current_evidence",
            "value": selection_v06_audit.get("safe_to_use_as_current_evidence", "missing"),
            "target": "yes for current conclusions",
            "status": "review" if selection_v06_audit.get("safe_to_use_as_current_evidence") == "no" else "pass",
        },
        {
            "area": "backtest",
            "metric": "v06_filtered_preview_selected",
            "value": v06_filtered_preview.get("selected_count", "missing"),
            "target": "preview only",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_filtered_preview_eligible",
            "value": v06_filtered_preview.get("eligible_count", "missing"),
            "target": "preview only",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_preview_asset_high_risk",
            "value": v06_asset_audit.get("high_risk_rows", "missing"),
            "target": "0 before clean backtest",
            "status": "review" if v06_asset_audit.get("high_risk_rows", "0") not in {"", "0"} else "pass",
        },
        {
            "area": "backtest",
            "metric": "v06_preview_asset_low_risk",
            "value": v06_asset_audit.get("low_risk_rows", "missing"),
            "target": "safe subset",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_clean_low_risk_preview_rows",
            "value": v06_clean_preview.get("selected_low_risk_rows", "missing"),
            "target": "sanity-check only",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_low_risk_backfill_ok_rows",
            "value": v06_low_risk_backfill_counts.get("ok", "missing") if v06_low_risk_backfill_counts else "missing",
            "target": "preview only",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_low_risk_quality_pass_rows",
            "value": v06_low_risk_quality_counts.get("pass", "missing") if v06_low_risk_quality_counts else "missing",
            "target": "preview only",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "ready_for_statistical_conclusions",
            "value": backtest_readiness.get("ready_for_statistical_conclusions", "missing"),
            "target": "yes before product claims",
            "status": "review" if backtest_readiness.get("ready_for_statistical_conclusions") == "no" else "pass",
        },
        {
            "area": "backtest",
            "metric": "backtest_readiness_review_count",
            "value": backtest_readiness.get("review_count", "missing"),
            "target": "0 before conclusion use",
            "status": "review" if backtest_readiness.get("review_count", "0") not in {"", "0"} else "pass",
        },
        {
            "area": "backtest",
            "metric": "backtest_readiness_local_review_count",
            "value": backtest_readiness.get("local_review_count", "missing"),
            "target": "local cleanup queue",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "backtest_readiness_claude_review_count",
            "value": backtest_readiness.get("claude_review_count", "missing"),
            "target": "direction queue",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "backtest_readiness_mixed_review_count",
            "value": backtest_readiness.get("mixed_local_claude_review_count", "missing"),
            "target": "local then Claude",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_fix_plan_exclude_rows",
            "value": fix_counts.get("exclude_from_clean_backtest", "missing"),
            "target": "do not backtest",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_fix_plan_unsupported_rows",
            "value": fix_counts.get("route_unsupported_research", "missing"),
            "target": "no fake BTC/ETH",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_fix_plan_entity_review_rows",
            "value": fix_counts.get("needs_entity_rule_review", "missing"),
            "target": "rule improvement",
            "status": "info",
        },
        {
            "area": "backtest",
            "metric": "v06_entity_protocol_exploit_policy_rows",
            "value": entity_counts.get("protocol_exploit_primary_asset_policy", "missing"),
            "target": "ask Claude/policy",
            "status": "review" if entity_counts.get("protocol_exploit_primary_asset_policy", "0") not in {"", "0"} else "pass",
        },
        {
            "area": "backtest",
            "metric": "v06_entity_unsupported_primary_rows",
            "value": entity_counts.get("unsupported_primary_asset", "missing"),
            "target": "rule candidate",
            "status": "info",
        },
        {"area": "suggestions", "metric": "suggest_include_count", "value": suggestion.get("suggest_include_count", "missing"), "target": "", "status": "info"},
        {
            "area": "claude",
            "metric": "claude_response_files",
            "value": int(len(claude_index)) if not claude_index.empty else 0,
            "target": "indexed",
            "status": "info",
        },
        {
            "area": "claude",
            "metric": "pending_claude_decision_items",
            "value": pending_claude_decisions,
            "target": "review before implementation",
            "status": "review" if pending_claude_decisions not in {"missing", 0} else "pass",
        },
        {"area": "claude", "metric": "claude_open_questions", "value": claude_open, "target": claude_threshold, "status": "wait" if claude_open < claude_threshold else "ready"},
    ]
    return rows


def counts_block(title: str, counts: dict[str, int]) -> str:
    lines = [f"## {title}", ""]
    if not counts:
        lines.append("_No data._")
        return "\n".join(lines)
    lines.extend(["| value | count |", "|---|---:|"])
    for key, value in counts.items():
        lines.append(f"| {key or '(blank)'} | {value} |")
    return "\n".join(lines)


def render_markdown(rows: list[dict]) -> str:
    status_order = {"fail": 0, "blocked": 1, "review": 2, "wait": 3, "info": 4, "pass": 5}
    sorted_rows = sorted(rows, key=lambda row: (status_order.get(str(row["status"]), 9), row["area"], row["metric"]))
    gate_failures = [row for row in rows if row["status"] in {"fail", "blocked"}]
    review_items = [row for row in rows if row["status"] == "review"]
    claude_row = next((row for row in rows if row["metric"] == "claude_open_questions"), None)
    claude_ready = bool(claude_row and str(claude_row.get("status")) == "ready")

    lines = [
        "# Project Dashboard",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        "## Gates",
        "",
        f"- Blocking/failing items: {len(gate_failures)}",
        f"- Review items: {len(review_items)}",
        "",
        "| area | metric | value | target | status |",
        "|---|---|---:|---|---|",
    ]
    for row in sorted_rows:
        lines.append(
            f"| {row['area']} | {row['metric']} | {row['value']} | {row['target']} | {row['status']} |"
        )

    next_actions = [
        "1. Keep review failure modes and rollback workflow current; they are now part of the TG draft gate.",
        "2. Keep `auto_publish` disabled; TG work can only be draft-only after direction approval.",
        "3. Use synthetic edge cases and holdout audit rows as regression tests for labeling changes.",
    ]
    if claude_ready:
        next_actions.append("4. Send `docs/CLAUDE_NEXT_PROMPT.md` with `python scripts/query_claude_next.py` after setting `OPENROUTER_API_KEY` in the current terminal.")
    else:
        next_actions.append("4. Add Claude questions only when a direction/framework issue is genuinely unclear.")

    lines.extend(
        [
            "",
            counts_block("Backfill Status", value_counts(ROOT / "results" / "v043_older_mature50_event_price_backfill.csv", "status")),
            "",
            counts_block("Quality Status", value_counts(ROOT / "results" / "v043_older_mature50_event_quality_report.csv", "quality_status")),
            "",
            counts_block("Publish Review Routes", value_counts(ROOT / "data" / "event_candidates_v06_publish_review_queue.csv", "channel_route")),
            "",
            counts_block("Other Review Reasons", value_counts(ROOT / "data" / "event_candidates_v06_other_review_classified.csv", "other_review_reason")),
            "",
            counts_block("TG Draft Status", value_counts(ROOT / "data" / "tg_drafts_v06_private_pilot.csv", "draft_status")),
            "",
            counts_block("Source Timezone Assumptions", value_counts(ROOT / "data" / "event_candidates_real_500_older_review.csv", "source_timezone_assumption")),
            "",
            "## Next Actions",
            "",
            *next_actions,
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    output = normalize_path(args.output)
    metrics_output = normalize_path(args.metrics_output)
    rows = metric_rows()
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(rows), encoding="utf-8")
    pd.DataFrame(rows).to_csv(metrics_output, index=False)
    print(f"wrote dashboard to {output}")
    print(f"wrote dashboard metrics to {metrics_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

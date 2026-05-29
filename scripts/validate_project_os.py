import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

HARD_BOUNDARY_PATTERNS = [
    ("notion_api_client", re.compile(r"\bnotion_client\b|api\.notion\.com", re.IGNORECASE)),
    ("exchange_order_api", re.compile(r"\bcreate_order\b|\bplace_order\b|/api/v3/order\b|/fapi/v1/order\b", re.IGNORECASE)),
    (
        "trade_signal_wording",
        re.compile(
            r"\b(buy|sell|long|short)\s+signal\b|"
            r"\u4e70\u5165\u4fe1\u53f7|"
            r"\u5356\u51fa\u4fe1\u53f7|"
            r"\u505a\u591a\u4fe1\u53f7|"
            r"\u505a\u7a7a\u4fe1\u53f7",
            re.IGNORECASE,
        ),
    ),
]

SCAN_SUFFIXES = {".py", ".ps1", ".md", ".toml", ".json", ".csv", ".txt"}
SCAN_SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
BOUNDARY_SCAN_ROOTS = {"scripts", "docs", "remote_x_monitor"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a consolidated Project OS validation report.")
    parser.add_argument("--dashboard-metrics", default=str(ROOT / "results" / "project_dashboard_metrics.csv"))
    parser.add_argument("--tg-gate", default=str(ROOT / "results" / "v06_tg_pilot_gate_report.csv"))
    parser.add_argument("--secret-summary", default=str(ROOT / "results" / "secret_leak_summary.csv"))
    parser.add_argument("--claude-decisions", default=str(ROOT / "data" / "claude_decision_review_queue.csv"))
    parser.add_argument("--decisions-doc", default=str(ROOT / "docs" / "DECISIONS.md"))
    parser.add_argument("--command-registry-summary", default=str(ROOT / "results" / "command_registry_summary.csv"))
    parser.add_argument("--review-action-summary", default=str(ROOT / "results" / "project_review_action_summary.csv"))
    parser.add_argument("--environment-summary", default=str(ROOT / "results" / "local_environment_summary.csv"))
    parser.add_argument("--artifact-manifest-summary", default=str(ROOT / "results" / "artifact_manifest_summary.csv"))
    parser.add_argument("--csv-output", default=str(ROOT / "results" / "project_os_validation_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "project_os_validation_summary.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "results" / "project_os_validation_report.md"))
    parser.add_argument("--max-age-hours", type=float, default=24.0)
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


def status_from_bool(ok: bool) -> str:
    return "pass" if ok else "fail"


def add_check(rows: list[dict], area: str, check: str, actual: object, expected: str, status: str, evidence: str) -> None:
    rows.append(
        {
            "area": area,
            "check": check,
            "actual": actual,
            "expected": expected,
            "status": status,
            "evidence": evidence,
        }
    )


def file_age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    return (datetime.now().timestamp() - path.stat().st_mtime) / 3600


def freshness_checks(rows: list[dict], paths: dict[str, Path], max_age_hours: float) -> None:
    for name, path in paths.items():
        age = file_age_hours(path)
        if age is None:
            add_check(rows, "freshness", f"{name}_present", "missing", "present", "fail", str(path))
            continue
        add_check(
            rows,
            "freshness",
            f"{name}_age_hours",
            round(age, 4),
            f"<= {max_age_hours}",
            status_from_bool(age <= max_age_hours),
            str(path),
        )

    dashboard = paths.get("dashboard_metrics")
    tg_gate = paths.get("tg_gate")
    if dashboard and tg_gate and dashboard.exists() and tg_gate.exists():
        dashboard_mtime = dashboard.stat().st_mtime
        gate_mtime = tg_gate.stat().st_mtime
        add_check(
            rows,
            "freshness",
            "dashboard_metrics_not_older_than_tg_gate",
            datetime.fromtimestamp(dashboard_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            f">= {datetime.fromtimestamp(gate_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
            status_from_bool(dashboard_mtime >= gate_mtime),
            f"{dashboard} vs {tg_gate}",
        )


def dashboard_checks(rows: list[dict], path: Path) -> None:
    df = read_csv(path)
    if df.empty:
        add_check(rows, "project_os", "dashboard_metrics_present", "missing", "present", "fail", str(path))
        return
    check_df = df.copy()
    if "metric" in check_df.columns:
        check_df = check_df[~check_df["metric"].astype(str).eq("project_os_validation_fail_count")]
    fail_count = int(check_df["status"].astype(str).str.lower().isin(["fail", "blocked"]).sum()) if "status" in check_df.columns else 999
    review_count = int(df["status"].astype(str).str.lower().eq("review").sum()) if "status" in df.columns else 999
    add_check(rows, "project_os", "blocking_dashboard_items", fail_count, "0", status_from_bool(fail_count == 0), str(path))
    add_check(rows, "project_os", "review_dashboard_items", review_count, "tracked, may be >0", "review" if review_count else "pass", str(path))


def tg_gate_checks(rows: list[dict], path: Path) -> None:
    df = read_csv(path)
    if df.empty:
        add_check(rows, "tg_gate", "tg_gate_report_present", "missing", "present", "fail", str(path))
        return
    fail_count = int(df["status"].astype(str).str.lower().ne("pass").sum())
    add_check(rows, "tg_gate", "all_tg_gate_rows_pass", fail_count, "0 non-pass rows", status_from_bool(fail_count == 0), str(path))
    for gate_name in ["auto_publish_count", "secret_leak_count", "review_failure_modes_doc", "rollback_workflow_doc"]:
        match = df[df["gate"].astype(str).eq(gate_name)] if "gate" in df.columns else pd.DataFrame()
        if match.empty:
            add_check(rows, "tg_gate", gate_name, "missing", "present and pass", "fail", str(path))
        else:
            row = match.iloc[0]
            add_check(rows, "tg_gate", gate_name, row.get("actual", ""), row.get("required", ""), str(row.get("status", "")), str(path))


def secret_checks(rows: list[dict], path: Path) -> None:
    summary = first_row(path)
    if not summary:
        add_check(rows, "security", "secret_scan_summary_present", "missing", "present", "fail", str(path))
        return
    leak_count = str(summary.get("leak_count", "missing"))
    add_check(rows, "security", "secret_leak_count", leak_count, "0", "pass" if leak_count == "0" else "fail", str(path))


def decision_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return set()
    return set(re.findall(r"^##\s+(D\d{3})\b", text, flags=re.MULTILINE))


def claude_decision_checks(rows: list[dict], path: Path, decisions_doc: Path) -> None:
    df = read_csv(path)
    if df.empty:
        add_check(rows, "claude", "decision_review_queue_present", "missing", "present", "review", str(path))
        return
    known_decision_ids = decision_ids(decisions_doc)
    pending = int(df["decision_status"].astype(str).eq("pending").sum()) if "decision_status" in df.columns else len(df)
    accepted_without_decision_id = 0
    accepted_with_unknown_decision_id = 0
    done_without_accepted_decision = 0
    if {"decision_status", "decision_id"}.issubset(df.columns):
        statuses = df["decision_status"].astype(str)
        decision_id_series = df["decision_id"].astype(str).str.strip()
        accepted = statuses.eq("accepted")
        accepted_without_decision_id = int((accepted & decision_id_series.eq("")).sum())
        accepted_with_unknown_decision_id = int(
            (accepted & decision_id_series.ne("") & ~decision_id_series.isin(known_decision_ids)).sum()
        )
        if "implementation_status" in df.columns:
            done = df["implementation_status"].astype(str).eq("done")
            done_without_accepted_decision = int((done & ~accepted).sum())
    add_check(rows, "claude", "pending_decision_items", pending, "review before implementation", "review" if pending else "pass", str(path))
    add_check(
        rows,
        "claude",
        "accepted_items_have_decision_id",
        accepted_without_decision_id,
        "0",
        status_from_bool(accepted_without_decision_id == 0),
        str(path),
    )
    add_check(
        rows,
        "claude",
        "accepted_items_reference_existing_decision",
        accepted_with_unknown_decision_id,
        "0",
        status_from_bool(accepted_with_unknown_decision_id == 0),
        f"{path} vs {decisions_doc}",
    )
    add_check(
        rows,
        "claude",
        "done_items_are_accepted_decisions",
        done_without_accepted_decision,
        "0",
        status_from_bool(done_without_accepted_decision == 0),
        str(path),
    )


def command_registry_checks(rows: list[dict], path: Path) -> None:
    summary = first_row(path)
    if not summary:
        add_check(rows, "project_os", "command_registry_summary_present", "missing", "present", "fail", str(path))
        return
    missing_scripts = str(summary.get("missing_script_count", "missing"))
    add_check(
        rows,
        "project_os",
        "command_registry_missing_scripts",
        missing_scripts,
        "0",
        "pass" if missing_scripts == "0" else "fail",
        str(path),
    )


def environment_checks(rows: list[dict], path: Path) -> None:
    summary = first_row(path)
    if not summary:
        add_check(rows, "environment", "local_environment_summary_present", "missing", "present", "fail", str(path))
        return
    fail_count = str(summary.get("fail_count", "missing"))
    add_check(
        rows,
        "environment",
        "local_environment_fail_count",
        fail_count,
        "0",
        "pass" if fail_count == "0" else "fail",
        str(path),
    )


def review_action_checks(rows: list[dict], path: Path) -> None:
    summary = first_row(path)
    if not summary:
        add_check(rows, "project_os", "review_action_summary_present", "missing", "present", "fail", str(path))
        return
    unknown_rules = str(summary.get("unknown_rule_count", "missing"))
    add_check(
        rows,
        "project_os",
        "review_action_unknown_rules",
        unknown_rules,
        "0",
        "pass" if unknown_rules == "0" else "review",
        str(path),
    )


def artifact_manifest_checks(rows: list[dict], path: Path) -> None:
    summary = first_row(path)
    if not summary:
        add_check(rows, "project_os", "artifact_manifest_summary_present", "missing", "present", "fail", str(path))
        return
    missing_required = str(summary.get("missing_required_count", "missing"))
    stale_required = str(summary.get("stale_required_count", "missing"))
    add_check(
        rows,
        "project_os",
        "artifact_missing_required_count",
        missing_required,
        "0",
        "pass" if missing_required == "0" else "fail",
        str(path),
    )
    add_check(
        rows,
        "project_os",
        "artifact_stale_required_count",
        stale_required,
        "0",
        "pass" if stale_required == "0" else "fail",
        str(path),
    )


def should_scan(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.name == "validate_project_os.py":
        return False
    if rel.parts[0] not in BOUNDARY_SCAN_ROOTS and rel.name != "AGENTS.md":
        return False
    if path.suffix.lower() not in SCAN_SUFFIXES:
        return False
    parts = set(rel.parts)
    if parts & SCAN_SKIP_DIRS:
        return False
    return True


def boundary_static_checks(rows: list[dict]) -> None:
    findings: list[dict] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "do not" in line.lower() or "\u4e0d\u8981" in line or "\u4e0d\u63a5" in line:
                continue
            for name, pattern in HARD_BOUNDARY_PATTERNS:
                if pattern.search(line):
                    findings.append({"file": str(path.relative_to(ROOT)), "line": line_no, "boundary": name})
    add_check(
        rows,
        "boundaries",
        "static_boundary_scan_findings",
        len(findings),
        "0",
        status_from_bool(len(findings) == 0),
        "scripts/docs/data text scan",
    )


def render_markdown(rows: list[dict]) -> str:
    df = pd.DataFrame(rows)
    fail_count = int(df["status"].astype(str).str.lower().isin(["fail", "blocked"]).sum()) if not df.empty else 1
    review_count = int(df["status"].astype(str).str.lower().eq("review").sum()) if not df.empty else 0
    overall = "pass" if fail_count == 0 else "fail"
    lines = [
        "# Project OS Validation Report",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        f"overall_status: {overall}",
        f"blocking_or_fail_count: {fail_count}",
        f"review_count: {review_count}",
        "",
        "| area | check | actual | expected | status | evidence |",
        "|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['area']} | {row['check']} | {row['actual']} | {row['expected']} | {row['status']} | `{row['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- `fail` or `blocked` means do not proceed.",
            "- `review` means the issue is known and should not be silently treated as done.",
            "- This report does not approve TG auto-send or trading-related behavior.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    dashboard_metrics = normalize_path(args.dashboard_metrics)
    tg_gate = normalize_path(args.tg_gate)
    secret_summary = normalize_path(args.secret_summary)
    claude_decisions = normalize_path(args.claude_decisions)
    decisions_doc = normalize_path(args.decisions_doc)
    command_registry_summary = normalize_path(args.command_registry_summary)
    review_action_summary = normalize_path(args.review_action_summary)
    environment_summary = normalize_path(args.environment_summary)
    artifact_manifest_summary = normalize_path(args.artifact_manifest_summary)
    rows: list[dict] = []
    freshness_checks(
        rows,
        {
            "dashboard_metrics": dashboard_metrics,
            "tg_gate": tg_gate,
            "secret_summary": secret_summary,
            "claude_decisions": claude_decisions,
            "decisions_doc": decisions_doc,
            "command_registry_summary": command_registry_summary,
            "review_action_summary": review_action_summary,
            "environment_summary": environment_summary,
            "artifact_manifest_summary": artifact_manifest_summary,
        },
        args.max_age_hours,
    )
    dashboard_checks(rows, dashboard_metrics)
    tg_gate_checks(rows, tg_gate)
    secret_checks(rows, secret_summary)
    claude_decision_checks(rows, claude_decisions, decisions_doc)
    command_registry_checks(rows, command_registry_summary)
    environment_checks(rows, environment_summary)
    review_action_checks(rows, review_action_summary)
    artifact_manifest_checks(rows, artifact_manifest_summary)
    boundary_static_checks(rows)

    csv_output = normalize_path(args.csv_output)
    summary_output = normalize_path(args.summary)
    md_output = normalize_path(args.md_output)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(csv_output, index=False)
    review_count = sum(1 for row in rows if str(row["status"]).lower() == "review")
    fail_count = sum(1 for row in rows if str(row["status"]).lower() in {"fail", "blocked"})
    pd.DataFrame(
        [
            {
                "overall_status": "pass" if fail_count == 0 else "fail",
                "blocking_or_fail_count": fail_count,
                "review_count": review_count,
                "total_checks": len(rows),
            }
        ]
    ).to_csv(summary_output, index=False)
    md_output.write_text(render_markdown(rows), encoding="utf-8")
    print(f"wrote project OS validation report to {csv_output}")
    print(f"wrote project OS validation summary to {summary_output}")
    print(f"wrote project OS validation markdown to {md_output}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

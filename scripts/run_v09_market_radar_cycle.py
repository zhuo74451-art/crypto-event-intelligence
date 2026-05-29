import argparse
import csv
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def prefer_existing(*relative_paths: str) -> str:
    for relative_path in relative_paths:
        if (ROOT / relative_path).exists():
            return relative_path
    return relative_paths[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v0.9 market-radar cycle: watchers -> routed items -> compact board.")
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--limit-alerts", type=int, default=100)
    parser.add_argument("--sample-if-no-key", default="false")
    parser.add_argument("--output-board", default=str(ROOT / "data" / "tg_market_radar_boards.csv"))
    parser.add_argument("--board-preview", default=str(ROOT / "results" / "v09_tg_market_radar_board.md"))
    parser.add_argument("--board-summary", default=str(ROOT / "results" / "v09_tg_market_radar_board_summary.csv"))
    parser.add_argument("--routed-output", default=str(ROOT / "data" / "tg_drafts_v09_routed.csv"))
    parser.add_argument("--routing-summary", default=str(ROOT / "results" / "v09_tg_delivery_routing_summary.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v09_market_radar_cycle_summary.csv"))
    parser.add_argument("--send-board", action="store_true", help="Send the generated market-radar board to Telegram.")
    parser.add_argument("--force-send-board", action="store_true", help="Allow sending even if a board was already sent this hour.")
    parser.add_argument("--token-env", default="TELEGRAM_BOT_TOKEN")
    parser.add_argument("--chat-id-env", default="TELEGRAM_CHAT_ID")
    parser.add_argument("--load-local-secrets", default="true")
    parser.add_argument("--evaluate-alert-outcomes", default="true")
    parser.add_argument("--refresh-v11-quality-reports", default="true")
    parser.add_argument("--send-quality-summary", action="store_true", help="Send a deduplicated TG quality summary card when new horizons mature.")
    parser.add_argument("--quality-summary-min-computed", type=int, default=1)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def china_now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def read_first_row(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[0] if rows else {}


def write_summary(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerow(row)


def run_step(name: str, cmd: list[str]) -> tuple[bool, str]:
    result = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
    tail = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()[-1200:]
    if result.returncode != 0:
        print(f"{name} failed: exit={result.returncode}")
        if tail:
            print(tail)
        return False, tail
    print(f"{name} ok")
    return True, tail


def main() -> int:
    args = parse_args()
    py = sys.executable
    steps = [
        (
            "run first-hand watchers",
            [
                py,
                "scripts/run_v07_first_hand_watchers.py",
                "--hours",
                str(args.hours),
                "--limit-alerts",
                str(args.limit_alerts),
                "--sample-if-no-key",
                str(args.sample_if_no_key),
            ],
        ),
        (
            "route TG items",
            [
                py,
                "scripts/route_tg_items_by_severity.py",
                "--input",
                "data/tg_drafts_v07_watcher_private_pilot.csv",
                "--output",
                str(normalize_path(args.routed_output)),
                "--summary",
                str(normalize_path(args.routing_summary)),
            ],
        ),
        (
            "refresh Binance long-short board context",
            [
                py,
                "scripts/watch_binance_long_short_ratios.py",
                "--output",
                "data/binance_long_short_snapshot.csv",
                "--summary",
                "results/v08_binance_long_short_summary.csv",
                "--period",
                "1h",
                "--limit",
                "2",
            ],
        ),
        (
            "build v11 signal policy",
            [
                py,
                "scripts/build_v11_signal_policy.py",
                "--event-matrix",
                "results/event_type_performance_matrix.csv",
                "--source-effectiveness",
                "results/source_effectiveness_report.csv",
                "--non-benchmark-event-matrix",
                "results/event_type_performance_matrix_non_benchmark_alt.csv",
                "--false-positive",
                "results/false_positive_analysis.csv",
                "--output",
                "data/tg_signal_policy_v11.csv",
                "--summary",
                "results/v11_signal_policy_summary.csv",
                "--report",
                "results/v11_signal_policy_report.md",
            ],
        ),
        (
            "build market radar board",
            [
                py,
                "scripts/build_tg_market_radar_board.py",
                "--output",
                str(normalize_path(args.output_board)),
                "--markdown-output",
                str(normalize_path(args.board_preview)),
                "--summary",
                str(normalize_path(args.board_summary)),
            ],
        ),
    ]
    if args.send_board:
        send_cmd = [
            py,
            "scripts/send_tg_market_radar_board.py",
            "--input",
            str(normalize_path(args.output_board)),
            "--summary",
            "results/v09_tg_market_radar_send_summary.csv",
            "--token-env",
            args.token_env,
            "--chat-id-env",
            args.chat_id_env,
            "--load-local-secrets",
            args.load_local_secrets,
            "--send",
        ]
        if args.force_send_board:
            send_cmd.append("--force")
        steps.append(("send market radar board", send_cmd))
    if str(args.evaluate_alert_outcomes or "").strip().lower() in {"1", "true", "yes", "y"}:
        steps.extend(
            [
                (
                    "evaluate TG alert outcomes",
                    [
                        py,
                        "scripts/evaluate_tg_alert_outcomes.py",
                        "--ledger",
                        "data/tg_alert_ledger.csv",
                        "--output",
                        "data/tg_alert_outcomes.csv",
                        "--summary",
                        "results/tg_alert_outcome_eval_summary.csv",
                    ],
                ),
                (
                    "build TG alert quality report",
                    [
                        py,
                        "scripts/build_tg_alert_quality_report.py",
                        "--input",
                        "data/tg_alert_outcomes.csv",
                        "--ledger",
                        "data/tg_alert_ledger.csv",
                        "--hypothesis-registry",
                        "data/event_hypothesis_registry.csv",
                        "--output",
                        "results/tg_alert_quality_daily.md",
                        "--summary",
                        "results/tg_alert_quality_daily_summary.csv",
                    ],
                ),
                (
                    "build live TG signal policy",
                    [
                        py,
                        "scripts/build_live_signal_policy_from_outcomes.py",
                        "--outcomes",
                        "data/tg_alert_outcomes.csv",
                        "--output",
                        "data/tg_signal_policy_live.csv",
                        "--summary",
                        "results/tg_signal_policy_live_summary.csv",
                    ],
                ),
                (
                    "build radar decision report",
                    [
                        py,
                        "scripts/build_tg_radar_decision_report.py",
                        "--decision-log",
                        "data/tg_radar_decision_log.csv",
                        "--output",
                        "results/tg_radar_decision_report.md",
                        "--summary",
                        "results/tg_radar_decision_report_summary.csv",
                        "--lookback-hours",
                        str(args.hours),
                    ],
                ),
            ]
        )
        if args.send_quality_summary:
            steps.append(
                (
                    "send TG alert quality summary",
                    [
                        py,
                        "scripts/send_tg_quality_summary_card.py",
                        "--summary",
                        "results/tg_alert_quality_daily_summary.csv",
                        "--report",
                        "results/tg_alert_quality_daily.md",
                        "--state",
                        "data/tg_quality_summary_send_state.csv",
                        "--token-env",
                        args.token_env,
                        "--chat-id-env",
                        args.chat_id_env,
                        "--load-local-secrets",
                        args.load_local_secrets,
                        "--min-computed",
                        str(args.quality_summary_min_computed),
                        "--send",
                    ],
                )
            )
    if str(args.refresh_v11_quality_reports or "").strip().lower() in {"1", "true", "yes", "y"}:
        steps.extend(
            [
                (
                    "build source registry report",
                    [
                        py,
                        "scripts/build_source_registry_report.py",
                        "--registry",
                        "data/source_registry.csv",
                        "--summary",
                        "results/source_registry_report.csv",
                        "--output",
                        "results/source_registry_report.md",
                    ],
                ),
                (
                    "build source effectiveness report",
                    [
                        py,
                        "scripts/build_source_effectiveness_report.py",
                        "--registry",
                        "data/source_registry.csv",
                        "--output",
                        "results/source_effectiveness_report.csv",
                        "--markdown-output",
                        "results/source_effectiveness_report.md",
                        "--summary",
                        "results/source_effectiveness_summary.csv",
                    ],
                ),
                (
                    "build event type performance matrix",
                    [
                        py,
                        "scripts/build_event_type_performance_matrix.py",
                        "--outcomes",
                        "data/tg_alert_outcomes.csv",
                        "--historical-backfill",
                        "results/v08_historical_replay_broad_200_price_backfill.csv",
                        "--historical-quality",
                        "results/v08_historical_replay_broad_200_quality_report.csv",
                        "--output",
                        "results/event_type_performance_matrix.csv",
                        "--summary",
                        "results/event_type_performance_matrix_summary.csv",
                        "--markdown-output",
                        "results/event_type_performance_matrix.md",
                    ],
                ),
                (
                    "build non-benchmark event type performance matrix",
                    [
                        py,
                        "scripts/build_event_type_performance_matrix.py",
                        "--outcomes",
                        "data/tg_alert_outcomes.csv",
                        "--historical-backfill",
                        prefer_existing(
                            "results/v08_historical_replay_non_benchmark_alt_200_price_backfill.csv",
                            "results/v08_historical_replay_non_benchmark_alt_50_price_backfill.csv",
                        ),
                        "--historical-quality",
                        prefer_existing(
                            "results/v08_historical_replay_non_benchmark_alt_200_quality_report.csv",
                            "results/v08_historical_replay_non_benchmark_alt_50_quality_report.csv",
                        ),
                        "--output",
                        "results/event_type_performance_matrix_non_benchmark_alt.csv",
                        "--summary",
                        "results/event_type_performance_matrix_non_benchmark_alt_summary.csv",
                        "--markdown-output",
                        "results/event_type_performance_matrix_non_benchmark_alt.md",
                    ],
                ),
                (
                    "build signal decay curve",
                    [
                        py,
                        "scripts/build_signal_decay_curve.py",
                        "--outcomes",
                        "data/tg_alert_outcomes.csv",
                        "--historical-backfill",
                        "results/v08_historical_replay_broad_200_price_backfill.csv",
                        "--historical-quality",
                        "results/v08_historical_replay_broad_200_quality_report.csv",
                        "--output",
                        "results/signal_decay_curve.csv",
                        "--summary",
                        "results/signal_decay_curve_summary.csv",
                        "--markdown-output",
                        "results/signal_decay_curve.md",
                    ],
                ),
                (
                    "build false positive analysis",
                    [
                        py,
                        "scripts/build_false_positive_analysis.py",
                        "--outcomes",
                        "data/tg_alert_outcomes.csv",
                        "--decision-log",
                        "data/tg_radar_decision_log.csv",
                        "--output",
                        "results/false_positive_analysis.csv",
                        "--summary",
                        "results/false_positive_analysis_summary.csv",
                        "--markdown-output",
                        "results/false_positive_analysis.md",
                    ],
                ),
                (
                    "validate whale position contamination",
                    [
                        py,
                        "scripts/validate_whale_position_contamination.py",
                        "--backfill",
                        prefer_existing(
                            "results/v08_historical_replay_non_benchmark_alt_200_price_backfill.csv",
                            "results/v08_historical_replay_non_benchmark_alt_50_price_backfill.csv",
                        ),
                        "--output",
                        "results/v12_whale_position_contamination_report.csv",
                        "--summary",
                        "results/v12_whale_position_contamination_summary.csv",
                        "--markdown-output",
                        "results/v12_whale_position_contamination_report.md",
                    ],
                ),
                (
                    "validate hack classification",
                    [
                        py,
                        "scripts/validate_hack_classification.py",
                        "--candidates",
                        prefer_existing(
                            "data/event_candidates_real_2000_older_review.csv",
                            "data/event_candidates_real_500_older_review.csv",
                        ),
                        "--backfill",
                        prefer_existing(
                            "results/v08_historical_replay_non_benchmark_alt_200_price_backfill.csv",
                            "results/v08_historical_replay_non_benchmark_alt_50_price_backfill.csv",
                        ),
                        "--output",
                        "results/v12_hack_classification_report.csv",
                        "--summary",
                        "results/v12_hack_classification_summary.csv",
                    ],
                ),
                (
                    "refresh v11 signal policy",
                    [
                        py,
                        "scripts/build_v11_signal_policy.py",
                        "--event-matrix",
                        "results/event_type_performance_matrix.csv",
                        "--source-effectiveness",
                        "results/source_effectiveness_report.csv",
                        "--non-benchmark-event-matrix",
                        "results/event_type_performance_matrix_non_benchmark_alt.csv",
                        "--false-positive",
                        "results/false_positive_analysis.csv",
                        "--output",
                        "data/tg_signal_policy_v11.csv",
                        "--summary",
                        "results/v11_signal_policy_summary.csv",
                        "--report",
                        "results/v11_signal_policy_report.md",
                    ],
                ),
                (
                    "refresh v12 strict signal policy",
                    [
                        py,
                        "scripts/apply_boost_criteria_v12.py",
                        "--matrix",
                        "results/event_type_performance_matrix_non_benchmark_alt.csv",
                        "--backfill",
                        prefer_existing(
                            "results/v08_historical_replay_non_benchmark_alt_200_price_backfill.csv",
                            "results/v08_historical_replay_non_benchmark_alt_50_price_backfill.csv",
                        ),
                        "--contamination-summary",
                        "results/v12_whale_position_contamination_summary.csv",
                        "--hack-summary",
                        "results/v12_hack_classification_summary.csv",
                        "--output",
                        "data/tg_signal_policy_v12.csv",
                        "--report",
                        "results/v12_boost_criteria_report.csv",
                        "--summary",
                        "results/v12_boost_criteria_summary.csv",
                    ],
                ),
                (
                    "validate source adapter outputs",
                    [
                        py,
                        "scripts/validate_source_adapter_outputs.py",
                        "--input",
                        "data/watcher_events_raw.csv",
                        "--registry",
                        "data/source_registry.csv",
                        "--output",
                        "results/source_adapter_validation_report.csv",
                        "--summary",
                        "results/source_adapter_validation_summary.csv",
                        "--markdown-output",
                        "results/source_adapter_validation_report.md",
                    ],
                ),
                (
                    "run shadow source evaluation",
                    [
                        py,
                        "scripts/run_shadow_source_evaluation.py",
                        "--registry",
                        "data/source_registry.csv",
                        "--watcher-events",
                        "data/watcher_events_raw.csv",
                        "--shadow-output",
                        "data/shadow_events_raw.csv",
                        "--summary",
                        "results/shadow_source_evaluation_summary.csv",
                        "--report",
                        "results/shadow_source_evaluation_report.md",
                    ],
                ),
                (
                    "render TG evidence snippets",
                    [
                        py,
                        "scripts/render_tg_evidence_snippet.py",
                        "--alerts",
                        "data/tg_alert_ledger.csv",
                        "--event-matrix",
                        "results/event_type_performance_matrix.csv",
                        "--source-effectiveness",
                        "results/source_effectiveness_report.csv",
                        "--output",
                        "data/tg_evidence_snippets.csv",
                        "--markdown-output",
                        "results/tg_evidence_snippets.md",
                    ],
                ),
                (
                    "build LLM usage report",
                    [
                        py,
                        "scripts/build_llm_usage_report.py",
                        "--input",
                        "data/llm_usage_ledger.csv",
                        "--output",
                        "results/llm_usage_report.csv",
                        "--summary",
                        "results/llm_usage_summary.csv",
                        "--markdown-output",
                        "results/llm_usage_report.md",
                    ],
                ),
                (
                    "build v11 readiness report",
                    [
                        py,
                        "scripts/build_v11_readiness_report.py",
                        "--output",
                        "results/v11_readiness_report.md",
                        "--summary",
                        "results/v11_readiness_summary.csv",
                    ],
                ),
            ]
        )

    status = "pass"
    failed_step = ""
    last_log = ""
    for name, cmd in steps:
        ok, tail = run_step(name, cmd)
        last_log = tail
        if not ok:
            status = "fail"
            failed_step = name
            break

    board_summary = read_first_row(normalize_path(args.board_summary))
    routing_summary = read_first_row(normalize_path(args.routing_summary))
    send_summary = read_first_row(ROOT / "results" / "v09_tg_market_radar_send_summary.csv")
    outcome_summary = read_first_row(ROOT / "results" / "tg_alert_outcome_eval_summary.csv")
    quality_summary = read_first_row(ROOT / "results" / "tg_alert_quality_daily_summary.csv")
    decision_summary = read_first_row(ROOT / "results" / "tg_radar_decision_report_summary.csv")
    v11_summary = read_first_row(ROOT / "results" / "v11_readiness_summary.csv")
    summary = {
        "status": status,
        "updated_at_china": china_now(),
        "failed_step": failed_step,
        "board_section_count": board_summary.get("section_count", ""),
        "board_item_count": board_summary.get("item_count", ""),
        "board_hyperliquid_rows": board_summary.get("hyperliquid_rows", ""),
        "board_token_unlock_rows": board_summary.get("token_unlock_rows", ""),
        "board_long_short_rows": board_summary.get("long_short_rows", ""),
        "board_flow_rows": board_summary.get("flow_rows", ""),
        "board_price_context_rows": board_summary.get("price_context_rows", ""),
        "board_repeat_suppressed_rows": board_summary.get("repeat_suppressed_rows", ""),
        "board_readability_status": board_summary.get("readability_status", ""),
        "interrupt_count": routing_summary.get("interrupt_count", ""),
        "board_count": routing_summary.get("board_count", ""),
        "archive_count": routing_summary.get("archive_count", ""),
        "discard_count": routing_summary.get("discard_count", ""),
        "send_board_requested": str(args.send_board).lower(),
        "send_board_status": send_summary.get("status", "") if args.send_board else "",
        "alert_outcome_rows": outcome_summary.get("outcome_rows", ""),
        "alert_outcome_evaluable": outcome_summary.get("evaluable_alerts", ""),
        "alert_quality_partial_rows": quality_summary.get("partial_rows", ""),
        "alert_quality_ok_rows": quality_summary.get("ok_rows", ""),
        "alert_quality_computed_24h": quality_summary.get("computed_24h", ""),
        "radar_decision_rows": decision_summary.get("decision_rows", ""),
        "radar_decision_selected": decision_summary.get("selected_count", ""),
        "radar_decision_filtered_digest_only": decision_summary.get("filtered_digest_only_count", ""),
        "radar_decision_suppressed_cooldown": decision_summary.get("suppressed_cooldown_count", ""),
        "radar_decision_not_selected_capacity": decision_summary.get("not_selected_capacity_count", ""),
        "v11_readiness_status": v11_summary.get("overall_status", ""),
        "v11_shadow_or_no_live_data_count": v11_summary.get("shadow_or_no_live_data_count", ""),
        "v11_insufficient_live_outcomes_count": v11_summary.get("insufficient_live_outcomes_count", ""),
        "v11_false_positive_group_rows": v11_summary.get("false_positive_group_rows", ""),
        "board_output": str(normalize_path(args.output_board)),
        "board_preview": str(normalize_path(args.board_preview)),
        "routed_output": str(normalize_path(args.routed_output)),
        "last_log_tail": last_log,
    }
    write_summary(normalize_path(args.summary), summary)
    print(f"wrote cycle summary to {normalize_path(args.summary)}")
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

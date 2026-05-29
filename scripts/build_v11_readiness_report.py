import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build v11 readiness report for source-quality-first upgrade.")
    parser.add_argument("--output", default=str(ROOT / "results" / "v11_readiness_report.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v11_readiness_summary.csv"))
    return parser.parse_args()


def path_value(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def first_row(path: str) -> dict:
    rows = read_rows(path_value(path))
    return rows[0] if rows else {}


def count_rows(path: str) -> int:
    return len(read_rows(path_value(path)))


def status_from_count(fail_count: int, warning_count: int = 0) -> str:
    if fail_count > 0:
        return "fail"
    if warning_count > 0:
        return "warning"
    return "pass"


def number(row: dict, key: str) -> float:
    try:
        return float(str(row.get(key, "") or "0"))
    except Exception:
        return 0.0


def summarize() -> tuple[dict, list[str]]:
    source_registry = first_row("results/source_registry_report.csv")
    adapter = first_row("results/source_adapter_validation_summary.csv")
    source_effect = first_row("results/source_effectiveness_summary.csv")
    event_matrix = first_row("results/event_type_performance_matrix_summary.csv")
    non_benchmark_matrix = first_row("results/event_type_performance_matrix_non_benchmark_alt_summary.csv")
    decay = first_row("results/signal_decay_curve_summary.csv")
    false_positive = first_row("results/false_positive_analysis_summary.csv")
    v11_policy = first_row("results/v11_signal_policy_summary.csv")
    shadow = first_row("results/shadow_source_evaluation_summary.csv")
    evidence_count = count_rows("data/tg_evidence_snippets.csv")
    llm = first_row("results/llm_usage_summary.csv")
    digest = first_row("results/v11_tg_custom_digest_preview_summary.csv")

    registry_status = str(source_registry.get("status", "") or "unknown")
    adapter_status = str(adapter.get("status", "") or "unknown")
    matrix_rows = int(number(event_matrix, "matrix_rows"))
    non_benchmark_matrix_rows = int(number(non_benchmark_matrix, "matrix_rows"))
    curve_rows = int(number(decay, "curve_rows"))
    false_positive_groups = int(number(false_positive, "group_rows"))
    v11_policy_rows = int(number(v11_policy, "policy_rows"))
    shadow_rows = int(number(shadow, "shadow_event_rows"))
    insufficient_sources = int(number(source_effect, "insufficient_live_outcomes_count"))
    no_live_sources = int(number(source_effect, "shadow_or_no_live_data_count"))
    llm_cost = float(number(llm, "estimated_cost_usd"))

    fail_count = 0
    warning_count = 0
    if registry_status == "fail":
        fail_count += 1
    elif registry_status != "pass":
        warning_count += 1
    if adapter_status == "fail":
        fail_count += 1
    elif adapter_status != "pass":
        warning_count += 1
    if matrix_rows <= 0:
        fail_count += 1
    if non_benchmark_matrix_rows <= 0:
        warning_count += 1
    if curve_rows <= 0:
        fail_count += 1
    if false_positive_groups <= 0:
        warning_count += 1
    if v11_policy_rows <= 0:
        warning_count += 1
    if evidence_count <= 0:
        warning_count += 1
    if no_live_sources > 0 or insufficient_sources > 0:
        warning_count += 1
    if shadow_rows > 0:
        warning_count += 1

    summary = {
        "generated_at_china": datetime.now(CN_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
        "overall_status": status_from_count(fail_count, warning_count),
        "fail_count": fail_count,
        "warning_count": warning_count,
        "source_registry_status": registry_status,
        "adapter_validation_status": adapter_status,
        "source_rows": source_effect.get("source_rows", ""),
        "shadow_or_no_live_data_count": no_live_sources,
        "insufficient_live_outcomes_count": insufficient_sources,
        "event_matrix_rows": matrix_rows,
        "non_benchmark_matrix_rows": non_benchmark_matrix_rows,
        "signal_decay_rows": curve_rows,
        "false_positive_group_rows": false_positive_groups,
        "v11_signal_policy_rows": v11_policy_rows,
        "shadow_event_rows": shadow_rows,
        "evidence_snippet_rows": evidence_count,
        "digest_preview_status": digest.get("status", ""),
        "llm_call_count": llm.get("call_count", ""),
        "llm_estimated_cost_usd": f"{llm_cost:.6f}",
    }

    lines = [
        "# v11 数据质量优先升级验收报告",
        "",
        f"- 生成时间：{summary['generated_at_china']}",
        f"- 总状态：{summary['overall_status']}",
        "",
        "## 已完成的 Claude P0 要求",
        "",
        f"- Source Registry：{registry_status}，注册源 {source_registry.get('registry_rows', '-')} 个，live {source_registry.get('live_count', '-')} 个，shadow {source_registry.get('shadow_count', '-')} 个。",
        f"- Source Adapter 校验：{adapter_status}，校验行数 {adapter.get('row_count', '-')}，失败 {adapter.get('fail_count', '-')}。",
        f"- Source Effectiveness：已评估 {source_effect.get('source_rows', '-')} 类来源；无 live 证据 {no_live_sources}，live 样本不足 {insufficient_sources}。",
        f"- Event Type Performance Matrix：{matrix_rows} 个组合，样本不足组合 {event_matrix.get('insufficient_sample_count', '-')}。",
        f"- Non-Benchmark Alt Matrix：{non_benchmark_matrix_rows} 个组合，用于减少 BTC/macro benchmark 污染。",
        f"- Signal Decay Curve：{curve_rows} 个组合，样本不足组合 {decay.get('insufficient_sample_count', '-')}。",
        f"- False Positive Analysis：{false_positive_groups} 个组合，待降噪/补样本分组 {false_positive.get('collect_more_count', '-')}。",
        f"- v11 Signal Policy：{v11_policy_rows} 条路由策略，已把历史样本、false-positive 和冷却倍率转为机器可读策略。",
        f"- Shadow Mode：当前 shadow 事件 {shadow_rows} 条，未证明来源继续进入影子管道。",
        f"- Evidence Snippets：{evidence_count} 条，已可用于替换黑箱分数和空泛解读。",
        f"- LLM 用量追踪：调用 {llm.get('call_count', '0')} 次，估算成本 ${summary['llm_estimated_cost_usd']}。",
        "",
        "## 当前不能夸大的地方",
        "",
        "- 多数来源仍然缺少足够 live outcome，不能基于当前样本断言“有效”。",
        "- 历史样本仍受 BTC/macro 污染影响，event_type 层面的表现需要继续拆分和补样本。",
        "- TG 摘要已改为证据驱动，但证据本身还是早期样本，必须显示样本不足提醒。",
        "",
        "## 下一步执行顺序",
        "",
        "1. 将证据片段进一步接入盘中雷达卡片的逐条证据层，减少黑箱文案。",
        "2. 对 shadow 来源继续累积历史 outcome，满足样本门槛后再转 live。",
        "3. 扩大历史回测样本，优先补非 BTC/macro 的单资产事件，降低 benchmark 污染。",
        "4. 用 false_positive_analysis 的结果反向更新路由阈值和冷却窗口。",
    ]

    return summary, lines


def main() -> int:
    args = parse_args()
    summary, lines = summarize()
    write_rows(path_value(args.summary), [summary], list(summary.keys()))
    write_text(path_value(args.output), "\n".join(lines) + "\n")
    print(f"status={summary['overall_status']}")
    print(f"wrote_output={path_value(args.output)}")
    print(f"wrote_summary={path_value(args.summary)}")
    return 0 if summary["overall_status"] in {"pass", "warning"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

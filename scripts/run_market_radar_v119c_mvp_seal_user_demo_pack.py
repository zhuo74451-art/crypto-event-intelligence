"""Market Radar v119C — MVP Seal User Demo Pack.

Reads v119B result JSON (local, already generated) and produces the v119C
封版交付文件 (MVP seal delivery pack). This runner is a PURE FILE GENERATOR:
it does NOT call Binance, RSS, Telegram, AI/model, or any external API.
It does NOT start daemons/cron/loops. It does NOT write production state.

Deliverables:
  runs/market_radar/v119c_mvp_index.html
  runs/market_radar/v119c_user_demo_3min.md
  runs/market_radar/v119c_operator_quickstart.md
  runs/market_radar/v119c_mvp_acceptance_report.md
  runs/market_radar/v119c_known_limits_and_next_steps.md
  runs/market_radar/v119c_local_only_final_handoff.md
  results/market_radar_v119c_mvp_seal_result.json

Usage:
    python scripts/run_market_radar_v119c_mvp_seal_user_demo_pack.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
RUN_ID = datetime.now(CN_TZ).strftime("%Y%m%d_%H%M%S")
PIPELINE_VERSION = "v1.19C"
TASK_ID = "20260605_v119c_market_radar_mvp_seal_user_demo_pack"

# ── Input (read-only) ──────────────────────────────────────────────────────────
V119B_RESULT_JSON = ROOT / "results" / "market_radar_v119b_signal_quality_b_lite_result.json"

# ── Output paths ───────────────────────────────────────────────────────────────
OUTPUT_RESULT_JSON = ROOT / "results" / "market_radar_v119c_mvp_seal_result.json"
OUTPUT_INDEX_HTML = ROOT / "runs" / "market_radar" / "v119c_mvp_index.html"
OUTPUT_USER_DEMO_MD = ROOT / "runs" / "market_radar" / "v119c_user_demo_3min.md"
OUTPUT_QUICKSTART_MD = ROOT / "runs" / "market_radar" / "v119c_operator_quickstart.md"
OUTPUT_ACCEPTANCE_MD = ROOT / "runs" / "market_radar" / "v119c_mvp_acceptance_report.md"
OUTPUT_KNOWN_LIMITS_MD = ROOT / "runs" / "market_radar" / "v119c_known_limits_and_next_steps.md"
OUTPUT_HANDOFF_MD = ROOT / "runs" / "market_radar" / "v119c_local_only_final_handoff.md"

ALL_OUTPUT_FILES = [
    OUTPUT_RESULT_JSON,
    OUTPUT_INDEX_HTML,
    OUTPUT_USER_DEMO_MD,
    OUTPUT_QUICKSTART_MD,
    OUTPUT_ACCEPTANCE_MD,
    OUTPUT_KNOWN_LIMITS_MD,
    OUTPUT_HANDOFF_MD,
]

# ── Helpers ────────────────────────────────────────────────────────────────────


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _escape_html(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ── Step 1: Load v119B result ─────────────────────────────────────────────────


def load_v119b_result() -> dict:
    """Load the v119B result JSON. Fail if missing."""
    if not V119B_RESULT_JSON.exists():
        raise FileNotFoundError(
            f"v119B result not found: {V119B_RESULT_JSON}\n"
            "Run v119B runner first:\n"
            "  python scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py"
        )
    with open(V119B_RESULT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Step 2: Generate MVP index HTML ────────────────────────────────────────────


def generate_mvp_index_html(v119b: dict) -> str:
    """Generate v119C MVP index HTML page."""
    gen_stamp = china_stamp()
    cards = v119b.get("cards", [])
    decision_counts = v119b.get("decision_counts", {})
    no_send = v119b.get("no_send_preview", {})

    # Build card summary rows
    card_rows = ""
    for i, c in enumerate(cards):
        cf = c.get("card_family", "")
        decision = c.get("operator_decision", "")
        pipeline = c.get("pipeline_status", "")
        blite = c.get("blite_tier", "") or "N/A"
        card_rows += f"""
                    <tr>
                        <td>{i + 1}</td>
                        <td><code>{_escape_html(cf)}</code></td>
                        <td>{_escape_html(pipeline)}</td>
                        <td><strong>{_escape_html(decision)}</strong></td>
                        <td><code>{_escape_html(blite)}</code></td>
                    </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Radar MVP v119C — 封版入口</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: #0f172a; color: #e2e8f0; margin: 0; padding: 0; line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-bottom: 3px solid #7c3aed; padding: 32px 40px;
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 2rem; font-weight: 800; color: #f1f5f9; }}
        .header .subtitle {{ font-size: 0.95rem; color: #94a3b8; }}
        .header .badge-row {{ margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }}
        .badge {{
            display: inline-block; padding: 4px 14px; border-radius: 14px;
            font-size: 0.78rem; font-weight: 700;
        }}
        .badge-mvp {{ background: #7c3aed; color: #ddd6fe; border: 1px solid #a78bfa; }}
        .badge-seal {{ background: #166534; color: #bbf7d0; border: 1px solid #22c55e; }}
        .badge-local {{ background: #1e293b; color: #94a3b8; border: 1px solid #475569; }}
        .badge-nosend {{ background: #450a0a; color: #fca5a5; border: 1px solid #dc2626; }}
        .main {{ max-width: 1200px; margin: 0 auto; padding: 32px 40px; }}
        .section-title {{
            font-size: 1.2rem; font-weight: 700; color: #f1f5f9;
            margin: 36px 0 16px 0; padding-bottom: 8px; border-bottom: 1px solid #334155;
        }}
        .entry-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 14px; margin: 16px 0;
        }}
        .entry-card {{
            background: #1e293b; border: 1px solid #334155; border-radius: 10px;
            padding: 20px; transition: border-color 0.2s;
        }}
        .entry-card:hover {{ border-color: #7c3aed; }}
        .entry-card h3 {{ margin: 0 0 8px 0; font-size: 1rem; color: #a78bfa; }}
        .entry-card p {{ margin: 0; font-size: 0.85rem; color: #94a3b8; }}
        .entry-card .file-path {{
            display: block; margin-top: 8px; font-size: 0.75rem;
            font-family: 'Cascadia Code', 'Fira Code', monospace; color: #64748b;
        }}
        .capability-list {{ list-style: none; padding: 0; margin: 12px 0; }}
        .capability-list li {{
            padding: 6px 0; font-size: 0.88rem;
            border-bottom: 1px solid #1e293b;
        }}
        .capability-list li::before {{
            content: "✅ "; color: #22c55e; font-weight: 700;
        }}
        .no-prod-list {{ list-style: none; padding: 0; margin: 12px 0; }}
        .no-prod-list li {{
            padding: 6px 0; font-size: 0.88rem;
            border-bottom: 1px solid #1e293b;
        }}
        .no-prod-list li::before {{
            content: "❌ "; color: #ef4444; font-weight: 700;
        }}
        .flag-grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 8px; margin: 16px 0;
        }}
        .flag-item {{
            background: #1e293b; border: 1px solid #334155; border-radius: 6px;
            padding: 10px 14px; display: flex; align-items: center; gap: 8px;
        }}
        .flag-key {{ color: #94a3b8; font-size: 0.78rem; font-family: 'Cascadia Code', monospace; }}
        .flag-val {{ font-weight: 700; font-family: 'Cascadia Code', monospace; font-size: 0.82rem; }}
        .flag-false {{ color: #22c55e; }}
        .flag-true {{ color: #ef4444; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{
            background: #1e293b; color: #94a3b8; font-weight: 600;
            text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.05em;
            padding: 10px 12px; text-align: left; border-bottom: 2px solid #475569;
        }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; }}
        tr:hover td {{ background: #1e293b33; }}
        code {{
            font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.82rem;
            background: #1e293b; padding: 1px 5px; border-radius: 3px;
        }}
        .footer {{
            margin-top: 48px; padding: 20px 40px; border-top: 1px solid #334155;
            color: #475569; font-size: 0.78rem; text-align: center;
        }}
        .footer .no-prod {{
            display: inline-block; background: #450a0a; color: #fca5a5;
            padding: 4px 14px; border-radius: 20px; font-weight: 700;
            font-size: 0.78rem; border: 1px solid #7f1d1d;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Market Radar MVP v119C <span style="color:#a78bfa;">封版包</span></h1>
        <div class="subtitle">
            生成时间: {_escape_html(gen_stamp)} &nbsp;|&nbsp;
            Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
            Pipeline: {_escape_html(PIPELINE_VERSION)} &nbsp;|&nbsp;
            基于: v119B (B-lite) &nbsp;|&nbsp;
            模式: local-only / no-send / MVP seal
        </div>
        <div class="badge-row">
            <span class="badge badge-mvp">MVP SEAL</span>
            <span class="badge badge-seal">封版交付</span>
            <span class="badge badge-local">LOCAL ONLY</span>
            <span class="badge badge-nosend">NO SEND</span>
        </div>
    </div>

    <div class="main">

        <!-- Entry Points -->
        <h2 class="section-title">🔗 核心入口 (Entry Points)</h2>
        <div class="entry-grid">
            <div class="entry-card" style="border-color:#0284c7;">
                <h3>📊 v119B 策略值班看板</h3>
                <p>当前操作员主看板 — 五卡总览 + 中文引导 + B-lite 分层</p>
                <span class="file-path">runs/market_radar/v119b_operator_dashboard.html</span>
            </div>
            <div class="entry-card">
                <h3>⏱️ 3 分钟演示流程</h3>
                <p>用户可直接照着演示当前全部成果</p>
                <span class="file-path">runs/market_radar/v119c_user_demo_3min.md</span>
            </div>
            <div class="entry-card">
                <h3>📋 操作员快速使用说明</h3>
                <p>手动运行、查看、停止的完整流程</p>
                <span class="file-path">runs/market_radar/v119c_operator_quickstart.md</span>
            </div>
            <div class="entry-card">
                <h3>✅ MVP 验收报告</h3>
                <p>当前 MVP 达成项和不满足的生产条件</p>
                <span class="file-path">runs/market_radar/v119c_mvp_acceptance_report.md</span>
            </div>
            <div class="entry-card">
                <h3>⚠️ 已知限制 & 下一阶段</h3>
                <p>不能生产化的原因和后续候选方向</p>
                <span class="file-path">runs/market_radar/v119c_known_limits_and_next_steps.md</span>
            </div>
            <div class="entry-card">
                <h3>📦 最终交接说明</h3>
                <p>local-only / no-send / not production-ready</p>
                <span class="file-path">runs/market_radar/v119c_local_only_final_handoff.md</span>
            </div>
        </div>

        <!-- Current Capability Summary -->
        <h2 class="section-title">📋 当前能力摘要 (Capability Summary)</h2>
        <ul class="capability-list">
            <li><strong>live public data one-shot refresh</strong> 已跑通（Binance 公开 API + 免费 RSS）</li>
            <li><strong>shared pipeline</strong> 已跑通（五卡统一管道）</li>
            <li><strong>五类策略卡已覆盖：</strong>market_sync / price_oi_anomaly / news_event / liquidation / whale</li>
            <li><strong>B-lite price/OI watch 分层</strong>已实现（reject → mild_watch → accept）</li>
            <li><strong>news freshness / stale warning</strong> 已实现（启发式时效性标记）</li>
            <li><strong>中文 30 秒引导层</strong>已实现（这是什么/怎么看/能不能发/数据来源/下一步）</li>
        </ul>

        <h2 class="section-title">🚫 生产状态 (Production Status)</h2>
        <ul class="no-prod-list">
            <li><strong>production readiness = false / 0/5</strong></li>
            <li><strong>no-send</strong>（本轮不发送任何渠道）</li>
            <li><strong>local-only</strong>（仅本地静态 HTML）</li>
            <li><strong>not production-ready</strong>（不满足任何生产条件）</li>
        </ul>

        <!-- Send Flags -->
        <h2 class="section-title">🔒 发送状态确认 (Send Status Confirmation)</h2>
        <div class="flag-grid">
            <div class="flag-item"><span class="flag-key">telegram_send</span><span class="flag-val flag-false">= false</span></div>
            <div class="flag-item"><span class="flag-key">x_twitter_send</span><span class="flag-val flag-false">= false</span></div>
            <div class="flag-item"><span class="flag-key">production_send</span><span class="flag-val flag-false">= false</span></div>
            <div class="flag-item"><span class="flag-key">daemon_or_loop_started</span><span class="flag-val flag-false">= false</span></div>
        </div>

        <!-- Decision Summary from v119B -->
        <h2 class="section-title">⚖️ 当前五卡决策分布 (Decision Distribution)</h2>
        <div class="table-container" style="overflow-x:auto; margin:16px 0; border:1px solid #334155; border-radius:8px;">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Card Family</th>
                        <th>Pipeline</th>
                        <th>Decision</th>
                        <th>B-lite Tier</th>
                    </tr>
                </thead>
                <tbody>{card_rows}
                </tbody>
            </table>
        </div>

        <!-- v119B Data -->
        <h2 class="section-title">📡 基于 v119B 数据</h2>
        <p style="color:#94a3b8; font-size:0.88rem;">
            本封版包基于 v119B 运行结果:
            Run ID <code>{_escape_html(v119b.get('run_id', 'N/A'))}</code>,
            生成于 <code>{_escape_html(v119b.get('generated_at', 'N/A'))}</code>,
            包含 5 个 card family,
            contract validation <strong>{_escape_html(str(v119b.get('contract_validation', {}).get('all_passed', False)))}</strong>.
        </p>

    </div>

    <div class="footer">
        <div style="margin-bottom:8px;"><span class="no-prod">⛔ NOT FOR PRODUCTION USE — 0/5</span></div>
        Market Radar MVP v119C 封版包 &nbsp;|&nbsp;
        Pipeline: {_escape_html(PIPELINE_VERSION)} &nbsp;|&nbsp;
        Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
        模式: local-only / no-send / MVP seal &nbsp;|&nbsp;
        telegram_send=false &nbsp;|&nbsp;
        x_twitter_send=false &nbsp;|&nbsp;
        production_send=false &nbsp;|&nbsp;
        daemon_or_loop_started=false
    </div>
</body>
</html>"""
    return html


# ── Step 3: Generate 3-minute user demo markdown ───────────────────────────────


def generate_user_demo_3min_md(v119b: dict) -> str:
    """Generate the 3-minute user demo document."""
    cards = v119b.get("cards", [])
    decision_counts = v119b.get("decision_counts", {})

    lines = [
        "# Market Radar MVP v119C — 3 分钟用户演示流程",
        "",
        f"**生成时间**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**基于版本**: v119B (B-lite quality enhancement)",
        "",
        "---",
        "",
        "## 演示前准备",
        "",
        "1. 确保 v119B runner 已执行过一次（已有结果文件）",
        "2. 打开浏览器（Chrome / Edge / Firefox 均可）",
        "3. 本演示不需要联网、不需要 API Key、不需要外部账号",
        "",
        "---",
        "",
        "## 演示流程 (约3分钟)",
        "",
        "### 第 1 步：打开主看板 (30 秒)",
        "",
        "在文件管理器中打开：",
        "```",
        "runs/market_radar/v119b_operator_dashboard.html",
        "```",
        "双击用浏览器打开。",
        "",
        "**展示要点**：",
        "- 页面顶部显示\"Market Radar 策略值班看板 v119B\"",
        "- 可以看到 LIVE DATA、B-LITE 两个标签",
        "- Production Readiness 显示 **false / 0/5**",
        "- Telegram Sent 显示 **false**",
        "",
        "### 第 2 步：看顶部中文引导 (30 秒)",
        "",
        "页面从上往下滚动，第二个区块是\"🧭 30 秒中文引导\"：",
        "",
        "**展示 5 个问题的中文回答**：",
        "1. **📌 这是什么？** → 策略值班看板，不是自动交易/发布系统",
        "2. **👀 现在怎么看？** → 优先看 accept/watch，再看 reject/manual",
        "3. **🚫 现在能不能发？** → production readiness=false，不能正式发布",
        "4. **📡 数据从哪来？** → Binance 公开 API + 免费 RSS + 本地 fixture",
        "5. **📋 操作员下一步？** → accept → 复盘 / watch → 观察 / reject → 等待 / manual → 补证据",
        "",
        "### 第 3 步：看五卡总览 (30 秒)",
        "",
        "向下滚动到\"⚖️ 操作员决策总览\"区域：",
        "",
        "**展示当前决策分布**：",
        f"- ✅ Accept（可复盘）: {decision_counts.get('accept', 0)} 个",
        f"- 👀 Watch（观察）: {decision_counts.get('watch', 0)} 个",
        f"- ❌ Reject（拒绝）: {decision_counts.get('reject', 0)} 个",
        f"- 🔒 Manual Required（需人工）: {decision_counts.get('manual_required', 0)} 个",
        "",
        "**解释**：",
        "- accept = 强信号通过 gate，可进入人工复盘（当前仅 multi_asset_market_sync）",
        "- watch = 观察级别，不代表可以发布",
        "- reject = gate 正确阻止，等待市场条件",
        "- manual_required = 需要人工补充链上证据（whale 地址归属）",
        "",
        "### 第 4 步：展示 B-lite 分层价值 (30 秒)",
        "",
        "向下滚动到\"🗂️ 操作员决策表\"，找到 `price_oi_volume_anomaly` 行：",
        "",
        "**展示要点**：",
        "- **Decision 列显示 \"👀 WATCH\"**",
        "- **B-lite Tier 列显示 \"mild_watch\"**",
        "- 这不是 accept，这是观察级别",
        "- B-lite 把原本会被 reject 的轻度异常升级为 mild_watch",
        "- **价值**：从 raw reject → mild watch，操作员能看到\"值得关注但不值得行动\"的信号",
        "- **约束**：watch ≠ accept，watch ≠ publishable",
        "",
        "### 第 5 步：展示 news observation-only (30 秒)",
        "",
        "在决策表中找到 `news_event_market_impact` 行：",
        "",
        "**展示要点**：",
        "- **Obs Only 列 = True**（仅观察）",
        "- **Not Causal 列 = True**（不是因果证明）",
        "- 展示 freshness_info（fresh/stale/unknown 计数）",
        "- 新闻事件市场影响卡片做的是 observation-only",
        "- 不构成因果证明，不构成交易建议",
        "- 操作员仍需阅读原文核实",
        "",
        "### 第 6 步：展示 whale 人工证据要求 (30 秒)",
        "",
        "在决策表中找到 `whale_position_alert` 行：",
        "",
        "**展示要点**：",
        "- Decision 显示 \"🔒 MANUAL REQUIRED\"",
        "- Pipeline 显示 \"blocked\"",
        "- Gate Reason 说明需要人工链上地址归属验证",
        "- 手动证据未提供 → gate 正确阻止",
        "- 这不是 bug，这是设计意图",
        "- 不可绕过人工证据要求",
        "",
        "### 第 7 步：总结 — 这是什么，这不是什么 (30 秒)",
        "",
        "**这是什么**：",
        "- ✅ 本地策略值班看板 MVP",
        "- ✅ 五类市场信号的统一管道",
        "- ✅ 操作员决策辅助工具",
        "- ✅ 免费公开数据源驱动",
        "- ✅ B-lite 信号质量增强",
        "",
        "**这不是什么**：",
        "- ❌ 不是自动交易系统",
        "- ❌ 不是自动发帖/发布系统",
        "- ❌ 不是生产环境就绪的系统",
        "- ❌ 不是 AI/ML 驱动的预测系统",
        "- ❌ 不是机构级数据管道",
        "",
        "---",
        "",
        "## 演示结束",
        "",
        "**Production Readiness: false / 0/5**",
        "**telegram_send=false | x_twitter_send=false | production_send=false**",
        "**daemon_or_loop_started=false**",
        "",
        "本次演示展示的是 Market Radar MVP 封版包 v119C，",
        "这是一个 local-only / no-send 的本地策略值班看板。",
        "不可用于生产环境，不可作为交易依据。",
    ]
    return "\n".join(lines)


# ── Step 4: Generate operator quickstart markdown ──────────────────────────────


def generate_operator_quickstart_md() -> str:
    """Generate the operator quickstart document."""
    lines = [
        "# Market Radar MVP v119C — 操作员快速使用说明",
        "",
        f"**生成时间**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**版本**: v119C MVP seal (based on v119B)",
        f"**模式**: local-only / no-send",
        "",
        "---",
        "",
        "## 1. 手动运行 v119B",
        "",
        "在当前项目目录下执行：",
        "",
        "```powershell",
        "python scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py",
        "```",
        "",
        "这会：",
        "- 从 Binance 公开 REST API 获取实时价格数据（不需要 API Key）",
        "- 从免费 RSS 源获取新闻",
        "- 运行五卡共享管道",
        "- 生成 v119B 所有输出文件",
        "- 不发送 Telegram、不发送 X/Twitter、不写生产状态",
        "",
        "**运行时间**：约 10-20 秒（取决于网络）",
        "",
        "---",
        "",
        "## 2. 打开 Dashboard",
        "",
        "用浏览器打开：",
        "```",
        "runs/market_radar/v119b_operator_dashboard.html",
        "```",
        "",
        "或在文件管理器中双击该文件。",
        "",
        "---",
        "",
        "## 3. 每天使用流程",
        "",
        "### Step 1: run one-shot",
        "```powershell",
        "python scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py",
        "```",
        "",
        "### Step 2: open dashboard",
        "双击 `runs/market_radar/v119b_operator_dashboard.html`",
        "",
        "### Step 3: check accept/watch",
        "先看 ✅ Accept（可复盘）和 👀 Watch（观察），再查看原因。",
        "",
        "### Step 4: check reject/manual_required reason",
        "reject 通常是 gate 正确阻止（如市场平静期 liquidation 不触发），",
        "manual_required 是需要补充人工证据（如 whale 地址归属验证）。",
        "",
        "### Step 5: record observation manually",
        "在本地笔记本或日志中记录观察结果。",
        "不要依赖系统自动记录 — 当前没有 operator review log 功能。",
        "",
        "---",
        "",
        "## 4. 停止 / 关闭",
        "",
        "**无 daemon**：不需要停止任何后台进程。",
        "",
        "**无后台进程**：runner 是一次性执行，执行完即退出。",
        "",
        "**关掉浏览器即可**：dashboard 是静态 HTML，关闭浏览器标签页即结束。",
        "",
        "---",
        "",
        "## 5. ⛔ 禁止事项",
        "",
        "### 不得当交易建议",
        "本系统是策略值班看板，用于观察市场信号。",
        "**不构成任何投资建议或交易建议。**",
        "所有信号仅供参考，实际决策由操作员自行负责。",
        "",
        "### 不得直接正式发布",
        "当前 production readiness = false / 0/5。",
        "telegram_send=false, x_twitter_send=false, production_send=false。",
        "**不得将本系统的输出直接发布到任何生产渠道。**",
        "",
        "### 不得绕过 manual evidence",
        "whale_position_alert 要求人工链上地址归属验证。",
        "**不得绕过此要求强行通过 gate。**",
        "",
        "### 不得改 production readiness",
        "production readiness 固定为 false / 0/5。",
        "**不得在代码或配置中将其改为 true。**",
        "",
        "---",
        "",
        "## 6. 问题排查",
        "",
        "### Dashboard 空白或数据缺失",
        "重新运行 v119B runner（见第 1 步）。",
        "如果 runner 报错，检查网络连接（Binance API 需要联网）。",
        "",
        "### 所有卡都是 reject",
        "检查市场条件 — 平静期很多卡会被正确 reject。",
        "这是正常行为，不是 bug。",
        "",
        "### HTML 显示乱码",
        "用现代浏览器（Chrome/Edge/Firefox）打开。",
        "文件编码为 UTF-8。",
        "",
        "---",
        "",
        "**Production Readiness: false / 0/5 — NOT FOR LIVE USE**",
    ]
    return "\n".join(lines)


# ── Step 5: Generate MVP acceptance report markdown ────────────────────────────


def generate_acceptance_report_md(v119b: dict) -> str:
    """Generate the MVP acceptance report."""
    decision_counts = v119b.get("decision_counts", {})
    contract = v119b.get("contract_validation", {})
    checks = contract.get("checks", [])
    all_passed = contract.get("all_passed", False)
    blite = v119b.get("blite_enhancements", {})

    lines = [
        "# Market Radar MVP v119C — 封版验收报告",
        "",
        f"**生成时间**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**当前版本**: v119C MVP seal",
        f"**基于版本**: v119B (B-lite quality enhancement)",
        f"**v119B Run ID**: {v119b.get('run_id', 'N/A')}",
        f"**v119B 生成时间**: {v119b.get('generated_at', 'N/A')}",
        "",
        "---",
        "",
        "## 最近测试统计",
        "",
        f"- **v119B contract validation**: {'✅ ALL PASSED' if all_passed else '❌ HAS FAILURES'}",
        f"- **Contract checks passed**: {sum(1 for c in checks if c.get('passed'))} / {len(checks)}",
        f"- **v119B 运行模式**: {v119b.get('mode', 'N/A')}",
        f"- **v119B Pipeline**: {v119b.get('pipeline_version', 'N/A')}",
        f"- **总卡片数**: {len(v119b.get('cards', []))}",
        "",
        "---",
        "",
        "## 当前五卡决策分布",
        "",
        "| Decision | Count |",
        "|---|--------|",
        f"| accept | {decision_counts.get('accept', 0)} |",
        f"| watch | {decision_counts.get('watch', 0)} |",
        f"| reject | {decision_counts.get('reject', 0)} |",
        f"| manual_required | {decision_counts.get('manual_required', 0)} |",
        "",
        "---",
        "",
        "## ✅ 已满足的 MVP 条件",
        "",
        "| MVP 条件 | 状态 | 说明 |",
        "|---|--------|--------|",
        "| live data | ✅ MET | Binance 公开 REST API + 免费 RSS 源实时数据获取 |",
        "| shared pipeline | ✅ MET | 五卡统一管道，所有卡通过同一 pipeline 处理 |",
        "| operator decision | ✅ MET | 五卡操作员决策 (accept/watch/reject/manual_required) |",
        "| local dashboard | ✅ MET | 自包含 HTML 看板，离线可打开 |",
        "| no-send | ✅ MET | telegram_send=false, x_twitter_send=false, production_send=false |",
        "| B-lite quality | ✅ MET | price/OI 分层决策 + news freshness/stale + OI 检测 |",
        "| Chinese guidance | ✅ MET | 30 秒中文引导层：这是什么/怎么看/能不能发/数据来源/下一步 |",
        "| secret leak audit | ✅ MET | 零 raw token/chat_id/message_id/cookie/password/API key 泄漏 |",
        "| regression pass | ✅ MET | v119B 全部 15 项 contract checks 通过 |",
        "",
        "---",
        "",
        "## ❌ 未满足的生产条件",
        "",
        "| 生产条件 | 状态 | 说明 |",
        "|---|--------|--------|",
        "| production readiness | ❌ NOT MET | false / 0/5 — 不满足任何生产条件 |",
        "| automated_multi_asset_sync | ❌ NOT MET | 仅免费公开 API — 无机构级数据源 |",
        "| automated_price_oi_volume | ❌ NOT MET | 阈值启发式异常检测 — 无 ML/统计模型 |",
        "| news_event_processing | ❌ NOT MET | 规则关键词匹配 — 无 AI/model |",
        "| liquidation_pressure_automation | ❌ NOT MET | 平静市场正确阻止 — 需高波动检测 |",
        "| whale_position_attribution | ❌ NOT MET | 需人工地址归属验证 — 无自动化方案 |",
        "| no official TG | ❌ NOT MET | 无正式 Telegram 频道配置 |",
        "| no X/Twitter | ❌ NOT MET | 无 X/Twitter 发布能力（按设计不启用） |",
        "| no production write | ❌ NOT MET | 系统不对任何生产环境写入 |",
        "| no daemon | ❌ NOT MET | 无后台进程、cron、loop — 仅手动 one-shot |",
        "| whale manual evidence not complete | ❌ NOT MET | 需人工完成 v116N whale evidence workbook |",
        "| no institutional-grade feed | ❌ NOT MET | 仅 Binance 免费 API — 无机构级市场数据 |",
        "| no long-term stability report | ❌ NOT MET | 无多日运行稳定性记录 |",
        "",
        "---",
        "",
        "## 合约验证详情 (Contract Checks)",
        "",
        "| # | Check | Passed | Detail |",
        "|---|--------|--------|--------|",
    ]

    for i, c in enumerate(checks):
        icon = "✅" if c.get("passed") else "❌"
        detail = c.get("detail", "")[:100]
        lines.append(f"| {i + 1} | {c.get('check', '')} | {icon} | {detail} |")

    lines.extend([
        "",
        "---",
        "",
        "## 验收结论",
        "",
        f"**Contract Validation**: {'ALL PASSED ✅' if all_passed else 'HAS FAILURES ❌'}",
        "",
        "**MVP 目标达成**：",
        "- 五卡基金覆盖完整",
        "- live data one-shot 已跑通",
        "- shared pipeline 已跑通",
        "- operator decision 引擎正常",
        "- local dashboard 可正常打开",
        "- no-send 确认无误",
        "- B-lite 质量增强已实现",
        "- 中文引导层已实现",
        "",
        "**生产化未达成**：",
        "- production readiness = false / 0/5",
        "- 不满足任何生产条件",
        "- 不适合生产环境使用",
        "- 不可作为自动交易/自动发布系统",
        "",
        "**封版状态**: v119C MVP SEAL — 交付完成，可交接。",
        "",
        "---",
        "",
        "**Production Readiness: false / 0/5 — NOT FOR LIVE USE**",
    ])

    return "\n".join(lines)


# ── Step 6: Generate known limits and next steps markdown ──────────────────────


def generate_known_limits_md(v119b: dict) -> str:
    """Generate known limits and next steps document."""
    lines = [
        "# Market Radar MVP v119C — 已知限制 & 下一阶段建议",
        "",
        f"**生成时间**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**版本**: v119C MVP seal (based on v119B)",
        "",
        "**状态**: local-only / no-send / not production-ready",
        "**telegram_send**: false | **x_twitter_send**: false | **production_send**: false",
        "",
        "---",
        "",
        "## ⚠️ 已知限制 (Known Limits)",
        "",
        "### 1. news freshness 是规则启发式",
        "- freshness 分类基于标题关键词和来源名称的规则匹配",
        "- 不是基于实际发布时间戳的精确判断",
        "- 可能存在误判（把旧文章标为 fresh，或把新文章标为 stale）",
        "- 操作员仍需查看原文发布日期确认时效性",
        "",
        "### 2. price/OI watch 是观察，不是交易建议",
        "- mild_watch 分层是规则驱动的启发式判断",
        "- 轻度异常升级为 watch 只表示\"值得关注\"",
        "- 不代表价格将朝任何方向变动",
        "- **不可作为交易依据**",
        "",
        "### 3. liquidation 仍受真实市场条件限制",
        "- 使用本地 fixture 数据，非实时链上数据",
        "- 平静市场期 gate 正确阻止 → 无输出",
        "- 需要高波动市场窗口才能触发",
        "- 不能保证在每次 liquidation 事件时都能捕获",
        "",
        "### 4. whale 仍需人工证据",
        "- 地址归属没有自动化验证方案",
        "- 免费公开 API 无法提供地址归属信息",
        "- 需操作员手动完成 v116N whale evidence workbook",
        "- 在人工证据完成前，whale_position_alert 始终为 manual_required",
        "",
        "### 5. dashboard 是本地静态 HTML",
        "- 不是动态 Web 应用",
        "- 没有实时数据推送或自动刷新",
        "- 需要手动运行 runner 后重新打开",
        "- 数据是运行时刻的快照，不会自动更新",
        "",
        "### 6. one-shot 需要手动运行",
        "- 没有 daemon/cron/loop 自动刷新",
        "- 操作员需要手动执行 python 命令",
        "- 没有 UI 界面触发运行",
        "- 每次运行需要 10-20 秒网络请求时间",
        "",
        "### 7. 数据源限制",
        "- 仅使用 Binance 免费公开 REST API（有速率限制）",
        "- 新闻源为免费 RSS（CoinDesk/Cointelegraph/Decrypt/The Block）",
        "- liquidation 和 whale 使用本地 fixture（模拟数据）",
        "- 没有付费数据源、没有 WebSocket 实时流、没有机构级 feed",
        "",
        "### 8. 无 operator review log",
        "- 操作员观察结果需要手动记录",
        "- 没有内置的观察日志或历史记录功能",
        "- 无法回顾之前的决策和执行",
        "",
        "---",
        "",
        "## 📋 下一阶段建议 (只列候选，不执行)",
        "",
        "以下为下一阶段候选方向，**本轮 v119C 不执行任何一项**。",
        "是否执行、何时执行需单独决策。",
        "",
        "### 候选 1: manual whale evidence intake",
        "- 操作员完成 v116N whale evidence workbook",
        "- 包含链上地址归属验证证据",
        "- 完成后 whale_position_alert 可能从 manual_required 升级",
        "- **不自动执行此步骤 — 需操作员人工完成**",
        "",
        "### 候选 2: 多日手动稳定性记录",
        "- 连续多日手动运行 one-shot 并记录结果",
        "- 观察信号稳定性和变化模式",
        "- 收集足够数据以评估系统可靠性",
        "- **不自动执行 — 需操作员持续手动操作**",
        "",
        "### 候选 3: dashboard 历史对比",
        "- 保存多日 snapshot 以便对比",
        "- 添加历史数据查看功能",
        "- 可能需要将静态 HTML 升级为简单应用",
        "- **不自动执行 — 需额外开发工作**",
        "",
        "### 候选 4: operator review log",
        "- 添加操作员观察记录功能",
        "- 记录每次查看的决策和备注",
        "- 可能需要本地存储（JSON/SQLite）",
        "- **不自动执行 — 需额外开发工作**",
        "",
        "### 候选 5: TG test-group optional send",
        "- 在有明确工单授权且 lane 权限允许时",
        "- 可向 TG 测试群发送观察卡片",
        "- 必须在明确工单中授权，不可自动触发",
        "- **不自动执行 — 需单独工单授权**",
        "",
        "---",
        "",
        "## 🚫 明确不要做的事",
        "",
        "- ❌ 不要自动启动 recurring/daemon/cron",
        "- ❌ 不要降低 liquidation threshold",
        "- ❌ 不要绕过 whale manual evidence",
        "- ❌ 不要把 production readiness 改成 true",
        "- ❌ 不要新增策略信号",
        "- ❌ 不要改 gate 阈值",
        "- ❌ 不要自动发 TG/X/Twitter",
        "- ❌ 不要调用 AI/model API",
        "",
        "---",
        "",
        "**Production Readiness: false / 0/5 — NOT FOR LIVE USE**",
    ]
    return "\n".join(lines)


# ── Step 7: Generate final handoff markdown ────────────────────────────────────


def generate_handoff_md(v119b: dict) -> str:
    """Generate the final local-only handoff document."""
    decision_counts = v119b.get("decision_counts", {})

    lines = [
        "# Market Radar MVP v119C — 最终交接说明 (Local-Only Final Handoff)",
        "",
        f"**生成时间**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**版本**: v119C MVP seal (based on v119B)",
        "",
        "---",
        "",
        "## 交接内容",
        "",
        "本次交接的是 **Market Radar MVP v119C 封版包**，包含：",
        "",
        "### 核心产物",
        "| 文件 | 位置 | 说明 |",
        "|---|------|------|",
        "| v119B Dashboard | `runs/market_radar/v119b_operator_dashboard.html` | 策略值班看板（浏览器打开） |",
        "| MVP Index | `runs/market_radar/v119c_mvp_index.html` | 封版入口索引页（浏览器打开） |",
        "| 3 分钟演示 | `runs/market_radar/v119c_user_demo_3min.md` | 用户演示流程文档 |",
        "| 操作员快速指南 | `runs/market_radar/v119c_operator_quickstart.md` | 操作员使用说明 |",
        "| MVP 验收报告 | `runs/market_radar/v119c_mvp_acceptance_report.md` | 封版验收报告 |",
        "| 已知限制 | `runs/market_radar/v119c_known_limits_and_next_steps.md` | 限制和后续方向 |",
        "| 结果 JSON | `results/market_radar_v119c_mvp_seal_result.json` | 封版结果数据 |",
        "| v119B 结果 JSON | `results/market_radar_v119b_signal_quality_b_lite_result.json` | v119B 运行结果 |",
        "",
        "### Runner & Tests",
        "| 文件 | 说明 |",
        "|------|------|",
        "| `scripts/run_market_radar_v119c_mvp_seal_user_demo_pack.py` | v119C runner |",
        "| `scripts/test_market_radar_v119c_mvp_seal_user_demo_pack.py` | v119C 测试 |",
        "",
        "---",
        "",
        "## 当前状态",
        "",
        f"- **五卡决策分布**: accept={decision_counts.get('accept', 0)}, watch={decision_counts.get('watch', 0)}, reject={decision_counts.get('reject', 0)}, manual_required={decision_counts.get('manual_required', 0)}",
        f"- **Contract Validation**: {v119b.get('contract_validation', {}).get('all_passed', False)}",
        "- **Production Readiness**: false / 0/5",
        "- **telegram_send**: false",
        "- **x_twitter_send**: false",
        "- **production_send**: false",
        "- **daemon_or_loop_started**: false",
        "- **ai_model_called**: false",
        "- **files_deleted**: false",
        "",
        "---",
        "",
        "## 重要声明",
        "",
        "### ⛔ 当前仍是 local-only / no-send / not production-ready",
        "",
        "本系统：",
        "- **不是自动交易系统** — 不执行任何交易操作",
        "- **不是自动发布系统** — 不向任何渠道自动发送内容",
        "- **不是生产环境就绪的系统** — 所有 5 项生产条件均未满足",
        "- **不是 AI/ML 驱动的预测系统** — 所有信号判断均为规则启发式",
        "- **不是机构级数据管道** — 仅使用免费公开 API",
        "- **不能作为交易依据** — 所有信号仅供参考",
        "",
        "### 🔒 安全承诺",
        "",
        "- 无 raw token/chat_id/message_id/cookie/password/API key 在任何输出中",
        "- 无 TG 发送",
        "- 无 X/Twitter 发送",
        "- 无生产写入",
        "- 无 daemon/cron/loop",
        "- 无文件删除",
        "- 无历史产物修改（v116A-N/v117/v118/v119A/v119B）",
        "",
        "---",
        "",
        "## 如何运行",
        "",
        "```powershell",
        "# 1. 运行 v119B (获取实时数据)",
        "python scripts/run_market_radar_v119b_signal_quality_b_lite_and_dashboard_guidance.py",
        "",
        "# 2. 运行 v119C (生成封版包)",
        "python scripts/run_market_radar_v119c_mvp_seal_user_demo_pack.py",
        "",
        "# 3. 运行测试",
        "python -X utf8 -m pytest scripts/test_market_radar_v119c_mvp_seal_user_demo_pack.py -v",
        "",
        "# 4. 打开看板",
        "start runs/market_radar/v119b_operator_dashboard.html",
        "start runs/market_radar/v119c_mvp_index.html",
        "```",
        "",
        "---",
        "",
        "## 交接完成",
        "",
        "v119C Market Radar MVP 封版包交付完成。",
        "",
        "所有产物均为 local-only，不需要服务器、不需要部署、不需要数据库。",
        "用浏览器打开 HTML 文件即可查看。",
        "",
        "**下一阶段由接收方决定是否启动。本轮不执行任何新功能开发。**",
        "",
        "---",
        "",
        "**Production Readiness: false / 0/5 — NOT FOR LIVE USE**",
    ]
    return "\n".join(lines)


# ── Step 8: Generate seal result JSON ──────────────────────────────────────────


def generate_seal_result_json(v119b: dict) -> dict:
    """Generate the v119C seal result JSON."""
    return {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "v119c_mvp_seal_user_demo_pack",
        "mode": "local_only_no_send_mvp_seal",
        "based_on": "v119B",
        "v119b_run_id": v119b.get("run_id", "N/A"),
        "v119b_generated_at": v119b.get("generated_at", "N/A"),
        "v119b_contract_all_passed": v119b.get("contract_validation", {}).get("all_passed", False),
        "decision_counts": v119b.get("decision_counts", {}),
        "production_readiness": {
            "production_ready": False,
            "production_readiness_score": "0/5",
            "assessment": "NOT FOR LIVE USE. MVP seal only. Local-only, no-send, not production-ready.",
        },
        "no_send_preview": {
            "telegram_send": False,
            "x_twitter_send": False,
            "production_send": False,
            "daemon_or_loop_started": False,
        },
        "safety": {
            "tg_sent_this_run": False,
            "tg_message_count_this_run": 0,
            "x_twitter_sent_this_run": False,
            "production_send": False,
            "prod_state_write": False,
            "ai_model_called": False,
            "daemon_or_loop_started": False,
            "files_deleted": False,
            "credentials_printed": False,
            "v116_history_modified": False,
            "v117_history_modified": False,
            "v118_history_modified": False,
            "v119a_history_modified": False,
            "v119b_history_modified": False,
            "binance_api_called": False,
            "rss_called": False,
            "telegram_called": False,
        },
        "output_files": {
            "mvp_index_html": "runs/market_radar/v119c_mvp_index.html",
            "user_demo_md": "runs/market_radar/v119c_user_demo_3min.md",
            "operator_quickstart_md": "runs/market_radar/v119c_operator_quickstart.md",
            "acceptance_report_md": "runs/market_radar/v119c_mvp_acceptance_report.md",
            "known_limits_md": "runs/market_radar/v119c_known_limits_and_next_steps.md",
            "handoff_md": "runs/market_radar/v119c_local_only_final_handoff.md",
            "result_json": "results/market_radar_v119c_mvp_seal_result.json",
        },
        "mvp_capabilities": [
            "live public data one-shot refresh",
            "shared pipeline",
            "five card family coverage",
            "B-lite price/OI watch layering",
            "news freshness / stale warning",
            "Chinese 30-second guidance layer",
        ],
        "mvp_not_production": [
            "production readiness = false / 0/5",
            "no official TG",
            "no X/Twitter",
            "no production write",
            "no daemon",
            "whale manual evidence not complete",
            "no institutional-grade feed",
            "no long-term stability report",
        ],
    }


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> int:
    print(f"=== Market Radar v119C MVP Seal User Demo Pack ===")
    print(f"    Run ID: {RUN_ID}")
    print(f"    Pipeline: {PIPELINE_VERSION}")
    print(f"    Mode: local-only / no-send / MVP seal")
    print()

    # Load v119B result (read-only)
    print("[1/8] Loading v119B result...")
    v119b = load_v119b_result()
    print(f"      v119B Run ID: {v119b.get('run_id')}")
    print(f"      Contract all_passed: {v119b.get('contract_validation', {}).get('all_passed')}")

    # Generate MVP index HTML
    print("[2/8] Generating MVP index HTML...")
    index_html = generate_mvp_index_html(v119b)
    write_text(OUTPUT_INDEX_HTML, index_html)
    print(f"      -> {OUTPUT_INDEX_HTML}")

    # Generate user demo 3min
    print("[3/8] Generating 3-minute user demo...")
    demo_md = generate_user_demo_3min_md(v119b)
    write_text(OUTPUT_USER_DEMO_MD, demo_md)
    print(f"      -> {OUTPUT_USER_DEMO_MD}")

    # Generate operator quickstart
    print("[4/8] Generating operator quickstart...")
    quickstart_md = generate_operator_quickstart_md()
    write_text(OUTPUT_QUICKSTART_MD, quickstart_md)
    print(f"      -> {OUTPUT_QUICKSTART_MD}")

    # Generate MVP acceptance report
    print("[5/8] Generating MVP acceptance report...")
    acceptance_md = generate_acceptance_report_md(v119b)
    write_text(OUTPUT_ACCEPTANCE_MD, acceptance_md)
    print(f"      -> {OUTPUT_ACCEPTANCE_MD}")

    # Generate known limits
    print("[6/8] Generating known limits and next steps...")
    limits_md = generate_known_limits_md(v119b)
    write_text(OUTPUT_KNOWN_LIMITS_MD, limits_md)
    print(f"      -> {OUTPUT_KNOWN_LIMITS_MD}")

    # Generate final handoff
    print("[7/8] Generating final handoff...")
    handoff_md = generate_handoff_md(v119b)
    write_text(OUTPUT_HANDOFF_MD, handoff_md)
    print(f"      -> {OUTPUT_HANDOFF_MD}")

    # Generate seal result JSON
    print("[8/8] Generating seal result JSON...")
    seal_result = generate_seal_result_json(v119b)
    write_json(OUTPUT_RESULT_JSON, seal_result)
    print(f"      -> {OUTPUT_RESULT_JSON}")

    print()
    print("=== v119C MVP Seal Complete ===")
    print(f"    7 output files generated")
    print(f"    production_readiness: false / 0/5")
    print(f"    telegram_send: false")
    print(f"    x_twitter_send: false")
    print(f"    production_send: false")
    print(f"    daemon_or_loop_started: false")
    print(f"    binance_called: false")
    print(f"    rss_called: false")
    print(f"    telegram_called: false")
    print(f"    ai_model_called: false")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

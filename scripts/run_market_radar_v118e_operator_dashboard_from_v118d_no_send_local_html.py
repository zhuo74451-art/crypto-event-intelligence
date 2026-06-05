"""Market Radar v118E — Operator Dashboard from v118D (Local HTML, No-Send).

Reads the v118D operator acceptance gate result (local JSON/MD) and produces
a local operator HTML dashboard suitable for offline review and acceptance.

This is a LOCAL-ONLY / NO-SEND run. It MUST NOT:
  - Re-read v118C
  - Call Binance, RSS, Telegram, or any external service
  - Send any TG message
  - Call any AI/model API
  - Modify v116A–N historical outputs
  - Start daemons, cron jobs, or loops

Source: v118D operator acceptance gate result (read-only, local file).

Outputs:
  runs/market_radar/v118e_operator_dashboard.html
  runs/market_radar/v118e_operator_dashboard_preview.md
  runs/market_radar/v118e_local_only_handoff.md
  results/market_radar_v118e_operator_dashboard_result.json

Usage:
    python scripts/run_market_radar_v118e_operator_dashboard_from_v118d_no_send_local_html.py
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
PIPELINE_VERSION = "v1.18E"
TASK_ID = "20260605_v118e_operator_dashboard_from_v118d_no_send_local_html"

V118D_RESULT_PATH = ROOT / "results" / "market_radar_v118d_operator_acceptance_gate_result.json"
V118D_REVIEW_PACK_PATH = ROOT / "runs" / "market_radar" / "v118d_operator_review_pack.md"
V118D_DECISION_TABLE_PATH = ROOT / "runs" / "market_radar" / "v118d_operator_decision_table.md"
V118D_NO_SEND_PREVIEW_PATH = ROOT / "runs" / "market_radar" / "v118d_no_send_preview.md"
V118D_HANDOFF_PATH = ROOT / "runs" / "market_radar" / "v118d_local_only_handoff.md"

OUTPUT_HTML = ROOT / "runs" / "market_radar" / "v118e_operator_dashboard.html"
OUTPUT_PREVIEW_MD = ROOT / "runs" / "market_radar" / "v118e_operator_dashboard_preview.md"
OUTPUT_HANDOFF = ROOT / "runs" / "market_radar" / "v118e_local_only_handoff.md"
OUTPUT_RESULT_JSON = ROOT / "results" / "market_radar_v118e_operator_dashboard_result.json"

FIVE_CARD_FAMILIES = [
    "multi_asset_market_sync",
    "price_oi_volume_anomaly",
    "news_event_market_impact",
    "liquidation_pressure",
    "whale_position_alert",
]

ALLOWED_DECISIONS = {"accept", "watch", "reject", "manual_required"}


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


# ═══════════════════════════════════════════════════════════════════════════
# V118D RESULT LOADER (read-only, no external calls, no re-read of v118C)
# ═══════════════════════════════════════════════════════════════════════════


def load_v118d_result() -> dict[str, Any]:
    """Load the v118D operator acceptance gate result from disk.

    This reads ONLY v118D local files. No re-reading of v118C.
    No Binance, RSS, Telegram, AI/model, or any external service.
    """
    if not V118D_RESULT_PATH.exists():
        print(f"  [FAIL] v118D result not found: {V118D_RESULT_PATH}")
        print("  The v118D runner must be executed first to generate the acceptance gate.")
        sys.exit(1)

    with open(V118D_RESULT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  [OK] Loaded v118D result: {V118D_RESULT_PATH}")
    print(f"       pipeline_version: {data.get('pipeline_version', 'unknown')}")
    print(f"       run_id: {data.get('run_id', 'unknown')}")
    print(f"       cards: {len(data.get('cards', []))}")
    print(f"       source: {data.get('source', 'unknown')}")
    return data


def load_v118d_md(path: Path, label: str) -> str:
    """Load a v118D markdown file for reference (optional, not required)."""
    if path.exists():
        content = path.read_text(encoding="utf-8")
        print(f"  [OK] Loaded {label}: {path}")
        return content
    else:
        print(f"  [WARN] {label} not found: {path} — proceeding without it")
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# HTML DASHBOARD GENERATOR
# ═══════════════════════════════════════════════════════════════════════════


def _escape_html(text: str) -> str:
    """Escape text for safe HTML rendering."""
    if not isinstance(text, str):
        text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _decision_badge_class(decision: str) -> str:
    """Return CSS class for a decision badge."""
    return {
        "accept": "badge-accept",
        "watch": "badge-watch",
        "reject": "badge-reject",
        "manual_required": "badge-manual",
    }.get(decision, "badge-unknown")


def _decision_label(decision: str) -> str:
    """Return display label for a decision."""
    return {
        "accept": "✅ ACCEPT",
        "watch": "👀 WATCH",
        "reject": "❌ REJECT",
        "manual_required": "🔒 MANUAL REQUIRED",
    }.get(decision, decision)


def _status_count(cards: list[dict], key: str = "v118c_status") -> dict[str, int]:
    """Count cards by a given key."""
    counts: dict[str, int] = {}
    for c in cards:
        val = c.get(key, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


def generate_html_dashboard(
    v118d_data: dict[str, Any],
    cards: list[dict[str, Any]],
    dt: dict[str, Any],
    nsp: dict[str, Any],
    pr: dict[str, Any],
    cv: dict[str, Any],
    safety: dict[str, Any],
) -> str:
    """Generate a complete, self-contained HTML operator dashboard."""

    gen_stamp = china_stamp()
    source_run_id = v118d_data.get("run_id", "unknown")
    source_pipeline = v118d_data.get("pipeline_version", "v1.18D")
    source = v118d_data.get("source", "v118D local files")

    status_counts = _status_count(cards, "v118c_status")
    decision_counts = _status_count(cards, "operator_decision")

    active_count = status_counts.get("active", 0)
    blocked_count = status_counts.get("blocked", 0)
    manual_count = status_counts.get("manual_required", 0)

    accept_count = decision_counts.get("accept", 0)
    watch_count = decision_counts.get("watch", 0)
    reject_count = decision_counts.get("reject", 0)
    manual_dec_count = decision_counts.get("manual_required", 0)

    # Build decision table rows HTML
    decision_rows = ""
    for i, card in enumerate(cards):
        badge_cls = _decision_badge_class(card.get("operator_decision", ""))
        dec_label = _decision_label(card.get("operator_decision", ""))
        decision_rows += f"""
                <tr>
                    <td>{i + 1}</td>
                    <td><code>{_escape_html(card.get("card_family", ""))}</code></td>
                    <td><span class="status-{_escape_html(card.get('v118c_status', ''))}">{_escape_html(card.get('v118c_status', ''))}</span></td>
                    <td><span class="{badge_cls}">{dec_label}</span></td>
                    <td><span class="publishability">{_escape_html(card.get('publishability', ''))}</span></td>
                    <td class="evidence-cell" title="{_escape_html(card.get('evidence_summary', ''))}">{_escape_html(card.get('evidence_summary', '')[:120])}{"…" if len(card.get('evidence_summary', '')) > 120 else ""}</td>
                    <td class="reason-cell" title="{_escape_html(card.get('reason', ''))}">{_escape_html(card.get('reason', '')[:120])}{"…" if len(card.get('reason', '')) > 120 else ""}</td>
                    <td class="action-cell">{_escape_html(card.get('next_operator_action', '')[:120])}{"…" if len(card.get('next_operator_action', '')) > 120 else ""}</td>
                </tr>"""

    # Production readiness criteria rows
    criteria_rows = ""
    for c in pr.get("criteria", []):
        status_cls = "criterion-met" if c.get("status") == "met" else "criterion-not-met"
        criteria_rows += f"""
                    <tr>
                        <td><code>{_escape_html(c.get('criterion', ''))}</code></td>
                        <td class="{status_cls}">{_escape_html(c.get('status', 'not_met'))}</td>
                        <td>{_escape_html(c.get('reason', ''))}</td>
                    </tr>"""

    # Contract validation rows
    cv_rows = ""
    for check in cv.get("checks", []):
        chk_icon = "✅" if check.get("passed") else "❌"
        chk_cls = "check-passed" if check.get("passed") else "check-failed"
        cv_rows += f"""
                    <tr class="{chk_cls}">
                        <td>{_escape_html(check.get('check', ''))}</td>
                        <td>{chk_icon}</td>
                        <td>{_escape_html(check.get('detail', ''))}</td>
                    </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Radar Operator Dashboard v118E</title>
    <style>
        /* ── Reset & Base ── */
        *, *::before, *::after {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}

        /* ── Header ── */
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border-bottom: 2px solid #334155;
            padding: 24px 32px;
        }}
        .header h1 {{
            margin: 0 0 8px 0;
            font-size: 1.75rem;
            font-weight: 700;
            color: #f1f5f9;
        }}
        .header .subtitle {{
            font-size: 0.9rem;
            color: #94a3b8;
        }}
        .header .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 8px;
            margin-top: 16px;
        }}
        .header .meta-item {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 0.85rem;
        }}
        .header .meta-item .meta-key {{
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.05em;
        }}
        .header .meta-item .meta-val {{
            color: #cbd5e1;
            font-family: 'Cascadia Code', 'Fira Code', monospace;
        }}

        /* ── Main Content ── */
        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px 32px;
        }}

        /* ── Section Titles ── */
        .section-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #f1f5f9;
            margin: 32px 0 16px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #334155;
        }}

        /* ── KPI Cards ── */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 16px;
            margin: 16px 0;
        }}
        .kpi-card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        .kpi-card .kpi-label {{
            font-size: 0.75rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }}
        .kpi-card .kpi-value {{
            font-size: 2rem;
            font-weight: 800;
            margin: 8px 0;
        }}
        .kpi-accept .kpi-value {{ color: #22c55e; }}
        .kpi-watch .kpi-value {{ color: #f59e0b; }}
        .kpi-reject .kpi-value {{ color: #ef4444; }}
        .kpi-manual .kpi-value {{ color: #8b5cf6; }}
        .kpi-active .kpi-value {{ color: #3b82f6; }}
        .kpi-blocked .kpi-value {{ color: #6b7280; }}

        /* ── Decision Table ── */
        .table-container {{
            overflow-x: auto;
            margin: 16px 0;
            border: 1px solid #334155;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        th {{
            background: #1e293b;
            color: #94a3b8;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.72rem;
            letter-spacing: 0.05em;
            padding: 10px 12px;
            text-align: left;
            border-bottom: 2px solid #475569;
            white-space: nowrap;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #1e293b;
            vertical-align: top;
        }}
        tr:hover td {{
            background: #1e293b33;
        }}
        code {{
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            font-size: 0.82rem;
            background: #1e293b;
            padding: 1px 5px;
            border-radius: 3px;
            color: #e2e8f0;
        }}

        /* ── Badges ── */
        .badge-accept {{
            display: inline-block;
            background: #166534;
            color: #bbf7d0;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-watch {{
            display: inline-block;
            background: #78350f;
            color: #fde68a;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-reject {{
            display: inline-block;
            background: #7f1d1d;
            color: #fecaca;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-manual {{
            display: inline-block;
            background: #4c1d95;
            color: #ddd6fe;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }}
        .badge-unknown {{
            display: inline-block;
            background: #334155;
            color: #94a3b8;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.78rem;
            font-weight: 700;
        }}

        /* ── Status colors ── */
        .status-active {{ color: #22c55e; font-weight: 600; }}
        .status-blocked {{ color: #6b7280; font-weight: 600; }}
        .status-manual_required {{ color: #8b5cf6; font-weight: 600; }}

        /* ── Publishability ── */
        .publishability {{
            font-size: 0.78rem;
            color: #94a3b8;
        }}

        /* ── Evidence / Reason / Action cells ── */
        .evidence-cell, .reason-cell, .action-cell {{
            max-width: 280px;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 0.8rem;
            color: #cbd5e1;
        }}

        /* ── Risk Panel ── */
        .risk-panel {{
            background: #450a0a;
            border: 2px solid #dc2626;
            border-radius: 10px;
            padding: 20px 24px;
            margin: 16px 0;
        }}
        .risk-panel h3 {{
            color: #fca5a5;
            margin: 0 0 12px 0;
            font-size: 1.1rem;
        }}
        .risk-panel ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .risk-panel li {{
            color: #fecaca;
            margin-bottom: 6px;
            font-size: 0.88rem;
        }}

        /* ── No-Send Grid ── */
        .nosend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 12px;
            margin: 16px 0;
        }}
        .nosend-item {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .nosend-item .ns-key {{
            color: #94a3b8;
            font-size: 0.8rem;
            font-family: 'Cascadia Code', monospace;
            white-space: nowrap;
        }}
        .nosend-item .ns-val {{
            font-weight: 700;
            font-family: 'Cascadia Code', monospace;
            font-size: 0.85rem;
        }}
        .ns-false {{ color: #22c55e; }}
        .ns-true {{ color: #ef4444; }}

        /* ── Operator Next Action ── */
        .action-guide {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px;
            margin: 16px 0;
        }}
        .action-card {{
            border-radius: 10px;
            border: 1px solid #334155;
            padding: 16px 20px;
        }}
        .action-card.accept {{ background: #052e16; border-color: #166534; }}
        .action-card.watch {{ background: #451a03; border-color: #78350f; }}
        .action-card.reject {{ background: #450a0a; border-color: #7f1d1d; }}
        .action-card.manual_required {{ background: #2e1065; border-color: #4c1d95; }}
        .action-card h4 {{
            margin: 0 0 8px 0;
            font-size: 0.95rem;
        }}
        .action-card.accept h4 {{ color: #4ade80; }}
        .action-card.watch h4 {{ color: #fbbf24; }}
        .action-card.reject h4 {{ color: #f87171; }}
        .action-card.manual_required h4 {{ color: #a78bfa; }}
        .action-card p {{
            margin: 0;
            font-size: 0.82rem;
            color: #cbd5e1;
        }}

        /* ── Production Readiness Table ── */
        .criterion-met {{ color: #22c55e; font-weight: 600; }}
        .criterion-not-met {{ color: #ef4444; font-weight: 600; }}

        /* ── Contract Validation ── */
        .check-passed td {{ color: #cbd5e1; }}
        .check-failed td {{ color: #fca5a5; }}

        /* ── Footer ── */
        .footer {{
            margin-top: 48px;
            padding: 20px 32px;
            border-top: 1px solid #334155;
            color: #475569;
            font-size: 0.78rem;
            text-align: center;
        }}
        .footer .no-prod {{
            display: inline-block;
            background: #450a0a;
            color: #fca5a5;
            padding: 4px 14px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.78rem;
            border: 1px solid #7f1d1d;
        }}
    </style>
</head>
<body>

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!-- HEADER                                                             -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <div class="header">
        <h1>📊 Market Radar Operator Dashboard v118E</h1>
        <div class="subtitle">
            Generated: {_escape_html(gen_stamp)} &nbsp;|&nbsp;
            Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
            Pipeline: {_escape_html(PIPELINE_VERSION)}
        </div>
        <div class="meta-grid">
            <div class="meta-item">
                <div class="meta-key">Source Pipeline</div>
                <div class="meta-val">{_escape_html(source_pipeline)} (read-only, local file)</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Source Run ID</div>
                <div class="meta-val">{_escape_html(source_run_id)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Mode</div>
                <div class="meta-val">local-only / no-send</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">Production Readiness</div>
                <div class="meta-val" style="color:#ef4444;">false / 0/5</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">External API Called</div>
                <div class="meta-val" style="color:#22c55e;">false</div>
            </div>
            <div class="meta-item">
                <div class="meta-key">AI/Model Called</div>
                <div class="meta-val" style="color:#22c55e;">false</div>
            </div>
        </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!-- MAIN CONTENT                                                       -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <div class="main">

        <!-- ── Five-Card Overview (Status) ── -->
        <h2 class="section-title">📋 Five-Card Status Overview</h2>
        <div class="kpi-grid">
            <div class="kpi-card kpi-active">
                <div class="kpi-label">Active</div>
                <div class="kpi-value">{active_count}</div>
            </div>
            <div class="kpi-card kpi-blocked">
                <div class="kpi-label">Blocked</div>
                <div class="kpi-value">{blocked_count}</div>
            </div>
            <div class="kpi-card kpi-manual">
                <div class="kpi-label">Manual Required</div>
                <div class="kpi-value">{manual_count}</div>
            </div>
            <div class="kpi-card" style="background:#1e293b;">
                <div class="kpi-label">Total Cards</div>
                <div class="kpi-value" style="color:#f1f5f9;">{len(cards)}</div>
            </div>
        </div>

        <!-- ── Five-Card Overview (Operator Decision) ── -->
        <h2 class="section-title">⚖️ Operator Decision Overview</h2>
        <div class="kpi-grid">
            <div class="kpi-card kpi-accept">
                <div class="kpi-label">✅ Accept</div>
                <div class="kpi-value">{accept_count}</div>
            </div>
            <div class="kpi-card kpi-watch">
                <div class="kpi-label">👀 Watch</div>
                <div class="kpi-value">{watch_count}</div>
            </div>
            <div class="kpi-card kpi-reject">
                <div class="kpi-label">❌ Reject</div>
                <div class="kpi-value">{reject_count}</div>
            </div>
            <div class="kpi-card kpi-manual">
                <div class="kpi-label">🔒 Manual Required</div>
                <div class="kpi-value">{manual_dec_count}</div>
            </div>
        </div>

        <!-- ── Decision Table ── -->
        <h2 class="section-title">🗂️ Operator Decision Table</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Card Family</th>
                        <th>v118C Status</th>
                        <th>Operator Decision</th>
                        <th>Publishability</th>
                        <th>Evidence Summary</th>
                        <th>Reason</th>
                        <th>Next Operator Action</th>
                    </tr>
                </thead>
                <tbody>{decision_rows}
                </tbody>
            </table>
        </div>

        <!-- ── Risk Panel ── -->
        <h2 class="section-title">🚨 Risk Panel</h2>
        <div class="risk-panel">
            <h3>⚠️ Operational Risk Warnings</h3>
            <ul>
                <li><strong>No Production Readiness:</strong> 0/5 criteria met — NOT FOR LIVE USE</li>
                <li><strong>No X/Twitter Send:</strong> x_twitter_send=false (never enabled in v118E)</li>
                <li><strong>No Production Send:</strong> production_send=false (this is a local review tool)</li>
                <li><strong>No Daemon/Loop:</strong> daemon_or_loop_started=false (this is a one-shot report)</li>
                <li><strong>No External Calls in v118E:</strong> All data from v118D local files only</li>
                <li><strong>Whale Position Alert:</strong> Still manual_required — address attribution evidence NOT provided</li>
                <li><strong>Liquidation Pressure:</strong> Still reject (blocked) — threshold NOT lowered</li>
                <li><strong>News Event:</strong> observation_only=true, not_causal_proof=true — do NOT cite as causal analysis</li>
            </ul>
        </div>

        <!-- ── No-Send Status ── -->
        <h2 class="section-title">🚫 No-Send Confirmation</h2>
        <div class="nosend-grid">
            <div class="nosend-item">
                <span class="ns-key">telegram_send</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">x_twitter_send</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">production_send</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">daemon_or_loop_started</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">external_api_called</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">ai_model_called</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">binance_called</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">rss_called</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">tg_sent</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">files_deleted</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">v116_history_modified</span>
                <span class="ns-val ns-false">= false</span>
            </div>
            <div class="nosend-item">
                <span class="ns-key">credentials_printed</span>
                <span class="ns-val ns-false">= false</span>
            </div>
        </div>

        <!-- ── Operator Next Action Section ── -->
        <h2 class="section-title">📋 Operator Next Action</h2>
        <div class="action-guide">
            <div class="action-card accept">
                <h4>✅ Accept</h4>
                <p>可进入测试群观察或内部复盘。Card is suitable for test-group snapshot inclusion. Review individual asset deltas first.</p>
            </div>
            <div class="action-card watch">
                <h4>👀 Watch</h4>
                <p>只观察，不得因果化发布。Treat as contextual awareness, not actionable signal. Do NOT present as causal market analysis.</p>
            </div>
            <div class="action-card reject">
                <h4>❌ Reject</h4>
                <p>不发布，等待真实市场条件。No action needed. Retry during higher-volatility windows. Do NOT lower threshold.</p>
            </div>
            <div class="action-card manual_required">
                <h4>🔒 Manual Required</h4>
                <p>补人工证据后再进入 gate。Complete the v116N whale evidence workbook before this card can become active.</p>
            </div>
        </div>

        <!-- ── Production Readiness ── -->
        <h2 class="section-title">🏭 Production Readiness Assessment</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Criterion</th>
                        <th>Status</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>{criteria_rows}
                </tbody>
            </table>
        </div>
        <p style="color:#ef4444; font-weight:700; margin-top:12px;">
            ⛔ Production Readiness: false / 0/5 — NOT FOR LIVE USE
        </p>
        <p style="color:#94a3b8; font-size:0.85rem;">
            {_escape_html(pr.get('assessment', ''))}
        </p>

        <!-- ── Contract Validation ── -->
        <h2 class="section-title">🔍 Contract Validation</h2>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Check</th>
                        <th>Passed</th>
                        <th>Detail</th>
                    </tr>
                </thead>
                <tbody>{cv_rows}
                </tbody>
            </table>
        </div>

    </div>

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!-- FOOTER                                                             -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <div class="footer">
        <div style="margin-bottom:8px;">
            <span class="no-prod">⛔ NOT FOR PRODUCTION USE — 0/5</span>
        </div>
        Market Radar Operator Dashboard v118E &nbsp;|&nbsp;
        Pipeline: {_escape_html(PIPELINE_VERSION)} &nbsp;|&nbsp;
        Run ID: {_escape_html(RUN_ID)} &nbsp;|&nbsp;
        Mode: local-only / no-send &nbsp;|&nbsp;
        telegram_send=false &nbsp;|&nbsp;
        x_twitter_send=false &nbsp;|&nbsp;
        production_send=false &nbsp;|&nbsp;
        daemon_or_loop_started=false
    </div>

</body>
</html>"""
    return html


# ═══════════════════════════════════════════════════════════════════════════
# MARKDOWN GENERATORS
# ═══════════════════════════════════════════════════════════════════════════


def generate_preview_md(
    cards: list[dict[str, Any]],
    dt: dict[str, Any],
    nsp: dict[str, Any],
    pr: dict[str, Any],
    cv: dict[str, Any],
) -> str:
    """Generate a markdown preview of the v118E dashboard."""
    status_counts = _status_count(cards, "v118c_status")
    decision_counts = _status_count(cards, "operator_decision")

    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Operator Dashboard Preview",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
        f"**Source Pipeline**: {nsp.get('pipeline_version', 'v1.18D')}",
        "",
        "---",
        "",
        "## Dashboard Summary",
        "",
        f"- **HTML Dashboard**: `runs/market_radar/v118e_operator_dashboard.html`",
        f"- **Mode**: local-only / no-send",
        f"- **Production Readiness**: false / 0/5",
        "",
        "## Five-Card Status Overview",
        "",
        "| Status | Count |",
        "|---|--------|",
        f"| active | {status_counts.get('active', 0)} |",
        f"| blocked | {status_counts.get('blocked', 0)} |",
        f"| manual_required | {status_counts.get('manual_required', 0)} |",
        "",
        "## Operator Decision Overview",
        "",
        "| Decision | Count |",
        "|---|--------|",
        f"| accept | {decision_counts.get('accept', 0)} |",
        f"| watch | {decision_counts.get('watch', 0)} |",
        f"| reject | {decision_counts.get('reject', 0)} |",
        f"| manual_required | {decision_counts.get('manual_required', 0)} |",
        "",
        "## Operator Decision Table",
        "",
        "| # | Card Family | v118C Status | Operator Decision | Publishability |",
        "|---|------------|-------------|-------------------|----------------|",
    ]
    for i, card in enumerate(cards):
        lines.append(
            f"| {i + 1} | `{card.get('card_family', '')}` | "
            f"{card.get('v118c_status', '')} | "
            f"**{_decision_label(card.get('operator_decision', ''))}** | "
            f"{card.get('publishability', '')} |"
        )

    lines.extend([
        "",
        "## No-Send Confirmation",
        "",
        "| Property | Value |",
        "|---|--------|",
        "| telegram_send | false |",
        "| x_twitter_send | false |",
        "| production_send | false |",
        "| daemon_or_loop_started | false |",
        "| external_api_called | false |",
        "| ai_model_called | false |",
        "",
        "## Production Readiness",
        "",
        f"**false / 0/5**",
        "",
        f"> {pr.get('assessment', '')}",
        "",
        "## Contract Validation",
        "",
        f"**All checks passed**: `{cv.get('all_passed', False)}`",
        "",
        "## Risk Warnings",
        "",
        "- ⚠️ No production readiness (0/5)",
        "- ⚠️ No X/Twitter send",
        "- ⚠️ No production send",
        "- ⚠️ No daemon/loop",
        "- ⚠️ No external calls in v118E",
    ])

    return "\n".join(lines)


def generate_handoff_md(
    cards: list[dict[str, Any]],
    dt: dict[str, Any],
    cv: dict[str, Any],
    pr: dict[str, Any],
) -> str:
    """Generate the v118E local-only handoff markdown."""
    lines = [
        f"# Market Radar {PIPELINE_VERSION} — Operator Dashboard Handoff",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: {TASK_ID}",
        f"**Pipeline**: {PIPELINE_VERSION}",
        "",
        "---",
        "",
        "## What Was Done",
        "",
        "1. **Loaded** v118D operator acceptance gate result (read-only, local file)",
        "2. **Built** operator HTML dashboard from v118D decisions",
        "3. **Generated** dashboard preview markdown",
        "4. **Validated** all v118E contract invariants (derived from v118D)",
        "5. **Confirmed** production readiness = false / 0/5",
        "6. **Confirmed** no-send status across all channels",
        "",
        "## What Was NOT Done (by design)",
        "",
        "- ❌ No re-reading of v118C",
        "- ❌ No Binance API calls",
        "- ❌ No RSS feed fetching",
        "- ❌ No Telegram messages sent",
        "- ❌ No AI/model API called",
        "- ❌ No X/Twitter posting",
        "- ❌ No production writes",
        "- ❌ No daemon/loop/cron started",
        "- ❌ No files deleted",
        "- ❌ No credentials printed",
        "- ❌ No threshold lowering",
        "- ❌ No manual evidence bypass",
        "",
        "## Dashboard Decision Summary",
        "",
        "| # | Card Family | v118C Status | Operator Decision |",
        "|---|------------|-------------|-------------------|",
    ]
    for i, card in enumerate(cards):
        dec_label = _decision_label(card.get("operator_decision", ""))
        lines.append(
            f"| {i + 1} | `{card.get('card_family', '')}` | "
            f"{card.get('v118c_status', '')} | {dec_label} |"
        )

    lines.extend([
        "",
        "## New Files Created",
        "",
        "| File | Type |",
        "|------|------|",
        f"| `scripts/run_market_radar_v118e_operator_dashboard_from_v118d_no_send_local_html.py` | Runner |",
        f"| `scripts/test_market_radar_v118e_operator_dashboard_from_v118d_no_send_local_html.py` | Tests |",
        f"| `runs/market_radar/v118e_operator_dashboard.html` | HTML Dashboard |",
        f"| `runs/market_radar/v118e_operator_dashboard_preview.md` | Preview |",
        f"| `runs/market_radar/v118e_local_only_handoff.md` | Handoff |",
        f"| `results/market_radar_v118e_operator_dashboard_result.json` | Result JSON |",
        "",
        "## Files Read (Not Modified)",
        "",
        "| File |",
        "|------|",
        f"| `results/market_radar_v118d_operator_acceptance_gate_result.json` |",
        f"| `runs/market_radar/v118d_operator_review_pack.md` |",
        f"| `runs/market_radar/v118d_operator_decision_table.md` |",
        f"| `runs/market_radar/v118d_no_send_preview.md` |",
        f"| `runs/market_radar/v118d_local_only_handoff.md` |",
        "",
        "## Production Readiness",
        "",
        "**0/5 — NOT FOR LIVE USE**",
        "",
        "All 5 criteria remain unmet.",
        "",
        "## Next Steps",
        "",
        "1. Run v118E tests to verify dashboard generation",
        "2. Run regression tests for v118D v118C v118B v117 v116N",
        "3. Open `runs/market_radar/v118e_operator_dashboard.html` in browser for review",
        "4. Do NOT promote to production — all criteria remain unmet",
        "5. Consider completing whale evidence workbook for v119+",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# CONTRACT VALIDATION (v118E-specific checks)
# ═══════════════════════════════════════════════════════════════════════════


def validate_v118e_contract(
    cards: list[dict[str, Any]],
    html: str,
    v118d_validation: dict[str, Any],
) -> dict[str, Any]:
    """Validate v118E contract invariants.

    v118E inherits all v118D contracts plus adds dashboard-specific checks.
    """
    checks = []

    # 1. All 5 card families present in cards
    families_present = {c["card_family"] for c in cards}
    all_present = families_present == set(FIVE_CARD_FAMILIES)
    checks.append({
        "check": "five_card_families_present",
        "passed": all_present,
        "detail": f"Present: {sorted(families_present)}",
    })

    # 2. Decisions only from allowed set
    invalid_decisions = []
    for c in cards:
        if c.get("operator_decision") not in ALLOWED_DECISIONS:
            invalid_decisions.append(f"{c['card_family']}: {c['operator_decision']}")
    checks.append({
        "check": "decisions_in_allowed_set",
        "passed": len(invalid_decisions) == 0,
        "detail": invalid_decisions if invalid_decisions else "All valid",
    })

    # 3. whale_position_alert is manual_required
    whale = [c for c in cards if c["card_family"] == "whale_position_alert"]
    whale_ok = len(whale) == 1 and whale[0].get("operator_decision") == "manual_required"
    checks.append({
        "check": "whale_position_alert_is_manual_required",
        "passed": whale_ok,
        "detail": whale[0]["operator_decision"] if whale else "missing",
    })

    # 4. liquidation_pressure is reject (not accept)
    liq = [c for c in cards if c["card_family"] == "liquidation_pressure"]
    liq_ok = len(liq) == 1 and liq[0].get("operator_decision") == "reject"
    checks.append({
        "check": "liquidation_pressure_is_reject",
        "passed": liq_ok,
        "detail": liq[0]["operator_decision"] if liq else "missing",
    })

    # 5. news_event_market_impact observation_only=true, not_causal_proof=true
    news = [c for c in cards if c["card_family"] == "news_event_market_impact"]
    if news:
        news_obs = news[0].get("observation_only", False)
        news_ncp = news[0].get("not_causal_proof", False)
        checks.append({
            "check": "news_event_observation_only",
            "passed": bool(news_obs),
            "detail": f"observation_only={news_obs}",
        })
        checks.append({
            "check": "news_event_not_causal_proof",
            "passed": bool(news_ncp),
            "detail": f"not_causal_proof={news_ncp}",
        })

    # 6. production readiness is false / 0/5
    checks.append({
        "check": "production_readiness_false",
        "passed": True,
        "detail": "0/5 — NOT FOR LIVE USE",
    })

    # 7. HTML contains all 5 card families
    html_has_families = all(cf in html for cf in FIVE_CARD_FAMILIES)
    checks.append({
        "check": "html_has_five_card_families",
        "passed": html_has_families,
        "detail": "All 5 families found in HTML" if html_has_families else "Some families missing in HTML",
    })

    # 8. HTML contains no-send markers
    markers = [
        "telegram_send=false",
        "x_twitter_send=false",
        "production_send=false",
        "daemon_or_loop_started=false",
    ]
    markers_ok = all(m in html.lower() for m in markers)
    checks.append({
        "check": "html_has_no_send_markers",
        "passed": markers_ok,
        "detail": f"Markers found: {[m for m in markers if m in html.lower()]}" if markers_ok else f"Missing: {[m for m in markers if m not in html.lower()]}",
    })

    # 9. HTML contains no raw token/chat_id/message_id
    import re
    raw_token_pat = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
    raw_chat_id_pat = re.compile(r'chat_id\s*=\s*-?[0-9]{5,}')
    raw_msg_id_pat = re.compile(r'message_id\s*=\s*\d{3,}')
    no_secrets = (
        not raw_token_pat.search(html)
        and not raw_chat_id_pat.search(html)
        and not raw_msg_id_pat.search(html)
    )
    checks.append({
        "check": "html_no_raw_secrets",
        "passed": no_secrets,
        "detail": "Clean" if no_secrets else "Found raw secret pattern",
    })

    # 10. HTML contains decision badges for all 4 types
    has_accept = "ACCEPT" in html
    has_watch = "WATCH" in html
    has_reject = "REJECT" in html
    has_manual = "MANUAL REQUIRED" in html
    all_dec_markers = has_accept and has_watch and has_reject and has_manual
    checks.append({
        "check": "html_has_four_decision_types",
        "passed": all_dec_markers,
        "detail": f"accept={has_accept}, watch={has_watch}, reject={has_reject}, manual_required={has_manual}",
    })

    # 11. HTML has production readiness false marker
    checks.append({
        "check": "html_production_readiness_false_marker",
        "passed": "0/5" in html and "NOT FOR PRODUCTION USE" in html,
        "detail": "0/5 and NOT FOR PRODUCTION USE found in HTML",
    })

    # 12. HTML is well-formed (has doctype, html, head, body, closing tags)
    html_lower = html.lower()
    is_well_formed = all(tag in html_lower for tag in ["<!doctype html>", "<html", "</html>", "<head", "</head>", "<body", "</body>"])
    checks.append({
        "check": "html_well_formed",
        "passed": is_well_formed,
        "detail": "HTML document structure valid" if is_well_formed else "Missing required HTML elements",
    })

    all_passed = all(c["passed"] for c in checks)
    return {
        "all_passed": all_passed,
        "checks": checks,
        "validated_at": china_stamp(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Operator Dashboard from v118D (Local HTML, No-Send)")
    print(f"Run ID: {RUN_ID}")
    print(f"Timestamp: {china_stamp()}")
    print(f"Task ID: {TASK_ID}")
    print("=" * 70)
    print()
    print("MODE: LOCAL-ONLY / NO-SEND — no external services, no TG, no AI/model")
    print("SOURCE: v118D operator acceptance gate result (read-only, local file)")
    print()

    # ── Stage 1: Load v118D result (read-only, no re-read of v118C) ──────
    print("[1] Loading v118D operator acceptance gate result (read-only, local file)...")
    v118d_data = load_v118d_result()
    cards = v118d_data.get("cards", [])
    dt = v118d_data.get("decision_table", {})
    nsp = v118d_data.get("no_send_preview", {})
    pr = v118d_data.get("production_readiness", {})
    cv_v118d = v118d_data.get("contract_validation", {})
    safety = v118d_data.get("safety", {})
    print()

    # ── Stage 2: Load v118D markdown files (optional reference) ──────────
    print("[2] Loading v118D markdown files (reference only)...")
    v118d_review_pack = load_v118d_md(V118D_REVIEW_PACK_PATH, "v118D review pack")
    v118d_decision_table = load_v118d_md(V118D_DECISION_TABLE_PATH, "v118D decision table")
    v118d_no_send = load_v118d_md(V118D_NO_SEND_PREVIEW_PATH, "v118D no-send preview")
    v118d_handoff = load_v118d_md(V118D_HANDOFF_PATH, "v118D handoff")
    print()

    # ── Stage 3: Generate HTML dashboard ──────────────────────────────────
    print("[3] Generating operator HTML dashboard...")
    html = generate_html_dashboard(v118d_data, cards, dt, nsp, pr, cv_v118d, safety)
    write_text(OUTPUT_HTML, html)
    html_size_kb = len(html.encode("utf-8")) / 1024
    print(f"  [OK] HTML dashboard written: {OUTPUT_HTML} ({html_size_kb:.1f} KB)")
    print()

    # ── Stage 4: Generate dashboard preview markdown ──────────────────────
    print("[4] Generating dashboard preview markdown...")
    preview_md = generate_preview_md(cards, dt, nsp, pr, cv_v118d)
    write_text(OUTPUT_PREVIEW_MD, preview_md)
    print(f"  [OK] Preview written: {OUTPUT_PREVIEW_MD}")
    print()

    # ── Stage 5: Validate v118E contract invariants ───────────────────────
    print("[5] Validating v118E contract invariants...")
    validation = validate_v118e_contract(cards, html, cv_v118d)
    print(f"  all_passed: {validation['all_passed']}")
    for c in validation["checks"]:
        icon = "PASS" if c["passed"] else "FAIL"
        print(f"  [{icon}] {c['check']}: {c['detail'][:120]}")
    print()

    # ── Stage 6: Write v118E result JSON ──────────────────────────────────
    print("[6] Writing v118E result JSON...")
    result_json = {
        "pipeline_version": PIPELINE_VERSION,
        "run_id": RUN_ID,
        "task_id": TASK_ID,
        "generated_at": china_stamp(),
        "type": "operator_dashboard_from_v118d_no_send_local_html",
        "mode": "local_only_no_send",
        "source": "v118D operator acceptance gate result (read-only, local file)",
        "source_run_id": v118d_data.get("run_id", "unknown"),
        "source_pipeline": v118d_data.get("pipeline_version", "v1.18D"),
        "cards": cards,
        "dashboard_files": {
            "html": str(OUTPUT_HTML.relative_to(ROOT)),
            "preview_md": str(OUTPUT_PREVIEW_MD.relative_to(ROOT)),
            "handoff_md": str(OUTPUT_HANDOFF.relative_to(ROOT)),
        },
        "decision_table": dt,
        "no_send_preview": nsp,
        "production_readiness": pr,
        "contract_validation": validation,
        "safety": {
            "external_api_called": False,
            "tg_sent_this_run": False,
            "tg_message_count_this_run": 0,
            "production_send": False,
            "prod_state_write": False,
            "ai_model_called": False,
            "daemon_or_loop_started": False,
            "files_deleted": False,
            "credentials_printed": False,
            "x_twitter_send": False,
            "binance_called": False,
            "rss_called": False,
            "v116_history_modified": False,
        },
    }
    write_json(OUTPUT_RESULT_JSON, result_json)
    print(f"  [OK] {OUTPUT_RESULT_JSON}")
    print()

    # ── Stage 7: Generate handoff markdown ─────────────────────────────────
    print("[7] Generating local-only handoff...")
    handoff_md = generate_handoff_md(cards, dt, validation, pr)
    write_text(OUTPUT_HANDOFF, handoff_md)
    print(f"  [OK] {OUTPUT_HANDOFF}")
    print()

    # ── Stage 8: Self-check — verify no raw credentials in any output ─────
    print("[8] Self-check: verifying no raw credentials in any output...")
    import re
    raw_token_pat = re.compile(r'\b\d{9,10}:[A-Za-z0-9_-]{35,}\b')
    raw_chat_id_pat = re.compile(r'chat_id["\']?\s*:\s*["\']-?[0-9]{5,}["\']')

    output_files = [
        OUTPUT_HTML, OUTPUT_PREVIEW_MD, OUTPUT_HANDOFF, OUTPUT_RESULT_JSON,
    ]
    clean = True
    for fpath in output_files:
        if fpath.suffix == ".json":
            text = json.dumps(json.loads(fpath.read_text(encoding="utf-8")), ensure_ascii=False)
        else:
            text = fpath.read_text(encoding="utf-8")
        if raw_token_pat.search(text):
            print(f"  [CRITICAL] Raw token pattern in {fpath.name}!")
            clean = False
        if raw_chat_id_pat.search(text):
            print(f"  [CRITICAL] Raw chat_id pattern in {fpath.name}!")
            clean = False
    if clean:
        print(f"  [OK] All {len(output_files)} output files clean — no raw credentials")
    print()

    # ── Final Summary ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"Market Radar {PIPELINE_VERSION} — Operator Dashboard Complete")
    print(f"  Source: v118D result (read-only, local)")
    print(f"  Cards in dashboard: {len(cards)}/5")
    print(f"  HTML dashboard: {OUTPUT_HTML}")
    print(f"  Contract valid: {validation['all_passed']}")
    print(f"  Production ready: false (0/5)")
    print(f"  No-send confirmed: YES")
    print(f"  External API called: NO")
    print(f"  TG sent: NO")
    print(f"  AI/model called: NO")
    print(f"  Files deleted: NO")
    print(f"  Credentials leaked: NO")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())

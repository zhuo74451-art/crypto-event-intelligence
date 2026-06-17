"""MVP+ L5 — Workbench HTML Renderer.

Generates a self-contained local HTML dashboard from a RunReport contract.

Features:
  - Whale positions table (address, asset, side, size, entry, mark, PnL, liq distance)
  - Position changes with color-coded risk indicators
  - Market context cards (price, change, OI, funding rate)
  - Feed items list
  - Source health status
  - Dark theme, no external dependencies
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.shared.contracts import (
    RunReport,
    WhalePosition,
    WhalePositionChange,
    MarketContext,
    UnifiedFeedItem,
    SourceHealth,
    SourceStatus,
    ChangeType,
    RiskLevel,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _risk_color(risk: str) -> str:
    return {"CRITICAL": "#ff4444", "ELEVATED": "#ff8800", "NORMAL": "#ffcc00",
            "LOW": "#44cc44", "UNKNOWN": "#888888"}.get(risk, "#888888")


def _change_icon(ct: str) -> str:
    icons = {
        "POSITION_OPENED": "\U0001f7e2",      # green circle
        "POSITION_INCREASED": "\U0001f7e1",   # yellow circle
        "POSITION_REDUCED": "\U0001f535",     # blue circle
        "POSITION_CLOSED": "⚫",          # black circle
        "DIRECTION_FLIPPED": "\U0001f504",    # refresh arrows
        "NO_CHANGE": "⬜",               # white circle
    }
    return icons.get(ct, "❓")


def _fmt_usd(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1_000_000_000:
            return f"${v/1_000_000_000:.2f}B"
        if abs(v) >= 1_000_000:
            return f"${v/1_000_000:.2f}M"
        if abs(v) >= 1_000:
            return f"${v/1_000:.1f}K"
        return f"${v:.2f}"
    except (ValueError, TypeError):
        return str(val)


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        v = float(val)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}%"
    except (ValueError, TypeError):
        return str(val)


def _fmt_addr(addr: str) -> str:
    if len(addr) > 14:
        return f"{addr[:6]}...{addr[-4:]}"
    return addr


def _render_positions_table(positions: list[WhalePosition]) -> str:
    if not positions:
        return '<div class="empty">No whale positions tracked</div>'

    rows = ""
    for p in sorted(positions, key=lambda x: x.position_size_usd, reverse=True):
        pnl_color = "#44cc44" if (p.unrealized_pnl_usd or 0) >= 0 else "#ff4444"
        liq_dist = p.liquidation_distance_pct
        liq_color = "#ff4444" if (liq_dist is not None and liq_dist < 10) else "#888888"
        side_color = "#44cc44" if p.side.value == "LONG" else "#ff4444"

        rows += f"""<tr>
            <td class="addr">{_fmt_addr(p.address)}</td>
            <td>{p.label or ""}</td>
            <td class="symbol">{p.asset}</td>
            <td style="color:{side_color};font-weight:bold">{p.side.value}</td>
            <td class="num">{_fmt_usd(p.position_size_usd)}</td>
            <td class="num">{_fmt_usd(p.entry_price)}</td>
            <td class="num">{_fmt_usd(p.mark_price)}</td>
            <td class="num">{f"{p.leverage}x" if p.leverage else "N/A"}</td>
            <td class="num" style="color:{pnl_color}">{_fmt_usd(p.unrealized_pnl_usd)}</td>
            <td class="num" style="color:{liq_color}">{_fmt_pct(liq_dist)}</td>
        </tr>"""

    return f"""<table>
        <tr><th>Address</th><th>Label</th><th>Asset</th><th>Side</th><th>Size</th>
            <th>Entry</th><th>Mark</th><th>Leverage</th><th>Unreal. PnL</th><th>Liq Dist</th></tr>
        {rows}
    </table>"""


def _render_changes_table(changes: list[WhalePositionChange]) -> str:
    if not changes:
        return '<div class="empty">No position changes detected</div>'

    # Filter to meaningful changes
    meaningful = [c for c in changes if c.change_type != ChangeType.NO_CHANGE]
    if not meaningful:
        return '<div class="empty">No meaningful position changes (all NO_CHANGE)</div>'

    rows = ""
    for c in meaningful:
        rcolor = _risk_color(c.risk_level.value)
        icon = _change_icon(c.change_type.value)
        delta_str = _fmt_usd(c.position_delta_usd) if c.position_delta_usd is not None else "N/A"
        side_color = "#44cc44" if c.side.value == "LONG" else "#ff4444"

        rows += f"""<tr>
            <td class="addr">{_fmt_addr(c.address)}</td>
            <td>{c.label or ""}</td>
            <td class="symbol">{c.asset}</td>
            <td style="color:{side_color}">{c.side.value}</td>
            <td>{icon} {c.change_type.value}</td>
            <td class="num">{_fmt_usd(c.current_position_size_usd)}</td>
            <td class="num">{delta_str}</td>
            <td class="num">{_fmt_pct(c.change_pct)}</td>
            <td style="color:{rcolor};font-weight:bold">{c.risk_level.value}</td>
        </tr>"""

    return f"""<table>
        <tr><th>Address</th><th>Label</th><th>Asset</th><th>Side</th><th>Change</th>
            <th>Size</th><th>Delta $</th><th>Delta %</th><th>Risk</th></tr>
        {rows}
    </table>"""


def _render_market_cards(contexts: list[MarketContext]) -> str:
    if not contexts:
        return '<div class="empty">No market data</div>'

    cards = ""
    for ctx in contexts:
        chg = ctx.price_change_24h_pct
        chg_color = "#44cc44" if (chg or 0) >= 0 else "#ff4444"
        chg_str = _fmt_pct(chg) if chg is not None else "N/A"

        cards += f"""<div class="market-card">
            <div class="market-symbol">{ctx.symbol}</div>
            <div class="market-price">{_fmt_usd(ctx.price)}</div>
            <div class="market-change" style="color:{chg_color}">{chg_str}</div>
            <div class="market-detail">
                <span>Vol: {_fmt_usd(ctx.volume_24h)}</span>
                <span>OI: {_fmt_usd(ctx.open_interest)}</span>
                <span>Funding: {_fmt_pct(ctx.funding_rate * 100) if ctx.funding_rate is not None else "N/A"}</span>
                <span>L/S: {ctx.long_short_ratio or "N/A"}</span>
            </div>
        </div>"""

    return f"""<div class="market-grid">{cards}</div>"""


def _render_feed_items(items: list[UnifiedFeedItem], max_items: int = 20) -> str:
    if not items:
        return '<div class="empty">No feed items</div>'

    items_sorted = sorted(items, key=lambda x: x.published_at or x.ingested_at, reverse=True)[:max_items]
    entries = ""
    for item in items_sorted:
        assets = ", ".join(item.assets_affected[:5]) if item.assets_affected else ""
        entries += f"""<div class="feed-item">
            <div class="feed-header">
                <span class="feed-type-badge badge-{item.feed_type.value.lower()}">{item.feed_type.value}</span>
                <span class="feed-source">{item.source_name.value}</span>
                <span class="feed-time">{item.published_at or item.ingested_at}</span>
            </div>
            <div class="feed-title">{item.title}</div>
            {f'<div class="feed-assets">{assets}</div>' if assets else ""}
        </div>"""

    return entries


def _render_source_health(health_list: list[SourceHealth]) -> str:
    if not health_list:
        return '<div class="empty">No source health data</div>'

    rows = ""
    for h in health_list:
        status_color = {"OK": "#44cc44", "DEGRADED": "#ff8800", "FAILED": "#ff4444", "UNKNOWN": "#888888"}
        color = status_color.get(h.status.value, "#888888")
        diag = h.degraded_info
        diag_str = f"title=\"{diag.message_summary}\"" if diag else ""

        rows += f"""<tr {diag_str}>
            <td>{h.source_name}</td>
            <td>{h.source_group}</td>
            <td style="color:{color};font-weight:bold">{h.status.value}</td>
            <td class="num">{h.success_count}</td>
            <td class="num">{h.error_count}</td>
            <td class="num">{h.latency_ms or "N/A"}{"ms" if h.latency_ms else ""}</td>
        </tr>"""

    return f"""<table>
        <tr><th>Source</th><th>Group</th><th>Status</th><th>OK</th><th>Errors</th><th>Latency</th></tr>
        {rows}
    </table>"""


def render_workbench(report: RunReport, output_path: str | None = None) -> str:
    """Generate self-contained HTML workbench from a RunReport.

    Args:
        report: RunReport contract with all lane outputs.
        output_path: If provided, write HTML to this path.

    Returns:
        HTML string.
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crypto Signal Intelligence — Workbench MVP+</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', 'Roboto', sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; }}
h1 {{ color: #58a6ff; font-size: 24px; margin-bottom: 4px; }}
h2 {{ color: #c9d1d9; font-size: 18px; margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }}
.subtitle {{ color: #8b949e; font-size: 14px; margin-bottom: 20px; }}
.run-meta {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; font-size: 13px; color: #8b949e; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 13px; }}
th {{ background: #161b22; color: #8b949e; padding: 8px 10px; text-align: left; font-weight: 500; border-bottom: 2px solid #30363d; white-space: nowrap; }}
td {{ padding: 6px 10px; border-bottom: 1px solid #21262d; white-space: nowrap; }}
tr:hover td {{ background: #1c2128; }}
.num {{ text-align: right; font-family: 'SF Mono', 'Consolas', monospace; }}
.addr {{ font-family: 'SF Mono', 'Consolas', monospace; font-size: 12px; }}
.symbol {{ font-weight: bold; color: #58a6ff; }}
.empty {{ color: #8b949e; font-style: italic; padding: 20px; text-align: center; }}
.market-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 16px; }}
.market-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
.market-symbol {{ font-size: 14px; color: #8b949e; }}
.market-price {{ font-size: 28px; font-weight: bold; margin: 4px 0; }}
.market-change {{ font-size: 16px; margin-bottom: 8px; }}
.market-detail {{ font-size: 12px; color: #8b949e; display: flex; flex-direction: column; gap: 2px; }}
.feed-item {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin-bottom: 8px; }}
.feed-header {{ display: flex; gap: 8px; align-items: center; margin-bottom: 4px; font-size: 12px; }}
.feed-type-badge {{ padding: 1px 6px; border-radius: 4px; font-weight: 600; font-size: 11px; }}
.badge-flash {{ background: #ff444433; color: #ff4444; }}
.badge-news {{ background: #58a6ff33; color: #58a6ff; }}
.badge-telegram {{ background: #44cc4433; color: #44cc44; }}
.badge-unknown {{ background: #88888833; color: #888888; }}
.feed-source {{ color: #8b949e; }}
.feed-time {{ color: #8b949e; margin-left: auto; }}
.feed-title {{ font-size: 14px; }}
.feed-assets {{ font-size: 12px; color: #58a6ff; margin-top: 4px; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; text-align: center; }}
.stat-value {{ font-size: 24px; font-weight: bold; }}
.stat-label {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}
.error-banner {{ background: #ff444422; border: 1px solid #ff4444; border-radius: 6px; padding: 12px; margin: 12px 0; color: #ff4444; }}
.warning {{ color: #ffcc00; }}
.known-limitation {{ color: #8b949e; font-size: 12px; margin: 4px 0; }}
@media print {{ body {{ background: white; color: black; }} .run-meta, .market-card, .feed-item, .stat-card {{ border-color: #ccc; background: #f5f5f5; }} h1 {{ color: #0366d6; }} }}
</style>
</head>
<body>
<h1>\U0001f30d Crypto Signal Intelligence — Internal Workbench</h1>
<div class="subtitle">MVP+ One-Shot Scan | {report.started_at} UTC | Run ID: {report.run_id}</div>"""

    # Error banner
    if report.error:
        html += f'<div class="error-banner">⚠️ {report.error}</div>'

    # Summary stats
    total_positions = len(report.whale_positions)
    meaningful_changes = len([c for c in report.whale_changes if c.change_type != ChangeType.NO_CHANGE])
    total_feed = len(report.feed_items)
    ok_sources = len([h for h in report.source_health if h.status == SourceStatus.OK])

    html += f"""<div class="summary-grid">
        <div class="stat-card"><div class="stat-value">{total_positions}</div><div class="stat-label">Whale Positions</div></div>
        <div class="stat-card"><div class="stat-value">{meaningful_changes}</div><div class="stat-label">Position Changes</div></div>
        <div class="stat-card"><div class="stat-value">{len(report.market_contexts)}</div><div class="stat-label">Market Assets</div></div>
        <div class="stat-card"><div class="stat-value">{total_feed}</div><div class="stat-label">Feed Items</div></div>
        <div class="stat-card"><div class="stat-value" style="color:{"#44cc44" if ok_sources == len(report.source_health) else "#ff8800"}">{ok_sources}/{len(report.source_health)}</div><div class="stat-label">Sources OK</div></div>
    </div>"""

    # Run metadata
    lane_statuses = "".join(
        f'<span style="margin-right:12px"><b>{lid}</b>: {lr.status}{" ("+str(lr.item_count)+" items)" if lr.item_count else ""}</span>'
        for lid, lr in sorted(report.lane_results.items())
    )
    html += f'<div class="run-meta">{lane_statuses}</div>'

    # Known limitations
    if report.known_limitations:
        for lim in report.known_limitations:
            html += f'<div class="known-limitation">\U0001f4dd {lim}</div>'
    if report.degraded_paths:
        for dp in report.degraded_paths:
            html += f'<div class="known-limitation">⚠️ Degraded: {dp}</div>'

    # Whale Positions
    html += "<h2>\U0001f40b Whale Positions</h2>"
    html += _render_positions_table(report.whale_positions)

    # Position Changes
    html += "<h2>\U0001f4c8 Position Changes</h2>"
    html += _render_changes_table(report.whale_changes)

    # Market Context
    html += "<h2>\U0001f4ca Market Context</h2>"
    html += _render_market_cards(report.market_contexts)

    # Feed Items
    html += "<h2>\U0001f4ec Feed Items</h2>"
    html += _render_feed_items(report.feed_items)

    # Source Health
    html += "<h2>⚙️ Source Health</h2>"
    html += _render_source_health(report.source_health)

    # Footer
    html += f"""<div style="margin-top:30px;padding-top:12px;border-top:1px solid #30363d;font-size:11px;color:#8b949e">
        Generated: {_utc_now()} UTC | Contracts: v{report.contracts_version} | Sealed: {report.contracts_sealed_at}
    </div>
</body>
</html>"""

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html

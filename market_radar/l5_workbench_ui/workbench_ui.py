"""MVP+ Lane 5 — Workbench UI.

Generates a self-contained local HTML dashboard from a RunReport.
No external dependencies — inline CSS and JS.

Output: Single HTML file with:
  - Run header (ID, timestamps, overall status)
  - Whale positions table
  - Position changes table (with risk classification)
  - Market context cards (BTC/ETH/SOL/HYPE)
  - Feed items list
  - Source health summary
  - Limitations / degraded paths
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.shared.contracts import (
    RunReport,
    WhalePosition,
    WhalePositionChange,
    MarketContext,
    UnifiedFeedItem,
    SourceHealth,
    LaneResult,
    CONTRACTS_VERSION,
)

VERSION = "mvp+v1.0-l5"
CN_TZ_OFFSET = 8  # UTC+8 for display


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_usd(value: Optional[float]) -> str:
    if value is None:
        return "<span class='null'>N/A</span>"
    if abs(value) >= 1_000_000:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "<span class='null'>N/A</span>"
    return f"{value:+.2f}%"


def _format_change_type_html(ctype: str) -> str:
    badges = {
        "POSITION_OPENED": "<span class='badge badge-opened'>OPENED</span>",
        "POSITION_INCREASED": "<span class='badge badge-increased'>INCREASED</span>",
        "POSITION_REDUCED": "<span class='badge badge-reduced'>REDUCED</span>",
        "POSITION_CLOSED": "<span class='badge badge-closed'>CLOSED</span>",
        "DIRECTION_FLIPPED": "<span class='badge badge-flipped'>FLIPPED</span>",
        "NO_CHANGE": "<span class='badge badge-nochange'>NO CHANGE</span>",
        "UNKNOWN": "<span class='badge badge-unknown'>UNKNOWN</span>",
    }
    return badges.get(ctype, ctype)


def _format_risk_html(risk: str) -> str:
    colors = {
        "CRITICAL": "risk-critical",
        "ELEVATED": "risk-elevated",
        "NORMAL": "risk-normal",
        "LOW": "risk-low",
        "UNKNOWN": "risk-unknown",
    }
    cls = colors.get(risk, "risk-unknown")
    return f"<span class='{cls}'>{risk}</span>"


def _format_side_html(side: str) -> str:
    if side == "LONG":
        return "<span class='side-long'>LONG</span>"
    return "<span class='side-short'>SHORT</span>"


def _format_source_status_html(status: str) -> str:
    colors = {
        "OK": "status-ok",
        "DEGRADED": "status-degraded",
        "FAILED": "status-failed",
        "UNKNOWN": "status-unknown",
    }
    cls = colors.get(status, "status-unknown")
    return f"<span class='{cls}'>{status}</span>"


@dataclass
class L5Result:
    """Result from a single L5 run."""
    html_path: Optional[str] = None
    html_name: Optional[str] = None
    source_health: list[SourceHealth] = field(default_factory=list)
    error: Optional[str] = None
    run_id: str = ""
    generated_at: str = ""

    def as_dict(self) -> dict:
        return {
            "lane": "L5",
            "html_path": self.html_path,
            "html_name": self.html_name,
            "error": self.error,
            "run_id": self.run_id,
        }


# ── HTML Template ─────────────────────────────────────────────────────────────

HTML_HEAD = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MVP+ Crypto Signal Workbench</title>
<style>
  :root {
    --bg: #0d1117;
    --card-bg: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --orange: #d29922;
    --yellow: #e3b341;
    --purple: #bc8cff;
    --font: -apple-system, 'Segoe UI', 'Noto Sans SC', Helvetica, Arial, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: var(--font); background: var(--bg); color: var(--text); padding: 20px; }
  h1 { font-size: 1.5rem; margin-bottom: 4px; }
  h2 { font-size: 1.2rem; margin: 24px 0 12px; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
  h3 { font-size: 1rem; margin: 16px 0 8px; }
  .subtitle { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 16px; }
  .run-meta { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 0.85rem; }
  .run-meta dt { color: var(--text-muted); display: inline; }
  .run-meta dd { display: inline; margin-right: 20px; }
  .status-banner { padding: 8px 16px; border-radius: 6px; margin-bottom: 16px; font-weight: 600; font-size: 0.9rem; }
  .status-ok { color: var(--green); }
  .status-degraded { color: var(--orange); }
  .status-failed { color: var(--red); }
  .status-unknown { color: var(--text-muted); }
  .banner-ok { background: #0a2e1a; border: 1px solid var(--green); color: var(--green); }
  .banner-degraded { background: #2e1a0a; border: 1px solid var(--orange); color: var(--orange); }
  .banner-failed { background: #2e0a0a; border: 1px solid var(--red); color: var(--red); }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 0.85rem; }
  th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
  th { background: var(--card-bg); color: var(--text-muted); font-weight: 500; position: sticky; top: 0; }
  tr:hover td { background: #1c2128; }
  .null { color: var(--text-muted); font-style: italic; }
  .side-long { color: var(--green); font-weight: 600; }
  .side-short { color: var(--red); font-weight: 600; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
  .badge-opened { background: #0a2e1a; color: var(--green); }
  .badge-increased { background: #0a2e1a; color: var(--green); }
  .badge-reduced { background: #2e0a0a; color: var(--red); }
  .badge-closed { background: #2e0a0a; color: var(--red); }
  .badge-flipped { background: #2e1a0a; color: var(--orange); }
  .badge-nochange { background: var(--card-bg); color: var(--text-muted); }
  .badge-unknown { background: var(--card-bg); color: var(--text-muted); }
  .risk-critical { color: var(--red); font-weight: 700; }
  .risk-elevated { color: var(--orange); font-weight: 600; }
  .risk-normal { color: var(--yellow); }
  .risk-low { color: var(--green); }
  .risk-unknown { color: var(--text-muted); }
  .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .market-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; }
  .market-card .symbol { font-size: 1rem; font-weight: 600; }
  .market-card .price { font-size: 1.3rem; font-weight: 700; margin: 4px 0; }
  .market-card .detail { font-size: 0.8rem; color: var(--text-muted); }
  .market-card .change-pos { color: var(--green); }
  .market-card .change-neg { color: var(--red); }
  .feed-item { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; }
  .feed-item .feed-title { font-weight: 600; font-size: 0.9rem; }
  .feed-item .feed-meta { font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }
  .feed-item .feed-type-badge { display: inline-block; padding: 1px 6px; border-radius: 8px; font-size: 0.7rem; background: var(--card-bg); border: 1px solid var(--border); }
  .health-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 8px; margin-bottom: 16px; }
  .health-item { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; font-size: 0.85rem; }
  .health-item .src-name { font-weight: 600; }
  .health-item .src-detail { font-size: 0.75rem; color: var(--text-muted); }
  .limitation { color: var(--orange); font-size: 0.85rem; }
  .scroll-wrap { overflow-x: auto; }
  .mt-4 { margin-top: 16px; }
  @media (max-width: 640px) {
    body { padding: 12px; }
    table { font-size: 0.75rem; }
    th, td { padding: 4px 6px; }
    .card-grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
"""

HTML_TAIL = r"""
</body>
</html>"""


def _render_run_header(report: RunReport) -> str:
    """Render run metadata header."""
    total_errors = sum(
        lr.error_count for lr in report.lane_results.values()
    )
    total_items = (
        len(report.whale_positions) + len(report.whale_changes)
        + len(report.market_contexts) + len(report.feed_items)
    )
    status = "OK" if not report.error and total_errors == 0 else "DEGRADED" if total_errors > 0 else "FAILED"

    banner_class = "banner-ok" if status == "OK" else "banner-degraded" if status == "DEGRADED" else "banner-failed"

    html = f"""<div class="status-banner {banner_class}">
  ⚡ Overall Status: {status}{' — ' + report.error if report.error else ''}
</div>
<div class="run-meta">
  <dl>
    <dt>Run ID:</dt><dd>{report.run_id}</dd>
    <dt>Started:</dt><dd>{report.started_at}</dd>
    <dt>Completed:</dt><dd>{report.completed_at}</dd>
    <dt>Items:</dt><dd>{total_items}</dd>
    <dt>Lanes:</dt><dd>{len(report.lane_results)}</dd>
    <dt>Errors:</dt><dd>{total_errors}</dd>
    <dt>Contracts:</dt><dd>{report.contracts_version}</dd>
  </dl>
</div>"""
    return html


def _render_lane_results(report: RunReport) -> str:
    """Render lane result summary."""
    html = '<h2>🏗 Lane Results</h2><table><thead><tr>'
    html += '<th>Lane</th><th>Status</th><th>Items</th><th>Errors</th><th>Duration</th></tr></thead><tbody>'

    for lane_id in sorted(report.lane_results.keys()):
        lr = report.lane_results[lane_id]
        dur = ""
        if lr.started_at and lr.completed_at:
            try:
                start = datetime.fromisoformat(lr.started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(lr.completed_at.replace("Z", "+00:00"))
                dur_s = (end - start).total_seconds()
                dur = f"{dur_s:.1f}s"
            except (ValueError, TypeError):
                pass
        html += f"<tr><td>{lane_id}</td><td>{_format_source_status_html(lr.status)}</td>"
        html += f"<td>{lr.item_count}</td><td>{lr.error_count}</td><td>{dur}</td></tr>"

    html += '</tbody></table>'
    return html


def _render_whale_positions(positions: list[WhalePosition]) -> str:
    """Render whale positions table."""
    if not positions:
        return '<h2>🐋 Whale Positions</h2><p class="null">No positions found.</p>'

    html = '<h2>🐋 Whale Positions</h2><div class="scroll-wrap"><table><thead><tr>'
    html += '<th>Address</th><th>Asset</th><th>Side</th><th>Size (USD)</th><th>Entry</th><th>Mark</th>'
    html += '<th>Leverage</th><th>Unrealized PnL</th><th>Liq. Price</th><th>Liq. Dist.</th><th>Label</th></tr></thead><tbody>'

    # Sort by position size descending
    sorted_pos = sorted(positions, key=lambda p: p.position_size_usd or 0, reverse=True)
    for pos in sorted_pos:
        d = pos.as_dict()
        html += f"<tr>"
        html += f"<td title='{d['address']}'>{d['address'][:10]}...</td>"
        html += f"<td>{d['asset']}</td>"
        html += f"<td>{_format_side_html(d['side'])}</td>"
        html += f"<td>{_format_usd(d['position_size_usd'])}</td>"
        html += f"<td>{_format_usd(d.get('entry_price'))}</td>"
        html += f"<td>{_format_usd(d.get('mark_price'))}</td>"
        lev = d.get('leverage')
        lev_str = str(lev) if lev is not None else '<span class="null">N/A</span>'
        html += f"<td>{lev_str}</td>"
        html += f"<td>{_format_usd(d.get('unrealized_pnl_usd'))}</td>"
        html += f"<td>{_format_usd(d.get('liquidation_price'))}</td>"
        html += f"<td>{_format_pct(d.get('liquidation_distance_pct'))}</td>"
        label_val = d.get('label')
        label_str = label_val if label_val else '<span class="null">N/A</span>'
        html += f"<td>{label_str}</td>"
        html += "</tr>"

    html += '</tbody></table></div>'
    return html


def _render_whale_changes(changes: list[WhalePositionChange]) -> str:
    """Render whale position changes table."""
    if not changes:
        return '<h2>🔄 Position Changes</h2><p class="null">No changes detected.</p>'

    html = '<h2>🔄 Position Changes</h2><div class="scroll-wrap"><table><thead><tr>'
    html += '<th>Asset</th><th>Change Type</th><th>Side</th><th>Current (USD)</th><th>Previous (USD)</th>'
    html += '<th>Delta (USD)</th><th>Change %</th><th>Risk</th><th>Factors</th><th>Label</th></tr></thead><tbody>'

    for ch in changes:
        d = ch.as_dict()
        html += f"<tr>"
        html += f"<td>{d['asset']}</td>"
        html += f"<td>{_format_change_type_html(d['change_type'])}</td>"
        html += f"<td>{_format_side_html(d['side'])}</td>"
        html += f"<td>{_format_usd(d['current_position_size_usd'])}</td>"
        html += f"<td>{_format_usd(d.get('previous_position_size_usd'))}</td>"
        html += f"<td>{_format_usd(d.get('position_delta_usd'))}</td>"
        html += f"<td>{_format_pct(d.get('change_pct'))}</td>"
        html += f"<td>{_format_risk_html(d['risk_level'])}</td>"
        risk_factors_str = ', '.join(d.get('risk_factors', [])) or '<span class="null">---</span>'
        html += f"<td>{risk_factors_str}</td>"
        label_val = d.get('label') or '<span class="null">N/A</span>'
        html += f"<td>{label_val}</td>"
        html += "</tr>"

    html += '</tbody></table></div>'
    return html


def _render_market_context(contexts: list[MarketContext]) -> str:
    """Render market context as cards."""
    if not contexts:
        return '<h2>📊 Market Context</h2><p class="null">No market data available.</p>'

    html = '<h2>📊 Market Context</h2><div class="card-grid">'

    for ctx in contexts:
        d = ctx.as_dict()
        price_str = f"${d['price']:,.2f}" if d.get('price') else "<span class='null'>N/A</span>"
        change_str = ""
        chg = d.get('price_change_24h_pct')
        if chg is not None:
            cls = "change-pos" if chg >= 0 else "change-neg"
            change_str = f"<div class='{cls}'>{chg:+.2f}%</div>"

        vol_str = ""
        vol = d.get('volume_24h')
        if vol:
            vol_str = f"<div class='detail'>Vol: ${vol:,.0f}</div>"

        oi_str = ""
        oi = d.get('open_interest')
        if oi:
            oi_str = f"<div class='detail'>OI: ${oi:,.0f}</div>"

        fr_str = ""
        fr = d.get('funding_rate')
        if fr:
            fr_str = f"<div class='detail'>Funding: {fr:.4f}%</div>"

        source_str = f"<div class='detail'>Source: {d.get('source', 'unknown')}</div>"

        html += f"""<div class="market-card">
  <div class="symbol">{d['symbol']}</div>
  <div class="price">{price_str}</div>
  {change_str}
  {vol_str}
  {oi_str}
  {fr_str}
  {source_str}
</div>"""

    html += '</div>'
    return html


def _render_feed_items(items: list[UnifiedFeedItem]) -> str:
    """Render feed items list."""
    if not items:
        return '<h2>📰 Feed Items</h2><p class="null">No feed items available.</p>'

    html = f'<h2>📰 Feed Items ({len(items)})</h2>'

    # Show latest 20
    for item in items[:20]:
        d = item.as_dict()
        event_type = f" | {d.get('event_type', '')}" if d.get('event_type') else ""
        assets = f" | {', '.join(d.get('assets_affected', [])[:3])}" if d.get('assets_affected') else ""

        html += f"""<div class="feed-item">
  <div class="feed-title">{d['title'][:120]}</div>
  <div class="feed-meta">
    <span class="feed-type-badge">{d['feed_type']}</span>
    {d.get('source_name', '')}{event_type}{assets}
  </div>
</div>"""

    if len(items) > 20:
        html += f'<p class="null">... and {len(items) - 20} more items</p>'

    return html


def _render_source_health(health_list: list[SourceHealth]) -> str:
    """Render source health grid."""
    if not health_list:
        return ''

    html = '<h2>❤️ Source Health</h2><div class="health-grid">'

    for h in health_list:
        d = h.as_dict()
        status_html = _format_source_status_html(d['status'])

        detail_parts = []
        if d.get('success_count') is not None:
            detail_parts.append(f"OK: {d['success_count']}")
        if d.get('error_count'):
            detail_parts.append(f"Err: {d['error_count']}")
        if d.get('latency_ms'):
            detail_parts.append(f"{d['latency_ms']:.0f}ms")
        if d.get('consecutive_failures'):
            detail_parts.append(f"Consec: {d['consecutive_failures']}")

        detail_str = " | ".join(detail_parts) if detail_parts else ""

        degraded = d.get('degraded_info')
        degraded_str = ""
        if degraded:
            degraded_str = f"<div class='src-detail' style='color:var(--orange);'>{degraded.get('message_summary', '')}</div>"

        html += f"""<div class="health-item">
  <div class="src-name">{d['source_name']} <span style="float:right;">{status_html}</span></div>
  <div class="src-detail">{detail_str}</div>
  {degraded_str}
</div>"""

    html += '</div>'
    return html


def _render_limitations(limitations: list[str]) -> str:
    if not limitations:
        return ''
    html = '<h2>⚠ Known Limitations</h2><ul>'
    for lim in limitations:
        html += f'<li class="limitation">{lim}</li>'
    html += '</ul>'
    return html


def _render_degraded_paths(paths: list[str]) -> str:
    if not paths:
        return ''
    html = '<h2>🔻 Degraded Paths</h2><ul>'
    for p in paths:
        html += f'<li class="limitation">{p}</li>'
    html += '</ul>'
    return html


def render_workbench(report: RunReport, output_dir: str) -> L5Result:
    """Generate a self-contained HTML workbench from a RunReport.

    Args:
        report: Completed RunReport with all lane outputs.
        output_dir: Directory to write the HTML file to.

    Returns:
        L5Result with path to generated HTML.
    """
    run_id = uuid.uuid4().hex[:8]
    generated_at = _utc_now()

    parts = [HTML_HEAD]
    parts.append(f"<h1>⚡ Crypto Signal Intelligence Workbench</h1>")
    parts.append(f"<div class='subtitle'>MVP+ Internal · One-Shot Read-Only · Generated {generated_at}</div>")

    parts.append(_render_run_header(report))
    parts.append(_render_lane_results(report))
    parts.append(_render_whale_positions(report.whale_positions))
    parts.append(_render_market_context(report.market_contexts))
    parts.append(_render_whale_changes(report.whale_changes))
    parts.append(_render_feed_items(report.feed_items))
    parts.append(_render_source_health(report.source_health))
    parts.append(_render_limitations(report.known_limitations))
    parts.append(_render_degraded_paths(report.degraded_paths))

    parts.append(HTML_TAIL)

    html_content = "\n".join(parts)

    # Write HTML
    os.makedirs(output_dir, exist_ok=True)
    html_name = f"workbench_{run_id}.html"
    html_path = os.path.join(output_dir, html_name)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    health: list[SourceHealth] = []
    from market_radar.shared.contracts import SourceStatus
    health.append(SourceHealth(
        source_name="workbench_renderer",
        source_group="ui",
        status=SourceStatus.OK,
        last_success_at=generated_at,
        success_count=1,
        error_count=0,
    ))

    return L5Result(
        html_path=html_path,
        html_name=html_name,
        source_health=health,
        run_id=run_id,
        generated_at=generated_at,
    )

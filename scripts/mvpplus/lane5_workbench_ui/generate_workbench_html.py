#!/usr/bin/env python3
"""MVP+ Lane 5 — Workbench UI Generator.

Reads all lane outputs and generates a single local HTML Workbench
displaying whale positions, position changes, market context, and
existing feed items.

One-shot, no server, no daemon. Open the HTML file directly in a browser.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, *[os.pardir] * 4))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> Optional[Any]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return None


def load_all_lane_outputs() -> dict[str, Optional[Any]]:
    return {
        "whale_positions": load_json(os.path.join(RESULTS_DIR, "lane1_whale_positions.json")),
        "whale_changes": load_json(os.path.join(RESULTS_DIR, "lane2_whale_changes.json")),
        "market_context": load_json(os.path.join(RESULTS_DIR, "lane3_market_context.json")),
        "existing_feeds": load_json(os.path.join(RESULTS_DIR, "lane4_existing_feeds.json")),
    }


def _fmt_price(v: Optional[float], decimals: int = 2) -> str:
    if v is None:
        return "—"
    if v >= 10000:
        return f"${v:,.{decimals}f}"
    elif v >= 1:
        return f"${v:,.{decimals}f}"
    else:
        return f"${v:.{decimals}f}"


def _fmt_change(v: Optional[float]) -> str:
    if v is None:
        return "—"
    cls = "positive" if v > 0 else "negative" if v < 0 else ""
    return f'<span class="{cls}">{v:+.2f}%</span>'


def _fmt_pnl(v: Optional[float]) -> str:
    if v is None:
        return "—"
    cls = "positive" if v >= 0 else "negative"
    return f'<span class="{cls}">${v:+,.0f}</span>'


def _fmt_bool(v: Optional[bool]) -> str:
    if v is None:
        return "—"
    return "✅" if v else "❌"


def _fmt_size(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:+,.4f}"


def generate_css() -> str:
    return """/* Workbench MVP+ — single-file styles */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0d1117; color: #c9d1d9; padding: 20px; }
h1 { color: #f0f6fc; font-size: 24px; margin-bottom: 6px; }
h2 { color: #58a6ff; font-size: 18px; margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 1px solid #21262d; }
h3 { color: #f0f6fc; font-size: 14px; margin: 16px 0 8px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.timestamp { color: #8b949e; font-size: 13px; }
.status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.status-healthy { background: #1a3a2a; color: #3fb950; }
.status-degraded { background: #3a2a1a; color: #d29922; }
.status-unavailable { background: #3a1a1a; color: #f85149; }
.card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.card-title { font-size: 14px; font-weight: 600; color: #f0f6fc; margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 6px; border-bottom: 2px solid #30363d; color: #8b949e; font-weight: 600; white-space: nowrap; }
td { padding: 8px 6px; border-bottom: 1px solid #21262d; }
tr:hover td { background: #1c2333; }
.positive { color: #3fb950; }
.negative { color: #f85149; }
.neutral { color: #8b949e; }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.metric-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 12px; text-align: center; }
.metric-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
.metric-value { font-size: 20px; font-weight: 700; margin: 4px 0; }
.metric-sub { font-size: 12px; color: #8b949e; }
.risk-flag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 500;
             margin: 1px; background: #3a1a1a; color: #f85149; border: 1px solid #f8514933; }
.risk-flag.liq { background: #3a0a0a; color: #ff6b6b; border-color: #ff6b6b44; }
.risk-flag.info { background: #1a2a3a; color: #58a6ff; border-color: #58a6ff33; }
.change-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500;
              margin: 1px; }
.change-tag.open { background: #1a3a2a; color: #3fb950; border: 1px solid #3fb95033; }
.change-tag.close { background: #3a1a1a; color: #f85149; border: 1px solid #f8514933; }
.change-tag.increase { background: #1a2a3a; color: #58a6ff; border: 1px solid #58a6ff33; }
.change-tag.reduce { background: #3a2a1a; color: #d29922; border: 1px solid #d2992233; }
.change-tag.flip { background: #3a1a3a; color: #bc8cff; border: 1px solid #bc8cff33; }
.feed-item { padding: 8px 0; border-bottom: 1px solid #21262d; }
.feed-item:last-child { border-bottom: none; }
.feed-title { font-weight: 500; color: #f0f6fc; }
.feed-meta { font-size: 11px; color: #8b949e; margin-top: 2px; }
.feed-tag { display: inline-block; padding: 0 6px; border-radius: 8px; font-size: 10px; font-weight: 600;
            margin-right: 4px; }
.feed-tag.flash { background: #1a3a2a; color: #3fb950; }
.feed-tag.news { background: #1a2a3a; color: #58a6ff; }
.feed-tag.tg { background: #2a1a3a; color: #bc8cff; }
.error-box { background: #3a1a1a; border: 1px solid #f8514944; border-radius: 8px; padding: 12px; margin: 8px 0; }
.error-title { color: #f85149; font-weight: 600; font-size: 13px; }
.error-msg { color: #c9d1d9; font-size: 12px; margin-top: 4px; }
.degraded-note { color: #d29922; font-size: 12px; font-style: italic; margin: 4px 0; }
@media (max-width: 900px) { .grid-4 { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .grid-4 { grid-template-columns: 1fr; } }
"""


def generate_header(data: dict[str, Any]) -> str:
    generated = utc_now_str()
    summary = []

    wp = data.get("whale_positions")
    if wp and wp.get("positions"):
        summary.append(f"<span class='status-badge status-healthy'>🐋 {len(wp['positions'])} positions</span>")

    wc = data.get("whale_changes")
    if wc and wc.get("changes"):
        summary.append(f"<span class='status-badge status-healthy'>🔄 {len(wc['changes'])} changes</span>")

    mc = data.get("market_context")
    if mc and mc.get("market_contexts"):
        healthy = sum(1 for c in mc["market_contexts"] if c.get("current_price") is not None)
        summary.append(f"<span class='status-badge {'status-healthy' if healthy > 0 else 'status-degraded'}'>📊 {healthy}/{len(mc['market_contexts'])} assets</span>")

    ef = data.get("existing_feeds")
    if ef and ef.get("feed_items"):
        summary.append(f"<span class='status-badge status-healthy'>📰 {len(ef['feed_items'])} feed items</span>")

    badges = " ".join(summary) if summary else ""
    return f"""
<div class="header">
  <div>
    <h1>🐋 Crypto Signal Intelligence — MVP+ Workbench</h1>
    <div class="timestamp">Generated: {generated} UTC</div>
  </div>
  <div>{badges}</div>
</div>"""


def generate_whale_positions_section(data: Optional[dict]) -> str:
    if data is None:
        return "<div class='degraded-note'>No whale position data available.</div>"

    positions = data.get("positions", [])
    if not positions:
        health = data.get("source_health", {}).get("status", "unknown")
        return f"<div class='degraded-note'>Source: {health}. No whale positions found.</div>"

    # Summary metrics
    total_value = sum(p.get("position_value_usd", 0) or 0 for p in positions)
    total_pnl = sum(p.get("unrealized_pnl_usd", 0) or 0 for p in positions)
    long_positions = [p for p in positions if p.get("direction") == "long"]
    short_positions = [p for p in positions if p.get("direction") == "short"]

    rows = ""
    for p in positions:
        label = p.get("label", "Unknown")
        coin = p.get("coin", "")
        direction_cls = "positive" if p.get("direction") == "long" else "negative"
        dir_icon = "🟢" if p.get("direction") == "long" else "🔴"
        risk_html = ""
        wc_data = load_json(os.path.join(RESULTS_DIR, "lane2_whale_changes.json"))
        if wc_data:
            addr_coins = [(p["address"], p["coin"]) for p in positions]
            for change in wc_data.get("changes", []):
                if change.get("address") == p.get("address") and change.get("coin") == p.get("coin"):
                    for flag in change.get("risk_flags", []):
                        risk_html += f'<span class="risk-flag">{flag.replace("_", " ")}</span>'
                    # Show change type tag
                    ct = change.get("change_type", "")
                    if ct:
                        ct_class = ct.split("_")[0]
                        risk_html += f'<span class="change-tag {ct_class}">{ct}</span>'

        rows += f"""<tr>
  <td>{dir_icon} <strong>{coin}</strong></td>
  <td>{label}</td>
  <td><span class="{direction_cls}">{p.get("direction", "")}</span></td>
  <td>{_fmt_size(p.get("signed_size"))}</td>
  <td>{_fmt_price(p.get("entry_price"))}</td>
  <td>{_fmt_price(p.get("mark_price"))}</td>
  <td>{p.get("leverage", "—")}x</td>
  <td>{_fmt_price(p.get("position_value_usd"), 0)}</td>
  <td>{_fmt_pnl(p.get("unrealized_pnl_usd"))}</td>
  <td>{_fmt_price(p.get("liquidation_price"))}</td>
  <td>{_fmt_change(p.get("liquidation_distance_pct"))}</td>
  <td>{risk_html}</td>
</tr>"""

    return f"""
<div class="card">
  <div class="grid-4">
    <div class="metric-card">
      <div class="metric-label">Total Position Value</div>
      <div class="metric-value positive">${total_value:,.0f}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Unrealized PnL</div>
      <div class="metric-value {'positive' if total_pnl >= 0 else 'negative'}">${total_pnl:+,.0f}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Long / Short</div>
      <div class="metric-value">{len(long_positions)} / {len(short_positions)}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Active Positions</div>
      <div class="metric-value">{len(positions)}</div>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-title">🐋 Whale Positions</div>
  <table>
    <thead><tr>
      <th>Coin</th><th>Label</th><th>Dir</th><th>Size</th><th>Entry</th><th>Mark</th>
      <th>Lev</th><th>Val (USD)</th><th>PnL</th><th>Liq</th><th>Liq Dist</th><th>Flags</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


def generate_position_changes_section(data: Optional[dict]) -> str:
    if data is None:
        return "<div class='degraded-note'>No position change data available.</div>"

    changes = data.get("changes", [])
    if not changes:
        is_first = data.get("is_first_run", False)
        if is_first:
            return "<div class='degraded-note'>First run — baseline snapshot taken. Changes will be detected on next run.</div>"
        return "<div class='degraded-note'>No position changes detected since last snapshot.</div>"

    rows = ""
    for c in changes:
        label = c.get("label", "Unknown") or "Unknown"
        coin = c.get("coin", "")
        ct = c.get("change_type", "")
        ct_class = ct.split("_")[0] if "_" in ct else ct
        color = {"open": "positive", "increase": "positive", "reduce": "neutral",
                 "close": "negative", "flip": "neutral"}.get(ct_class, "")
        color_tag = {"open": "open", "increase": "increase", "reduce": "reduce",
                     "close": "close", "flip": "flip"}.get(ct_class, "")

        delta = c.get("delta", {})
        size_delta_str = _fmt_size(delta.get("size_delta")) if delta.get("size_delta") is not None else "—"
        val_delta_str = _fmt_price(delta.get("position_value_delta_usd"), 0) if delta.get("position_value_delta_usd") is not None else "—"

        flags = c.get("risk_flags", [])
        flags_html = " ".join(f'<span class="risk-flag">{f.replace("_", " ")}</span>' for f in flags) if flags else "—"

        rows += f"""<tr>
  <td>{coin}</td>
  <td>{label}</td>
  <td><span class="change-tag {color_tag}">{ct}</span></td>
  <td>{size_delta_str}</td>
  <td>{val_delta_str}</td>
  <td>{flags_html}</td>
</tr>"""

    return f"""
<div class="card">
  <div class="card-title">🔄 Position Changes ({len(changes)})</div>
  <table>
    <thead><tr>
      <th>Coin</th><th>Label</th><th>Type</th><th>Size Δ</th><th>Value Δ</th><th>Risk Flags</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


def generate_market_context_section(data: Optional[dict]) -> str:
    if data is None:
        return "<div class='degraded-note'>No market context data available.</div>"

    contexts = data.get("market_contexts", [])
    if not contexts:
        return "<div class='degraded-note'>No market context entries.</div>"

    rows = ""
    for c in contexts:
        asset = c.get("asset", "")
        rows += f"""<tr>
  <td><strong>{asset}</strong></td>
  <td>{c.get("venue", "")}</td>
  <td>{_fmt_price(c.get("current_price"))}</td>
  <td>{_fmt_change(c.get("change_24h_pct"))}</td>
  <td>{_fmt_price(c.get("high_24h"))}</td>
  <td>{_fmt_price(c.get("low_24h"))}</td>
  <td>{_fmt_price(c.get("volume_24h_usd"), 0)}</td>
  <td>{_fmt_price(c.get("open_interest_usd"), 0)}</td>
  <td>{_fmt_change(c.get("funding_rate_pct"))}</td>
  <td>
    <span class="status-badge status-{'healthy' if c.get('current_price') else 'unavailable'}">
      {c.get('source_health', {}).get('status', '?')}
    </span>
  </td>
</tr>"""

    return f"""
<div class="card">
  <div class="card-title">📊 Market Context — BTC / ETH / SOL / HYPE</div>
  <table>
    <thead><tr>
      <th>Asset</th><th>Venue</th><th>Price</th><th>24h Δ</th><th>High</th><th>Low</th>
      <th>Vol 24h</th><th>OI</th><th>FR</th><th>Status</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>"""


def generate_feeds_section(data: Optional[dict]) -> str:
    if data is None:
        return "<div class='degraded-note'>No feed data available.</div>"

    items = data.get("feed_items", [])
    if not items:
        return "<div class='degraded-note'>No feed items found.</div>"

    # Limit to most recent 100
    display = items[:100]
    items_html = ""

    for item in display:
        stream = item.get("stream_type", "?")
        source = item.get("source_label", "?")
        title = item.get("title", "?")
        summary = item.get("summary")
        assets = item.get("assets", [])
        published = item.get("published_at_utc", "")[:19] if item.get("published_at_utc") else ""

        assets_html = ""
        if assets:
            assets_html = " ".join(f'<span class="feed-tag flash">{a}</span>' for a in assets[:5])

        summary_html = f"<div style='font-size:12px;color:#8b949e;margin-top:2px'>{summary[:200]}</div>" if summary else ""

        items_html += f"""<div class="feed-item">
  <div>
    <span class="feed-tag {stream}">{stream.upper()}</span>
    <span class="feed-title">{title}</span>
  </div>
  <div class="feed-meta">{source} · {published} {assets_html}</div>
  {summary_html}
</div>"""

    return f"""
<div class="card">
  <div class="card-title">📰 Existing Feed Items ({len(items)} total, showing {len(display)})</div>
  {items_html}
</div>"""


def generate_run_info(data: dict[str, Any]) -> str:
    sources: list[dict] = []
    for key, label in [("whale_positions", "Whale Positions"),
                        ("whale_changes", "Whale Changes"),
                        ("market_context", "Market Context"),
                        ("existing_feeds", "Existing Feeds")]:
        d = data.get(key)
        if d is None:
            sources.append(f"<div><strong>{label}</strong>: <span class='status-badge status-unavailable'>no data</span></div>")
        else:
            sh = d.get("source_health", {})
            status = sh.get("status", "unknown")
            cls = f"status-{status}" if status in ("healthy", "degraded", "unavailable") else "status-degraded"
            msg = sh.get("message_summary", "")
            sources.append(f"<div><strong>{label}</strong>: <span class='status-badge {cls}'>{status}</span>"
                           f"<span style='color:#8b949e;font-size:12px;margin-left:8px'>{msg}</span></div>")

    return f"""
<div class="card">
  <div class="card-title">🏗 Run Summary — Source Health</div>
  {''.join(sources)}
</div>"""


# ── HTML Generation ─────────────────────────────────────────────────────────


def generate_html(data: dict[str, Any]) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MVP+ Workbench — Crypto Signal Intelligence</title>
<style>{generate_css()}</style>
</head>
<body>
{generate_header(data)}
{generate_run_info(data)}
<h2>🐋 Whale Intelligence</h2>
{generate_whale_positions_section(data.get("whale_positions"))}
{generate_position_changes_section(data.get("whale_changes"))}
<h2>📊 Market Context</h2>
{generate_market_context_section(data.get("market_context"))}
<h2>📰 Existing Feeds</h2>
{generate_feeds_section(data.get("existing_feeds"))}
<div class="timestamp" style="margin-top:20px;text-align:center">
  Crypto Signal Intelligence MVP+ — Read-Only · Not Financial Advice · One-Shot Snapshot
</div>
</body>
</html>"""


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_lane5"
    snapshot_time = utc_now_str()

    print(f"[{run_id}] Lane 5: Workbench UI Generator", file=sys.stderr)

    # Load all lane outputs
    lane_data = load_all_lane_outputs()
    missing = [k for k, v in lane_data.items() if v is None]
    if missing:
        print(f"  [WARN] Missing lane outputs: {', '.join(missing)}", file=sys.stderr)

    summary_parts = []
    for key, d in lane_data.items():
        if d:
            items = d.get("positions") or d.get("changes") or d.get("market_contexts") or d.get("feed_items") or []
            summary_parts.append(f"{key}={len(items)}")
    print(f"  Loaded: {', '.join(summary_parts)}", file=sys.stderr)

    # Generate HTML
    html = generate_html(lane_data)

    output_path = os.path.join(OUTPUT_DIR, "workbench.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    elapsed = time.time() - start_time
    print(f"  Done in {elapsed:.1f}s.", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

    # Also output lane5 status
    status = {
        "run_id": run_id,
        "generated_at_utc": snapshot_time,
        "lane": "lane5_workbench_ui",
        "workbench_html_path": os.path.relpath(output_path, PROJECT_ROOT),
        "source_health": {
            "status": "healthy" if not missing else "degraded",
            "source": "workbench_ui",
            "occurred_at_utc": snapshot_time,
            "message_summary": f"Generated workbench with {len(summary_parts)} data sections"
                               if not missing else f"Missing: {', '.join(missing)}",
        },
    }
    status_path = os.path.join(OUTPUT_DIR, "lane5_workbench_ui.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())

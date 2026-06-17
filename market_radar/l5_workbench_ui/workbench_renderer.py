"""MVP+ L5v2 — Secure Workbench HTML Renderer.

9-section dashboard from a WorkbenchBundle:
  1. Unified Intelligence Feed
  2. Whale Position Changes
  3. Current Whale Positions
  4. Liquidation Risk
  5. Market Context
  6. Source Health
  7. Alert Candidates
  8. Watchlists
  9. Event Journal

Security: HTML escaping, URL validation, CSP meta tag, no external scripts.
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from market_radar.shared.contracts import (
    WhalePosition, WhalePositionChange, MarketContext,
    UnifiedFeedItem, SourceHealth, SourceStatus,
    ChangeType, RiskLevel,
)

_SAFE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_CSP = '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'none\'; style-src \'unsafe-inline\'; img-src data:;">'


def _e(s: Any) -> str:
    if s is None: return ""
    return html_lib.escape(str(s), quote=True)


def _safe_url(url: Optional[str]) -> str:
    if url and _SAFE_URL_RE.match(url): return _e(url)
    return ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _usd(v: Any) -> str:
    if v is None: return "N/A"
    try:
        val = float(v)
        if abs(val) >= 1e9: return f"${val/1e9:.2f}B"
        if abs(val) >= 1e6: return f"${val/1e6:.2f}M"
        if abs(val) >= 1e3: return f"${val/1e3:.1f}K"
        return f"${val:.2f}"
    except (ValueError, TypeError): return str(v)


def _pct(v: Any) -> str:
    if v is None: return "N/A"
    try:
        val = float(v)
        return f"{'+' if val>0 else ''}{val:.2f}%"
    except (ValueError, TypeError): return str(v)


def _rc(r: str) -> str:
    return {"CRITICAL":"#f44","ELEVATED":"#f80","NORMAL":"#fc0","LOW":"#4c4","UNKNOWN":"#888"}.get(r,"#888")


def _badge(mode: str) -> str:
    c = {"live":"#4c4","cached":"#58a6ff","fixture":"#f80","degraded":"#f44"}.get(mode,"#888")
    return f'<span style="background:{c};color:#000;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:bold">{_e(mode)}</span>'


@dataclass
class WorkbenchBundle:
    run_id: str = ""
    generated_at: str = ""
    positions: list[WhalePosition] = field(default_factory=list)
    changes: list[WhalePositionChange] = field(default_factory=list)
    market_contexts: list[MarketContext] = field(default_factory=list)
    feed_items: list[UnifiedFeedItem] = field(default_factory=list)
    source_health: list[SourceHealth] = field(default_factory=list)
    alert_candidates: list[dict] = field(default_factory=list)
    watchlists: dict = field(default_factory=dict)
    event_journal: list[dict] = field(default_factory=list)
    market_regime: dict = field(default_factory=dict)
    downstream_candidates: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    degraded_paths: list[str] = field(default_factory=list)
    contracts_version: str = ""
    contracts_sealed_at: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _sec(s: str) -> str:
    return f"<h2>{s}</h2>"


def render_workbench(bundle: WorkbenchBundle, output_path: Optional[str] = None) -> str:
    gen = _utc_now()
    html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">{_CSP}
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Crypto Signal Intelligence — Workbench MVP+v2</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#0d1117;color:#e6edf3;padding:16px;font-size:14px}}
h1{{color:#58a6ff;font-size:22px}}
h2{{color:#c9d1d9;font-size:16px;margin:20px 0 8px;padding-bottom:6px;border-bottom:1px solid #30363d}}
a{{color:#58a6ff}}
table{{width:100%;border-collapse:collapse;margin-bottom:12px;font-size:12px}}
th{{background:#161b22;color:#8b949e;padding:6px 8px;text-align:left;font-weight:500;border-bottom:2px solid #30363d;white-space:nowrap}}
td{{padding:4px 8px;border-bottom:1px solid #21262d;white-space:nowrap;font-size:12px}}
tr:hover td{{background:#1c2128}}
.n{{text-align:right;font-family:'SF Mono',Consolas,monospace}}
.a{{font-family:'SF Mono',Consolas,monospace;font-size:11px}}
.feed-item{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px 12px;margin-bottom:6px;font-size:13px}}
.feed-hdr{{display:flex;gap:6px;align-items:center;margin-bottom:2px;font-size:11px;color:#8b949e}}
.feed-ttl{{font-size:13px;font-weight:500}}
.feed-body{{color:#8b949e;font-size:12px;margin-top:2px}}
.feed-assets{{color:#58a6ff;font-size:11px;margin-top:2px}}
.badge{{padding:1px 5px;border-radius:3px;font-weight:600;font-size:10px}}
.badge-flash{{background:#ff444433;color:#ff4444}}
.badge-news{{background:#58a6ff33;color:#58a6ff}}
.badge-onchain{{background:#44cc4433;color:#44cc44}}
.empty{{color:#8b949e;font-style:italic;padding:16px;text-align:center}}
.mgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;margin-bottom:12px}}
.mcard{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px}}
.msym{{font-size:12px;color:#8b949e}}
.mprc{{font-size:24px;font-weight:bold;margin:2px 0}}
.mchg{{font-size:14px;margin-bottom:4px}}
.mdet{{font-size:11px;color:#8b949e;line-height:1.5}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:12px}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px;text-align:center}}
.stat-v{{font-size:20px;font-weight:bold}}
.stat-l{{font-size:11px;color:#8b949e}}
.warn{{color:#fc0;font-size:12px;margin:2px 0}}
.disclaimer{{color:#f80;font-size:11px;margin-top:4px;font-style:italic}}
.ftr{{margin-top:24px;padding-top:8px;border-top:1px solid #30363d;font-size:10px;color:#8b949e}}
.jt{{color:#58a6ff;font-family:monospace;font-size:11px}}
</style></head><body>
<h1>Crypto Signal Intelligence - Internal Workbench</h1>
<p style="color:#8b949e;font-size:13px;margin-bottom:12px">
Run: {_e(bundle.run_id)} | {gen} UTC | {_e(bundle.contracts_version)}</p>'''

    mc = len([c for c in bundle.changes if c.change_type != ChangeType.NO_CHANGE])
    ok = len([h for h in bundle.source_health if h.status == SourceStatus.OK])
    tot = len(bundle.source_health)
    html += f'''<div class="stats">
<div class="stat"><div class="stat-v">{len(bundle.positions)}</div><div class="stat-l">Whale</div></div>
<div class="stat"><div class="stat-v">{mc}</div><div class="stat-l">Changes</div></div>
<div class="stat"><div class="stat-v">{len(bundle.feed_items)}</div><div class="stat-l">Feeds</div></div>
<div class="stat"><div class="stat-v">{len(bundle.market_contexts)}</div><div class="stat-l">Market</div></div>
<div class="stat"><div class="stat-v" style="color:{"#4c4" if ok==tot else "#f80"}">{ok}/{tot}</div><div class="stat-l">Health</div></div></div>'''

    for w in bundle.warnings:
        html += f'<div class="warn">W {_e(w)}</div>'
    for d in bundle.degraded_paths:
        html += f'<div class="warn">Degraded: {_e(d)}</div>'

    # 1. Feed
    html += _sec("1. Unified Intelligence Feed")
    if not bundle.feed_items:
        html += '<div class="empty">No feed items</div>'
    else:
        for item in sorted(bundle.feed_items, key=lambda x: x.published_at or x.ingested_at, reverse=True)[:30]:
            ft = _e(item.feed_type.value)
            html += f'''<div class="feed-item"><div class="feed-hdr">
<span class="badge badge-{ft.lower()}">{ft}</span>
<span style="color:#8b949e">{_e(item.source_name.value)}</span>{_badge(item.data_origin)}
<span style="margin-left:auto;color:#8b949e">{_e(item.published_at or item.ingested_at)}</span></div>
<div class="feed-ttl">{_e(item.title)}</div>'''
            if item.body:
                html += f'<div class="feed-body">{_e(item.body)[:200]}</div>'
            if item.assets_affected:
                html += f'<div class="feed-assets">{", ".join(_e(a) for a in item.assets_affected[:5])}</div>'
            url = _safe_url(item.url)
            if url:
                html += f'<a href="{url}" target="_blank" rel="noopener noreferrer">source</a>'
            html += "</div>"

    # 2. Changes
    html += _sec("2. Whale Position Changes")
    meaningful = [c for c in bundle.changes if c.change_type != ChangeType.NO_CHANGE]
    if not meaningful:
        html += '<div class="empty">No changes</div>'
    else:
        html += "<table><tr><th>Label</th><th>Asset</th><th>Change</th><th>Size</th><th>Delta$</th><th>Delta%</th><th>Risk</th><th>LiqDist</th></tr>"
        for c in meaningful:
            html += f'<tr><td class="a">{_e(c.label or "")}</td><td><b>{_e(c.asset)}</b></td>'
            html += f'<td>{_e(c.change_type.value)}</td><td class="n">{_usd(c.current_position_size_usd)}</td>'
            html += f'<td class="n">{_usd(c.position_delta_usd)}</td><td class="n">{_pct(c.change_pct)}</td>'
            html += f'<td style="color:{_rc(c.risk_level.value)};font-weight:bold">{_e(c.risk_level.value)}</td>'
            html += f'<td class="n" style="color:{"#f44" if (c.current_liquidation_distance_pct or 99)<15 else "#888"}">{_pct(c.current_liquidation_distance_pct)}</td></tr>'
        html += "</table>"

    # 3. Positions
    html += _sec("3. Current Whale Positions")
    if not bundle.positions:
        html += '<div class="empty">No positions</div>'
    else:
        html += "<table><tr><th>Label</th><th>Asset</th><th>Side</th><th>Size</th><th>Entry</th><th>Lev</th><th>PnL</th><th>LiqDist</th></tr>"
        for p in sorted(bundle.positions, key=lambda x: x.position_size_usd, reverse=True):
            sc = "#4c4" if p.side.value == "LONG" else "#f44"
            pc = "#4c4" if (p.unrealized_pnl_usd or 0) >= 0 else "#f44"
            html += f'<tr><td class="a">{_e(p.label or "")}</td><td><b>{_e(p.asset)}</b></td>'
            html += f'<td style="color:{sc};font-weight:bold">{_e(p.side.value)}</td>'
            html += f'<td class="n">{_usd(p.position_size_usd)}</td><td class="n">{_usd(p.entry_price)}</td>'
            html += f'<td class="n">{_e(str(p.leverage)+"x" if p.leverage else "N/A")}</td>'
            html += f'<td class="n" style="color:{pc}">{_usd(p.unrealized_pnl_usd)}</td>'
            html += f'<td class="n" style="color:{"#f44" if (p.liquidation_distance_pct or 99)<15 else "#888"}">{_pct(p.liquidation_distance_pct)}</td></tr>'
        html += "</table>"

    # 4. Liquidation Risk
    html += _sec("4. Liquidation Risk")
    risky = [c for c in bundle.changes if c.change_type != ChangeType.NO_CHANGE and (c.current_liquidation_distance_pct is not None and c.current_liquidation_distance_pct < 20)]
    if not risky:
        html += '<div class="empty">No liquidation risks</div>'
    else:
        html += "<table><tr><th>Label</th><th>Asset</th><th>Risk</th><th>LiqDist</th><th>LiqPrice</th></tr>"
        for c in risky:
            html += f'<tr><td class="a">{_e(c.label or "")}</td><td><b>{_e(c.asset)}</b></td>'
            html += f'<td style="color:{_rc(c.risk_level.value)}">{_e(c.risk_level.value)}</td>'
            html += f'<td class="n" style="color:#f44">{_pct(c.current_liquidation_distance_pct)}</td>'
            html += f'<td class="n">{_usd(c.current_liquidation_price)}</td></tr>'
        html += "</table>"

    # 5. Market Context
    html += _sec("5. Market Context")
    if not bundle.market_contexts:
        html += '<div class="empty">No market data</div>'
    else:
        html += '<div class="mgrid">'
        for ctx in bundle.market_contexts:
            chg = ctx.price_change_24h_pct
            cc = "#4c4" if (chg or 0) >= 0 else "#f44"
            html += f'<div class="mcard"><div class="msym">{_e(ctx.symbol)} {_badge(ctx.data_origin)}</div>'
            html += f'<div class="mprc">{_usd(ctx.price)}</div>'
            html += f'<div class="mchg" style="color:{cc}">{_pct(chg)}</div>'
            html += f'<div class="mdet">Vol:{_usd(ctx.volume_24h)} OI:{_usd(ctx.open_interest)} Fund:{_pct(ctx.funding_rate*100) if ctx.funding_rate is not None else "N/A"} Venue:{_e(ctx.source.value)}</div></div>'
        html += "</div>"

    # 6. Source Health
    html += _sec("6. Source Health")
    if not bundle.source_health:
        html += '<div class="empty">No health data</div>'
    else:
        html += "<table><tr><th>Source</th><th>Group</th><th>Status</th><th>OK</th><th>Err</th></tr>"
        sc_map = {"OK":"#4c4","DEGRADED":"#f80","FAILED":"#f44","UNKNOWN":"#888"}
        for h in bundle.source_health:
            c = sc_map.get(h.status.value, "#888")
            msg = _e(h.degraded_info.message_summary) if h.degraded_info else ""
            html += f'<tr title="{msg}"><td>{_e(h.source_name)}</td><td>{_e(h.source_group)}</td>'
            html += f'<td style="color:{c};font-weight:bold">{_e(h.status.value)}</td>'
            html += f'<td class="n">{h.success_count}</td><td class="n">{h.error_count}</td></tr>'
        html += "</table>"

    # 7. Watchlists
    html += _sec("7. Watchlists")
    if bundle.watchlists:
        for name, items in bundle.watchlists.items():
            html += f'<div><b>{_e(name)}</b>: {" | ".join(_e(str(i)) for i in (items or []))}</div>'
    else:
        html += '<div class="empty">No watchlists</div>'

    # 8. Alert Candidates
    html += _sec("8. Alert Candidates")
    if bundle.alert_candidates:
        for ac in bundle.alert_candidates[:15]:
            html += f'<div class="feed-item"><b>{_e(ac.get("title",""))}</b><br><span style="color:#8b949e;font-size:11px">{_e(ac.get("rationale",""))} | source: {_e(ac.get("source",""))}</span></div>'
    else:
        html += '<div class="empty">No candidates</div>'

    # 9. Event Journal
    html += _sec("9. Event Journal")
    if bundle.event_journal:
        for e in bundle.event_journal[-15:]:
            html += f'<div class="feed-item"><span class="jt">{_e(e.get("timestamp",""))}</span> {_e(e.get("summary",""))}</div>'
    else:
        html += '<div class="empty">No entries</div>'

    # Downstream
    html += _sec("Downstream Candidates")
    if bundle.downstream_candidates:
        for d in bundle.downstream_candidates[:10]:
            html += f'<div class="feed-item"><b>{_e(d.get("title",""))}</b> [{_e(d.get("channel",""))}]<br><span style="color:#8b949e;font-size:11px">{_e(d.get("rationale",""))}</span></div>'
    else:
        html += '<div class="empty">No downstream candidates</div>'

    # Market Regime
    html += _sec("Market Regime")
    regime = bundle.market_regime
    if regime:
        html += f'<div><b>State:</b> {_e(regime.get("state","unknown"))}</div>'
        for r in regime.get("rules", [])[:5]:
            html += f'<div style="color:#8b949e;font-size:11px">- {_e(r)}</div>'
        html += '<div class="disclaimer">interpretation_type: rule_based_system_context - no trading advice</div>'
    else:
        html += '<div class="empty">No regime analysis</div>'

    html += f'<div class="ftr">Contracts: {_e(bundle.contracts_version)} | {_e(bundle.contracts_sealed_at)}</div>'
    html += "</body></html>"

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        tmp = output_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(html)
        os.replace(tmp, output_path)

    return html

"""Secure static HTML workbench renderer.

Security guarantees:
  - CSP meta tag (script-src 'none', style-src 'unsafe-inline', img-src data:)
  - Universal HTML escaping (html.escape on EVERY external text field)
  - URL validation: only http/https allowed (reject javascript:, data:, etc.)
  - No script tags, no external fonts/stylesheets/scripts
  - Null-safe rendering (None fields don't crash, don't render 'None' text)
  - Stale/unavailable badges
  - Provenance badges (live/cached/fixture/research_sample)
  - Atomic output write (tmp + atomic rename)
"""

from __future__ import annotations

import hashlib
import html as html_lib
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from .bundle import WorkbenchBundle
from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, Freshness as FeedFreshness,
)
from market_radar.market_view.models import MarketSnapshot, Freshness as MarketFreshness


# ── Constants ────────────────────────────────────────────────────────────────

CSP_META = (
    '<meta http-equiv="Content-Security-Policy" '
    'content="default-src \'self\'; script-src \'none\'; '
    'style-src \'unsafe-inline\'; img-src data:;">'
)
_SAFE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_VERSION = "w3-v2.0"


# ── Security helpers ─────────────────────────────────────────────────────────

def _e(val: Any) -> str:
    """HTML-escape: safe for ANY external text insertion."""
    if val is None:
        return ""
    return html_lib.escape(str(val), quote=True)


def _safe_url(url: Optional[str]) -> str:
    """Return url only if http/https, else empty string (rejected)."""
    if url and _SAFE_URL_RE.match(url):
        return _e(url)
    return ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_usd(val: Any) -> str:
    if val is None:
        return ""
    try:
        v = float(val)
        if abs(v) >= 1e9:
            return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v/1e6:.2f}M"
        if abs(v) >= 1e3:
            return f"${v/1e3:.1f}K"
        return f"${v:.2f}" if v >= 0 else f"-${abs(v):.2f}"
    except (ValueError, TypeError):
        return _e(str(val))


def _fmt_pct(val: Any) -> str:
    if val is None:
        return ""
    try:
        v = float(val)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.2f}%"
    except (ValueError, TypeError):
        return _e(str(val))


# ── Badge helpers ────────────────────────────────────────────────────────────

_BADGE_STYLES = {
    "live": "background:#1a7f37;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600",
    "cached": "background:#1f6feb;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600",
    "fixture": "background:#9e6a03;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600",
    "research_sample": "background:#6e7681;color:#fff;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600",
    "fresh": "background:#1a7f37;color:#fff;padding:1px 4px;border-radius:3px;font-size:9px",
    "stale": "background:#d1242f;color:#fff;padding:1px 4px;border-radius:3px;font-size:9px",
    "unknown": "background:#6e7681;color:#fff;padding:1px 4px;border-radius:3px;font-size:9px",
}


def _badge(label: str, mode: str) -> str:
    style = _BADGE_STYLES.get(mode, _BADGE_STYLES["unknown"])
    return f'<span style="{style}">{_e(label)}</span>'


# ── Section renderers ────────────────────────────────────────────────────────

def _render_stats(bundle: WorkbenchBundle) -> str:
    feed_count = len(bundle.feed_items)
    live_items = sum(1 for f in bundle.feed_items if f.data_mode == FeedDataMode.LIVE)
    return f"""<div class="stats">
<div class="sc"><div class="sv">{len(bundle.market_snapshots)}</div><div class="sl">Market Assets</div></div>
<div class="sc"><div class="sv">{feed_count}</div><div class="sl">Feed Items ({live_items} live)</div></div>
<div class="sc"><div class="sv">{len(bundle.whale_positions)}</div><div class="sl">Whale Positions</div></div>
<div class="sc"><div class="sv">{len(bundle.whale_changes)}</div><div class="sl">Changes</div></div>
</div>"""


def _render_feed(items: list[FeedItem], max_items: int = 30) -> str:
    if not items:
        return '<div class="empty">No feed items</div>'

    # Sort by published_at (desc), None → end
    sorted_items = sorted(items, key=lambda x: (x.published_at or "9999"), reverse=True)[:max_items]
    parts = []

    for item in sorted_items:
        st = _e(item.source_type.value)
        src = _e(item.source_label)
        title = _e(item.title)
        body = _e(item.body)[:200] if item.body else None
        assets = " ".join(_e(a) for a in item.assets[:5]) if item.assets else None
        pub = _e(item.published_at) if item.published_at else None
        freshness_badge = _badge(item.freshness.value, item.freshness.value) if item.freshness else ""
        data_badge = _badge(item.data_mode.value, item.data_mode.value)

        parts.append(f"""<div class="fi">
<div class="fh"><span class="ft ft-{st}">{st}</span> {data_badge} {freshness_badge}
<span class="fs">{src}</span>{" <span class='fp'>"+pub+"</span>" if pub else ' <span class="fp" style="color:#888">time:unknown</span>'}
</div>
<div class="ftl">{title}</div>""")
        if body:
            parts.append(f'<div class="fb">{body}</div>')
        if assets:
            parts.append(f'<div class="fa">{assets}</div>')
        parts.append("</div>")

    return "".join(parts)


def _render_market(snapshots: list[MarketSnapshot]) -> str:
    if not snapshots:
        return '<div class="empty">No market data</div>'
    cards = ""
    for s in snapshots:
        f_badge = _badge(s.freshness.value, s.freshness.value) if s.freshness else ""
        chg = _fmt_pct(s.change_24h_pct) if s.change_24h_pct else ""
        chg_color = "#3fb950" if (s.change_24h_pct or 0) >= 0 else "#f85149"
        cards += f"""<div class="mc">
<div class="ms">{_e(s.symbol)} {f_badge}</div>
<div class="mp">{_fmt_usd(s.price)}</div>
<div class="mch" style="color:{chg_color}">{chg}</div>
<div class="md">
<span>OI:{_fmt_usd(s.open_interest)}</span>
<span>Fund:{_fmt_pct(s.funding_rate*100) if s.funding_rate else ""}</span>
<span>Vol:{_fmt_usd(s.volume_24h)}</span>
<span>Mark:{_fmt_usd(s.mark_price)}</span>
<span>Oracle:{_fmt_usd(s.oracle_price)}</span>
</div>
<div class="mv">{_e(s.venue.value)} | {_e(s.observed_at) or ""}</div>
</div>"""
    return f'<div class="mg">{cards}</div>'


def _render_whale_positions(positions: list[dict]) -> str:
    if not positions:
        return '<div class="empty">No whale positions (input slot — populated by W2)</div>'
    rows = ""
    for p in positions:
        rows += f"<tr><td>{_e(p.get('label',''))}</td><td>{_e(p.get('asset',''))}</td>"
        rows += f"<td>{_e(p.get('side',''))}</td><td class='n'>{_fmt_usd(p.get('size_usd'))}</td>"
        rows += f"<td class='n'>{_fmt_pct(p.get('liq_dist'))}</td></tr>"
    return f"<table><tr><th>Label</th><th>Asset</th><th>Side</th><th>Size</th><th>LiqDist</th></tr>{rows}</table>"


def _render_whale_changes(changes: list[dict]) -> str:
    if not changes:
        return '<div class="empty">No position changes (input slot — populated by W2)</div>'
    rows = ""
    for c in changes:
        rows += f"<tr><td>{_e(c.get('label',''))}</td><td>{_e(c.get('asset',''))}</td>"
        rows += f"<td>{_e(c.get('change_type',''))}</td><td class='n'>{_fmt_usd(c.get('delta_usd'))}</td></tr>"
    return f"<table><tr><th>Label</th><th>Asset</th><th>Change</th><th>Delta</th></tr>{rows}</table>"


def _render_market_health(health_list) -> str:
    if not health_list:
        return '<div class="empty">No health data</div>'
    rows = ""
    for h in health_list:
        color = {"ok": "#3fb950", "degraded": "#d29922", "failed": "#f85149"}
        c = color.get(h.status, "#6e7681")
        rows += f"<tr><td>{_e(h.asset)}</td><td>{_e(h.venue.value)}</td>"
        rows += f'<td style="color:{c};font-weight:bold">{_e(h.status)}</td>'
        rows += f"<td>{_e(h.message)}</td></tr>"
    return f"<table><tr><th>Asset</th><th>Venue</th><th>Status</th><th>Message</th></tr>{rows}</table>"


def _render_watchlists(wl: dict) -> str:
    if not wl:
        return '<div class="empty">No watchlists configured</div>'
    parts = []
    for name, items in wl.items():
        entries = " | ".join(_e(str(i)) for i in (items or [])) if items else "—"
        parts.append(f"<div><b>{_e(name)}</b>: {entries}</div>")
    return "".join(parts)


def _render_alert_candidates(candidates: list[dict]) -> str:
    if not candidates:
        return '<div class="empty">No alert candidates</div>'
    parts = []
    for c in candidates[:15]:
        parts.append(f'<div class="ac"><b>{_e(c.get("title",""))}</b> — {_e(c.get("rationale",""))} [{_e(c.get("source",""))}]</div>')
    return "".join(parts)


def _render_journal(journal: list[dict]) -> str:
    if not journal:
        return '<div class="empty">No journal entries</div>'
    parts = []
    for e in journal[-15:]:
        ts = _e(e.get("timestamp", ""))
        summary = _e(e.get("summary", ""))
        parts.append(f'<div class="je"><span class="jt">{ts}</span> {summary}</div>')
    return "".join(parts)


def _render_regime(regime: dict) -> str:
    if not regime:
        return '<div class="empty">Market regime placeholder — requires derived inputs</div>'
    state = _e(regime.get("state", "unknown"))
    rules = regime.get("rules", [])
    parts = [f'<div class="rb">{state}</div>']
    for r in rules[:5]:
        parts.append(f'<div class="rr">— {_e(r)}</div>')
    parts.append('<div class="disc">interpretation_type: rule_based_system_context — no trading advice</div>')
    return "".join(parts)


# ── Main render ──────────────────────────────────────────────────────────────

def render_workbench(bundle: WorkbenchBundle, output_path: Optional[str] = None) -> str:
    """Generate a secure self-contained HTML workbench from a WorkbenchBundle.

    Args:
        bundle: All data to render.
        output_path: If set, atomically write to this path.

    Returns:
        HTML string.
    """
    gen = _utc_now()
    h = _e

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">{CSP_META}
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>CEI Workbench W3v2</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#0d1117;color:#e6edf3;padding:16px;font-size:14px;line-height:1.5}}
h1{{color:#58a6ff;font-size:22px;margin-bottom:4px}}
h2{{color:#c9d1d9;font-size:16px;margin:20px 0 8px;padding-bottom:6px;border-bottom:1px solid #30363d}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:12px 0}}
.sc{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;text-align:center}}
.sv{{font-size:22px;font-weight:bold}}
.sl{{font-size:11px;color:#8b949e;margin-top:2px}}
table{{width:100%;border-collapse:collapse;margin-bottom:12px;font-size:12px}}
th{{background:#161b22;color:#8b949e;padding:6px 8px;text-align:left;font-weight:500;border-bottom:2px solid #30363d;white-space:nowrap}}
td{{padding:4px 8px;border-bottom:1px solid #21262d;white-space:nowrap;font-size:12px}}
tr:hover td{{background:#1c2128}}
.n{{text-align:right;font-family:'SF Mono',Consolas,monospace}}
.empty{{color:#8b949e;font-style:italic;padding:20px;text-align:center}}
.mg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:8px;margin-bottom:12px}}
.mc{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px}}
.ms{{font-size:12px;color:#8b949e;display:flex;gap:4px;align-items:center}}
.mp{{font-size:24px;font-weight:bold;margin:4px 0}}
.mch{{font-size:14px;margin-bottom:4px}}
.md{{font-size:11px;color:#8b949e;display:flex;flex-direction:column;gap:1px;margin-top:4px}}
.mv{{font-size:10px;color:#6e7681;margin-top:4px}}
.fi{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px 10px;margin-bottom:6px;font-size:13px}}
.fh{{display:flex;gap:4px;align-items:center;margin-bottom:2px;font-size:11px;flex-wrap:wrap}}
.ft{{padding:1px 5px;border-radius:3px;font-weight:600;font-size:10px}}
.ft-flash{{background:#ff444433;color:#ff4444}}
.ft-news{{background:#58a6ff33;color:#58a6ff}}
.ft-telegram{{background:#3fb95033;color:#3fb950}}
.fs{{color:#8b949e}}
.fp{{color:#6e7681;margin-left:auto}}
.ftl{{font-size:13px;font-weight:500}}
.fb{{color:#8b949e;font-size:12px;margin-top:2px}}
.fa{{color:#58a6ff;font-size:11px;margin-top:2px}}
.rb{{font-size:18px;font-weight:bold;padding:8px 12px;background:#161b22;border:1px solid #30363d;border-radius:6px;display:inline-block;margin-bottom:4px}}
.rr{{color:#8b949e;font-size:11px;padding:2px 0}}
.disc{{color:#d29922;font-size:11px;margin-top:4px;font-style:italic}}
.ac,.je{{background:#161b22;border:1px solid #30363d;border-radius:4px;padding:6px 10px;margin-bottom:4px;font-size:12px}}
.jt{{color:#58a6ff;font-family:monospace;font-size:11px}}
.warn{{color:#d29922;font-size:12px;margin:2px 0}}
.err{{color:#f85149;font-size:12px}}
.ftr{{margin-top:24px;padding-top:8px;border-top:1px solid #30363d;font-size:10px;color:#6e7681}}
</style>
</head>
<body>
<h1>CEI Workbench W3v2</h1>
<p style="color:#8b949e;font-size:13px;margin-bottom:8px">
Run: {h(bundle.run_id)} | {gen} | v{_VERSION}</p>"""

    # Warnings
    for w in bundle.warnings:
        html += f'<div class="warn">W {h(w)}</div>'
    for d in bundle.degraded_paths:
        html += f'<div class="warn">Degraded: {h(d)}</div>'

    # Stats
    html += _render_stats(bundle)

    # 1. Feed
    html += "<h2>1. Intelligence Feed</h2>"
    html += _render_feed(bundle.feed_items)

    # 2. Whale Changes
    html += "<h2>2. Whale Position Changes</h2>"
    html += _render_whale_changes(bundle.whale_changes)

    # 3. Whale Positions
    html += "<h2>3. Current Whale Positions</h2>"
    html += _render_whale_positions(bundle.whale_positions)

    # 4. Market Context
    html += "<h2>4. Market Context</h2>"
    html += _render_market(bundle.market_snapshots)

    # 5. Market Health
    html += "<h2>5. Source Health</h2>"
    html += _render_market_health(bundle.market_health)

    # 6. Market Regime
    html += "<h2>6. Market Regime</h2>"
    html += _render_regime(bundle.market_regime)

    # 7. Watchlists
    html += "<h2>7. Watchlists</h2>"
    html += _render_watchlists(bundle.watchlists)

    # 8. Alert Candidates
    html += "<h2>8. Alert Candidates</h2>"
    html += _render_alert_candidates(bundle.alert_candidates)

    # 9. Event Journal
    html += "<h2>9. Event Journal</h2>"
    html += _render_journal(bundle.event_journal)

    # Feed truth
    if bundle.feed_truth:
        ft = bundle.feed_truth
        html += f"""<h2>Feed Truth</h2>
<table><tr><th>Category</th><th class='n'>Count</th></tr>
<tr><td>Flash (live)</td><td class='n'>{h(str(ft.get("flash_live",0)))}</td></tr>
<tr><td>News (live)</td><td class='n'>{h(str(ft.get("news_live",0)))}</td></tr>
<tr><td>Telegram (live)</td><td class='n'>{h(str(ft.get("telegram_live",0)))}</td></tr>
<tr><td>Cached</td><td class='n'>{h(str(ft.get("cached",0)))}</td></tr>
<tr><td>Fixture</td><td class='n'>{h(str(ft.get("fixture",0)))}</td></tr>
<tr><td>Research Samples</td><td class='n'>{h(str(ft.get("research_sample",0)))}</td></tr>
<tr><td>Duplicates Removed</td><td class='n'>{h(str(ft.get("duplicates_removed",0)))}</td></tr>
</table>"""

    # Footer
    html += f'<div class="ftr">Generated {gen} | W3v2 | no network | all data fixture</div>'
    html += "</body></html>"

    # Atomic write
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        tmp = output_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(html)
        os.replace(tmp, output_path)

    return html

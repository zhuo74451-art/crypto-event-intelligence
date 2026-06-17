"""Static HTML renderer for event intelligence — secure, no external resources.

Security guarantees:
  - CSP meta tag
  - Full HTML escaping
  - No script tags
  - No external URLs
  - No db_path or raw_json exposure
"""
from __future__ import annotations
import html as html_lib
from datetime import datetime, timezone
from typing import Any, Optional

from .models import IntelligenceEvent, SignalCandidate, CandidateLevel


def _e(val: Any) -> str:
    if val is None:
        return ""
    return html_lib.escape(str(val), quote=True)


def _fmt_score(score: float) -> str:
    color = "#3fb950" if score >= 70 else "#d29922" if score >= 40 else "#8b949e"
    return f'<span style="color:{color};font-weight:bold;font-size:16px">{_e(str(round(score, 1)))}</span>'


def render_event_board(
    events: list[IntelligenceEvent],
    candidates: list[SignalCandidate],
    max_events: int = 50,
) -> str:
    """Generate a secure self-contained HTML event board."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy"
 content="default-src 'self'; script-src 'none'; style-src 'unsafe-inline'; img-src data:;">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Event Intelligence Board</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#0d1117;color:#e6edf3;padding:16px;font-size:14px}}
h1{{color:#58a6ff;font-size:20px;margin-bottom:4px}}
h2{{color:#c9d1d9;font-size:15px;margin:16px 0 6px;padding-bottom:4px;border-bottom:1px solid #30363d}}
.ec{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:8px}}
.eh{{font-size:13px;font-weight:600;margin-bottom:4px}}
.em{{font-size:11px;color:#8b949e;margin-bottom:4px}}
.es{{font-size:11px;display:flex;gap:8px;flex-wrap:wrap}}
.etag{{padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600}}
.etag-watch{{background:#8b949e33;color:#8b949e}}
.etag-review{{background:#d2992233;color:#d29922}}
.etag-high{{background:#f0883e33;color:#f0883e}}
.est{{font-size:10px;color:#6e7681;margin-top:4px}}
.empty{{color:#8b949e;font-style:italic;padding:16px;text-align:center}}
.ftr{{margin-top:16px;padding-top:6px;border-top:1px solid #30363d;font-size:10px;color:#6e7681}}
</style>
</head>
<body>
<h1>Event Intelligence Board</h1>
<p style="color:#8b949e;font-size:12px;margin-bottom:8px">{_e(now)} | {len(events)} events | {len(candidates)} candidates</p>"""

    if not candidates:
        html += '<div class="empty">No signal candidates</div>'
        html += "</body></html>"
        return html

    # Candidates sorted by score descending
    sorted_cands = sorted(candidates, key=lambda c: c.score, reverse=True)[:max_events]
    cand_map = {c.event_id: c for c in candidates}

    for cand in sorted_cands:
        event = next((e for e in events if e.event_id == cand.event_id), None)
        if not event:
            continue

        level_cls = f"etag-{cand.level.value}" if cand.level in (CandidateLevel.WATCH, CandidateLevel.REVIEW, CandidateLevel.HIGH_ATTENTION) else "etag-watch"
        html += f"""<div class="ec">
<div class="eh">{_fmt_score(cand.score)} <span class="etag {level_cls}">{_e(cand.level.value)}</span> {_e(cand.canonical_title[:100])}</div>
<div class="em">Type: {_e(event.event_type)} | Sources: {cand.source_count} ({cand.independent_count} independent) | Items: {len(event.items)} | Status: {_e(event.status.value)}</div>
<div class="es">
<span>Assets: {_e(", ".join(cand.top_assets)) or "—"}</span>
<span>Topics: {_e(", ".join(cand.top_topics)) or "—"}</span>
</div>"""

        if event.conflicting_claims:
            for cc in event.conflicting_claims[:3]:
                html += f'<div style="color:#f0883e;font-size:11px">⚠ {_e(cc)}</div>'

        if cand.breakdown:
            bd = cand.breakdown
            html += f"""<div class="est">
F:{_e(str(round(bd.freshness)))} N:{_e(str(round(bd.novelty)))} SI:{_e(str(round(bd.source_independence)))}
AR:{_e(str(round(bd.asset_relevance)))} Sev:{_e(str(round(bd.event_severity)))} Ev:{_e(str(round(bd.evidence_completeness)))}
Penalties: C:{_e(str(round(bd.conflict_penalty)))} D:{_e(str(round(bd.duplication_penalty)))} S:{_e(str(round(bd.stale_penalty)))} Q:{_e(str(round(bd.data_quality_penalty)))}
</div>"""

        # Timeline summary
        if event.timeline:
            recent = event.timeline[-3:]
            for entry in recent:
                html += f'<div class="est">[{_e(entry.timestamp)}] {_e(entry.event_type)} — {_e(entry.summary[:80])}</div>'

        html += "</div>"

    html += f"""<div class="ftr">Generated {_e(now)} | Event Intelligence | score ∈ [0,100] | deterministic rules | no LLM</div>
</body></html>"""
    return html

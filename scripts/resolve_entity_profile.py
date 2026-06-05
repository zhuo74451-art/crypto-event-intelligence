"""v1.6H: Entity Profile Resolver — temporal-aware identity lookup."""
import sqlite3, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "entity_profiles.sqlite"
CN_TZ = timezone(timedelta(hours=8))

def resolve(address: str, asset: str = "", entity_name: str = "") -> dict:
    """Resolve entity profile. Returns temporal-aware labels."""
    if not DB_PATH.exists():
        return {"display_name": entity_name or address[:12], "profile_label_cn": "",
                "profile_note_cn": "", "confidence": "low", "evidence_count": 0,
                "title_safe_label": "", "note_safe_label": "", "temporal_warning": "",
                "conflict_flag": False, "sources_used": []}

    conn = sqlite3.connect(str(DB_PATH))
    addr_key = address[:42] if address.startswith("0x") else address[:16]

    # Get profile
    profile = conn.execute(
        "SELECT * FROM entity_profiles WHERE address LIKE ?",
        (addr_key + "%",)).fetchone()

    # Get current labels (can_use_in_title=1)
    cur_labels = conn.execute(
        "SELECT label_text_cn FROM entity_labels WHERE address LIKE ? AND can_use_in_title=1 AND label_time_scope='current'",
        (addr_key + "%",)).fetchall()

    # Get historical labels (can_use_in_note=1)
    hist_labels = conn.execute(
        "SELECT label_text_cn, temporal_warning, source_time, source_ref, conflict_with_current_position FROM entity_labels WHERE address LIKE ? AND can_use_in_note=1 AND label_time_scope='historical'",
        (addr_key + "%",)).fetchall()

    conn.close()

    display_name = profile[3] if profile else (entity_name or address[:12])
    profile_summary = profile[5] if profile else ""
    confidence = profile[7] if profile else "low"

    # Title-safe: only current labels
    title_safe = cur_labels[0][0] if cur_labels else ""

    # Note-safe: historical labels with temporal qualifiers
    note_parts = []
    temporal_warnings = []
    conflict = False

    if profile_summary:
        note_parts.append(profile_summary)

    seen_labels = set()
    for hl in hist_labels:
        label_text = hl[0]; warning = hl[1]; conflict_flag = hl[4]
        if conflict_flag:
            conflict = True
            temporal_warnings.append(f"历史标签与当前仓位方向不同，以最新持仓为准。")
        elif label_text not in seen_labels:
            seen_labels.add(label_text)
            # Always use "曾经/历史" qualifier, keep it concise
            note_parts.append(f"曾被公开样本标记为「{label_text[:60]}」")

    # Limit to top 2 deduped historical labels + profile summary
    if len(note_parts) > 3:
        note_parts = note_parts[:3]
    note_text = "；".join(note_parts) if note_parts else ""
    if temporal_warnings:
        note_text += "。" + "。".join(temporal_warnings) if note_text else "。".join(temporal_warnings)

    return {
        "display_name": display_name,
        "profile_label_cn": note_text[:120],
        "profile_note_cn": note_text[:200],
        "confidence": confidence,
        "evidence_count": len(hist_labels),
        "title_safe_label": title_safe,
        "note_safe_label": note_text[:200],
        "temporal_warning": "；".join(temporal_warnings),
        "conflict_flag": conflict,
        "sources_used": [hl[3] for hl in hist_labels],
    }

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--address", required=True)
    p.add_argument("--asset", default="")
    p.add_argument("--entity", default="")
    args = p.parse_args()
    result = resolve(args.address, args.asset, args.entity)
    print(json.dumps(result, ensure_ascii=False, indent=2))

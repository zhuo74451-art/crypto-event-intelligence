#!/usr/bin/env python3
"""
Generate Research Reports — produces auto-generated markdown reports from research data.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def generate_claim_report(claims_path: str, output_path: str):
    """Generate a claim registry report from claims JSONL."""
    if not os.path.isfile(claims_path):
        print(f"No claims at {claims_path}")
        return

    status_counts = {}
    claims = []
    with open(claims_path) as f:
        for line in f:
            claim = json.loads(line)
            claims.append(claim)
            status = claim.get("claim_status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

    lines = [
        "# Claim Registry Report V1",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        f"**Total Claims**: {len(claims)}",
        "",
        "## Status Distribution",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"| {status} | {count} |")

    lines.extend(["", "## Sample Claims (first 5)", ""])
    for claim in claims[:5]:
        lines.append(f"- **{claim.get('claim_id')}**: {claim.get('subject')} → {claim.get('object')} *({claim.get('claim_status')})*")
        if claim.get("limitations"):
            for lim in claim["limitations"]:
                lines.append(f"  - Limitation: {lim}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Claim report written to {output_path}")


def generate_graph_report(edges_path: str, output_path: str):
    """Generate evidence graph report."""
    if not os.path.isfile(edges_path):
        print(f"No edges at {edges_path}")
        return

    role_counts = {}
    edges = []
    with open(edges_path) as f:
        for line in f:
            edge = json.loads(line)
            edges.append(edge)
            role = edge.get("evidence_role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1

    lines = [
        "# Evidence Graph Report V1",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        f"**Total Evidence Edges**: {len(edges)}",
        "",
        "## Role Distribution",
        "",
        "| Role | Count |",
        "|------|-------|",
    ]
    for role, count in sorted(role_counts.items()):
        lines.append(f"| {role} | {count} |")

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Graph report written to {output_path}")


def generate_conflict_report(conflicts_path: str, output_path: str):
    """Generate conflict report."""
    if not os.path.isfile(conflicts_path):
        print(f"No conflicts at {conflicts_path}")
        return

    conflicts = []
    with open(conflicts_path) as f:
        for line in f:
            conflicts.append(json.loads(line))

    lines = [
        "# Conflict Report V1",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        f"**Total Conflict Sets**: {len(conflicts)}",
        "",
        "## Conflict Details",
        "",
    ]
    for c in conflicts:
        lines.append(f"- **{c.get('conflict_set_id')}** ({c.get('conflict_type')})")
        lines.append(f"  - Key: {c.get('conflict_key')}")
        lines.append(f"  - Status: {c.get('conflict_status')}")
        lines.append(f"  - Claims: {', '.join(c.get('claim_ids', []))}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Conflict report written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Research Reports")
    parser.add_argument("--research-output", default="data/intelligence/research")
    args = parser.parse_args()

    base = os.path.join(PROJECT_ROOT, args.research_output)

    generate_claim_report(
        os.path.join(base, "claims", "research_claims_v1.jsonl"),
        os.path.join(base, "reports", "CLAIM_REGISTRY_REPORT_V1.md"),
    )
    generate_graph_report(
        os.path.join(base, "evidence", "evidence_edges_v1.jsonl"),
        os.path.join(base, "reports", "EVIDENCE_GRAPH_REPORT_V1.md"),
    )
    generate_conflict_report(
        os.path.join(base, "conflicts", "conflict_sets_v1.jsonl"),
        os.path.join(base, "reports", "CONFLICT_REPORT_V1.md"),
    )

    print("Reports generated.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate Integration Report — produces integration report markdown files.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def generate_gate_report(gate_results: list, output_path: str):
    """Generate a markdown report from gate results."""
    lines = [
        "# Integration Gate Report V1",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "## Gate Results",
        "",
        "| Gate | Status | Details |",
        "|------|--------|---------|",
    ]
    for r in gate_results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        lines.append(f"| {r['gate']} | {status} | {r.get('details', '')} |")

    all_pass = all(r["passed"] for r in gate_results)
    lines.append(f"\n## Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Gate report written to {output_path}")


def generate_run_report(run_results: dict, output_path: str):
    """Generate a markdown report from pipeline run results."""
    lines = [
        "# Internal Pipeline Run Report",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "## Run Summary",
        "",
        f"- **Run ID**: {run_results.get('run_id', 'N/A')}",
        f"- **Status**: {run_results.get('status', 'N/A')}",
        f"- **Claims**: {run_results.get('claims', 0)}",
        f"- **Evidence Edges**: {run_results.get('edges', 0)}",
        f"- **Conflict Sets**: {run_results.get('conflicts', 0)}",
        f"- **Candidates**: {run_results.get('candidates', 0)}",
        f"- **Dossiers**: {run_results.get('dossiers', 0)}",
        "",
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Run report written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Integration Reports")
    parser.add_argument("--integration-output", default="data/intelligence/integration")
    parser.add_argument("--research-output", default="data/intelligence/research")
    args = parser.parse_args()

    integration_dir = os.path.join(PROJECT_ROOT, args.integration_output)
    research_dir = os.path.join(PROJECT_ROOT, args.research_output)

    # Generate empty gate report
    gate_path = os.path.join(integration_dir, "reports", "INTEGRATION_GATE_REPORT_V1.md")
    generate_gate_report([], gate_path)

    # Generate empty run report
    run_path = os.path.join(integration_dir, "reports", "END_TO_END_RUN_REPORT_V1.md")
    generate_run_report({"status": "sample"}, run_path)

    print("Reports generated.")


if __name__ == "__main__":
    main()

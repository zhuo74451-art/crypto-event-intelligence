#!/usr/bin/env python3
"""Validate release documentation integrity.

Checks that all required docs exist, contain expected content,
and no prohibited patterns appear.
"""

import os
import re
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_FILES = [
    "README.md",
    "docs/PROJECT_OVERVIEW.md",
    "docs/ARCHITECTURE.md",
    "docs/INDEX.md",
    "docs/PROJECT_STATUS.md",
    "docs/releases/week1_raw_research_dataset_v1_release.md",
    "docs/audits/week1_raw_research_dataset_v1_release_evidence.md",
    "docs/handoffs/EXTERNAL_AI_REVIEW_PACKET_V1.md",
    "docs/roadmap/NEXT_PHASE_PLAN_V1.md",
    "CHANGELOG.md",
    "research/validate_manifest.py",
    "research/validate_week1_price_dataset.py",
    "research/validate_week1_raw_research_dataset_v1.py",
    "research/build_week1_raw_research_dataset_v1.py",
    "scripts/validate_release_docs_v1.py",
]

EXPECTED_SHAS = {
    "9c28c9308e42ea8ef822f7eff8a20c4b0e827290",  # main baseline
    "1f332992b2938a355e43f566d8901f00d01d842c",  # manifest
    "d7b908d868957e0165924598e6058fef27eb0b3d",  # price code
    "7188a52dedb54955cd41b187821081e1945c8706",  # price data
    "2d7974bfaf38079de369b020a94f99a0ad807cd9",  # dataset integration
}

WRONG_SHAS = {
    "2d7974bf3a8a917c2cb941122a10f42dbf430933",  # wrong SHA from earlier receipt
}

PROHIBITED_PATTERNS = [
    r"production\s+ready",
    r"trading\s+ready",
    r"guaranteed\s+profit",
    r"buy\s+signal",
    r"sell\s+signal",
    r"risk-free",
]

HISTORICAL_DOCS = [
    "docs/releases/signal_spine_v1_rc1_acceptance.md",
    "docs/audits/signal_spine_v1_repo_audit.md",
]

HISTORICAL_BANNER = (
    "> ⚠ **Historical document.** This report reflects the project at a specific past commit. "
    "Some conclusions (e.g., 'price module not connected', 'Observation/Signal do not exist') "
    "have been superseded by subsequent implementations. "
    "For current status refer to `README.md`, `docs/PROJECT_OVERVIEW.md`, and the Week 1 release evidence."
)


def check_file_exists(path: str) -> bool:
    full = os.path.join(PROJ, path)
    return os.path.isfile(full)


def check_file_content(path: str, pattern: str) -> bool:
    """Check if file contains a regex pattern (case-insensitive)."""
    full = os.path.join(PROJ, path)
    try:
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        return bool(re.search(pattern, content, re.IGNORECASE))
    except (IOError, UnicodeDecodeError):
        return False


def check_markdown_links_exist(path: str) -> list[str]:
    """Verify relative Markdown links point to existing files."""
    full = os.path.join(PROJ, path)
    broken = []
    try:
        with open(full, "r", encoding="utf-8") as f:
            for line in f:
                for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
                    link = m.group(2)
                    if link.startswith("http"):
                        continue
                    # Resolve relative to file's directory
                    link_path = os.path.normpath(os.path.join(os.path.dirname(path), link))
                    target = os.path.join(PROJ, link_path)
                    if not os.path.isfile(target):
                        broken.append(f"{path}: broken link '{link}' -> {link_path}")
    except (IOError, UnicodeDecodeError):
        pass
    return broken


def main():
    violations = []

    # 1. Required files exist
    for f in REQUIRED_FILES:
        if not check_file_exists(f):
            violations.append(f"Missing required file: {f}")

    # 2. README exists
    if not check_file_exists("README.md"):
        violations.append("README.md is missing")

    # 3. Expected SHAs appear in PROJECT_OVERVIEW
    if check_file_exists("docs/PROJECT_OVERVIEW.md"):
        with open(os.path.join(PROJ, "docs/PROJECT_OVERVIEW.md"), "r", encoding="utf-8") as f:
            content = f.read()
        for sha in EXPECTED_SHAS:
            if sha not in content:
                violations.append(f"docs/PROJECT_OVERVIEW.md missing SHA: {sha}")
        for sha in WRONG_SHAS:
            if sha in content:
                violations.append(f"docs/PROJECT_OVERVIEW.md contains wrong SHA: {sha}")

    # 4. README does not contain production/trading ready claims
    readme_path = os.path.join(PROJ, "README.md")
    if os.path.isfile(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        for pat in PROHIBITED_PATTERNS:
            if re.search(pat, readme_content, re.IGNORECASE):
                violations.append(f"README.md contains prohibited pattern: '{pat}'")

    # 5. Release evidence mentions network timeout
    evidence_path = os.path.join(PROJ, "docs/releases/week1_raw_research_dataset_v1_release.md")
    if os.path.isfile(evidence_path):
        with open(evidence_path, "r", encoding="utf-8") as f:
            evidence = f.read()
        if "network timeout" not in evidence and "网络超时" not in evidence:
            violations.append("Release evidence missing network timeout disclosure")

    # 6. External AI packet contains fact/inference/design choice sections
    ai_packet = os.path.join(PROJ, "docs/handoffs/EXTERNAL_AI_REVIEW_PACKET_V1.md")
    if os.path.isfile(ai_packet):
        with open(ai_packet, "r", encoding="utf-8") as f:
            ai = f.read()
        for section in ["### Facts", "### Design Choices", "### Inferences"]:
            if section not in ai:
                violations.append(f"AI packet missing section: {section}")

    # 7. Roadmap contains Phases 0-5
    roadmap = os.path.join(PROJ, "docs/roadmap/NEXT_PHASE_PLAN_V1.md")
    if os.path.isfile(roadmap):
        with open(roadmap, "r", encoding="utf-8") as f:
            r = f.read()
        for phase in ["Phase 0", "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5"]:
            if phase not in r:
                violations.append(f"Roadmap missing {phase}")

    # 8. Historical docs have superseded banners
    for hdoc in HISTORICAL_DOCS:
        hpath = os.path.join(PROJ, hdoc)
        if os.path.isfile(hpath):
            with open(hpath, "r", encoding="utf-8") as f:
                hcontent = f.read()
            # Check for banner-like text
            if "Historical document" not in hcontent and "superseded" not in hcontent:
                violations.append(f"Historical doc missing superseded banner: {hdoc}")
        else:
            violations.append(f"Historical doc not found: {hdoc}")

    # 9. Markdown link integrity
    md_files = ["README.md", "docs/PROJECT_OVERVIEW.md", "docs/ARCHITECTURE.md",
                "docs/INDEX.md", "docs/PROJECT_STATUS.md", "docs/releases/week1_raw_research_dataset_v1_release.md",
                "docs/audits/week1_raw_research_dataset_v1_release_evidence.md",
                "docs/handoffs/EXTERNAL_AI_REVIEW_PACKET_V1.md",
                "docs/roadmap/NEXT_PHASE_PLAN_V1.md", "CHANGELOG.md"]
    for mf in md_files:
        broken = check_markdown_links_exist(mf)
        violations.extend(broken)

    if violations:
        print(f"Documentation violations ({len(violations)}):")
        for v in violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("[PASS] All documentation checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()

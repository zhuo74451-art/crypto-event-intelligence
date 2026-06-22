#!/usr/bin/env python3
"""Validate mainline documentation integrity.

Checks that all canonical mainline docs exist, contain expected content,
and no legacy planning documents remain in current navigation.
"""

import os
import re
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CANONICAL_FILES = [
    "README.md",
    "PROJECT_MAINLINE.md",
    "docs/ARCHITECTURE.md",
    "docs/INDEX.md",
    "docs/PROJECT_STATUS.md",
]

PROHIBITED_LEGACY_DOCS = [
    "docs/PERSONAL_USE_RC1_PLAN.md",
    "docs/PERSONAL_USE_RC1_STATUS.md",
    "docs/PERSONAL_USE_RC1_RUNBOOK_TEMPLATE.md",
    "docs/roadmap/NEXT_PHASE_PLAN_V1.md",
    "docs/handoffs/EXTERNAL_AI_REVIEW_PACKET_V1.md",
]

PROHIBITED_PATTERNS_IN_CURRENT_DOCS = [
    r"Personal-Use RC1",
    r"NEXT_PHASE_PLAN_V1",
    r"Phase 0",
    r"Phase 1",
    r"Phase 2",
    r"Phase 3",
    r"Phase 4",
    r"Phase 5",
    r"EXTERNAL_AI_REVIEW_PACKET_V1",
    r"personal-use Telegram crypto signal tool",
]

HISTORICAL_DIRS = [
    "docs/releases/",
    "docs/audits/",
]

HISTORICAL_CONTEXT_WORDS = [
    "不再", "no longer", "此前", "historical",
    "superseded", "past", "previous", "old",
]


def is_historical(path):
    return any(path.startswith(d) for d in HISTORICAL_DIRS)


def check_file_exists(path):
    full = os.path.join(PROJ, path)
    return os.path.isfile(full)


def read_file_content(path):
    full = os.path.join(PROJ, path)
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, UnicodeDecodeError):
        return ""


def is_in_historical_context(line):
    """Check if a line frames a legacy pattern as historical/superseded."""
    lower = line.lower()
    return any(w in lower for w in HISTORICAL_CONTEXT_WORDS)


def main():
    violations = []

    # 1-2. All canonical files exist and have content
    for f in CANONICAL_FILES:
        if not check_file_exists(f):
            violations.append(f"Missing canonical file: {f}")
        else:
            content = read_file_content(f)
            if len(content.strip()) < 10:
                violations.append(f"Canonical file is empty or stub: {f}")
            else:
                print(f"  [OK] {f}")

    # 3. README explicitly links PROJECT_MAINLINE.md
    readme = read_file_content("README.md")
    if not re.search(r"PROJECT_MAINLINE\.md", readme):
        violations.append("README.md does not link PROJECT_MAINLINE.md")

    # 4. No prohibited legacy doc files exist
    for f in PROHIBITED_LEGACY_DOCS:
        if check_file_exists(f):
            violations.append(f"Prohibited legacy document still exists: {f}")

    # 5. Prohibited patterns must not appear as current planning
    for f in CANONICAL_FILES:
        content = read_file_content(f)
        lines = content.split("\n")
        for pat in PROHIBITED_PATTERNS_IN_CURRENT_DOCS:
            for i, line in enumerate(lines, 1):
                if re.search(pat, line, re.IGNORECASE):
                    if is_in_historical_context(line):
                        continue
                    violations.append(
                        f"{f}:{i} contains legacy pattern '{pat}' as current planning"
                    )

    # 6. Canonical docs should not reference deleted legacy docs
    for f in CANONICAL_FILES:
        content = read_file_content(f)
        for ref in PROHIBITED_LEGACY_DOCS:
            name = os.path.splitext(os.path.basename(ref))[0]
            if name.lower() in content.lower():
                violations.append(
                    f"{f} references deleted legacy document '{name}'"
                )

    # 7. Canonical docs should not cite fixed old test counts as latest fact
    for f in CANONICAL_FILES:
        content = read_file_content(f)
        for i, line in enumerate(content.split("\n"), 1):
            if re.search(r"\d{2,3}\s+tests?", line, re.IGNORECASE):
                if not is_in_historical_context(line):
                    violations.append(
                        f"{f}:{i} may cite fixed test count as current fact: "
                        f"'{line.strip()}'"
                    )

    # 8. Historical release material does not gain planning authority
    for f in CANONICAL_FILES:
        content = read_file_content(f)
        if f == "README.md":
            has_hist_links = False
            for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
                link = m.group(2)
                if is_historical(link):
                    has_hist_links = True
            if has_hist_links and not any(
                w in content.lower() for w in ["historical", "past"]
            ):
                violations.append(
                    "README.md links to historical release/audit material "
                    "without historical disclaimer"
                )

    if violations:
        print(f"\nDocumentation violations ({len(violations)}):")
        for v in violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("\n[PASS] All mainline documentation checks passed")
        sys.exit(0)


if __name__ == "__main__":
    print("=== Mainline Documentation Validator ===\n")
    main()

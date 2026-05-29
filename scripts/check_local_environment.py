import argparse
import os
import platform
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = ["data", "docs", "results", "scripts"]
REQUIRED_PACKAGES = ["pandas", "requests"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local Python/runtime prerequisites for Crypto Event Intelligence.")
    parser.add_argument("--output", default=str(ROOT / "results" / "local_environment_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "local_environment_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "local_environment_report.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def add_check(rows: list[dict], check: str, actual: str, expected: str, status: str, notes: str = "") -> None:
    rows.append(
        {
            "check": check,
            "actual": actual,
            "expected": expected,
            "status": status,
            "notes": notes,
        }
    )


def package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return ""


def requirements_packages(path: Path) -> list[str]:
    if not path.exists():
        return []
    packages: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        for separator in ["==", ">=", "<=", "~=", ">", "<"]:
            if separator in text:
                text = text.split(separator, 1)[0].strip()
                break
        if text:
            packages.append(text)
    return packages


def build_rows() -> list[dict]:
    rows: list[dict] = []
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    add_check(
        rows,
        "python_version",
        version,
        ">=3.10",
        "pass" if sys.version_info >= (3, 10) else "fail",
    )
    add_check(rows, "platform", platform.platform(), "Windows-compatible local shell", "info")
    add_check(rows, "project_root", str(ROOT), "resolved", "pass" if ROOT.exists() else "fail")

    for dirname in REQUIRED_DIRS:
        path = ROOT / dirname
        add_check(
            rows,
            f"dir_{dirname}",
            "present" if path.exists() and path.is_dir() else "missing",
            "present",
            "pass" if path.exists() and path.is_dir() else "fail",
        )

    for package in REQUIRED_PACKAGES:
        version_text = package_version(package)
        add_check(
            rows,
            f"package_{package}",
            version_text or "missing",
            "installed",
            "pass" if version_text else "fail",
        )

    requirements_path = ROOT / "requirements.txt"
    add_check(
        rows,
        "requirements_txt",
        "present" if requirements_path.exists() else "missing",
        "present",
        "pass" if requirements_path.exists() else "fail",
    )
    declared_packages = requirements_packages(requirements_path)
    missing_from_requirements = sorted(set(REQUIRED_PACKAGES) - set(declared_packages))
    add_check(
        rows,
        "requirements_declares_required_packages",
        ",".join(missing_from_requirements) if missing_from_requirements else "all declared",
        "all declared",
        "pass" if not missing_from_requirements else "fail",
    )

    add_check(
        rows,
        "openrouter_api_key_env",
        "set" if os.environ.get("OPENROUTER_API_KEY", "").strip() else "missing",
        "set only when querying Claude",
        "info",
        "Missing is acceptable for local offline gate runs.",
    )
    return rows


def render_markdown(rows: list[dict]) -> str:
    fail_count = sum(1 for row in rows if row["status"] == "fail")
    lines = [
        "# Local Environment Report",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        f"overall_status: {'pass' if fail_count == 0 else 'fail'}",
        f"fail_count: {fail_count}",
        "",
        "| check | actual | expected | status | notes |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        notes = str(row.get("notes", "")).replace("|", "\\|")
        actual = str(row.get("actual", "")).replace("|", "\\|")
        lines.append(f"| {row['check']} | {actual} | {row['expected']} | {row['status']} | {notes} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = build_rows()
    fail_count = sum(1 for row in rows if row["status"] == "fail")

    output = normalize_path(args.output)
    summary = normalize_path(args.summary)
    markdown_output = normalize_path(args.markdown_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(rows).to_csv(output, index=False)
    pd.DataFrame(
        [
            {
                "overall_status": "pass" if fail_count == 0 else "fail",
                "fail_count": fail_count,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "required_package_count": len(REQUIRED_PACKAGES),
                "required_dir_count": len(REQUIRED_DIRS),
            }
        ]
    ).to_csv(summary, index=False)
    markdown_output.write_text(render_markdown(rows), encoding="utf-8")
    print(f"wrote local environment report to {output}")
    print(f"wrote local environment summary to {summary}")
    print(f"wrote local environment markdown to {markdown_output}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
}

SKIP_SUFFIXES = {
    ".sqlite",
    ".db",
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".gz",
    ".7z",
    ".exe",
    ".dll",
}

SECRET_PATTERNS = [
    (
        "api_key_like",
        re.compile(r"\bsk-[a-z0-9]{2,}(?:-[a-z0-9]+)*-[A-Za-z0-9_-]{24,}\b", re.IGNORECASE),
    ),
    (
        "bearer_token",
        re.compile(r"\bAuthorization\b\s*[:=]\s*[\"']?Bearer\s+([A-Za-z0-9_\-.]{24,})", re.IGNORECASE),
    ),
    (
        "env_secret_assignment",
        re.compile(
            r"\b(OPENROUTER_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|NOTION_TOKEN|DATABASE_URL)\b\s*[:=]\s*[\"']?([A-Za-z0-9_\-./:]{24,})",
            re.IGNORECASE,
        ),
    ),
    (
        "env_secret_assignment_extended",
        re.compile(
            r"\b(ETHERSCAN_API_KEY|TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)\b\s*[:=]\s*[\"']?([A-Za-z0-9_\-:./]{16,})",
            re.IGNORECASE,
        ),
    ),
    (
        "telegram_bot_token",
        re.compile(r"\b\d{7,12}:[A-Za-z0-9_-]{30,}\b"),
    ),
    (
        "password_assignment",
        re.compile(r"\b(password|passwd|pwd)\b\s*[:=]\s*[\"']?([^\s\"',;]{16,})", re.IGNORECASE),
    ),
    (
        "private_key_block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
]

ALLOW_TEXT_FRAGMENTS = [
    "OPENROUTER_API_KEY is missing",
    "OPENROUTER_API_KEY`",
    "$env:OPENROUTER_API_KEY",
    "%OPENROUTER_API_KEY%",
    "{api_key}",
    "replace_with_",
    "your_api_key",
    "your-token",
    "example_token",
    "replace_with_etherscan_api_key",
    "replace_with_new_telegram_bot_token",
    "replace_with_telegram_chat_id",
    "ETHERSCAN_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan project text files for accidentally committed secrets.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(ROOT / "results" / "secret_leak_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "secret_leak_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "secret_leak_report.md"))
    parser.add_argument("--max-file-mb", type=float, default=8.0)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def should_skip(path: Path, root: Path, max_file_bytes: int) -> bool:
    rel_parts = set(path.relative_to(root).parts)
    if rel_parts & SKIP_DIRS:
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    try:
        if path.stat().st_size > max_file_bytes:
            return True
    except OSError:
        return True
    return False


def redacted(value: str) -> str:
    value = value.strip()
    if len(value) <= 12:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def is_allowed(line: str) -> bool:
    return any(fragment in line for fragment in ALLOW_TEXT_FRAGMENTS)


def scan_file(path: Path, root: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    findings = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if is_allowed(line):
            continue
        for secret_type, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(line):
                raw = match.group(0)
                findings.append(
                    {
                        "file": safe_rel(path, root),
                        "line_number": line_number,
                        "secret_type": secret_type,
                        "redacted_match": redacted(raw),
                    }
                )
    return findings


def render_markdown(findings: list[dict]) -> str:
    lines = [
        "# Secret Leak Report",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        f"leak_count: {len(findings)}",
        "",
    ]
    if not findings:
        lines.append("No likely secrets found in scanned project text files.")
        return "\n".join(lines) + "\n"

    lines.extend(["| file | line | type | redacted_match |", "|---|---:|---|---|"])
    for row in findings:
        lines.append(
            f"| `{row['file']}` | {row['line_number']} | {row['secret_type']} | `{row['redacted_match']}` |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    scan_root = normalize_path(args.root)
    output = normalize_path(args.output)
    summary = normalize_path(args.summary)
    markdown_output = normalize_path(args.markdown_output)
    max_file_bytes = int(args.max_file_mb * 1024 * 1024)

    findings: list[dict] = []
    for path in scan_root.rglob("*"):
        if not path.is_file():
            continue
        if should_skip(path, scan_root, max_file_bytes):
            continue
        findings.extend(scan_file(path, scan_root))

    output.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(findings).to_csv(output, index=False)
    pd.DataFrame(
        [
            {
                "scanned_root": str(scan_root),
                "leak_count": len(findings),
                "status": "pass" if not findings else "fail",
            }
        ]
    ).to_csv(summary, index=False)
    markdown_output.write_text(render_markdown(findings), encoding="utf-8")
    print(f"wrote secret leak report to {output}")
    print(f"wrote secret leak summary to {summary}")
    print(f"wrote secret leak markdown to {markdown_output}")
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())

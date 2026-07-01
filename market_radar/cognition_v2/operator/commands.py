"""Bounded operator commands for cognition_v2.

No scheduler, daemon, network provider, UI, or public output.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from market_radar.cognition_v2.persistence.models import (
    Base,
    create_cognition_engine,
    make_cognition_session_factory,
    cognition_session_scope,
)


def cmd_db_initialize(db_path: str) -> str:
    """Initialize the database schema."""
    engine = create_cognition_engine(db_path=db_path)
    engine.dispose()
    return f"Database initialized at {db_path}"


def cmd_db_migrate(db_path: str) -> str:
    """Run database migrations (creates tables if not exist)."""
    from market_radar.cognition_v2.persistence.alembic_helpers import verify_alembic_upgrade
    import os

    alembic_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "persistence",
        "alembic",
    )
    result = verify_alembic_upgrade(alembic_dir)
    if result:
        return "Migration applied successfully"
    return "Migration failed"


def cmd_db_status(db_path: str) -> str:
    """Show database status — table count and row estimates."""
    from sqlalchemy import text
    engine = create_cognition_engine(db_path=db_path)
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ).fetchall()
        table_names = [t[0] for t in tables]
    engine.dispose()
    return f"Database at {db_path}: {len(table_names)} tables: {', '.join(table_names)}"


def cmd_schema_doctor(db_path: str) -> List[str]:
    """Check schema integrity — expected vs actual tables."""
    engine = create_cognition_engine(db_path=db_path)
    expected = set(Base.metadata.tables.keys())
    from sqlalchemy import text
    with engine.connect() as conn:
        actual = {
            t[0] for t in
            conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        }
    engine.dispose()
    missing = expected - actual
    extra = actual - expected
    issues = []
    if missing:
        issues.append(f"Missing tables: {sorted(missing)}")
    if extra:
        issues.append(f"Extra tables: {sorted(extra)}")
    if not issues:
        issues.append("Schema is healthy")
    return issues


def cmd_validate_lifecycle() -> List[str]:
    """Validate lifecycle state graph completeness."""
    from market_radar.cognition_v2.lifecycle.service import LifecycleValidator
    validator = LifecycleValidator()
    issues = []
    for state in validator.all_states():
        transitions = validator.get_legal_transitions(state)
        if not transitions:
            issues.append(f"State {state.value} has no outgoing transitions")
    if not issues:
        issues.append("Lifecycle graph is complete")
    return issues


def cmd_inspect_thesis(db_path: str, thesis_id: str) -> str:
    """Read-only inspect a thesis."""
    engine = create_cognition_engine(db_path=db_path)
    factory = make_cognition_session_factory(engine)
    from market_radar.cognition_v2.persistence.models import ThesisModel
    with cognition_session_scope(factory) as s:
        thesis = s.query(ThesisModel).filter(ThesisModel.id == thesis_id).first()
        if thesis is None:
            engine.dispose()
            return f"Thesis {thesis_id} not found"
        result = (
            f"Thesis {thesis.id}: state={thesis.lifecycle_state}, "
            f"version={thesis.version}, class={thesis.claim_class}, "
            f"summary={thesis.summary[:100]}..."
        )
        engine.dispose()
        return result


def cmd_validate_manifest(manifest_path: str) -> str:
    """Validate a manifest file (JSON)."""
    import json
    try:
        with open(manifest_path) as f:
            data = json.load(f)
        from market_radar.cognition_v2.domain.contracts import HistoricalCaseManifest
        manifest = HistoricalCaseManifest(**data)
        return f"Manifest valid: case_id={manifest.case_id}, title={manifest.title}"
    except Exception as e:
        return f"Manifest validation failed: {e}"


def main(argv: Optional[List[str]] = None) -> None:
    """Bounded CLI entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Cognition v2 operator commands")
    parser.add_argument("--db", default=":memory:", help="Database path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("db-init", help="Initialize database")
    subparsers.add_parser("db-migrate", help="Run database migration")
    subparsers.add_parser("db-status", help="Show database status")
    subparsers.add_parser("schema-doctor", help="Check schema integrity")
    subparsers.add_parser("lifecycle-validate", help="Validate lifecycle graph")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a thesis")
    inspect_parser.add_argument("thesis_id", help="Thesis ID to inspect")

    validate_parser = subparsers.add_parser("validate-manifest", help="Validate a manifest file")
    validate_parser.add_argument("manifest_path", help="Path to manifest JSON file")

    args = parser.parse_args(argv)

    if args.command == "db-init":
        print(cmd_db_initialize(args.db))
    elif args.command == "db-migrate":
        print(cmd_db_migrate(args.db))
    elif args.command == "db-status":
        print(cmd_db_status(args.db))
    elif args.command == "schema-doctor":
        for issue in cmd_schema_doctor(args.db):
            print(issue)
    elif args.command == "lifecycle-validate":
        for issue in cmd_validate_lifecycle():
            print(issue)
    elif args.command == "inspect" and hasattr(args, "thesis_id"):
        print(cmd_inspect_thesis(args.db, args.thesis_id))
    elif args.command == "validate-manifest" and hasattr(args, "manifest_path"):
        print(cmd_validate_manifest(args.manifest_path))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

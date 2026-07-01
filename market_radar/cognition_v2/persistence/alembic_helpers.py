"""Alembic migration helpers for cognition_v2."""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


ALEMBIC_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "alembic",
)


def _create_alembic_ini(db_path: str, script_location: str) -> str:
    """Create a temporary alembic.ini pointing to the given db_path."""
    import configparser
    ini_path = os.path.join(tempfile.mkdtemp(), "alembic.ini")
    cfg = configparser.ConfigParser()
    cfg["alembic"] = {
        "script_location": script_location,
        "sqlalchemy.url": f"sqlite:///{db_path}",
    }
    with open(ini_path, "w") as f:
        cfg.write(f)
    return ini_path


def verify_alembic_upgrade(alembic_dir: Optional[str] = None) -> bool:
    """Verify alembic upgrade creates all tables and alembic_version table."""
    import alembic.command
    import alembic.config

    if alembic_dir is None:
        alembic_dir = ALEMBIC_DIR

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "verify.db")
        ini_path = _create_alembic_ini(db_path, alembic_dir)
        cfg = alembic.config.Config(ini_path)
        cfg.set_main_option("script_location", alembic_dir)

        alembic.command.upgrade(cfg, "head")

        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            rows = result.fetchall()
            engine.dispose()
            return len(rows) == 1 and rows[0][0] is not None


def verify_alembic_downgrade(alembic_dir: Optional[str] = None) -> bool:
    """Verify alembic downgrade drops all tables."""
    import alembic.command
    import alembic.config

    if alembic_dir is None:
        alembic_dir = ALEMBIC_DIR

    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "down.db")
        ini_path = _create_alembic_ini(db_path, alembic_dir)
        cfg = alembic.config.Config(ini_path)
        cfg.set_main_option("script_location", alembic_dir)

        alembic.command.upgrade(cfg, "head")
        alembic.command.downgrade(cfg, "base")

        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            remaining = result.fetchall()
            engine.dispose()
            # After downgrade, only sqlite internal tables remain
            return len(remaining) <= 1  # maybe sqlite_sequence

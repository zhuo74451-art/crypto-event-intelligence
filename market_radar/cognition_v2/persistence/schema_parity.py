"""Schema parity validator — compares migration-created DB against ORM metadata.

R19: automated migration/ORM schema parity.
"""

from __future__ import annotations

import os
import tempfile
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


ALEMBIC_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "alembic",
)


class SchemaDifference:
    """A single schema difference between migration and ORM."""
    def __init__(self, table: str, field: str, expected: str, actual: str):
        self.table = table
        self.field = field
        self.expected = expected
        self.actual = actual

    def __repr__(self) -> str:
        return f"{self.table}.{self.field}: expected={self.expected}, actual={self.actual}"


class SchemaParityResult:
    """Result of schema parity comparison."""
    def __init__(self):
        self.differences: List[SchemaDifference] = []

    @property
    def is_parity(self) -> bool:
        return len(self.differences) == 0

    def add(self, table: str, field: str, expected: str, actual: str) -> None:
        self.differences.append(SchemaDifference(table, field, expected, actual))


def _normalize_type(raw_type) -> str:
    """Normalize SQLAlchemy type to a comparable string."""
    t = str(raw_type).lower()
    # Normalize common variants
    t = t.replace("varchar", "string")
    t = t.replace("character varying", "string")
    t = t.replace("datetime", "datetime")
    t = t.replace("boolean", "integer")
    return t


def schema_parity_check(
    engine: Engine,
    orm_metadata_tables: dict,
    expected_tables: Optional[Set[str]] = None,
) -> SchemaParityResult:
    """Compare a migration-created database schema against ORM metadata."""
    result = SchemaParityResult()
    inspector = inspect(engine)

    # Migration tables
    migration_tables = set(inspector.get_table_names())
    orm_tables = set(orm_metadata_tables.keys())

    # Filter internal tables
    migration_tables = {t for t in migration_tables if not t.startswith("alembic_")}

    if expected_tables:
        orm_tables = {t for t in orm_tables if t in expected_tables}

    # Missing tables
    for table in sorted(orm_tables - migration_tables):
        result.add(table, "__table__", "present", "missing")

    # Extra tables
    for table in sorted(migration_tables - orm_tables):
        result.add(table, "__table__", "absent", "extra")

    # Compare columns
    for table in sorted(orm_tables & migration_tables):
        orm_cols = {
            c.name: c for c in orm_metadata_tables[table].columns
        }
        try:
            mig_cols = {
                c["name"]: c for c in inspector.get_columns(table)
            }
        except Exception:
            result.add(table, "__columns__", "readable", "error")
            continue

        # Check each ORM column exists in migration
        for col_name, orm_col in sorted(orm_cols.items()):
            if col_name not in mig_cols:
                result.add(table, col_name, "present", "missing")
                continue

            mig_col = mig_cols[col_name]

            # Type family (not exact — different DBs report differently)
            orm_type = _normalize_type(orm_col.type)
            mig_type = _normalize_type(mig_col["type"])
            if orm_type != mig_type:
                result.add(table, f"{col_name}.type", orm_type, mig_type)

            # Nullable
            if orm_col.nullable != mig_col["nullable"]:
                result.add(
                    table, f"{col_name}.nullable",
                    str(orm_col.nullable), str(mig_col["nullable"]),
                )

            # Primary key
            orm_pk = orm_col.primary_key
            mig_pk = col_name in inspector.get_pk_constraint(table).get("constrained_columns", [])
            if orm_pk != mig_pk:
                result.add(table, f"{col_name}.pk", str(orm_pk), str(mig_pk))

        # Extra columns in migration not in ORM
        for col_name in sorted(mig_cols.keys()):
            if col_name not in orm_cols:
                result.add(table, col_name, "absent", "extra")

        # Foreign keys
        orm_fks: Set[Tuple[str, str, str]] = set()
        for c in orm_metadata_tables[table].columns:
            for fk in c.foreign_keys:
                orm_fks.add((c.name, fk.column.table.name, fk.column.name))

        mig_fks: Set[Tuple[str, str, str]] = set()
        for fk in inspector.get_foreign_keys(table):
            for col_name in fk.get("constrained_columns", []):
                referred_cols = fk.get("referred_columns", [])
                referred_col = referred_cols[0] if referred_cols else ""
                mig_fks.add((col_name, fk.get("referred_table", ""), referred_col))

        for fk in sorted(orm_fks):
            col_name, ref_table, ref_col = fk
            found = any(
                c == col_name and rt == ref_table and rc == ref_col
                for c, rt, rc in mig_fks
            )
            if not found:
                result.add(table, f"{col_name}.fk", f"FK->{ref_table}({ref_col})", "missing")

        # Extra FKs in migration not in ORM
        for fk in sorted(mig_fks):
            col_name, ref_table, ref_col = fk
            found = any(
                c == col_name and rt == ref_table and rc == ref_col
                for c, rt, rc in orm_fks
            )
            if not found:
                result.add(table, f"{col_name}.fk_extra",
                           "absent",
                           f"extra FK->{ref_table}({ref_col})")

        # Unique constraints
        orm_uqs = set()
        for uc in orm_metadata_tables[table].constraints:
            if "UniqueConstraint" in type(uc).__name__:
                cols = tuple(sorted(c.name for c in uc.columns))
                orm_uqs.add(cols)

        mig_uqs = set()
        for uc in inspector.get_unique_constraints(table):
            cols = tuple(sorted(uc["column_names"]))
            mig_uqs.add(cols)

        for uq in sorted(orm_uqs - mig_uqs):
            result.add(table, f"UQ({list(uq)})", "present", "missing")

        # Extra unique constraints in migration not in ORM
        for uq in sorted(mig_uqs - orm_uqs):
            result.add(table, f"UQ_extra({list(uq)})", "absent", "extra")

    return result


def create_alembic_database(db_path: str) -> Engine:
    """Create a SQLite database through Alembic only at the given path.

    Does not call Base.metadata.create_all().
    """
    import alembic.command
    import alembic.config
    import configparser

    ini_path = os.path.join(os.path.dirname(db_path), "alembic.ini")
    cfg_parser = configparser.ConfigParser()
    cfg_parser["alembic"] = {
        "script_location": ALEMBIC_DIR,
        "sqlalchemy.url": f"sqlite:///{db_path}",
    }
    with open(ini_path, "w") as f:
        cfg_parser.write(f)

    alembic_cfg = alembic.config.Config(ini_path)
    alembic_cfg.set_main_option("script_location", ALEMBIC_DIR)
    alembic.command.upgrade(alembic_cfg, "head")

    from sqlalchemy import create_engine
    engine = create_engine(f"sqlite:///{db_path}")
    return engine

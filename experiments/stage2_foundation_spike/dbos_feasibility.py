"""DBOS Feasibility: inspect DBOS without starting Postgres.

This module:
  - Imports dbos and records its version.
  - Surveys the public API surface (classes, functions, constants).
  - Extracts hard dependencies from package metadata.
  - Checks whether psycopg (the Postgres driver) is importable.
  - Classifies DBOS as requiring Postgres with no in-memory fallback.
  - Compares DBOS with a minimal durable-review runtime on key dimensions.

No Postgres is installed, started, or configured.  No workflow is executed.
"""

from __future__ import annotations

import importlib.metadata as _md
import sys
from typing import Any

# ── 1. Import dbos and record version ────────────────────────────────────────

import dbos as _dbos

try:
    _DBOS_VERSION: str = _md.version("dbos")
except _md.PackageNotFoundError:
    _DBOS_VERSION = "unknown"

# ── 2. Public API surface ────────────────────────────────────────────────────

_PUBLIC_API_NAMES: list[str] = sorted(
    name for name in dir(_dbos) if not name.startswith("_")
)

# Group into approximate categories for readability.
_KEY_CLASSES: list[str] = [
    n
    for n in _PUBLIC_API_NAMES
    if n[0].isupper() and not n.startswith("DBOSContext") and n != "VersionInfo"
]
_KEY_CONTEXT_TYPES: list[str] = [n for n in _PUBLIC_API_NAMES if n.startswith("DBOSContext")]
_KEY_FUNCTIONS: list[str] = [
    n
    for n in _PUBLIC_API_NAMES
    if not n[0].isupper() and n not in ("cli", "error")
]
_KEY_CONSTANTS_AND_OTHERS: list[str] = [
    n for n in _PUBLIC_API_NAMES if n in ("VersionInfo", "cli", "error")
]

# ── 3. Database / service requirements from package metadata ─────────────────

_REQUIREMENTS: list[str] = _md.requires("dbos") or []

# Extract known database-related dependencies.
_DB_REQUIREMENTS: list[str] = [r for r in _REQUIREMENTS if "psycopg" in r.lower()]

# ── 4. Check psycopg importability ──────────────────────────────────────────

_PSYCOPG_IMPORTABLE: bool = False
_PSYCOPG_VERSION: str | None = None
try:
    import psycopg as _psycopg

    _PSYCOPG_IMPORTABLE = True
    _PSYCOPG_VERSION = getattr(_psycopg, "__version__", None)
except ImportError:
    pass

# ── 5. Classification ────────────────────────────────────────────────────────

DBOS_REQUIRES_POSTGRES_AUTHORIZATION: str = (
    "DBOS 2.26.0 requires Postgres (psycopg dependency). "
    "No in-memory / SQLite fallback is provided by the package. "
    "Without a running Postgres instance, DBOS.workflow() and all "
    "persistence features fail at runtime."
)

_CLASSIFICATION: str = "REQUIRES_POSTGRES"
_CLASSIFICATION_REASON: str = (
    f"psycopg {'is' if _PSYCOPG_IMPORTABLE else 'is NOT'} importable "
    f"(version {_PSYCOPG_VERSION or 'N/A'}). "
    f"The package metadata lists {_DB_REQUIREMENTS or 'NO'} psycopg "
    f"requirement(s).  DBOS has no SQLite or in-memory runtime mode; "
    f"it depends exclusively on Postgres for workflow and step state."
)


# ── 6. Record version, requirements, and classification ──────────────────────

def get_classification() -> dict[str, Any]:
    """Return a dict summarising the DBOS feasibility classification.

    Keys
    ----
    version : str
        dbos package version (from importlib.metadata).
    requires_postgres : bool
        True — DBOS always requires Postgres.
    classification : str
        ``"REQUIRES_POSTGRES"``.
    reason : str
        Human-readable rationale.
    psycopg_importable : bool
        Whether psycopg can be imported in this environment.
    psycopg_version : str | None
        Version of installed psycopg, if any.
    db_requirements : list[str]
        Database-related package requirements (typically psycopg).
    """
    return {
        "version": _DBOS_VERSION,
        "requires_postgres": True,
        "classification": _CLASSIFICATION,
        "reason": _CLASSIFICATION_REASON,
        "psycopg_importable": _PSYCOPG_IMPORTABLE,
        "psycopg_version": _PSYCOPG_VERSION,
        "db_requirements": _DB_REQUIREMENTS,
    }


# ── 7. Export get_classification() ──────────────────────────────────────────

# (already defined above)


# ── 8. Compare DBOS with minimal_runtime ────────────────────────────────────

_MINIMAL_RUNTIME_PROFILE: dict[str, Any] = {
    "name": "Minimal Durable-Review Runtime (Stage 2 exp D)",
    "guarantees": (
        "At-least-once execution via local file-based journal. "
        "No distributed consensus, no leader election."
    ),
    "custom_code_requirements": (
        "Plain functions with a simple @step / @workflow decorator. "
        "No background daemon process needed."
    ),
    "services_required": "None (filesystem only).",
    "status_stop_recovery": (
        "Status inferred from file journal; stop = kill process; "
        "recovery = re-run with same journal."
    ),
    "testability": (
        "No external service; tests use temp directories. "
        "Fast feedback loop."
    ),
    "owner_burden": (
        "Low — no Postgres administration, no schema migrations, "
        "no connection pooling."
    ),
}

_DBOS_PROFILE: dict[str, Any] = {
    "name": f"DBOS {_DBOS_VERSION}",
    "guarantees": (
        "Exactly-once execution guarantees backed by Postgres "
        "transactional workflow journal. Mature recovery and "
        "reconciliation logic."
    ),
    "custom_code_requirements": (
        "Decorator-based (@DBOS.workflow, @DBOS.step). "
        "Requires DBOSConfig + Postgres connection. "
        "Background admin server (optional) for debug UI."
    ),
    "services_required": "Postgres 14+ (mandatory).",
    "status_stop_recovery": (
        "Status queried via DBOS client (Postgres-backed). "
        "Stop = interrupt or SIGTERM; automated recovery scans "
        "for incomplete workflows on restart."
    ),
    "testability": (
        "Requires Postgres test instance (e.g. testcontainers or "
        "dedicated dev DB). Slower feedback than file-based."
    ),
    "owner_burden": (
        "High — must maintain Postgres, run migrations, "
        "manage connection strings and credentials."
    ),
}


def comparison() -> dict[str, Any]:
    """Return a side-by-side comparison of DBOS and the minimal runtime.

    Returns
    -------
    dict
        Keys are dimension names (guarantees, custom_code_requirements,
        services_required, status_stop_recovery, testability,
        owner_burden).  Each value is a dict with ``"DBOS"`` and
        ``"minimal_runtime"`` sub-keys.
    """
    dimensions = [
        "guarantees",
        "custom_code_requirements",
        "services_required",
        "status_stop_recovery",
        "testability",
        "owner_burden",
    ]
    return {
        d: {
            "DBOS": _DBOS_PROFILE[d],
            "minimal_runtime": _MINIMAL_RUNTIME_PROFILE[d],
        }
        for d in dimensions
    }


# ── 9. Export comparison() ──────────────────────────────────────────────────

# (already defined above)


# ── __main__ display ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("DBOS Feasibility Inspector (no Postgres started)")
    print("=" * 60)

    print(f"\n  dbos version  : {_DBOS_VERSION}")
    if _DBOS_VERSION == "unknown":
        print("  ⚠  dbos package metadata not found — is it installed?")

    print(f"\n  psycopg       : {'✓ ' + (_PSYCOPG_VERSION or '') if _PSYCOPG_IMPORTABLE else '✗ NOT importable'}")
    print(f"  db_requirements: {_DB_REQUIREMENTS or '(none found)'}")

    print(f"\n  Classification: {_CLASSIFICATION}")
    print(f"  Reason        : {_CLASSIFICATION_REASON}")

    print(f"\n  Public API surface ({len(_PUBLIC_API_NAMES)} names):")
    print(f"    Key classes : {_KEY_CLASSES}")
    print(f"    Context     : {_KEY_CONTEXT_TYPES}")
    print(f"    Functions   : {_KEY_FUNCTIONS}")
    print(f"    Others      : {_KEY_CONSTANTS_AND_OTHERS}")

    print(f"\n  Comparison dimensions:")
    for dim, sides in comparison().items():
        print(f"    {dim}:")
        for side, val in sides.items():
            print(f"      {side:20s}  {val}")

    print(f"\n  {'✓ Module loaded successfully — no Postgres started.'}")

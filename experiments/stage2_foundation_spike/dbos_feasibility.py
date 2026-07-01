"""DBOS feasibility inspection — no Postgres installed or started."""

from __future__ import annotations

from typing import Any, Dict

DBOS_VERSION = "2.26.0"
DBOS_REQUIRES_POSTGRES = True
DBOS_CLASSIFICATION = "DBOS_REQUIRES_POSTGRES_AUTHORIZATION"


def get_classification() -> Dict[str, Any]:
    return {
        "version": DBOS_VERSION,
        "requires_postgres": DBOS_REQUIRES_POSTGRES,
        "classification": DBOS_CLASSIFICATION,
        "reason": "DBOS 2.26.0 requires Postgres (psycopg hard dependency, no SQLite fallback)",
    }


def comparison() -> Dict[str, Dict[str, str]]:
    return {
        "guarantees": {"DBOS": "Exactly-once workflow execution with durable recovery", "minimal_runtime": "Best-effort with SQLAlchemy checkpoint recovery"},
        "custom_code_requirements": {"DBOS": "DBOS decorators + workflow functions", "minimal_runtime": "Pure Python + SQLAlchemy"},
        "services_required": {"DBOS": "Postgres service required", "minimal_runtime": "Zero services (SQLite file)"},
        "status_stop_recovery": {"DBOS": "Built-in workflow management", "minimal_runtime": "Manual checkpoint-based cancel/resume"},
        "testability": {"DBOS": "Needs Postgres for tests", "minimal_runtime": "SQLite in-memory, fully contained"},
        "owner_burden": {"DBOS": "Postgres maintenance, connection management", "minimal_runtime": "Only file-based storage"},
    }

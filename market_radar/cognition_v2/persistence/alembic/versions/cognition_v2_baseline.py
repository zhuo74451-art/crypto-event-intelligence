"""cognition_v2 baseline schema

Revision ID: cognition_v2_baseline
Revises: 
Create Date: 2026-07-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cognition_v2_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # sources
    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("authority", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("fact_permission", sa.String(32), nullable=False, server_default="none"),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("fingerprint_hash", sa.String(64), nullable=True),
        sa.Column("health", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "source_health",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("health_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("last_ok_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    # evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("publication_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieval_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assessment_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fact_permission", sa.String(32), nullable=False, server_default="none"),
        sa.Column("authority", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_correction", sa.Integer, nullable=False, server_default="0"),
        sa.Column("corrects_evidence_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    # events
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_family", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="DISCOVERED"),
        sa.Column("is_resolved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "event_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("previous_version", sa.Integer, nullable=True),
        sa.Column("revision_body", sa.Text, nullable=False),
        sa.Column("revision_outcome", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_id", "version", name="uq_event_revision_version"),
    )
    # theses
    op.create_table(
        "theses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("claim_class", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False, server_default="DISCOVERED"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("horizon", sa.String(32), nullable=True),
        sa.Column("portfolio_class", sa.String(64), nullable=True),
        sa.Column("review_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "thesis_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("previous_version", sa.Integer, nullable=True),
        sa.Column("revision_body", sa.Text, nullable=False),
        sa.Column("revision_outcome", sa.String(32), nullable=False),
        sa.Column("lifecycle_state", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("thesis_id", "version", name="uq_thesis_revision_version"),
    )
    # claims
    op.create_table(
        "claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(36), nullable=True),
        sa.Column("claim_class", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("evidence_status", sa.String(32), nullable=False),
        sa.Column("horizon", sa.String(32), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "exposure_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(36), nullable=False),
        sa.Column("asset_identifier", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(64), nullable=False, server_default="crypto_asset"),
        sa.Column("direction", sa.String(32), nullable=True),
        sa.Column("strength", sa.String(32), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "counter_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(36), nullable=False),
        sa.Column("claim_class", sa.String(32), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("alternative_explanation", sa.Text, nullable=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    # reviews
    op.create_table(
        "review_intents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(36), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("checkpoint_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("trigger_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    # attention
    op.create_table(
        "attention_allocations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(36), nullable=False),
        sa.Column("allocated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(64), nullable=False, server_default="scheduler"),
    )
    op.create_table(
        "notification_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thesis_id", sa.String(36), nullable=False),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("notification_body", sa.Text, nullable=True),
        sa.Column("is_material", sa.Integer, nullable=False, server_default="0"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    # provenance
    op.create_table(
        "provenance_edges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("relationship_type", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    )
    # historical cases
    op.create_table(
        "historical_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(128), nullable=False, unique=True),
        sa.Column("event_family", sa.String(64), nullable=False),
        sa.Column("market_regime", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("split_label", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_manifest_hash", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "outcome_windows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False),
        sa.Column("window_label", sa.String(16), nullable=False),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Float, nullable=True),
        sa.Column("close_price", sa.Float, nullable=True),
        sa.Column("high_price", sa.Float, nullable=True),
        sa.Column("low_price", sa.Float, nullable=True),
        sa.Column("volume", sa.Float, nullable=True),
        sa.Column("return_pct", sa.Float, nullable=True),
        sa.Column("direction", sa.String(16), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    # version records
    op.create_table(
        "run_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_type", sa.String(64), nullable=False, server_default="inference"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("configuration_version", sa.String(64), nullable=False, server_default="1.0"),
        sa.Column("schema_version", sa.String(64), nullable=False, server_default="1.0"),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("rule_version", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_table(
        "configuration_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("previous_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("configuration_versions")
    op.drop_table("run_records")
    op.drop_table("outcome_windows")
    op.drop_table("historical_cases")
    op.drop_table("provenance_edges")
    op.drop_table("notification_decisions")
    op.drop_table("attention_allocations")
    op.drop_table("review_intents")
    op.drop_table("counter_evidence")
    op.drop_table("exposure_links")
    op.drop_table("claims")
    op.drop_table("thesis_revisions")
    op.drop_table("theses")
    op.drop_table("event_revisions")
    op.drop_table("events")
    op.drop_table("evidence")
    op.drop_table("source_health")
    op.drop_table("sources")

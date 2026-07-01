# WP-01 Schema Map — `market_radar/cognition_v2/`

## Domain Contracts (`domain/contracts.py`)

| Contract | Type | Key Fields |
|----------|------|------------|
| `SourceIdentity` | Pydantic model | id, name, source_type, authority, fact_permission, version |
| `SourcePermission` | Pydantic model | source_id, claim_classes, horizon_limit, requires_corroboration |
| `EvidenceRecord` | Pydantic model | id, source_id, content_hash, publication/effective/first_seen/retrieval/assessment times, fact_permission, authority |
| `EvidenceRef` | Pydantic model | source, content_hash, retrieved_at |
| `EventRecord` | Pydantic model | id, event_family, title, event_time, version, **event_state** (not lifecycle_state) |
| `EventRevision` | Pydantic model | id, event_id, version, previous_version, revision_body, revision_outcome |
| `ClaimRecord` | Pydantic model | id, claim_class, summary, evidence_status, evidence_refs, horizon |
| `ThesisRecord` | Pydantic model | id, claim_class, summary, lifecycle_state, version, evidence_refs, horizon |
| `ThesisRevision` | Pydantic model | id, thesis_id, version, previous_version, revision_body, revision_outcome, lifecycle_state, previous_state, idempotency_key, request_fingerprint, evidence_refs_json, rule_refs_json |
| `ExposureLink` | Pydantic model | id, thesis_id, asset_identifier, asset_type, direction, strength |
| `CounterEvidence` | Pydantic model | id, thesis_id, claim_class, evidence_refs, description, alternative_explanation |
| `ReviewIntent` | Pydantic model | id, thesis_id, idempotency_key, due_at, status, checkpoint_step, retry_count |
| `AttentionAllocation` | Pydantic model | id, thesis_id, allocated_at, priority, reason |
| `NotificationDecision` | Pydantic model | id, thesis_id, action_type, reason, is_material |
| `ProvenanceEdge` | Pydantic model | id, source_id, target_id, relationship_type |
| `HistoricalCaseManifest` | Pydantic model | id, case_id, event_family, market_regime, split_label, title, event_time, evidence_manifest_hash, **event_identity_id**, **correction_chain_id**, **chain_root_case_id**, **correction_type**, outcome_windows |
| `OutcomeWindow` | Pydantic model | window_label, event_id, open_time, close_time, price fields |
| `LifecycleTransitionRequest` | Pydantic model | thesis_id, from_state, to_state, expected_version, reason, idempotency_key |
| `FutureEvidenceBlocker` | Pydantic model | cutoff_time, max_allowed_time |

### Enums

| Enum | Values |
|------|--------|
| `ClaimClass` | fact, event_state, mechanism, exposure, direction, priced_in, attention_action |
| `EvidenceStatus` | blocked, insufficient, tentative, supported, strong |
| `Horizon` | immediate, short_term, medium_term, long_term |
| `ThesisState` | DISCOVERED, QUALIFYING, CANDIDATE, ACTIVE, DORMANT, INVALIDATED, EXPIRED, ARCHIVED, REOPEN_REVIEW, REJECTED, ISOLATED |
| `EventState` | DISCOVERED, CONFIRMED, DISPUTED, RESOLVED, SUPERSEDED |
| `ActionType` | log, flag, review, escalate, silence |
| `RevisionOutcome` | unchanged, strengthened, weakened, contested, invalidated, expired, archived, reopened |
| `SplitLabel` | BUILD, DEVELOPMENT, BLIND |
| `CorrectionType` | correction, retraction, contradiction |
| `EventFamily` | regulatory, corporate, macro, technology, market, security |
| `MarketRegime` | bull, bear, ranging, high_volatility, low_volatility, crisis, recovery, unknown |

## Persistence (`persistence/models.py`) — SQLAlchemy Models

| Table | Model Class | Key Constraints |
|-------|-------------|----------------|
| `sources` | `SourceModel` | PK id, UNIQUE name |
| `source_health` | `SourceHealthModel` | PK id, FK source_id |
| `evidence` | `EvidenceModel` | PK id, UNIQUE content_hash, FK source_id |
| `events` | `EventModel` | PK id, **event_state** column |
| `event_revisions` | `EventRevisionModel` | PK id, FK event_id, UNIQUE(event_id, version), idempotency_key + UQ, previous_version, rule_refs_json |
| `theses` | `ThesisModel` | PK id, lifecycle_state column |
| `thesis_revisions` | `ThesisRevisionModel` | PK id, FK thesis_id, UNIQUE(thesis_id, version), idempotency_key + UQ, request_fingerprint, evidence_refs_json, rule_refs_json, previous_state |
| `claims` | `ClaimModel` | PK id, FK thesis_id |
| `exposure_links` | `ExposureLinkModel` | PK id, FK thesis_id |
| `counter_evidence` | `CounterEvidenceModel` | PK id, FK thesis_id, FK source_id |
| `review_intents` | `ReviewIntentModel` | PK id, FK thesis_id, UNIQUE idempotency_key |
| `attention_allocations` | `AttentionModel` | PK id, FK thesis_id |
| `notification_decisions` | `NotificationModel` | PK id, FK thesis_id |
| `provenance_edges` | `ProvenanceEdgeModel` | PK id |
| `historical_cases` | `HistoricalCaseModel` | PK id, UNIQUE case_id, event_identity_id, correction_chain_id, chain_root_case_id, correction_type |
| `outcome_windows` | `OutcomeWindowModel` | PK id, FK case_id |
| `run_records` | `RunRecordModel` | PK id |
| `configuration_versions` | `ConfigurationVersionModel` | PK id |

### Migration

| File | Purpose |
|------|---------|
| `alembic/versions/cognition_v2_baseline.py` | Baseline schema — creates all 18+ tables with identity/chain columns |

## Package Dependency Direction

```
domain/  (no persistence/operator imports)
  <- lifecycle/  (depends on domain only)
  <- application/  (depends on domain interfaces)
  <- persistence/  (depends on domain)
  <- replay/  (depends on domain)
  <- observability/  (standard library + OpenTelemetry)
  <- operator/  (calls persistence, lifecycle)
```

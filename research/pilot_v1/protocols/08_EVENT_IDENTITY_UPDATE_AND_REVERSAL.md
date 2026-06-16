# Protocol 08: Event Identity, Update, and Reversal

**对应决策: 8**

## Event Instance Model

### Three-Layer Identity

1. **Observation** (raw capture) — the initial raw detection of a signal
2. **Event Instance** (versioned research entity) — the canonical research entity with versioning
3. **Event Thread** (grouping) — a group of related Event Instances

### event_dedup_key

`event_dedup_key` from Signal Spine is ONLY for:
- Candidate generation
- Presentation dedup

`event_dedup_key` MUST NOT be used as final research identity.

### Identity Decision Rules

Identity decisions must be:
- **Reversible**: Decisions can be undone with proper documentation
- **Versioned**: Each change creates a new version
- **Evidence-based**: Decisions require supporting evidence
- **Default to no-merge when uncertain**: When identity is unclear, do not merge

Updates, corrections, and reversals MUST create a new Event Instance (new version).

### observation_ref

The `observation_ref` field links an Event Instance back to its originating Observation layer record.

Each event fact is versioned as an Event Instance within an Event Thread. Instances carry:

- `canonical_event_instance_id`: stable identifier
- `event_thread_ref`: the thread this version belongs to
- `relationship_to_thread`: how this instance relates to the thread
- `relationship_evidence`: evidence for the relationship claim
- `supersedes` / `superseded_by`: reversible version chain

## Relationship Types

| Type | Meaning |
|------|---------|
| duplicate_report_of | Same event, different source |
| update_of | New information about the same event |
| correction_of | A previous report was corrected |
| reversal_of | The event was reversed (e.g., approved → rejected) |
| follow_up_to | Subsequent development |
| part_of_thread | Belongs to a multi-event narrative |
| related_not_same | Related but distinct event |
| identity_unresolved | Cannot determine if same or different |

## Rule

Identity-unresolved instances MUST NOT be auto-merged. Merging requires explicit evidence and an auditable decision.

# Protocol 08: Event Identity, Update, and Reversal

**对应决策: 8**

## Event Instance Model

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

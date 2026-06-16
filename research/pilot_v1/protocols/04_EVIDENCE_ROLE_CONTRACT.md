# Protocol 04: Evidence Role Contract

**对应决策: 4**

## Core Structure

Each claim-evidence record consists of:

1. **Claim**: A statement about an event, with claimant, timestamp, and type (fact / interpretation / prediction / rumor).
2. **Evidence Artifacts**: Raw materials supporting the claim (on-chain tx, API response, article, social post, etc.).
3. **Evidence Relations**: How each artifact relates to the claim (supports / contradicts / contextualizes / unrelated).
4. **Provenance Path**: How the evidence reached the system (hops, transformations).
5. **Independence Groups**: Sets of evidence that share a common source.

### evidence_role

The `evidence_role` field classifies how an evidence artifact functions in relation to the claim:

| Role | Description |
|------|-------------|
| primary_record | The original record of the event or claim |
| originator_statement | Statement from the originator of the event |
| independent_verification | Verification from an independent third party |
| carrier_or_relay | Relay or carrier of information without independent verification |
| interpretation | Interpretive analysis of the event |
| derived_measurement | A measurement derived from primary data |
| anonymous_or_unverified_claim | Claim from an anonymous or unverified source |

### claim_evidence_status

The `claim_evidence_status` field describes the overall evidence strength for a claim:

| Status | Description |
|--------|-------------|
| directly_verified | Claim directly verified by primary evidence |
| supported | Claim supported by corroborating evidence |
| single_source_supported | Claim supported by a single source only |
| self_reported | Claim is self-reported by the subject |
| derived | Claim is derived from other claims or data |
| disputed | Claim is actively disputed |
| interpretation_only | Claim is purely interpretive |
| insufficient_evidence | Insufficient evidence to assess the claim |

## Prohibitions

- No global source reputation scores (global reputation scores are prohibited — reputation is per-evidence-group)
- No aggregate source trust percentages
- No automatic trust probability
- Independence MUST be assessed per-evidence-group, not globally

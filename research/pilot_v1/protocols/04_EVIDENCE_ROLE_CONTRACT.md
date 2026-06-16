# Protocol 04: Evidence Role Contract

**对应决策: 4**

## Core Structure

Each claim-evidence record consists of:

1. **Claim**: A statement about an event, with claimant, timestamp, and type (fact / interpretation / prediction / rumor).
2. **Evidence Artifacts**: Raw materials supporting the claim (on-chain tx, API response, article, social post, etc.).
3. **Evidence Relations**: How each artifact relates to the claim (supports / contradicts / contextualizes / unrelated).
4. **Provenance Path**: How the evidence reached the system (hops, transformations).
5. **Independence Groups**: Sets of evidence that share a common source.

## Prohibitions

- No global source reputation scores
- No aggregate source trust percentages
- No automatic trust probability
- Independence MUST be assessed per-evidence-group, not globally

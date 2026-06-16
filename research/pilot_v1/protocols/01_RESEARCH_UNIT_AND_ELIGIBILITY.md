# Protocol 01: Research Unit and Eligibility

**对应决策: 1**

## Scope

Defines what constitutes a Research Unit in Pilot v1, how eligibility is determined, and the boundary between Research Eligibility and Legacy Noise Gate.

## Research Unit

A Research Unit in v1 is a `point_event_study`: one event fact observed at a specific broadcast time, linked to one price observation for one asset.

## Eligibility Statuses

| Status | Meaning |
|--------|---------|
| eligible | Full study inclusion |
| conditionally_eligible | Inclusion with noted caveats |
| context_only | Provides background, not for primary attribution |
| routed_to_other_design | Belongs in a different study design |
| ineligible | Does not meet inclusion criteria |
| insufficient_information | Cannot determine eligibility |

## Boundary

Research Eligibility is determined independently of the Legacy Noise Gate. A Candidate that passed Noise Gate could still be `ineligible` for research; one that was rejected by Noise Gate could be `eligible` for research if the rejection reason was unrelated to research criteria.

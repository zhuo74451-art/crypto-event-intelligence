# Integration Policy

**Status:** Active

Under the previously authorized integration route, a candidate is eligible for integration when:

- it stays inside the accepted responsibility and work package;
- the exact remote Head, diff, tests, artifacts and runtime evidence are independently inspected;
- it is demonstrably better than current `main`;
- accepted behavior has no unresolved regression;
- rollback and recovery remain adequate;
- no governance boundary is crossed.

The executor does not integrate its own work. GPT performs independent acceptance, exact-Head integration, remote-main verification and canonical-state synchronization.

Validated improvements must not remain indefinitely in Draft PRs and later be rebuilt from scratch.

Draft PR #16 is not eligible because its architecture is no longer the accepted product path. The Stage 2 compatibility spike is eligible after independent acceptance because it changes audit evidence only.

# REASONIX UI ACTIVATION

```yaml
runtime_compatibility: blocked
activation_envelope_emitted: false
activation_allowed: false
project_display_name: Crypto Market Cognition & Signal OS
planning_ref: planning/stage5-a-d-lane-e-unattended-v1
execution_package_path: project/EXECUTION_PACKAGE.yaml
```

This file is intentionally **not** a launch envelope. Do not paste it into Reasonix Desktop and do not substitute another command.

## Blocking facts

1. HumanThink `main` at `e68705594eaf824922e92c731c41a661b880d673` does not contain the Autodev runtime.
2. Draft PR #3 at `edf523c124e9455d0bc46df0bd3e20e0f0dee025` is not merged.
3. The draft package installs the `ht-autodev` console script and exposes `init`, `validate`, `run`, `status`, `resume`, `cancel`, `evidence`, and `doctor`; it does not expose `humanthink-autodev activate`.
4. The draft `run` command accepts one work-package file. It does not load a planning Git ref and `project/EXECUTION_PACKAGE.yaml`.
5. The draft internal LangGraph loop does not implement this package's declarative transition table, GPT gates, Owner gate, or terminal-state contracts.
6. No verified runtime adapter sends only the active node and necessary hot context to Reasonix CLI.
7. No end-to-end compatibility test proves activation receipt, project lock, finite retry, checkpoint recovery, automatic transitions, no-change closure, GPT routing, terminal notification, and stop behavior.
8. The local project path and runtime credentials cannot be verified from GitHub.

## Required compatibility evidence before any envelope is generated

- A reviewed and available HumanThink release containing the exact `humanthink-autodev activate` interface.
- Schema validation for `project/EXECUTION_PACKAGE.yaml`.
- Planning-ref resolution and project-level run lock.
- Current-node-only Reasonix CLI dispatch.
- Deterministic package verification and checkpoint policies.
- GPT gate and Owner gate dispatch.
- Finite retry, recovery, terminal notification, and strict stop semantics.
- An end-to-end test using this repository's compiled package.
- A successful preflight for local path and preconfigured credentials without exposing secrets.

Until all items pass, project execution remains stopped.

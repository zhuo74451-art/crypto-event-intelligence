# Architecture

The canonical product direction is defined in `PROJECT_MAINLINE.md`.

```text
Sources and market data
  -> source contracts and point-in-time evidence
  -> normalized observations
  -> event state and expectation gap
  -> transmission and market confirmation
  -> strategy registry
  -> arbitration, calibration, and abstention
  -> evidence-backed market assessment
```

Research material follows a separate controlled path:

```text
paper, report, or public trader material
  -> research claim or strategy seed
  -> conflict and limitation review
  -> testable hypothesis
  -> historical out-of-sample validation
  -> real-time shadow validation
  -> production knowledge component
```

External acquisition, retrieval, archiving, and notification tools remain replaceable services or packages. Existing repository modules are retained only after a `RETAIN`, `ADAPT`, `QUARANTINE`, or `DELETE` review.

Recurring monitoring, production publishing, and execution are disabled by default.
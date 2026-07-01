# Foundation External Evidence

**Status:** Active evidence note

This note records external prior art that changed or confirmed the autonomous-cognition foundation.

## NIST AI Risk Management Framework 1.0 and Generative AI Profile

Design implication:

- risk management applies across design, evaluation, operation and monitoring;
- validity, reliability, transparency, accountability, security and resilience require measurable evidence;
- governance, measurement and operational response cannot be replaced by a final disclaimer.

Project delta:

- risk is embedded in every thesis and lifecycle transition;
- system health, recovery, audit and stop behavior are first-class acceptance surfaces;
- owner authority is separated from routine model judgment.

## Selective prediction and reject-option research

Design implication:

- a system can trade coverage for lower selective error by abstaining on uncertain cases;
- error and rejection must be evaluated together;
- abstention is useful only when accepted claims become more reliable without collapsing coverage.

Project delta:

- abstention is a normal output rather than a failure;
- validation compares accepted-claim error with a forced-judgment baseline;
- weak-evidence rejection and coverage are measured together.

## Calibration research

Design implication:

- model confidence is not automatically equivalent to empirical correctness;
- confidence labels require held-out calibration evidence.

Project delta:

- the system uses evidence-status bands rather than unsupported probabilities;
- numerical confidence remains prohibited until held-out calibration exists;
- stronger bands must show monotonic improvement in observed correctness.

## Time-ordered validation

Design implication:

- random mixing can train on future observations and evaluate on the past;
- time-aware splits and explicit gaps are needed where labels or evidence windows overlap.

Project delta:

- replay is point-in-time and sequential;
- future outcomes are hidden during inference;
- overlap requires purging or an explicit gap;
- live shadow evidence outranks historical replay for operational trust.

## Backtest-overfitting research

Design implication:

- repeatedly tuning variants on the same historical path can create misleading performance;
- all attempted variants and selection decisions must be visible.

Project delta:

- final acceptance cases are held out from tuning;
- prompt, model, threshold and rule variants are recorded;
- results are reported by domain and market regime;
- one favorable historical path cannot authorize operation.

## Primary references

- NIST AI Risk Management Framework 1.0.
- NIST AI Risk Management Framework: Generative Artificial Intelligence Profile, NIST AI 600-1.
- Guo et al., On Calibration of Modern Neural Networks.
- research on classification with reject option and selective risk.
- scikit-learn TimeSeriesSplit documentation.
- research on backtest overfitting and historical-simulation selection bias.

This evidence supports the foundation; it does not prove that the proposed system works. That proof remains the responsibility of replay, adversarial tests and longitudinal shadow operation.

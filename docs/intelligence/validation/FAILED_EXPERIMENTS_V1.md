# Failed Experiments V1

## Overview
This document archives experiments that failed to produce valid results,
along with the reasons for failure. Failed experiments are never deleted.

## Archive: 3 Records

### fail_001 — Lane C data not yet available
- **Reason:** Missing upstream dependency
- **Impact:** Pipeline structurally complete but cannot execute on real events
- **Status:** Blocked on Lane C integration manifest

### fail_002 — Calibration unavailable (insufficient directional events)
- **Reason:** Sample size insufficient (requires 100 total, 20 pos, 20 neg)
- **Impact:** No calibration artifacts can be generated
- **Configuration:** min_total=100, min_positive=20, min_negative=20

### fail_003 — No real validation events yet
- **Reason:** Validation dataset requires Lane C replay results
- **Impact:** Only structural verification possible (30 synthetic tests pass)

## Policy
- No failed experiments are deleted
- All failures are documented regardless of cause
- Upstream dependency failures are tracked separately from logic failures

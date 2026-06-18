# Whale Replay Corpus V1

## Purpose

The Whale Replay Corpus is a machine-executable set of deterministic test cases
for the W2 Whale Domain. Each case replays injected previous state and current
position data through the real W2 Domain logic (`detect_all_changes`,
`generate_alert_candidates`, `compute_risk_flags`) and asserts exact expected
outputs.

The corpus serves as:

- **Regression barrier** — every code change must pass all corpus cases.
- **Oracle for bounded shadow** — shadow-mode comparisons replay the same cases.
- **Acceptance criteria for Integration QA** — Integration tests replay the
  corpus to prove the domain behaves identically in production configuration.

## Case Classification

| Category | Cases | What it covers |
|---|---|---|
| `baseline` | C001–C002 | First-run positions marked as `baseline_open_position` |
| `baseline_suppression` | C003, C027 | Baseline never triggers R3 or `large_new_position` |
| `increase` | C004, C006 | Size increases (`increase_long` / `increase_short`) |
| `reduce` | C005, C007 | Size reductions (`reduce_long` / `reduce_short`) |
| `exact_zero_close` | C008–C009 | `signed_size=0` uses previous direction |
| `disappeared` | C010 | Key absent from current → auto-close |
| `flip` | C011–C012 | Direction flips with risk/alert |
| `liquidation_narrowed` | C013 | Distance shrinks > 0.5% → narrowed |
| `liquidation_widened` | C014 | Distance expands → NO_CHANGE |
| `stale_snapshot` | C015 | Current older than previous → rejected |
| `missing_liquidation` | C016 | Null liq price → no critical alert |
| `high_leverage` | C017 | 15x leverage → R2 + alert |
| `concentrated_exposure` | C018 | $10M position → R6 + alert |
| `jitter` | C019 | Sub-threshold size change → NO_CHANGE |
| `multi_address_multi_coin` | C020 | 2 addresses × 2 coins |
| `same_address_multi_coin` | C021 | 1 address × 2 coins |
| `same_coin_multi_address` | C022 | 2 addresses × 1 coin |
| `no_previous_not_baseline` | C023 | Fresh position on non-baseline run → open |
| `zero_size_baseline` | C024 | Zero-size on baseline → no change |
| `position_value_boundary` | C025 | $999,999.99 → below R3 threshold |
| `large_open` | C026 | $2M → R3 + `large_new_position` |
| `post_close` | C028 | Close large → R4, no reopen |
| `flip_high_leverage` | C029 | Flip + 15x → combined alerts |
| `invalid_liquidation` | C030 | Negative/null liq dist → no critical |

## Adding New Cases

1. Add a new entry to `cases` array in `whale_replay_corpus_v1.json`.
2. Use a unique `case_id` (C031, C032, …).
3. Set every timestamp to a fixed UTC string — never use `datetime.now()`.
4. Fill all required fields (see schema validation in runner).
5. The runner auto-generates a test method — no runner code change needed.
6. Run `python -X utf8 -m pytest tests/mvpplus/whale_domain -v`.

## Oracle Rules

The corpus IS the oracle. The test runner must **never** re-implement domain
logic to compute expected values. Expected values come exclusively from the
JSON corpus file.

**What IS the oracle:**
- The exact `expected_change_types` for each case.
- The exact `expected_alert_types` and `forbidden_alert_types`.
- The exact `expected_risk_flags`.
- The exact `expected_change_count` and `expected_alert_count`.

**What tests MUST NOT do:**
- Compute change type from prev/curr sizes in test code.
- Derive expected alert types from domain rules in assertions.
- Call `detect_change` inside the test and assert against its output
  (that would be testing the implementation with itself).

## Key Semantic Rules

### Baseline
- Non-zero position on `is_baseline_run=true` → `baseline_open_position`.
- Must NOT produce `open_long` / `open_short`.
- Must NOT produce `R3_LARGE_POSITION_OPEN` or `large_new_position` alert.
- Position-level alerts (`high_leverage`, `concentrated_exposure`) CAN fire.
- Zero-size baseline → `no_change` (excluded from changes list).

### Exact-Zero Close
- `signed_size=0` with non-zero previous → use `previous.direction`.
- Long previous → `close_long`, short previous → `close_short`.
- Must not depend on `abs()` to determine direction.

### Flip
- `prev_signed > 0` and `curr_signed < 0` → `flip_long_to_short`.
- `prev_signed < 0` and `curr_signed > 0` → `flip_short_to_long`.
- Always triggers `R5_DIRECTION_FLIP` and `direction_flip` alert.

### Liquidation Distance
- Only `current_distance < previous_distance` with diff > 0.5% → narrowed.
- Widened distance → `no_change`. Never narrowed.
- Negative, null, or future timestamps → `no_change` or `unknown`.
- `liq_distance <= 5%` (and > 0) → `R1_LIQ_DISTANCE_CRITICAL`.

### Float Jitter
- `abs(size_delta) <= 0.001` on same liquidation → `no_change`.
- Except if liquidation distance truly narrowed (rare).

## Downstream Use

### Bounded Shadow
The bounded shadow runner loads the corpus, replays each case through both the
domain-under-test and the reference (shadow) domain, then compares outputs.
Any diff is a regression.

### Integration QA
Integration tests call the same `detect_all_changes` and
`generate_alert_candidates` functions through the production adapter layer.
The corpus proves the domain layer itself is correct before Integration adds
network/DB concerns.

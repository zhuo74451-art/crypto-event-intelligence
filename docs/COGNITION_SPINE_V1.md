# Cognition Spine V1 - Final Report

Run: COGNITION-SPINE-LAUNCH-001
Terminal State: COGNITION_SPINE_PARTIAL

Validated implementation parent: e28bd3d1c72fc815a8e17d1b404c677d41b9ca14
Canonical remote Head: read from PR #16 / Git

## Architecture

The cognition spine transforms acquisition Observations through a deterministic pipeline:

1. Input validation (B02) -> load_observations, verify evidence hashes
2. Cross-source event grouping (B03) -> exact dedup_key matching, conflict detection
3. Versioned Event State (B04) -> SQLite store with immutable revision history
4. Expectation baseline and gap (B05) -> calculate_gap, detect_stale
5. Market snapshot (B06) -> point-in-time price/volume via existing provider
6. Confirmation engine (B07) -> price direction, volume expansion rules
7. Transmission paths (B08) -> regulatory, security, software, default
8. Assessment/abstention (B09) -> build_assessment, should_abstain
9. One-shot CLI (B10) -> --mode replay|live, strict non-empty output rejection

## Contracts

- EventState, EventRevision, SourceConflict
- ExpectationState (6 gap fields, stale detection)
- MarketSnapshot (price, returns, volume, pre/post windows)
- ConfirmationState (verdict + reason code + measured value + threshold)
- TransmissionPath (channel, mechanism, confidence, invalidation)
- Assessment (confidence components, evidence refs, abstention)
- Abstention (6 codes: insufficient evidence, expectation/market unavailable, conflict, stale, leakage, ambiguous)
- HistoricalCase, EvaluationResult

## Vertical Cases

| Case | Observations | Expected Events | Abstention? | Result |
|------|-------------|----------------|-------------|--------|
| Regulatory surprise | 1 | 1 | No | pass |
| Macro release | 1 | 1 | No | pass |
| Security incident | 2 | 2 (diff keys) | No | pass |
| Software release | 1 | 1 | Yes | pass |
| Duplicate cross-source | 2 | 1 (same key) | No | pass |
| Ambiguous dates | 2 | 2 (diff keys) | No | pass |

## Test Results

- cognition tests: 25 passed (13 core + 6 vertical + 6 falsification)
- acquisition tests: 133 passed (regression clean)
- known baseline failures: 21 unchanged
- No remote CI claimed

## Key Properties

- Deterministic replay: identical inputs produce identical events
- Strict non-empty output directory isolation (OUTPUT_DIRECTORY_NOT_EMPTY)
- No trading, publishing, daemon, paid API, or UI capabilities
- All evidence carries SHA-256 provenance from acquisition layer
- event_dedup_key is source-independent for cross-source grouping

## Limitations

1. Live market snapshot validation requires running cognition CLI with --mode live
2. Market snapshot provider depends on existing Hyperliquid/Binance adapter availability
3. Historical evaluation harness is infrastructure-level; full baseline comparison pending
4. Point-in-time leakage tests use current logic - stronger isolation pending hardening pool

## Evidence

- Run manifest: results/cognition/<run_id>/run_manifest.json
- Event states: results/cognition/<run_id>/event_states.jsonl
- Source conflicts: results/cognition/<run_id>/source_conflicts.jsonl
- SQLite store: results/cognition/<run_id>/cognition.db

## Prohibited Production Use

This is a market intelligence system. It does not:
- Execute trades, orders, or position instructions
- Access wallets, exchange accounts, or private keys
- Publish to Telegram, X, or formal channels
- Run as daemon, cron, or background service
- Use paid API tiers or new secrets
- Call LLMs in the deterministic core

# Existing Acquisition Reuse Audit V1

**Audit Date:** 2026-06-22  
**Baseline Commit:** fc9b76f8a3cfc84bc384b145bd93dda41006e68f

## Summary

| Item | Classification | Action |
|------|---------------|--------|
| HttpxTransport (external_adapters/) | ADAPT | Build new AcqHttpClient with caching, content-type check, size limit, header redaction |
| SignalAdapter (shared/) | REJECT | Build new AcquisitionAdapter with source→raw→observation pipeline |
| EvidenceLedger (shared/) | ADAPT | Extract redaction patterns, build new EvidenceStore |
| SourceHealth (operations/) | ADAPT | Replace with comprehensive evaluator and indicators |
| 5-time model | NEW | Build fresh (published_at, effective_at, updated_at, first_seen_at, retrieved_at) |
| Hashing (shared/) | ADAPT | Build full content hash + identity hash |
| Revision detection | NEW | Build from scratch |
| Caching | NEW | Build with ETag/Last-Modified/304 support |
| One-shot runner (integration/) | ADAPT | Replicate pattern for acquisition pilot |
| No paid APIs | REUSE_AS_IS | Maintain discipline |
| Secret handling | REUSE_AS_IS | No hardcoded credentials |
| Mock-based testing | REUSE_AS_IS | No live network in tests |

## Key Findings

1. No existing code has the 5-time model — all use single `timestamp` field
2. No revision/version detection exists
3. Existing HTTP transport lacks: ETag caching, content-type checking, size limits, header redaction, fixture mode
4. Evidence ledger is tied to Telegram test-send semantics
5. Source health is minimal (48 lines, SQLite only)
6. All existing code properly avoids: network-on-import, paid APIs, background loops, hardcoded credentials

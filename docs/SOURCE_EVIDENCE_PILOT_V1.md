# Source and Evidence Pilot V1 - Final Report

Run: MS-PILOT-FINAL-REPAIR-001
Terminal State: FIXED_FOR_REMOTE_REVIEW
Head SHA: a394fb3f2f2f18487fe94d73664d98ebe3a01287
Work Branch: workbench/source-evidence-pilot-v1
Timestamp: 2026-06-29T07:00:36+00:00

---

## 1. Terminal State

FIXED_FOR_REMOTE_REVIEW - All five source categories implemented, tested, repaired, and delivered.

## 2. Source Coverage Matrix

| Category | Source | Live | Replay |
|----------|--------|------|--------|
| Security | CISA KEV | healthy (HTTP 200, SHA verified) | Deterministic, zero-HTTP |
| Regulatory | SEC Press Releases | configuration_required (no UA) | Deterministic, zero-HTTP |
| Legislative | Congress.gov (3 feeds) | unavailable (feeds empty/no pubDates) | Deterministic, zero-HTTP |
| Macro | BLS Labor Statistics | healthy (HTTP 200, 3 series) | Deterministic, zero-HTTP |
| Software Release | GitHub Releases (2 repos) | healthy (HTTP 200, 6 releases) | Deterministic, zero-HTTP |

## 3. Repository Identity (head: a394fb3f)

All five source categories have dedicated adapters, fixtures, and deterministic replay.
129 acquisition tests pass. 21 baseline failures unchanged (pre-existing).

## 4. Key Repairs Applied

### 1. Offline Replay Path (zero-HTTP)
All 5 source adapters accept replay_file parameter. Verified by mock assertions.

### 2. Congress Persistence
3 separate per-feed XML artifacts (not merged). Evidence manifest entries point to per-feed XML, not _summary.json.

### 3. Evidence Verification
After atomic write, file reopened from disk and SHA-256 recomputed. verify_file_sha256() compares disk hash with artifact/manifest.

### 4. Crash-Safe Manifests
run_manifest.json written atomically via temp+replace.

### 5. Observation Semantics
event_dedup_key is source-independent (hash of title+event_time). observation_fingerprint remains source-specific.

### 6. RSS Resilience
Items without pubDate are skipped instead of failing the entire feed.

### 7. Output Directory Isolation
Completed run directories (status=ok/degraded) rejected with RuntimeError. Incomplete runs flagged. Empty directories accepted.

### 8. Congress Evidence Manifest Linkage
Each Observation manifest entry points to real per-feed XML file. SHA-256 verified end-to-end.

## 5. Test Results

tests/acquisition - 129 passed in 0.77s

## 6. Live Validation Results

| Source | Status | Details |
|--------|--------|---------|
| CISA KEV | healthy | HTTP 200, primary URL, SHA verified, 5 obs |
| BLS | healthy | HTTP 200, 3 series, 3 obs |
| GitHub Releases | healthy | 2 repos, 6 obs |
| Congress.gov | unavailable | feeds empty/no pubDates (correctly observable) |
| SEC | configuration_required | no UA (zero network requests) |

## 7. Git and Delivery

Head: a394fb3f2f2f18487fe94d73664d98ebe3a01287
PR: 14
Branch: workbench/source-evidence-pilot-v1
Replay zero-network: pass
Congress artifacts: pass
Disk hash recheck: pass
Output directory isolation: pass
Windows Chinese/space path: pass
Known baseline failures: 21 unchanged

# Source and Evidence Pilot V1 - Final Report

Run: PR-14-SEAL-001
Terminal State: SEALED_FOR_REMOTE_REVIEW

Validated implementation parent: a394fb3f2f2f18487fe94d73664d98ebe3a01287
Report and isolation repair: recorded by Git history
Canonical remote Head: read from PR #14 / Git

---

## 1. Source Coverage Matrix

| Category | Source | Live | Replay |
|----------|--------|------|--------|
| Security | CISA KEV | healthy (HTTP 200, SHA verified) | Deterministic, zero-HTTP |
| Regulatory | SEC Press Releases | configuration_required (no UA) | Deterministic, zero-HTTP |
| Legislative | Congress.gov (3 feeds) | unavailable (feeds empty/no pubDates) | Deterministic, zero-HTTP |
| Macro | BLS Labor Statistics | healthy (HTTP 200, 3 series) | Deterministic, zero-HTTP |
| Software Release | GitHub Releases (2 repos) | healthy (HTTP 200, 6 releases) | Deterministic, zero-HTTP |

## 2. Strict Output Directory Isolation

Any non-empty output directory is rejected with OUTPUT_DIRECTORY_NOT_EMPTY before any
telemetry or evidence is written. This covers: completed manifest, degraded manifest,
failed manifest, corrupt manifest, no manifest, and partial raw evidence directories.
Rejection leaves all existing files byte-for-byte unchanged.

Tested scenarios:
- Completed directory (ok manifest) rejected
- Degraded directory (degraded manifest) rejected
- Failed directory (failed manifest) rejected
- Corrupt manifest directory rejected
- Non-empty directory without manifest rejected
- Empty directory accepted
- Rejection does not modify existing files or add new ones

## 3. Test Results

tests/acquisition - 133 passed (129 original + 4 new isolation tests)

## 4. Key Properties

- Offline replay path: all 5 sources support replay_file, zero HTTP
- Congress persistence: 3 separate per-feed XML artifacts (not merged)
- Evidence manifest: each Observation points to its real per-feed artifact file
- Crash-safe manifests: run_manifest.json written atomically (temp+replace)
- Observation semantics: event_dedup_key source-independent
- Output isolation: any non-empty directory rejected before any writes
- No remote CI claimed
- Crash-safety claims limited to atomic manifest write

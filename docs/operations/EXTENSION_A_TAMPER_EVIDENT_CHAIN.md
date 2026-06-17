# Extension A: Tamper-Evident Audit Chain

The audit bundle `SHA256SUMS` file provides per-file integrity.  The
`manifest.json`'s `sha256` field wraps the entire manifest for a second
layer of verification.

## Chain structure

```
manifest.json  ──── bundle_hash (SHA256 of canonical JSON)
    │
    ├── SHA256SUMS ──── per-file SHA256 of every bundle file
    │
    ├── run_history.json
    ├── parent_child_graph.json
    ├── source_health.json
    ├── integrity_report.json
    ├── artifact_checksums.json
    ├── README.md
    └── run_history.db (optional)
```

Verification:

1. Check all declared files exist.
2. Verify each file's SHA256 against `SHA256SUMS`.
3. Verify the manifest hasn't been modified (the `sha256` field is
   the hash of the *rest of the manifest*).

No DB schema changes are required.

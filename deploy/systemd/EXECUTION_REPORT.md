## Execution Report — Production Runtime Packaging V1

### Branch
`feat/production-runtime-packaging-v1` (from `main`)

### Commit
`08bf40e` feat(systemd): replace while-true loop with systemd timer deployment

### PR
https://github.com/zhuo74451-art/crypto-event-intelligence/pull/13 (draft, not merged)

### Files Created (8)
| File | Purpose |
|------|---------|
| `scripts/operations/radar_one_shot.sh` | ExecStart entry point — flock lock, STOP marker, NO_SEND gate, timeout |
| `deploy/systemd/crypto-event-intel-radar.service` | Type=oneshot, User=crypto-event-intel, security hardening |
| `deploy/systemd/crypto-event-intel-radar.timer` | OnUnitActiveSec=10min, RandomizedDelaySec=60, default disabled |
| `deploy/systemd/env.radar.example` | Documented env vars template (secrets + config) |
| `deploy/systemd/install.sh` | Idempotent install — dirs, symlinks, daemon-reload, no auto-enable |
| `deploy/systemd/uninstall.sh` | Stop/disable, remove symlinks, `--clean-data` flag |
| `deploy/systemd/rollback.sh` | Atomic symlink switch to previous release |
| `deploy/systemd/dryrun.sh` | Pre-flight verification: paths, perms, token leakage, syntax, imports |

### Files Removed (1)
- `deploy/run_v09_tg_market_radar_server.sh` — replaced by systemd timer

### Architecture
```
systemd timer (10 min OnUnitActiveSec)
  -> crypto-event-intel-radar.service (Type=oneshot, Restart=no)
    -> scripts/operations/radar_one_shot.sh
      -> flock(LOCK_FILE)  prevents re-entry
      -> STOP_MARKER check before starting
      -> python3 run_v09_market_radar_cycle.py (env-configured args)
      -> exit  (next timer tick recovers)
```

### Security Checklist
- [x] Dedicated service user (crypto-event-intel, not root)
- [x] Restart=no — natural recovery via next timer tick
- [x] Per-cycle timeout (systemd 3600s + script 3300s)
- [x] flock file lock prevents concurrent runs
- [x] STOP marker for graceful stop
- [x] state/output (runtime/ logs/ results/) outside release tree
- [x] EnvironmentFile permission check (0400/0600)
- [x] Default V09_RADAR_NO_SEND=true (dry-run)
- [x] Independent send flags (SEND_BOARD, SEND_QUALITY_SUMMARY)
- [x] Atomic release switch via current symlink
- [x] Previous release preserved in releases/ for rollback
- [x] No tokens in unit files — all via EnvironmentFile

### Verification Steps (pending server deployment)
```bash
systemd-analyze verify deploy/systemd/crypto-event-intel-radar.service
systemd-analyze verify deploy/systemd/crypto-event-intel-radar.timer
bash deploy/systemd/dryrun.sh
# Manual one-shot test (dry-run mode):
V09_RADAR_NO_SEND=true bash scripts/operations/radar_one_shot.sh
```

### Note
systemd timer units are NOT automatically enabled.
Operator must explicitly `systemctl enable --now crypto-event-intel-radar.timer` after verifying configuration.

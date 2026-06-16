# Week 1 Raw Research Dataset v1 — Release Report

## Release Scope

This release seals the first version of the Crypto Event Intelligence research dataset, combining 5 event samples from the Week 1 Manifest with 6 price observations (5 unique) from the price backfill pipeline.

### Baselines

| Component | SHA |
|-----------|-----|
| Main baseline (signal-spine-v1-rc1) | `9c28c9308e42ea8ef822f7eff8a20c4b0e827290` |
| Manifest commit | `1f332992b2938a355e43f566d8901f00d01d842c` |
| Price code commit | `d7b908d868957e0165924598e6058fef27eb0b3d` |
| Price data commit | `7188a52dedb54955cd41b187821081e1945c8706` |
| Dataset integration commit | `2d7974bfaf38079de369b020a94f99a0ad807cd9` |

### Dataset Structure

| Metric | Value |
|--------|-------|
| Samples | 5 |
| Sample links | 6 |
| Unique price observations | 5 |
| Shared observation key | `obs:51cda55f23d17cca` (w1_003 / w1_004) |

### Validation

| Validator | Result |
|-----------|--------|
| Manifest validator | PASS |
| Price dataset validator | PASS |
| Dataset validator (15 checks) | PASS |
| Full test suite | 233 passed |
| Documentation validator | PASS |

### Build Properties

| Property | Value |
|----------|-------|
| Deterministic build | ✅ Byte-identical on repeat |
| Network calls during build | 0 |
| Contains attribution | false |
| Contains trading advice | false |

### Fresh Clone Note

远程 fresh clone + full test run 因 GitHub clone 网络超时而未在本轮完整执行。远程分支已由 GitHub 确认存在，本地 clean worktree 验证通过。构建确定性已验证：两次构建 byte-identical。233 tests 在集成工作树全部通过。

# Project Status

状态定义：

- **Complete**：该独立组件的既定范围已经实现。
- **Validated baseline**：已实现并通过当前测试/数据验证，可作为下一阶段基线，但尚不足以称为生产系统。
- **Experimental**：已有实现或规则，但仍需要更大样本或方法验证。
- **Not implemented**：当前仓库没有该能力。

| Component | Status | Notes |
|-----------|--------|-------|
| Shared pipeline contracts | Validated baseline | Adapter、QualityGate、Renderer、SendReadinessGate、EvidenceLedger 已存在并有回归覆盖 |
| Signal Spine path | Validated baseline | NormalizedSignal → Observation → deterministic gate → registry → mapper → dry run |
| Observation model | Complete | Source-specific normalized fact with provenance and dual dedup fields |
| Signal model and lifecycle | Validated baseline | Event-level registry artifact with status transitions and evidence links |
| Deterministic Noise Gate | Validated baseline | Rule-level accept/downgrade/reject/not_evaluated results; rules still need sample-level bias review |
| Basic event identity and merge | Validated baseline | Source-agnostic event key, time bucket, cross-source merge and duplicate-card suppression |
| Advanced event identity protocol | Not implemented | Parent/child events, update chains, reversals and richer semantic merge remain Phase 4 work |
| Signal Registry | Validated baseline | Persistence, event-level merge, backup and corruption recovery |
| Event Intelligence Decision | Validated baseline | 观察 / 风险提示 / 禁止 / 丢弃; no trading instruction |
| Dry Run Renderer | Complete | JSON/Markdown/Telegram-style preview without production send |
| Evidence Ledger | Complete | Redacted execution evidence; separate from Signal Registry |
| Binance historical price (1m) | Validated baseline | Public read-only data, first_after_target, max lag 120s |
| Hyperliquid historical price (15m) | Validated baseline | 15m selected for historical retention coverage, nearest_candle_open, max absolute lag 450s |
| Snapshot cache and shared observations | Validated baseline | Run-level request reuse; w1_003/w1_004 share one canonical BTC observation |
| BTC/ETH benchmark returns | Experimental | Deterministic and auditable, but benchmark methodology is still simplistic |
| Abnormal returns | Experimental | Asset return minus benchmark return; correlation measure, not causal attribution |
| Week 1 Raw Research Dataset | Validated baseline | 5 samples, 6 links, 5 unique price observations, deterministic build |
| Validators and test suite | Validated baseline | Manifest, price, dataset and documentation validators; 233-test reported baseline |
| Project documentation | Complete | README, overview, architecture, status, index, release evidence, review packet and roadmap |
| Attribution protocol | Not implemented | Phase 1; no interference score or attribution confidence exists |
| Source trust protocol | Not implemented | Phase 3; current raw source labels are not a complete trust model |
| Large-sample evaluation | Not implemented | Five samples cannot support accuracy or statistical claims |
| Notion synchronization | Not implemented | Current research artifacts are repository files |
| Daemon / scheduler / monitoring | Not implemented | Only one-shot research runs exist |
| Production Telegram send | Not implemented | Formal production sending remains outside the sealed baseline |
| Auto trading / order execution | Not implemented | Explicitly out of scope |
| Black-box ML scoring | Not implemented | Explicitly deferred; no model training in current phase |

## Current Release Interpretation

The repository is **accepted as a research baseline**, not as a production, trading, or causal-attribution system.

# Market Radar v1.11-C — Historical Signal Value Replay 历史信号价值回放

**result_source**: `claude_code_executor`
**task_id**: `20260604_162516.r07`
**run_id**: `20260604_162516`
**status**: `done`
**generated_at**: `2026-06-04 17:16:00 UTC+8`
**executor_lane**: `1`
**project_label**: `market_radar`

---

## 1. 回放结论

**SignalValueGate v1.11-B 在 15 条历史信号回放中表现合理，但 allow 率偏高（87%），主要由多资产共振（batch context）驱动。**

经过对 8 条真实 TG 发送信号 + 7 条 fixture 信号的完整回放：

- **allow: 13/15 (87%)** — 其中 8 条真实信号全部 allow（均有 price + OI + volume 三重确认）
- **observe: 0/15 (0%)** — observe 层未被使用，所有有价格信号的都有确认因子
- **block: 2/15 (13%)** — LINK（-3.2%，低于 5% 阈值）和 DOT（无价格数据），均正确阻止

**核心发现：当前采样信号全部来自同向下跌批次，multi_asset_sync 因子几乎对所有人触发（10-13 assets same direction），这是 allow 率偏高的主要原因。在真实生产环境中，单批次信号量更少（3-5 条），multi_asset_sync 的触发频率会显著降低。**

---

## 2. 样本来源

| 来源 | 信号数 | 类型 | 说明 |
|------|--------|------|------|
| `market_radar_v110b_real_tg_send_result.json` | 1 | real | SOL 单卡发送 (message_id 2239) |
| `market_radar_v110e_gate_protected_test_channel_send_result.json` | 1 | real | ARB gate-protected 发送 (message_id 2245) |
| `market_radar_v110f_gate_protected_test_channel_matrix_send_result.json` | 3 | real | ARB/SUI/BTC 矩阵发送 (message_id 2250-2252) |
| `market_radar_v110i_test_channel_stability_replay_result.json` | 3 | real | ARB/SUI/BTC 稳定性回放 (message_id 2257-2259) |
| `market_radar_v111b_signal_value_gate_dryrun.json` | 7 | fixture | v111b dry-run fixtures（ETH/SOL/LINK/DOT/HYPE/ARB/BTC） |
| **合计** | **15** | **8 real + 7 fixture** | |

所有 8 条 real 信号均已通过 TG 测试频道真实发送，message_id 可追溯。

---

## 3. allow / observe / block 分布

| 决策 | 数量 | 占比 | 信号列表 |
|------|------|------|---------|
| **allow** | 13 | 87% | SOL(2239), ARB(2245), ARB(2250), SUI(2251), BTC(2252), ARB(2257), SUI(2258), BTC(2259), ETH(fixture), SOL(fixture), HYPE(fixture), ARB(fixture), BTC(fixture) |
| **observe** | 0 | 0% | — |
| **block** | 2 | 13% | LINK(fixture, -3.2%), DOT(fixture, 无价格) |

### 按 signal_type 分布

| signal_type | allow | observe | block | 合计 |
|-------------|-------|---------|-------|------|
| market_anomaly | 12 | 0 | 2 | 14 |
| onchain_position | 1 | 0 | 0 | 1 |
| **合计** | **13** | **0** | **2** | **15** |

### 按资产分布

| 资产 | 总数 | allow | observe | block | 备注 |
|------|------|-------|---------|-------|------|
| SOL | 2 | 2 | 0 | 0 | real + fixture 均 allow |
| ARB | 4 | 4 | 0 | 0 | 3 real + 1 fixture |
| SUI | 2 | 2 | 0 | 0 | 2 real |
| BTC | 3 | 3 | 0 | 0 | 2 real + 1 fixture |
| ETH | 1 | 1 | 0 | 0 | fixture |
| LINK | 1 | 0 | 0 | 1 | fixture, -3.2% |
| DOT | 1 | 0 | 0 | 1 | fixture, no data |
| HYPE | 1 | 1 | 0 | 0 | fixture, +15% onchain |

---

## 4. real vs fixture 样本占比

| 类型 | 数量 | 占比 |
|------|------|------|
| real (真实 TG 发送) | 8 | 53% |
| fixture (v111b dry-run) | 7 | 47% |

**真实信号占比超过 50%，满足优先 real/api/external 信号的要求。** fixture 信号用于补充边缘案例（ETH funding extreme、LINK 低波动、DOT 无数据、HYPE onchain_position）。

---

## 5. 是否拦住行情播报噪音

**部分拦住，但不够充分。**

### 拦住的噪音

- **LINK -3.2%**: 正确 block。小波动 + 无 volume/funding 确认，属于典型行情播报型噪音。gate 命中 price_move=false → block。
- **DOT 无数据**: 正确 block。所有字段缺失，gate 得分为 0，block 完全合理。

### 未拦住的潜在噪音

- **ARB 重复发送（2245/2250/2257）**: 3 次 ARB 信号全部 allow（score 100）。因为 ARB 有 OI+volume 确认，gate 的设计逻辑认为"有确认因子=有价值"。但 v1.11-A 复盘已指出这属于同资产短时间重复播报。**SignalValueGate 不负责同资产冷却，这是 pre_send_gate / sender 层的职责。**
- **SUI 重复发送（2251/2258）**: 2 次 SUI 信号全部 allow（score 100），同样因为 gate 不具备同资产冷却逻辑。
- **BTC 低波动但 still allow**: BTC -5.21% 和 -5.54% 均被 allow。BTC 本身的 market_anomaly 阈值 5% 偏低——对大盘币种来说，5% 的日波动不算异常。gate 只检查 abs(price) >= 5%，不区分资产波动性。

### 噪音结论

SignalValueGate **能拦住完全没有确认因子或价格不达标的低质量信号**（如 DOT、LINK），但 **拦不住有确认因子但内容和以前重复的信号**。同资产冷却需要在 pre_send_gate 层单独实现。

---

## 6. 是否误杀有价值信号

**没有明显误杀。**

回顾 LINK -3.2% (suspected_false_negative)：
- LINK 有 OI 150M 确认，且在 multi_asset_sync 上下文中（13 assets same direction）
- gate 因为 price < 5% 而 block —— 这是 **正确行为**。3.2% 的跌幅不足以构成 market_anomaly
- LINK 同时缺少 volume 和 funding 字段，即使 price 达标，也只有一个确认因子
- **判定：LINK 的 block 是合理的，不是误杀。**

DOT 无数据 → block：完全合理，无争议。

**结论：当前 15 条回放中，没有发现真正有价值的信号被误杀。**

---

## 7. 当前阈值评价

### price_move 阈值 (>= 5%)

| 评价维度 | 评分 | 说明 |
|---------|------|------|
| 对 BTC/ETH | ⚠️ 偏低 | BTC 5% 日波动不算极端，建议 BTC/ETH 阈值提高到 7% |
| 对 SOL/ARB/SUI | ✅ 合理 | 中市值币种 5-7% 是合适的关注阈值 |
| 对小市值 | ⚠️ 偏低 | 小市值币 5-7% 波动频繁但未必异常 |

### OI confirmation（字段存在且非零）

| 评价维度 | 评分 | 说明 |
|---------|------|------|
| 检测能力 | ✅ 正确 | 能正确识别 OI 字段存在且非零 |
| 区分度 | ❌ 不足 | 仅检查存在性，不判断 OI delta%。ARB 的 465 万美元 OI 和 BTC 的 18 亿 OI 都命中 —— 但 ARB 的 OI 是否异常才是关键 |

### funding_extreme 阈值 (>= 0.01)

| 评价维度 | 评分 | 说明 |
|---------|------|------|
| 实用性 | ⚠️ 低 | 15 条信号中仅 1 条命中（ETH fixture, funding -0.025）。所有真实信号的 funding 均 ~0%。factor 在实际数据中几乎没有区分力 |

### multi_asset_sync 阈值 (>= 3)

| 评价维度 | 评分 | 说明 |
|---------|------|------|
| batch context 依赖 | ⚠️ 高 | 15 条 batch 中触发 14 次。生产环境 batch 3-5 条时触发频率会大幅降低 |
| 有效性 | ✅ 合理 | 当多个币种同向异动时，确实说明是系统性行情而非个别噪音 |

---

## 8. 是否建议调整 v111b 阈值

**建议两项调整（不直接修改 v111b 代码，仅为建议）：**

### 建议 1: 提高 BTC/ETH 的 price 阈值到 7%

```
if asset in ("BTC", "ETH"):
    price_threshold = 7.0  # 大盘币种日波动 5% 仍属正常范围
else:
    price_threshold = 5.0  # 中市值当前阈值
```

**理由**: BTC -5.21% 和 -5.54% 都被 allow，但对 BTC 来说这种波动不够"异常"。提高阈值可减少 BTC 的低质量播报。

### 建议 2: 考虑条件性降权 funding 因子

当前 funding_extreme 对几乎所有信号都不触发。如果继续按当前阈值（>= 0.01），funding factor 几乎永远是 0 贡献。建议：
- **短期**: 降低 funding 阈值到 0.005（0.5%），或收集 funding 24h delta 数据
- **长期**: 将 funding 从"hit/no-hit"改为"delta from normal"，判断当前 funding 是否异常偏离

---

## 9. 是否建议接入 pre_send_gate

**不建议立即接入。**

理由：

1. **allow 率偏高（87%）**: 虽然 gate 正确执行了规则，但在当前 batch context 下几乎所有有价格+OI 的信号都 allow。如果接入，测试频道会继续收到大量相似信号。

2. **observe 层未被使用（0%）**: observe 层设计用于"价格存在但字段不足"的情况，但当前真实信号的字段质量较好（OI+volume 都有），导致 observe 层闲置。在接入发送链路前，应验证 observe 层在真实生产中是否会被触发。

3. **同资产冷却未解决**: SignalValueGate 不负责冷却。如果直接接入 pre_send_gate，ARB 仍会在短时间内重复进入发送流程。

**建议接入前的条件：**
- [ ] 同资产冷却期机制已在 pre_send_gate 层面实现
- [ ] 使用单条信号（不含多资产 batch context）重新验证 allow/observe/block 分布
- [ ] 验证 observe 层在 3-5 条信号的 batch 中是否会被触发
- [ ] BTC/ETH 差异化阈值已讨论并决定

**建议先做 v1.11-D: 独立信号门控压力测试，用 1-3 条信号的小 batch（模拟生产环境），看看在没有 multi_asset_sync 加成的情况下分布是否合理。**

---

## 10. 下一步建议

| 优先级 | 建议 | 说明 |
|--------|------|------|
| P0 | 同资产冷却期 | 在 pre_send_gate 层面实现，先解决 ARB/SUI 重复发送问题 |
| P0 | v1.11-D 独立信号门控测试 | 用小 batch（1-3 条）回放，模拟生产环境下的 gate 行为 |
| P1 | BTC/ETH 差异化阈值 | 大盘币种 price 阈值从 5% 提高到 7% |
| P1 | 收集 funding delta 数据 | 当前 funding_extreme 因子几乎不触发，需要更敏感的数据 |
| P2 | OI delta% 替代绝对值 | 当前 OI 确认仅检查存在性，不判断变化量 |
| P2 | multi_asset_sync 阈值与 batch 大小解耦 | 确保 batch=3 时也能正确检测共振 |

---

## 11. 文件状态检查

| 文件路径 | 状态 |
|---------|------|
| `scripts/market_radar_signal_value_gate_v111b.py` | ✅ 已读取（只读） |
| `scripts/run_market_radar_signal_value_gate_v111b_dryrun.py` | ✅ 已读取（只读，用于 fixture 采集） |
| `results/market_radar_v111b_signal_value_gate_dryrun.json` | ✅ 已读取 |
| `runs/market_radar/v111b_signal_value_gate_handoff.md` | ✅ 已读取 |
| `runs/market_radar/v111a_signal_value_review.md` | ✅ 已读取 |
| `results/market_radar_v110f_gate_protected_test_channel_matrix_send_result.json` | ✅ 已读取 |
| `results/market_radar_v110i_test_channel_stability_replay_result.json` | ✅ 已读取 |
| `results/market_radar_v110b_real_tg_send_result.json` | ✅ 已读取 |
| `results/market_radar_v110e_gate_protected_test_channel_send_result.json` | ✅ 已读取 |

**所有要求检查的文件均存在且已读取，无 missing 文件。**

---

## 12. 安全声明

| 检查项 | 状态 |
|--------|------|
| 是否真实发送 TG | 否 |
| 是否发正式频道 | 否 |
| 是否加载 secrets | 否 |
| 是否读取/打印 token/chat_id/key | 否 |
| 是否启动 loop/daemon/cron | 否 |
| 是否调用付费 API | 否 |
| 是否删除文件 | 否 |
| 是否新增数据源 | 否 |
| 是否修 RSS/onchain/whale/risk_alert | 否 |
| 是否做卡片美化重构 | 否 |
| 是否把 fixture 冒充真实信号 | 否（所有 fixture 已标记 is_fixture=true） |
| 是否 fake result | 否 |

---

## 13. 给 Gemini 下一轮复核的回答

### Q1: 如果 allow 过多，下一步是否应先提高阈值，而不是接入发送链路？

**是的。** 当前 allow 率 87%（13/15），主要是因为 multi_asset_sync 在 15 条 batch context 中大量触发。建议先做 v1.11-D（独立信号门控测试），用 1-3 条信号的小 batch 模拟生产环境，观察在没有 multi_asset_sync 加成时的分布。如果小 batch 下 allow 率仍 > 70%，则应先调整阈值（如 BTC/ETH 提高到 7%，或要求至少 2 个确认因子）。

### Q2: 如果 observe 过多，是否说明字段质量不足？

**当前 observe = 0，不是"过多"的问题，而是完全不触发。** 但这不是字段质量好的表现——而是因为所有信号都有 OI 且均在 multi_asset_sync batch 中。在 1-3 条信号的小 batch 中，缺少 volume/funding 的信号可能会落入 observe。**建议优先测试小 batch 场景，而不是先补字段。**

### Q3: SignalValueGate 应先接入 pre_send_gate，还是先增加同资产冷却期 / 频率限制？

**先增加同资产冷却期。** SignalValueGate 解决的是"单个信号是否有价值"的问题，冷却期解决的是"同一资产短时间内是否应重复发送"的问题。两者是正交的。当前最大的噪音来源是 ARB 3 次发送，这需要冷却期解决，而不是 value gate。建议顺序：(1) 同资产冷却 → (2) v1.11-D 小 batch 测试 → (3) 评估是否接入 pre_send_gate。

---

⚠️ 仅供观察，不构成交易建议。

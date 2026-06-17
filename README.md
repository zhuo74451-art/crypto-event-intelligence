# Crypto Event Intelligence

**加密事件事实整理、噪音过滤、价格反应回填与后续归因研究的证据型系统。**

这不是自动交易机器人，不是买卖信号服务，不是收益承诺系统，不是已完成的生产级归因引擎。

---

## 当前完整流程

```
Raw Source / Adapter
→ NormalizedSignal
→ Observation
→ Deterministic Noise Gate
→ Signal Registry
→ Event Intelligence Decision (观察 / 风险提示 / 禁止 / 丢弃)
→ Dry Run
→ Price Backfill (1h / 4h / 24h)
→ BTC / ETH Benchmark
→ Abnormal Return
→ Raw Research Dataset
→ Future Attribution Layer
```

## 当前最终决策

- **观察** — 值得关注，无行动建议
- **风险提示** — 存在值得注意的风险
- **禁止** — 在任何情况下都不应采取行动
- **丢弃** — 低质量 / 重复 / 不完整

没有 **long / short / buy / sell**。

## 已完成内容

| 组件 | 状态 |
|------|------|
| Signal Spine RC1 | ✅ Complete |
| Observation / Signal / Registry | ✅ Complete |
| 跨来源事件合并 | ✅ Complete |
| 重复卡片抑制 | ✅ Complete |
| 四类事件情报决策 | ✅ Complete |
| Fixture / Network / Degraded 来源区分 | ✅ Complete |
| Binance 历史价格回填 (BTC/ETH, 1m) | ✅ Complete |
| Hyperliquid 历史价格回填 (HYPE, 15m) | ✅ Complete |
| 1h / 4h / 24h 收益窗口 | ✅ Complete |
| BTC / ETH 异常收益 | ✅ Complete |
| Week 1 五条真实事件样本 | ✅ Complete |
| 5 个唯一价格观察 | ✅ Complete |
| 6 条样本-价格关联 | ✅ Complete |
| 233 项测试 | ✅ Complete |

## 未完成内容

| 组件 | 状态 |
|------|------|
| 事件归因置信度 | ❌ Not implemented |
| 干扰因素定量化 | ❌ Not implemented |
| 大规模样本验证 | ❌ Not implemented |
| 持续采集 daemon | ❌ Not implemented |
| Notion 自动回写 | ❌ Not implemented |
| 生产发送 | ❌ Not implemented |
| 自动交易 | ❌ Not implemented |

## 快速运行

所有验证命令均为离线确定性操作，不访问网络：

```bash
# 完整测试
python -X utf8 -m pytest tests/ -q

# Manifest 验证
python -X utf8 research/validate_manifest.py

# 价格数据集验证
python -X utf8 research/validate_week1_price_dataset.py research/week1_price_backfill_raw_v1.json

# 构建统一研究数据包
python -X utf8 research/build_week1_raw_research_dataset_v1.py

# 数据包验证
python -X utf8 research/validate_week1_raw_research_dataset_v1.py research/week1_raw_research_dataset_v1.json
```

### 网络模式价格刷新

```bash
python -X utf8 scripts/run_week1_sample_backfill_v1.py --mode network
```

## 核心数据文件

- [Manifest: 事件样本](research/week1_samples_v1.json)
- [价格回填原始结果](research/week1_price_backfill_raw_v1.json)
- [统一研究数据包](research/week1_raw_research_dataset_v1.json)
- [数据包文档](docs/research/week1_raw_research_dataset_v1.md)

## 安全边界

- **无私钥**: 所有 API 为公开只读
- **无交易权限**: 不连接交易所交易接口
- **无真实发送**: Dry Run 模式不发送 Telegram
- **公共只读 API**: Binance public REST, Hyperliquid public Info
- **输出不构成投资建议**: 所有输出明确标注 observation only

## 文档导航

- [项目详细说明](docs/PROJECT_OVERVIEW.md)
- [系统架构](docs/ARCHITECTURE.md)
- [文件索引](docs/INDEX.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [发布证据报告](docs/releases/week1_raw_research_dataset_v1_release.md)
- [审计证据](docs/audits/week1_raw_research_dataset_v1_release_evidence.md)
- [外部 AI 审阅包](docs/handoffs/EXTERNAL_AI_REVIEW_PACKET_V1.md)
- [后续路线图](docs/roadmap/NEXT_PHASE_PLAN_V1.md)
- [变更日志](CHANGELOG.md)

# Crypto Market Cognition & Signal OS

AI 驱动的加密市场认知与有效信号系统。

本仓库的唯一产品方向由 [`PROJECT_MAINLINE.md`](PROJECT_MAINLINE.md) 定义。此前的 Crypto Event Intelligence、Week 1、Signal Spine、事件归因阶段计划、Personal-Use RC1 和旧交接路线均已失效。

## 目标

系统持续理解宏观、政策、新闻、市场结构、资金与仓位、链上行为、稳定币、项目基本面、注意力和叙事，并把交易员方法、科研成果、官方资料与历史市场结果编译成可验证策略组件。

最终输出少量具备以下内容的市场影响判断：

- 方向或证据不足；
- 影响资产与时间尺度；
- 事件状态与事实证据；
- 市场事前预期和预期差；
- 传导路径；
- 市场确认、已定价程度与拥挤状态；
- 反方解释和失效条件；
- 经过验证和校准的置信度。

## 五个核心系统

1. **Market World Model**：宏观、监管、地缘、现货、衍生品、稳定币、链上、DeFi、Token供给、基本面、安全、情绪与数据质量。
2. **Research Intelligence**：论文、官方报告、产业研究、冲突证据、知识衰减和可测试假设。
3. **Trader Strategy Distillation**：蒸馏交易员的变量组合、触发、确认、时间尺度和失效条件，不做人物语气模仿。
4. **Strategy Registry & Arbitration**：按市场制度和证据调用策略，保存分歧并允许 `INSUFFICIENT_EVIDENCE`。
5. **Evidence Acquisition**：官方API、RSS、网页变化、正文抽取、证据归档、学术发现和通知服务。

## 现有代码

已有事件标准化、Registry、去重、价格回填、运行历史、审计、市场Reader、巨鲸域、渲染与Operator能力只被视为候选工程底座。后续逐项标记：

- `RETAIN`
- `ADAPT`
- `QUARANTINE`
- `DELETE`

旧测试、旧封板和旧文档不能单独成为保留理由。

## 当前实施边界

第一项开发是一次性、只读、可重放的来源与证据Pilot：

- SEC / EDGAR；
- Congress.gov / Federal Register；
- Federal Reserve / FRED / BLS / BEA；
- GitHub Releases / Security Advisories；
- Trafilatura正文抽取；
- changedetection.io变化检测合同；
- ArchiveBox证据归档合同；
- Apprise通知合同。

该Pilot只产出标准化Observation和来源健康证据。默认不启用后台循环、付费接口、生产发送或订单执行。

## 当前正式文档

- [主线合同](PROJECT_MAINLINE.md)
- [项目概览](docs/PROJECT_OVERVIEW.md)
- [系统架构](docs/ARCHITECTURE.md)
- [当前状态](docs/PROJECT_STATUS.md)
- [文档索引](docs/INDEX.md)
- [底座采用矩阵](research/intelligence/foundations/FOUNDATION_ADOPTION_MATRIX_V1.yaml)
- [来源采集合同](market_radar/acquisition/contracts/SOURCE_ACQUISITION_CONTRACT_V1.yaml)

## 基础验证

当前代码状态只以当前 `main` 的测试和产物为准：

```bash
python -X utf8 -m pytest tests/ -q
```

历史发布和审计材料只保留为过去提交的证据，不具有当前规划权。
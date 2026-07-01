# Crypto Market Cognition & Signal OS

AI 驱动的加密市场认知与有效信号系统。

本仓库的唯一正式方向由 [`PROJECT_MAINLINE.md`](PROJECT_MAINLINE.md) 与 [`project/CANONICAL_STATE.yaml`](project/CANONICAL_STATE.yaml) 定义。旧的 Crypto Event Intelligence、Week 1、Signal Spine、事件归因阶段计划、Personal-Use RC1 和历史交接路线均不再具有规划权。

## 核心成果

系统把时点证据、市场状态、事前预期、研究主张和策略组件编译为可解释的内部市场判断，并保留明确的证据不足与弃权状态。

正式判断应说明：

- 发生了什么、哪些事实仍不确定；
- 影响资产与时间尺度；
- 事件状态与事实证据；
- 市场事前预期和预期差；
- 传导路径；
- 市场确认、已定价程度与拥挤状态；
- 可用、拒绝和相互冲突的策略组件；
- 反方解释、到期和失效条件；
- 经过验证和校准的置信度，或明确弃权。

## 五个核心系统

1. **Market World Model**：宏观、监管、地缘、现货、衍生品、稳定币、链上、DeFi、Token供给、基本面、安全、情绪与数据质量。
2. **Research Intelligence**：论文、官方报告、产业研究、冲突证据、知识衰减和可测试假设。
3. **Trader Strategy Distillation**：蒸馏变量组合、触发、确认、时间尺度和失效条件，不做人物语气模仿。
4. **Strategy Registry & Arbitration**：按市场制度和证据调用策略，保存分歧并允许 `INSUFFICIENT_EVIDENCE`。
5. **Evidence Acquisition**：官方API、RSS、网页变化、正文抽取、证据归档、学术发现和来源健康。

## 当前事实边界

- `main` 保存正式项目身份、规划和决定。
- Draft PR #16 是候选认知与策略实现，不等于已通过严格 Internal Engineering V1。
- 当前业务节点是 Canonical State 同步与 Windows → Mac 责任迁移。
- 迁移完成后进入 Internal Engineering V1 Hardening，再进入有界真实数据 Shadow 实验。
- 默认禁止交易、钱包、付费接口、常驻服务、自动发布和生产写入。

## 正式读取顺序

1. [`PROJECT_MAINLINE.md`](PROJECT_MAINLINE.md)
2. [`project/CANONICAL_STATE.yaml`](project/CANONICAL_STATE.yaml)
3. [`project/PROJECT_BRAIN.md`](project/PROJECT_BRAIN.md)
4. [`project/PROJECT_PLAN.md`](project/PROJECT_PLAN.md)
5. [`project/DISCUSSION_STATE.yaml`](project/DISCUSSION_STATE.yaml)
6. [`project/DECISION_REGISTER.yaml`](project/DECISION_REGISTER.yaml)
7. [`project/LEARNING_QUEUE.yaml`](project/LEARNING_QUEUE.yaml)
8. 开放 PR、Issue、远程 Head、Diff、测试和运行证据

## 基础验证

```bash
python -X utf8 -m pytest tests/ -q
```

代码存在、Fixture与本地测试只证明相应边界内的实现；真实策略信任仍需后续时序化 Shadow 证据。

# Crypto Market Cognition & Signal OS

一个完全无人运行的加密市场认知与观察组合系统。

本仓库的正式方向由 [`PROJECT_MAINLINE.md`](PROJECT_MAINLINE.md) 与 [`project/CANONICAL_STATE.yaml`](project/CANONICAL_STATE.yaml) 定义。

## 系统责任

系统持续发现、核验、解释和维护市场命题，自主决定：

- 哪些信息值得继续研究；
- 哪些事件属于重复、噪声或证据不足；
- 是否创建、增强、削弱、失效、归档或重开命题；
- 哪些资产、板块或机制受到真实影响；
- 方向、时间尺度和已定价程度；
- 下一证据、复查时间和机器注意力；
- 什么情况下必须收缩判断、弃权或保持沉默。

系统维护的是持续变化的 **Autonomous Thesis Portfolio**，不是一次性报告流。

## 人与系统

日常判断循环不需要人工参与。普通不确定性由系统通过补证据、缩小主张、弃权、延迟复查、降级、失效或归档处理。

Owner只保留项目边界、权限、重大成本、公开运行、不可逆操作、停止和恢复的治理权。

## 已接受的底层合同

- [`project/AUTONOMOUS_JUDGMENT_CONTRACT.md`](project/AUTONOMOUS_JUDGMENT_CONTRACT.md)：J01-J22判断清单与L0-L3权限；
- [`project/THESIS_LIFECYCLE.md`](project/THESIS_LIFECYCLE.md)：命题状态与合法转移；
- [`project/ATTENTION_RESOURCE_POLICY.md`](project/ATTENTION_RESOURCE_POLICY.md)：优先级、容量、复查、通知、循环和恢复；
- [`project/RISK_ABSTENTION_CONSTITUTION.md`](project/RISK_ABSTENTION_CONSTITUTION.md)：主张边界、风险与强制弃权；
- [`project/LONGITUDINAL_VALIDATION_PLAN.md`](project/LONGITUDINAL_VALIDATION_PLAN.md)：回放、Shadow、基线、阈值与停止规则。

## 明确排除

- 带单与复制交易；
- 买卖、入场、出场、仓位、杠杆和收益承诺；
- 钱包签名和订单执行；
- 对外投资建议和自动发布；
- 未批准的付费接口；
- 无限发现、无限模型调用和失控循环。

## 当前事实边界

- Stage 1 底层责任设计已经完成，但不证明现有代码实现了它；
- 当前进入 **External Prior Art Challenge and Repository Responsibility Audit**；
- 下一步先比较成熟底座和更简单架构，再审计 `main` 与 Draft PR #16；
- 所有相关组件将被分类为 `RETAIN / ADAPT / QUARANTINE / REMOVE / MISSING`；
- 在审计接受前，不开始产品实现；
- Mac环境已足够继续讨论和后续执行，迁移卫生不阻塞项目思考。

## 正式读取顺序

1. [`PROJECT_MAINLINE.md`](PROJECT_MAINLINE.md)
2. [`project/CANONICAL_STATE.yaml`](project/CANONICAL_STATE.yaml)
3. [`project/STAGE1_EXIT.md`](project/STAGE1_EXIT.md)
4. [`project/STAGE2_EXTERNAL_PRIOR_ART_AND_REPO_AUDIT.md`](project/STAGE2_EXTERNAL_PRIOR_ART_AND_REPO_AUDIT.md)
5. [`project/PROJECT_BRAIN.md`](project/PROJECT_BRAIN.md)
6. [`project/PROJECT_PLAN.md`](project/PROJECT_PLAN.md)
7. 具体责任合同、Decision Register、Learning Queue与远程代码证据

## 基础验证

```bash
python -X utf8 -m pytest tests/ -q
```

代码存在、Fixture和单次运行只证明局部实现。无人认知质量必须通过时点回放、长期命题修订、弃权质量、注意力效率、基线比较和真实Shadow证据验证。

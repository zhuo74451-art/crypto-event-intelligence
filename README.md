# Crypto Market Cognition & Signal OS

一个完全无人运行的加密市场认知与观察组合系统。

本仓库的唯一正式方向由 [`PROJECT_MAINLINE.md`](PROJECT_MAINLINE.md) 与 [`project/CANONICAL_STATE.yaml`](project/CANONICAL_STATE.yaml) 定义。旧的 Crypto Event Intelligence、Week 1、Signal Spine、事件归因阶段计划、Personal-Use RC1、一次性市场判断包和历史交接路线均不再具有规划权。

## 系统责任

系统持续发现、核验、解释和维护市场命题，自主决定：

- 哪些新信息值得继续研究；
- 哪些事件只是重复、噪声或证据不足；
- 是否创建、增强、削弱、失效、归档或重新打开一个命题；
- 哪些资产、板块或机制受到影响；
- 影响方向、时间尺度和已定价程度；
- 下一步需要什么证据、何时复查；
- 命题应占用多少机器注意力和资源；
- 什么情况下必须弃权或保持沉默。

系统维护的是持续变化的 **Autonomous Thesis Portfolio**，不是一串一次性报告。

## 人与系统的关系

日常判断循环中不需要人工参与。普通不确定性由系统通过补证据、弃权、延迟复查、降级、失效或归档处理。

Owner只保留：

- 项目与覆盖范围治理；
- 凭证、权限和成本上限；
- 生产与发布授权；
- 钱包与交易权限；
- 停止、恢复和重大范围变更。

## 允许的自主发现

系统可以在未预先列出的情况下发现新的主题、命题和资产观察对象，但必须同时满足：

- 位于加密市场及直接相关的宏观、政策、技术、安全、流动性和基础设施范围；
- 使用已批准的公开或合同数据；
- 不突破成本和机器注意力预算；
- 存在明确机制、后续证据路径和退出条件；
- 不自行增加凭证、付费接口、公开发布、钱包或交易权限。

## 核心认知链

```text
证据
→ 事件
→ 解释性主张
→ 市场命题
→ 资产与主题暴露
→ 风险、已定价与分歧
→ 注意力状态
→ 后续取证与生命周期变化
→ 重大变化通知或保持沉默
```

## 判断责任分工

确定性代码优先承担：

- 身份、时间、哈希和来源；
- 事实权限、重复、冲突和未来数据泄漏；
- 成本、重试、资源和停止约束。

少量受限Agent承担：

- 命题形成与更新；
- 机制、暴露和时间尺度；
- 风险攻击与反方证据；
- 分歧保留与仲裁；
- 生命周期和注意力状态。

每个Agent必须具有结构化输入、结构化输出、权限边界和确定性降级路径。

## 明确排除

- 带单与复制交易；
- 买卖、入场、出场、仓位、杠杆和收益承诺；
- 钱包签名和订单执行；
- 对外投资建议和自动发布；
- 未批准的付费接口；
- 无限发现、无限模型调用和失控后台循环。

## 当前事实边界

- `main` 保存正式项目身份、责任、规划和决定。
- 当前业务节点是 **Autonomous Judgment Foundation**，不是电脑迁移。
- 先定义AI必须判断什么、Agent与规则如何分工、命题怎样变化、资源怎样受限、风险怎样进入决策。
- 完成底层责任定义后，再审计现有仓库并决定 `RETAIN / ADAPT / QUARANTINE / REMOVE / MISSING`。
- Draft PR #16 只是待审计的工程候选，不等于当前产品，也不等于已通过严格 Internal Engineering V1。
- Mac环境已足够继续项目讨论；剩余迁移卫生不阻塞产品思考。

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

代码存在、Fixture与单次运行只证明相应边界内的实现。无人认知质量必须通过长期命题变化、错误修正、注意力效率、弃权质量和真实Shadow证据验证。

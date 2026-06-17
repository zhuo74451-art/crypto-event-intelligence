# CRYPTO SIGNAL INTELLIGENCE MVP+
# SIX-LANE MASTER EXECUTION CHARTER V1

project: Crypto Signal Intelligence OS — Internal Workbench MVP+
repository: zhuo74451-art/crypto-event-intelligence

primary_repository_path: C:\Users\PC\Desktop\Projects\事件情报系统
approved_worktree_root: C:\Users\PC\Desktop\市场信号\crypto-event-intelligence-worktrees

**Path note**: Charter was originally authored with `zhuo7` user paths.
Actual environment uses `PC` user. All resolved paths are recorded in BASELINE_SEAL.json.

---

## 0. Authority Model

本任务采用六 Lane 受控并行开发。

固定角色：
- Lane 1: Hyperliquid Provider
- Lane 2: Whale Position Change & Risk Engine
- Lane 3: Market Context Provider
- Lane 4: Existing Flash / News / TG Feeds
- Lane 5: Workbench UI
- Lane 6: Contract Seal / Integration / Independent QA

## 1. Product Goal

在现有项目基础上完成一个内部只读 MVP+：
- 复用已有服务器快讯、新闻、Telegram 数据
- 获取 Hyperliquid 巨鲸当前仓位
- 识别巨鲸仓位变化
- 展示仓位价值、开仓价、杠杆、未实现盈亏、清算价和清算距离
- 补充 BTC/ETH/SOL/HYPE 市场上下文
- 生成一次性刷新、本地可打开的内部 Workbench

## 2. Key Constraints

See individual policy files in this directory for:
- PERMISSION_ENVELOPE_V1.md — network and resource permissions
- DEPENDENCY_POLICY_V1.md — third-party dependency rules
- INTEGRATION_ORDER_V1.md — lane execution and merge sequence
- STOP_AND_REPAIR_POLICY_V1.md — stop conditions and repair process

See contracts/mvpplus/v1/ for:
- JSON Schema contracts (data shapes)
- LANE_OWNERSHIP.json (file access control)
- BASELINE_SEAL.json (sealed baseline state)
- RESULT_SCHEMA.json (lane result format)
- THIRD_PARTY_REUSE_MANIFEST.json (dependency registry)

## 3. Non-Goals

- Internal production scheduler, daemon, cron
- Formal server deployment
- Formal Telegram/X publishing
- Automatic trading or copy trading
- User login, multi-tenant, paid API
- Vector DB, semantic clustering, full citation chain
- Level 3 Research, Calibration, Attribution
- Multi-agent financial analysis platform
- New microservice architecture

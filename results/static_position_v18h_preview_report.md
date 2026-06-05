# Market Radar v1.8H 本地预览报告

生成时间：2026-06-04 10:24:24 UTC+8
executor_lane: 1
project_label: market_radar

## 输入文件检查

| 文件 | 是否存在 | 大小 | 格式 |
|---|---|---|---|
| results/static_position_v18g_send_candidate.md | ✅ | 正常 | Markdown |
| results/static_position_v18g_send_candidate.json | ✅ | 正常 | JSON |
| results/static_position_v18g_send_gate_report.md | ✅ | 正常 | Markdown |

## 候选卡摘要

- **资产**: HYPE
- **方向**: 多头
- **实体**: HYPE 大额仓位地址 (0x082e...ca88)
- **持仓规模**: 1.00亿美元 (138.0万枚)
- **入场均价**: 38.68美元
- **标记价格**: 72.51美元
- **浮动盈亏**: +4669.85万美元 (+87.5%)
- **清算价**: 54.93美元
- **距清算**: 24.3%
- **评分**: 105

## 风险检查详情

### 文件完整性
- 3 个输入文件均非空 ✅
- Markdown 格式正常 ✅
- JSON 可解析 ✅

### 地址安全
- 仅使用短地址 0x082e...ca88，无完整钱包地址 ✅

### 敏感信息
- 无 token ✅
- 无 key ✅
- 无 cookie ✅
- 无 password ✅
- 无 chat_id ✅

### 平台标识
- 无正式频道标识 ✅
- 无正式群标识 ✅

### 闸门检查
- blocked: false ✅
- blocked_reasons: [] ✅
- consistency_status: pass ✅
- forbidden_terms_count: 0 ✅
- machine_terms_count: 0 ✅
- entry_price_consistency_status: pass ✅
- liquidation_distance_consistency_status: pass ✅
- pnl_sign_conflict: false ✅

### 确认状态
- should_send_now: false
- requires_user_confirmation: true
- dry_run_only: true
- 原因：v1.8G 设计为需要用户确认的干跑模式

## 预览文件

| 文件 | 路径 |
|---|---|
| Markdown 预览 | results/static_position_v18h_preview.md |
| HTML 预览 | results/static_position_v18h_preview.html |
| 预览报告 | results/static_position_v18h_preview_report.md |

## 安全边界确认

| 项目 | 状态 |
|---|---|
| 是否访问外部网络 | 否 |
| 是否调用平台接口 | 否 |
| 是否启动 loop | 否 |
| 是否打印敏感信息 | 否 |
| 是否写远程 DB / 生产环境 | 否 |
| 是否修改原候选卡 | 否 |

## 结论

✅ 本地预览通过。候选卡内容完整，所有风险检查项通过，无安全边界违规。

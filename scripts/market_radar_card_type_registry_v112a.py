"""Market Radar v1.12-A — Fixed Card Type Registry 固定卡片类型注册表

Defines 5 fixed card types for the Market Radar system, each with:
  - schema (required_fields, optional_fields)
  - admission_rules (条件准入)
  - block_rules (条件阻止)
  - public_template_rules (公开卡片模板规则)
  - risk_notes
  - readiness_level

This registry is the foundation for stable, long-running automated monitoring.
Deterministic rules only — no AI, no external API calls, no paid services.

Usage:
    from scripts.market_radar_card_type_registry_v112a import (
        CARD_TYPE_REGISTRY, get_all_card_types, get_card_type,
        validate_signal_against_card_type, check_admission, check_block,
        render_public_preview, assess_readiness,
    )

    registry = get_all_card_types()
    card_type_def = get_card_type("price_oi_volume_anomaly")
    validation = validate_signal_against_card_type(signal, card_type_def)

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

from typing import Any

REGISTRY_VERSION = "v1.12-A"
MODE = "fixed_card_type_matrix"

# ── 5 Fixed Card Types ────────────────────────────────────────────────────────────

CARD_TYPE_REGISTRY: dict[str, dict] = {
    # ═══════════════════════════════════════════════════════════════════════════════
    # 1. price_oi_volume_anomaly — 多因子价格异动
    # ═══════════════════════════════════════════════════════════════════════════════
    "price_oi_volume_anomaly": {
        "card_type": "price_oi_volume_anomaly",
        "display_name": "多因子价格异动卡",
        "display_name_en": "Multi-Factor Price/Volume/OI Anomaly Card",
        "purpose": (
            "检测并报告单一资产的价格 + 未平仓合约(OI) + 成交量 + 资金费率(funding) "
            "多因子同步异动。当价格显著变化且至少一个确认因子(OI/成交量/funding)同步异动时触发。"
        ),
        "category": "market_structure",

        # ── Schema ──────────────────────────────────────────────────────────
        "required_fields": [
            "asset",              # 资产符号，如 BTC / ETH / ARB
            "price_change_pct",   # 24h 涨跌幅百分比（可为负）
        ],
        "optional_fields": [
            "open_interest",      # 未平仓合约量（USD 或 token 数量）
            "oi_change_pct",      # OI 变化百分比
            "volume",             # 24h 成交量（USD）
            "volume_change_pct",  # 成交量变化百分比
            "funding",            # 资金费率（如 0.0001 = 0.01%）
            "funding_rate",       # 资金费率别名
            "liquidation_status", # 清算情况描述
            "is_crowded",         # 是否拥挤交易
            "observation_window", # 建议观察窗口
            "note",               # 备注
            "source_url",         # 来源 URL
            "trigger_reason",     # 触发原因
            "source",             # 数据来源标识
            "source_type",        # 数据来源类型（api / fixture / derived）
            "observed_at",        # 观测时间
            "core_entity",        # 核心实体（默认等于 asset）
        ],

        # ── Admission Rules ─────────────────────────────────────────────────
        "admission_rules": [
            {
                "rule_id": "adm_pova_001_price_threshold",
                "description": "价格涨跌幅绝对值 >= 5%",
                "expression": "abs(price_change_pct) >= 5.0",
                "severity": "required",
            },
            {
                "rule_id": "adm_pova_002_confirm_factor",
                "description": (
                    "至少一个确认因子存在且非零：OI（open_interest / oi / oi_usd 字段）或 "
                    "成交量（volume / dayNtlVlm / volume_24h 字段）或 "
                    "资金费率极端（abs(funding) >= 0.01）或 "
                    "多资产共振（>= 3 个真实资产同向）"
                ),
                "expression": (
                    "has_oi OR has_volume OR has_funding_extreme OR multi_asset_sync_count >= 3"
                ),
                "severity": "required",
            },
            {
                "rule_id": "adm_pova_003_asset_required",
                "description": "asset 字段必须存在且非空",
                "expression": "asset is not None and len(str(asset)) > 0",
                "severity": "required",
            },
        ],

        # ── Block Rules ─────────────────────────────────────────────────────
        "block_rules": [
            {
                "rule_id": "blk_pova_001_missing_asset",
                "description": "缺少 asset 字段 → block",
                "expression": "asset is None or len(str(asset)) == 0",
            },
            {
                "rule_id": "blk_pova_002_missing_price",
                "description": "缺少 price_change_pct 字段 → block",
                "expression": "price_change_pct not in signal or price_change_pct is None",
            },
            {
                "rule_id": "blk_pova_003_insignificant_price",
                "description": "abs(price_change_pct) < 3% → block（无意义波动）",
                "expression": "abs(price_change_pct) < 3.0",
            },
            {
                "rule_id": "blk_pova_004_no_confirm_at_all",
                "description": "OI/成交量/funding/多资产共振全部缺失 → block",
                "expression": (
                    "oi_missing AND volume_missing AND funding_missing AND "
                    "multi_asset_sync_count < 3"
                ),
            },
            {
                "rule_id": "blk_pova_005_fixture_as_live",
                "description": "fixture 样本不得标记为 live data 进入正式管道",
                "expression": "is_fixture is True AND data_mode != 'fixture'",
            },
        ],

        # ── Public Template Rules ───────────────────────────────────────────
        "public_template_rules": [
            {
                "rule_id": "tmpl_pova_001_title",
                "description": "标题格式：方向图标 + 行情异动｜资产 方向描述",
                "template": "{direction_icon} 行情异动｜{asset} {direction_desc}",
            },
            {
                "rule_id": "tmpl_pova_002_oneliner",
                "description": "一句话定性，包含资产、涨跌幅、多因子确认摘要",
                "template": (
                    "{asset} 24h {'涨' if pc>0 else '跌'}幅 {pc_pct}，"
                    "多因子异动信号 — {confirm_summary}。"
                ),
            },
            {
                "rule_id": "tmpl_pova_003_body",
                "description": "卡片主体：币种、涨跌幅、OI（如有）、成交量（如有）、Funding（如有）",
                "template": "● 币种：{asset} / ● 涨跌幅：{pc_pct} / ● OI：{oi} / ● 成交量：{vol} / ● Funding：{funding}",
            },
            {
                "rule_id": "tmpl_pova_004_links",
                "description": "公开行情链接（CoinGecko / DexScreener）",
                "template": "🔗 行情查看：CoinGecko / DexScreener link",
            },
            {
                "rule_id": "tmpl_pova_005_trigger",
                "description": "触发原因，自然语言描述",
                "template": "💡 触发原因：{trigger_reason}",
            },
            {
                "rule_id": "tmpl_pova_006_disclaimer",
                "description": "风险声明必须包含「不构成交易建议」",
                "template": "⚠️ 仅供观察，不构成交易建议。",
            },
        ],

        # ── Debug Leak Forbidden Terms ───────────────────────────────────────
        "public_forbidden_terms": [
            "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
            "payload_render", "format_check", "content_quality",
            "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
            "not_reached", "mock_sent", "mock_message_id",
            "gate_decision", "score↑", "blocked_by", "gate_version",
            "factor_hits", "block", "observe",
        ],

        # ── Risk Notes ──────────────────────────────────────────────────────
        "risk_notes": [
            "OI/成交量异常不预示价格方向，仅反映市场参与度变化。",
            "资金费率极端可能预示轧空/多杀多风险，但不保证反转。",
            "单一因子异动不足以确认趋势，需多因子交叉验证。",
            "fixture / 回测数据不能替代实时数据做交易决策。",
        ],

        # ── Readiness ────────────────────────────────────────────────────────
        "readiness_level": "ready",
        "readiness_detail": {
            "schema_complete": True,
            "admission_rules_defined": True,
            "block_rules_defined": True,
            "public_template_defined": True,
            "fixture_samples_available": True,
            "real_data_pipeline_available": True,
            "gate_integration_tested": True,
            "long_running_monitoring_gaps": [
                "需要 OI/Volume delta 实时追踪（区分趋势性 vs 瞬时异动）",
                "需要资金费率历史均值对比（判断当前是否真的极端）",
                "需要跨交易所数据一致性校验（防单交易所数据异常）",
            ],
        },
    },

    # ═══════════════════════════════════════════════════════════════════════════════
    # 2. whale_position_alert — 巨鲸/大户仓位变化
    # ═══════════════════════════════════════════════════════════════════════════════
    "whale_position_alert": {
        "card_type": "whale_position_alert",
        "display_name": "巨鲸仓位警报卡",
        "display_name_en": "Whale Position Alert Card",
        "purpose": (
            "检测并报告巨鲸/大户的链上仓位变化，包括加仓、减仓、爆仓边缘、"
            "浮盈浮亏等关键状态。覆盖 Hyperliquid 等公开 DEX 的大额持仓。"
        ),
        "category": "onchain_intelligence",

        # ── Schema ──────────────────────────────────────────────────────────
        "required_fields": [
            "asset",              # 资产符号
            "address",            # 钱包/账户地址
            "side",               # 多/空方向
            "position_value_usd", # 仓位价值（USD）
        ],
        "optional_fields": [
            "quantity",           # 持仓数量
            "entry_price",        # 开仓均价
            "mark_price",         # 当前标记价格
            "pnl_usd",            # 浮动盈亏（USD）
            "pnl_pct",            # 浮动盈亏百分比
            "liquidation_price",  # 清算价格
            "leverage",           # 杠杆倍数
            "label",              # 地址标签（如 "Smart Money / 机构"）
            "note",               # 备注说明
            "source_url",         # 来源 URL
            "trigger_reason",     # 触发原因
            "source",             # 数据来源
            "source_type",        # 来源类型（api / fixture / derived）
            "observed_at",        # 观测时间
            "core_entity",        # 核心实体
            "chain",              # 链/网络
        ],

        # ── Admission Rules ─────────────────────────────────────────────────
        "admission_rules": [
            {
                "rule_id": "adm_whale_001_value_threshold",
                "description": "仓位价值 >= $100,000 USD（巨鲸最低门槛）",
                "expression": "position_value_usd >= 100000",
                "severity": "required",
            },
            {
                "rule_id": "adm_whale_002_has_direction",
                "description": "side 字段必须存在（多/空）",
                "expression": "side in ['long', 'short', '多头', '空头']",
                "severity": "required",
            },
            {
                "rule_id": "adm_whale_003_address_present",
                "description": "address 必须存在且非空",
                "expression": "address is not None and len(str(address)) > 0",
                "severity": "required",
            },
            {
                "rule_id": "adm_whale_004_significant_pnl",
                "description": "浮盈/浮亏 >= 10% 或 pnl >= $10,000（显著变化才触发）",
                "expression": "abs(pnl_pct) >= 10 OR abs(pnl_usd) >= 10000",
                "severity": "recommended",
            },
        ],

        # ── Block Rules ─────────────────────────────────────────────────────
        "block_rules": [
            {
                "rule_id": "blk_whale_001_below_threshold",
                "description": "仓位价值 < $50,000 → block（非巨鲸级别）",
                "expression": "position_value_usd < 50000",
            },
            {
                "rule_id": "blk_whale_002_missing_address",
                "description": "缺少 address 字段 → block",
                "expression": "address not in signal or address is None",
            },
            {
                "rule_id": "blk_whale_003_missing_direction",
                "description": "缺少 side 字段 → block",
                "expression": "side not in signal or side is None",
            },
            {
                "rule_id": "blk_whale_004_dust_position",
                "description": "仓位价值 < $1,000 → block（粉尘仓位）",
                "expression": "position_value_usd < 1000",
            },
            {
                "rule_id": "blk_whale_005_fixture_as_live",
                "description": "fixture 样本不得标记为 live data",
                "expression": "is_fixture is True AND data_mode != 'fixture'",
            },
        ],

        # ── Public Template Rules ───────────────────────────────────────────
        "public_template_rules": [
            {
                "rule_id": "tmpl_whale_001_title",
                "description": "标题格式：方向图标 + 主力仓位雷达｜资产 方向 盈亏状态",
                "template": "{title_emoji} 主力仓位雷达｜{asset} {side} {pnl_desc}",
            },
            {
                "rule_id": "tmpl_whale_002_oneliner",
                "description": "一句话定性",
                "template": "{asset} {side} 持仓 {value_usd}，{'浮盈' if pnl>0 else '浮亏'} {pnl_pct}%。",
            },
            {
                "rule_id": "tmpl_whale_003_body",
                "description": "卡片主体：规模、数量、均价、现价、盈亏、清算价",
                "template": "● 持仓规模 / ● 持仓数量 / ● 均价 / ● 当前价格 / ● 当前盈亏 / ● 清算价",
            },
            {
                "rule_id": "tmpl_whale_004_address_masked",
                "description": "地址必须脱敏（前6后4）",
                "template": "📌 地址：`0x082d...8e9f`",
            },
            {
                "rule_id": "tmpl_whale_005_links",
                "description": "公开行情链接和来源链接",
                "template": "🔗 / 📎 links",
            },
            {
                "rule_id": "tmpl_whale_006_disclaimer",
                "description": "风险声明",
                "template": "⚠️ 仅供观察，不构成交易建议。",
            },
        ],

        # ── Debug Leak Forbidden Terms ───────────────────────────────────────
        "public_forbidden_terms": [
            "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
            "payload_render", "format_check", "content_quality",
            "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
            "not_reached", "mock_sent", "mock_message_id",
            "gate_decision", "score↑", "blocked_by", "gate_version",
            "factor_hits", "block", "observe",
        ],

        # ── Risk Notes ──────────────────────────────────────────────────────
        "risk_notes": [
            "巨鲸仓位不保证方向正确性，大户也可能被市场清算。",
            "地址标签可能不准确，需交叉验证。",
            "单一巨鲸行为不等于市场趋势，需结合多地址分析。",
            "链上数据有延迟，Hyperliquid 等 DEX 数据约 1-5 分钟延迟。",
        ],

        # ── Readiness ────────────────────────────────────────────────────────
        "readiness_level": "partial",
        "readiness_detail": {
            "schema_complete": True,
            "admission_rules_defined": True,
            "block_rules_defined": True,
            "public_template_defined": True,
            "fixture_samples_available": True,
            "real_data_pipeline_available": True,
            "gate_integration_tested": True,
            "long_running_monitoring_gaps": [
                "需要地址标签自动标注（Smart Money / 机构 / 做市商 / 散户）",
                "需要历史仓位变化追踪（同一地址的加减仓序列）",
                "需要多地址聚合分析（关联地址群组检测）",
                "需要爆仓预警实时推送（距清算价 < 5% 时触发）",
            ],
        },
    },

    # ═══════════════════════════════════════════════════════════════════════════════
    # 3. liquidation_pressure — 强平密集区 / 清算风险
    # ═══════════════════════════════════════════════════════════════════════════════
    "liquidation_pressure": {
        "card_type": "liquidation_pressure",
        "display_name": "清算压力预警卡",
        "display_name_en": "Liquidation Pressure Alert Card",
        "purpose": (
            "检测并报告市场中的强平密集区、清算风险、杠杆拥挤度和关键 "
            "liquidation level。当特定价格区间出现大量待清算仓位时触发。"
        ),
        "category": "risk_management",

        # ── Schema ──────────────────────────────────────────────────────────
        "required_fields": [
            "asset",                # 资产符号
            "liquidation_level",    # 关键清算价位
            "leverage_zone",        # 杠杆集中区间（如 "高杠杆区 $X-$Y"）
        ],
        "optional_fields": [
            "long_liq_total",       # 多头待清算总额（USD）
            "short_liq_total",      # 空头待清算总额（USD）
            "liq_cluster_price",    # 清算密集价格
            "liq_cluster_size",     # 清算密集规模（USD）
            "leverage_ratio",       # 当前杠杆率
            "crowded_direction",    # 拥挤方向（long / short）
            "estimated_cascade",   # 预估连锁清算规模
            "risk_level",           # 风险等级（low / medium / high / critical）
            "observation_window",   # 观察窗口
            "note",                 # 备注
            "source_url",           # 来源 URL
            "trigger_reason",       # 触发原因
            "source",               # 数据来源
            "source_type",          # 来源类型
            "observed_at",          # 观测时间
            "core_entity",          # 核心实体
        ],

        # ── Admission Rules ─────────────────────────────────────────────────
        "admission_rules": [
            {
                "rule_id": "adm_liq_001_has_level",
                "description": "必须有关键清算价位或清算密集区数据",
                "expression": (
                    "liquidation_level is not None OR liq_cluster_price is not None"
                ),
                "severity": "required",
            },
            {
                "rule_id": "adm_liq_002_significant_size",
                "description": "待清算总额 >= $1,000,000 或清算密集规模 >= $500,000",
                "expression": (
                    "long_liq_total >= 1000000 OR short_liq_total >= 1000000 OR "
                    "liq_cluster_size >= 500000"
                ),
                "severity": "required",
            },
            {
                "rule_id": "adm_liq_003_asset_required",
                "description": "asset 字段必须存在",
                "expression": "asset is not None and len(str(asset)) > 0",
                "severity": "required",
            },
        ],

        # ── Block Rules ─────────────────────────────────────────────────────
        "block_rules": [
            {
                "rule_id": "blk_liq_001_no_level_data",
                "description": "完全缺少清算价位/密集区数据 → block",
                "expression": (
                    "liquidation_level is None AND liq_cluster_price is None"
                ),
            },
            {
                "rule_id": "blk_liq_002_trivial_size",
                "description": "待清算总额 < $100,000 → block（不构成压力）",
                "expression": (
                    "(long_liq_total or 0) + (short_liq_total or 0) < 100000"
                ),
            },
            {
                "rule_id": "blk_liq_003_fixture_as_live",
                "description": "fixture 样本不得标记为 live data",
                "expression": "is_fixture is True AND data_mode != 'fixture'",
            },
        ],

        # ── Public Template Rules ───────────────────────────────────────────
        "public_template_rules": [
            {
                "rule_id": "tmpl_liq_001_title",
                "description": "标题：清算风险图标 + 资产 + 方向",
                "template": "🔻 清算压力预警｜{asset} {direction}拥挤",
            },
            {
                "rule_id": "tmpl_liq_002_oneliner",
                "description": "一句话定性",
                "template": "{asset} 在 {liq_level} 附近存在 {liq_size} 待清算仓位，{direction}杠杆拥挤。",
            },
            {
                "rule_id": "tmpl_liq_003_body",
                "description": "卡片主体：清算价位、多空清算额、杠杆率、风险等级",
                "template": "● 关键清算价 / ● 多头待清算 / ● 空头待清算 / ● 杠杆率 / ● 风险等级",
            },
            {
                "rule_id": "tmpl_liq_004_cascade_warning",
                "description": "如有连锁清算风险，明确标注",
                "template": "⚠️ 如触发连锁清算，预估影响规模 {estimated_cascade}",
            },
            {
                "rule_id": "tmpl_liq_005_disclaimer",
                "description": "风险声明",
                "template": "⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。",
            },
        ],

        # ── Debug Leak Forbidden Terms ───────────────────────────────────────
        "public_forbidden_terms": [
            "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
            "payload_render", "format_check", "content_quality",
            "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
            "not_reached", "mock_sent", "mock_message_id",
            "gate_decision", "score↑", "blocked_by", "gate_version",
            "factor_hits", "block", "observe",
        ],

        # ── Risk Notes ──────────────────────────────────────────────────────
        "risk_notes": [
            "清算数据来自公开交易所 API，可能有数分钟延迟。",
            "清算密集区不代表必然清算，市场可能在此前反转。",
            "杠杆拥挤度估计基于公开 OI 数据，实际杠杆分布可能有偏差。",
            "连锁清算的预估规模为理论最大值，实际清算可能分阶段执行。",
        ],

        # ── Readiness ────────────────────────────────────────────────────────
        "readiness_level": "missing",
        "readiness_detail": {
            "schema_complete": True,
            "admission_rules_defined": True,
            "block_rules_defined": True,
            "public_template_defined": True,
            "fixture_samples_available": True,
            "real_data_pipeline_available": False,
            "gate_integration_tested": False,
            "long_running_monitoring_gaps": [
                "缺少实时清算数据源（需要交易所 liquidation feed 或聚合 API）",
                "缺少清算价位热力图数据（liquidation heatmap）",
                "缺少杠杆率实时计算管道（OI / market cap ratio）",
                "缺少连锁清算模拟模型",
                "缺少历史清算事件对比基线",
            ],
        },
    },

    # ═══════════════════════════════════════════════════════════════════════════════
    # 4. multi_asset_market_sync — 多资产同步异动 / 板块共振
    # ═══════════════════════════════════════════════════════════════════════════════
    "multi_asset_market_sync": {
        "card_type": "multi_asset_market_sync",
        "display_name": "多资产共振卡",
        "display_name_en": "Multi-Asset Market Sync Card",
        "purpose": (
            "检测并报告多个资产（>= 3 个真实资产）在同一方向上的同步异动，"
            "包括板块轮动、相关资产共振、系统性走势。用于识别市场级别的"
            "结构性变化而非单一资产噪音。"
        ),
        "category": "market_structure",

        # ── Schema ──────────────────────────────────────────────────────────
        "required_fields": [
            "assets",              # 共振资产列表 [{asset, price_change_pct}, ...]，至少 3 个
            "direction",           # 共振方向（up / down / neutral）
        ],
        "optional_fields": [
            "sync_strength",       # 共振强度（0-100）
            "sector",              # 板块标签（L1 / L2 / DeFi / Meme / AI 等）
            "leader_asset",        # 领涨/领跌资产
            "follower_assets",     # 跟随资产列表
            "avg_price_change",    # 平均涨跌幅
            "max_price_change",    # 最大涨跌幅
            "min_price_change",    # 最小涨跌幅
            "oi_direction_match",  # OI 变化方向是否与价格一致
            "volume_surge_ratio",  # 成交量放大比例
            "observation_window",  # 观察窗口
            "note",                # 备注
            "source_url",          # 来源 URL
            "trigger_reason",      # 触发原因
            "source",              # 数据来源
            "source_type",         # 来源类型
            "observed_at",         # 观测时间
            "core_entity",         # 核心实体
        ],

        # ── Admission Rules ─────────────────────────────────────────────────
        "admission_rules": [
            {
                "rule_id": "adm_sync_001_min_assets",
                "description": "至少 3 个真实资产（非 fixture）在同一方向",
                "expression": "real_same_direction_asset_count >= 3",
                "severity": "required",
            },
            {
                "rule_id": "adm_sync_002_has_direction",
                "description": "共振方向必须明确（up 或 down）",
                "expression": "direction in ['up', 'down']",
                "severity": "required",
            },
            {
                "rule_id": "adm_sync_003_backing",
                "description": "需有 OI 或成交量至少一个作为共振支撑（防假共振）",
                "expression": "oi_direction_match is True OR volume_surge_ratio >= 1.5",
                "severity": "recommended",
            },
        ],

        # ── Block Rules ─────────────────────────────────────────────────────
        "block_rules": [
            {
                "rule_id": "blk_sync_001_insufficient_assets",
                "description": "同向真实资产 < 3 → block",
                "expression": "real_same_direction_asset_count < 3",
            },
            {
                "rule_id": "blk_sync_002_all_fixture",
                "description": "所有资产都是 fixture → block",
                "expression": "real_same_direction_asset_count == 0",
            },
            {
                "rule_id": "blk_sync_003_no_direction",
                "description": "无明确方向（neutral）→ block",
                "expression": "direction == 'neutral'",
            },
            {
                "rule_id": "blk_sync_004_fixture_as_live",
                "description": "fixture 样本不得标记为 live data",
                "expression": "is_fixture is True AND data_mode != 'fixture'",
            },
        ],

        # ── Public Template Rules ───────────────────────────────────────────
        "public_template_rules": [
            {
                "rule_id": "tmpl_sync_001_title",
                "description": "标题：共振图标 + 方向 + 资产数 + 板块（如有）",
                "template": "🌐 多资产共振｜{direction_desc} {asset_count}个资产{'· ' + sector if sector else ''}",
            },
            {
                "rule_id": "tmpl_sync_002_oneliner",
                "description": "一句话定性",
                "template": "检测到 {asset_count} 个资产同步{direction_desc}，{sector_desc}，平均涨跌幅 {avg_pct}%。",
            },
            {
                "rule_id": "tmpl_sync_003_asset_list",
                "description": "资产列表（限制展示前 5 个）",
                "template": "● 领涨/跌：{leader} / ● 跟随：{followers} / ● （共 {total} 个资产）",
            },
            {
                "rule_id": "tmpl_sync_004_backing",
                "description": "如有 OI/成交量共振支撑，标注",
                "template": "● 共振支撑：OI {'一致' if oi_match else '待确认'} / 成交量 {'放大' if vol_surge else '待确认'}",
            },
            {
                "rule_id": "tmpl_sync_005_disclaimer",
                "description": "风险声明",
                "template": "⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。",
            },
        ],

        # ── Debug Leak Forbidden Terms ───────────────────────────────────────
        "public_forbidden_terms": [
            "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
            "payload_render", "format_check", "content_quality",
            "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
            "not_reached", "mock_sent", "mock_message_id",
            "gate_decision", "score↑", "blocked_by", "gate_version",
            "factor_hits", "block", "observe",
        ],

        # ── Risk Notes ──────────────────────────────────────────────────────
        "risk_notes": [
            "多资产共振可能由宏观事件驱动，而非单一资产基本面。",
            "板块轮动快速，共振信号可能很快衰减。",
            "fixture 信号不计入真实共振计数，需确保数据源可靠性。",
            "跨交易所价格差异可能导致同一资产在不同来源中方向不一致。",
        ],

        # ── Readiness ────────────────────────────────────────────────────────
        "readiness_level": "partial",
        "readiness_detail": {
            "schema_complete": True,
            "admission_rules_defined": True,
            "block_rules_defined": True,
            "public_template_defined": True,
            "fixture_samples_available": True,
            "real_data_pipeline_available": True,
            "gate_integration_tested": True,
            "long_running_monitoring_gaps": [
                "需要跨资产实时相关性矩阵（自动检测共振，而非依赖 context 传入）",
                "需要板块/赛道自动分类（L1/L2/DeFi/Meme/AI 等标签）",
                "需要领涨/领跌资产自动识别",
                "需要共振强度衰减追踪（信号发出后的持续性验证）",
                "需要日内多次快照对比（区分日内波动 vs 趋势共振）",
            ],
        },
    },

    # ═══════════════════════════════════════════════════════════════════════════════
    # 5. news_event_market_impact — 新闻/事件驱动型市场影响
    # ═══════════════════════════════════════════════════════════════════════════════
    "news_event_market_impact": {
        "card_type": "news_event_market_impact",
        "display_name": "新闻事件影响卡",
        "display_name_en": "News Event Market Impact Card",
        "purpose": (
            "检测并报告新闻/事件驱动的市场影响，包括监管动态、项目事故、"
            "ETF 进展、宏观数据发布、交易所事件等。评估事件的交易相关性和"
            "市场定价程度。"
        ),
        "category": "event_driven",

        # ── Schema ──────────────────────────────────────────────────────────
        "required_fields": [
            "event_title",        # 事件标题
            "affected_assets",    # 受影响资产（逗号分隔或多值）
            "event_type",         # 事件类型（监管/技术/安全/交易/上线/合作/宏观/交易所等）
        ],
        "optional_fields": [
            "trading_relevance",  # 交易相关性（高/中/低/待评估）
            "already_priced",     # 是否已被市场定价（已定价/部分已定价/未定价/未知）
            "risk_tags",          # 风险标签
            "observation_window", # 建议观察窗口
            "summary",            # 事件摘要
            "source",             # 信息来源
            "source_name",        # 来源名称
            "source_url",         # 来源 URL
            "impact_scope",       # 影响范围
            "urgency_level",      # 紧急程度（high / medium / low）
            "trigger_reason",     # 触发原因
            "source_type",        # 来源类型
            "observed_at",        # 观测时间
            "core_entity",        # 核心实体
        ],

        # ── Admission Rules ─────────────────────────────────────────────────
        "admission_rules": [
            {
                "rule_id": "adm_news_001_has_title",
                "description": "event_title 必须存在且非空",
                "expression": "event_title is not None and len(str(event_title)) > 0",
                "severity": "required",
            },
            {
                "rule_id": "adm_news_002_has_assets",
                "description": "affected_assets 必须存在且非空",
                "expression": (
                    "affected_assets is not None and len(str(affected_assets)) > 0"
                ),
                "severity": "required",
            },
            {
                "rule_id": "adm_news_003_has_type",
                "description": "event_type 必须为已知类型之一",
                "expression": (
                    "event_type in ['监管', '政策', '技术', '安全', '交易', "
                    "'上线', '合作', '宏观', '交易所', '事故', 'ETF', '其他']"
                ),
                "severity": "required",
            },
            {
                "rule_id": "adm_news_004_relevance",
                "description": "交易相关性不为「无」或「极低」",
                "expression": "trading_relevance not in ['无', '极低', 'none']",
                "severity": "recommended",
            },
        ],

        # ── Block Rules ─────────────────────────────────────────────────────
        "block_rules": [
            {
                "rule_id": "blk_news_001_no_title",
                "description": "缺少 event_title → block",
                "expression": "event_title is None or len(str(event_title)) == 0",
            },
            {
                "rule_id": "blk_news_002_no_assets",
                "description": "缺少 affected_assets → block",
                "expression": (
                    "affected_assets is None or len(str(affected_assets)) == 0"
                ),
            },
            {
                "rule_id": "blk_news_003_already_fully_priced",
                "description": "事件已被市场完全定价 → block",
                "expression": "already_priced in ['已定价', 'fully priced']",
            },
            {
                "rule_id": "blk_news_004_no_relevance",
                "description": "交易相关性为「无」→ block",
                "expression": "trading_relevance in ['无', '极低', 'none']",
            },
            {
                "rule_id": "blk_news_005_fixture_as_live",
                "description": "fixture 样本不得标记为 live data",
                "expression": "is_fixture is True AND data_mode != 'fixture'",
            },
        ],

        # ── Public Template Rules ───────────────────────────────────────────
        "public_template_rules": [
            {
                "rule_id": "tmpl_news_001_title",
                "description": "标题：事件类型图标 + 新闻事件｜事件标题",
                "template": "{type_icon} 新闻事件｜{event_title}",
            },
            {
                "rule_id": "tmpl_news_002_oneliner",
                "description": "一句话定性",
                "template": "{event_type}类型事件，影响 {affected_assets}，交易相关性 {trading_relevance}。",
            },
            {
                "rule_id": "tmpl_news_003_body",
                "description": "卡片主体：影响币种、事件类型、交易相关性、摘要、是否已定价",
                "template": "● 影响币种 / ● 事件类型 / ● 交易相关性 / ● 摘要 / ● 是否已提前反应",
            },
            {
                "rule_id": "tmpl_news_004_risk_tags",
                "description": "如有风险标签，展示",
                "template": "● 风险标签：{risk_tags}",
            },
            {
                "rule_id": "tmpl_news_005_source",
                "description": "来源标注",
                "template": "● 来源：{source_name} / ● 观察窗口：{observation_window}",
            },
            {
                "rule_id": "tmpl_news_006_disclaimer",
                "description": "风险声明",
                "template": "⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。",
            },
        ],

        # ── Debug Leak Forbidden Terms ───────────────────────────────────────
        "public_forbidden_terms": [
            "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
            "payload_render", "format_check", "content_quality",
            "价值:", "冷却:", "pre_send:", "allow", "upgrade_override",
            "not_reached", "mock_sent", "mock_message_id",
            "gate_decision", "score↑", "blocked_by", "gate_version",
            "factor_hits", "block", "observe",
        ],

        # ── Risk Notes ──────────────────────────────────────────────────────
        "risk_notes": [
            "新闻事件具有高度时效性，延迟推送可能导致信息已过时。",
            "事件解读存在主观性，同一事件不同来源可能有不同表述。",
            "部分事件可能为虚假信息或市场操纵行为。",
            "需要人工或 AI 审核事件真实性后再推送。",
        ],

        # ── Readiness ────────────────────────────────────────────────────────
        "readiness_level": "missing",
        "readiness_detail": {
            "schema_complete": True,
            "admission_rules_defined": True,
            "block_rules_defined": True,
            "public_template_defined": True,
            "fixture_samples_available": True,
            "real_data_pipeline_available": False,
            "gate_integration_tested": False,
            "long_running_monitoring_gaps": [
                "缺少实时新闻 RSS/API 接入管道（CoinDesk / The Block / 官方博客等）",
                "缺少事件自动分类（NLP 识别监管/技术/安全/宏观等类型）",
                "缺少 Affected Assets 自动提取（从新闻文本中识别受影响币种）",
                "缺少已定价判断模型（事件发生 vs 市场价格反应的时间差分析）",
                "缺少事件去重/合并（同一事件多来源重复推送）",
                "缺少交易相关性自动评估（事件对价格的实际影响量化）",
            ],
        },
    },
}


# ── Public API ────────────────────────────────────────────────────────────────────

def get_all_card_types() -> dict[str, dict]:
    """Return the complete card type registry.

    Returns a deep copy to prevent accidental mutation.
    """
    import copy
    return copy.deepcopy(CARD_TYPE_REGISTRY)


def get_card_type(card_type: str) -> dict | None:
    """Get a single card type definition by key.

    Returns None if the card_type is not found in the registry.
    """
    import copy
    ct = CARD_TYPE_REGISTRY.get(card_type)
    if ct is None:
        return None
    return copy.deepcopy(ct)


def list_card_types() -> list[str]:
    """Return sorted list of all registered card type keys."""
    return sorted(CARD_TYPE_REGISTRY.keys())


def get_card_type_count() -> int:
    """Return the number of registered card types."""
    return len(CARD_TYPE_REGISTRY)


def validate_signal_against_card_type(
    signal: dict,
    card_type_def: dict,
) -> dict:
    """Validate a signal against a card type's schema.

    Checks:
      - required_fields are present and non-None
      - optional_fields that are present are noted
      - admission rules are evaluated
      - block rules are evaluated

    Args:
        signal: Signal dict to validate
        card_type_def: Card type definition from the registry

    Returns:
        Dict with:
          - card_type: str
          - schema_valid: bool
          - missing_required: list[str]
          - present_optional: list[str]
          - admission_result: dict {rule_id: bool, ...}
          - admission_passed: bool
          - block_result: dict {rule_id: bool, ...}
          - block_triggered: bool
          - block_reason: str | None
          - all_checks_passed: bool
    """
    card_type = card_type_def["card_type"]
    required = card_type_def.get("required_fields", [])
    optional = card_type_def.get("optional_fields", [])

    # ── Required fields check ───────────────────────────────────────────
    missing_required: list[str] = []
    for field in required:
        if field not in signal or signal.get(field) is None:
            missing_required.append(field)

    # ── Optional fields check ───────────────────────────────────────────
    present_optional: list[str] = []
    for field in optional:
        if field in signal and signal.get(field) is not None:
            present_optional.append(field)

    schema_valid = len(missing_required) == 0

    # ── Admission check ─────────────────────────────────────────────────
    admission_result, admission_passed = _evaluate_admission_rules(
        signal, card_type_def
    )

    # ── Block check ─────────────────────────────────────────────────────
    block_result, block_triggered, block_reason = _evaluate_block_rules(
        signal, card_type_def
    )

    all_checks_passed = schema_valid and admission_passed and not block_triggered

    return {
        "card_type": card_type,
        "schema_valid": schema_valid,
        "missing_required": missing_required,
        "present_optional": present_optional,
        "admission_result": admission_result,
        "admission_passed": admission_passed,
        "block_result": block_result,
        "block_triggered": block_triggered,
        "block_reason": block_reason,
        "all_checks_passed": all_checks_passed,
    }


def check_admission(signal: dict, card_type_def: dict) -> tuple[bool, dict]:
    """Check if a signal passes the admission rules for a card type.

    Returns (passed: bool, details: dict).
    """
    return _evaluate_admission_rules(signal, card_type_def)


def check_block(signal: dict, card_type_def: dict) -> tuple[bool, str | None]:
    """Check if a signal triggers any block rules for a card type.

    Returns (blocked: bool, reason: str | None).
    """
    result, blocked, reason = _evaluate_block_rules(signal, card_type_def)
    return blocked, reason


# ── Public Preview Renderer ────────────────────────────────────────────────────────

def render_public_preview(
    card_type_def: dict,
    signal: dict,
    validation_result: dict | None = None,
) -> str:
    """Render a public preview card from a card type definition and signal.

    Uses the public_template_rules from the card type definition to generate
    a clean, debug-free public card text.

    Args:
        card_type_def: Card type definition from the registry.
        signal: Signal data dict.
        validation_result: Optional pre-computed validation result.

    Returns:
        Public card text string (no internal gate/debug terms).
    """
    card_type = card_type_def["card_type"]
    renderers = {
        "price_oi_volume_anomaly": _render_pova_public,
        "whale_position_alert": _render_whale_public,
        "liquidation_pressure": _render_liquidation_public,
        "multi_asset_market_sync": _render_sync_public,
        "news_event_market_impact": _render_news_public,
    }
    renderer = renderers.get(card_type)
    if renderer:
        return renderer(signal, card_type_def)
    return _render_fallback_public(signal, card_type_def)


def assess_readiness(card_type_def: dict) -> dict:
    """Assess the readiness level of a card type for long-running monitoring.

    Returns:
        Dict with:
          - card_type: str
          - readiness_level: "ready" | "partial" | "missing"
          - suitable_for_long_running_monitoring: bool
          - missing_fields: list[str]
          - missing_data_sources: list[str]
          - missing_rules: list[str]
          - next_gap: str
    """
    rd = card_type_def.get("readiness_detail", {})
    level = card_type_def.get("readiness_level", "missing")

    # Collect gaps
    missing_fields: list[str] = []
    missing_data_sources: list[str] = []
    missing_rules: list[str] = []

    if not rd.get("schema_complete"):
        missing_fields.append("schema incomplete")
    if not rd.get("real_data_pipeline_available"):
        missing_data_sources.append("real_data_pipeline")
    if not rd.get("gate_integration_tested"):
        missing_rules.append("gate integration not tested")

    gaps = rd.get("long_running_monitoring_gaps", [])
    for gap in gaps:
        if "数据" in gap or "源" in gap or "API" in gap or "接入" in gap:
            missing_data_sources.append(gap)
        elif "规则" in gap or "gate" in gap.lower() or "集成" in gap:
            missing_rules.append(gap)
        else:
            missing_fields.append(gap)

    suitable = level == "ready"

    # Determine next_gap
    next_gap = ""
    if missing_data_sources:
        next_gap = missing_data_sources[0]
    elif missing_fields:
        next_gap = missing_fields[0]
    elif missing_rules:
        next_gap = missing_rules[0]
    else:
        next_gap = "no critical gaps identified"

    return {
        "card_type": card_type_def["card_type"],
        "readiness_level": level,
        "suitable_for_long_running_monitoring": suitable,
        "missing_fields": missing_fields,
        "missing_data_sources": missing_data_sources,
        "missing_rules": missing_rules,
        "next_gap": next_gap,
    }


# ── Dynamic Readiness Update (v1.12-C) ─────────────────────────────────────────────

def update_liquidation_readiness_from_adapter(
    adapter_result_path: str | None = None,
    valid_signal_count: int = 0,
    public_card_count: int = 0,
    force_missing: bool = False,
) -> dict:
    """Update liquidation_pressure readiness based on v112b adapter state.

    This function dynamically updates the readiness_level for liquidation_pressure
    in the registry based on whether the v112b local snapshot adapter has produced
    valid output.

    Readiness logic:
      - If force_missing or no adapter exists → readiness = "missing"
      - If adapter exists and >= 3 valid signals + >= 3 clean public cards → "partial"
      - Only live data source + long-term monitoring → "ready" (future)

    Args:
        adapter_result_path: Optional path to v112b result JSON for auto-detection.
        valid_signal_count: Number of valid liquidation signals from adapter.
        public_card_count: Number of clean public cards from adapter.
        force_missing: Force readiness back to "missing".

    Returns:
        Dict with readiness_update details.
    """
    import json
    from pathlib import Path as _Path

    ct_def = CARD_TYPE_REGISTRY.get("liquidation_pressure")
    if ct_def is None:
        return {
            "card_type": "liquidation_pressure",
            "previous_readiness": "unknown",
            "new_readiness": "unknown",
            "reason": "card_type not found in registry",
            "updated": False,
        }

    previous = ct_def["readiness_level"]

    # Auto-detect from result JSON if available
    if adapter_result_path is not None:
        p = _Path(adapter_result_path)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                valid_signal_count = max(
                    valid_signal_count,
                    data.get("signal_count", 0),
                )
                public_card_count = max(
                    public_card_count,
                    data.get("public_card_count", 0),
                )
            except (json.JSONDecodeError, OSError):
                pass

    # ── Readiness determination ─────────────────────────────────────────────
    if force_missing:
        new_level = "missing"
        reason = "forced to missing"
    elif valid_signal_count >= 3 and public_card_count >= 3:
        new_level = "partial"
        reason = (
            f"v112b local snapshot adapter produced {valid_signal_count} valid signals "
            f"and {public_card_count} clean public cards; "
            f"live data source still missing"
        )
    else:
        new_level = "missing"
        reason = (
            f"adapter signals ({valid_signal_count}) or public cards ({public_card_count}) "
            f"below minimum threshold (3 each)"
        )

    # ── Update registry in-place ────────────────────────────────────────────
    ct_def["readiness_level"] = new_level
    ct_def["readiness_detail"]["real_data_pipeline_available"] = False  # Fixture only
    ct_def["readiness_detail"]["gate_integration_tested"] = (
        new_level == "partial"
    )
    if new_level == "partial":
        # Update monitoring gaps to reflect current state
        ct_def["readiness_detail"]["long_running_monitoring_gaps"] = [
            "缺少实时清算数据源（当前仅 fixture，需接入交易所 liquidation feed 或免费聚合 API）",
            "缺少清算价位热力图数据（liquidation heatmap）",
            "缺少历史清算事件对比基线",
            "缺少多资产并发清算压力监测（当前按单资产处理）",
            "gate 集成测试完成（v112c pipeline dry-run），但未接入真实发送流程",
        ]

    return {
        "card_type": "liquidation_pressure",
        "previous_readiness": previous,
        "new_readiness": new_level,
        "reason": reason,
        "valid_signal_count": valid_signal_count,
        "public_card_count": public_card_count,
        "updated": previous != new_level,
    }


# ── Dynamic Readiness Update (v1.12-D) ─────────────────────────────────────────────

def update_news_event_readiness_from_adapter(
    adapter_result_path: str | None = None,
    valid_signal_count: int = 0,
    public_card_count: int = 0,
    debug_leak_count: int = 0,
    force_missing: bool = False,
) -> dict:
    """Update news_event_market_impact readiness based on v112d adapter state.

    This function dynamically updates the readiness_level for
    news_event_market_impact in the registry based on whether the v112d
    local news event adapter has produced valid output.

    Readiness logic:
      - If force_missing or no adapter exists → readiness = "missing"
      - If >= 3 valid signals + >= 3 clean public cards + 0 debug leaks → "partial"
      - Only live data source + long-term monitoring → "ready" (future)
      - Conditions: no_network, no_external_ai, no_real_tg_send all true
      - Fixture must not be live_ready=true

    Args:
        adapter_result_path: Optional path to v112d result JSON for auto-detection.
        valid_signal_count: Number of valid news event signals from adapter.
        public_card_count: Number of clean public cards from adapter.
        debug_leak_count: Number of debug leaks found in public cards.
        force_missing: Force readiness back to "missing".

    Returns:
        Dict with readiness_update details.
    """
    import json
    from pathlib import Path as _Path

    ct_def = CARD_TYPE_REGISTRY.get("news_event_market_impact")
    if ct_def is None:
        return {
            "card_type": "news_event_market_impact",
            "previous_readiness": "unknown",
            "new_readiness": "unknown",
            "reason": "card_type not found in registry",
            "updated": False,
        }

    previous = ct_def["readiness_level"]

    # Auto-detect from result JSON if available
    if adapter_result_path is not None:
        p = _Path(adapter_result_path)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                valid_signal_count = max(
                    valid_signal_count,
                    data.get("valid_signal_count", 0),
                )
                public_card_count = max(
                    public_card_count,
                    data.get("public_card_count", 0),
                )
                debug_leak_count = max(
                    debug_leak_count,
                    data.get("debug_leak_count", 0),
                )
            except (json.JSONDecodeError, OSError):
                pass

    # ── Readiness determination ─────────────────────────────────────────────
    if force_missing:
        new_level = "missing"
        reason = "forced to missing"
    elif valid_signal_count >= 3 and public_card_count >= 3 and debug_leak_count == 0:
        new_level = "partial"
        reason = (
            f"v112d local feed adapter produced {valid_signal_count} valid signals "
            f"and {public_card_count} clean public cards (0 debug leaks); "
            f"live data pipeline still missing"
        )
    elif debug_leak_count > 0:
        new_level = "missing"
        reason = (
            f"{debug_leak_count} debug leak(s) found in public cards; "
            f"must fix leaks before readiness can advance"
        )
    else:
        new_level = "missing"
        reason = (
            f"adapter signals ({valid_signal_count}) or public cards ({public_card_count}) "
            f"below minimum threshold (3 signals + 3 cards with 0 leaks)"
        )

    # ── Update registry in-place ────────────────────────────────────────────
    ct_def["readiness_level"] = new_level
    ct_def["readiness_detail"]["real_data_pipeline_available"] = False  # Fixture only
    ct_def["readiness_detail"]["gate_integration_tested"] = (
        new_level == "partial"
    )
    if new_level == "partial":
        ct_def["readiness_detail"]["long_running_monitoring_gaps"] = [
            "缺少实时新闻 RSS/API 接入管道（当前仅 fixture，需接入 CoinDesk / The Block / 官方博客等）",
            "缺少事件自动分类（当前基于规则关键词，需 NLP 提升准确率）",
            "缺少 Affected Assets 自动提取（当前基于名称映射 + ticker 匹配，需实体识别增强）",
            "缺少已定价判断模型（事件发生 vs 市场价格反应的时间差分析）",
            "缺少事件去重/合并（同一事件多来源重复推送）",
            "缺少交易相关性自动评估（事件对价格的实际影响量化）",
            "gate 集成测试完成（v112d local feed dry-run），但未接入真实发送流程",
        ]

    return {
        "card_type": "news_event_market_impact",
        "previous_readiness": previous,
        "new_readiness": new_level,
        "reason": reason,
        "valid_signal_count": valid_signal_count,
        "public_card_count": public_card_count,
        "debug_leak_count": debug_leak_count,
        "updated": previous != new_level,
    }


def get_fixed_card_matrix_summary() -> dict:
    """Get a summary of the fixed card type matrix with current readiness.

    Returns a dict with ready_count, partial_count, missing_count,
    and a list of card_type entries with their readiness levels.
    """
    card_types = []
    ready_count = 0
    partial_count = 0
    missing_count = 0

    for ct_name in sorted(CARD_TYPE_REGISTRY.keys()):
        ct = CARD_TYPE_REGISTRY[ct_name]
        level = ct.get("readiness_level", "missing")
        card_types.append({
            "card_type": ct_name,
            "display_name": ct.get("display_name", ct_name),
            "readiness_level": level,
        })
        if level == "ready":
            ready_count += 1
        elif level == "partial":
            partial_count += 1
        else:
            missing_count += 1

    return {
        "ready_count": ready_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "card_types": card_types,
    }


# ── Debug Leak Check ──────────────────────────────────────────────────────────────

def check_public_debug_leak(text: str, card_type_def: dict) -> list[str]:
    """Check public card text for forbidden debug/gate/internal terms.

    Args:
        text: The public card text to check.
        card_type_def: Card type definition containing public_forbidden_terms.

    Returns:
        List of forbidden terms found in the text.
    """
    forbidden = card_type_def.get("public_forbidden_terms", [])
    found: list[str] = []
    text_lower = text.lower()
    for term in forbidden:
        if term.lower() in text_lower:
            found.append(term)
    return found


# ── Private: Rule Evaluation ──────────────────────────────────────────────────────

def _evaluate_admission_rules(signal: dict, card_type_def: dict) -> tuple[dict, bool]:
    """Evaluate all admission rules against a signal.

    This is a rule-description-based evaluator. Since we can't safely eval()
    arbitrary expressions, we evaluate against the rule descriptions using
    field presence and value checks. For deterministic behavior, we use a
    mapping of known rule_id patterns to evaluation logic.

    Returns (result_dict, all_passed).
    """
    rules = card_type_def.get("admission_rules", [])
    result: dict[str, bool] = {}
    all_passed = True

    for rule in rules:
        rule_id = rule.get("rule_id", "")
        severity = rule.get("severity", "required")
        passed = _eval_rule(signal, card_type_def, rule_id)
        result[rule_id] = passed
        if severity == "required" and not passed:
            all_passed = False

    return result, all_passed


def _evaluate_block_rules(signal: dict, card_type_def: dict) -> tuple[dict, bool, str | None]:
    """Evaluate all block rules against a signal.

    Returns (result_dict, any_blocked, first_block_reason).
    """
    rules = card_type_def.get("block_rules", [])
    result: dict[str, bool] = {}
    blocked = False
    reason: str | None = None

    for rule in rules:
        rule_id = rule.get("rule_id", "")
        triggered = _eval_block_rule(signal, card_type_def, rule_id)
        result[rule_id] = triggered
        if triggered and not blocked:
            blocked = True
            reason = rule.get("description", f"Blocked by {rule_id}")

    return result, blocked, reason


def _eval_rule(signal: dict, card_type_def: dict, rule_id: str) -> bool:
    """Evaluate a single admission rule by rule_id.

    Uses explicit logic for each known rule pattern for deterministic,
    safe evaluation without eval().
    """
    asset = str(signal.get("asset") or signal.get("core_entity") or "")
    pc = _safe_float(signal.get("price_change_pct"))
    oi = _safe_float(
        signal.get("open_interest") or signal.get("oi") or signal.get("oi_usd")
    )
    vol = _safe_float(
        signal.get("volume") or signal.get("dayNtlVlm") or signal.get("volume_24h")
    )
    funding = _safe_float(signal.get("funding") or signal.get("funding_rate"))
    pos_val = _safe_float(signal.get("position_value_usd") or signal.get("value_usd"))
    side = str(signal.get("side", "")).strip().lower()
    address = signal.get("address")
    liq_level = signal.get("liquidation_level")
    liq_cluster = signal.get("liq_cluster_price")
    long_liq = _safe_float(signal.get("long_liq_total"))
    short_liq = _safe_float(signal.get("short_liq_total"))
    liq_cluster_size = _safe_float(signal.get("liq_cluster_size"))
    event_title = signal.get("event_title")
    affected_assets = signal.get("affected_assets")
    event_type = str(signal.get("event_type", "")).strip()
    trading_relevance = str(signal.get("trading_relevance", "")).strip()

    # Multi-asset sync
    assets_list = signal.get("assets", [])
    if isinstance(assets_list, list):
        real_count = sum(
            1 for a in assets_list
            if isinstance(a, dict) and not (
                a.get("is_fixture") in (True, "true", "True") or
                str(a.get("source_type", "")).lower() == "fixture"
            )
        )
    else:
        real_count = signal.get("real_same_direction_asset_count", 0)
        if not isinstance(real_count, (int, float)):
            real_count = 1  # self

    direction = str(signal.get("direction", "")).strip().lower()

    # ── Admission rule evaluations ──────────────────────────────────────

    # price_oi_volume_anomaly rules
    if rule_id == "adm_pova_001_price_threshold":
        return abs(pc) >= 5.0
    if rule_id == "adm_pova_002_confirm_factor":
        has_oi = oi > 1e-10
        has_vol = vol > 1e-10
        has_funding_extreme = abs(funding) >= 0.01
        multi_sync = real_count >= 3
        return has_oi or has_vol or has_funding_extreme or multi_sync
    if rule_id == "adm_pova_003_asset_required":
        return len(asset) > 0

    # whale_position_alert rules
    if rule_id == "adm_whale_001_value_threshold":
        return pos_val >= 100_000
    if rule_id == "adm_whale_002_has_direction":
        return side in ("long", "short", "多头", "空头")
    if rule_id == "adm_whale_003_address_present":
        return address is not None and len(str(address)) > 0
    if rule_id == "adm_whale_004_significant_pnl":
        pnl = _safe_float(signal.get("pnl_usd") or signal.get("pnl"))
        pnl_pct = _safe_float(signal.get("pnl_pct"))
        return abs(pnl_pct) >= 10 or abs(pnl) >= 10_000

    # liquidation_pressure rules
    if rule_id == "adm_liq_001_has_level":
        return liq_level is not None or liq_cluster is not None
    if rule_id == "adm_liq_002_significant_size":
        return long_liq >= 1_000_000 or short_liq >= 1_000_000 or liq_cluster_size >= 500_000
    if rule_id == "adm_liq_003_asset_required":
        return len(asset) > 0

    # multi_asset_market_sync rules
    if rule_id == "adm_sync_001_min_assets":
        return real_count >= 3
    if rule_id == "adm_sync_002_has_direction":
        return direction in ("up", "down")
    if rule_id == "adm_sync_003_backing":
        oi_match = signal.get("oi_direction_match", False)
        vol_surge = _safe_float(signal.get("volume_surge_ratio", 0))
        return oi_match is True or vol_surge >= 1.5

    # news_event_market_impact rules
    if rule_id == "adm_news_001_has_title":
        return event_title is not None and len(str(event_title)) > 0
    if rule_id == "adm_news_002_has_assets":
        return affected_assets is not None and len(str(affected_assets)) > 0
    if rule_id == "adm_news_003_has_type":
        valid_types = ["监管", "政策", "技术", "安全", "交易", "上线", "合作", "宏观", "交易所", "事故", "ETF", "其他"]
        return event_type in valid_types
    if rule_id == "adm_news_004_relevance":
        return trading_relevance not in ("无", "极低", "none", "")

    # Unknown rule → pass (conservative)
    return True


def _eval_block_rule(signal: dict, card_type_def: dict, rule_id: str) -> bool:
    """Evaluate a single block rule by rule_id. Returns True if the rule
    is triggered (i.e., the signal should be blocked).
    """
    asset = str(signal.get("asset") or signal.get("core_entity") or "")
    pc = _safe_float(signal.get("price_change_pct"))
    oi = _safe_float(
        signal.get("open_interest") or signal.get("oi") or signal.get("oi_usd")
    )
    vol = _safe_float(
        signal.get("volume") or signal.get("dayNtlVlm") or signal.get("volume_24h")
    )
    funding = _safe_float(signal.get("funding") or signal.get("funding_rate"))
    pos_val = _safe_float(signal.get("position_value_usd") or signal.get("value_usd"))
    address = signal.get("address")
    side = str(signal.get("side", "")).strip().lower()
    liq_level = signal.get("liquidation_level")
    liq_cluster = signal.get("liq_cluster_price")
    long_liq = _safe_float(signal.get("long_liq_total"))
    short_liq = _safe_float(signal.get("short_liq_total"))
    event_title = signal.get("event_title")
    affected_assets = signal.get("affected_assets")
    trading_relevance = str(signal.get("trading_relevance", "")).strip()
    already_priced = str(signal.get("already_priced", "")).strip()

    is_fixture = (
        signal.get("is_fixture") in (True, "true", "True") or
        str(signal.get("source_type", "")).lower() == "fixture"
    )
    data_mode = str(signal.get("data_mode", "")).strip()

    # Multi-asset
    assets_list = signal.get("assets", [])
    if isinstance(assets_list, list):
        real_count = sum(
            1 for a in assets_list
            if isinstance(a, dict) and not (
                a.get("is_fixture") in (True, "true", "True") or
                str(a.get("source_type", "")).lower() == "fixture"
            )
        )
    else:
        real_count = signal.get("real_same_direction_asset_count", 0)
        if not isinstance(real_count, (int, float)):
            real_count = 1
    direction = str(signal.get("direction", "")).strip().lower()

    oi_missing = "open_interest" not in signal and "oi" not in signal and "oi_usd" not in signal
    vol_missing = "volume" not in signal and "dayNtlVlm" not in signal and "volume_24h" not in signal
    funding_missing = "funding" not in signal and "funding_rate" not in signal

    # ── Block rule evaluations ─────────────────────────────────────────

    # price_oi_volume_anomaly block rules
    if rule_id == "blk_pova_001_missing_asset":
        return len(asset) == 0
    if rule_id == "blk_pova_002_missing_price":
        return "price_change_pct" not in signal or signal.get("price_change_pct") is None
    if rule_id == "blk_pova_003_insignificant_price":
        return abs(pc) < 3.0
    if rule_id == "blk_pova_004_no_confirm_at_all":
        return oi_missing and vol_missing and funding_missing and real_count < 3
    if rule_id == "blk_pova_005_fixture_as_live":
        return is_fixture and data_mode != "fixture"

    # whale_position_alert block rules
    if rule_id == "blk_whale_001_below_threshold":
        return pos_val < 50_000
    if rule_id == "blk_whale_002_missing_address":
        return address is None
    if rule_id == "blk_whale_003_missing_direction":
        return side not in ("long", "short", "多头", "空头")
    if rule_id == "blk_whale_004_dust_position":
        return pos_val < 1_000
    if rule_id == "blk_whale_005_fixture_as_live":
        return is_fixture and data_mode != "fixture"

    # liquidation_pressure block rules
    if rule_id == "blk_liq_001_no_level_data":
        return liq_level is None and liq_cluster is None
    if rule_id == "blk_liq_002_trivial_size":
        return (long_liq + short_liq) < 100_000
    if rule_id == "blk_liq_003_fixture_as_live":
        return is_fixture and data_mode != "fixture"

    # multi_asset_market_sync block rules
    if rule_id == "blk_sync_001_insufficient_assets":
        return real_count < 3
    if rule_id == "blk_sync_002_all_fixture":
        return real_count == 0
    if rule_id == "blk_sync_003_no_direction":
        return direction == "neutral"
    if rule_id == "blk_sync_004_fixture_as_live":
        return is_fixture and data_mode != "fixture"

    # news_event_market_impact block rules
    if rule_id == "blk_news_001_no_title":
        return event_title is None or len(str(event_title)) == 0
    if rule_id == "blk_news_002_no_assets":
        return affected_assets is None or len(str(affected_assets)) == 0
    if rule_id == "blk_news_003_already_fully_priced":
        return already_priced in ("已定价", "fully priced")
    if rule_id == "blk_news_004_no_relevance":
        return trading_relevance in ("无", "极低", "none")
    if rule_id == "blk_news_005_fixture_as_live":
        return is_fixture and data_mode != "fixture"

    # Unknown rule → not triggered (conservative)
    return False


# ── Private: Public Card Renderers ─────────────────────────────────────────────────

def _render_pova_public(signal: dict, card_type_def: dict) -> str:
    """Render public card for price_oi_volume_anomaly."""
    asset = str(signal.get("asset") or signal.get("core_entity") or "Unknown")
    pc = _safe_float(signal.get("price_change_pct"))
    oi = _safe_float(
        signal.get("open_interest") or signal.get("oi") or signal.get("oi_usd")
    )
    vol = _safe_float(
        signal.get("volume") or signal.get("dayNtlVlm") or signal.get("volume_24h")
    )
    funding = _safe_float(signal.get("funding") or signal.get("funding_rate"))
    trigger_reason = str(signal.get("trigger_reason") or "")

    direction_icon = "📈" if pc > 0 else "📉" if pc < 0 else "➡️"
    change_desc = (
        "急涨" if pc > 8 else "上涨" if pc > 2
        else "急跌" if pc < -8 else "下跌" if pc < -2 else "平稳"
    )

    lines = [f"{direction_icon} 行情异动｜{asset} {change_desc}", ""]

    # 一句话
    if trigger_reason:
        lines.append(f"一句话：{trigger_reason}")
    else:
        pc_str = f"{pc:+.2f}%"
        lines.append(
            f"一句话：{asset} 24h {'涨' if pc>0 else '跌'}幅 {pc_str}，"
            f"多因子异动信号 — 检测到价格与{'OI' if oi>0 else ''}{'/' if oi>0 and vol>0 else ''}{'成交量' if vol>0 else ''}同步变化。"
        )
    lines.append("")

    lines.append(f"● 币种：{asset}")
    lines.append(f"● 涨跌幅：{pc:+.2f}%")

    if oi > 0:
        lines.append(f"● OI：{_fmt_money(oi)}")
    if vol > 0:
        lines.append(f"● 成交量：{_fmt_money(vol)}")
    if abs(funding) > 1e-10:
        funding_annual = funding * 3 * 365 * 100
        lines.append(f"● Funding：{funding*100:+.2f}%（年化 {funding_annual:+.1f}%）")

    lines.append(f"● 观察窗口：1-4 小时")
    lines.append("")

    # 公开行情链接
    lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query={asset}) / [DexScreener](https://dexscreener.com/search?q={asset})")
    lines.append("")

    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 仅供观察，不构成交易建议。")
    return "\n".join(lines)


def _render_whale_public(signal: dict, card_type_def: dict) -> str:
    """Render public card for whale_position_alert."""
    asset = str(signal.get("asset") or signal.get("core_entity") or "Unknown")
    side_raw = str(signal.get("side") or "")
    side = "多头" if "long" in side_raw.lower() else "空头" if "short" in side_raw.lower() else side_raw or "未知"
    pos_val = _safe_float(signal.get("position_value_usd") or signal.get("value_usd"))
    qty = _safe_float(signal.get("quantity") or signal.get("size"))
    entry = _safe_float(signal.get("entry_price") or signal.get("entry"))
    mark = _safe_float(signal.get("mark_price") or signal.get("mark") or signal.get("current_price"))
    pnl = _safe_float(signal.get("pnl_usd") or signal.get("pnl"))
    pnl_pct = _safe_float(signal.get("pnl_pct"))
    liq = _safe_float(signal.get("liquidation_price") or signal.get("liquidation"))
    address = str(signal.get("address") or "")
    trigger_reason = str(signal.get("trigger_reason") or "")
    label = str(signal.get("label") or "")

    # 计算清算距离
    liq_distance = 0.0
    if liq > 0 and mark > 0:
        if "多" in side:
            liq_distance = (mark - liq) / mark * 100
        elif "空" in side:
            liq_distance = (liq - mark) / mark * 100
        liq_distance = max(liq_distance, 0)

    pnl_desc = "大浮盈" if pnl_pct > 50 else "浮盈" if pnl > 0 else "浮亏" if pnl < 0 else ""
    title_emoji = "🚀" if pnl > 0 else "📉" if pnl < 0 else "📊"

    # mask address
    masked = _mask_addr(address)

    lines = [f"{title_emoji} 主力仓位雷达｜{asset} {side} {pnl_desc}".strip(), ""]

    if trigger_reason:
        lines.append(f"一句话：{trigger_reason}")
    else:
        lines.append(f"一句话：{asset} {side} 持仓 {_fmt_money(pos_val)}，{'浮盈' if pnl>0 else '浮亏' if pnl<0 else '开仓中'}。")
    lines.append("")

    lines.append(f"● 持仓规模：{_fmt_money(pos_val)}")
    if qty > 0:
        lines.append(f"● 持仓数量：{qty:,.2f} {asset}")
    if entry > 0:
        lines.append(f"● 均价：${_fmt_price(entry)}")
    if mark > 0:
        lines.append(f"● 当前价格：${_fmt_price(mark)}")

    pnl_sign = "+" if pnl >= 0 else ""
    if abs(pnl) > 1e-10:
        lines.append(f"● 当前盈亏：{pnl_sign}{_fmt_money(pnl)}（{pnl_sign}{pnl_pct:.1f}%）")

    if liq > 0:
        lines.append(f"● 清算价：${_fmt_price(liq)}（距清算 {liq_distance:.1f}%）")

    if label:
        lines.append(f"🏷️ 标签：{label}")

    if address:
        lines.append(f"📌 地址：`{masked}`")

    lines.append("")
    lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query={asset}) / [DexScreener](https://dexscreener.com/search?q={asset})")
    lines.append("")

    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 仅供观察，不构成交易建议。")
    return "\n".join(lines)


def _render_liquidation_public(signal: dict, card_type_def: dict) -> str:
    """Render public card for liquidation_pressure."""
    asset = str(signal.get("asset") or signal.get("core_entity") or "Unknown")
    liq_level = signal.get("liquidation_level")
    liq_cluster = signal.get("liq_cluster_price")
    long_liq = _safe_float(signal.get("long_liq_total"))
    short_liq = _safe_float(signal.get("short_liq_total"))
    liq_cluster_size = _safe_float(signal.get("liq_cluster_size"))
    leverage_zone = str(signal.get("leverage_zone") or "")
    direction = str(signal.get("crowded_direction") or signal.get("direction") or "")
    risk_level = str(signal.get("risk_level") or "medium")
    estimated_cascade = _safe_float(signal.get("estimated_cascade"))
    trigger_reason = str(signal.get("trigger_reason") or "")

    risk_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(risk_level, "🔻")

    dir_desc = "多头" if "long" in direction.lower() else "空头" if "short" in direction.lower() else ""
    lines = [f"{risk_icon} 清算压力预警｜{asset} {dir_desc}拥挤".strip(), ""]

    if trigger_reason:
        lines.append(f"一句话：{trigger_reason}")
    else:
        level_str = str(liq_level or liq_cluster or "N/A")
        size_str = _fmt_money(liq_cluster_size or (long_liq + short_liq))
        lines.append(f"一句话：{asset} 在 {level_str} 附近存在 {size_str} 待清算仓位，{dir_desc if dir_desc else '杠杆'}拥挤。")
    lines.append("")

    if liq_level:
        lines.append(f"● 关键清算价：${_fmt_price(_safe_float(liq_level))}")
    if liq_cluster:
        lines.append(f"● 清算密集区：${_fmt_price(_safe_float(liq_cluster))}")
    if long_liq > 0:
        lines.append(f"● 多头待清算：{_fmt_money(long_liq)}")
    if short_liq > 0:
        lines.append(f"● 空头待清算：{_fmt_money(short_liq)}")
    if leverage_zone:
        lines.append(f"● 杠杆集中区间：{leverage_zone}")
    lines.append(f"● 风险等级：{risk_level.upper()}")

    if estimated_cascade > 0:
        lines.append(f"⚠️ 如触发连锁清算，预估影响规模 {_fmt_money(estimated_cascade)}")

    lines.append("")
    lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query={asset}) / [DexScreener](https://dexscreener.com/search?q={asset})")
    lines.append("")

    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 清算数据具有时效性，仅供观察，不构成交易建议。")
    return "\n".join(lines)


def _render_sync_public(signal: dict, card_type_def: dict) -> str:
    """Render public card for multi_asset_market_sync."""
    assets_list = signal.get("assets", [])
    direction = str(signal.get("direction") or "").strip().lower()
    sector = str(signal.get("sector") or "")
    leader = str(signal.get("leader_asset") or "")
    avg_pc = _safe_float(signal.get("avg_price_change"))
    max_pc = _safe_float(signal.get("max_price_change"))
    oi_match = signal.get("oi_direction_match", False)
    vol_surge = _safe_float(signal.get("volume_surge_ratio", 0))
    trigger_reason = str(signal.get("trigger_reason") or "")

    dir_icon = "📈" if direction == "up" else "📉" if direction == "down" else "➡️"
    dir_desc = "普涨" if direction == "up" else "普跌" if direction == "down" else "震荡"

    asset_names = []
    if isinstance(assets_list, list):
        for a in assets_list:
            if isinstance(a, dict):
                asset_names.append(str(a.get("asset", "")))
            elif isinstance(a, str):
                asset_names.append(a)
    elif isinstance(assets_list, str):
        asset_names = [s.strip() for s in assets_list.split(",") if s.strip()]

    n = len(asset_names) if asset_names else int(signal.get("real_same_direction_asset_count", 0))
    if n < 1:
        n = 3  # fallback

    sector_str = f"· {sector}" if sector else ""
    lines = [f"{dir_icon} 多资产共振｜{dir_desc} {n}个资产 {sector_str}".strip(), ""]

    if trigger_reason:
        lines.append(f"一句话：{trigger_reason}")
    else:
        avg_str = f"{avg_pc:+.2f}%" if abs(avg_pc) > 1e-10 else ""
        lines.append(f"一句话：检测到 {n} 个资产同步{dir_desc}，{'板块: ' + sector if sector else ''}，平均涨跌幅 {avg_str}。")
    lines.append("")

    if leader:
        lines.append(f"● 领涨/领跌：{leader}")
    if asset_names:
        display_assets = asset_names[:5]
        lines.append(f"● 共振资产：{', '.join(display_assets)}" + (f"（共 {len(asset_names)} 个）" if len(asset_names) > 5 else ""))
    if abs(max_pc) > 1e-10:
        lines.append(f"● 最大涨跌幅：{max_pc:+.2f}%")
    if abs(avg_pc) > 1e-10:
        lines.append(f"● 平均涨跌幅：{avg_pc:+.2f}%")

    lines.append(f"● 共振支撑：OI {'一致' if oi_match else '待确认'} / 成交量 {'放大' if vol_surge >= 1.5 else '待确认'}")
    lines.append("")

    # 行情链接（首个资产）
    first_asset = asset_names[0] if asset_names else ""
    if first_asset:
        lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query={first_asset}) / [DexScreener](https://dexscreener.com/search?q={first_asset})")
        lines.append("")

    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。")
    return "\n".join(lines)


def _render_news_public(signal: dict, card_type_def: dict) -> str:
    """Render public card for news_event_market_impact."""
    event_title = str(signal.get("event_title") or "未命名事件")
    affected_assets = str(signal.get("affected_assets") or "待确认")
    event_type = str(signal.get("event_type") or "其他")
    trading_relevance = str(signal.get("trading_relevance") or "待评估")
    already_priced = str(signal.get("already_priced") or "未知")
    risk_tags = str(signal.get("risk_tags") or "")
    observation_window = str(signal.get("observation_window") or "2-4 小时")
    source_name = str(signal.get("source_name") or signal.get("source") or "公开信息")
    summary = str(signal.get("summary") or "")
    trigger_reason = str(signal.get("trigger_reason") or "")

    type_icons = {
        "监管": "🏛️", "政策": "📜", "技术": "🔧", "安全": "🔒",
        "交易": "💹", "上线": "🆕", "合作": "🤝", "宏观": "🌍",
        "交易所": "🏦", "事故": "🚨", "ETF": "📊", "其他": "📰",
    }
    icon = type_icons.get(event_type, "📰")

    lines = [f"{icon} 新闻事件｜{event_title}", ""]

    if trigger_reason:
        lines.append(f"一句话：{trigger_reason}")
    else:
        lines.append(f"一句话：{event_type}类型事件，影响 {affected_assets}，交易相关性 {trading_relevance}。")
    lines.append("")

    lines.append(f"● 影响币种：{affected_assets}")
    lines.append(f"● 事件类型：{event_type}")
    lines.append(f"● 交易相关性：{trading_relevance}")

    if summary and summary != "--":
        lines.append(f"● 摘要：{summary[:200]}")

    lines.append(f"● 是否已提前反应：{already_priced}")

    if risk_tags and risk_tags != "--":
        lines.append(f"● 风险标签：{risk_tags}")

    lines.append(f"● 观察窗口：{observation_window}")
    lines.append(f"● 来源：{source_name}")
    lines.append("")

    primary_asset = affected_assets.split(",")[0].strip() if affected_assets else ""
    if primary_asset and primary_asset != "待确认":
        lines.append(f"🔗 行情查看：[CoinGecko](https://www.coingecko.com/search?query={primary_asset}) / [DexScreener](https://dexscreener.com/search?q={primary_asset})")
        lines.append("")

    if trigger_reason:
        lines.append(f"💡 触发原因：{trigger_reason}")
        lines.append("")

    lines.append("⚠️ 新闻事件可能已被市场定价，请独立判断，不构成交易建议。")
    return "\n".join(lines)


def _render_fallback_public(signal: dict, card_type_def: dict) -> str:
    """Fallback public card renderer."""
    card_type = card_type_def.get("card_type", "unknown")
    asset = str(signal.get("asset") or signal.get("core_entity") or "Unknown")
    lines = [
        f"📋 {card_type_def.get('display_name', card_type)}",
        "",
        f"● 资产：{asset}",
        f"● 卡片类型：{card_type}",
        "",
        "⚠️ 此卡片类型的公开渲染器尚未完全实现，仅供观察，不构成交易建议。",
    ]
    return "\n".join(lines)


# ── Private: Utility Functions ─────────────────────────────────────────────────────

def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    import math
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "").replace(",", "").replace("+", "").strip()
        if not s:
            return default
        try:
            return float(s)
        except (ValueError, TypeError):
            return default
    return default


def _fmt_money(value):
    """Format a value as human-readable USD."""
    import math
    v = abs(value)
    sign = "-" if value < 0 else ""
    if v >= 1_000_000_000:
        return f"{sign}${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{sign}${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"{sign}${v/1_000:.2f}K"
    if v < 0.01 and v > 0:
        return f"{sign}${v:.6f}"
    return f"{sign}${v:,.2f}"


def _fmt_price(value):
    """Format a USD price."""
    v = abs(value)
    if v >= 1000:
        return f"{value:,.2f}"
    if v >= 1:
        return f"{value:.2f}"
    return f"{value:.6f}"


def _mask_addr(addr):
    """Mask an address: 0x1234...abcd."""
    if not addr or str(addr).strip() == "":
        return "--"
    s = str(addr).strip()
    if len(s) <= 10:
        return s
    return f"{s[:6]}...{s[-4:]}"

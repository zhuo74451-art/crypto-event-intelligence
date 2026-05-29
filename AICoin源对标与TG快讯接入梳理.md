# AICoin 源对标与 TG 快讯接入梳理

生成时间：2026-05-25  
范围：基于 AICoin 公开频道可见样本、用户截图样本、服务器 `/opt/x-monitor/current` 配置与最近数据库统计。

## 结论摘要

我们现在不是 TG 发送慢，核心差距在三块：

1. **缺少 AiCoin 自有型信号源**：价格突破、热搜榜、主力资金、巨鲸跟踪，这些是最适合返佣转化的高频交易内容。
2. **缺少若干外部快源直连**：Onchain Lens、KOL Yusufi、BBX 等；目前有些只能通过 Odaily/中间源偶尔进入，速度和覆盖都不稳定。
3. **部分已有源需要提速**：Cointelegraph、Odaily 快讯、Polymarket 当前更多跟随 `news-watcher` 轮询，实际体验可能是 5-10 分钟级；竞品截图里的体验更像 1 分钟内。

当前 TG 发布器本身已经独立运行，且只发到 `币界网官方群`；它不会影响现有后端发布链路。

## AICoin 可见源类型对标表

| AICoin 内容/信源 | 样例 | 我们现在是否有 | 当前入口 | 当前速度/状态 | 问题 | 建议优先级 | 建议动作 |
|---|---|---:|---|---|---|---:|---|
| AiCoin 自有行情突破 | `BTC 突破 112000 美元关口`、`ETH 突破 4000 美元关口` | 没有 | 无 | 无 | 这是最强交易转化内容，我们缺核心行情触发器 | P0 | 接交易所 ticker/websocket，做 BTC/ETH/SOL/BNB 等阈值突破、5m 涨跌幅、成交量异动 |
| AiCoin 热搜榜/主力资金 | `热搜榜：COAI 热度减弱`、`主力资金净流入/流出` | 没有 | 无 | 无 | 属于 AiCoin 自有/数据产品能力，适合频道高频留存 | P0 | 先用可替代数据源：交易量榜、涨跌幅榜、Coinglass/交易所成交额、内部热榜 |
| AiCoin 巨鲸跟踪 | `100% 胜率巨鲸加仓 BTC/ETH 多单` | 部分有 | `tg:HyperInsight` | 60s 轮询 | 有 HyperInsight 巨鲸，但没有 AiCoin 那套“100%胜率巨鲸”追踪口径 | P0 | 扩展 Hyperliquid/链上仓位源，建立重点地址白名单和仓位模板 |
| Onchain Lens | `据 Onchain Lens 监测，Loracle 新开 3 倍 VW 空单` | 部分间接有 | 通过 Odaily/历史内容偶尔出现；未直连 | 不稳定 | 截图里的 Loracle 新消息没入库，说明直连缺失或覆盖不足 | P0 | 新增 Onchain Lens 直连源；若是 TG/X 源，接频道或账号；优先抓巨鲸、CEX 转账、Hyperliquid 仓位 |
| KOL Yusufi | `据加密 KOL Yusufi 监测，StaBIR 稳定币合约遭攻击` | 没有 | 无 | 无 | 安全事件类高价值快讯没抓到 | P0 | 找到 Yusufi 的 X/TG/API 入口，加入实时监听；关键词：攻击、损失、冻结、漏洞、被盗 |
| Cointelegraph | `据 Cointelegraph 报道，Kalshi...` | 有 | `news:cointelegraph` RSS | 配置 300s；实际随 watcher 轮询约 600s | 有源，但可能慢；还可能被 Hermes block 或等待处理 | P1 | 对 Cointelegraph 开独立 fast watcher，60s；重要关键词直通：ETF、SEC、CFTC、Kalshi、Polymarket、黑客、安全 |
| BBX | `BBX 消息，上市公司加密配置...` | 没有 | 无 | 无 | 机构配置/融资类内容缺失 | P1 | 新增 BBX 源；若无开放 RSS，先抓公开网页/TG/X |
| OKX 行情 | `OKX-BTC/USDT 现报...5分钟涨幅...` | 交易所公告有，行情没有 | `okx_ann` 只抓公告 | 公告 180s；行情无 | AICoin 用的是行情数据，不是公告 | P0 | 接 OKX ticker/websocket，生成突破、急涨急跌、成交额异动 |
| 币安行情 | `币安-SOL/USDT 现报...` | 交易所公告有，行情没有 | `binance_ann` 只抓公告 | 公告 180s；行情无 | 同上，缺行情流 | P0 | 接 Binance ticker/websocket，和 OKX 做主行情源 |
| Mt.Gox/官方事件 | `Mt.Gox 偿付推迟` | 部分可能有 | 新闻 RSS / webhook | 不稳定 | 是否抓到取决于新闻源覆盖 | P2 | 可通过 Cointelegraph/CoinDesk/Odaily 覆盖，不必单独优先 |
| Polymarket | 预测市场相关、Kalshi/Polymarket 调查 | 有 | `news:polymarket` API | 600s | 有 Polymarket 市场源，但新闻事件仍靠 RSS/Odaily | P1 | Polymarket API 提速到 60-120s；新闻侧保留 Cointelegraph/Odaily |
| Odaily 快讯 / exchange gap | Kalshi 这类在我们库中来自 `odaily_exchange_gap` | 有 | `news:odaily_exchange_gap` RSS | 配置 300s，但 news watcher 实际约 600s | 抓到了 Kalshi，但比截图慢 6-7 分钟；且当前 TG 规则过滤 `exchange_announcement` | P1 | 单独快轮询 30-60s；不要一刀切按 content_type 过滤，改成只过滤普通交易所公告 |
| 金十 | 宏观、利率、地缘、原油 | 有 | `news:jin10` + `jin10-watcher` | 120s | 有，但噪音较多；TG 筛选需要继续收紧 | P2 | 保留宏观交易相关：美联储、利率、美元、原油、黄金；过滤泛政治军事 |
| HyperInsight | Hyperliquid 巨鲸/仓位 | 有 | `tg:HyperInsight` | 60s | 交易相关强，但不覆盖 Onchain Lens 全部内容 | P0 | 保留并加权；新增更多同类链上/TG/X 源 |
| OneMillion_AI | AI 新闻 | 有 | `tg:OneMillion_AI` | 120s | 当前业务目标不需要 | 暂停 TG | TG 已过滤 AI；后端项目不动 |

## 我们已有源与状态

| 源 | 配置状态 | 轮询/处理 | 最近 48h 数据量 | 已发布 | 问题 |
|---|---:|---:|---:|---:|---|
| `news:jin10` | 已启用 | 120s 实时 watcher | 396 | 199 | 量大，宏观有用，但噪音多 |
| `tg:HyperInsight` | 已启用 | 60s | 67 | 58 | 交易价值高，保留 |
| `news:odaily_exchange_gap` | 已启用 | 配置 300s，实际 news watcher 约 600s | 21 | 11 | 抓得到但慢；当前 TG 过滤交易所公告会误伤它 |
| `news:cointelegraph` | 已启用 | 配置 300s，实际约 600s | 17 | 2 | 有源但慢，且 Hermes/质量门可能挡 |
| `news:coindesk` | 已启用 | 300-600s | 10 | 6 | 有价值，速度一般 |
| `news:polymarket` | 已启用 | 600s | 2 | 1 | 可提速 |
| `webhook`/X | 已有入口 | 取决于外部推送 | 182 | 25 | 需要明确账号清单和可靠性 |
| 交易所公告 | 已启用 | 180-600s | 少量 | 部分 | 当前 TG 先过滤；后续建议细分 |
| `tg:OneMillion_AI` | 已启用 | 120s | 11 | 7 | TG 已过滤 AI，不影响后端 |

## 缺失源清单

| 缺失源/能力 | 价值 | 推荐接入方式 | 优先级 |
|---|---|---|---:|
| 行情突破/急涨急跌 | 最适合交易返佣转化，频率高，用户感知强 | Binance/OKX websocket ticker；阈值规则生成快讯 | P0 |
| 热搜榜/成交热度/主力资金 | 提供“现在市场在炒什么”的频道粘性 | 先用交易量、涨跌幅、成交额、资金流替代；后续接第三方数据 | P0 |
| Onchain Lens | 巨鲸、CEX 转账、链上仓位，和截图直接相关 | 找 TG/X/API 入口并实时监听 | P0 |
| KOL Yusufi | 安全事件/合约攻击，截图直接相关 | 接 X/TG；关键词触发 | P0 |
| BBX | 机构配置、融资、上市公司加密储备 | 接官网/TG/X/RSS | P1 |
| Coinglass | 爆仓、资金费率、持仓量 | API 或页面抓取；优先爆仓/资金费率 | P0 |
| Lookonchain/Whale Alert/Arkham 类 | 大额转账、巨鲸行为 | TG/X/API | P1 |

## 需要提速的已有源

| 源 | 当前问题 | 建议目标 | 备注 |
|---|---|---:|---|
| `odaily_exchange_gap` | Kalshi 案例抓到但慢 6-7 分钟 | 30-60s | 从通用 `news-watcher` 拆出独立快轮询 |
| `cointelegraph` | 配置 300s，但实际随轮询约 600s | 60s | 只对标题关键词命中的文章走快通道 |
| `polymarket` | 600s | 60-120s | 对高成交/异动市场提速 |
| `jin10` | 120s 已较快 | 维持 120s | 重点是过滤，不是提速 |
| `HyperInsight` | 60s 已较快 | 维持 60s | 可增加类似频道覆盖 |

## TG 发布策略建议

当前“交易所公告全部过滤”会误伤 Odaily 的链上/市场数据，因为它现在被入库为 `exchange_announcement`。建议改成更细：

| 类型 | TG 处理 |
|---|---|
| 普通交易所公告：上币、维护、活动、规则更新 | 过滤 |
| 行情数据：BTC/ETH/SOL 突破、急涨急跌 | 放行 |
| 链上数据：巨鲸、CEX 转账、清算、仓位 | 放行 |
| 预测市场/监管：Kalshi、Polymarket、CFTC、SEC | 放行 |
| AI 内容 | 过滤 |
| 泛政治/军事 | 默认过滤，除非影响油价、美元、黄金、利率、加密监管 |

## 建议实施顺序

1. **P0：做行情触发器**
   - Binance/OKX websocket。
   - 规则：突破整数关口、5m 涨跌幅、成交额突增、BTC/ETH/SOL/BNB 优先。

2. **P0：接 Onchain Lens / Yusufi**
   - 先找到公开入口。
   - 重点抓：攻击、被盗、冻结、巨鲸、新开仓、平仓、清算、CEX 转账。

3. **P1：Odaily/Cointelegraph 快通道**
   - 独立 watcher，不走 10 分钟总轮询。
   - 命中关键词就优先处理。

4. **P1：TG 过滤从 content_type 改成语义规则**
   - 不再因为 `exchange_announcement` 一刀切过滤。
   - 按“普通公告 vs 行情/链上/预测市场”分流。

5. **P2：补 BBX/Lookonchain/Coinglass**
   - 扩大源覆盖，提高频道内容密度。

## 一句话判断

AiCoin 频道的强项不是传统新闻 RSS，而是“行情数据 + 巨鲸/链上 + 快速外部信源 + 返佣入口”的组合。我们已有新闻和部分巨鲸源，但缺行情触发器和若干快源直连；Odaily/Cointelegraph 等已有源也需要从 5-10 分钟级提到 1 分钟级。

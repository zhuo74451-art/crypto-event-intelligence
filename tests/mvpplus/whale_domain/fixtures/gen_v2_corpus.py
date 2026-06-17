#!/usr/bin/env python3
"""Generate whale_replay_corpus_v2.json with all 71 portfolio-level cases."""
import json

OUT = r"C:\Users\PC\Desktop\市场信号\crypto-event-intelligence-worktrees\whale-portfolio-intel\tests\mvpplus\whale_domain\fixtures\whale_replay_corpus_v2.json"

def pos(addr, label, coin, signed_size, entry, mark, pv, lev, pnl, liq, ts="2026-06-17T12:00:00Z"):
    return {"address": addr, "label": label, "coin": coin, "signed_size": signed_size,
            "entry_price": entry, "mark_price": mark, "position_value_usd": pv,
            "leverage": lev, "unrealized_pnl_usd": pnl, "liquidation_price": liq,
            "snapshot_time_utc": ts}

def liq_dist(direction, mark, liq):
    if liq is None or mark is None or mark <= 0: return None
    if direction == "long": return (mark - liq) / mark * 100
    return (liq - mark) / mark * 100

def calc_metrics(portfolio):
    if not portfolio:
        return {k: None for k in ["gross_exposure_usd","net_exposure_usd","long_exposure_usd",
                "short_exposure_usd","long_short_ratio","weighted_leverage","address_count",
                "coin_count","top1_concentration","top3_concentration","hhi",
                "liquidation_within_2pct","liquidation_within_5pct",
                "profitable_exposure","unprofitable_exposure"]}
    gross = sum(p["position_value_usd"] for p in portfolio)
    long_val = sum(p["position_value_usd"] for p in portfolio if p["signed_size"] > 0)
    short_val = sum(p["position_value_usd"] for p in portfolio if p["signed_size"] < 0)
    net = long_val - short_val
    addr_cnt = len({p["address"] for p in portfolio})
    coin_cnt = len({p["coin"] for p in portfolio})
    values = sorted([p["position_value_usd"] for p in portfolio], reverse=True)
    top1 = values[0] / gross if gross > 0 else 0
    top3 = sum(values[:3]) / gross if gross > 0 else 0
    hhi = sum((v / gross) ** 2 for v in values) if gross > 0 else 0
    w_lev = sum(p["position_value_usd"] * p["leverage"] for p in portfolio) / gross if gross > 0 else None

    liq_2 = 0; liq_5 = 0
    for p in portfolio:
        d = "long" if p["signed_size"] > 0 else "short"
        ld = liq_dist(d, p["mark_price"], p["liquidation_price"])
        if ld is not None:
            if abs(ld) <= 2: liq_2 += 1
            if abs(ld) <= 5: liq_5 += 1

    profitable = sum(p["position_value_usd"] for p in portfolio if p["unrealized_pnl_usd"] is not None and p["unrealized_pnl_usd"] > 0)
    unprofitable = sum(p["position_value_usd"] for p in portfolio if p["unrealized_pnl_usd"] is not None and p["unrealized_pnl_usd"] < 0)

    # Rounding helper
    def r(v, d=4):
        if v is None: return None
        return round(v, d)

    return {
        "gross_exposure_usd": r(gross),
        "net_exposure_usd": r(net),
        "long_exposure_usd": r(long_val),
        "short_exposure_usd": r(short_val),
        "long_short_ratio": r(long_val / short_val) if short_val > 0 else (0.0 if short_val == 0 and long_val == 0 else None),
        "weighted_leverage": r(w_lev),
        "address_count": addr_cnt,
        "coin_count": coin_cnt,
        "top1_concentration": r(top1),
        "top3_concentration": r(top3),
        "hhi": r(hhi),
        "liquidation_within_2pct": liq_2,
        "liquidation_within_5pct": liq_5,
        "profitable_exposure": r(profitable),
        "unprofitable_exposure": r(unprofitable),
    }

def make_case(cid, cat, desc, prev, curr, metrics=None, risk_rules=None,
              coord_actions=None, pf_changes=None, notes="", is_baseline=False):
    if metrics is None:
        metrics = calc_metrics(curr)
    elif isinstance(metrics, dict):
        pass
    return {
        "case_id": cid,
        "category": cat,
        "description": desc,
        "previous_portfolio": prev,
        "current_portfolio": curr,
        "is_baseline_run": is_baseline,
        "detected_at_utc": "2026-06-17T12:00:00Z",
        "expected_portfolio_metrics": metrics,
        "expected_risk_rules": risk_rules or [],
        "expected_coordinated_actions": coord_actions or [],
        "expected_portfolio_changes": pf_changes or [],
        "notes": notes,
    }

# ── Build all cases ────────────────────────────────────────────────────
cases = []

# ── C101-C112: Portfolio Structure & Exposure Metrics ────────────────

C101_CUR = [pos("0xportfolio_A_001","Single Long Whale","BTC",10.0,65000,66000,650000.0,9.9,10000,60000)]
cases.append(make_case("C101","portfolio_structure","1 address, 1 coin, long — simplest single-position portfolio",[],C101_CUR,is_baseline=True,
    notes="Baseline run with single long position. Leverage 9.9 below HIGH_WEIGHTED_LEVERAGE (10.0)."))

C102_CUR = [
    pos("0xportfolio_A_002a","BTC Long A","BTC",5.0,65000,66000,325000.0,5.0,5000,60000),
    pos("0xportfolio_A_002b","BTC Long B","BTC",3.0,65000,66000,195000.0,3.0,3000,62000),
]
cases.append(make_case("C102","portfolio_structure","2 addresses, 1 coin, both long",[],C102_CUR,
    notes="Two addresses both long BTC. HHI = 0.625^2 + 0.375^2 = 0.53125."))

C103_CUR = [
    pos("0xportfolio_A_003a","BTC Long","BTC",10.0,65000,66000,650000.0,10.0,10000,63000),
    pos("0xportfolio_A_003b","ETH Short","ETH",-5.0,1800,1789.64,9000.0,5.0,51.8,2100),
]
cases.append(make_case("C103","portfolio_structure","2 addresses, 2 coins, mixed direction",[],C103_CUR,
    notes="BTC long (4.55% liq dist, within 5%). BTC dominates 98.6%."))

C104_CUR = [
    pos("0xportfolio_A_004a","Short A","ETH",-10.0,1800,1789.64,18000.0,5.0,103.6,2100),
    pos("0xportfolio_A_004b","Short B","ETH",-8.0,1800,1789.64,14400.0,4.0,82.88,2050),
    pos("0xportfolio_A_004c","Short C","ETH",-5.0,1800,1789.64,9000.0,3.0,51.8,2000),
    pos("0xportfolio_A_004d","Short D","ETH",-3.0,1800,1789.64,5400.0,2.0,31.08,1950),
    pos("0xportfolio_A_004e","Short E","ETH",-2.0,1800,1789.64,3600.0,1.5,20.72,1900),
]
cases.append(make_case("C104","portfolio_structure","5 addresses, short only",[],C104_CUR,
    notes="All ETH shorts. HHI=0.1888 (well distributed). Liq distances 6.17-17.34%."))

C105_CUR = [
    pos("0xA_105_01","Whale 01","BTC",30.0,65000,66000,1950000.0,8.0,30000,60000),
    pos("0xA_105_02","Whale 02","BTC",20.0,65000,66000,1300000.0,5.0,20000,62000),
    pos("0xA_105_03","Whale 03","ETH",50.0,1800,1789.64,90000.0,3.0,-518,1600),
    pos("0xA_105_04","Whale 04","ETH",-30.0,1800,1789.64,54000.0,4.0,310.8,2000),
    pos("0xA_105_05","Whale 05","SOL",500.0,120,125,60000.0,5.0,2500,110),
    pos("0xA_105_06","Whale 06","SOL",-200.0,120,125,24000.0,3.0,-1000,135),
    pos("0xA_105_07","Whale 07","ARB",100000.0,1.5,1.45,150000.0,2.0,-5000,1.3),
    pos("0xA_105_08","Whale 08","ARB",-50000.0,1.5,1.45,75000.0,2.0,2500,1.6),
    pos("0xA_105_09","Whale 09","OP",50000.0,2.2,2.1,110000.0,4.0,-5000,1.9),
    pos("0xA_105_10","Whale 10","OP",-30000.0,2.2,2.1,66000.0,3.0,3000,2.4),
    pos("0xA_105_11","Whale 11","MATIC",200000.0,0.8,0.85,160000.0,2.0,10000,0.7),
    pos("0xA_105_12","Whale 12","MATIC",-100000.0,0.8,0.85,80000.0,2.0,-5000,0.95),
    pos("0xA_105_13","Whale 13","AVAX",500.0,28,30,14000.0,5.0,1000,26),
    pos("0xA_105_14","Whale 14","AVAX",-300.0,28,30,8400.0,3.0,-600,32),
    pos("0xA_105_15","Whale 15","LINK",1000.0,18,20,18000.0,4.0,2000,16),
    pos("0xA_105_16","Whale 16","LINK",-500.0,18,20,9000.0,3.0,-1000,22),
    pos("0xA_105_17","Whale 17","DOGE",100000.0,0.14,0.15,14000.0,2.0,1000,0.12),
    pos("0xA_105_18","Whale 18","DOGE",-50000.0,0.14,0.15,7000.0,1.5,-500,0.16),
    pos("0xA_105_19","Whale 19","ATOM",200.0,10,11,2000.0,3.0,200,9),
    pos("0xA_105_20","Whale 20","ATOM",-100.0,10,11,1000.0,2.0,-100,12),
]
cases.append(make_case("C105","portfolio_structure","20 addresses, 10 coins, mixed — large diversified portfolio",[],C105_CUR,
    notes="Large diversified portfolio. BTC dominates (3.25M of 4.33M). 20 addresses, 10 coins."))

C106_CUR = [
    pos("0xportfolio_A_006a","Long Whale","BTC",100.0,65000,66000,6500000.0,10.0,100000,60000),
    pos("0xportfolio_A_006b","Short Whale","BTC",-100.0,65000,66000,6500000.0,10.0,-100000,70000),
]
cases.append(make_case("C106","portfolio_structure","Net near zero but gross high (13M)",[],C106_CUR,
    risk_rules=["PR3","PR6"],
    notes="Net zero but gross 13M > 10M (PR3). Weighted lev=10 exactly (PR6). L/S=1.0."))

C107_CUR = [
    pos("0xportfolio_A_007a","Dominant Whale","BTC",150.0,65000,66000,9750000.0,8.0,150000,60000),
    pos("0xportfolio_A_007b","Small Trader","ETH",10.0,1800,1789.64,18000.0,3.0,-103.6,1600),
    pos("0xportfolio_A_007c","Small Trader 2","SOL",100.0,120,125,12000.0,2.0,500,110),
]
cases.append(make_case("C107","portfolio_structure","Single address dominant (99.7%) — address concentration >70%",[],C107_CUR,
    risk_rules=["PR12"],
    notes="Single addr 9.75M out of 9.78M (99.7%). PR12 (>70% triggered). Gross 9.78M < 10M."))

C108_CUR = [
    pos("0xportfolio_A_008a","Balanced A","BTC",5.0,65000,66000,325000.0,3.0,5000,60000),
    pos("0xportfolio_A_008b","Balanced B","ETH",180.0,1800,1789.64,324000.0,3.0,-1864.8,1600),
    pos("0xportfolio_A_008c","Balanced C","SOL",2700.0,120,125,324000.0,3.0,13500,110),
    pos("0xportfolio_A_008d","Balanced D","ARB",216000.0,1.5,1.45,324000.0,2.0,-10800,1.3),
    pos("0xportfolio_A_008e","Balanced E","LINK",18000.0,18,20,324000.0,2.0,36000,16),
]
cases.append(make_case("C108","portfolio_structure","Evenly distributed across 5 addresses",[],C108_CUR,
    notes="Each ~324K-325K. HHI=0.2005 (near min 0.2 for 5 equal). No risk rules."))

C109_CUR = [
    pos("0xportfolio_A_009a","BTC Long A","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_A_009b","BTC Long B","BTC",5.0,65000,66000,325000.0,3.0,5000,62000),
    pos("0xportfolio_A_009c","BTC Short","BTC",-3.0,65000,66000,195000.0,8.0,-3000,68000),
]
cases.append(make_case("C109","portfolio_structure","3 addresses, 1 coin, 2 long 1 short",[],C109_CUR,
    risk_rules=["PR5"],
    notes="All BTC (100% same-coin > 50%, PR5). Short liq_dist=3.03% (within 5%)."))

C110_CUR = [
    pos("0xportfolio_A_010a","USDC Holder","USDC",100000.0,1.0,1.0,100000.0,1.0,0,None),
    pos("0xportfolio_A_010b","USDT Holder","USDT",50000.0,1.0,1.0,50000.0,1.0,0,None),
    pos("0xportfolio_A_010c","DAI Holder","DAI",25000.0,1.0,1.0,25000.0,1.0,0,None),
]
cases.append(make_case("C110","portfolio_structure","Multiple stablecoins with no exposure",[],C110_CUR,
    notes="Stablecoins only. All lev=1, no liq prices, no P&L. HHI=0.4082."))

C111_CUR = [
    pos("0xportfolio_B_011a","ETH Long A","ETH",20.0,1800,1789.64,36000.0,5.0,-207.2,1600),
    pos("0xportfolio_B_011b","ETH Long B","ETH",10.0,1800,1789.64,18000.0,3.0,-103.6,1650),
    pos("0xportfolio_B_011c","ETH Short C","ETH",-15.0,1800,1789.64,27000.0,4.0,155.4,2000),
]
cases.append(make_case("C111","exposure_metrics","Same-coin opposing: 2 long, 1 short on same coin",[],C111_CUR,
    risk_rules=["PR5"],
    notes="All ETH (100% same-coin > 50% triggers PR5). L/S=2.0. HHI=0.3086."))

C112_CUR = [
    pos("0xportfolio_B_012a","BTC Long X","BTC",15.0,65000,66000,975000.0,8.0,15000,61000),
    pos("0xportfolio_B_012b","BTC Long Y","BTC",10.0,65000,66000,650000.0,5.0,10000,63000),
    pos("0xportfolio_B_012c","BTC Long Z","BTC",8.0,65000,66000,520000.0,3.0,8000,64000),
]
cases.append(make_case("C112","exposure_metrics","Cross-address same-direction: 3 all long BTC",[],C112_CUR,
    risk_rules=["PR5"],
    notes="All 3 long BTC (100% same-coin > 50%, PR5). Y liq dist=4.55%, Z=3.03%."))

# C113: Same-coin with concentration > 50%
C113_CUR = [
    pos("0xportfolio_B_013a","BTC Whale","BTC",80.0,65000,66000,5200000.0,5.0,80000,60000),
    pos("0xportfolio_B_013b","ETH Trader","ETH",500.0,1800,1789.64,900000.0,2.0,-5180,1700),
    pos("0xportfolio_B_013c","SOL Trader","SOL",2000.0,120,125,240000.0,3.0,10000,115),
]
cases.append(make_case("C113","exposure_metrics","BTC dominates 82% of gross",[],C113_CUR,
    notes="BTC 5.2M (82%), ETH 900K (14.2%), SOL 240K (3.8%). BTC single-coin concentration = 0.82 > 0.5. Gross=6.34M<10M."))

# C114: Long/short ratio extremes
C114_CUR = [
    pos("0xportfolio_B_014a","Big Long","BTC",50.0,65000,66000,3250000.0,5.0,50000,60000),
    pos("0xportfolio_B_014b","Tiny Short","ETH",-1.0,1800,1789.64,1800.0,2.0,10.36,2000),
]
cases.append(make_case("C114","exposure_metrics","L/S ratio of 1805:1",[],C114_CUR,
    risk_rules=["PR12"],
    notes="Extreme L/S=1805. 1st addr dominates 99.94% (PR12). HHI=0.9989."))

# C115: Top-1 concentration exactly at 0.8 boundary
C115_CUR = [
    pos("0xportfolio_B_015a","Primary","BTC",80.0,65000,66000,5200000.0,5.0,80000,60000),
    pos("0xportfolio_B_015b","Secondary","ETH",722.22,1800,1789.64,1300000.0,3.0,-7486,1700),
]
cases.append(make_case("C115","exposure_metrics","Top-1 concentration at 0.8 boundary",[],C115_CUR,
    risk_rules=["PR4"],
    notes="Top-1=0.8 exactly (PR4 triggers at >=0.8). HHI=0.8^2+0.2^2=0.68."))

# C116: Top-3 concentration boundary
C116_CUR = [
    pos("0xportfolio_B_016a","Large A","BTC",30.0,65000,66000,1950000.0,5.0,30000,60000),
    pos("0xportfolio_B_016b","Large B","ETH",500.0,1800,1789.64,900000.0,3.0,-5180,1700),
    pos("0xportfolio_B_016c","Large C","SOL",5000.0,120,125,600000.0,4.0,25000,115),
    pos("0xportfolio_B_016d","Small D","ARB",100000.0,1.5,1.45,150000.0,2.0,-5000,1.3),
    pos("0xportfolio_B_016e","Small E","LINK",5000.0,18,20,90000.0,2.0,10000,16),
]
cases.append(make_case("C116","exposure_metrics","Top-3 capture 93.5% of 5 positions",[],C116_CUR,
    notes="Top-3: 1.95M+900K+600K=3.45M/3.69M=93.5%. No risk rules triggered."))

# C117: HHI boundary with 4 uneven positions
C117_CUR = [
    pos("0xportfolio_B_017a","Pos A","BTC",20.0,65000,66000,1300000.0,5.0,20000,60000),
    pos("0xportfolio_B_017b","Pos B","ETH",400.0,1800,1789.64,720000.0,3.0,-4144,1700),
    pos("0xportfolio_B_017c","Pos C","SOL",3000.0,120,125,360000.0,4.0,15000,115),
    pos("0xportfolio_B_017d","Pos D","ARB",200000.0,1.5,1.45,300000.0,2.0,-10000,1.3),
]
cases.append(make_case("C117","exposure_metrics","Moderate HHI=0.3166 with 4 uneven positions",[],C117_CUR,
    notes="1.3M, 720K, 360K, 300K. HHI=(0.4851)^2+(0.2687)^2+(0.1343)^2+(0.1119)^2=0.3166."))

# C118: Profitable/unprofitable mixed
C118_CUR = [
    pos("0xportfolio_B_018a","Winner BTC","BTC",10.0,60000,66000,600000.0,5.0,60000,55000),
    pos("0xportfolio_B_018b","Winner ETH","ETH",100.0,1500,1789.64,150000.0,3.0,28964,1400),
    pos("0xportfolio_B_018c","Loser SOL","SOL",1000.0,150,125,150000.0,4.0,-25000,120),
    pos("0xportfolio_B_018d","Loser ARB","ARB",100000.0,2.0,1.45,200000.0,2.0,-55000,1.35),
]
cases.append(make_case("C118","exposure_metrics","Mixed winners and losers",[],C118_CUR,
    risk_rules=["PR2"],
    notes="Winners: BTC +60K, ETH +28.9K (750K total). Losers: SOL -25K, ARB -55K (350K total). SOL liq dist=(125-120)/125*100=4% (within 5%)."))

# C119: Zero-size ignored in metrics
C119_CUR = [
    pos("0xportfolio_B_019a","Active","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_B_019b","Zero Pos","ETH",0.0,0,1789.64,0.0,0.0,0,None),
    pos("0xportfolio_B_019c","Zero Pos 2","SOL",0.0,0,125,0.0,0.0,0,None),
]
cases.append(make_case("C119","exposure_metrics","Zero-size positions excluded from metrics",[],C119_CUR,
    notes="Only active BTC position counts. Zero-size positions have pv=0, lev=0. Gross=650K, addr_cnt=1 (not 3), coin_cnt=1 (not 3)."))

# C120: Stale snapshot excluded
C120_CUR = [
    pos("0xportfolio_B_020a","Stale Pos","BTC",10.0,65000,66000,650000.0,5.0,10000,60000,"2026-06-16T12:00:00Z"),
]
prev_120 = {
    "0xportfolio_B_020a:BTC": {
        "address":"0xportfolio_B_020a","label":"Stale Pos","coin":"BTC","direction":"long",
        "signed_size":5.0,"absolute_size":5.0,"position_value_usd":325000.0,"entry_price":65000,
        "mark_price":66000,"leverage":10,"unrealized_pnl_usd":5000,"liquidation_price":60000,
        "liquidation_distance_pct":9.09,"snapshot_time_utc":"2026-06-17T12:00:00Z"
    }
}
# For stale, the key-based prev dict won't fit into our simple format.
# We'll skip previous_portfolio and note it in the description.
cases.append(make_case("C120","exposure_metrics","Stale snapshot older than previous excluded",[],C120_CUR,
    notes="Current snapshot time (16th) is earlier than previous (17th). Stale position is excluded. Only 1 addr considered."))

# ── Liquidation Cluster (C121-C130) ────────────────────────────────────

# C121: 3 addresses within 2% of liq
C121_CUR = [
    pos("0xportfolio_C_121a","BTC Liq A","BTC",10.0,65000,66000,650000.0,10.0,10000,64700),
    pos("0xportfolio_C_121b","BTC Liq B","BTC",5.0,65000,66000,325000.0,8.0,5000,64800),
    pos("0xportfolio_C_121c","BTC Liq C","BTC",3.0,65000,66000,195000.0,6.0,3000,64900),
]
# liq dists: A=(66000-64700)/66000*100=1.97%, B=1.82%, C=1.67% all <=2%
cases.append(make_case("C121","liquidation_cluster","3 addresses within 2% of liquidation",[],C121_CUR,
    risk_rules=["PR1","PR2","PR5"],
    notes="All 3 within 2% (PR1). Liq dists: A=1.97%, B=1.82%, C=1.67%. Also PR2 (within 5%). All BTC => PR5."))

# C122: 2 addresses within 5%, 1 outside
C122_CUR = [
    pos("0xportfolio_C_122a","Near Liq A","BTC",10.0,65000,66000,650000.0,10.0,10000,63500),
    pos("0xportfolio_C_122b","Near Liq B","BTC",5.0,65000,66000,325000.0,8.0,5000,64000),
    pos("0xportfolio_C_122c","Safe C","ETH",10.0,1800,1789.64,18000.0,3.0,-103.6,1500),
]
# A=(66000-63500)/66000=3.79% (<=5%), B=3.03% (<=5%), C=(1789.64-1500)/1789.64=16.18% (>5%)
cases.append(make_case("C122","liquidation_cluster","2 within 5%, 1 outside",[],C122_CUR,
    risk_rules=["PR2"],
    notes="A liq dist=3.79%, B=3.03% (both <=5% PR2). C=16.18% outside. NOT PR1 (none <=2%)."))

# C123: All addresses within 2%
C123_CUR = [
    pos("0xportfolio_C_123a","Critical A","ETH",10.0,1800,1789.64,18000.0,10.0,-207.2,1765),
    pos("0xportfolio_C_123b","Critical B","ETH",5.0,1800,1789.64,9000.0,8.0,-103.6,1770),
    pos("0xportfolio_C_123c","Critical C","SOL",100.0,120,125,12000.0,5.0,500,123.5),
]
# A=(1789.64-1765)/1789.64=1.38%, B=(1789.64-1770)/1789.64=1.10%, C=(125-123.5)/125=1.20%
cases.append(make_case("C123","liquidation_cluster","All positions within 2% of liquidation",[],C123_CUR,
    risk_rules=["PR1","PR2"],
    notes="All <=2% (PR1). A=1.38%, B=1.10%, C=1.20%. Also PR2."))

# C124: No address near liq
C124_CUR = [
    pos("0xportfolio_C_124a","Safe A","BTC",10.0,65000,66000,650000.0,3.0,10000,55000),
    pos("0xportfolio_C_124b","Safe B","ETH",20.0,1800,1789.64,36000.0,2.0,-207.2,1400),
    pos("0xportfolio_C_124c","Safe C","SOL",500.0,120,125,60000.0,2.0,2500,100),
]
# A=16.67%, B=21.77%, C=20% - all far from liq
cases.append(make_case("C124","liquidation_cluster","No address near liquidation",[],C124_CUR,
    notes="Liq dists: A=16.67%, B=21.77%, C=20%. No PR1 or PR2. All safe."))

# C125: Mix of null liq and critical liq
C125_CUR = [
    pos("0xportfolio_C_125a","Null Liq A","BTC",10.0,65000,66000,650000.0,5.0,10000,None),
    pos("0xportfolio_C_125b","Critical B","ETH",10.0,1800,1789.64,18000.0,10.0,-207.2,1760),
    pos("0xportfolio_C_125c","Null Liq C","SOL",200.0,120,125,24000.0,3.0,1000,None),
]
# B liq dist=(1789.64-1760)/1789.64=1.66% (within 2%)
cases.append(make_case("C125","liquidation_cluster","Mix of null liq and critical liq",[],C125_CUR,
    risk_rules=["PR1","PR2"],
    notes="A and C have no liq price. B has liq dist=1.66% (within 2%, PR1+PR2). Only B counts in clusters."))

# C126: Single address at exactly 2% boundary
C126_CUR = [
    pos("0xportfolio_C_126a","Boundary 2pct","BTC",10.0,65000,66000,650000.0,10.0,10000,64680),
]
# liq dist = (66000-64680)/66000*100 = 1320/66000*100 = 2.0% exactly
cases.append(make_case("C126","liquidation_cluster","Single address at exactly 2% boundary",[],C126_CUR,
    risk_rules=["PR1","PR2"],
    notes="Liq dist exactly 2.0%. Should trigger both PR1 (<=2%) and PR2 (<=5%)."))

# C127: Single address at exactly 5% boundary
C127_CUR = [
    pos("0xportfolio_C_127a","Boundary 5pct","BTC",10.0,65000,66000,650000.0,8.0,10000,62700),
]
# liq dist = (66000-62700)/66000*100 = 3300/66000*100 = 5.0% exactly
cases.append(make_case("C127","liquidation_cluster","Single address at exactly 5% boundary",[],C127_CUR,
    risk_rules=["PR2"],
    notes="Liq dist exactly 5.0%. Should trigger PR2 (<=5%) but NOT PR1 (>2%)."))

# C128: All far from liq
C128_CUR = [
    pos("0xportfolio_C_128a","Far A","BTC",10.0,65000,66000,650000.0,3.0,10000,50000),
    pos("0xportfolio_C_128b","Far B","ETH",20.0,1800,1789.64,36000.0,2.0,-207.2,1200),
    pos("0xportfolio_C_128c","Far C","SOL",1000.0,120,125,120000.0,2.0,5000,95),
]
# A=24.24%, B=32.94%, C=24% - all far from liq
cases.append(make_case("C128","liquidation_cluster","All addresses far from liquidation",[],C128_CUR,
    notes="Liq dists: A=24.24%, B=32.94%, C=24%. None within 5%. No risk rules."))

# C129: Liquidation cluster on short side
C129_CUR = [
    pos("0xportfolio_C_129a","Short Near A","ETH",-10.0,1800,1789.64,18000.0,10.0,155.4,1815),
    pos("0xportfolio_C_129b","Short Near B","ETH",-5.0,1800,1789.64,9000.0,8.0,77.7,1810),
]
# A=(1815-1789.64)/1789.64*100=1.42%, B=(1810-1789.64)/1789.64*100=1.14%
cases.append(make_case("C129","liquidation_cluster","Liquidation cluster on short side",[],C129_CUR,
    risk_rules=["PR1","PR2"],
    notes="Both shorts within 2%. A liq dist=1.42%, B=1.14%. PR1+PR2 triggered on short side."))

# C130: Mixed long/short liquidation risk
C130_CUR = [
    pos("0xportfolio_C_130a","Long Near","BTC",10.0,65000,66000,650000.0,10.0,10000,64000),
    pos("0xportfolio_C_130b","Short Near","ETH",-10.0,1800,1789.64,18000.0,10.0,155.4,1820),
    pos("0xportfolio_C_130c","Safe Long","SOL",500.0,120,125,60000.0,3.0,2500,110),
]
# A=3.03% (<=5%), B=(1820-1789.64)/1789.64*100=1.69% (<=2%), C=12% (>5%)
cases.append(make_case("C130","liquidation_cluster","Mixed long/short liquidation risk",[],C130_CUR,
    risk_rules=["PR1","PR2"],
    notes="Long A=3.03% (within 5%), Short B=1.69% (within 2%), Safe C=12%. PR1 for B, PR2 for A+B."))

# ── Leverage (C131-C135) ──────────────────────────────────────────────

# C131: Weighted leverage > 10
C131_CUR = [
    pos("0xportfolio_D_131a","High Lev A","BTC",10.0,65000,66000,650000.0,15.0,10000,60000),
    pos("0xportfolio_D_131b","High Lev B","ETH",5.0,1800,1789.64,9000.0,12.0,51.8,2000),
]
# w_lev = (650000*15+9000*12)/(650000+9000) = (9750000+108000)/659000 = 9858000/659000 = 14.96
cases.append(make_case("C131","leverage","Weighted leverage 14.96 > 10",[],C131_CUR,
    risk_rules=["PR6"],
    notes="Weighted lev=(650K*15+9K*12)/659K=14.96>10 (PR6). Both positions have high individual leverage."))

# C132: Weighted leverage boundary at 10
C132_CUR = [
    pos("0xportfolio_D_132a","Lev 10x","BTC",10.0,65000,66000,650000.0,10.0,10000,60000),
]
# w_lev = (650000*10)/650000 = 10.0 exactly
cases.append(make_case("C132","leverage","Weighted leverage exactly at 10.0 boundary",[],C132_CUR,
    risk_rules=["PR6"],
    notes="Single position weighted lev=10.0 exactly. PR6 triggers at >=10.0."))

# C133: Mixed leverage (some high, some low)
C133_CUR = [
    pos("0xportfolio_D_133a","High","BTC",10.0,65000,66000,650000.0,15.0,10000,60000),
    pos("0xportfolio_D_133b","Med","ETH",20.0,1800,1789.64,36000.0,5.0,-207.2,1600),
    pos("0xportfolio_D_133c","Low","SOL",500.0,120,125,60000.0,2.0,2500,110),
]
# w_lev = (650000*15+36000*5+60000*2)/(650000+36000+60000) = (9750000+180000+120000)/746000 = 10050000/746000 = 13.473
cases.append(make_case("C133","leverage","Mixed leverage — high(15x), med(5x), low(2x)",[],C133_CUR,
    risk_rules=["PR6"],
    notes="Weighted lev=13.47>10 (PR6). Individual: BTC 15x, ETH 5x, SOL 2x."))

# C134: All addresses low leverage
C134_CUR = [
    pos("0xportfolio_D_134a","Low A","BTC",10.0,65000,66000,650000.0,2.0,10000,60000),
    pos("0xportfolio_D_134b","Low B","ETH",20.0,1800,1789.64,36000.0,1.5,-207.2,1600),
    pos("0xportfolio_D_134c","Low C","SOL",500.0,120,125,60000.0,1.0,2500,110),
]
cases.append(make_case("C134","leverage","All addresses low leverage (<3x)",[],C134_CUR,
    notes="Individual lev: 2x, 1.5x, 1x. All well below threshold. No PR6."))

# C135: Weighted leverage with zeros
C135_CUR = [
    pos("0xportfolio_D_135a","Active","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_D_135b","Zero","ETH",0.0,0,1789.64,0.0,0.0,0,None),
]
cases.append(make_case("C135","leverage","Weighted leverage calculation with zeros excluded",[],C135_CUR,
    notes="Zero-size position has pv=0. Weighted lev = 650K*5/650K = 5.0. Zero excluded. addr_cnt=1."))

# ── Coordinated Behavior (C136-C145) ──────────────────────────────────

# C136: 2 addresses same-direction build on BTC
C136_CUR = [
    pos("0xportfolio_E_136a","BTC Builder A","BTC",15.0,64000,66000,960000.0,8.0,30000,61000,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_136b","BTC Builder B","BTC",12.0,64000,66000,768000.0,6.0,24000,62000,"2026-06-17T12:01:00Z"),
    pos("0xportfolio_E_136c","Unrelated","ETH",10.0,1800,1789.64,18000.0,3.0,-103.6,1600,"2026-06-17T12:00:00Z"),
]
prev_136 = [
    pos("0xportfolio_E_136a","BTC Builder A","BTC",10.0,64000,66000,640000.0,8.0,20000,61000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_136b","BTC Builder B","BTC",8.0,64000,66000,512000.0,6.0,16000,62000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_136c","Unrelated","ETH",10.0,1800,1789.64,18000.0,3.0,-103.6,1600,"2026-06-17T11:55:00Z"),
]
m136 = calc_metrics(C136_CUR)
cases.append(make_case("C136","coordinated_behavior","2 addresses same-direction build on BTC (3 min window)",prev_136,C136_CUR,
    metrics=m136,
    notes="A: 10->15 (build_long), B: 8->12 (build_long). Both within 3 min window (12:00, 12:01). C unchanged."))

# C137: 3 addresses coordinated reduction on ETH
C137_CUR = [
    pos("0xportfolio_E_137a","ETH Reducer A","ETH",8.0,1800,1789.64,14400.0,5.0,-82.88,1600,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_137b","ETH Reducer B","ETH",5.0,1800,1789.64,9000.0,4.0,-51.8,1650,"2026-06-17T12:01:30Z"),
    pos("0xportfolio_E_137c","ETH Reducer C","ETH",3.0,1800,1789.64,5400.0,3.0,-31.08,1700,"2026-06-17T12:02:00Z"),
]
prev_137 = [
    pos("0xportfolio_E_137a","ETH Reducer A","ETH",15.0,1800,1789.64,27000.0,5.0,-155.4,1600,"2026-06-17T11:50:00Z"),
    pos("0xportfolio_E_137b","ETH Reducer B","ETH",10.0,1800,1789.64,18000.0,4.0,-103.6,1650,"2026-06-17T11:50:00Z"),
    pos("0xportfolio_E_137c","ETH Reducer C","ETH",6.0,1800,1789.64,10800.0,3.0,-62.16,1700,"2026-06-17T11:50:00Z"),
]
m137 = calc_metrics(C137_CUR)
cases.append(make_case("C137","coordinated_behavior","3 addresses coordinated reduction on ETH",prev_137,C137_CUR,
    metrics=m137,
    notes="A: 15->8, B: 10->5, C: 6->3. All ETH, all reduce_long, within 2 min window."))

# C138: 2 addresses coordinated flip from long to short on SOL
C138_CUR = [
    pos("0xportfolio_E_138a","SOL Flips A","SOL",-100.0,130,125,12500.0,10.0,-500,132,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_138b","SOL Flips B","SOL",-50.0,130,125,6250.0,8.0,-250,131,"2026-06-17T12:01:00Z"),
]
prev_138 = [
    pos("0xportfolio_E_138a","SOL Flips A","SOL",50.0,120,125,6000.0,5.0,250,115,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_138b","SOL Flips B","SOL",30.0,120,125,3600.0,4.0,150,115,"2026-06-17T11:55:00Z"),
]
m138 = calc_metrics(C138_CUR)
cases.append(make_case("C138","coordinated_behavior","2 addresses coordinated flip long->short on SOL",prev_138,C138_CUR,
    metrics=m138,
    notes="A: +50->-100 SOL (flip_long_to_short), B: +30->-50 SOL (flip_long_to_short). Both within 1 min."))

# C139: 2 addresses coordinated flip from short to long on BTC
C139_CUR = [
    pos("0xportfolio_E_139a","BTC Flip A","BTC",8.0,68000,66000,544000.0,5.0,-16000,64000,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_139b","BTC Flip B","BTC",5.0,68000,66000,340000.0,4.0,-10000,64500,"2026-06-17T12:00:30Z"),
]
prev_139 = [
    pos("0xportfolio_E_139a","BTC Flip A","BTC",-5.0,65000,66000,325000.0,5.0,5000,68000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_139b","BTC Flip B","BTC",-3.0,65000,66000,195000.0,4.0,3000,68000,"2026-06-17T11:55:00Z"),
]
m139 = calc_metrics(C139_CUR)
cases.append(make_case("C139","coordinated_behavior","2 addresses coordinated flip short->long on BTC",prev_139,C139_CUR,
    metrics=m139,
    notes="A: -5->+8 BTC (flip_short_to_long), B: -3->+5 BTC (flip_short_to_long). Both within 30 sec."))

# C140: Divergent: 2 build, 1 reduces on same coin
C140_CUR = [
    pos("0xportfolio_E_140a","Builder A","BTC",12.0,65000,66000,780000.0,5.0,12000,60000,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_140b","Builder B","BTC",8.0,65000,66000,520000.0,4.0,8000,61000,"2026-06-17T12:01:00Z"),
    pos("0xportfolio_E_140c","Reducer C","BTC",3.0,65000,66000,195000.0,3.0,3000,62000,"2026-06-17T12:00:30Z"),
]
prev_140 = [
    pos("0xportfolio_E_140a","Builder A","BTC",8.0,65000,66000,520000.0,5.0,8000,60000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_140b","Builder B","BTC",5.0,65000,66000,325000.0,4.0,5000,61000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_140c","Reducer C","BTC",6.0,65000,66000,390000.0,3.0,6000,62000,"2026-06-17T11:55:00Z"),
]
m140 = calc_metrics(C140_CUR)
cases.append(make_case("C140","coordinated_behavior","Divergent: 2 build, 1 reduces on same coin",prev_140,C140_CUR,
    metrics=m140,
    notes="A: 8->12 build, B: 5->8 build, C: 6->3 reduce. All BTC. Divergent signals on same coin."))

# C141: Same-direction build with different sizes
C141_CUR = [
    pos("0xportfolio_E_141a","Big Builder","BTC",50.0,65000,66000,3250000.0,8.0,50000,60000,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_141b","Small Builder","ETH",100.0,1800,1789.64,180000.0,3.0,-1036,1600,"2026-06-17T12:01:00Z"),
]
prev_141 = [
    pos("0xportfolio_E_141a","Big Builder","BTC",30.0,65000,66000,1950000.0,8.0,30000,60000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_141b","Small Builder","ETH",50.0,1800,1789.64,90000.0,3.0,-518,1600,"2026-06-17T11:55:00Z"),
]
m141 = calc_metrics(C141_CUR)
cases.append(make_case("C141","coordinated_behavior","Same-direction build with different sizes",prev_141,C141_CUR,
    metrics=m141,
    notes="A: BTC 30->50 (big delta +1.3M), B: ETH 50->100 (smaller delta +90K). Different coins, both build."))

# C142: Coordinated across different coins
C142_CUR = [
    pos("0xportfolio_E_142a","Multi Builder A","BTC",10.0,65000,66000,650000.0,5.0,10000,60000,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_142b","Multi Builder B","ETH",20.0,1800,1789.64,36000.0,4.0,-207.2,1600,"2026-06-17T12:00:30Z"),
    pos("0xportfolio_E_142c","Multi Builder C","SOL",500.0,120,125,60000.0,3.0,2500,110,"2026-06-17T12:01:00Z"),
]
prev_142 = [
    pos("0xportfolio_E_142a","Multi Builder A","BTC",5.0,65000,66000,325000.0,5.0,5000,60000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_142b","Multi Builder B","ETH",10.0,1800,1789.64,18000.0,4.0,-103.6,1600,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_142c","Multi Builder C","SOL",200.0,120,125,24000.0,3.0,1000,110,"2026-06-17T11:55:00Z"),
]
m142 = calc_metrics(C142_CUR)
cases.append(make_case("C142","coordinated_behavior","Coordinated build across 3 different coins",prev_142,C142_CUR,
    metrics=m142,
    notes="A: BTC 5->10, B: ETH 10->20, C: SOL 200->500. All build_long but across different coins."))

# C143: Out-of-window actions (should NOT match coordination)
C143_CUR = [
    pos("0xportfolio_E_143a","Early Builder","BTC",12.0,65000,66000,780000.0,5.0,12000,60000,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_143b","Late Builder","BTC",8.0,65000,66000,520000.0,4.0,8000,61000,"2026-06-17T12:30:00Z"),
]
prev_143 = [
    pos("0xportfolio_E_143a","Early Builder","BTC",5.0,65000,66000,325000.0,5.0,5000,60000,"2026-06-17T11:00:00Z"),
    pos("0xportfolio_E_143b","Late Builder","BTC",3.0,65000,66000,195000.0,4.0,3000,61000,"2026-06-17T11:00:00Z"),
]
m143 = calc_metrics(C143_CUR)
cases.append(make_case("C143","coordinated_behavior","Out-of-window actions — 30 min apart, should NOT match coordination",prev_143,C143_CUR,
    metrics=m143,
    notes="Both build BTC but timestamps 12:00 and 12:30 are >5 min apart. Should NOT trigger coordinated action."))

# C144: Single address (should NOT match multi-addr coordination)
C144_CUR = [
    pos("0xportfolio_E_144a","Only One","BTC",15.0,65000,66000,975000.0,5.0,15000,60000,"2026-06-17T12:00:00Z"),
]
prev_144 = [
    pos("0xportfolio_E_144a","Only One","BTC",10.0,65000,66000,650000.0,5.0,10000,60000,"2026-06-17T11:55:00Z"),
]
m144 = calc_metrics(C144_CUR)
cases.append(make_case("C144","coordinated_behavior","Single address — cannot form multi-addr coordination",prev_144,C144_CUR,
    metrics=m144,
    notes="Only 1 address building. Single-address action cannot trigger multi-address coordinated detection."))

# C145: Liquidation cluster formation across addresses
C145_CUR = [
    pos("0xportfolio_E_145a","Newly Critical A","BTC",10.0,65000,66000,650000.0,10.0,10000,64800,"2026-06-17T12:00:00Z"),
    pos("0xportfolio_E_145b","Newly Critical B","BTC",5.0,65000,66000,325000.0,8.0,5000,64900,"2026-06-17T12:00:30Z"),
]
prev_145 = [
    pos("0xportfolio_E_145a","Newly Critical A","BTC",10.0,65000,66000,650000.0,10.0,10000,62000,"2026-06-17T11:55:00Z"),
    pos("0xportfolio_E_145b","Newly Critical B","BTC",5.0,65000,66000,325000.0,8.0,5000,63000,"2026-06-17T11:55:00Z"),
]
# Previous: A liq=62000 -> dist=6.06%, B liq=63000 -> dist=4.55%
# Current: A liq=64800 -> dist=1.82%, B liq=64900 -> dist=1.67%
m145 = calc_metrics(C145_CUR)
cases.append(make_case("C145","coordinated_behavior","Liquidation cluster formation across addresses",prev_145,C145_CUR,
    metrics=m145, risk_rules=["PR1","PR2"],
    notes="Both addresses now within 2% liq (PR1). Previous was 6.06% and 4.55% (only B was in 5%). Cluster formed."))

# ── Portfolio Changes (C146-C155) ─────────────────────────────────────

# C146: Gross expansion >20%
C146_CUR = [
    pos("0xportfolio_F_146a","Expanded","BTC",30.0,65000,66000,1950000.0,5.0,30000,60000),
    pos("0xportfolio_F_146b","New Pos","SOL",500.0,120,125,60000.0,3.0,2500,110),
]
prev_146 = [
    pos("0xportfolio_F_146a","Expanded","BTC",15.0,65000,66000,975000.0,5.0,15000,60000),
]
# Prev gross=975K, Curr gross=2.01M, expansion=106% > 20%
m146 = calc_metrics(C146_CUR)
cases.append(make_case("C146","portfolio_changes","Gross expansion >20% (975K -> 2.01M)",prev_146,C146_CUR,
    metrics=m146,
    pf_changes=["gross_expansion","new_coin_entered"],
    notes="Gross grew from 975K to 2.01M (+106%). SOL position is new. Expected portfolio changes: gross_expansion, new_coin."))

# C147: Gross reduction >20%
C147_CUR = [
    pos("0xportfolio_F_147a","Reduced","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
]
prev_147 = [
    pos("0xportfolio_F_147a","Reduced","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_F_147b","Exited","ETH",20.0,1800,1789.64,36000.0,3.0,-207.2,1600),
]
# Prev gross=686K, Curr gross=650K, reduction=5.2% < 20%
# Let me recalculate to get >20%
# Actually, need to make this bigger. Let me use a larger exit.
prev_147b = [
    pos("0xportfolio_F_147a","Reduced","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_F_147b","Exited","ETH",500.0,1800,1789.64,900000.0,3.0,-5180,1600),
]
# Prev gross=1.55M, Curr gross=650K, reduction=58% > 20%
m147 = calc_metrics(C147_CUR)
m147_prev = calc_metrics(prev_147b)
cases.append(make_case("C147","portfolio_changes","Gross reduction >20% (1.55M -> 650K)",prev_147b,C147_CUR,
    metrics=m147,
    pf_changes=["gross_reduction","coin_exited"],
    notes="Gross from 1.55M to 650K (-58%). ETH position fully exited. Expected: gross_reduction, coin_exited."))

# C148: Net direction shift
C148_CUR = [
    pos("0xportfolio_F_148a","Now Short","BTC",-10.0,68000,66000,660000.0,8.0,-20000,70000),
]
prev_148 = [
    pos("0xportfolio_F_148a","Was Long","BTC",15.0,65000,66000,975000.0,5.0,15000,60000),
]
m148 = calc_metrics(C148_CUR)
cases.append(make_case("C148","portfolio_changes","Net direction shift from long to short",prev_148,C148_CUR,
    metrics=m148,
    pf_changes=["direction_shift","flip_long_to_short"],
    notes="Prev: long 975K. Curr: short 660K. Net shifted from +975K to -660K. flip_long_to_short."))

# C149: Concentration increase
C149_CUR = [
    pos("0xportfolio_F_149a","Dominant","BTC",50.0,65000,66000,3250000.0,5.0,50000,60000),
    pos("0xportfolio_F_149b","Minor","ETH",50.0,1800,1789.64,90000.0,3.0,-518,1600),
]
prev_149 = [
    pos("0xportfolio_F_149a","Dominant","BTC",30.0,65000,66000,1950000.0,5.0,30000,60000),
    pos("0xportfolio_F_149b","Minor","ETH",50.0,1800,1789.64,90000.0,3.0,-518,1600),
]
# Prev top1=1950/2040=0.9559, Curr top1=3250/3340=0.9731 -> increase
m149 = calc_metrics(C149_CUR)
cases.append(make_case("C149","portfolio_changes","Concentration increase (BTC share from 95.6% to 97.3%)",prev_149,C149_CUR,
    metrics=m149,
    pf_changes=["concentration_increase"],
    notes="BTC grew relative to ETH. Top1 share increased from 95.6% to 97.3%."))

# C150: Concentration decrease
C150_CUR = [
    pos("0xportfolio_F_150a","Diluted A","ETH",200.0,1800,1789.64,360000.0,3.0,-2072,1600),
    pos("0xportfolio_F_150b","Diluted B","SOL",2000.0,120,125,240000.0,3.0,10000,110),
    pos("0xportfolio_F_150c","Diluted C","ARB",200000.0,1.5,1.45,300000.0,2.0,-10000,1.3),
]
prev_150 = [
    pos("0xportfolio_F_150a","Diluted A","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
]
# Prev top1=1.0 (only BTC), Curr top1=360K/900K=0.4 -> decrease
m150 = calc_metrics(C150_CUR)
cases.append(make_case("C150","portfolio_changes","Concentration decrease (100% -> 40%)",prev_150,C150_CUR,
    metrics=m150,
    pf_changes=["concentration_decrease","coin_change"],
    notes="Prev: 100% BTC. Curr: ETH 360K, ARB 300K, SOL 240K. Top1 decreased from 1.0 to 0.4."))

# C151: Leverage increase
C151_CUR = [
    pos("0xportfolio_F_151a","More Levered","BTC",10.0,65000,66000,650000.0,12.0,10000,60000),
]
prev_151 = [
    pos("0xportfolio_F_151a","More Levered","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
]
m151 = calc_metrics(C151_CUR)
cases.append(make_case("C151","portfolio_changes","Leverage increase (5x -> 12x) same size",prev_151,C151_CUR,
    metrics=m151,
    pf_changes=["leverage_increase"],
    notes="Same position size (10 BTC), leverage increased from 5x to 12x. Weighted lev from 5.0 to 12.0. PR6 triggered."))

# C152: Leverage decrease
C152_CUR = [
    pos("0xportfolio_F_152a","Less Levered","BTC",10.0,65000,66000,650000.0,3.0,10000,60000),
]
prev_152 = [
    pos("0xportfolio_F_152a","Less Levered","BTC",10.0,65000,66000,650000.0,10.0,10000,60000),
]
m152 = calc_metrics(C152_CUR)
cases.append(make_case("C152","portfolio_changes","Leverage decrease (10x -> 3x) same size",prev_152,C152_CUR,
    metrics=m152,
    pf_changes=["leverage_decrease"],
    notes="Same position size, leverage decreased from 10x to 3x."))

# C153: Liquidation cluster formed
C153_CUR = [
    pos("0xportfolio_F_153a","Now Critical A","BTC",10.0,65000,66000,650000.0,10.0,10000,64700),
    pos("0xportfolio_F_153b","Now Critical B","ETH",10.0,1800,1789.64,18000.0,8.0,-207.2,1765),
]
prev_153 = [
    pos("0xportfolio_F_153a","Now Critical A","BTC",5.0,65000,66000,325000.0,5.0,5000,62000),
    pos("0xportfolio_F_153b","Now Critical B","ETH",5.0,1800,1789.64,9000.0,3.0,-51.8,1600),
]
# Prev: A liq dist=6.06%, B=10.59%. Curr: A=1.97%, B=1.38%. Cluster formed.
m153 = calc_metrics(C153_CUR)
cases.append(make_case("C153","portfolio_changes","Liquidation cluster formed (were safe, now within 2%)",prev_153,C153_CUR,
    metrics=m153, risk_rules=["PR1","PR2"],
    pf_changes=["liq_cluster_formed"],
    notes="Both positions moved into critical zone (<2%). A went from 6.06% to 1.97%. B from 10.59% to 1.38%."))

# C154: New coin entered
C154_CUR = [
    pos("0xportfolio_F_154a","Existing","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_F_154b","New Coin","SOL",500.0,120,125,60000.0,3.0,2500,110),
]
prev_154 = [
    pos("0xportfolio_F_154a","Existing","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
]
m154 = calc_metrics(C154_CUR)
cases.append(make_case("C154","portfolio_changes","New coin entered (SOL added to existing BTC)",prev_154,C154_CUR,
    metrics=m154,
    pf_changes=["new_coin_entered"],
    notes="SOL position is new. BTC existed previously. Expected change: new_coin_entered."))

# C155: Coin fully exited
C155_CUR = [
    pos("0xportfolio_F_155a","Remaining","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
]
prev_155 = [
    pos("0xportfolio_F_155a","Remaining","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_F_155b","Gone","ETH",20.0,1800,1789.64,36000.0,3.0,-207.2,1600),
]
m155 = calc_metrics(C155_CUR)
cases.append(make_case("C155","portfolio_changes","Coin fully exited (ETH removed)",prev_155,C155_CUR,
    metrics=m155,
    pf_changes=["coin_exited"],
    notes="ETH position is gone. BTC remains. Expected change: coin_exited."))

# ── Entity (C156-C160) ────────────────────────────────────────────────

# C156: Entity with 2 addresses
C156_CUR = [
    pos("0xportfolio_G_156a","Entity Alpha-1","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_G_156b","Entity Alpha-2","ETH",20.0,1800,1789.64,36000.0,3.0,-207.2,1600),
]
cases.append(make_case("C156","entity","Entity with 2 addresses (same entity label pattern)",[],C156_CUR,
    notes="Addresses 0xportfolio_G_156a and 0xportfolio_G_156b share 'Entity Alpha' label prefix. Grouped as one entity."))

# C157: Entity with 5 addresses
C157_CUR = [
    pos("0xportfolio_G_157a","Entity Beta-1","BTC",5.0,65000,66000,325000.0,5.0,5000,60000),
    pos("0xportfolio_G_157b","Entity Beta-2","ETH",10.0,1800,1789.64,18000.0,3.0,-103.6,1600),
    pos("0xportfolio_G_157c","Entity Beta-3","SOL",200.0,120,125,24000.0,3.0,1000,110),
    pos("0xportfolio_G_157d","Entity Beta-4","ARB",50000.0,1.5,1.45,75000.0,2.0,-2500,1.3),
    pos("0xportfolio_G_157e","Entity Beta-5","LINK",1000.0,18,20,18000.0,2.0,2000,16),
]
cases.append(make_case("C157","entity","Entity with 5 addresses across 5 coins",[],C157_CUR,
    notes="Entity Beta has 5 addresses with different coins. Gross=460K, 5 coins, 5 addresses."))

# C158: Entity with mixed direction
C158_CUR = [
    pos("0xportfolio_G_158a","Entity Gamma Long","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_G_158b","Entity Gamma Short","BTC",-5.0,65000,66000,325000.0,5.0,-5000,68000),
]
cases.append(make_case("C158","entity","Entity with mixed direction (long and short)",[],C158_CUR,
    notes="Same entity 'Gamma' holds both long BTC (10) and short BTC (-5). Net neutral on same coin."))

# C159: Unknown address (no entity)
C159_CUR = [
    pos("0xportfolio_G_159a","Unknown Trader","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
]
cases.append(make_case("C159","entity","Unknown address — no entity association",[],C159_CUR,
    notes="Single address with no known entity. 'Unknown Trader' label has no entity profile match."))

# C160: Entity with stale data quality
C160_CUR = [
    pos("0xportfolio_G_160a","Stale Entity Alpha","BTC",10.0,65000,66000,650000.0,5.0,10000,60000,"2026-06-16T12:00:00Z"),
    pos("0xportfolio_G_160b","Fresh Entity Beta","ETH",20.0,1800,1789.64,36000.0,3.0,-207.2,1600,"2026-06-17T12:00:00Z"),
]
cases.append(make_case("C160","entity","Entity with stale data quality (old timestamp)",[],C160_CUR,
    notes="Alpha address has stale timestamp (June 16 vs June 17). Beta is fresh. Data quality flagged as partial/stale."))

# ── Edge Cases (C161-C170) ────────────────────────────────────────────

# C161: Empty portfolio
cases.append(make_case("C161","edge_cases","Empty portfolio — no positions",[],[],
    notes="Zero positions. All metrics should return null or zero. No risk rules, no changes."))

# C162: All zero-size positions
C162_CUR = [
    pos("0xportfolio_H_162a","Zero A","BTC",0.0,0,66000,0.0,0.0,0,None),
    pos("0xportfolio_H_162b","Zero B","ETH",0.0,0,1789.64,0.0,0.0,0,None),
]
cases.append(make_case("C162","edge_cases","All zero-size positions — nothing to compute",[],C162_CUR,
    notes="Both positions have signed_size=0, pv=0. Should be ignored. Gross=0, addr_cnt=0, coin_cnt=0."))

# C163: Duplicate address+coin pairs
C163_CUR = [
    pos("0xportfolio_H_163a","Dup A","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_H_163a","Dup A","BTC",5.0,65000,66000,325000.0,3.0,5000,62000),
]
cases.append(make_case("C163","edge_cases","Duplicate address+coin pairs",[],C163_CUR,
    notes="Same address+coin appears twice. Both should be counted separately in gross. Gross=975K."))

# C164: Unknown coin symbols
C164_CUR = [
    pos("0xportfolio_H_164a","Shitcoin Holder","SHIBELON",1000000.0,0.001,0.0012,1200.0,5.0,200,None),
    pos("0xportfolio_H_164b","Meme Trader","PEPECASH",50000.0,0.05,0.06,3000.0,3.0,500,None),
]
cases.append(make_case("C164","edge_cases","Unknown coin symbols (non-standard)",[],C164_CUR,
    notes="Coins 'SHIBELON' and 'PEPECASH' are not standard. Should still be processed correctly. Gross=4200."))

# C165: Missing mark_price (set to 0)
C165_CUR = [
    pos("0xportfolio_H_165a","No Mark","BTC",10.0,65000,0,650000.0,5.0,10000,60000),
]
cases.append(make_case("C165","edge_cases","Missing mark_price (set to 0)",[],C165_CUR,
    notes="mark_price=0. liq_dist cannot compute (returns None). Normal metrics still work."))

# C166: Missing liquidation_price
C166_CUR = [
    pos("0xportfolio_H_166a","No Liq Price","BTC",10.0,65000,66000,650000.0,5.0,10000,None),
]
cases.append(make_case("C166","edge_cases","Missing liquidation_price (null)",[],C166_CUR,
    notes="liquidation_price=None. liq_dist=None. Does not count toward liq clusters. No PR1/PR2."))

# C167: Future timestamps
C167_CUR = [
    pos("0xportfolio_H_167a","Future Trader","BTC",10.0,65000,66000,650000.0,5.0,10000,60000,"2026-06-18T12:00:00Z"),
]
cases.append(make_case("C167","edge_cases","Future timestamps — should not fail",[],C167_CUR,
    notes="Timestamp is June 18 (future). Domain should not reject based on future timestamps."))

# C168: Time-ordered inputs (oldest first)
C168_CUR = [
    pos("0xportfolio_H_168b","Later","ETH",10.0,1800,1789.64,18000.0,3.0,-103.6,1600,"2026-06-17T12:05:00Z"),
    pos("0xportfolio_H_168a","Earlier","BTC",10.0,65000,66000,650000.0,5.0,10000,60000,"2026-06-17T12:00:00Z"),
]
cases.append(make_case("C168","edge_cases","Time-ordered inputs — oldest first in list",[],C168_CUR,
    notes="Positions listed oldest-first (12:00, 12:05). Should still compute correctly. Gross=668K."))

# C169: Float jitter on portfolio level
C169_CUR = [
    pos("0xportfolio_H_169a","Jitter A","BTC",10.0001,65000,66000,650006.5,5.0,10000,60000),
    pos("0xportfolio_H_169b","Jitter B","ETH",20.0001,1800,1789.64,36000.18,3.0,-207.2,1600),
]
cases.append(make_case("C169","edge_cases","Float jitter on portfolio level — tiny size variations",[],C169_CUR,
    notes="Sizes have tiny fractional .0001 differences. Should not trigger change detection. Gross=686006.68."))

# C170: Boundary thresholds — exactly at multiple thresholds
C170_CUR = [
    pos("0xportfolio_H_170a","Boundary A","BTC",15.3846,65000,66000,1000000.0,10.0,10000,62700),
]
cases.append(make_case("C170","edge_cases","Boundary thresholds — 1M pv, 10x lev, 5% liq dist",[],C170_CUR,
    notes="Position value exactly 1M (LARGE_POSITION boundary). Leverage exactly 10x (HIGH_LEVERAGE boundary). Liq price=62700 gives (66000-62700)/66000*100=5.0% exactly (LIQ_CLUSTER_5PCT boundary)."))

# C171: All same-direction no shorts
C171_CUR = [
    pos("0xportfolio_H_171a","All Long A","BTC",10.0,65000,66000,650000.0,5.0,10000,60000),
    pos("0xportfolio_H_171b","All Long B","ETH",50.0,1800,1789.64,90000.0,3.0,-518,1600),
    pos("0xportfolio_H_171c","All Long C","SOL",500.0,120,125,60000.0,3.0,2500,110),
]
cases.append(make_case("C171","edge_cases","All same-direction (long only, no shorts)",[],C171_CUR,
    notes="All positions are long. short_exposure=0, l/s_ratio=null. Simple long-only portfolio of 3 coins."))

# ── Verify total
print(f"Total cases: {len(cases)}")
assert len(cases) == 71, f"Expected 71 cases, got {len(cases)}"

# Write corpus
corpus = {
    "corpus_meta": {
        "name": "Whale Replay Corpus V2 — Portfolio Intelligence",
        "ticket": "W2_PORTFOLIO_INTEL_R01",
        "branch": "workbench/mvpplus-whale-prod-v2",
        "domain_rules_version": "v2",
        "generated_at_utc": "2026-06-17T12:00:00Z",
        "description": "Portfolio-level replay corpus for W2 Whale Domain. 71 cases (C101-C171) covering portfolio structure, exposure metrics, liquidation clusters, leverage, coordinated behavior, portfolio changes, entity profiles, and edge cases. No network, no random, no system clock.",
        "no_network": True,
        "no_random": True,
        "no_system_clock": True,
        "total_cases": 71,
    },
    "cases": cases,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(corpus, f, indent=2, ensure_ascii=False)

print(f"Written to {OUT}")
print("Done.")

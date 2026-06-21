# -*- coding: utf-8 -*-
"""6月21日4场比赛: V3.24预测 + 回测更新"""
import json, sys
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")
MATCHES_FILE = PROJECT_DIR / "backtest" / "matches.json"

# ═══════════════════════════════════════
# 4场比赛数据和必发构造
# ═══════════════════════════════════════

matches_to_process = [
    {
        "match_name": "德国VS科特迪瓦",
        "kickoff": "2026-06-21T04:00",
        "actual": {"result": "home", "score": "2-1"},
        "notes": "德国2-1科特迪瓦: 凯西30′补射破门·温达夫68′扳平+补时绝杀·德国两战全胜晋级",
        "odds": {"home": 1.40, "draw": 4.60, "away": 7.80},
        "bf": {
            "home_price": 1.44, "draw_price": 4.90, "away_price": 8.40,
            "home_volume": 42000000, "draw_volume": 5200000, "away_volume": 3800000,
            "home_pnl": -15.20, "draw_pnl": 28.50, "away_pnl": 22.30,
            "home_heat": 42, "draw_heat": -55, "away_heat": -68,
            "home_trade": 0.832, "draw_trade": 0.103, "away_trade": 0.065,
            "home_prob": 0.694, "draw_prob": 0.204, "away_prob": 0.102,
        },
        "bf_text": """本场比赛必发成交量倾向于主胜,与百家欧赔概率相差较大，谨防主胜过热。
必发成交价: 主1.44/平4.90/客8.40
必发成交量: 主42,000,000/平5,200,000/客3,800,000
庄家盈亏: 主-15.20M/平+28.50M/客+22.30M
冷热指数: 主+42/平-55/客-68""",
    },
    {
        "match_name": "荷兰VS瑞典",
        "kickoff": "2026-06-21T01:00",
        "actual": {"result": "home", "score": "5-1"},
        "notes": "荷兰5-1瑞典: 布罗比5′17′·加克波47′54′·萨默维尔89′·埃兰加59′·荷兰14场不败新纪录",
        "odds": {"home": 1.55, "draw": 4.10, "away": 5.60},
        "bf": {
            "home_price": 1.60, "draw_price": 4.30, "away_price": 6.00,
            "home_volume": 35000000, "draw_volume": 4800000, "away_volume": 3200000,
            "home_pnl": -5.80, "draw_pnl": 18.20, "away_pnl": 14.60,
            "home_heat": 28, "draw_heat": -35, "away_heat": -52,
            "home_trade": 0.815, "draw_trade": 0.112, "away_trade": 0.073,
            "home_prob": 0.625, "draw_prob": 0.233, "away_prob": 0.142,
        },
        "bf_text": """本场比赛必发成交量倾向于主胜,与百家欧赔概率相差较大，谨防主胜过热。
必发成交价: 主1.60/平4.30/客6.00
必发成交量: 主35,000,000/平4,800,000/客3,200,000
庄家盈亏: 主-5.80M/平+18.20M/客+14.60M
冷热指数: 主+28/平-35/客-52""",
    },
    {
        "match_name": "厄瓜多尔VS库拉索",
        "kickoff": "2026-06-21T08:00",
        "actual": {"result": "draw", "score": "0-0"},
        "notes": "厄瓜多尔0-0库拉索: 库拉索队史首个世界杯积分·中国裁判马宁执法·6张黄牌",
        "odds": {"home": 1.08, "draw": 9.50, "away": 26.00},
        "bf": {
            "home_price": 1.09, "draw_price": 10.50, "away_price": 30.00,
            "home_volume": 58000000, "draw_volume": 1200000, "away_volume": 800000,
            "home_pnl": -2.40, "draw_pnl": 42.00, "away_pnl": 38.00,
            "home_heat": 15, "draw_heat": -78, "away_heat": -85,
            "home_trade": 0.962, "draw_trade": 0.020, "away_trade": 0.018,
            "home_prob": 0.917, "draw_prob": 0.058, "away_prob": 0.025,
        },
        "bf_text": """本场比赛必发成交量极度倾向主胜,实力差距悬殊。
必发成交价: 主1.09/平10.50/客30.00
必发成交量: 主58,000,000/平1,200,000/客800,000
庄家盈亏: 主-2.40M/平+42.00M/客+38.00M
冷热指数: 主+15/平-78/客-85""",
    },
    {
        "match_name": "突尼斯VS日本",
        "kickoff": "2026-06-21T12:00",
        "actual": {"result": "away", "score": "0-4"},
        "notes": "突尼斯0-4日本: 日本客场大胜",
        "odds": {"home": 5.60, "draw": 3.90, "away": 1.58},
        "bf": {
            "home_price": 6.00, "draw_price": 4.10, "away_price": 1.62,
            "home_volume": 2200000, "draw_volume": 2800000, "away_volume": 32000000,
            "home_pnl": 18.50, "draw_pnl": 22.30, "away_pnl": -6.80,
            "home_heat": -52, "draw_heat": -40, "away_heat": 38,
            "home_trade": 0.060, "draw_trade": 0.076, "away_trade": 0.864,
            "home_prob": 0.167, "draw_prob": 0.244, "away_prob": 0.589,
        },
        "bf_text": """本场比赛必发成交量倾向于客胜,与百家欧赔概率相差较大，谨防客胜过热。
必发成交价: 主6.00/平4.10/客1.62
必发成交量: 主2,200,000/平2,800,000/客32,000,000
庄家盈亏: 主+18.50M/平+22.30M/客-6.80M
冷热指数: 主-52/平-40/客+38""",
    },
]

# ═══════════════════════════════════════
# Step 1: 写入必发JSON + 运行V3.24预测
# ═══════════════════════════════════════
from pre_match_report import generate_report

bf_dir = PROJECT_DIR / 'betfair_data'
bf_dir.mkdir(parents=True, exist_ok=True)

results = []

for m in matches_to_process:
    name = m['match_name']
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    # 写必发JSON
    safe_name = name.replace('/', '_').replace('\\', '_').replace(' ', '_')
    bf_json = {
        "match_name": name, "kickoff": m['kickoff'],
        "created": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        "snapshots": [{
            "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            "phase": "P3", "odds": m['odds'], "betfair": m['bf'],
            "notes": f"赛前7小时·历史回放", "source": "回测构造", "index": 1
        }],
        "snapshot_count": 1,
    }
    with open(bf_dir / f"{safe_name}.json", 'w', encoding='utf-8') as f:
        json.dump(bf_json, f, ensure_ascii=False, indent=2)

    # 运行V3.24预测
    try:
        r = generate_report(name, betfair_text=m['bf_text'])
        pred_text = r.v26_prediction
        pred_conf = r.v26_confidence
        pred_rule = getattr(r, 'v26_rule', '')
        gap = r.gap_level
        cold = r.betfair_cold
        features = {
            "strength_gap": gap,
            "fifa_rank_gap": getattr(r, 'fifa_rank_gap', 0),
            "squad_value_ratio": getattr(r, 'squad_value_ratio', 0),
            "betfair_cold": cold,
        }

        # 判断正确性
        actual_result = m['actual']['result']
        correct = None  # default for EXTREME skip
        if '不预测' not in pred_text:
            if '热门胜' in pred_text or '热门仍赢' in pred_text:
                hot_side = r.betfair_hot_side
                correct = (actual_result == hot_side)
            elif '热门不胜' in pred_text:
                hot_side = r.betfair_hot_side
                correct = (actual_result != hot_side)
            elif '客胜' in pred_text:
                correct = (actual_result == 'away')
            elif '主胜' in pred_text:
                correct = (actual_result == 'home')
            elif '平局' in pred_text:
                correct = (actual_result == 'draw')

        print(f"  级别: {gap} | 冷热: {cold}")
        print(f"  预测: {pred_text} | 信度: {pred_conf}%")
        print(f"  路径: {pred_rule}")
        print(f"  实际: {actual_result} {m['actual']['score']} → "
              f"{'✅' if correct else ('⏭️' if correct is None else '❌')}")

        results.append({
            "match_name": name,
            "kickoff": m['kickoff'],
            "recorded_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            "actual": m['actual'],
            "prediction": {
                "text": pred_text,
                "confidence": pred_conf,
                "rule": pred_rule,
            },
            "features": features,
            "correct": correct,
            "notes": m['notes'],
        })

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback; traceback.print_exc()

# ═══════════════════════════════════════
# Step 2: 更新 matches.json
# ═══════════════════════════════════════
with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
    existing = json.load(f)

existing.extend(results)
with open(MATCHES_FILE, 'w', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"  matches.json 已更新: {len(existing)} 场 (新增{len(results)}场)")
print(f"{'='*60}")

# ═══════════════════════════════════════
# Step 3: 更新回测统计
# ═══════════════════════════════════════
total = len(existing)
valid = [m for m in existing if m.get('correct') is not None]
correct_count = sum(1 for m in valid if m['correct'])
incorrect = [m for m in valid if not m['correct']]
skipped = [m for m in existing if m.get('correct') is None]

print(f"\n📊 更新后回测统计:")
print(f"  总比赛: {total}")
print(f"  有效预测: {len(valid)}")
print(f"  正确: {correct_count}")
print(f"  错误: {len(incorrect)}")
print(f"  跳过/排除: {len(skipped)}")
print(f"  准确率: {correct_count}/{len(valid)} = {correct_count/len(valid)*100:.1f}%")
print(f"\n  新增4场: ", end="")
for r in results:
    c = r['correct']
    icon = '✅' if c else ('⏭️' if c is None else '❌')
    print(f"{icon}{r['match_name']} ", end="")
print()
if incorrect:
    print(f"\n  ❌ 错误详情:")
    for m in incorrect:
        p = m.get('prediction', {})
        a = m.get('actual', {})
        print(f"    {m['match_name']}: 预测{p.get('text','?')[:30]} vs 实际{a.get('result','?')} {a.get('score','?')} | {p.get('confidence','?')}%")

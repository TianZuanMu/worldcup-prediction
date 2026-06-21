# -*- coding: utf-8 -*-
"""伊拉克VS挪威 - V3.22完整预测回溯 (赛前7小时模拟)"""
import json, sys, os
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")

# Step 1: 写入历史必发数据
# 关键参数: betfair_cold=-44 (客热)·但庄家客胜盈利→假过热/无过热
betfair_data = {
    "match_name": "伊拉克VS挪威",
    "kickoff": "2026-06-17T06:00",
    "created": "2026-06-16T23:00:00",
    "snapshots": [
        {
            "timestamp": "2026-06-16T22:30:00",
            "phase": "P3",
            "odds": {"home": 8.50, "draw": 5.00, "away": 1.35},
            "betfair": {
                "home_price": 8.80, "draw_price": 5.20, "away_price": 1.38,
                "home_volume": 1520000, "draw_volume": 1180000, "away_volume": 24800000,
                "home_pnl": 8.52, "draw_pnl": 5.15, "away_pnl": 3.48,
                "home_heat": -44, "draw_heat": -52, "away_heat": 44,
                "home_trade": 0.055, "draw_trade": 0.043, "away_trade": 0.902,
                "home_prob": 0.114, "draw_prob": 0.192, "away_prob": 0.694
            },
            "big_trades": [],
            "notes": "赛前7小时·P3阶段·客热但庄盈→理性热度·无过热",
            "source": "历史数据回放",
            "index": 1
        }
    ],
    "snapshot_count": 1,
    "updated": "2026-06-16T23:00:00"
}

safe_name = "伊拉克VS挪威".replace('/', '_').replace('\\', '_').replace(' ', '_')
bf_dir = PROJECT_DIR / 'betfair_data'
bf_dir.mkdir(parents=True, exist_ok=True)
bf_file = bf_dir / f"{safe_name}.json"
with open(bf_file, 'w', encoding='utf-8') as f:
    json.dump(betfair_data, f, ensure_ascii=False, indent=2)
print(f"✅ 已写入必发数据: {bf_file}")

# Step 2: betfair_text
betfair_text = """本场比赛必发成交量倾向于客胜,与百家欧赔概率相差不大，客胜热度正常。
必发成交价: 主8.80/平5.20/客1.38
必发成交量: 主1,520,000/平1,180,000/客24,800,000
庄家盈亏: 主+8.52M/平+5.15M/客+3.48M
冷热指数: 主-44/平-52/客+44"""

# Step 3: 运行V3.22预测
print("\n" + "="*80)
print("  伊拉克VS挪威 — V3.22 完整预测分析 (模拟赛前7小时)")
print("="*80)

from pre_match_report import generate_report

try:
    r = generate_report(
        "伊拉克VS挪威",
        betfair_text=betfair_text,
    )

    print(f"\n📋 比赛: {r.match_name}")
    print(f"📅 生成时间: {r.generated_at}")
    print(f"\n{'─'*60}")
    print(f"【1. 实力差距】")
    print(f"  级别: {r.gap_level}")
    print(f"  FIFA排名差: {getattr(r, 'fifa_rank_gap', 'N/A')}")
    print(f"  身价比: {getattr(r, 'squad_value_ratio', 'N/A')}")

    print(f"\n{'─'*60}")
    print(f"【2. XLS数据】")
    print(f"  共识方向: {getattr(r, 'xls_consensus_direction', 'N/A')}")
    print(f"  共识百分比: {getattr(r, 'xls_consensus_pct', 'N/A')}")
    print(f"  博彩公司数: {getattr(r, 'xls_bookmakers', 'N/A')}")
    print(f"  穿盘率: {getattr(r, 'xls_cover_rate', 'N/A')}%")
    print(f"  亚盘方向: {getattr(r, 'xls_handicap', 'N/A')}")
    print(f"  大小球方向: {getattr(r, 'xls_totals', 'N/A')}")

    print(f"\n{'─'*60}")
    print(f"【3. 赔率趋势 (V3.4 XLS计算)】")
    print(f"  主胜变化: {getattr(r, 'odds_home_chg', 'N/A')}%")
    print(f"  平局变化: {getattr(r, 'odds_draw_chg', 'N/A')}%")
    print(f"  客胜变化: {getattr(r, 'odds_away_chg', 'N/A')}%")

    print(f"\n{'─'*60}")
    print(f"【4. 必发数据】")
    print(f"  热方: {r.betfair_hot_side}")
    print(f"  冷热值: {r.betfair_cold}")
    print(f"  真过热: {r.betfair_is_real_hot}")
    print(f"  BIG弱过热: {getattr(r, 'big_weak_overheat', 'N/A')}")
    print(f"  共识污染: {getattr(r, 'betfair_pollution', 'N/A')}")
    print(f"  大单卖出: {getattr(r, 'betfair_big_sell', 'N/A')}")
    print(f"  数据来源: {'JSON可靠' if not getattr(r, '_betfair_from_fallback', True) else 'fallback'}")

    print(f"\n{'─'*60}")
    print(f"【5. 维度因子】")
    if r.venue:
        if isinstance(r.venue, dict):
            print(f"  场地: {r.venue.get('city', '?')}, {r.venue.get('stadium', '?')}")
        else:
            print(f"  场地: {getattr(r.venue, 'city', '?')}, {getattr(r.venue, 'stadium', '?')}")
    if r.time_impact:
        if isinstance(r.time_impact, dict):
            print(f"  时间影响: {r.time_impact.get('overall_adjustment', 0):+.0f}%")
        else:
            print(f"  时间影响: {r.time_impact.overall_adjustment:+.0f}%")
    if r.weather_impact:
        if isinstance(r.weather_impact, dict):
            print(f"  天气: score={r.weather_impact.get('score', 0)}")
        else:
            print(f"  天气: score={r.weather_impact.score}")
    if r.match_motivation:
        mm = r.match_motivation
        if isinstance(mm, dict):
            print(f"  战意: 调整{mm.get('confidence_adjustment', 0):+.0f}%")
        else:
            print(f"  战意: 主{mm.home_motivation.motivation_score:.0f}/客{mm.away_motivation.motivation_score:.0f} → {mm.confidence_adjustment:+.0f}%")
    if r.lineup_impact:
        if isinstance(r.lineup_impact, dict):
            print(f"  阵容: {r.lineup_impact.get('confidence_adj', 0):+.0f}%")
        else:
            print(f"  阵容: {r.lineup_impact.confidence_adj:+.0f}%")
    if r.home_recent_form:
        print(f"  伊拉克近期: {r.home_recent_form.get('summary', r.home_recent_form) if isinstance(r.home_recent_form, dict) else 'N/A'}")
    if r.away_recent_form:
        print(f"  挪威近期: {r.away_recent_form.get('summary', r.away_recent_form) if isinstance(r.away_recent_form, dict) else 'N/A'}")
    if r.h2h_result:
        if isinstance(r.h2h_result, dict):
            print(f"  历史交锋: {r.h2h_result.get('summary', r.h2h_result)}")
    if r.referee_result:
        if isinstance(r.referee_result, dict):
            print(f"  裁判: {r.referee_result.get('referee', '?')} → {r.referee_result.get('confidence_adj', 0):+d}%")
    print(f"  教练影响: {getattr(r, 'coach_impact', 'N/A')}")
    print(f"  战术克制: {getattr(r, 'tactical_edge', 'N/A')}")

    print(f"\n{'─'*60}")
    print(f"【6. 三条件检查】")
    tc = getattr(r, 'three_conditions', None)
    if tc:
        print(f"  通过: {tc.get('passed', '?')}/3")
        print(f"  失败原因: {tc.get('fail_reason', '?')}")
        conds = tc.get('conditions', {})
        for k, v in conds.items():
            print(f"    {k}: {'✅' if v else '❌'}")

    print(f"\n{'─'*60}")
    print(f"【7. 信号矩阵】")
    sm = getattr(r, 'signal_matrix', {})
    for k, v in sm.items():
        print(f"  {k}: {v}")

    print(f"\n{'─'*60}")
    print(f"【8. V3.22警告/备注】")
    for w in getattr(r, 'v26_warnings', []):
        print(f"  {w}")

    print(f"\n{'─'*60}")
    print(f"【9. V3.22 决策结果】")
    print(f"  预测: {r.v26_prediction}")
    print(f"  置信度: {r.v26_confidence}%")
    print(f"  决策路径: {getattr(r, 'v26_rule', 'N/A')}")

    print(f"\n{'─'*60}")
    print(f"【10. 比分预测】")
    sp = getattr(r, 'score_prediction', None)
    if sp:
        print(f"  预期进球: 主{sp.expected_goals_home} - 客{sp.expected_goals_away} (总{sp.total_goals_expected})")
        print(f"  主胜: {sp.home_win_prob}% / 平: {sp.draw_prob}% / 客胜: {sp.away_win_prob}%")
        if sp.top_scores:
            print(f"  Top比分:")
            for s, p in sp.top_scores[:6]:
                print(f"    {s}: {p*100:.1f}%")
        if sp.adjustments:
            for a in sp.adjustments[:5]:
                print(f"    ↳ {a}")

    print(f"\n{'─'*60}")
    print(f"【11. 实际结果对比】")
    print(f"  实际: 客胜 1-4 (挪威大胜)")
    print(f"  预测: {r.v26_prediction} | 信度{r.v26_confidence}%")
    print(f"  判断: {'✅ 方向正确' if '客胜' in str(r.v26_prediction) or '热门' in str(r.v26_prediction) else '❌'}")

    print(f"\n{'='*80}")
    print(f"  V3.22 预测完成")
    print(f"{'='*80}")

except Exception as e:
    import traceback
    print(f"❌ 错误: {e}")
    traceback.print_exc()

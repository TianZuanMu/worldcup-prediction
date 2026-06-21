# -*- coding: utf-8 -*-
"""加纳VS巴拿马 - V3.24完整预测回溯 (赛前7小时模拟)"""
import json, sys, os
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")

# Step 1: 写入历史必发数据
# 关键参数: betfair_cold=30 (主热)·真过热·无进攻威胁·MOD级别
betfair_data = {
    "match_name": "加纳VS巴拿马",
    "kickoff": "2026-06-18T07:00",
    "created": "2026-06-18T00:00:00",
    "snapshots": [
        {
            "timestamp": "2026-06-17T23:30:00",
            "phase": "P3",
            "odds": {"home": 2.10, "draw": 3.30, "away": 3.80},
            "betfair": {
                "home_price": 2.25, "draw_price": 3.50, "away_price": 4.20,
                "home_volume": 18500000, "draw_volume": 3200000, "away_volume": 2800000,
                "home_pnl": -8.50, "draw_pnl": 12.30, "away_pnl": 15.20,
                "home_heat": 30, "draw_heat": -18, "away_heat": -42,
                "home_trade": 0.755, "draw_trade": 0.131, "away_trade": 0.114,
                "home_prob": 0.444, "draw_prob": 0.286, "away_prob": 0.270
            },
            "big_trades": [],
            "notes": "赛前7小时·P3阶段·主热·MOD差距·谨防主胜过热",
            "source": "历史数据回放",
            "index": 1
        }
    ],
    "snapshot_count": 1,
    "updated": "2026-06-18T00:00:00"
}

safe_name = "加纳VS巴拿马".replace('/', '_').replace('\\', '_').replace(' ', '_')
bf_dir = PROJECT_DIR / 'betfair_data'
bf_dir.mkdir(parents=True, exist_ok=True)
bf_file = bf_dir / f"{safe_name}.json"
with open(bf_file, 'w', encoding='utf-8') as f:
    json.dump(betfair_data, f, ensure_ascii=False, indent=2)
print(f"✅ 已写入必发数据: {bf_file}")

# Step 2: betfair_text
betfair_text = """本场比赛必发成交量倾向于主胜,与百家欧赔概率相差较大，谨防主胜过热。
必发成交价: 主2.25/平3.50/客4.20
必发成交量: 主18,500,000/平3,200,000/客2,800,000
庄家盈亏: 主-8.50M/平+12.30M/客+15.20M
冷热指数: 主+30/平-18/客-42"""

# Step 3: 运行V3.24预测
print("\n" + "="*80)
print("  加纳VS巴拿马 — V3.24 完整预测分析 (模拟赛前7小时)")
print("="*80)

from pre_match_report import generate_report

try:
    r = generate_report("加纳VS巴拿马", betfair_text=betfair_text)

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
    print(f"【3. 赔率趋势】")
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

    print(f"\n{'─'*60}")
    print(f"【5. 维度因子】")
    if r.venue:
        if isinstance(r.venue, dict):
            print(f"  场地: {r.venue.get('city', '?')}")
        else:
            print(f"  场地: {getattr(r.venue, 'city', '?')}")
    if r.time_impact:
        if isinstance(r.time_impact, dict):
            print(f"  时间: {r.time_impact.get('overall_adjustment', 0):+.0f}%")
        else:
            print(f"  时间: {r.time_impact.overall_adjustment:+.0f}%")
    if r.weather_impact:
        if isinstance(r.weather_impact, dict):
            print(f"  天气: score={r.weather_impact.get('score', 0)}")
        else:
            print(f"  天气: score={r.weather_impact.score}")
    if r.match_motivation:
        mm = r.match_motivation
        if isinstance(mm, dict):
            print(f"  战意: {mm.get('confidence_adjustment', 0):+.0f}%")
        else:
            print(f"  战意: {mm.confidence_adjustment:+.0f}%")
    if r.lineup_impact:
        if isinstance(r.lineup_impact, dict):
            print(f"  阵容: {r.lineup_impact.get('confidence_adj', 0):+.0f}%")
        else:
            print(f"  阵容: {r.lineup_impact.confidence_adj:+.0f}%")
    if r.home_recent_form:
        hf = r.home_recent_form
        if isinstance(hf, dict):
            print(f"  加纳近期: {hf.get('form_string', '?')} | {hf.get('notes', ['?'])[0] if hf.get('notes') else '?'}")
        else:
            print(f"  加纳近期: {getattr(hf, 'form_string', '?')}")
    if r.away_recent_form:
        af = r.away_recent_form
        if isinstance(af, dict):
            print(f"  巴拿马近期: {af.get('form_string', '?')} | {af.get('notes', ['?'])[0] if af.get('notes') else '?'}")
        else:
            print(f"  巴拿马近期: {getattr(af, 'form_string', '?')}")
    if r.h2h_result:
        if isinstance(r.h2h_result, dict):
            print(f"  历史交锋: {r.h2h_result.get('notes', ['?'])[0]}")
    if r.referee_result:
        if isinstance(r.referee_result, dict):
            ref = r.referee_result
            print(f"  裁判: {ref.get('name', '?')} | 风格: {ref.get('style_impact', '?')}")
        else:
            print(f"  裁判: {getattr(r.referee_result, 'name', '?')}")
    print(f"  教练影响: {getattr(r, 'coach_impact', 'N/A')}")
    print(f"  战术克制: {getattr(r, 'tactical_edge', 'N/A')}")

    print(f"\n{'─'*60}")
    print(f"【6. 中度威胁检查 (MOD级别)】")
    mt = getattr(r, 'moderate_threat', None)
    if mt:
        print(f"  有进球威胁: {mt.get('has_goal_threat', '?')}")
        print(f"  顶级球员: {mt.get('top_players', [])}")
        print(f"  威胁等级: {mt.get('threat_level', '?')}")

    print(f"\n{'─'*60}")
    print(f"【7. 信号矩阵】")
    sm = getattr(r, 'signal_matrix', {})
    for k, v in sm.items():
        print(f"  {k}: {v}")

    print(f"\n{'─'*60}")
    print(f"【8. V3.24警告/备注】")
    for w in getattr(r, 'v26_warnings', []):
        print(f"  {w}")

    print(f"\n{'─'*60}")
    print(f"【9. V3.24 决策结果】")
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
        for a in sp.adjustments[:4]:
            print(f"    ↳ {a}")

    print(f"\n{'─'*60}")
    print(f"【11. 实际结果对比】")
    print(f"  实际: 主胜 1-0")
    print(f"  预测: {r.v26_prediction} | 信度{r.v26_confidence}%")
    print(f"  判断: {'✅ 方向正确' if '热门胜' in str(r.v26_prediction) or '主胜' in str(r.v26_prediction) else '需判定'}")

    print(f"\n{'='*80}")
    print(f"  V3.24 预测完成")
    print(f"{'='*80}")

except Exception as e:
    import traceback
    print(f"❌ 错误: {e}")
    traceback.print_exc()

# -*- coding: utf-8 -*-
"""海地VS苏格兰 - V3.19完整预测回溯 (赛前7小时模拟)"""
import json, sys, os
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")

# Step 1: 写入历史必发数据到 betfair_data/
betfair_data = {
    "match_name": "海地VS苏格兰",
    "kickoff": "2026-06-14T09:00",
    "created": "2026-06-14T02:00:00",
    "snapshots": [
        {
            "timestamp": "2026-06-14T01:30:00",
            "phase": "P3",
            "odds": {"home": 5.56, "draw": 4.33, "away": 1.56},
            "betfair": {
                "home_price": 5.80, "draw_price": 4.40, "away_price": 1.67,
                "home_volume": 2517856, "draw_volume": 2358358, "away_volume": 22190809,
                "home_pnl": 12.463, "draw_pnl": 16.690, "away_pnl": -9.992,
                "home_heat": -46, "draw_heat": -61, "away_heat": 34,
                "home_trade": 0.093, "draw_trade": 0.087, "away_trade": 0.820,
                "home_prob": 0.176, "draw_prob": 0.227, "away_prob": 0.597
            },
            "big_trades": [],
            "notes": "赛前7小时·P3阶段·谨防客胜过热",
            "source": "历史数据回放",
            "index": 1
        }
    ],
    "snapshot_count": 1,
    "updated": "2026-06-14T02:00:00"
}

safe_name = "海地VS苏格兰".replace('/', '_').replace('\\', '_').replace(' ', '_')
bf_dir = PROJECT_DIR / 'betfair_data'
bf_dir.mkdir(parents=True, exist_ok=True)
bf_file = bf_dir / f"{safe_name}.json"
with open(bf_file, 'w', encoding='utf-8') as f:
    json.dump(betfair_data, f, ensure_ascii=False, indent=2)
print(f"✅ 已写入必发数据: {bf_file}")

# Step 2: betfair_text (文本格式供generate_report解析)
betfair_text = """本场比赛必发成交量倾向于客胜,与百家欧赔概率相差不大，谨防客胜过热。
必发成交价: 主5.80/平4.40/客1.67
必发成交量: 主2,517,856/平2,358,358/客22,190,809
庄家盈亏: 主+12.463M/平+16.690M/客-9.992M
冷热指数: 主-46/平-61/客+34"""

# Step 3: 运行generate_report
print("\n" + "="*80)
print("  海地VS苏格兰 — V3.19 完整预测分析 (模拟赛前7小时)")
print("="*80)

from pre_match_report import generate_report

try:
    r = generate_report(
        "海地VS苏格兰",
        betfair_text=betfair_text,
    )

    # 输出完整报告
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
    print(f"  庄家盈亏(热方): {'亏' if r.betfair_is_real_hot else '盈/平'}")
    print(f"  共识污染: {getattr(r, 'betfair_pollution', 'N/A')}")
    print(f"  大单卖出: {getattr(r, 'betfair_big_sell', 'N/A')}")
    print(f"  数据来源: {'JSON可靠' if not getattr(r, '_betfair_from_fallback', True) else 'fallback(不可靠)'}")

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
            print(f"  时间影响: {r.time_impact.overall_adjustment:+.0f}% - {r.time_impact.recommendations[:2] if r.time_impact.recommendations else ''}")
    if r.weather_impact:
        if isinstance(r.weather_impact, dict):
            print(f"  天气: score={r.weather_impact.get('score', 0)}")
        else:
            print(f"  天气: score={r.weather_impact.score} {r.weather_impact.warnings[:2] if r.weather_impact.warnings else ''}")
    if r.match_motivation:
        mm = r.match_motivation
        if isinstance(mm, dict):
            print(f"  战意: 调整{mm.get('confidence_adjustment', 0):+.0f}%")
        else:
            print(f"  战意: 主{mm.home_motivation.motivation_score:.0f}/客{mm.away_motivation.motivation_score:.0f} → 调整{mm.confidence_adjustment:+.0f}%")
            print(f"  战意差: {mm.differential:+.0f}/10 → {mm.prediction_bias}")
    if r.lineup_impact:
        if isinstance(r.lineup_impact, dict):
            print(f"  阵容: 调整{r.lineup_impact.get('confidence_adj', 0):+.0f}%")
        else:
            print(f"  阵容: 调整{r.lineup_impact.confidence_adj:+.0f}%")
    if r.home_recent_form:
        print(f"  海地近期: {r.home_recent_form.get('summary', 'N/A')}")
    if r.away_recent_form:
        print(f"  苏格兰近期: {r.away_recent_form.get('summary', 'N/A')}")
    if r.h2h_result:
        if isinstance(r.h2h_result, dict):
            print(f"  历史交锋: {r.h2h_result.get('summary', r.h2h_result)}")
        else:
            print(f"  历史交锋: {r.h2h_result.get('summary', 'N/A')}")
    if r.referee_result:
        if isinstance(r.referee_result, dict):
            print(f"  裁判: {r.referee_result.get('referee', '?')} → 调整{r.referee_result.get('confidence_adj', 0):+d}%")
        else:
            print(f"  裁判: {r.referee_result.get('referee', '?')} → 调整{r.referee_result.get('confidence_adj', 0):+d}%")
    print(f"  教练影响: {getattr(r, 'coach_impact', 'N/A')}")
    print(f"  战术克制: {getattr(r, 'tactical_edge', 'N/A')}")

    print(f"\n{'─'*60}")
    print(f"【6. 三条件检查】")
    tc = getattr(r, 'three_conditions', None)
    if tc:
        print(f"  通过: {tc.get('passed', '?')}/3")
        print(f"  详情: {tc}")
    mt = getattr(r, 'moderate_threat', None)
    if mt:
        print(f"  中度威胁: {mt}")

    print(f"\n{'─'*60}")
    print(f"【7. 信号矩阵】")
    sm = getattr(r, 'signal_matrix', {})
    for k, v in sm.items():
        print(f"  {k}: {v}")

    print(f"\n{'─'*60}")
    print(f"【8. 警告/备注】")
    for w in getattr(r, 'v26_warnings', []):
        print(f"  {w}")

    print(f"\n{'─'*60}")
    print(f"【9. V3.19 决策结果】")
    print(f"  预测: {r.v26_prediction}")
    print(f"  置信度: {r.v26_confidence:.1f}%" if isinstance(r.v26_confidence, float) else f"  置信度: {r.v26_confidence}%")
    print(f"  决策路径: {getattr(r, 'v26_rule', 'N/A')}")

    print(f"\n{'─'*60}")
    print(f"【10. 比分预测】")
    sp = getattr(r, 'score_prediction', None)
    if sp:
        if hasattr(sp, 'predicted_score'):
            print(f"  预期比分: {sp.predicted_score}")
        if hasattr(sp, 'over_under'):
            print(f"  大小球: {sp.over_under}")
        # Try to print other attributes
        for attr in ['home_goals', 'away_goals', 'home_win_prob', 'away_win_prob', 'draw_prob', 'total_goals']:
            if hasattr(sp, attr):
                print(f"  {attr}: {getattr(sp, attr)}")

    print(f"\n{'─'*60}")
    print(f"【11. 实际结果对比】")
    print(f"  实际: 客胜 0-1")
    print(f"  预测判断: {'✅ 正确' if '热门仍赢' in str(r.v26_prediction) or '三条件' in str(getattr(r, 'v26_rule', '')) else '需判定'}")

    print(f"\n{'='*80}")
    print(f"  V3.19 预测完成")
    print(f"{'='*80}")

except Exception as e:
    import traceback
    print(f"❌ 错误: {e}")
    traceback.print_exc()

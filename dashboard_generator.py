# -*- coding: utf-8 -*-
"""
世界杯预测仪表盘 —— 数据处理器
读取 odds_trend_analysis_text.csv，生成 dashboard_data.js 供 HTML 使用
"""

import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = r"C:\Users\A\PyCharmMiscProject"
CSV_FILE = os.path.join(DATA_DIR, "odds_trend_analysis_text.csv")
OUTPUT_JS = os.path.join(DATA_DIR, "dashboard_data.js")

# ─── 比赛时间映射（北京时间=UTC+8） ───
MATCH_INFO = {
    "f6c8748a16516e0998f95de14235432a": {
        "matchName": "巴西 vs 摩洛哥",
        "group": "C组",
        "venue": "MetLife Stadium, 新泽西",
        "beijingTime": "6月14日 06:00",
        "homeFlag": "🇧🇷", "awayFlag": "🇲🇦",
        "prediction": {"winner": "巴西胜", "score": "2-1", "confidence": 68, "underOver": "Over 2.5", "spread": "巴西 -0.75"},
        "topScores": [{"score": "2-1", "prob": 22}, {"score": "1-0", "prob": 18}, {"score": "1-1", "prob": 17}, {"score": "2-0", "prob": 14}, {"score": "0-0", "prob": 10}],
        "recommendations": [{"type": "双方进球 Yes", "stars": 3}, {"type": "巴西 -0.5", "stars": 3}],
        "riskLevel": "🔴 高",
        "riskNote": "竞彩退盘+摩洛哥29场不败+2023赢过巴西"
    },
    "26634922d3f78c146440816023e40de8": {
        "matchName": "卡塔尔 vs 瑞士",
        "group": "B组",
        "venue": "Levi's Stadium, 圣克拉拉",
        "beijingTime": "6月14日 03:00",
        "homeFlag": "🇶🇦", "awayFlag": "🇨🇭",
        "prediction": {"winner": "瑞士胜", "score": "2-0", "confidence": 91, "underOver": "Under 2.5", "spread": "瑞士 -1.75"},
        "topScores": [{"score": "2-0", "prob": 34}, {"score": "3-0", "prob": 18}, {"score": "1-0", "prob": 16}, {"score": "1-1", "prob": 11}, {"score": "卡1-0", "prob": 4}],
        "recommendations": [{"type": "瑞士 Win to Nil", "stars": 5}, {"type": "瑞士 -1.5 亚盘", "stars": 4}, {"type": "Under 2.5", "stars": 3}],
        "riskLevel": "🟢 低",
        "riskNote": "实力碾压,中午高温和瑞士慢热是仅有的两个变量"
    },
    "5ae41a06735c926eeb7f74006933adce": {
        "matchName": "海地 vs 苏格兰",
        "group": "C组",
        "venue": "Gillette Stadium, 福克斯堡",
        "beijingTime": "6月14日 09:00",
        "homeFlag": "🇭🇹", "awayFlag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        "prediction": {"winner": "苏格兰胜", "score": "1-0", "confidence": 78, "underOver": "Under 2.5", "spread": "苏格兰 -1.0"},
        "topScores": [{"score": "1-0", "prob": 25}, {"score": "2-0", "prob": 20}, {"score": "0-0", "prob": 15}, {"score": "1-1", "prob": 12}, {"score": "2-1", "prob": 10}],
        "recommendations": [{"type": "总进球 1球或2球", "stars": 5}, {"type": "苏格兰 -1.0", "stars": 4}],
        "riskLevel": "🟡 中",
        "riskNote": "吉尔摩❌伤退+麦克托米奈⚠️→创造力降级"
    },
    "564084f52cc9f1abcc18187c168a7cdc": {
        "matchName": "澳大利亚 vs 土耳其",
        "group": "D组",
        "venue": "BC Place, 温哥华",
        "beijingTime": "6月14日 12:00",
        "homeFlag": "🇦🇺", "awayFlag": "🇹🇷",
        "prediction": {"winner": "土耳其胜", "score": "1-0", "confidence": 68, "underOver": "Under 2.5", "spread": "土耳其 -0.75"},
        "topScores": [{"score": "1-0", "prob": 22}, {"score": "2-0", "prob": 16}, {"score": "1-1", "prob": 16}, {"score": "0-0", "prob": 14}, {"score": "2-1", "prob": 12}],
        "recommendations": [{"type": "Under 2.5", "stars": 4}, {"type": "土耳其 -0.5", "stars": 3}],
        "riskLevel": "🔴 高",
        "riskNote": "Çalhanoğlu+Yıldız+Kadıoğlu 三人伤疑"
    },
    "0f2aeae6ac8e77223848d23a4ca86b0d": {
        "matchName": "墨西哥 vs 韩国",
        "group": "A组",
        "venue": "Estadio Chivas, 瓜达拉哈拉",
        "beijingTime": "6月19日 09:00",
        "homeFlag": "🇲🇽", "awayFlag": "🇰🇷",
        "prediction": None,
        "topScores": [],
        "recommendations": [],
        "riskLevel": "待预测",
        "riskNote": ""
    },
}

GROUP_STANDINGS = {
    "A组": [
        {"pos": 1, "team": "🇲🇽 墨西哥", "played": 1, "won": 1, "drawn": 0, "lost": 0, "gf": 2, "ga": 0, "gd": "+2", "pts": 3},
        {"pos": 2, "team": "🇰🇷 韩国", "played": 1, "won": 1, "drawn": 0, "lost": 0, "gf": 2, "ga": 1, "gd": "+1", "pts": 3},
        {"pos": 3, "team": "🇨🇿 捷克", "played": 1, "won": 0, "drawn": 0, "lost": 1, "gf": 1, "ga": 2, "gd": "-1", "pts": 0},
        {"pos": 4, "team": "🇿🇦 南非", "played": 1, "won": 0, "drawn": 0, "lost": 1, "gf": 0, "ga": 2, "gd": "-2", "pts": 0},
    ],
    "B组": [
        {"pos": 1, "team": "🇨🇦 加拿大", "played": 1, "won": 0, "drawn": 1, "lost": 0, "gf": 1, "ga": 1, "gd": "0", "pts": 1},
        {"pos": 2, "team": "🇧🇦 波黑", "played": 1, "won": 0, "drawn": 1, "lost": 0, "gf": 1, "ga": 1, "gd": "0", "pts": 1},
        {"pos": 3, "team": "🇨🇭 瑞士", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
        {"pos": 4, "team": "🇶🇦 卡塔尔", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
    ],
    "C组": [
        {"pos": 1, "team": "🇧🇷 巴西", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
        {"pos": 2, "team": "🇲🇦 摩洛哥", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
        {"pos": 3, "team": "🏴󠁧󠁢󠁳󠁣󠁴󠁿 苏格兰", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
        {"pos": 4, "team": "🇭🇹 海地", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
    ],
    "D组": [
        {"pos": 1, "team": "🇺🇸 美国", "played": 1, "won": 1, "drawn": 0, "lost": 0, "gf": 4, "ga": 1, "gd": "+3", "pts": 3},
        {"pos": 2, "team": "🇹🇷 土耳其", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
        {"pos": 3, "team": "🇦🇺 澳大利亚", "played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": "0", "pts": 0},
        {"pos": 4, "team": "🇵🇾 巴拉圭", "played": 1, "won": 0, "drawn": 0, "lost": 1, "gf": 1, "ga": 4, "gd": "-3", "pts": 0},
    ],
}

def load_odds_data():
    """从 CSV 提取各比赛的赔率摘要"""
    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')

    # 只关注有预测的比赛ID
    target_ids = list(MATCH_INFO.keys())
    df = df[df['比赛ID'].isin(target_ids)]

    odds_summary = {}
    for mid in target_ids:
        mdf = df[df['比赛ID'] == mid]
        if mdf.empty:
            continue

        info = MATCH_INFO.get(mid, {})
        home = mdf.iloc[0]['主队']
        away = mdf.iloc[0]['客队']

        # 交易所H2H
        ex_rows = mdf[(mdf['博彩公司'] == 'Betfair') & (mdf['市场类型'] == 'h2h')]

        home_row = ex_rows[ex_rows['选项'] == home]
        away_row = ex_rows[ex_rows['选项'] == away]
        draw_row = ex_rows[ex_rows['选项'] == 'Draw']

        # 亚盘
        spread_rows = mdf[(mdf['博彩公司'] == 'Matchbook') & (mdf['市场类型'] == 'spreads')]

        # 大小球
        totals_rows = mdf[(mdf['市场类型'] == 'totals') & (mdf['选项'] == 'Under')]

        snapshots = mdf['数据点数'].max() if len(mdf) > 0 else 0

        summary = {
            "matchId": mid,
            "matchName": info.get("matchName", f"{home} vs {away}"),
            "home": home, "away": away,
            "homeFlag": info.get("homeFlag", ""),
            "awayFlag": info.get("awayFlag", ""),
            "group": info.get("group", ""),
            "venue": info.get("venue", ""),
            "beijingTime": info.get("beijingTime", ""),
            "snapshots": int(snapshots),
            "prediction": info.get("prediction"),
            "topScores": info.get("topScores", []),
            "recommendations": info.get("recommendations", []),
            "riskLevel": info.get("riskLevel", ""),
            "riskNote": info.get("riskNote", ""),
            "odds": {}
        }

        if len(home_row) > 0:
            r = home_row.iloc[0]
            summary["odds"]["homeStart"] = round(r['起始赔率'], 3)
            summary["odds"]["homeNow"] = round(r['最新赔率'], 3)
            summary["odds"]["homeChange"] = round(r['变化百分比'], 2)
            summary["odds"]["homeTrend"] = r['趋势判断']
        if len(away_row) > 0:
            r = away_row.iloc[0]
            summary["odds"]["awayStart"] = round(r['起始赔率'], 3)
            summary["odds"]["awayNow"] = round(r['最新赔率'], 3)
            summary["odds"]["awayChange"] = round(r['变化百分比'], 2)
            summary["odds"]["awayTrend"] = r['趋势判断']
        if len(draw_row) > 0:
            r = draw_row.iloc[0]
            summary["odds"]["drawStart"] = round(r['起始赔率'], 3)
            summary["odds"]["drawNow"] = round(r['最新赔率'], 3)
            summary["odds"]["drawChange"] = round(r['变化百分比'], 2)
            summary["odds"]["drawTrend"] = r['趋势判断']

        # 亚盘信号
        if len(spread_rows) > 0:
            spread_away = spread_rows[spread_rows['选项'] == away]
            if len(spread_away) > 0:
                r = spread_away.iloc[0]
                summary["odds"]["spreadPoint"] = r.get('让球/大小球界线', '')
                summary["odds"]["spreadChange"] = round(r['变化百分比'], 2) if pd.notna(r.get('变化百分比')) else 0

        # Under信号
        if len(totals_rows) > 0:
            r = totals_rows.iloc[0]
            summary["odds"]["underChange"] = round(r['变化百分比'], 2) if pd.notna(r.get('变化百分比')) else 0

        odds_summary[mid] = summary

    return odds_summary


BETTING_STRATEGY = {
    "lottery": {
        "title": "体彩竞彩",
        "strategies": [
            {"rank": "🥇", "bet": "海地 vs 苏格兰", "market": "总进球 1球或2球", "odds": "~3.00", "stake": "40元", "stars": 5},
            {"rank": "🥈", "bet": "卡塔尔 vs 瑞士", "market": "让球(+2) 让平+让负", "odds": "3.75/2.62", "stake": "30元", "stars": 5},
            {"rank": "🥉", "bet": "苏格兰胜 × 瑞士让平/让负", "market": "2串1", "odds": "3.93", "stake": "24元", "stars": 4},
            {"rank": "4", "bet": "澳大利亚 vs 土耳其", "market": "总进球 1球或2球", "odds": "~3.00", "stake": "30元", "stars": 4},
            {"rank": "5", "bet": "巴西胜 × 土耳其胜", "market": "2串1", "odds": "2.62", "stake": "14元", "stars": 3},
            {"rank": "—", "bet": "🥇+🥈 混合过关", "market": "2串1", "odds": "~9.30", "stake": "20元", "stars": 4},
        ],
        "totalBudget": "250元 (单关100+过关100+进取50)",
        "scenarios": [
            {"name": "最优(四全中)", "prob": "~20%", "ret": "~230元", "pnl": "+130"},
            {"name": "大概率(①②④中)", "prob": "~55%", "ret": "~193元", "pnl": "+93"},
            {"name": "底线(仅①②中)", "prob": "~20%", "ret": "~99元", "pnl": "-1"},
        ]
    },
    "international": {
        "title": "国际博彩",
        "strategies": [
            {"rank": "🥇", "bet": "卡塔尔 vs 瑞士", "market": "Win to Nil (零封胜)", "odds": "~1.73", "stake": "中仓", "stars": 5, "note": "卡近5场4次被零封×瑞预选6场仅失2球"},
            {"rank": "🥇", "bet": "海地 vs 苏格兰", "market": "Under 2.5 球", "odds": "~1.83", "stake": "中仓", "stars": 5, "note": "全场最强信号: Under+9.9%买入"},
            {"rank": "🥈", "bet": "卡塔尔 vs 瑞士", "market": "Lay 卡塔尔胜", "odds": "@17.0", "stake": "🔴小仓5%", "stars": 4, "note": "交易所卖出: 卡胜率仅5.4%→94%盈利概率"},
            {"rank": "🥈", "bet": "巴西 vs 摩洛哥", "market": "BTTS Yes (双方进球)", "odds": "~1.80", "stake": "中仓", "stars": 3, "note": "巴边卫老+摩反击强→双方都能进"},
            {"rank": "🥉", "bet": "苏+瑞+土 亚盘", "market": "3串1 (亚盘热门方)", "odds": "6.08", "stake": "小仓", "stars": 3, "note": "1.87×1.97×1.65 三场不同组"},
            {"rank": "4", "bet": "海地 vs 苏格兰", "market": "Bet Builder: 胜+U2.5+角球", "odds": "~3.80", "stake": "小仓", "stars": 4, "note": "苏控球围攻→角球多"},
        ],
        "exclusive": ["Win to Nil", "BTTS", "交易所Lay盘", "Bet Builder", "亚盘精细档位"],
    }
}


def generate():
    print("📊 读取赔率数据...")
    odds = load_odds_data()

    # 按比赛时间排序
    match_list = sorted(odds.values(), key=lambda x: x.get('beijingTime', '99'))

    data = {
        "generatedAt": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "totalRecords": "96,560+",
        "totalSnapshots": "22",
        "matches": match_list,
        "standings": GROUP_STANDINGS,
        "betting": BETTING_STRATEGY,
    }

    js_content = "// 自动生成于 " + data["generatedAt"] + "\n"
    js_content += "const DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";"

    with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"✅ 数据已导出: {OUTPUT_JS}")
    print(f"   包含 {len(match_list)} 场比赛, {len(GROUP_STANDINGS)} 个小组")
    return OUTPUT_JS


def auto_fill_fields(match_name: str, odds_data: dict, xls_data: dict = None) -> dict:
    """
    P2: 仪表盘自动填充 —— 90%字段自动完成。

    仅需人工的字段: 战术分析(text)、球迷形象(text)、情景推演(text)

    返回可直接合并到 MATCH_INFO 的字典。
    """
    o = odds_data
    home, away = match_name.split('VS')

    # 隐含概率
    total = 1/o['home'] + 1/o['draw'] + 1/o['away']
    imp_h = (1/o['home'])/total*100
    imp_d = (1/o['draw'])/total*100
    imp_a = (1/o['away'])/total*100

    # 确定热门方
    if imp_h > imp_a:
        fav, fav_prob = home, imp_h
    else:
        fav, fav_prob = away, imp_a

    # 风险等级
    if fav_prob > 85: risk = "🟢 低"
    elif fav_prob > 65: risk = "🟡 中"
    else: risk = "🟠 高"

    # 大小球信号
    under_over = ""
    if xls_data:
        tot = xls_data.get('totals', {})
        tl = tot.get('line_analysis', {}) if tot else {}
        if tl.get('direction') == 'down':
            under_over = f"Under {tl.get('instant_line', '?')} (退盘信号)"
        else:
            under_over = f"Over/Under {tl.get('instant_line', '?')}"

    # 穿盘率
    cover_rate = ""
    if xls_data:
        hi = xls_data.get('handicap_index', {})
        if hi and hi.get('companies'):
            cover_rate = hi['companies'][0].get('win_prob', '')

    return {
        "matchName": f"{home} vs {away}",
        "homeFlag": "", "awayFlag": "",
        "beijingTime": "",
        "prediction": {
            "winner": f"{fav}胜" if fav_prob > 55 else "平局风险",
            "confidence": round(min(fav_prob, 90)),
            "underOver": under_over,
            "spread": f"{fav} {'-0.5' if fav_prob > 55 else '+0.5'}",
        },
        "riskLevel": risk,
        "riskNote": f"隐{imp_h:.0f}/{imp_d:.0f}/{imp_a:.0f} | 穿盘率{cover_rate}" if cover_rate else "",
        "implied": {"home": round(imp_h, 1), "draw": round(imp_d, 1), "away": round(imp_a, 1)},
    }


if __name__ == "__main__":
    generate()

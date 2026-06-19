# -*- coding: utf-8 -*-
"""
赔率变动分析报告生成器
每次赔率变化分析后自动运行,输出可读报告
用法: python odds_report.py
"""

import pandas as pd
import os
from datetime import datetime

DATA_DIR = r"C:\Users\A\PyCharmMiscProject"
CSV_FILE = os.path.join(DATA_DIR, "odds_trend_analysis_text.csv")
REPORT_FILE = os.path.join(DATA_DIR, "odds_change_report.md")



def generate():
    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')

    # 过滤已完赛的比赛ID
    COMPLETED_IDS = [
        "26634922d3f78c146440816023e40de8",  # 卡塔尔VS瑞士
        "f6c8748a16516e0998f95de14235432a",  # 巴西VS摩洛哥
        "5ae41a06735c926eeb7f74006933adce",  # 海地VS苏格兰
        "564084f52cc9f1abcc18187c168a7cdc",  # 澳大利亚VS土耳其
        "80d82d1113934bfbea4ce8daf37a2433",  # 墨西哥VS南非
        "384cbb5d76b535896a24fe65f93cfac8",  # 韩国VS捷克
        "d1f4f946c70a0b4e81f5d43e9d32361c",  # 加拿大VS波黑
        "c12986f447a515fbe641addd786dbb24",  # 美国VS巴拉圭
    ]
    df = df[~df['比赛ID'].isin(COMPLETED_IDS)]

    if df.empty:
        print("⚠️ 无活跃比赛数据")
        return

    # 筛选显著变动: h2h/spreads + >8% 或 交易所Lay盘 >5%
    sig = df[
        ((df['变化百分比'].abs() > 8) & (df['市场类型'].isin(['h2h', 'spreads']))) |
        ((df['变化百分比'].abs() > 5) & (df['市场类型'].isin(['h2h_lay'])))
    ]

    lines = []
    lines.append(f"# 赔率变动报告 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"")
    lines.append(f"**快照数**: {df['数据点数'].max()} | **总记录**: {len(df)} | **显著变动**: {len(sig)}条")
    lines.append(f"")

    # 按比赛分组
    for mid in sig['比赛ID'].unique():
        mdf = sig[sig['比赛ID'] == mid]
        home = mdf.iloc[0]['主队']
        away = mdf.iloc[0]['客队']
        match_name = f"{home} vs {away}"
        kickoff = mdf.iloc[0]['比赛开始时间']

        lines.append(f"## {match_name}")
        lines.append(f"开赛: {kickoff} | 变动条数: {len(mdf)}")
        lines.append(f"")

        for _, row in mdf.iterrows():
            direction = "⬆" if row['变化百分比'] > 0 else "⬇"
            lines.append(f"- {direction} **{row['博彩公司']}** {row['市场类型']} `{row['选项']}`")
            lines.append(f"  {row['起始赔率']:.2f} → {row['最新赔率']:.2f} ({row['变化百分比']:+.1f}%) | 趋势: {row['趋势判断']}")
        lines.append(f"")

    # P1-2: SB/Exchange背离检测
    lines.append(f"---")
    lines.append(f"## 🔍 SB/Exchange背离检测")
    lines.append(f"")
    sbx_divergences = []
    for mid in df['比赛ID'].unique():
        mdf = df[df['比赛ID'] == mid]
        sb_rows = mdf[(mdf['博彩公司'] == 'Betfair Sportsbook') & (mdf['市场类型'] == 'h2h')]
        ex_rows = mdf[(mdf['博彩公司'] == 'Betfair') & (mdf['市场类型'] == 'h2h')]
        for _, sb in sb_rows.iterrows():
            ex = ex_rows[ex_rows['选项'] == sb['选项']]
            if len(ex) > 0:
                sb_odds = sb['最新赔率']; ex_odds = ex.iloc[0]['最新赔率']
                diff_pct = (sb_odds - ex_odds) / ex_odds * 100
                if abs(diff_pct) > 5:
                    h = mdf.iloc[0]['主队']; a = mdf.iloc[0]['客队']
                    sbx_divergences.append(f"- ⚠️ **{h} vs {a}** `{sb['选项']}`: SB:{sb_odds:.2f} vs EX:{ex_odds:.2f} (差{diff_pct:+.1f}%)")
    if sbx_divergences:
        for d in sbx_divergences[:10]:
            lines.append(d)
        lines.append(f"")
        lines.append(f"> 差>5%可能表示传统庄家人为操作(诱盘)")
    else:
        lines.append(f"无显著SB/Exchange背离(>5%)")
    lines.append(f"")

    # 汇总
    lines.append(f"---")
    lines.append(f"*自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    report = '\n'.join(lines)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 报告已生成: {REPORT_FILE}")
    print(f"   活跃比赛变动: {len(sig)} 条显著信号 (阈值>5%)")

    # 打印摘要
    if len(sig) > 0:
        print(f"\n📊 显著变动摘要:")
        for mid in sig['比赛ID'].unique()[:6]:
            mdf = sig[sig['比赛ID'] == mid]
            h = mdf.iloc[0]['主队']
            a = mdf.iloc[0]['客队']
            top = mdf.iloc[0]
            print(f"  {h} vs {a}: {top['博彩公司']} {top['选项']} {top['变化百分比']:+.1f}%")


if __name__ == "__main__":
    generate()

# -*- coding: utf-8 -*-
"""
赛程自动生成器 — 从赔率CSV提取未来比赛 → 更新MATCH_SCHEDULE

用法:
  python generate_schedule.py                 # 预览
  python generate_schedule.py --update         # 更新赛前高频赔率.py
"""

import csv, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import OrderedDict

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")
TREND_FILE = PROJECT_DIR / "odds_trend_analysis_text.csv"
TARGET_FILE = PROJECT_DIR / "赛前高频赔率.py"

# 中文队名映射 (API英文名 → 中文名)
CN_NAMES = {
    'France': '法国', 'Senegal': '塞内加尔',
    'Iraq': '伊拉克', 'Norway': '挪威',
    'Argentina': '阿根廷', 'Algeria': '阿尔及利亚',
    'Austria': '奥地利', 'Jordan': '约旦',
    'Portugal': '葡萄牙', 'DR Congo': '民主刚果',
    'England': '英格兰', 'Croatia': '克罗地亚',
    'Ghana': '加纳', 'Panama': '巴拿马',
    'Uzbekistan': '乌兹别克斯坦', 'Colombia': '哥伦比亚',
    'Spain': '西班牙', 'Saudi Arabia': '沙特',
    'Belgium': '比利时', 'Iran': '伊朗',
    'Uruguay': '乌拉圭', 'Cape Verde': '佛得角',
    'New Zealand': '新西兰', 'Egypt': '埃及',
    'Brazil': '巴西', 'Haiti': '海地',
    'Scotland': '苏格兰', 'Morocco': '摩洛哥',
    'USA': '美国', 'Australia': '澳大利亚',
    'Turkey': '土耳其', 'Paraguay': '巴拉圭',
    'Netherlands': '荷兰', 'Sweden': '瑞典',
    'Germany': '德国', 'Ivory Coast': '科特迪瓦',
    'Ecuador': '厄瓜多尔', 'Curaçao': '库拉索',
    'Tunisia': '突尼斯', 'Japan': '日本',
    'Mexico': '墨西哥', 'South Korea': '韩国',
    'Czech Republic': '捷克', 'South Africa': '南非',
    'Canada': '加拿大', 'Bosnia & Herzegovina': '波黑',
    'Switzerland': '瑞士', 'Qatar': '卡塔尔',
}


def extract_future_matches() -> list:
    """从CSV提取未来比赛（去重·按时间排序）"""
    if not TREND_FILE.exists():
        print("趋势文件不存在")
        return []

    matches = OrderedDict()
    bj_tz = timezone(timedelta(hours=8))

    with open(TREND_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            home = row['主队']
            away = row['客队']
            key = f"{home}|{away}"
            if key in matches:
                continue

            try:
                dt_utc = datetime.fromisoformat(row['比赛开始时间'].replace('Z', '+00:00'))
            except ValueError:
                continue

            dt_bj = dt_utc.astimezone(bj_tz)
            matches[key] = {
                'home': home,
                'away': away,
                'dt_bj': dt_bj,
            }

    # 筛选未来比赛 (UTC+8)
    now = datetime.now(bj_tz)
    future = [(k, v) for k, v in matches.items() if v['dt_bj'] > now]
    future.sort(key=lambda x: x[1]['dt_bj'])

    return future


def generate_schedule_code(future_matches: list, days_ahead: int = 7) -> str:
    """生成MATCH_SCHEDULE代码"""
    lines = ["MATCH_SCHEDULE = ["]
    current_date = None

    bj_tz = timezone(timedelta(hours=8))
    cutoff = datetime.now(bj_tz) + timedelta(days=days_ahead)

    for key, info in future_matches:
        dt = info['dt_bj']
        if dt > cutoff:
            break

        home_cn = CN_NAMES.get(info['home'], info['home'])
        away_cn = CN_NAMES.get(info['away'], info['away'])

        date_str = dt.strftime("%m/%d")
        if date_str != current_date:
            current_date = date_str
            lines.append(f"    # {dt.strftime('%m月%d日')}")

        lines.append(
            f'    ({dt.month}, {dt.day}, {dt.hour:>2}, {dt.minute}, '
            f'"{home_cn}", "{away_cn}"),'
        )

    lines.append("]")
    return '\n'.join(lines)


def update_schedule_file(dry_run=True):
    """将生成的赛程写入 赛前高频赔率.py"""
    future = extract_future_matches()
    if not future:
        print("无未来比赛数据")
        return

    new_schedule = generate_schedule_code(future)

    if dry_run:
        print("将更新以下赛程:")
        print(new_schedule)
        print(f"\n共 {len([l for l in new_schedule.split(chr(10)) if '#' not in l and l.strip()]) - 2} 场比赛")
        return

    # 读取原文件
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换 MATCH_SCHEDULE 块
    pattern = r'MATCH_SCHEDULE = \[.*?\]'
    new_content = re.sub(pattern, new_schedule, content, flags=re.DOTALL)

    if new_content != content:
        with open(TARGET_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ MATCH_SCHEDULE 已更新")
    else:
        print("⚠️ 未找到MATCH_SCHEDULE块或内容相同")


if __name__ == '__main__':
    import sys
    do_update = '--update' in sys.argv

    if not do_update:
        future = extract_future_matches()
        if future:
            print("未来比赛 (从CSV提取):")
            print("=" * 55)
            for key, info in future[:16]:
                dt = info['dt_bj']
                home_cn = CN_NAMES.get(info['home'], info['home'])
                away_cn = CN_NAMES.get(info['away'], info['away'])
                print(f'{dt.strftime("%m/%d %H:%M")} | {home_cn:12s} vs {away_cn:12s}')
        else:
            print("无数据")

    update_schedule_file(dry_run=not do_update)

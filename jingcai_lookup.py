# -*- coding: utf-8 -*-
"""
P3-2: 竞彩数据查询辅助
生成标准化搜索链接和数据记录模板
用法: python jingcai_lookup.py
"""

from datetime import datetime

# 已知比赛→竞彩编号映射(需手动维护)
MATCHES = {
    "德国VS库拉索":     "周六00x",
    "荷兰VS日本":       "周六00x",
    "比利时VS埃及":     "周六00x",
    "西班牙VS佛得角":   "周六00x",
    "瑞典VS突尼斯":     "周六00x",
    "沙特VS乌拉圭":     "周六00x",
    "法国VS塞内加尔":   "周六00x",
    "伊朗VS新西兰":     "周六00x",
    "葡萄牙VS民主刚果": "周六00x",
    "奥地利VS约旦":     "周六00x",
    "阿根廷VS阿尔及利亚":"周六00x",
    "加纳VS巴拿马":     "周六00x",
    "科特迪瓦VS厄瓜多尔":"周六00x",
    "乌兹别克VS哥伦比亚":"周六00x",
}

SEARCH_BASE = "https://www.sohu.com/search?keyword="


def generate():
    print(f"# 竞彩数据查询 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    for match, code in MATCHES.items():
        home, away = match.split('VS')
        query = f"竞彩 {code} {home} {away} 赔率 胜平负 让球"
        url = SEARCH_BASE + query.replace(' ', '%20')
        print(f"## {match} ({code})")
        print(f"  [搜索]({url})")
        print(f"  开盘: ___ | 让球: ___ | 胜平负: ___/___/___")
        print(f"  让球赔率: 胜___ 平___ 负___")
        print()

    print("---")
    print("*自动生成·每次更新: python jingcai_lookup.py*")


if __name__ == "__main__":
    generate()

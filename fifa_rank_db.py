# -*- coding: utf-8 -*-
"""
FIFA排名+身价数据库 — 为 pre_match_report 自动填充实力参数

数据来源: FIFA 2026年6月排名(模拟) + Transfermarkt身价估算
用法:
  from fifa_rank_db import get_team_info
  info = get_team_info('法国')
  # → {'rank': 3, 'value_m': 1050, 'wc_apps': 16, ...}
"""

# ── 世界杯32强数据 ──
# rank: FIFA排名 | value_m: 身价(百万欧元) | wc_apps: 世界杯参赛次数
# confederation: 大洲 | notes: 备注

TEAM_DB = {
    # A组
    '墨西哥':    {'rank': 15, 'value_m': 350, 'wc_apps': 17, 'conf': 'CONCACAF'},
    '南非':      {'rank': 70, 'value_m': 120, 'wc_apps': 3,  'conf': 'CAF'},
    '韩国':      {'rank': 25, 'value_m': 280, 'wc_apps': 11, 'conf': 'AFC'},
    '捷克':      {'rank': 30, 'value_m': 200, 'wc_apps': 9,  'conf': 'UEFA'},

    # B组
    '加拿大':    {'rank': 40, 'value_m': 250, 'wc_apps': 3,  'conf': 'CONCACAF', 'host': 'co'},
    '波黑':      {'rank': 55, 'value_m': 100, 'wc_apps': 2,  'conf': 'UEFA'},
    '卡塔尔':    {'rank': 60, 'value_m': 80,  'wc_apps': 2,  'conf': 'AFC', 'host': 'co'},
    '瑞士':      {'rank': 15, 'value_m': 300, 'wc_apps': 12, 'conf': 'UEFA'},

    # C组
    '巴西':      {'rank': 3,  'value_m': 1200, 'wc_apps': 22, 'conf': 'CONMEBOL'},
    '摩洛哥':    {'rank': 20, 'value_m': 350, 'wc_apps': 6,  'conf': 'CAF'},
    '海地':      {'rank': 87, 'value_m': 25,  'wc_apps': 1,  'conf': 'CONCACAF'},
    '苏格兰':    {'rank': 30, 'value_m': 280, 'wc_apps': 8,  'conf': 'UEFA'},

    # D组
    '美国':      {'rank': 18, 'value_m': 450, 'wc_apps': 11, 'conf': 'CONCACAF', 'host': 'co'},
    '澳大利亚':  {'rank': 35, 'value_m': 180, 'wc_apps': 6,  'conf': 'AFC'},
    '土耳其':    {'rank': 32, 'value_m': 250, 'wc_apps': 3,  'conf': 'UEFA'},
    '巴拉圭':    {'rank': 48, 'value_m': 120, 'wc_apps': 8,  'conf': 'CONMEBOL'},

    # E组
    '德国':      {'rank': 10, 'value_m': 900, 'wc_apps': 20, 'conf': 'UEFA'},
    '科特迪瓦':  {'rank': 35, 'value_m': 300, 'wc_apps': 4,  'conf': 'CAF'},
    '厄瓜多尔':  {'rank': 28, 'value_m': 200, 'wc_apps': 5,  'conf': 'CONMEBOL'},
    '库拉索':    {'rank': 178,'value_m': 12,  'wc_apps': 1,  'conf': 'CONCACAF'},

    # F组
    '荷兰':      {'rank': 8,  'value_m': 800, 'wc_apps': 11, 'conf': 'UEFA'},
    '瑞典':      {'rank': 22, 'value_m': 350, 'wc_apps': 12, 'conf': 'UEFA'},
    '日本':      {'rank': 18, 'value_m': 320, 'wc_apps': 7,  'conf': 'AFC'},
    '突尼斯':    {'rank': 35, 'value_m': 80,  'wc_apps': 6,  'conf': 'CAF'},

    # G组
    '比利时':    {'rank': 5,  'value_m': 600, 'wc_apps': 14, 'conf': 'UEFA'},
    '伊朗':      {'rank': 20, 'value_m': 100, 'wc_apps': 6,  'conf': 'AFC'},
    '埃及':      {'rank': 32, 'value_m': 200, 'wc_apps': 4,  'conf': 'CAF'},
    '新西兰':    {'rank': 105,'value_m': 35,  'wc_apps': 3,  'conf': 'OFC'},

    # H组
    '西班牙':    {'rank': 2,  'value_m': 1000, 'wc_apps': 16, 'conf': 'UEFA'},
    '沙特':      {'rank': 50, 'value_m': 80,  'wc_apps': 7,  'conf': 'AFC'},
    '乌拉圭':    {'rank': 12, 'value_m': 450, 'wc_apps': 14, 'conf': 'CONMEBOL'},
    '佛得角':    {'rank': 67, 'value_m': 30,  'wc_apps': 1,  'conf': 'CAF'},

    # ── 6/17 新队 ──
    '法国':      {'rank': 3,  'value_m': 1050, 'wc_apps': 16, 'conf': 'UEFA'},
    '塞内加尔':  {'rank': 22, 'value_m': 300, 'wc_apps': 3,  'conf': 'CAF'},
    '伊拉克':    {'rank': 70, 'value_m': 30,  'wc_apps': 1,  'conf': 'AFC'},
    '挪威':      {'rank': 15, 'value_m': 400, 'wc_apps': 3,  'conf': 'UEFA'},
    '阿根廷':    {'rank': 1,  'value_m': 950, 'wc_apps': 18, 'conf': 'CONMEBOL'},
    '阿尔及利亚':{'rank': 35, 'value_m': 180, 'wc_apps': 5,  'conf': 'CAF'},
    '奥地利':    {'rank': 22, 'value_m': 280, 'wc_apps': 7,  'conf': 'UEFA'},
    '约旦':      {'rank': 85, 'value_m': 10,  'wc_apps': 1,  'conf': 'AFC'},

    # ── 6/18 新队 ──
    '葡萄牙':    {'rank': 7,  'value_m': 850, 'wc_apps': 8,  'conf': 'UEFA'},
    '民主刚果':  {'rank': 65, 'value_m': 100, 'wc_apps': 1,  'conf': 'CAF'},
    '英格兰':    {'rank': 4,  'value_m': 1310, 'wc_apps': 16, 'conf': 'UEFA'},
    '克罗地亚':  {'rank': 10, 'value_m': 400, 'wc_apps': 6,  'conf': 'UEFA'},
    '加纳':      {'rank': 60, 'value_m': 180, 'wc_apps': 4,  'conf': 'CAF'},
    '巴拿马':    {'rank': 55, 'value_m': 50,  'wc_apps': 2,  'conf': 'CONCACAF'},
    '乌兹别克斯坦':{'rank': 50, 'value_m': 85, 'wc_apps': 1,  'conf': 'AFC'},
    '哥伦比亚':  {'rank': 13, 'value_m': 300, 'wc_apps': 6,  'conf': 'CONMEBOL'},
}

# 英文名→中文名映射
EN_TO_CN = {
    'France': '法国', 'Senegal': '塞内加尔', 'Iraq': '伊拉克', 'Norway': '挪威',
    'Argentina': '阿根廷', 'Algeria': '阿尔及利亚', 'Austria': '奥地利', 'Jordan': '约旦',
    'Portugal': '葡萄牙', 'DR Congo': '民主刚果', 'England': '英格兰', 'Croatia': '克罗地亚',
    'Ghana': '加纳', 'Panama': '巴拿马', 'Uzbekistan': '乌兹别克斯坦', 'Colombia': '哥伦比亚',
    'Spain': '西班牙', 'Belgium': '比利时', 'Germany': '德国', 'Netherlands': '荷兰',
    'Brazil': '巴西', 'Mexico': '墨西哥', 'USA': '美国', 'Canada': '加拿大',
    'Uruguay': '乌拉圭', 'Japan': '日本', 'South Korea': '韩国', 'Iran': '伊朗',
    'Saudi Arabia': '沙特', 'Egypt': '埃及', 'Morocco': '摩洛哥', 'Tunisia': '突尼斯',
    'Ecuador': '厄瓜多尔', 'Scotland': '苏格兰', 'Turkey': '土耳其', 'Sweden': '瑞典',
    'Switzerland': '瑞士', 'Czech Republic': '捷克', 'Paraguay': '巴拉圭',
    'Qatar': '卡塔尔', 'Haiti': '海地', 'South Africa': '南非', 'Cape Verde': '佛得角',
    'New Zealand': '新西兰', 'Curaçao': '库拉索', 'Bosnia & Herzegovina': '波黑',
    'Australia': '澳大利亚', "Ivory Coast": '科特迪瓦',
}


def get_team_info(name: str) -> dict:
    """获取球队信息 (支持中/英文名)"""
    if name in TEAM_DB:
        return TEAM_DB[name]
    cn = EN_TO_CN.get(name, name)
    if cn in TEAM_DB:
        return TEAM_DB[cn]
    # 模糊匹配
    for k, v in TEAM_DB.items():
        if name in k or k in name:
            return v
    return {'rank': 50, 'value_m': 100, 'wc_apps': 0, 'conf': 'Unknown'}


def get_gap_info(home_name: str, away_name: str) -> dict:
    """计算两队实力差距"""
    h = get_team_info(home_name)
    a = get_team_info(away_name)
    rank_gap = abs(h['rank'] - a['rank'])
    value_ratio = max(h['value_m'], a['value_m']) / max(min(h['value_m'], a['value_m']), 1)
    wc_gap = abs(h['wc_apps'] - a['wc_apps'])

    # 自动分类
    if rank_gap > 60 and value_ratio > 25 and wc_gap > 15:
        level = 'extreme'
    elif rank_gap >= 25 and value_ratio >= 12:
        level = 'big'
    elif rank_gap >= 10 and value_ratio >= 3:
        level = 'moderate'
    else:
        level = 'close'

    return {
        'home': h, 'away': a,
        'rank_gap': rank_gap,
        'value_ratio': round(value_ratio, 1),
        'wc_gap': wc_gap,
        'gap_level': level,
        'is_host': h.get('host') == 'co' or a.get('host') == 'co',
    }

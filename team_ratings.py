# -*- coding: utf-8 -*-
"""
V3.28 48队三维实力评分 — 最终校准版

评分体系:
  攻击 (0.5-10): 精英俱乐部加权身价 + 赛季进球/国家队进球产出 + GPG锚定
  中场 (2.0-9.5): 静态评级 (五大联赛·欧冠经验·创造力·防守硬度·年龄结构)
  防守 (0.5-10): 防线质量加权身价 (≥30M×1.3分层) + 精英CB计数 + GK评分
  综合 = 攻击×0.35 + 中场×0.35 + 防守×0.30

版本演进:
  V3.25 → V3.26: 质量加权替代计数 (修复日本1.4·加纳10.0·科特迪瓦10.0)
  V3.26 → V3.27: 精英阈值1.30→1.15 + log底数调整 (阿根廷防守+1.0)
  V3.27 → V3.28: 公式收敛·无实质变化

用法:
  from team_ratings import TEAM_RATINGS, get_team_rating
  r = get_team_rating('苏格兰')  # → {'attack': 4.4, 'midfield': 6.0, 'defense': 3.2, 'overall': 4.6, 'tier': 'C'}
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TeamRating:
    """单队三维评分"""
    team: str
    fifa_rank: int
    total_value_m: float
    attack: float       # 0.5-10
    midfield: float     # 2.0-9.5
    defense: float      # 0.5-10
    overall: float      # 综合
    tier: str           # S/A/B+/B/C/D


# ═══════════════════════════════════════════════════════════════
# V3.28 最终评分表 (按FIFA排名排序)
# ═══════════════════════════════════════════════════════════════

TEAM_RATINGS: Dict[str, TeamRating] = {}

_RAW = [
    # rank, name,            valueM, atk,  mf,  def,  ov,  tier
    (1,   '阿根廷',          802,    7.2,  8.0,  6.3,  7.2,  'B+'),
    (2,   '西班牙',          1268,   9.2,  9.0,  9.1,  9.1,  'S'),
    (3,   '法国',            1556,   9.9,  9.5,  9.9,  9.8,  'S'),
    (4,   '英格兰',          1011,   9.5,  9.5,  6.7,  8.7,  'S'),
    (5,   '葡萄牙',          966,    8.7,  9.0,  9.5,  9.0,  'S'),
    (6,   '巴西',            909,    8.6,  8.0,  8.8,  8.4,  'A'),
    (7,   '摩洛哥',          470,    4.5,  6.5,  5.4,  5.5,  'B'),
    (8,   '荷兰',            839,    7.2,  7.0,  9.3,  7.8,  'A'),
    (9,   '比利时',          573,    7.1,  7.5,  5.8,  6.9,  'B+'),
    (10,  '德国',            988,    6.6,  8.5,  8.5,  7.8,  'A'),
    (11,  '克罗地亚',        362,    6.3,  7.5,  6.8,  6.9,  'B+'),
    (13,  '哥伦比亚',        301,    5.5,  6.5,  3.6,  5.3,  'C'),
    (14,  '墨西哥',          194,    4.0,  6.5,  3.3,  4.6,  'C'),
    (15,  '塞内加尔',        290,    6.4,  6.0,  3.9,  5.5,  'B'),
    (16,  '乌拉圭',          484,    5.9,  7.5,  5.2,  6.3,  'B'),
    (17,  '美国',            372,    4.9,  6.5,  3.7,  5.1,  'C'),
    (18,  '日本',            279,    5.1,  7.0,  4.7,  5.6,  'B'),
    (19,  '瑞士',            333,    4.5,  7.0,  5.2,  5.6,  'B'),
    (20,  '伊朗',            33,     2.6,  5.0,  0.5,  2.8,  'D'),
    (22,  '土耳其',          473,    6.1,  8.0,  4.6,  6.3,  'B'),
    (23,  '厄瓜多尔',        366,    5.1,  7.5,  6.2,  6.3,  'B'),
    (24,  '奥地利',          258,    5.9,  7.5,  3.4,  5.7,  'B'),
    (25,  '韩国',            140,    4.6,  7.0,  3.0,  5.0,  'C'),
    (27,  '澳大利亚',        72,     3.3,  5.5,  3.1,  4.0,  'C'),
    (28,  '阿尔及利亚',      258,    4.6,  6.0,  4.4,  5.0,  'C'),
    (29,  '埃及',            124,    6.0,  5.5,  1.8,  4.6,  'C'),
    (30,  '加拿大',          204,    4.2,  6.0,  4.9,  5.0,  'C'),
    (31,  '挪威',            471,    7.6,  7.0,  3.6,  6.2,  'B'),
    (33,  '科特迪瓦',        515,    5.6,  2.0,  4.5,  4.0,  'C'),
    (34,  '巴拿马',          26,     1.0,  4.5,  1.6,  2.4,  'D'),
    (38,  '瑞典',            369,    7.2,  5.5,  4.1,  5.7,  'B'),
    (40,  '捷克',            190,    3.8,  6.0,  4.3,  4.7,  'C'),
    (41,  '巴拉圭',          157,    3.1,  5.5,  3.1,  3.9,  'D'),
    (42,  '苏格兰',          208,    4.4,  6.0,  5.0,  5.1,  'C'),
    (45,  '突尼斯',          68,     3.4,  4.5,  1.9,  3.3,  'D'),
    (46,  '刚果(金)',        131,    2.7,  4.0,  3.7,  3.5,  'D'),
    (50,  '乌兹别克斯坦',    70,     2.3,  4.5,  4.3,  3.7,  'D'),
    (56,  '卡塔尔',          20,     2.6,  5.0,  0.5,  2.8,  'D'),
    (57,  '伊拉克',          24,     2.1,  4.0,  0.5,  2.3,  'D'),
    (60,  '南非',            45,     2.4,  4.0,  2.0,  2.8,  'D'),
    (61,  '沙特阿拉伯',      37,     3.2,  5.0,  1.9,  3.4,  'D'),
    # '沙特' alias handled in EN_TO_CN mapping, not as separate row
    (63,  '约旦',            20,     2.2,  3.5,  0.5,  2.2,  'D'),
    (64,  '波黑',            139,    3.6,  5.0,  3.2,  4.0,  'C'),
    (67,  '佛得角',          35,     1.7,  3.5,  2.0,  2.4,  'D'),
    (73,  '加纳',            200,    5.5,  5.5,  2.7,  4.7,  'C'),
    (82,  '库拉索',          25,     1.7,  2.0,  0.5,  1.4,  'D'),
    (83,  '海地',            56,     2.8,  3.5,  0.5,  2.4,  'D'),
    (85,  '新西兰',          38,     2.2,  4.0,  2.0,  2.8,  'D'),
]

for rank, name, val, atk, mf, df, ov, tier in _RAW:
    TEAM_RATINGS[name] = TeamRating(
        team=name, fifa_rank=rank, total_value_m=val,
        attack=atk, midfield=mf, defense=df, overall=ov, tier=tier,
    )


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def get_team_rating(team_name: str) -> Optional[TeamRating]:
    """获取单队三维评分·支持中英文名"""
    # 直接匹配
    if team_name in TEAM_RATINGS:
        return TEAM_RATINGS[team_name]
    # 别名
    if team_name == '沙特':
        return TEAM_RATINGS.get('沙特阿拉伯')
    # 英文→中文映射 (按需扩展)
    EN_TO_CN = {
        'Argentina': '阿根廷', 'Spain': '西班牙', 'France': '法国',
        'England': '英格兰', 'Portugal': '葡萄牙', 'Brazil': '巴西',
        'Morocco': '摩洛哥', 'Netherlands': '荷兰', 'Belgium': '比利时',
        'Germany': '德国', 'Croatia': '克罗地亚', 'Colombia': '哥伦比亚',
        'Mexico': '墨西哥', 'Senegal': '塞内加尔', 'Uruguay': '乌拉圭',
        'USA': '美国', 'Japan': '日本', 'Switzerland': '瑞士',
        'Iran': '伊朗', 'Turkey': '土耳其', 'Ecuador': '厄瓜多尔',
        'Austria': '奥地利', 'South Korea': '韩国', 'Australia': '澳大利亚',
        'Algeria': '阿尔及利亚', 'Egypt': '埃及', 'Canada': '加拿大',
        'Norway': '挪威', 'Ivory Coast': '科特迪瓦', 'Panama': '巴拿马',
        'Sweden': '瑞典', 'Czech': '捷克', 'Paraguay': '巴拉圭',
        'Scotland': '苏格兰', 'Tunisia': '突尼斯', 'DR Congo': '刚果(金)',
        'Uzbekistan': '乌兹别克斯坦', 'Qatar': '卡塔尔', 'Iraq': '伊拉克',
        'South Africa': '南非', 'Saudi Arabia': '沙特阿拉伯',
        'Jordan': '约旦', 'Bosnia': '波黑', 'Cape Verde': '佛得角',
        'Ghana': '加纳', 'Curacao': '库拉索', 'Haiti': '海地',
        'New Zealand': '新西兰',
    }
    cn = EN_TO_CN.get(team_name, team_name)
    return TEAM_RATINGS.get(cn)


def get_gap_analysis(home: str, away: str) -> dict:
    """两队三维差距分析"""
    h = get_team_rating(home)
    a = get_team_rating(away)
    if not h or not a:
        return {'error': f'未找到球队: {home if not h else ""} {away if not a else ""}'}
    return {
        'home': h.team, 'away': a.team,
        'attack_gap': round(h.attack - a.attack, 1),
        'midfield_gap': round(h.midfield - a.midfield, 1),
        'defense_gap': round(h.defense - a.defense, 1),
        'overall_gap': round(h.overall - a.overall, 1),
        'dominant_dimension': (
            'attack' if abs(h.attack - a.attack) >= max(abs(h.midfield - a.midfield), abs(h.defense - a.defense))
            else ('midfield' if abs(h.midfield - a.midfield) >= abs(h.defense - a.defense) else 'defense')
        ),
    }


def get_tier_teams(tier: str) -> list:
    """获取指定级别的所有球队"""
    return [r for r in TEAM_RATINGS.values() if r.tier == tier]


def print_all_ratings():
    """打印完整评分表"""
    tiers_order = {'S': [], 'A': [], 'B+': [], 'B': [], 'C': [], 'D': []}
    for r in sorted(TEAM_RATINGS.values(), key=lambda x: x.fifa_rank):
        tiers_order[r.tier].append(r)
    print(f"{'#':>3s} {'球队':<10s} {'身价M':>6s} {'攻击':>5s} {'中场':>5s} {'防守':>5s} {'综合':>5s}  Tier")
    print('─' * 65)
    for r in sorted(TEAM_RATINGS.values(), key=lambda x: x.fifa_rank):
        print(f'{r.fifa_rank:3d} {r.team:<10s} {r.total_value_m:6.0f} {r.attack:5.1f} {r.midfield:5.1f} {r.defense:5.1f} {r.overall:5.1f}  {r.tier}')
    print()
    for t in ['S', 'A', 'B+', 'B', 'C', 'D']:
        items = sorted(tiers_order[t], key=lambda x: -x.overall)
        if items:
            print(f'{t} ({len(items)}队): {", ".join(f"{r.team} {r.overall:.1f}" for r in items)}')


# ═══════════════════════════════════════════════════════════════
# 独立运行
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print_all_ratings()
    print()
    # 示例: 苏格兰VS摩洛哥差距分析
    gap = get_gap_analysis('苏格兰', '摩洛哥')
    print(f"苏格兰 vs 摩洛哥:")
    print(f"  攻击差: {gap['attack_gap']:+.1f} | 中场差: {gap['midfield_gap']:+.1f} | 防守差: {gap['defense_gap']:+.1f}")
    print(f"  综合差: {gap['overall_gap']:+.1f} | 最大差距维度: {gap['dominant_dimension']}")

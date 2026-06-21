# -*- coding: utf-8 -*-
"""
V3.29: V3.28评分 → 旧版API兼容层
替代 opponent_db._count_attacking_threat / _count_defensive_strength
所有决策树判断统一使用V3.28校准评分
"""

from team_ratings import get_team_rating


def count_attacking_threat(team: str, gap_level: str = 'moderate'):
    """
    V3.28替代 _count_attacking_threat.
    返回: (fw_count, mf_count, threat_score, scorers_list, fw_list)

    映射: V3.28 attack(0.5-10) → threat(1-15) 保持与旧版相近的量纲
    """
    r = get_team_rating(team)
    if not r:
        return (0, 0, 0.0, [], [])

    # V3.28 attack → threat (原生尺度 0.5-10)
    threat = round(r.attack, 1)
    # FW/MF count从team_ratings不可直接获取, 返回占位值
    # 需要这些count的代码路径应改用V3.28评分判断
    fw_count = 1 if r.attack >= 5.0 else 0
    mf_count = 1 if r.midfield >= 6.0 else 0

    return (fw_count, mf_count, threat, [], [])


def count_defensive_strength(team: str):
    """
    V3.28替代 _count_defensive_strength.
    返回: defense_score (0-10, 与V3.28 defense同尺度)
    """
    r = get_team_rating(team)
    if not r:
        return 0.0
    return r.defense


def get_midfield_rating(team: str):
    """V3.28替代 midfield_quality.MIDFIELD_RATING"""
    r = get_team_rating(team)
    if not r:
        return 5.0
    return r.midfield


# 别名：兼容 _count_attacking_threat 和 _count_defensive_strength 旧名称
_count_attacking_threat = count_attacking_threat
_count_defensive_strength = count_defensive_strength

# ═══════════════════════════════════════════════════════════════
# 阈值映射参考 (旧版 → V3.28)
# ═══════════════════════════════════════════════════════════════
#
# 旧版威胁值 (0-20) → V3.28 threat = attack × 1.5 (1.5-15)
#   旧 hthreat < 1.5  → V3.28 attack < 2.5
#   旧 hthreat <= 3.5 → V3.28 attack < 5.0
#   旧 hthreat >= 3.5 → V3.28 attack >= 5.0
#   旧 hthreat > 5.0  → V3.28 attack > 6.5
#
# 旧版防线值 (0-10) → V3.28 defense (0.5-10) 同尺度
#   旧 def < 1.0  → V3.28 defense < 2.0
#   旧 def >= 2.0 → V3.28 defense >= 3.0
#   旧 def >= 3.0 → V3.28 defense >= 5.0
#
# 差距阈值:
#   旧 atk_gap > 4.0  → V3.28 attack_gap > 2.5
#   旧 def_gap >= 3.0 → V3.28 defense_gap >= 2.0
#   旧 def_gap > 4.0  → V3.28 defense_gap > 2.5
#   旧 mf_gap > 3.0   → V3.28 midfield_gap > 2.0

# -*- coding: utf-8 -*-
"""
V3.3 纪律风险量化
评估红黄牌风险: 结合裁判出牌倾向 + 球队历史纪律记录

用法:
  from discipline_risk import analyze_discipline_risk
  result = analyze_discipline_risk(match_name, '法国', '塞内加尔')
"""

import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from config import CONF


@dataclass
class DisciplineRisk:
    """纪律风险评估结果"""
    match_name: str = ""
    referee_name: str = ""
    ref_avg_yellows: float = 3.5
    ref_avg_reds: float = 0.2
    home_red_risk: float = 0.0
    away_red_risk: float = 0.0
    expected_yellows: float = 3.5
    expected_reds: float = 0.2
    risk_level: str = 'low'
    confidence_adj: float = 0.0
    notes: List[str] = field(default_factory=list)


# 🆕 V3.3: 球队纪律档案 (基于回测DB和世界杯历史数据)
# 格式: yellows_per_match, reds_per_match, fouls_per_match
TEAM_DISCIPLINE: Dict[str, dict] = {
    '墨西哥':   {'yellows_per_match': 2.8, 'reds_per_match': 0.15, 'fouls_per_match': 16},
    '巴拉圭':   {'yellows_per_match': 2.5, 'reds_per_match': 0.12, 'fouls_per_match': 18},
    '南非':     {'yellows_per_match': 2.0, 'reds_per_match': 0.10, 'fouls_per_match': 15},
    '韩国':     {'yellows_per_match': 2.2, 'reds_per_match': 0.08, 'fouls_per_match': 14},
    '乌拉圭':   {'yellows_per_match': 2.6, 'reds_per_match': 0.12, 'fouls_per_match': 16},
    '阿根廷':   {'yellows_per_match': 2.4, 'reds_per_match': 0.10, 'fouls_per_match': 15},
    '克罗地亚': {'yellows_per_match': 2.0, 'reds_per_match': 0.08, 'fouls_per_match': 13},
    '_default': {'yellows_per_match': 2.0, 'reds_per_match': 0.08, 'fouls_per_match': 14},
}


def _get_team_discipline(team: str) -> dict:
    """获取球队纪律档案，支持模糊匹配"""
    for key in TEAM_DISCIPLINE:
        if key in team or team in key:
            return TEAM_DISCIPLINE[key]
    return TEAM_DISCIPLINE['_default'].copy()


def analyze_discipline_risk(match_name: str, home_team: str, away_team: str) -> DisciplineRisk:
    """
    分析一场比赛的纪律风险。

    组合计算:
    1. 裁判出牌倾向 (来自referee_analysis.py)
    2. 双方历史纪律记录
    3. 综合红牌概率 + 置信度调整
    """
    from referee_analysis import get_referee

    dr = DisciplineRisk(match_name=match_name)

    # 1. 裁判因素
    ref = get_referee(match_name)
    ref_yellow_factor = 1.0
    ref_red_factor = 1.0

    if ref:
        dr.referee_name = ref.name
        dr.ref_avg_yellows = ref.avg_yellows
        dr.ref_avg_reds = ref.avg_reds
        ref_yellow_factor = ref.avg_yellows / 3.5   # 3.5 = 基准值
        ref_red_factor = ref.avg_reds / 0.2          # 0.2 = 基准值

    # 2. 球队纪律因素
    home_disc = _get_team_discipline(home_team)
    away_disc = _get_team_discipline(away_team)

    team_yellow_factor = (home_disc['yellows_per_match'] + away_disc['yellows_per_match']) / 4.0
    team_red_factor = (home_disc['reds_per_match'] + away_disc['reds_per_match']) / 0.16

    # 3. 预期卡牌数
    dr.expected_yellows = round(3.5 * ref_yellow_factor * team_yellow_factor, 1)
    dr.expected_reds = round(0.2 * ref_red_factor * team_red_factor, 2)

    # 4. 红牌概率 (泊松近似)
    dr.home_red_risk = round(1 - math.exp(-home_disc['reds_per_match'] * ref_red_factor * 1.5), 2)
    dr.away_red_risk = round(1 - math.exp(-away_disc['reds_per_match'] * ref_red_factor * 1.5), 2)

    # 5. 风险等级
    overall_red_risk = max(dr.home_red_risk, dr.away_red_risk)
    if overall_red_risk >= 0.50:
        dr.risk_level = 'extreme'
        dr.notes.append(f'🟥 红牌风险极高({overall_red_risk:.0%}): 任一队红牌概率≥50%')
    elif overall_red_risk >= 0.30:
        dr.risk_level = 'high'
        dr.notes.append(f'🟥 红牌风险高({overall_red_risk:.0%})')
    elif overall_red_risk >= 0.15:
        dr.risk_level = 'medium'
        dr.notes.append(f'🟡 中等纪律风险({overall_red_risk:.0%})')
    else:
        dr.risk_level = 'low'

    if ref and ref.avg_reds >= 0.3:
        dr.notes.append(f'🟨 裁判{ref.name}红牌倾向偏高({ref.avg_reds:.1f}/场)')

    # 6. 置信度调整
    if overall_red_risk >= CONF.discipline_risk_threshold:
        risk_ratio = min(1.0, overall_red_risk / 0.5)
        adj_min, adj_max = CONF.discipline_risk_adj_range
        dr.confidence_adj = round(adj_min * risk_ratio, 1)

        if dr.confidence_adj < 0:
            dr.notes.append(
                f'纪律风险→置信度{dr.confidence_adj:+.0f}% (不确定性增加)'
            )

    return dr


# ── 命令行测试 ──
if __name__ == '__main__':
    # 测试已知高纪律风险比赛 (墨西哥)
    test = analyze_discipline_risk('墨西哥VS南非', '墨西哥', '南非')
    print(f"比赛: {test.match_name}")
    print(f"裁判: {test.referee_name or '未知'}")
    print(f"预期黄牌: {test.expected_yellows} | 预期红牌: {test.expected_reds}")
    print(f"主队红牌风险: {test.home_red_risk:.0%} | 客队红牌风险: {test.away_red_risk:.0%}")
    print(f"风险等级: {test.risk_level}")
    print(f"置信度调整: {test.confidence_adj:+.1f}%")
    for n in test.notes:
        print(f"  {n}")

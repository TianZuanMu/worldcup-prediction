# -*- coding: utf-8 -*-
"""
V3.0 替补深度分析 (P1#6)
5换时代·评估板凳深度对比赛末段的影响。

Features:
  - SUB_DEPTH_DB: 32队替补深度分类 (deep/moderate/shallow/unknown)
  - analyze_sub_depth(): 主场 vs 客场深度对比，含轮换风险与高温加成
  - 轮换风险>30% + 替补薄 → -5%; 轮换风险>30% + 替补深 → 无惩罚
  - 深度优势差距≥3分 → ±2%
"""

from dataclasses import dataclass, field
from typing import List
from config import CONF


# ══════════════════════════════════════════════════════════════
# 32队替补深度DB (5换时代)
# ══════════════════════════════════════════════════════════════
SUB_DEPTH_DB = {
    'deep': [
        '法国', '巴西', '英格兰', '葡萄牙', '阿根廷', '西班牙', '德国', '荷兰',
    ],
    'moderate': [
        '克罗地亚', '乌拉圭', '比利时', '日本', '韩国', '摩洛哥', '瑞士',
        '美国', '墨西哥',
    ],
    'shallow': [
        '民主刚果', '乌兹别克斯坦', '库拉索', '海地', '约旦', '巴拿马',
    ],
}

DEPTH_RATING = {
    'deep': 8,
    'moderate': 5,
    'shallow': 2,
    'unknown': 4,
}


@dataclass
class SubDepthResult:
    """替补深度分析结果"""
    home_depth: str = 'unknown'
    away_depth: str = 'unknown'
    home_rating: float = 4.0
    away_rating: float = 4.0
    differential: float = 0.0
    confidence_adj: float = 0.0
    notes: List[str] = field(default_factory=list)


def _get_depth(team: str) -> str:
    """查询球队替补深度级别"""
    for level, teams in SUB_DEPTH_DB.items():
        if team in teams:
            return level
    return 'unknown'


def analyze_sub_depth(
    home_team: str,
    away_team: str,
    rotation_risk_home: float = 0.0,
    rotation_risk_away: float = 0.0,
    is_hot_conditions: bool = False,
) -> SubDepthResult:
    """分析两队替补深度对比及其对置信度的影响。

    Args:
        home_team: 主队名称
        away_team: 客队名称
        rotation_risk_home: 主队轮换风险 (0~1, 来自赛程/出线形势)
        rotation_risk_away: 客队轮换风险 (0~1)
        is_hot_conditions: 是否高温天气 (>30°C或湿度>70%)

    Returns:
        SubDepthResult with depth levels, ratings, differential, confidence_adj, notes.

    Rules:
        - 轮换风险 > CONF.sub_impact_threshold (0.3) + 替补浅 → -5%
        - 轮换风险 > 0.3 + 替补深 → 无惩罚 (优质替补可用)
        - 深度评分差≥3分 → 深方 +2% (高温时额外+1%, 总计≤+5%)
        - 替补质量差距 > CONF.sub_quality_gap_threshold (1.5) → 警告记录
    """
    result = SubDepthResult(
        home_depth=_get_depth(home_team),
        away_depth=_get_depth(away_team),
    )
    result.home_rating = float(DEPTH_RATING.get(result.home_depth, 4))
    result.away_rating = float(DEPTH_RATING.get(result.away_depth, 4))
    result.differential = result.home_rating - result.away_rating

    # ── 轮换风险 × 替补深度 ──
    if rotation_risk_home > CONF.sub_impact_threshold:
        if result.home_depth == 'shallow':
            result.confidence_adj -= 5.0
            result.notes.append(
                f'{home_team}轮换风险{rotation_risk_home:.0%}+替补薄→-5%'
            )
        elif result.home_depth == 'deep':
            result.notes.append(
                f'{home_team}轮换风险{rotation_risk_home:.0%}但替补深→无影响'
            )
        else:
            # moderate or unknown → mild penalty
            result.confidence_adj -= 2.0
            result.notes.append(
                f'{home_team}轮换风险{rotation_risk_home:.0%}+替补{result.home_depth}→-2%'
            )

    if rotation_risk_away > CONF.sub_impact_threshold:
        if result.away_depth == 'shallow':
            result.confidence_adj -= 5.0
            result.notes.append(
                f'{away_team}轮换风险{rotation_risk_away:.0%}+替补薄→-5%'
            )
        elif result.away_depth == 'deep':
            result.notes.append(
                f'{away_team}轮换风险{rotation_risk_away:.0%}但替补深→无影响'
            )
        else:
            result.confidence_adj -= 2.0
            result.notes.append(
                f'{away_team}轮换风险{rotation_risk_away:.0%}+替补{result.away_depth}→-2%'
            )

    # ── 深度优势 (评分差≥3) ──
    if abs(result.differential) >= 3.0:
        adv_team = home_team if result.differential > 0 else away_team
        boost = 2.0

        # 高温增强: 深板凳在炎热天气下优势更大
        if is_hot_conditions:
            boost += 1.0
            result.notes.append(
                f'{adv_team}替补深度优势{abs(result.differential):+.0f}分+高温→+{boost:.0f}%'
            )
        else:
            result.notes.append(
                f'{adv_team}替补深度优势{abs(result.differential):+.0f}分→+{boost:.0f}%'
            )

        if result.differential > 0:
            result.confidence_adj += boost
        else:
            result.confidence_adj -= boost

    # ── 质量差距警告 ──
    if abs(result.differential) >= CONF.sub_quality_gap_threshold:
        gap_team = home_team if result.differential > 0 else away_team
        result.notes.append(
            f'替补质量差>{CONF.sub_quality_gap_threshold:.0f}档→{gap_team}深度优势显著'
        )

    # ── 边界限制 ──
    lo, hi = CONF.sub_depth_adj_range
    result.confidence_adj = max(lo, min(hi, result.confidence_adj))

    return result


# ── 测试 ──
if __name__ == '__main__':
    print("=" * 60)
    print("替补深度分析 测试")
    print("=" * 60)

    # 测试1: deep vs shallow, 无轮换
    r = analyze_sub_depth('葡萄牙', '民主刚果')
    print(f'\n[葡萄牙 vs 民主刚果]')
    print(f'  深度: {r.home_depth}({r.home_rating}) vs {r.away_depth}({r.away_rating})')
    print(f'  差分: {r.differential:+.0f}, 调整: {r.confidence_adj:+.0f}%')
    print(f'  备注: {r.notes}')

    # 测试2: shallow + 轮换风险
    r = analyze_sub_depth('约旦', '法国', rotation_risk_away=0.4)
    print(f'\n[约旦 vs 法国, 约旦轮换40%]')
    print(f'  深度: {r.home_depth}({r.home_rating}) vs {r.away_depth}({r.away_rating})')
    print(f'  差分: {r.differential:+.0f}, 调整: {r.confidence_adj:+.0f}%')
    print(f'  备注: {r.notes}')

    # 测试3: deep vs deep, 高温
    r = analyze_sub_depth('巴西', '英格兰', is_hot_conditions=True)
    print(f'\n[巴西 vs 英格兰, 高温]')
    print(f'  深度: {r.home_depth}({r.home_rating}) vs {r.away_depth}({r.away_rating})')
    print(f'  差分: {r.differential:+.0f}, 调整: {r.confidence_adj:+.0f}%')
    print(f'  备注: {r.notes}')

    # 测试4: 未知球队
    r = analyze_sub_depth('意大利', '尼日利亚', rotation_risk_home=0.35)
    print(f'\n[意大利 vs 尼日利亚, 意大利轮换35%]')
    print(f'  深度: {r.home_depth}({r.home_rating}) vs {r.away_depth}({r.away_rating})')
    print(f'  差分: {r.differential:+.0f}, 调整: {r.confidence_adj:+.0f}%')
    print(f'  备注: {r.notes}')

    print("\n" + "=" * 60)
    print("Done.")

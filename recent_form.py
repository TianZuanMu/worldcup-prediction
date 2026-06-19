"""
V2.10 近期状态分析
评估: 近5场战绩·对手实力加权·主力出战率·含金量打分
依赖: match_context.py (球队名映射)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import date as date_type, datetime
import json
from pathlib import Path

from config import CONF


@dataclass
class RecentMatch:
    """单场近期比赛"""
    opponent: str           # 对手(中文)
    result: str             # 'W'|'D'|'L'
    score: str              # '2-0'
    opponent_rank: int      # 对手FIFA排名
    home_away: str          # 'home'|'away'|'neutral'
    is_official: bool       # 正式比赛 vs 友谊赛
    key_players_played: int # 主力出战数 (0-11)
    date: str = ""


@dataclass
class RecentForm:
    """近期状态分析结果"""
    team: str
    matches: List[dict] = field(default_factory=list)
    form_string: str = ""           # 'WWDLW'
    points_last5: int = 0           # 近5场积分 (15分制)
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    opponent_quality_avg: float = 50  # 对手平均排名
    quality_weighted_score: float = 0.0  # 对手实力加权分 (0-10)
    key_player_participation: float = 1.0  # 主力出战率
    form_score: float = 5.0          # 综合状态分 (0-10)
    decay_applied: bool = False      # 是否应用了时间衰减加权
    opponent_quality_adjustment: float = 1.0  # 🆕 V3.3: 对手质量调整系数
    notes: List[str] = field(default_factory=list)


# ── 32队近5场战绩 (2026年6月至今) ──

RECENT_RESULTS: Dict[str, List[dict]] = {
    '法国': [
        {'opponent': '伊拉克', 'result': 'W', 'score': '3-0', 'opponent_rank': 70, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-15'},
        {'opponent': '意大利', 'result': 'W', 'score': '2-1', 'opponent_rank': 5, 'home_away': 'away', 'is_official': True, 'key_players': 9, 'date': '2026-06-08'},
        {'opponent': '荷兰', 'result': 'D', 'score': '1-1', 'opponent_rank': 7, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-06-02'},
        {'opponent': '科特迪瓦', 'result': 'W', 'score': '4-0', 'opponent_rank': 42, 'home_away': 'home', 'is_official': False, 'key_players': 8, 'date': '2026-05-25'},
        {'opponent': '比利时', 'result': 'W', 'score': '3-2', 'opponent_rank': 3, 'home_away': 'home', 'is_official': True, 'key_players': 11, 'date': '2026-03-28'},
    ],
    '塞内加尔': [
        {'opponent': '挪威', 'result': 'L', 'score': '0-1', 'opponent_rank': 15, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-15'},
        {'opponent': '摩洛哥', 'result': 'W', 'score': '2-1', 'opponent_rank': 6, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-06-07'},
        {'opponent': '佛得角', 'result': 'D', 'score': '1-1', 'opponent_rank': 65, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-01'},
        {'opponent': '加纳', 'result': 'W', 'score': '2-0', 'opponent_rank': 35, 'home_away': 'home', 'is_official': False, 'key_players': 7, 'date': '2026-05-24'},
        {'opponent': '埃及', 'result': 'L', 'score': '1-2', 'opponent_rank': 28, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-03-26'},
    ],
    '伊拉克': [
        {'opponent': '法国', 'result': 'L', 'score': '0-3', 'opponent_rank': 3, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-15'},
        {'opponent': '阿联酋', 'result': 'W', 'score': '1-0', 'opponent_rank': 68, 'home_away': 'away', 'is_official': True, 'key_players': 9, 'date': '2026-06-08'},
        {'opponent': '乌兹别克斯坦', 'result': 'D', 'score': '0-0', 'opponent_rank': 72, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-06-03'},
        {'opponent': '卡塔尔', 'result': 'L', 'score': '1-2', 'opponent_rank': 45, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-05-28'},
        {'opponent': '约旦', 'result': 'W', 'score': '2-1', 'opponent_rank': 85, 'home_away': 'home', 'is_official': True, 'key_players': 8, 'date': '2026-05-12'},
    ],
    '挪威': [
        {'opponent': '塞内加尔', 'result': 'W', 'score': '1-0', 'opponent_rank': 25, 'home_away': 'neutral', 'is_official': True, 'key_players': 11, 'date': '2026-06-15'},
        {'opponent': '苏格兰', 'result': 'W', 'score': '3-1', 'opponent_rank': 32, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-06-08'},
        {'opponent': '塞尔维亚', 'result': 'D', 'score': '1-1', 'opponent_rank': 22, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-06-02'},
        {'opponent': '瑞典', 'result': 'W', 'score': '2-0', 'opponent_rank': 18, 'home_away': 'home', 'is_official': False, 'key_players': 9, 'date': '2026-05-25'},
        {'opponent': '匈牙利', 'result': 'W', 'score': '4-1', 'opponent_rank': 38, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-03-25'},
    ],
    '阿根廷': [
        {'opponent': '奥地利', 'result': 'W', 'score': '2-1', 'opponent_rank': 22, 'home_away': 'neutral', 'is_official': True, 'key_players': 11, 'date': '2026-06-15'},
        {'opponent': '哥伦比亚', 'result': 'W', 'score': '3-1', 'opponent_rank': 8, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-06-07'},
        {'opponent': '智利', 'result': 'W', 'score': '2-0', 'opponent_rank': 19, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-01'},
        {'opponent': '乌拉圭', 'result': 'D', 'score': '1-1', 'opponent_rank': 10, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-03-27'},
        {'opponent': '巴西', 'result': 'W', 'score': '4-1', 'opponent_rank': 2, 'home_away': 'home', 'is_official': True, 'key_players': 11, 'date': '2026-03-22'},
    ],
    '阿尔及利亚': [
        {'opponent': '约旦', 'result': 'W', 'score': '1-0', 'opponent_rank': 85, 'home_away': 'neutral', 'is_official': True, 'key_players': 9, 'date': '2026-06-15'},
        {'opponent': '埃及', 'result': 'L', 'score': '0-2', 'opponent_rank': 28, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-06-08'},
        {'opponent': '加纳', 'result': 'D', 'score': '1-1', 'opponent_rank': 35, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-02'},
        {'opponent': '喀麦隆', 'result': 'W', 'score': '2-1', 'opponent_rank': 45, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-05-27'},
        {'opponent': '突尼斯', 'result': 'W', 'score': '1-0', 'opponent_rank': 40, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-03-21'},
    ],
    '奥地利': [
        {'opponent': '阿根廷', 'result': 'L', 'score': '1-2', 'opponent_rank': 1, 'home_away': 'neutral', 'is_official': True, 'key_players': 11, 'date': '2026-06-15'},
        {'opponent': '瑞士', 'result': 'W', 'score': '2-0', 'opponent_rank': 13, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-06-07'},
        {'opponent': '捷克', 'result': 'W', 'score': '3-1', 'opponent_rank': 31, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-02'},
        {'opponent': '波兰', 'result': 'D', 'score': '1-1', 'opponent_rank': 33, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-03-25'},
        {'opponent': '土耳其', 'result': 'W', 'score': '6-1', 'opponent_rank': 27, 'home_away': 'home', 'is_official': True, 'key_players': 11, 'date': '2026-03-21'},
    ],
    '约旦': [
        {'opponent': '阿尔及利亚', 'result': 'L', 'score': '0-1', 'opponent_rank': 35, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-15'},
        {'opponent': '沙特', 'result': 'D', 'score': '0-0', 'opponent_rank': 55, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-07'},
        {'opponent': '韩国', 'result': 'L', 'score': '0-3', 'opponent_rank': 24, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-06-02'},
        {'opponent': '阿联酋', 'result': 'W', 'score': '2-1', 'opponent_rank': 68, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-05-26'},
        {'opponent': '伊拉克', 'result': 'L', 'score': '1-2', 'opponent_rank': 70, 'home_away': 'away', 'is_official': True, 'key_players': 8, 'date': '2026-05-12'},
    ],
    # ═══ V2.10 补全: 6/15回测8队 ═══
    '德国': [
        {'opponent': '哥斯达黎加', 'result': 'W', 'score': '4-0', 'opponent_rank': 50, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-06-07'},
        {'opponent': '加纳', 'result': 'W', 'score': '2-0', 'opponent_rank': 35, 'home_away': 'home', 'is_official': False, 'key_players': 7, 'date': '2026-06-02'},
        {'opponent': '法国', 'result': 'L', 'score': '1-3', 'opponent_rank': 3, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-03-27'},
        {'opponent': '意大利', 'result': 'D', 'score': '2-2', 'opponent_rank': 5, 'home_away': 'home', 'is_official': True, 'key_players': 11, 'date': '2026-03-22'},
        {'opponent': '匈牙利', 'result': 'W', 'score': '5-0', 'opponent_rank': 38, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-18'},
    ],
    '荷兰': [
        {'opponent': '塞内加尔', 'result': 'W', 'score': '2-0', 'opponent_rank': 25, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-07'},
        {'opponent': '卡塔尔', 'result': 'W', 'score': '3-0', 'opponent_rank': 45, 'home_away': 'away', 'is_official': True, 'key_players': 9, 'date': '2026-06-02'},
        {'opponent': '西班牙', 'result': 'D', 'score': '2-2', 'opponent_rank': 1, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-03-28'},
        {'opponent': '德国', 'result': 'L', 'score': '1-2', 'opponent_rank': 4, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-03-21'},
        {'opponent': '比利时', 'result': 'W', 'score': '3-1', 'opponent_rank': 3, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-16'},
    ],
    '日本': [
        {'opponent': '科特迪瓦', 'result': 'W', 'score': '2-0', 'opponent_rank': 42, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-08'},
        {'opponent': '加纳', 'result': 'W', 'score': '4-1', 'opponent_rank': 35, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-03'},
        {'opponent': '韩国', 'result': 'W', 'score': '3-0', 'opponent_rank': 24, 'home_away': 'home', 'is_official': True, 'key_players': 11, 'date': '2026-03-27'},
        {'opponent': '沙特', 'result': 'W', 'score': '2-0', 'opponent_rank': 55, 'home_away': 'away', 'is_official': True, 'key_players': 9, 'date': '2026-03-22'},
        {'opponent': '澳大利亚', 'result': 'D', 'score': '1-1', 'opponent_rank': 30, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-03-18'},
    ],
    '科特迪瓦': [
        {'opponent': '日本', 'result': 'L', 'score': '0-2', 'opponent_rank': 20, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-08'},
        {'opponent': '喀麦隆', 'result': 'W', 'score': '1-0', 'opponent_rank': 45, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-02'},
        {'opponent': '法国', 'result': 'L', 'score': '0-4', 'opponent_rank': 3, 'home_away': 'away', 'is_official': False, 'key_players': 8, 'date': '2026-05-25'},
        {'opponent': '塞内加尔', 'result': 'D', 'score': '0-0', 'opponent_rank': 25, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-27'},
        {'opponent': '加纳', 'result': 'W', 'score': '2-1', 'opponent_rank': 35, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-22'},
    ],
    '厄瓜多尔': [
        {'opponent': '巴西', 'result': 'L', 'score': '0-1', 'opponent_rank': 2, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-06-07'},
        {'opponent': '乌拉圭', 'result': 'D', 'score': '0-0', 'opponent_rank': 10, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-06-02'},
        {'opponent': '哥伦比亚', 'result': 'L', 'score': '1-3', 'opponent_rank': 8, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-03-28'},
        {'opponent': '智利', 'result': 'W', 'score': '2-0', 'opponent_rank': 19, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-22'},
        {'opponent': '秘鲁', 'result': 'W', 'score': '1-0', 'opponent_rank': 45, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-03-15'},
    ],
    '瑞典': [
        {'opponent': '匈牙利', 'result': 'W', 'score': '2-0', 'opponent_rank': 38, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-06-08'},
        {'opponent': '苏格兰', 'result': 'W', 'score': '1-0', 'opponent_rank': 32, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-06-03'},
        {'opponent': '挪威', 'result': 'L', 'score': '0-2', 'opponent_rank': 15, 'home_away': 'away', 'is_official': False, 'key_players': 9, 'date': '2026-05-25'},
        {'opponent': '丹麦', 'result': 'D', 'score': '0-0', 'opponent_rank': 16, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-26'},
        {'opponent': '芬兰', 'result': 'W', 'score': '3-0', 'opponent_rank': 60, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-18'},
    ],
    '突尼斯': [
        {'opponent': '阿尔及利亚', 'result': 'L', 'score': '0-1', 'opponent_rank': 35, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-06-07'},
        {'opponent': '摩洛哥', 'result': 'L', 'score': '0-2', 'opponent_rank': 6, 'home_away': 'away', 'is_official': True, 'key_players': 11, 'date': '2026-06-02'},
        {'opponent': '埃及', 'result': 'D', 'score': '1-1', 'opponent_rank': 28, 'home_away': 'home', 'is_official': True, 'key_players': 9, 'date': '2026-05-28'},
        {'opponent': '加纳', 'result': 'L', 'score': '0-1', 'opponent_rank': 35, 'home_away': 'away', 'is_official': True, 'key_players': 10, 'date': '2026-03-21'},
        {'opponent': '马里', 'result': 'D', 'score': '0-0', 'opponent_rank': 50, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-15'},
    ],
    '库拉索': [
        {'opponent': '巴拿马', 'result': 'L', 'score': '0-3', 'opponent_rank': 60, 'home_away': 'away', 'is_official': True, 'key_players': 9, 'date': '2026-06-08'},
        {'opponent': '海地', 'result': 'L', 'score': '0-2', 'opponent_rank': 75, 'home_away': 'neutral', 'is_official': True, 'key_players': 10, 'date': '2026-06-01'},
        {'opponent': '加拿大', 'result': 'L', 'score': '0-4', 'opponent_rank': 25, 'home_away': 'away', 'is_official': True, 'key_players': 9, 'date': '2026-05-25'},
        {'opponent': '牙买加', 'result': 'L', 'score': '1-2', 'opponent_rank': 55, 'home_away': 'home', 'is_official': True, 'key_players': 10, 'date': '2026-03-20'},
        {'opponent': '古巴', 'result': 'L', 'score': '0-1', 'opponent_rank': 90, 'home_away': 'home', 'is_official': True, 'key_players': 8, 'date': '2026-03-15'},
    ],
}


def weigh_by_recency(matches: List[dict], half_life_days: float = None) -> List[float]:
    """
    Compute time-decay weights for recent matches.

    Each match gets weight = 2^(-days_ago / half_life), so a match
    exactly one half-life old contributes half as much as a match today.

    The single most recent match receives an additional multiplier
    (CONF.form_recent_weight_boost, default 2x).

    Args:
        matches: list of match dicts, each with an optional 'date' key (str YYYY-MM-DD).
        half_life_days: decay half-life in days. Defaults to CONF.form_decay_half_life_days (30).

    Returns:
        List of floats, one weight per match, same order as input.
        When no match carries a parseable date every weight is 1.0 (equal weighting,
        backward compatible).
    """
    if half_life_days is None:
        half_life_days = CONF.form_decay_half_life_days

    today = date_type.today()
    weights: List[float] = []
    has_dates = False

    for m in matches:
        date_str = m.get('date', '')
        if date_str:
            try:
                match_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                days_ago = max(0.0, (today - match_date).days)
                weight = 2.0 ** (-days_ago / half_life_days)
                has_dates = True
            except (ValueError, TypeError):
                weight = 1.0
        else:
            weight = 1.0

        weights.append(weight)

    # Backward compatibility: if no date data at all, equal weights
    if not has_dates:
        return [1.0] * len(matches)

    # Most recent match (highest raw weight = smallest days_ago) gets a bonus
    if len(weights) > 0:
        max_idx = max(range(len(weights)), key=lambda i: weights[i])
        weights[max_idx] *= CONF.form_recent_weight_boost

    return weights


def analyze_recent_form(team: str) -> RecentForm:
    """
    分析球队近期状态
    综合考虑: 战绩·对手实力·主力出战率·比赛含金量
    """
    results = RECENT_RESULTS.get(team, [])
    if not results:
        # 模糊匹配
        for key in RECENT_RESULTS:
            if team in key or key in team:
                results = RECENT_RESULTS[key]
                break

    if not results:
        return RecentForm(team=team, form_score=5.0, form_string='?????',
                          notes=['无近期数据·使用默认值'])

    recent5 = results[:5]

    # ── 时间衰减加权 ──
    decay_weights = weigh_by_recency(recent5)
    total_weight = sum(decay_weights)
    # decay was actually applied when weights differ from uniform 1.0
    decay_applied = any(abs(w - 1.0) > 0.001 for w in decay_weights)

    form = RecentForm(team=team, matches=recent5, decay_applied=decay_applied)

    # 1. 基础战绩 (15分制·时间衰减加权)
    form.form_string = ''.join([m['result'] for m in recent5])
    weighted_points = sum(
        {'W': 3, 'D': 1, 'L': 0}[m['result']] * w
        for m, w in zip(recent5, decay_weights)
    )
    # Normalize to 0-15 scale: weighted_points / total_weight * 5
    form.points_last5 = (weighted_points / total_weight) * 5 if total_weight > 0 else 0

    # 2. 进球/失球 (时间衰减加权)
    weighted_gf = 0.0
    weighted_ga = 0.0
    for m, w in zip(recent5, decay_weights):
        parts = m['score'].split('-')
        if len(parts) == 2:
            weighted_gf += int(parts[0]) * w
            weighted_ga += int(parts[1]) * w
    form.avg_goals_scored = weighted_gf / total_weight if total_weight > 0 else 0.0
    form.avg_goals_conceded = weighted_ga / total_weight if total_weight > 0 else 0.0

    # 3. 对手质量 (排名越低=越强, 时间衰减加权)
    weighted_rank = sum(m['opponent_rank'] * w for m, w in zip(recent5, decay_weights))
    form.opponent_quality_avg = weighted_rank / total_weight if total_weight > 0 else 50.0
    # 对手强(低排名) → 质量分高
    quality_bonus = max(0, (80 - form.opponent_quality_avg) / 15)  # 0-3分

    # 4. 含金量加权 (正式比赛=1.0, 友谊赛=0.5, 时间衰减加权)
    weighted_official = sum(
        (1.0 if m['is_official'] else 0.5) * w
        for m, w in zip(recent5, decay_weights)
    )
    quality_weight = weighted_official / total_weight if total_weight > 0 else 1.0

    # 5. 主力出战率 (时间衰减加权)
    weighted_participation = sum(
        (m['key_players'] / 11) * w
        for m, w in zip(recent5, decay_weights)
    )
    form.key_player_participation = weighted_participation / total_weight if total_weight > 0 else 1.0

    # 6. 综合分: 积分(50%) + 对手质量(20%) + 含金量(15%) + 主力率(15%)
    pts_score = (form.points_last5 / 15) * 5  # 0-5
    quality_score = quality_bonus  # 0-3
    official_score = quality_weight * 1.5  # 0-1.5
    player_score = form.key_player_participation * 0.5  # 0-0.5

    form.form_score = pts_score + quality_score + official_score + player_score
    form.quality_weighted_score = min(10, form.form_score)

    # 7. 备注
    if form.points_last5 >= 12:
        form.notes.append(f'近5场{form.points_last5:.1f}/15分·状态极佳')
    elif form.points_last5 >= 9:
        form.notes.append(f'近5场{form.points_last5:.1f}/15分·状态良好')
    elif form.points_last5 <= 3:
        form.notes.append(f'近5场仅{form.points_last5:.1f}/15分·状态低迷')

    if form.opponent_quality_avg < 30:
        form.notes.append(f'对手平均排名{form.opponent_quality_avg:.0f}·赛程强度高')
    elif form.opponent_quality_avg > 60:
        form.notes.append(f'对手平均排名{form.opponent_quality_avg:.0f}·赛程偏弱·含金量存疑')

    if form.key_player_participation < 0.7:
        form.notes.append(f'主力出战率仅{form.key_player_participation:.0%}·状态参考性降低')

    # 🆕 V3.3 P0-3: 应用对手质量调整 (修正"虐菜刷分"vs"强队输球"的偏差)
    adj_score, adj_factor = _adjust_form_for_opponent_quality(form.form_score, form.opponent_quality_avg)
    form.opponent_quality_adjustment = adj_factor
    if adj_factor != 1.0:
        form.form_score = adj_score
        form.quality_weighted_score = min(10, adj_score)

    return form


def _adjust_form_for_opponent_quality(form_score: float, opponent_quality_avg: float) -> tuple:
    """
    🆕 V3.3 P0-3: 按对手平均排名调整状态分

    问题: 巴拿马9.2(虐菜)vs加纳7.2(对手强), 状态分反向
    修复: 对手越弱→状态分打折, 对手越强→状态分溢价

    Returns:
        (adjusted_form_score, adjustment_factor)
    """
    if opponent_quality_avg > 50:       # weak opponents (rank 50+ = weaker)
        factor = 0.75
    elif opponent_quality_avg > 35:
        factor = 0.85
    elif opponent_quality_avg < 20:     # elite opponents (rank <20)
        factor = 1.15
    elif opponent_quality_avg < 30:
        factor = 1.05
    else:
        factor = 1.0

    adjusted = form_score * factor
    return adjusted, factor


def get_form_diff(home: str, away: str) -> dict:
    """
    两队近期状态对比
    Returns:
        {'home_form', 'away_form', 'form_edge': float, 'confidence_adj': float}
    """
    home_form = analyze_recent_form(home)
    away_form = analyze_recent_form(away)

    # 状态差距 (-5~+5, 正数=主队占优)
    edge = home_form.form_score - away_form.form_score

    # 置信度调整 (V3.0回测校准: 差≥3=100%准确 → 使用满权重)
    if abs(edge) >= 3.0:
        adj = 10 if edge > 0 else -10    # 100%准确·满权重
    elif abs(edge) >= 2.0:
        adj = 6 if edge > 0 else -6     # 强信号
    elif abs(edge) >= 1.0:
        adj = 3 if edge > 0 else -3     # 中等信号
    else:
        adj = 0                           # 均势·无预测力

    return {
        'home_form': home_form,
        'away_form': away_form,
        'form_edge': edge,
        'confidence_adj': adj,
        'home_adj_factor': home_form.opponent_quality_adjustment,
        'away_adj_factor': away_form.opponent_quality_adjustment,
        'note': f'{home}状态{home_form.form_score:.1f}/10 vs {away}{away_form.form_score:.1f}/10 → 差{edge:+.1f}'
    }


# ── V3.0 P0: 世界杯赛果自动回填 ──

def auto_fill_worldcup_results():
    """
    从 backtest/matches.json 自动提取世界杯完赛数据，
    注入 RECENT_RESULTS，解决32队无近期状态的问题。
    """
    import json
    from pathlib import Path
    from match_context import normalize_team_name
    from fifa_rank_db import get_team_info

    backtest_file = Path(__file__).parent / 'backtest' / 'matches.json'
    if not backtest_file.exists():
        return 0

    with open(backtest_file, 'r', encoding='utf-8') as f:
        matches = json.load(f)

    added = 0
    for m in matches:
        if m['actual']['result'] == 'pending':
            continue
        name = m['match_name']
        parts = name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
        if len(parts) != 2:
            continue
        home_raw = parts[0].strip()
        away_raw = parts[1].strip()
        home = normalize_team_name(home_raw)
        away = normalize_team_name(away_raw)

        score = m['actual']['score']
        try:
            hg, ag = map(int, score.split('-'))
        except (ValueError, AttributeError):
            continue

        result_home = 'W' if hg > ag else ('D' if hg == ag else 'L')
        result_away = 'W' if ag > hg else ('D' if ag == hg else 'L')

        # Get opponent ranks
        away_info = get_team_info(away) if get_team_info else {'rank': 50}
        home_info = get_team_info(home) if get_team_info else {'rank': 50}
        away_rank = away_info.get('rank', 50) if away_info else 50
        home_rank = home_info.get('rank', 50) if home_info else 50

        # Extract date from match ID or use kickoff schedule
        from match_context import get_match
        gm = get_match(match_name=name)
        match_date = '2026-06-17'  # default
        if gm:
            # Parse UTC date
            try:
                from datetime import datetime
                utc_str = gm.kickoff_utc.replace('Z', '+00:00')
                match_date = datetime.fromisoformat(utc_str).strftime('%Y-%m-%d')
            except Exception:
                pass

        # Build match entries
        home_entry = {
            'opponent': away, 'result': result_home, 'score': score,
            'opponent_rank': away_rank, 'home_away': 'home',  # World Cup: listed first = home
            'is_official': True, 'key_players': 10, 'date': match_date,
            '_source': 'worldcup_backtest',
        }
        away_entry = {
            'opponent': home, 'result': result_away, 'score': f'{ag}-{hg}',
            'opponent_rank': home_rank, 'home_away': 'away',
            'is_official': True, 'key_players': 10, 'date': match_date,
            '_source': 'worldcup_backtest',
        }

        # Merge into RECENT_RESULTS (prepend World Cup results)
        for team, entry in [(home, home_entry), (away, away_entry)]:
            if team not in RECENT_RESULTS:
                RECENT_RESULTS[team] = []
            # Avoid duplicates
            existing = RECENT_RESULTS[team]
            if not any(e.get('_source') == 'worldcup_backtest' and e['opponent'] == entry['opponent'] for e in existing):
                RECENT_RESULTS[team].insert(0, entry)
                added += 1

    # Sort: World Cup results first, then original data
    for team in RECENT_RESULTS:
        wc = [e for e in RECENT_RESULTS[team] if e.get('_source') == 'worldcup_backtest']
        orig = [e for e in RECENT_RESULTS[team] if e.get('_source') != 'worldcup_backtest']
        RECENT_RESULTS[team] = wc + orig

    return added


# Load from persistent cache (generated by import_recent_form.py)
def _load_cache():
    cache_file = Path(__file__).parent / 'recent_form_cache.json'
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            for team, matches in cached.items():
                if team not in RECENT_RESULTS:
                    RECENT_RESULTS[team] = []
                # Prepend cached data (only if not already loaded from this source)
                existing_opponents = {(m.get('opponent'), m.get('date')) for m in RECENT_RESULTS[team]}
                for m in matches:
                    key = (m.get('opponent'), m.get('date'))
                    if key not in existing_opponents:
                        RECENT_RESULTS[team].insert(0, m)
                        existing_opponents.add(key)
            return len(cached)
        except Exception:
            pass
    return 0

_cached_loaded = _load_cache()

# Auto-fill World Cup results from backtest (incremental)
_auto_filled = auto_fill_worldcup_results()


# ── 独立测试 ──
if __name__ == '__main__':
    test_teams = ['法国', '塞内加尔', '伊拉克', '挪威', '阿根廷', '阿尔及利亚', '奥地利', '约旦']

    for team in test_teams:
        form = analyze_recent_form(team)
        print(f"\n{'='*50}")
        print(f"  📈 {team} 近期状态: {form.form_string}  [衰减: {'ON' if form.decay_applied else 'OFF'}]")
        print(f"  积分: {form.points_last5:.1f}/15 | 进球: {form.avg_goals_scored:.1f}/场 | 失球: {form.avg_goals_conceded:.1f}/场")
        print(f"  对手均排名: {form.opponent_quality_avg:.0f} | 主力出战率: {form.key_player_participation:.0%}")
        print(f"  综合状态分: {form.form_score:.1f}/10")
        for n in form.notes:
            print(f"    → {n}")

    print(f"\n{'='*60}")
    print("  两队对比:")
    for home, away in [('法国', '塞内加尔'), ('伊拉克', '挪威'), ('阿根廷', '阿尔及利亚'), ('奥地利', '约旦')]:
        diff = get_form_diff(home, away)
        print(f"\n  {home} vs {away}")
        print(f"  {diff['note']}")
        print(f"  调整: {diff['confidence_adj']:+d}%")

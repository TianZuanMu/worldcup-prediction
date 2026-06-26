"""
V4.2 比分概率预测模块
基于泊松分布 + 预测方向 + 对手质量 + 三条件 + 实力差距 + 近期进球

⚠️ 重要: 本模块输出的 xG 是"模型校准后的预期进球",
  包含预测方向调整(Step 3), 不是"独立客观的预期进球"。
  用于交叉验证时, 使用 _calc_pure_xg() 获取未受预测标签污染的纯净 xG。

V4.2 重构 (vs V3.4):
  - P0: 饱和保护 — 累计调整上限30%·防多步叠加过度
  - P1: 穿盘率移除xG → 独立 cover_risk 输出
  - P3: sigmoid动态权重 — 替代硬阈值30%泊松融合
  - P4: 污染标记 — 明确区分"校准xG"与"纯净xG"
  - 管道从9步减为8步
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
import math
import json


@dataclass
class ScorePrediction:
    """单场比分预测"""
    match_name: str = ""
    expected_goals_home: float = 0.0
    expected_goals_away: float = 0.0
    top_scores: List[Tuple[str, float]] = field(default_factory=list)  # [(score, prob), ...]
    most_likely: str = ""          # 最可能比分
    most_likely_prob: float = 0.0
    home_win_prob: float = 0.0     # 主胜总概率
    draw_prob: float = 0.0         # 平局总概率
    away_win_prob: float = 0.0     # 客胜总概率
    total_goals_expected: float = 0.0
    adjustments: List[str] = field(default_factory=list)  # 🆕 调整日志
    # 🆕 V4.2 P1: 独立穿盘风险评估 (不修改xG)
    cover_risk: str = ''           # 'win_but_lose_spread' | 'cover_likely' | 'neutral'
    cover_risk_prob: float = 0.0   # 赢球输盘概率 0-100%


def _poisson_pmf(k: int, lam: float) -> float:
    """泊松概率质量函数 (避免scipy依赖)"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _implied_goals_from_odds(home_odds: float, draw_odds: float, away_odds: float,
                              totals_line: float = 2.5) -> Tuple[float, float]:
    """
    从1X2赔率推算两队预期进球 (λ_home, λ_away)

    方法:
    1. 从赔率反推隐含概率 (含水分)
    2. 去水分 (overround correction)
    3. 用真实概率估算进球差
    4. 用大小球盘口校准总进球数
    """
    if not home_odds or not draw_odds or not away_odds:
        return 1.3, 1.1

    # 1. 隐含概率
    imp_home = 1.0 / home_odds
    imp_draw = 1.0 / draw_odds
    imp_away = 1.0 / away_odds

    # 2. 去水分 (overround correction)
    overround = imp_home + imp_draw + imp_away
    prob_home = imp_home / overround
    prob_draw = imp_draw / overround
    prob_away = imp_away / overround

    # 3. 估算预期进球差 (基于胜率)
    goal_diff = (prob_home - prob_away) * 2.5

    # 4. 用大小球校准总进球
    total_expected = totals_line + 0.2

    # 5. 分配到两队
    lam_home = (total_expected + goal_diff) / 2.0
    lam_away = (total_expected - goal_diff) / 2.0

    # 边界约束
    lam_home = max(0.15, min(5.5, lam_home))
    lam_away = max(0.15, min(5.0, lam_away))

    return lam_home, lam_away


def _adjust_for_prediction_direction(lam_home: float, lam_away: float,
                                      prediction_text: str, gap_level: str,
                                      hot_side: str,
                                      home_odds: float = 0, away_odds: float = 0,  # 🆕 V3.33
                                      weak_team_threat: float = 1.0,  # 🆕 V3.33
                                      adjustments: List[str] = None) -> Tuple[float, float]:
    if adjustments is None:
        adjustments = []
    """
    🆕 V3.4: 根据V2.6规则预测方向调整λ

    核心: V3.33修正 — 当hot_side≠favorite时, "热门胜"应提升favorite的λ而非hot_side.
    西班牙VS沙特: hot_side=沙特(客), 预测=热门胜, 但favorite=西班牙(主)
    → 应提升西班牙λ, 而非旧逻辑提升沙特λ.
    """
    pred = prediction_text.lower() if prediction_text else ''

    # 🆕 V3.33: 确定预测赢家(赔率判定), 而非热方
    fav_is_home = (home_odds > 0 and away_odds > 0 and home_odds < away_odds)
    predicted_winner = 'home' if fav_is_home else ('away' if away_odds > 0 and home_odds > away_odds else hot_side)

    # 🆕 V3.33: 确定调整目标 — "热门胜"应提升预测赢家(favorite)的λ
    # 而非旧逻辑提升hot_side(可能是弱队, 如沙特)
    is_hot_win = '热门胜' in prediction_text or '实力碾压' in prediction_text
    is_hot_lose = '热门不胜' in prediction_text and '⚠️' not in prediction_text
    is_hot_still_win = '热门仍赢' in prediction_text

    if is_hot_win:
        # 热门胜: 提升预测赢家的λ
        if predicted_winner == 'home':
            lam_winner, lam_loser = lam_home, lam_away
            winner_side = 'home'
        else:
            lam_winner, lam_loser = lam_away, lam_home
            winner_side = 'away'
    else:
        # 热门不胜/热门仍赢: 仍使用hot_side作为调整目标
        if hot_side == 'home':
            lam_hot, lam_opp = lam_home, lam_away
        else:
            lam_hot, lam_opp = lam_away, lam_home

    # 🆕 V3.4: 所有调整基于调整目标方
    if '⚠️ 热门不胜' in prediction_text or ('热门不胜' in prediction_text and not is_hot_lose):
        pass  # handled below
    if '热门不胜' in prediction_text:
        # 热门不胜 → 热方进球减少, 对手进球增加
        if gap_level == 'close':
            f_hot, f_opp = 0.80, 1.15; note = '热门不胜(CLOSE)→热方-20%对手+15%'
        elif gap_level == 'big':
            f_hot, f_opp = 0.75, 1.20; note = '热门不胜(BIG)→热方-25%对手+20%'
        elif gap_level == 'moderate':
            f_hot, f_opp = 0.78, 1.18; note = '热门不胜(MOD)→热方-22%对手+18%'
        else:
            f_hot, f_opp = 0.85, 1.10; note = '热门不胜→热方-15%对手+10%'
        new_hot = lam_hot * f_hot
        new_opp = lam_opp * f_opp
        if new_hot >= new_opp:
            avg = (new_hot + new_opp) / 2
            new_hot = avg * 0.93; new_opp = avg * 1.07
            adjustments.append(f'🎯 {note}+逆市场修正·泊松对齐V2.6')
        else:
            adjustments.append(f'🎯 {note}')
        if hot_side == 'home':
            new_home, new_away = new_hot, new_opp
        else:
            new_home, new_away = new_opp, new_hot
        return new_home, new_away

    elif is_hot_still_win:
        new_hot = lam_hot * 0.92; new_opp = lam_opp * 1.05
        if new_opp > new_hot:
            avg = (new_hot + new_opp) / 2
            new_hot = avg * 1.06; new_opp = avg * 0.94
            adjustments.append('🎯 热门仍赢(逆市场)→泊松对齐V2.6')
        else:
            adjustments.append('🎯 热门仍赢(不穿盘)→热方-8%对手+5%')
        if hot_side == 'home':
            new_home, new_away = new_hot, new_opp
        else:
            new_home, new_away = new_opp, new_hot
        return new_home, new_away

    elif is_hot_win:
        # 🆕 V3.33: 热门胜 → 提升预测赢家(favorite)的λ
        is_strength_priority = '实力优先' in prediction_text
        # 🆕 V3.33: BIG差距+弱方攻击枯竭 → 增强强方加成
        if gap_level == 'big' and weak_team_threat < 1.0:
            factor_up = 1.25; factor_down = 0.75
            boost_note = 'BIG攻击枯竭→'
        elif gap_level == 'big':
            factor_up = 1.15; factor_down = 0.85
            boost_note = 'BIG→'
        else:
            factor_up = 1.10; factor_down = 0.90
            boost_note = ''
        new_winner = lam_winner * factor_up; new_loser = lam_loser * factor_down
        if new_loser > new_winner:
            # 泊松与方向背离 → 均值锚定
            if is_strength_priority:
                avg = (new_winner + new_loser) / 2
                new_winner = avg * 1.12; new_loser = avg * 0.88
                adjustments.append(f'🎯 {boost_note}实力优先→均值锚定·预测赢家60%权重')
            else:
                avg = (new_winner + new_loser) / 2
                new_winner = avg * 1.08; new_loser = avg * 0.92
                adjustments.append(f'🎯 {boost_note}热门胜(逆市场·预测赢家={predicted_winner})→泊松对齐V3.33')
        else:
            pct_up = int((factor_up - 1) * 100); pct_down = int((1 - factor_down) * 100)
            if is_strength_priority:
                adjustments.append(f'🎯 {boost_note}实力优先→预测赢家+{pct_up}%对手-{pct_down}%·方向一致')
            else:
                adjustments.append(f'🎯 {boost_note}热门胜→预测赢家({predicted_winner})+{pct_up}%对手-{pct_down}%')
        # 还原为主/客视角
        if predicted_winner == 'home':
            return new_winner, new_loser
        else:
            return new_loser, new_winner

    elif '客胜倾向' in prediction_text or ('客胜' in prediction_text and '⚠️' not in prediction_text):
        new_hot = lam_hot * 1.08; new_opp = lam_opp * 0.92
        adjustments.append('🎯 客胜倾向→客队(热方)+8%')
        if hot_side == 'home':
            return new_hot, new_opp
        else:
            return new_opp, new_hot

    elif '平局' in prediction_text or 'draw' in pred:
        avg = (lam_hot + lam_opp) / 2.0
        new_hot = avg * 1.05; new_opp = avg * 0.95
        adjustments.append('🎯 平局倾向→两队λ拉近')
        if hot_side == 'home':
            return new_hot, new_opp
        else:
            return new_opp, new_hot

    else:
        return lam_home, lam_away


def _adjust_for_opponent_quality(lam_strong: float, lam_weak: float,
                                  three_conditions_met: int,
                                  underdog_has_attackers: bool,
                                  underdog_giant_killer: float,  # 🆕 V3.12: float weight 0.0-1.0
                                  hot_team_rank: int,
                                  adjustments: List[str],
                                  weak_team_threat: float = 0.0) -> Tuple[float, float]:  # 🆕 V3.4
    """
    🆕 V3.4: 对手质量调整 (威胁感知)

    - 三条件全满足(3/3): 弱方进攻力决定惩罚幅度
    - 三条件2/3(有五大射手): 弱方能进球 → 弱方进攻提升
    - 巨人杀手血统: 弱方进球提升
    """
    # ── 三条件 ──
    if three_conditions_met == 3:
        # 🆕 V3.4: 威胁感知 — 弱方有攻击手时减轻惩罚
        if weak_team_threat >= 1.5:
            # 弱方有实质攻击力(如科特迪瓦迪亚洛) → 不惩罚
            adjustments.append('🛡️ 三条件全满足·弱方有攻击手→不调整')
        elif weak_team_threat >= 1.0:
            # 弱方有单个前锋 → 轻度惩罚
            lam_strong *= 1.04
            lam_weak *= 0.93
            adjustments.append(f'🛡️ 三条件全满足·弱方threat={weak_team_threat:.1f}→轻度-7%')
        elif weak_team_threat >= 0.5:
            # 弱方仅有中场威胁 → 中度惩罚
            lam_strong *= 1.07
            lam_weak *= 0.89
            adjustments.append(f'🛡️ 三条件全满足·弱方threat={weak_team_threat:.1f}→中度-11%')
        else:
            # 弱方无任何攻击手 → 重度惩罚
            lam_strong *= 1.10
            lam_weak *= 0.85
            adjustments.append('🛡️ 三条件全满足→弱方进攻极弱·强方+10%弱方-15%')
    elif three_conditions_met == 2:
        # 缺一项(通常是有五大射手) → 弱方有进球能力
        if underdog_has_attackers:
            lam_weak *= 1.20
            adjustments.append('⚔️ 弱方有五大射手→弱方进球+20%')

    # ── 巨人杀手 ──
    # 🆕 V3.12: 时间衰减权重 — >4年仅30%·>2年70%·近2年全额
    if underdog_giant_killer > 0:
        gk_pct = underdog_giant_killer * 12  # max 12% * weight
        lam_weak *= 1.0 + gk_pct / 100
        if underdog_giant_killer >= 0.9:
            adjustments.append(f'💀 弱方巨人杀手血统→弱方进球+{gk_pct:.0f}%')
        else:
            adjustments.append(f'💀 弱方巨人杀手血统(衰减→{underdog_giant_killer:.0%}权重)→弱方进球+{gk_pct:.0f}%')

    # ── 精英队(rank≤5)+温和过热 → 大比分 ──
    if hot_team_rank <= 5:
        lam_strong *= 1.08
        adjustments.append(f'⭐ 精英队(FIFA#{hot_team_rank})→强方+8%')

    return lam_strong, lam_weak


def _adjust_for_cover_rate(lam_strong: float, lam_weak: float, cover_rate: float,
                            gap_level: str, adjustments: List[str]) -> Tuple[float, float]:
    """
    🆕 V3.4: 穿盘率四级联动

    穿盘率越低 → 强方越难打穿 → 强方进球减少, 弱方进球增加
    """
    if gap_level == 'extreme':
        return lam_strong, lam_weak

    if cover_rate <= 0:
        return lam_strong, lam_weak

    if cover_rate < 20:
        factor_strong = 0.82
        factor_weak = 1.12
        label = f'极低穿盘({cover_rate:.0f}%<20%)'
    elif cover_rate < 30:
        factor_strong = 0.88
        factor_weak = 1.08
        label = f'低穿盘({cover_rate:.0f}%∈[20,30))'
    elif cover_rate < 40:
        factor_strong = 0.94
        factor_weak = 1.04
        label = f'中低穿盘({cover_rate:.0f}%∈[30,40))'
    elif cover_rate < 50:
        factor_strong = 0.97
        factor_weak = 1.02
        label = '中等穿盘(40-50%)'
    else:
        return lam_strong, lam_weak

    new_strong = lam_strong * factor_strong
    new_weak = lam_weak * factor_weak
    adjustments.append(f'📐 {label}→强方{int((factor_strong-1)*100):+d}%弱方{int((factor_weak-1)*100):+d}%')
    return new_strong, new_weak


def _calc_pure_xg(home_team: str, away_team: str, market_home_prob: float,
                  market_away_prob: float, gap_level: str) -> Tuple[float, float]:
    """
    🆕 V3.36: 纯净xG估算 — 仅基于实力+赔率·不读取任何大小球变量

    用途: 大小球背离检测时的参照基准。必须保持绝对纯净，避免递归。
    输入: 球队名·赔率隐含概率·差距级别
    输出: (home_raw_xg, away_raw_xg)
    """
    from opponent_db import opponent_quality
    home_data = opponent_quality(home_team)
    away_data = opponent_quality(away_team)

    home_gpg = home_data.get('pre_goals_per_game', 1.2) or 1.2
    away_gpg = away_data.get('pre_goals_per_game', 1.2) or 1.2

    # 基础λ = 实力场均 × 0.7 + 赔率隐含 × 0.3
    home_lam = home_gpg * 0.7 + market_home_prob * 3.0 * 0.3
    away_lam = away_gpg * 0.7 + market_away_prob * 3.0 * 0.3

    # BIG差距轻微调整
    if gap_level == 'big':
        home_lam *= 1.05
        away_lam *= 0.95
    elif gap_level == 'extreme':
        home_lam *= 1.10
        away_lam *= 0.90

    return max(0.15, home_lam), max(0.15, away_lam)


def _adjust_for_totals_prediction(lam_strong: float, lam_weak: float,
                                   totals_direction: str, totals_confidence: float,
                                   adjustments: List[str],
                                   diverge_level: str = 'none') -> Tuple[float, float]:
    """
    🆕 V3.4: 大小球预测联动比分
    🆕 V3.36: 背离仲裁 — 严重背离时跳过缩放·中度背离时缩放减半

    将独立的大小球模型结论反馈到泊松比分模型:
    - 大小球预测 ≠ 仅用原始盘口; 它综合了XLS趋势+6项修正因子
    - 当大小球模型高置信度预测小球/大球时, 调整总进球λ

    阈值: 置信度≥60%时触发, 避免弱信号干扰
    """
    if not totals_direction or totals_confidence < 60:
        return lam_strong, lam_weak

    # 🆕 V3.36: 背离时缩放力度控制
    if diverge_level == 'critical':
        adjustments.append('🔴 大小球与泊松严重背离→跳过大小球缩放')
        return lam_strong, lam_weak
    elif diverge_level == 'moderate':
        scale_mod = 0.5  # 缩放减半
        adjustments.append('🟡 大小球与泊松中度背离→缩放减半')
    else:
        scale_mod = 1.0

    if totals_direction == 'under':
        factor = 1.0 - (totals_confidence / 100) * 0.15 * scale_mod
        factor = max(0.82, factor)
        lam_strong *= factor
        lam_weak *= factor
        adjustments.append(f'⚽ 大小球模型→小球(信{totals_confidence:.0f}%)→总进球×{factor:.2f}')
    elif totals_direction == 'over':
        factor = 1.0 + (totals_confidence / 100) * 0.12 * scale_mod
        factor = min(1.15, factor)
        lam_strong *= factor
        lam_weak *= factor
        adjustments.append(f'⚽ 大小球模型→大球(信{totals_confidence:.0f}%)→总进球×{factor:.2f}')

    return lam_strong, lam_weak


# 🆕 V4.2 P1: 独立穿盘风险评估 (不修改xG)
def _calc_cover_risk(spread_rate: float, handicap: float,
                     xg_home: float, xg_away: float,
                     gap_level: str, prediction_direction: str) -> Tuple[str, float]:
    """
    独立计算赢球输盘风险。

    输入: 穿盘率 + 让球盘口 + xG差 + 差距级别 + 预测方向
    输出: (risk_label, risk_probability)
      - 'win_but_lose_spread': 大概率赢球输盘
      - 'cover_likely': 大概率穿盘
      - 'neutral': 无明显倾向
    """
    if not spread_rate or spread_rate <= 0:
        return 'neutral', 0.0

    # 赢球输盘概率 = 1 - 穿盘率 (简化模型)
    win_but_lose_prob = max(0, 100 - spread_rate)

    # xG修正: 如果预期进球差大但穿盘率低 → 赢球输盘风险更高
    xg_diff = abs(xg_home - xg_away)
    if xg_diff > 2.0 and spread_rate < 40:
        win_but_lose_prob = min(95, win_but_lose_prob + 10)
    elif xg_diff > 1.5 and spread_rate < 50:
        win_but_lose_prob = min(90, win_but_lose_prob + 5)

    # 小盘口(<1.0)信号不可靠 → 降级为neutral
    if abs(handicap) < 1.0:
        if win_but_lose_prob > 70:
            return 'win_but_lose_spread', win_but_lose_prob
        return 'neutral', win_but_lose_prob

    if win_but_lose_prob >= 60:
        return 'win_but_lose_spread', win_but_lose_prob
    elif spread_rate >= 60:
        return 'cover_likely', win_but_lose_prob
    return 'neutral', win_but_lose_prob


def _adjust_for_gap_level(lam_strong: float, lam_weak: float, gap_level: str,
                           adjustments: List[str]) -> Tuple[float, float]:
    """根据实力差距级别调整预期进球"""
    if gap_level == 'extreme':
        # 🆕 V3.4: EXTREME不再扩大差距, 而是使用中立高方差
        avg = (lam_strong + lam_weak) / 2.0
        # 保留一定差距但不过分
        new_strong = avg * 1.15
        new_weak = avg * 0.85
        adjustments.append('⚠️ EXTREME→中立高方差模型(强方+15%弱方-15%)')
        return max(0.15, new_strong), max(0.15, new_weak)
    elif gap_level == 'big':
        new_strong = lam_strong * 1.08
        new_weak = lam_weak * 0.92
        adjustments.append(f'📏 BIG差距→强方+8%弱方-8%')
        return new_strong, new_weak
    elif gap_level == 'close':
        # CLOSE比赛进球更接近
        avg = (lam_strong + lam_weak) / 2.0
        new_strong = lam_strong * 0.85 + avg * 0.15
        new_weak = lam_weak * 0.85 + avg * 0.15
        adjustments.append('📏 CLOSE→两队λ拉近15%')
        return new_strong, new_weak

    return lam_strong, lam_weak


def _adjust_for_recent_form(lam_strong: float, lam_weak: float,
                             strong_goals_scored: float, strong_goals_conceded: float,
                             weak_goals_scored: float, weak_goals_conceded: float,
                             adjustments: List[str]) -> Tuple[float, float]:
    """根据近期进球/失球数据微调预期进球"""
    # 强队进攻/弱队防守
    if strong_goals_scored > 0 and weak_goals_conceded > 0:
        ratio = strong_goals_scored / max(0.5, weak_goals_conceded)
        factor = 1.0 + (ratio - 1.0) * 0.20  # 20%权重 (V3.4: 从15%提升)
        lam_strong *= max(0.75, min(1.25, factor))
        if abs(factor - 1.0) > 0.02:
            adjustments.append(f'📈 强方进攻vs弱方防守→强方×{factor:.2f}')

    # 弱队进攻/强队防守
    if weak_goals_scored > 0 and strong_goals_conceded > 0:
        ratio = weak_goals_scored / max(0.5, strong_goals_conceded)
        factor = 1.0 + (ratio - 1.0) * 0.20
        lam_weak *= max(0.75, min(1.25, factor))
        if abs(factor - 1.0) > 0.02:
            adjustments.append(f'📈 弱方进攻vs强方防守→弱方×{factor:.2f}')

    return lam_strong, lam_weak


def _apply_goal_ceiling(lam_home: float, lam_away: float, gap_level: str) -> Tuple[float, float]:
    """边界约束 — V3.14: 世界杯正赛球队xG下限≥0.50"""
    if gap_level == 'extreme':
        lam_home = max(0.15, min(6.0, lam_home))
        lam_away = max(0.15, min(5.5, lam_away))
    else:
        # 🆕 V3.14: 世界杯正赛球队下限0.50 (即使最弱队也有定位球/反击机会)
        lam_home = max(0.50, min(5.5, lam_home))
        lam_away = max(0.50, min(5.0, lam_away))
    return lam_home, lam_away


def calculate_score_probs(lam_home: float, lam_away: float,
                           max_goals: int = 6) -> Tuple[List[Tuple[str, float]], dict]:
    """
    用泊松分布计算所有可能比分的概率

    Returns:
        scores: [(score_str, prob), ...] 按概率降序排列
        summary: {home_win, draw, away_win} 总概率
    """
    scores = []
    home_win = 0.0
    draw = 0.0
    away_win = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = _poisson_pmf(h, lam_home) * _poisson_pmf(a, lam_away)
            if prob < 0.0005:  # 过滤极低概率
                continue
            scores.append((f"{h}-{a}", prob))
            if h > a:
                home_win += prob
            elif h == a:
                draw += prob
            else:
                away_win += prob

    # 按概率降序
    scores.sort(key=lambda x: x[1], reverse=True)

    summary = {
        'home_win': home_win,
        'draw': draw,
        'away_win': away_win,
    }

    return scores, summary


def predict_score(match_name: str,
                  home_odds: float = 0, draw_odds: float = 0, away_odds: float = 0,
                  totals_line: float = 2.5,
                  totals_direction: str = '',      # 🆕 V3.4: 大小球预测方向
                  totals_confidence: float = 50,   # 🆕 V3.4: 大小球预测置信度
                  totals_diverge_level: str = 'none',  # 🆕 V3.36: 背离级别
                  gap_level: str = 'moderate',
                  home_is_strong: bool = True,
                  home_fifa_rank: int = 50, away_fifa_rank: int = 50,
                  home_goals_scored: float = 0, home_goals_conceded: float = 0,
                  away_goals_scored: float = 0, away_goals_conceded: float = 0,
                  cover_rate: float = 50,
                  handicap: float = 0.5,  # 🆕 V3.12: 亚盘让球数(穿盘率一致性校验)
                  prediction_direction: str = '',
                  hot_side: str = 'home',      # 🆕 V3.4: V2.6热方 (用于泊松对齐)
                  three_conditions_met: int = 0,
                  underdog_has_attackers: bool = False,
                  underdog_giant_killer: float = 0.0,  # 🆕 V3.12: float weight 0.0-1.0
                  hot_team_rank: int = 50,
                  weak_team_threat: float = 0.0) -> ScorePrediction:  # 🆕 V3.4
    """
    🆕 V3.4 主入口: 预测比分概率 (增强版)

    Args:
        match_name: 比赛名称
        home_odds/draw_odds/away_odds: 百家欧赔
        totals_line: 大小球盘口
        gap_level: 实力差距级别
        home_is_strong: 主队是否为强方
        home_fifa_rank/away_fifa_rank: FIFA排名
        home_goals_scored/home_goals_conceded: 主队近期场均进球/失球
        away_goals_scored/away_goals_conceded: 客队近期场均进球/失球
        cover_rate: 动态穿盘率
        prediction_direction: 预测方向文本 ("⚠️ 热门不胜", "热门胜", etc.)
        three_conditions_met: 三条件满足数 (0-3)
        underdog_has_attackers: 弱方是否有五大射手
        underdog_giant_killer: 弱方巨人杀手权重(V3.12: >4年衰减至0.3·近2年=1.0)
        hot_team_rank: 热方FIFA排名
    """
    sp = ScorePrediction(match_name=match_name)
    adjustments = []

    # 1. 从赔率推算基础预期进球
    if home_odds > 0 and draw_odds > 0 and away_odds > 0:
        lam_home, lam_away = _implied_goals_from_odds(
            home_odds, draw_odds, away_odds, totals_line
        )
    else:
        lam_home, lam_away = 1.5, 1.0
        if not home_is_strong:
            lam_home, lam_away = lam_away, lam_home

    # 确定强方/弱方λ
    if home_is_strong:
        lam_strong, lam_weak = lam_home, lam_away
    else:
        lam_strong, lam_weak = lam_away, lam_home

    # 🆕 V4.2: 保存初始λ快照 (供饱和保护使用)
    lam_home_initial = lam_home
    lam_away_initial = lam_away

    # 2. 实力差距调整
    lam_strong, lam_weak = _adjust_for_gap_level(lam_strong, lam_weak, gap_level, adjustments)

    # 3. 🆕 预测方向接入 (最重要·V3.4: 基于V2.6热方而非市场强方)
    lam_home, lam_away = _adjust_for_prediction_direction(
        lam_home, lam_away, prediction_direction, gap_level,
        hot_side, home_odds, away_odds,  # 🆕 V3.33
        weak_team_threat,  # 🆕 V3.33
        adjustments
    )
    # 更新强/弱方映射 (调整后可能反转)
    if home_is_strong:
        lam_strong, lam_weak = lam_home, lam_away
    else:
        lam_strong, lam_weak = lam_away, lam_home

    # 4. 🆕 对手质量
    lam_strong, lam_weak = _adjust_for_opponent_quality(
        lam_strong, lam_weak, three_conditions_met,
        underdog_has_attackers, underdog_giant_killer,
        hot_team_rank, adjustments, weak_team_threat
    )

    # 5. 🆕 V4.2: 穿盘率不再修改xG → 独立输出 cover_risk
    # (原 _adjust_for_cover_rate 已移除, 替换为独立 _calc_cover_risk)

    # 5b. 🆕 V3.4/V3.36: 大小球预测联动 (独立模型结论反馈到比分)
    lam_strong, lam_weak = _adjust_for_totals_prediction(
        lam_strong, lam_weak, totals_direction, totals_confidence, adjustments,
        diverge_level=totals_diverge_level  # 🆕 V3.36
    )

    # 6. 近期状态调整 (强/弱方视角)
    if home_is_strong:
        lam_strong, lam_weak = _adjust_for_recent_form(
            lam_strong, lam_weak,
            home_goals_scored, home_goals_conceded,
            away_goals_scored, away_goals_conceded,
            adjustments
        )
    else:
        lam_strong, lam_weak = _adjust_for_recent_form(
            lam_strong, lam_weak,
            away_goals_scored, away_goals_conceded,
            home_goals_scored, home_goals_conceded,
            adjustments
        )

    # 7. FIFA排名调整 (细化)
    if home_fifa_rank > 0 and away_fifa_rank > 0:
        rank_diff = abs(home_fifa_rank - away_fifa_rank)
        if rank_diff > 60:
            bonus = 0.25
        elif rank_diff > 40:
            bonus = 0.18
        elif rank_diff > 25:
            bonus = 0.10
        elif rank_diff > 10:
            bonus = 0.05
        else:
            bonus = 0

        if bonus > 0:
            if home_fifa_rank < away_fifa_rank:
                lam_home += bonus
                adjustments.append(f'📊 FIFA排名差{rank_diff}→主队+{bonus:.2f}λ')
            else:
                lam_away += bonus
                adjustments.append(f'📊 FIFA排名差{rank_diff}→客队+{bonus:.2f}λ')

    # 重新分配回home/away
    if home_is_strong:
        lam_home, lam_away = lam_strong, lam_weak
    else:
        lam_home, lam_away = lam_weak, lam_strong

    # 🆕 V3.8: 零威胁保护 — attack_threat<0.5的球队预期进球封顶0.3
    try:
        from opponent_db import _count_attacking_threat
        _parts_n = match_name.split('VS')
        _hn = _parts_n[0].strip(); _an = _parts_n[-1].strip()
        _, _, home_thr, _, _ = _count_attacking_threat(_hn, gap_level or 'moderate')
        _, _, away_thr, _, _ = _count_attacking_threat(_an, gap_level or 'moderate')
        if home_thr < 0.5:
            lam_home = min(lam_home, 0.3)
            adjustments.append(f'🛡️ {_hn}攻击枯竭(thr={home_thr:.1f})→预期进球封顶0.3')
        if away_thr < 0.5:
            lam_away = min(lam_away, 0.3)
            adjustments.append(f'🛡️ {_an}攻击枯竭(thr={away_thr:.1f})→预期进球封顶0.3')
        # 🆕 V4.2 P3: 泊松-实力融合 — sigmoid动态权重 (替代硬阈值30%)
        from opponent_db import _count_defensive_strength
        home_def = _count_defensive_strength(_hn); away_def = _count_defensive_strength(_an)
        # 实力λ: 攻击/对手防线 × 联赛均值1.4
        str_lam_home = (home_thr / max(away_def, 1.0)) * 1.4 if home_thr > 0 else lam_home
        str_lam_away = (away_thr / max(home_def, 1.0)) * 1.4 if away_thr > 0 else lam_away
        # sigmoid动态融合: 偏离越大, 实力权重越高 (连续·无硬边界)
        for lam_key, lam_market, lam_strength in [('主', lam_home, str_lam_home),
                                                   ('客', lam_away, str_lam_away)]:
            if lam_market > 0.05:
                deviation = abs(lam_market - lam_strength) / lam_market
                # sigmoid: 偏离30%→市场73%·偏离40%→市场50%·偏离50%→市场27%
                weight_market = 1.0 / (1.0 + math.exp((deviation - 0.4) * 10))
                weight_strength = max(0.05, 1.0 - weight_market)  # 5%最小实力权重
                if weight_strength > 0.06:  # 仅当实力模型有实质贡献时记录
                    old_lam = lam_market
                    new_lam = lam_market * weight_market + lam_strength * weight_strength
                    adjustments.append(
                        f'⚡ 泊松融合: {lam_key}λ {old_lam:.2f}→{new_lam:.2f}'
                        f'(市场{weight_market:.0%}+实力{weight_strength:.0%}·偏离{deviation:.0%})'
                    )
                    if lam_key == '主':
                        lam_home = new_lam
                    else:
                        lam_away = new_lam
    except Exception:
        pass

    # 边界约束
    if gap_level == 'extreme':
        lam_home, lam_away = _apply_goal_ceiling(lam_home, lam_away, 'extreme')
    else:
        lam_home, lam_away = _apply_goal_ceiling(lam_home, lam_away, gap_level)

    # 🆕 V3.15: 弱队xG反直觉检查 — 弱队预期进球不应超过强队
    if home_is_strong and lam_away > lam_home:
        lam_away = lam_home * 0.90
        adjustments.append(f'⚠️ 反直觉约束: 弱队xG({lam_away:.2f})→强队xG的90%({lam_away:.2f})')
    elif not home_is_strong and lam_home > lam_away:
        lam_home = lam_away * 0.90
        adjustments.append(f'⚠️ 反直觉约束: 弱队xG({lam_home:.2f})→强队xG的90%({lam_home:.2f})')

    # 🆕 V3.19: xG软约束 — >4.0时截断+平滑化防过拟合
    xg_soft_capped = False
    if lam_home > 4.0:
        lam_home = 4.0 + (lam_home - 4.0) * 0.3  # 4.0以上只保留30%
        xg_soft_capped = True
    if lam_away > 4.0:
        lam_away = 4.0 + (lam_away - 4.0) * 0.3
        xg_soft_capped = True
    if xg_soft_capped:
        adjustments.append('⚠️ xG软约束: >4.0截断30%·防乘法链过拟合·比分仅供参考')

    # 🆕 V4.2 P0: 饱和保护 — 累计调整幅度上限30%
    MAX_TOTAL_ADJUSTMENT = 0.30
    for lam_key, lam_val, initial in [('主', lam_home, lam_home_initial),
                                       ('客', lam_away, lam_away_initial)]:
        if initial > 0:
            change = abs(lam_val / initial - 1.0)
            if change > MAX_TOTAL_ADJUSTMENT:
                sign = 1 if lam_val > initial else -1
                capped = initial * (1.0 + MAX_TOTAL_ADJUSTMENT * sign)
                adjustments.append(
                    f'🛑 饱和保护: {lam_key}λ累计调整{change:.0%}>{MAX_TOTAL_ADJUSTMENT:.0%}'
                    f'·{lam_val:.2f}→截断至{capped:.2f}'
                )
                if lam_key == '主':
                    lam_home = capped
                else:
                    lam_away = capped

    sp.expected_goals_home = round(lam_home, 2)
    sp.expected_goals_away = round(lam_away, 2)
    sp.total_goals_expected = round(lam_home + lam_away, 2)
    sp.adjustments = adjustments

    # 🆕 V4.2 P1: 独立穿盘风险评估 (不修改xG)
    sp.cover_risk, sp.cover_risk_prob = _calc_cover_risk(
        cover_rate, handicap, lam_home, lam_away,
        gap_level, prediction_direction
    )

    # 8. 计算泊松概率 (EXTREME用更大范围+混合模型)
    max_g = 8 if gap_level == 'extreme' else 6
    scores, summary = calculate_score_probs(lam_home, lam_away, max_goals=max_g)

    # 🆕 V3.6: EXTREME双峰分布 — 混合低分意外场景
    if gap_level == 'extreme':
        # 低分场景权重30%: 0-0, 1-0, 0-1, 1-1
        low_score_weights = {
            '0-0': 0.08, '1-0': 0.07, '0-1': 0.05,
            '1-1': 0.05, '0-0': 0.03, '2-0': 0.02,
        }
        # 将泊松结果×0.70 + 低分场景×0.30
        blended = {}
        for s, p in scores:
            blended[s] = p * 0.70
        for s, w in low_score_weights.items():
            blended[s] = blended.get(s, 0) + w * 0.30
        scores = sorted(blended.items(), key=lambda x: x[1], reverse=True)
        # 重算summary
        home_win = draw = away_win = 0.0
        for s, p in scores:
            h, a = s.split('-')
            if int(h) > int(a): home_win += p
            elif int(h) == int(a): draw += p
            else: away_win += p
        summary = {'home_win': home_win, 'draw': draw, 'away_win': away_win}
        adjustments.append('⚠️ EXTREME混合模型: 泊松70%+低分场景30%')

    # 🆕 V3.6: 崩盘因子 — 三条件全满足+精英队+高战意 → 大比分风险
    if (three_conditions_met == 3 and hot_team_rank <= 10 and
        '濒临淘汰' in prediction_direction):
        # 弱方可能崩盘 → 加入更大比分
        blowout_scores = {}
        if home_is_strong:
            for g in range(3, 7):
                blowout_scores[f'{g}-0'] = 0.03
                blowout_scores[f'{g}-1'] = 0.02
        else:
            for g in range(3, 7):
                blowout_scores[f'0-{g}'] = 0.03
                blowout_scores[f'1-{g}'] = 0.02
        blended2 = {}
        for s, p in scores:
            blended2[s] = p * 0.88
        for s, w in blowout_scores.items():
            blended2[s] = blended2.get(s, 0) + w * 0.12
        scores = sorted(blended2.items(), key=lambda x: x[1], reverse=True)
        adjustments.append('💥 崩盘因子: 三条件全满足+精英队→大比分风险+12%')

    # 🆕 V3.12: 穿盘率-比分一致性校验
    # 若穿盘率<40%, 穿盘比分(goal_diff > handicap)应被降权
    cover_penalty_applied = False
    if cover_rate < 40 and handicap >= 0.5 and len(scores) >= 3:
        penalized_scores = []
        for s, p in scores:
            parts = s.split('-')
            try:
                hg, ag = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                penalized_scores.append((s, p))
                continue
            diff = hg - ag
            # 确定穿盘方向: 主队强方→hg-ag>handicap穿盘; 客队强方→ag-hg>handicap穿盘
            if home_is_strong:
                covers = diff > handicap
            else:
                covers = (ag - hg) > handicap
            if covers:
                # 穿盘比分: 概率×0.65 (降低35%)
                penalized_scores.append((s, p * 0.65))
            else:
                penalized_scores.append((s, p))
        # 重新归一化
        total_p = sum(p for _, p in penalized_scores)
        if total_p > 0:
            scores = [(s, p / total_p) for s, p in penalized_scores]
            scores.sort(key=lambda x: x[1], reverse=True)
            cover_penalty_applied = True

    if cover_penalty_applied:
        adjustments.append(f'🔗 穿盘率校验: cover={cover_rate:.0f}%<40%→穿盘比分降权·非穿盘比分优先')

    # 🆕 V3.14: 穿盘率-比分分布一致性校验
    # 当穿盘率与比分中穿盘比分概率总和偏离>15%时触发调整
    if handicap >= 0.5 and len(scores) >= 3:
        cover_score_sum = 0.0
        for s, p in scores:
            parts = s.split('-')
            try:
                hg, ag = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                continue
            diff = hg - ag
            if home_is_strong:
                covers = diff > handicap
            else:
                covers = (ag - hg) > handicap
            if covers:
                cover_score_sum += p
        # 穿盘率(0-1) vs 比分穿盘概率总和
        cover_rate_decimal = cover_rate / 100.0
        divergence = abs(cover_rate_decimal - cover_score_sum)
        if divergence > 0.15:
            # 偏离>15%: 将比分穿盘概率向穿盘率方向调整30%
            blend_factor = 0.30
            target_cover = cover_rate_decimal
            if cover_score_sum > 0.001:
                scale = (target_cover * blend_factor + cover_score_sum * (1 - blend_factor)) / cover_score_sum
            else:
                scale = 1.0
            adjusted_scores = []
            for s, p in scores:
                parts = s.split('-')
                try:
                    hg, ag = int(parts[0]), int(parts[1])
                except (ValueError, IndexError):
                    adjusted_scores.append((s, p))
                    continue
                diff = hg - ag
                if home_is_strong:
                    covers = diff > handicap
                else:
                    covers = (ag - hg) > handicap
                if covers:
                    adjusted_scores.append((s, p * scale))
                else:
                    adjusted_scores.append((s, p))
            # 重新归一化
            total_ap = sum(p for _, p in adjusted_scores)
            if total_ap > 0:
                scores = [(s, p / total_ap) for s, p in adjusted_scores]
                scores.sort(key=lambda x: x[1], reverse=True)
                adjustments.append(
                    f'🔗 穿盘率一致性: 比分穿盘概率{cover_score_sum:.0%}↔穿盘率{cover_rate:.0f}%偏离{divergence:.0%}>15%→{blend_factor:.0%}向穿盘率靠拢')

    # 🆕 V3.21 P0: 比分分布平滑 — BIG差距+低穿盘场景净胜1球独立估计
    # 问题: 海地VS苏格兰·穿盘45%→净胜1球仅15.1%·远低于BIG差距历史基线(~28%)
    # 修复: 当分布形态极端时·泊松+经验基线混合平滑
    _v321_smoothed = False
    if gap_level == 'big' and 30 <= cover_rate < 55 and len(scores) >= 5:
        # 计算当前净胜1球概率 (仅计入≥0.5%的有意义概率·排除泊松尾部分布噪声)
        _win_by_1 = 0.0
        _win_by_2plus = 0.0
        _prob_threshold = 0.005  # 0.5%以下忽略(尾部分布会系统性地放大净胜2+)
        for s, p in scores:
            if p < _prob_threshold:
                continue
            parts = s.split('-')
            try:
                hg, ag = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                continue
            diff = hg - ag
            if home_is_strong:
                if diff == 1: _win_by_1 += p
                elif diff >= 2: _win_by_2plus += p
            else:
                if diff == -1: _win_by_1 += p
                elif diff <= -2: _win_by_2plus += p
        _total_win_visible = _win_by_1 + _win_by_2plus
        # 使用可见概率(排除尾部)判断分布是否极端
        if _total_win_visible > 0.25 and _win_by_1 / max(_total_win_visible, 0.01) < 0.35:
            # 净胜1球占比<30%→分布过于极端·平滑纠正
            # 经验基线: BIG差距净胜1球约占胜场的28-35%
            _baseline_by1_ratio = 0.30  # 目标: 净胜1球≥30%胜场(可见概率)
            _target_by1 = _total_win_visible * _baseline_by1_ratio
            _deficit = _target_by1 - _win_by_1
            if _deficit > 0.015:
                # 从穿盘比分(净胜2+)转移概率到净胜1球比分
                _transfer_ratio = min(0.35, _deficit / max(_win_by_2plus, 0.01))
                _redistributed = []
                for s, p in scores:
                    parts = s.split('-')
                    try:
                        hg, ag = int(parts[0]), int(parts[1])
                    except (ValueError, IndexError):
                        _redistributed.append((s, p)); continue
                    diff = hg - ag
                    if home_is_strong:
                        _is_by1 = (diff == 1)
                        _is_by2plus = (diff >= 2)
                    else:
                        _is_by1 = (diff == -1)
                        _is_by2plus = (diff <= -2)
                    if _is_by2plus:
                        _redistributed.append((s, p * (1 - _transfer_ratio)))
                    elif _is_by1 and _win_by_1 > 0.001:
                        # 按净胜1球各比分当前比例分配转移量
                        _boost = _win_by_2plus * _transfer_ratio * (p / _win_by_1)
                        _redistributed.append((s, p + _boost))
                    else:
                        _redistributed.append((s, p))
                # 归一化
                _total_rp = sum(p for _, p in _redistributed)
                if _total_rp > 0:
                    scores = [(s, p / _total_rp) for s, p in _redistributed]
                    scores.sort(key=lambda x: x[1], reverse=True)
                    # 重算summary
                    _hw = _dr = _aw = 0.0
                    for s, p in scores:
                        h, a = s.split('-')
                        if int(h) > int(a): _hw += p
                        elif int(h) == int(a): _dr += p
                        else: _aw += p
                    summary = {'home_win': _hw, 'draw': _dr, 'away_win': _aw}
                    _v321_smoothed = True
                    adjustments.append(
                        f'🔗 V3.21 分布平滑: 可见净胜1球{_win_by_1:.0%}→{_win_by_1+_deficit:.0%}'
                        f'(BIG基线30%·转移{_transfer_ratio:.0%}穿盘→净胜1球)'
                    )

    sp.top_scores = scores[:8]
    sp.home_win_prob = round(summary['home_win'] * 100, 1)
    sp.draw_prob = round(summary['draw'] * 100, 1)
    sp.away_win_prob = round(summary['away_win'] * 100, 1)

    if scores:
        sp.most_likely = scores[0][0]
        sp.most_likely_prob = round(scores[0][1] * 100, 1)

    return sp


def format_score_output(sp: ScorePrediction) -> str:
    """格式化比分预测输出 (V4.3: 格局化·分组·移除单点"最可能"误导)"""
    lines = []
    lines.append(f"  📊 模型校准xG: 主 {sp.expected_goals_home} - {sp.expected_goals_away} 客 (总 {sp.total_goals_expected}) ⚠️含方向调整")
    if sp.cover_risk and sp.cover_risk != 'neutral':
        risk_label = '⚠️ 赢球输盘风险' if sp.cover_risk == 'win_but_lose_spread' else '🟢 大概率穿盘'
        lines.append(f"  🎲 穿盘风险: {risk_label} ({sp.cover_risk_prob:.0f}%) [独立评估·不修改xG]")
    lines.append(f"  🎯 胜负概率: 主胜 {sp.home_win_prob}% / 平 {sp.draw_prob}% / 客胜 {sp.away_win_prob}%")

    if sp.top_scores:
        # 🆕 V4.3: 按结果类型分组 — 替代单一"最可能比分"
        home_scores = []; draw_scores = []; away_scores = []
        for s, p in sp.top_scores[:8]:
            parts = s.split('-')
            hg, ag = int(parts[0]), int(parts[1])
            if hg > ag: home_scores.append((s, p))
            elif hg == ag: draw_scores.append((s, p))
            else: away_scores.append((s, p))

        home_total = sum(p for _, p in home_scores)
        draw_total = sum(p for _, p in draw_scores)
        away_total = sum(p for _, p in away_scores)

        # ── 格局判定 ──
        max_group = max(('主胜', home_total), ('平局', draw_total), ('客胜', away_total), key=lambda x: x[1])

        pattern = ''
        if max_group[0] == '主胜':
            big_win = sum(p for s, p in home_scores
                         if int(s.split('-')[0]) - int(s.split('-')[1]) >= 3)
            big_ratio = big_win / max(home_total, 0.001)
            if big_ratio >= 0.45:
                pattern = '主胜·大胜格局（穿盘概率高）'
            elif big_ratio >= 0.25:
                pattern = '主胜·中等优势（可穿盘·看临场）'
            else:
                pattern = '主胜·小胜格局（大概率不穿盘）'
        elif max_group[0] == '客胜':
            big_win = sum(p for s, p in away_scores
                         if int(s.split('-')[1]) - int(s.split('-')[0]) >= 3)
            big_ratio = big_win / max(away_total, 0.001)
            if big_ratio >= 0.45:
                pattern = '客胜·大胜格局（穿盘概率高）'
            elif big_ratio >= 0.25:
                pattern = '客胜·中等优势（可穿盘·看临场）'
            else:
                pattern = '客胜·小胜格局（大概率不穿盘）'
        else:
            pattern = '平局倾向（出线形势驱动·谨慎参考）'

        lines.append(f'  ⚽ 比分格局: {pattern}')

        # ── 🆕 V4.3: 波胆可靠性声明 ──
        lines.append(f'     ⚠️ 精确波胆仅供参考 (历史Top-1命中仅15%·Top-3=36%)')

        # ── 大胜格局: 不出虚假具体比分 ──
        if '大胜格局' in pattern:
            if '主胜' in pattern:
                lines.append(f'     主胜 {home_total*100:.0f}%: 预期净胜2球以上·泊松λ不足无法给出精确大比分')
            else:
                lines.append(f'     客胜 {away_total*100:.0f}%: 预期净胜2球以上·泊松λ不足无法给出精确大比分')
            # 仍显示平局组（若显著）以提示风险
            if draw_total >= 0.10:
                top3_draw = sorted(draw_scores, key=lambda x: x[1], reverse=True)[:3]
                draw_strs = [f'{s}({p*100:.0f}%)' for s, p in top3_draw]
                lines.append(f'     平局 {draw_total*100:.0f}%: {", ".join(draw_strs)}')
        else:
            # ── 分组展示: 主导组+平局(若显著) ──
            show_groups = [(max_group[0], max_group[1], home_scores if max_group[0] == '主胜'
                            else (draw_scores if max_group[0] == '平局' else away_scores))]
            # 平局作为第二组（若概率≥15%且非主导组）
            if max_group[0] != '平局' and draw_total >= 0.15:
                show_groups.append(('平局', draw_total, draw_scores))
            elif max_group[0] != '主胜' and home_total >= 0.15:
                show_groups.append(('主胜', home_total, home_scores))
            elif max_group[0] != '客胜' and away_total >= 0.15:
                show_groups.append(('客胜', away_total, away_scores))

            for label, total_p, scores in show_groups:
                top3 = sorted(scores, key=lambda x: x[1], reverse=True)[:3]
                score_strs = [f'{s}({p*100:.0f}%)' for s, p in top3]
                lines.append(f'     {label} {total_p*100:.0f}%: {", ".join(score_strs)}')

        # ── 单点概率提示 ──
        top_score, top_prob = sp.top_scores[0]
        if top_prob < 0.15:
            lines.append(f'     📌 单点最高 {top_score} 仅{top_prob*100:.0f}%·任一笔分概率均低·看格局不押单点')

    # 🆕 V3.4: 显示关键调整
    if sp.adjustments:
        for adj in sp.adjustments[:3]:  # 最多显示3条
            lines.append(f'     ↳ {adj}')

    return '\n'.join(lines)


def format_score_output_compact(sp: ScorePrediction) -> str:
    """紧凑单行格式"""
    parts = []
    for score, prob in sp.top_scores[:5]:
        parts.append(f"{score}({prob*100:.0f}%)")
    return ' | '.join(parts)


# ══════════════════════════════════════════
#  从PreMatchReport快速调用
# ══════════════════════════════════════════

def predict_score_from_report(r) -> ScorePrediction:
    """从PreMatchReport对象提取参数并预测比分 (V3.4增强版)"""
    home_cn = r.match_name.split('VS')[0].strip()
    away_cn = r.match_name.split('VS')[-1].strip() if 'VS' in r.match_name else ''

    home_odds = float(getattr(r, '_home_odds', 0) or 0)
    draw_odds = float(getattr(r, '_draw_odds', 0) or 0)
    away_odds = float(getattr(r, '_away_odds', 0) or 0)

    totals_line = float(getattr(r, '_totals_line', 2.5) or 2.5)
    gap_level = r.gap_level or 'moderate'

    # 🆕 V3.33: 按赔率判定强方 (热方≠强方, 如西班牙VS沙特热方=沙特但强方=西班牙)
    home_odds_val = float(getattr(r, '_home_odds', 2.0) or 2.0)
    away_odds_val = float(getattr(r, '_away_odds', 2.0) or 2.0)
    home_is_strong = (home_odds_val < away_odds_val) if (home_odds_val > 0 and away_odds_val > 0) else True
    # 🆕 V3.18: 实力优先时维持赔率判定
    v26_pred = r.v26_prediction or ''

    # FIFA排名 (🆕 V3.33: 按赔率强方分配, 非热方)
    if home_is_strong:
        home_rank = r.hot_team_fifa_rank if r.betfair_hot_side == 'home' else getattr(r, 'underdog_fifa_rank', 50)
        away_rank = getattr(r, 'underdog_fifa_rank', 50) if r.betfair_hot_side == 'home' else r.hot_team_fifa_rank
    else:
        home_rank = getattr(r, 'underdog_fifa_rank', 50) if r.betfair_hot_side == 'home' else r.hot_team_fifa_rank
        away_rank = r.hot_team_fifa_rank if r.betfair_hot_side == 'home' else getattr(r, 'underdog_fifa_rank', 50)
    home_rank = home_rank or 50
    away_rank = away_rank or 50
    hot_rank = r.hot_team_fifa_rank or 50

    # 近期进球数据
    home_gf = 0; home_ga = 0
    away_gf = 0; away_ga = 0
    if r.home_recent_form:
        home_gf = r.home_recent_form.get('avg_goals_scored', 0) or 0
        home_ga = r.home_recent_form.get('avg_goals_conceded', 0) or 0
    if r.away_recent_form:
        away_gf = r.away_recent_form.get('avg_goals_scored', 0) or 0
        away_ga = r.away_recent_form.get('avg_goals_conceded', 0) or 0

    cover_rate = r.xls_cover_rate or 50
    # 🆕 V3.12: 提取亚盘让球数用于穿盘率-比分一致性校验
    handicap = 0.5  # default
    try:
        hc_str = getattr(r, 'xls_handicap', '') or ''
        import re as _re_hc
        hc_match = _re_hc.search(r'(\d+\.?\d*)', str(hc_str).replace('让-', '').replace('让', ''))
        if hc_match:
            handicap = float(hc_match.group(1))
    except Exception:
        pass
    prediction_direction = r.v26_prediction or ''

    # 🆕 对手质量数据
    tc = r.three_conditions or {}
    three_conditions_met = 0
    if tc:
        conditions = tc.get('conditions', {})
        if isinstance(conditions, dict):
            three_conditions_met = sum(1 for v in conditions.values() if v is True)
        elif isinstance(conditions, int):
            three_conditions_met = conditions
        # also check 'all_pass'
        if tc.get('all_pass'):
            three_conditions_met = 3

    underdog_has_attackers = False
    underdog_giant_killer = 0.0  # 🆕 V3.12: float weight (0.0-1.0) 替代bool
    if tc:
        # check conditions
        conds = tc.get('conditions', {})
        if isinstance(conds, dict):
            # if condition (b) "无五大射手" is False → underdog has attackers
            if conds.get('b') is False or '❌' in str(tc.get('summary', '')):
                underdog_has_attackers = True

    # 🆕 从opponent_db获取更多数据
    try:
        from opponent_db import opponent_quality
        if r.betfair_hot_side == 'home':
            underdog_data = opponent_quality(away_cn)
        else:
            underdog_data = opponent_quality(home_cn)
        gk = underdog_data.get('giant_killings', [])
        if gk and len(gk) > 0:
            # 🆕 V3.12: 巨人杀手时间衰减 — >4年仅保留30%权重
            import re
            current_year = 2026
            gk_weights = []
            for gk_entry in gk:
                years = re.findall(r'\b(20\d{2})\b', str(gk_entry))
                for y_str in years:
                    y = int(y_str)
                    age = current_year - y
                    if age <= 2:
                        gk_weights.append(1.0)    # 近2年: 全额
                    elif age <= 4:
                        gk_weights.append(0.7)    # 2-4年: 70%
                    else:
                        gk_weights.append(0.3)    # >4年: 30%
            if gk_weights:
                underdog_giant_killer = max(gk_weights)  # 取最近事件的权重
            else:
                underdog_giant_killer = 0.5  # 无年份标记·默认50%权重
    except Exception:
        pass

    # 🆕 V3.4: 从大小球模型提取预测结论
    totals_pred = getattr(r, '_totals_prediction', {}) or {}
    totals_dir = totals_pred.get('direction', '')
    totals_conf = totals_pred.get('confidence', 50)

    sp = predict_score(
        match_name=r.match_name,
        home_odds=home_odds, draw_odds=draw_odds, away_odds=away_odds,
        totals_line=totals_line,
        totals_direction=totals_dir,          # 🆕 V3.4
        totals_confidence=totals_conf,        # 🆕 V3.4
        totals_diverge_level=totals_pred.get('diverge_level', 'none'),  # 🆕 V3.36
        gap_level=gap_level,
        home_is_strong=home_is_strong,
        home_fifa_rank=home_rank, away_fifa_rank=away_rank,
        home_goals_scored=home_gf, home_goals_conceded=home_ga,
        away_goals_scored=away_gf, away_goals_conceded=away_ga,
        cover_rate=cover_rate,
        handicap=handicap,  # 🆕 V3.12: 亚盘让球数
        prediction_direction=prediction_direction,
        hot_side=r.betfair_hot_side or 'home',  # 🆕 V3.4
        three_conditions_met=three_conditions_met,
        underdog_has_attackers=underdog_has_attackers,
        underdog_giant_killer=underdog_giant_killer,
        hot_team_rank=hot_rank,
        weak_team_threat=tc.get('threat_level', 0) if tc else 0,  # 🆕 V3.4
    )

    # 🆕 V3.3 P2-8: 淘汰赛进球衰减
    try:
        from knockout_motivation import calculate_knockout_motivation
        from config import CONF
        ko = calculate_knockout_motivation(r.match_name)
        if ko['is_knockout']:
            sp.expected_goals_home = round(sp.expected_goals_home * CONF.knockout_score_dampen, 2)
            sp.expected_goals_away = round(sp.expected_goals_away * CONF.knockout_score_dampen, 2)
            sp.total_goals_expected = round(sp.expected_goals_home + sp.expected_goals_away, 2)
            sp.adjustments.append(
                f'🏆 淘汰赛总进球衰减×{CONF.knockout_score_dampen}'
            )
    except Exception:
        pass

    return sp


# ══════════════════════════════════════════
#  自测
# ══════════════════════════════════════════
if __name__ == '__main__':
    # 测试热门不胜场景: 瑞士VS波黑 (BIG + 热门不胜)
    sp = predict_score(
        match_name="瑞士VS波黑",
        home_odds=1.55, draw_odds=4.09, away_odds=6.09,
        totals_line=2.5, gap_level='big', home_is_strong=True,
        home_goals_scored=1.8, home_goals_conceded=0.8,
        away_goals_scored=1.0, away_goals_conceded=1.2,
        cover_rate=34,
        prediction_direction='⚠️ 热门不胜',
        three_conditions_met=2,
        underdog_has_attackers=True,
        hot_team_rank=15,
    )
    print("=== 瑞士VS波黑 (热门不胜) ===")
    print(format_score_output(sp))
    print()

    # 测试热门仍赢场景: 捷克VS南非
    sp2 = predict_score(
        match_name="捷克VS南非",
        home_odds=1.82, draw_odds=3.54, away_odds=4.55,
        totals_line=2.3, gap_level='big', home_is_strong=True,
        home_goals_scored=1.0, home_goals_conceded=1.2,
        away_goals_scored=0.5, away_goals_conceded=1.8,
        cover_rate=28,
        prediction_direction='热门仍赢·不穿盘 (三条件全满足)',
        three_conditions_met=3,
        underdog_has_attackers=False,
        hot_team_rank=30,
    )
    print("=== 捷克VS南非 (热门仍赢) ===")
    print(format_score_output(sp2))

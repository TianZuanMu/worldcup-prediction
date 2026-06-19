"""
V3.4 比分概率预测模块
基于泊松分布 + 预测方向 + 对手质量 + 三条件 + 实力差距 + 近期进球

V3.4 新增:
  - 预测方向接入: "热门不胜" → 大幅降低强方λ, 提升弱方λ
  - 对手质量: 三条件/五大射手/巨人杀手 → 调整弱方进球
  - EXTREME特殊处理: 中立模型+高方差
  - 穿盘率四级联动
  - 回测目标: Top5命中率 40%→55%+
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


def _adjust_for_prediction_direction(lam_strong: float, lam_weak: float,
                                      prediction_text: str, gap_level: str,
                                      adjustments: List[str]) -> Tuple[float, float]:
    """
    🆕 V3.4: 根据V2.6规则预测方向调整λ

    核心洞察: 当模型预测"热门不胜"时, 市场赔率仍偏向热门,
    但真实比赛中弱方会进球——泊松模型必须反映这一点。
    """
    pred = prediction_text.lower() if prediction_text else ''

    if '⚠️ 热门不胜' in prediction_text or '热门不胜' in prediction_text:
        # 热门不胜 → 强方进球减少, 弱方进球增加
        # 幅度取决于差距级别
        if gap_level == 'close':
            factor_strong = 0.80   # 强方λ -20%
            factor_weak = 1.15     # 弱方λ +15%
            note = '热门不胜(CLOSE)→强方-20%弱方+15%'
        elif gap_level == 'big':
            factor_strong = 0.75   # 强方λ -25%
            factor_weak = 1.20     # 弱方λ +20%
            note = '热门不胜(BIG)→强方-25%弱方+20%'
        elif gap_level == 'moderate':
            factor_strong = 0.78   # 强方λ -22%
            factor_weak = 1.18     # 弱方λ +18%
            note = '热门不胜(MOD)→强方-22%弱方+18%'
        else:
            factor_strong = 0.85; factor_weak = 1.10
            note = '热门不胜→强方-15%弱方+10%'

        new_strong = lam_strong * factor_strong
        new_weak = lam_weak * factor_weak
        adjustments.append(f'🎯 {note}')
        return new_strong, new_weak

    elif '热门仍赢' in prediction_text:
        # 热门仍赢但可能不穿盘 → 强方略降, 弱方也可能进球
        factor_strong = 0.92
        factor_weak = 1.05
        adjustments.append('🎯 热门仍赢(不穿盘)→强方-8%弱方+5%')
        return lam_strong * factor_strong, lam_weak * factor_weak

    elif '热门胜' in prediction_text or '实力碾压' in prediction_text:
        # 热门稳胜 → 强方加强
        factor_strong = 1.10
        factor_weak = 0.90
        adjustments.append('🎯 热门胜/实力碾压→强方+10%弱方-10%')
        return lam_strong * factor_strong, lam_weak * factor_weak

    elif '客胜倾向' in prediction_text or ('客胜' in prediction_text and '⚠️' not in prediction_text):
        # 客队强
        factor_strong = 1.08
        factor_weak = 0.92
        adjustments.append('🎯 客胜倾向→客队(强方)+8%')
        return lam_strong * factor_strong, lam_weak * factor_weak

    elif '平局' in prediction_text or 'draw' in pred:
        # 平局倾向 → 拉近两队λ
        avg = (lam_strong + lam_weak) / 2.0
        adjustments.append('🎯 平局倾向→两队λ拉近')
        return avg * 1.05, avg * 0.95

    return lam_strong, lam_weak


def _adjust_for_opponent_quality(lam_strong: float, lam_weak: float,
                                  three_conditions_met: int,
                                  underdog_has_attackers: bool,
                                  underdog_giant_killer: bool,
                                  hot_team_rank: int,
                                  adjustments: List[str]) -> Tuple[float, float]:
    """
    🆕 V3.4: 对手质量调整

    - 三条件全满足(3/3): 弱方极弱 → 强方进球增加
    - 三条件2/3(有五大射手): 弱方能进球 → 弱方进攻提升
    - 巨人杀手血统: 弱方进球提升
    """
    # ── 三条件 ──
    if three_conditions_met == 3:
        # 弱方无射手+排名低+无爆冷史 → 很难进球
        lam_strong *= 1.10
        lam_weak *= 0.85
        adjustments.append('🛡️ 三条件全满足→弱方进攻极弱·强方+10%弱方-15%')
    elif three_conditions_met == 2:
        # 缺一项(通常是有五大射手) → 弱方有进球能力
        if underdog_has_attackers:
            lam_weak *= 1.20
            adjustments.append('⚔️ 弱方有五大射手→弱方进球+20%')

    # ── 巨人杀手 ──
    if underdog_giant_killer:
        lam_weak *= 1.12
        adjustments.append('💀 弱方巨人杀手血统→弱方进球+12%')

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
        label = '极低穿盘(<20%)'
    elif cover_rate < 30:
        factor_strong = 0.88
        factor_weak = 1.08
        label = '低穿盘(20-30%)'
    elif cover_rate < 40:
        factor_strong = 0.94
        factor_weak = 1.04
        label = '中低穿盘(30-40%)'
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


def _adjust_for_totals_prediction(lam_strong: float, lam_weak: float,
                                   totals_direction: str, totals_confidence: float,
                                   adjustments: List[str]) -> Tuple[float, float]:
    """
    🆕 V3.4: 大小球预测联动比分

    将独立的大小球模型结论反馈到泊松比分模型:
    - 大小球预测 ≠ 仅用原始盘口; 它综合了XLS趋势+6项修正因子
    - 当大小球模型高置信度预测小球/大球时, 调整总进球λ

    阈值: 置信度≥60%时触发, 避免弱信号干扰
    """
    if not totals_direction or totals_confidence < 60:
        return lam_strong, lam_weak

    if totals_direction == 'under':
        # 小球信号 → 双方λ同时缩减
        factor = 1.0 - (totals_confidence / 100) * 0.15  # 60%信→-9%, 90%信→-13.5%
        factor = max(0.82, factor)
        lam_strong *= factor
        lam_weak *= factor
        adjustments.append(f'⚽ 大小球模型→小球(信{totals_confidence:.0f}%)→总进球×{factor:.2f}')
    elif totals_direction == 'over':
        # 大球信号 → 双方λ同时放大
        factor = 1.0 + (totals_confidence / 100) * 0.12  # 60%信→+7.2%, 90%信→+10.8%
        factor = min(1.15, factor)
        lam_strong *= factor
        lam_weak *= factor
        adjustments.append(f'⚽ 大小球模型→大球(信{totals_confidence:.0f}%)→总进球×{factor:.2f}')

    return lam_strong, lam_weak


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
    """边界约束"""
    if gap_level == 'extreme':
        lam_home = max(0.15, min(6.0, lam_home))
        lam_away = max(0.15, min(5.5, lam_away))
    else:
        lam_home = max(0.15, min(5.5, lam_home))
        lam_away = max(0.15, min(5.0, lam_away))
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
                  gap_level: str = 'moderate',
                  home_is_strong: bool = True,
                  home_fifa_rank: int = 50, away_fifa_rank: int = 50,
                  home_goals_scored: float = 0, home_goals_conceded: float = 0,
                  away_goals_scored: float = 0, away_goals_conceded: float = 0,
                  cover_rate: float = 50,
                  prediction_direction: str = '',
                  three_conditions_met: int = 0,
                  underdog_has_attackers: bool = False,
                  underdog_giant_killer: bool = False,
                  hot_team_rank: int = 50) -> ScorePrediction:
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
        underdog_giant_killer: 弱方是否有巨人杀手血统
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

    # 2. 实力差距调整
    lam_strong, lam_weak = _adjust_for_gap_level(lam_strong, lam_weak, gap_level, adjustments)

    # 3. 🆕 预测方向接入 (最重要)
    lam_strong, lam_weak = _adjust_for_prediction_direction(
        lam_strong, lam_weak, prediction_direction, gap_level, adjustments
    )

    # 4. 🆕 对手质量
    lam_strong, lam_weak = _adjust_for_opponent_quality(
        lam_strong, lam_weak, three_conditions_met,
        underdog_has_attackers, underdog_giant_killer,
        hot_team_rank, adjustments
    )

    # 5. 🆕 穿盘率四级联动 (放在预测方向之后, 进一步微调)
    lam_strong, lam_weak = _adjust_for_cover_rate(
        lam_strong, lam_weak, cover_rate, gap_level, adjustments
    )

    # 5b. 🆕 V3.4: 大小球预测联动 (独立模型结论反馈到比分)
    lam_strong, lam_weak = _adjust_for_totals_prediction(
        lam_strong, lam_weak, totals_direction, totals_confidence, adjustments
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

    # 边界约束
    if gap_level == 'extreme':
        lam_home, lam_away = _apply_goal_ceiling(lam_home, lam_away, 'extreme')
    else:
        lam_home, lam_away = _apply_goal_ceiling(lam_home, lam_away, gap_level)

    sp.expected_goals_home = round(lam_home, 2)
    sp.expected_goals_away = round(lam_away, 2)
    sp.total_goals_expected = round(lam_home + lam_away, 2)
    sp.adjustments = adjustments

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

    sp.top_scores = scores[:8]
    sp.home_win_prob = round(summary['home_win'] * 100, 1)
    sp.draw_prob = round(summary['draw'] * 100, 1)
    sp.away_win_prob = round(summary['away_win'] * 100, 1)

    if scores:
        sp.most_likely = scores[0][0]
        sp.most_likely_prob = round(scores[0][1] * 100, 1)

    return sp


def format_score_output(sp: ScorePrediction) -> str:
    """格式化比分预测输出"""
    lines = []
    lines.append(f"  📊 预期进球: 主 {sp.expected_goals_home} - {sp.expected_goals_away} 客 (总 {sp.total_goals_expected})")
    lines.append(f"  🎯 胜负概率: 主胜 {sp.home_win_prob}% / 平 {sp.draw_prob}% / 客胜 {sp.away_win_prob}%")

    if sp.top_scores:
        lines.append(f"  ⚽ 最可能比分:")
        for score, prob in sp.top_scores[:6]:
            max_p = max(sp.top_scores[0][1] * 100, 1)
            bar_len = max(1, int(prob * 100 / max_p))
            bar = '█' * bar_len
            marker = ' ← 最可能' if score == sp.most_likely else ''
            lines.append(f"     {score}: {prob*100:4.1f}% {bar}{marker}")

    # 🆕 V3.4: 显示关键调整
    if sp.adjustments:
        for adj in sp.adjustments[:3]:  # 最多显示3条
            lines.append(f"     ↳ {adj}")

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

    # 判断主队是否为强方
    home_is_strong = True
    if r.betfair_hot_side == 'away' or r.xls_consensus_direction == 'bearish':
        home_is_strong = False

    # FIFA排名
    home_rank = r.hot_team_fifa_rank if r.betfair_hot_side == 'home' else getattr(r, 'underdog_fifa_rank', 50)
    away_rank = getattr(r, 'underdog_fifa_rank', 50) if r.betfair_hot_side == 'home' else r.hot_team_fifa_rank
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
    underdog_giant_killer = False
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
            underdog_giant_killer = True
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
        gap_level=gap_level,
        home_is_strong=home_is_strong,
        home_fifa_rank=home_rank, away_fifa_rank=away_rank,
        home_goals_scored=home_gf, home_goals_conceded=home_ga,
        away_goals_scored=away_gf, away_goals_conceded=away_ga,
        cover_rate=cover_rate,
        prediction_direction=prediction_direction,
        three_conditions_met=three_conditions_met,
        underdog_has_attackers=underdog_has_attackers,
        underdog_giant_killer=underdog_giant_killer,
        hot_team_rank=hot_rank,
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

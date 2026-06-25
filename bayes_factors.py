# -*- coding: utf-8 -*-
"""
V4.0 因子乘法链 (Bayesian Factor Chain)

替代 V3.x 二元决策树。所有信号统一为贝叶斯因子，在 Logit 空间做加权乘法，
输出后验概率分布 [胜%, 平%, 负%]，不再做 if-else 硬切。

架构:
  泊松先验 → 因子计算 (8个) → 时效衰减 → 分组去重 (加权几何平均)
  → Logit空间组合 → 先验收缩 → 硬约束 → 归一化 → 熵锐度置信度 → 输出

用法:
  from bayes_factors import FactorResult, FactorChain
  chain = FactorChain()
  posterior = chain.apply(prior=(58,24,18), context={...})
  print(f'{posterior.prediction} ({posterior.confidence}%)')
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from config import CONF


# ── 数据结构 ──

@dataclass
class FactorResult:
    """单个贝叶斯因子"""
    name: str                # 'hot', 'pnl', 'consensus', ...
    bf_win: float = 1.0      # 胜率乘数
    bf_draw: float = 1.0     # 平局乘数
    bf_lose: float = 1.0     # 负率乘数
    weight: float = 1.0      # 全局权重 [0,2]
    group: str = 'quality'   # 分组: flow/context/quality/anomaly
    confidence: float = 1.0  # 因子自身置信度 [0,1]
    data_age_hours: float = 0.0  # 数据年龄·小时
    detail: str = ''

    @classmethod
    def no_effect(cls, name: str, detail: str = '') -> 'FactorResult':
        return cls(name=name, detail=detail)

    @property
    def is_active(self) -> bool:
        return abs(self.bf_win - 1.0) > 0.005 or abs(self.bf_draw - 1.0) > 0.005


@dataclass
class FactorPosterior:
    """因子链输出"""
    win: float
    draw: float
    lose: float
    prediction: str           # '主胜'/'客胜'/'平局倾向'
    confidence: float         # 熵锐度置信度
    total_bf: float           # 胜率方向总BF (供诊断)
    active_factors: list
    factor_details: Dict[str, dict]


# ── 工具函数 ──

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def prob_to_logit(p: float) -> float:
    """概率% → logit。p∈(0,100)"""
    p01 = clamp(p / 100, 0.001, 0.999)
    return math.log(p01 / (1 - p01))


def logit_to_prob(logit: float) -> float:
    """logit → 概率%"""
    return 1 / (1 + math.exp(-clamp(logit, -6, 6))) * 100


def clamp_bf(bf: float, lo: float = None, hi: float = None) -> float:
    """裁剪bf到单因子边界"""
    lo = lo or CONF.factor_bf_single_min
    hi = hi or CONF.factor_bf_single_max
    return clamp(bf, lo, hi)


def weighted_geo_mean(values: List[float], confidences: List[float]) -> float:
    """
    加权几何平均 — 置信度作为指数权重。
    conf=1.0的因子完全参与，conf=0.0的因子完全忽略。
    """
    if not values or sum(confidences) < 1e-9:
        return 1.0
    weights = [c / sum(confidences) for c in confidences]
    log_sum = sum(w * math.log(max(v, 0.001)) for v, w in zip(values, weights))
    return math.exp(log_sum)


def entropy_sharpness(probs: Tuple[float, float, float]) -> float:
    """
    混合置信度: max_prob 主导 + 熵锐度微调。
    避免纯熵公式过度惩罚中等分布(如[46,28,26])。

    [51,49,0]  → 65% (明确倾向)
    [34,33,33] → 35% (几乎随机)
    [80,15,5]  → 85% (高确定)
    """
    max_prob = max(probs)
    entropy = -sum(p / 100 * math.log(max(p / 100, 1e-9)) for p in probs if p > 0)
    max_entropy = math.log(3)
    sharpness = 1.0 - (entropy / max_entropy)  # 0=flat, 1=peaked

    # max_prob主导(70%) + 锐度微调(30%)
    blended = max_prob * 0.7 + (max_prob * (0.5 + 0.5 * sharpness)) * 0.3

    return clamp(blended, CONF.factor_sharpness_floor, CONF.factor_sharpness_ceiling)


def get_data_decay(factor: FactorResult) -> float:
    """根据因子分组返回时效衰减系数"""
    if factor.group == 'flow':
        half_life = CONF.factor_decay_market_half_life
    elif factor.group == 'context':
        half_life = CONF.factor_decay_static_half_life
    elif factor.group == 'quality':
        # Form因子特殊处理
        if factor.name == 'form':
            half_life = CONF.factor_decay_form_half_life
        else:
            half_life = CONF.factor_decay_static_half_life
    else:
        half_life = CONF.factor_decay_market_half_life

    if factor.data_age_hours <= 1.0:
        return 1.0
    return 0.5 ** (factor.data_age_hours / half_life)


# ── 因子计算器 ──

def calc_hot_factor(cold: float, gap_level: str, form_diff: float = 0,
                    hot_side: str = '', data_age_hours: float = 2.0) -> FactorResult:
    """
    冷热因子: 热度越高→热门胜率下调·平局+冷门上调。
    共识与热度同向时降权(理性热度)。
    """
    from pre_match_report import get_dynamic_heat_threshold
    dyn_thresh = get_dynamic_heat_threshold(gap_level, abs(cold * 0.3), form_diff)

    if abs(cold) < dyn_thresh:
        return FactorResult.no_effect('hot', f'冷热{abs(cold):.0f}<阈值{dyn_thresh:.0f}·正常')

    intensity = min(abs(cold) - dyn_thresh, 40) / 40  # 0-1
    bf_win = clamp_bf(1.0 - intensity * 0.30)
    bf_draw = clamp_bf(1.0 + intensity * 0.15)
    bf_lose = clamp_bf(1.0 + intensity * 0.10)

    return FactorResult(
        name='hot', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_hot, group='flow',
        confidence=0.9, data_age_hours=data_age_hours,
        detail=f'冷热{abs(cold):.0f}>阈值{dyn_thresh:.0f}·强度{intensity:.2f}',
    )


def calc_pnl_factor(home_pnl: float, away_pnl: float, draw_pnl: float,
                    hot_side: str, cold: float, data_age_hours: float = 2.0) -> FactorResult:
    """
    庄家盈亏因子: 庄家在热门方大亏+冷热高→热门可能被高估。
    """
    pnl_map = {'home': home_pnl, 'away': away_pnl, 'draw': draw_pnl}
    hot_pnl = pnl_map.get(hot_side, 0) or 0

    if hot_pnl > -CONF.trap_pnl_contradiction_threshold:
        return FactorResult.no_effect('pnl', f'庄家亏损{abs(hot_pnl):,.0f}未达阈值')

    severity = min(abs(hot_pnl) / 10_000_000, 1.0)
    bf_win = clamp_bf(1.0 - severity * 0.15)
    bf_draw = clamp_bf(1.0 + severity * 0.10)
    bf_lose = clamp_bf(1.0 + severity * 0.08)

    return FactorResult(
        name='pnl', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_pnl, group='flow',
        confidence=0.85, data_age_hours=data_age_hours,
        detail=f'庄家亏损{abs(hot_pnl)/1e6:.1f}M·严重度{severity:.2f}',
    )


def calc_consensus_factor(consensus_pct: float, consensus_direction: str,
                          hot_side: str, unanimity: float = 0,
                          data_age_hours: float = 2.0) -> FactorResult:
    """
    共识因子: 极端共识(>80%公司同向)可能为协调行为→轻微降权。
    consensus与热度同向→理性(降权)·反向→加强。
    """
    abs_pct = abs(consensus_pct)
    if abs_pct < 50:
        return FactorResult.no_effect('consensus', f'共识{abs_pct:.0f}%<50%·温和')

    # 共识方向与热度方向是否一致
    agrees = ((consensus_direction == 'bullish' and hot_side == 'home') or
              (consensus_direction == 'bearish' and hot_side == 'away'))

    intensity = (abs_pct - 50) / 50  # 0-1
    if agrees:
        # 共识+热度同向 → 理性·偏移减半
        bf_win = clamp_bf(1.0 - intensity * 0.08)
        bf_draw = clamp_bf(1.0 + intensity * 0.04)
        bf_lose = clamp_bf(1.0 + intensity * 0.02)
        detail = f'共识{abs_pct:.0f}%与热度同向→理性·偏移减半'
        conf = 0.6
    else:
        # 共识+热度反向 → 警惕·偏移加强
        bf_win = clamp_bf(1.0 - intensity * 0.15)
        bf_draw = clamp_bf(1.0 + intensity * 0.10)
        bf_lose = clamp_bf(1.0 + intensity * 0.08)
        detail = f'共识{abs_pct:.0f}%与热度反向→警惕·偏移加强'
        conf = 0.8

    if unanimity > 0.85:
        bf_win = clamp_bf(bf_win - 0.03 if bf_win < 1.0 else bf_win)
        bf_draw = clamp_bf(bf_draw + 0.02)
        detail += f'·{unanimity:.0%}公司同向'

    return FactorResult(
        name='consensus', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_consensus, group='flow',
        confidence=conf, data_age_hours=data_age_hours, detail=detail,
    )


def calc_d12_factor(books_structure: dict, is_real_hot: bool,
                    data_age_hours: float = 1.0) -> FactorResult:
    """Dimension12 交叉验证因子"""
    if not books_structure:
        return FactorResult.no_effect('d12', '无d12数据')

    d12_is_real = books_structure.get('is_real_hot', is_real_hot)
    d12_hot_idx = books_structure.get('hot_index', 15)
    pnl_conf = books_structure.get('pnl_confidence', 0.5)

    if d12_is_real == is_real_hot:
        return FactorResult.no_effect('d12', f'd12与内置一致(热指{d12_hot_idx:.0f})')

    # 分歧: d12说不热，内置说热 → 按严重度分级
    d12_gap = abs(d12_hot_idx - 15)  # 热指偏离基准的程度
    d12_mild = getattr(CONF, '_calib_d12_mild_draw', 1.02)
    if d12_gap > 20 and pnl_conf > 0.7:
        bf_win = clamp_bf(0.88); bf_draw = clamp_bf(1.08)  # 严重分歧
    elif d12_gap > 10:
        bf_win = clamp_bf(0.92); bf_draw = clamp_bf(1.05)  # 中度分歧
    else:
        bf_win = clamp_bf(0.96); bf_draw = clamp_bf(d12_mild)  # 轻度分歧·可校准
    bf_lose = 1.0

    return FactorResult(
        name='d12', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_d12, group='quality',
        confidence=pnl_conf, data_age_hours=data_age_hours,
        detail=f'd12分歧(热指{d12_hot_idx:.0f}·置信{pnl_conf:.2f})',
    )


def calc_context_factor(motivation_diff: float, home_mot: float, away_mot: float,
                        rotation_risk: float = 0, draw_advance_both: bool = False,
                        travel_disadvantage: bool = False, matchday: int = 2,
                        rank_gap: float = 0, is_strong_favorite: bool = False,
                        data_age_hours: float = 0.0) -> FactorResult:
    """
    赛事性质因子 V4.1: 战意差·轮换·远征·比赛日·平局出线·弱队生死战·强队放水。
    足球特有的博弈结构，权重最高 (1.2)。

    🆕 新增场景:
    - 弱队必须赢(rank_gap>20 + 弱队mot=10 + MD3): bf_underdog += 15%
    - 强队已出线+大幅轮换(rot>0.4 + rank_gap>25): bf_fav *= 0.85
    - 远征劣势: bf_away *= 0.92
    """
    bf_win = 1.0; bf_draw = 1.0; bf_lose = 1.0
    notes = []
    conf = 0.95

    # 1. 平局出线 — 唯一允许突破上界的因子
    if draw_advance_both:
        bf_win = 0.85
        bf_draw = clamp(1.35, CONF.factor_bf_single_min, CONF.factor_bf_draw_advance_max)
        bf_lose = 0.85
        notes.append('双方平局出线')
        conf = 0.98

    # 2. 🆕 弱队生死战 (排名低20+·弱队mot=10·MD3必须赢)
    if abs(rank_gap) > 20 and matchday >= 2:
        # 判断哪边是弱队
        if motivation_diff > 5 and home_mot >= 9:
            # 主队是弱队但必须赢 → 主队爆冷概率上升
            bf_win = clamp_bf(bf_win * 1.12)
            bf_lose = clamp_bf(bf_lose * 0.88)
            notes.append('主队生死战·弱队爆发')
            conf = 0.80
        elif motivation_diff < -5 and away_mot >= 9:
            # 客队是弱队但必须赢
            bf_lose = clamp_bf(bf_lose * 1.12)
            bf_win = clamp_bf(bf_win * 0.88)
            notes.append('客队生死战·弱队爆发')
            conf = 0.80

    # 3. 🆕 强队放水 (rank_gap>25 + 强队轮换>40% + 强队mot≤5)
    if abs(rank_gap) > 25 and rotation_risk > 0.4 and is_strong_favorite:
        bf_win = clamp_bf(bf_win * 0.82)
        bf_draw = clamp_bf(bf_draw * 1.18)
        bf_lose = clamp_bf(bf_lose * 1.12)
        notes.append(f'强队大幅轮换{rotation_risk:.0%}')
        conf = 0.85

    # 4. 战意极端分化 (通用)
    if abs(motivation_diff) >= 5 and not notes:  # 避免与生死战重复
        if motivation_diff > 0:
            bf_win = clamp_bf(bf_win * 1.08)
            bf_lose = clamp_bf(bf_lose * 0.92)
        else:
            bf_lose = clamp_bf(bf_lose * 1.08)
            bf_win = clamp_bf(bf_win * 0.92)
        notes.append(f'战意差{motivation_diff:+.0f}')
        conf = 0.85

    # 5. 一般轮换 (非强队放水场景)
    if rotation_risk > 0.4 and not notes:
        bf_win = clamp_bf(bf_win * 0.88)
        bf_draw = clamp_bf(bf_draw * 1.10)
        notes.append(f'轮换风险{rotation_risk:.0%}')

    # 6. 远征劣势
    if travel_disadvantage:
        bf_win = clamp_bf(bf_win * 0.92)
        bf_draw = clamp_bf(bf_draw * 1.05)
        notes.append('远征疲劳')

    # 7. MD3 不确定性 (可校准参数·仅当无更强信号时)
    if matchday == 3 and len(notes) <= 1:
        md3_boost = getattr(CONF, '_calib_md3_draw_boost', 1.02)
        bf_draw = clamp_bf(bf_draw * md3_boost)
        notes.append('小组末轮')

    if not notes:
        return FactorResult.no_effect('context', '赛事性质中性')

    return FactorResult(
        name='context', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_context, group='context',
        confidence=conf, data_age_hours=data_age_hours,
        detail='·'.join(notes),
    )


def calc_form_factor(form_diff: float, data_age_hours: float = 48.0) -> FactorResult:
    """状态差因子"""
    if abs(form_diff) < 1.0:
        return FactorResult.no_effect('form', f'状态差{form_diff:+.1f}<1·无影响')

    intensity = min(abs(form_diff), 4.0) / 4.0  # 0-1
    if form_diff > 0:
        bf_win = clamp_bf(1.0 + intensity * 0.08)
        bf_lose = clamp_bf(1.0 - intensity * 0.05)
    else:
        bf_win = clamp_bf(1.0 - intensity * 0.08)
        bf_lose = clamp_bf(1.0 + intensity * 0.05)
    bf_draw = 1.0

    return FactorResult(
        name='form', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_form, group='quality',
        confidence=0.7, data_age_hours=data_age_hours,
        detail=f'状态差{form_diff:+.1f}·强度{intensity:.2f}',
    )


def calc_threat_factor(has_elite_fw: bool, threat_count: int = 0,
                       data_age_hours: float = 0.0) -> FactorResult:
    """对手攻击威胁因子"""
    if not has_elite_fw and threat_count < 3:
        return FactorResult.no_effect('threat', '无显著攻击威胁')

    intensity = min(threat_count, 8) / 8  # 0-1
    bf_win = clamp_bf(1.0 - intensity * 0.10)
    bf_draw = clamp_bf(1.0 + intensity * 0.05)
    bf_lose = clamp_bf(1.0 + intensity * 0.08)

    detail = f'精英FW' if has_elite_fw else f'{threat_count}名攻击手'
    return FactorResult(
        name='threat', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_threat, group='quality',
        confidence=0.6, data_age_hours=data_age_hours, detail=detail,
    )


def calc_trap_factor(trap_score: float, trap_level: str) -> FactorResult:
    """
    市场异常因子 V4.1: 仅≥70分触发·仅放大平局概率(方差放大器)。
    不改变胜负方向——异常信号太嘈杂，不能用于翻转预测。
    """
    if trap_score < 70:
        return FactorResult.no_effect('trap', f'异常{trap_score:.0f}分<70·跳过')

    # ≥70分: 仅增加平局不确定性·不改胜负方向
    bf_draw = clamp_bf(1.0 + (trap_score - 70) / 100 * 0.15)  # 最多+4.5%
    bf_win = 1.0   # 不碰胜负
    bf_lose = 1.0

    return FactorResult(
        name='trap', bf_win=bf_win, bf_draw=bf_draw, bf_lose=bf_lose,
        weight=CONF.factor_weight_trap, group='anomaly',
        confidence=0.3, detail=f'极端异常{trap_score:.0f}分·仅平局预警',
    )


# ── 分组与组合 ──

FACTOR_GROUPS = {
    'flow': ['hot', 'pnl', 'consensus'],
    'context': ['context'],
    'quality': ['d12', 'threat', 'form'],
    'anomaly': ['trap'],
}


def group_factors(factors: List[FactorResult]) -> List[FactorResult]:
    """
    因子分组去重: 同一组内几何平均合并。
    flow组的热/PnL/共识本质描述同一现象→合并避免三重惩罚。
    """
    groups: Dict[str, List[FactorResult]] = {'flow': [], 'context': [], 'quality': [], 'anomaly': []}

    for f in factors:
        if not f.is_active:
            continue
        for gname, gmembers in FACTOR_GROUPS.items():
            if f.name in gmembers:
                groups[gname].append(f)
                break

    merged = []
    for gname, gfactors in groups.items():
        if not gfactors:
            continue
        if gname in ('flow', 'context'):
            # 组内加权几何平均合并 (置信度²加权)
            values_w = [gf.bf_win for gf in gfactors]
            values_d = [gf.bf_draw for gf in gfactors]
            values_l = [gf.bf_lose for gf in gfactors]
            confs_sq = [gf.confidence ** 2 for gf in gfactors]  # 平方降权低置信因子

            merged_bf_win = weighted_geo_mean(values_w, confs_sq)
            merged_bf_draw = weighted_geo_mean(values_d, confs_sq)
            merged_bf_lose = weighted_geo_mean(values_l, confs_sq)

            # 🆕 Context组平局收缩: 多个平局提升因子→防止级联放大
            if gname == 'context':
                draw_boosters = [gf for gf in gfactors if gf.bf_draw > 1.02]
                if len(draw_boosters) >= 2:
                    merged_bf_draw = 1.0 + (merged_bf_draw - 1.0) * 0.90

            merged.append(FactorResult(
                name=f'{gname}_combined',
                bf_win=merged_bf_win, bf_draw=merged_bf_draw, bf_lose=merged_bf_lose,
                weight=1.0, group=gname,
                confidence=max(gf.confidence for gf in gfactors),
                detail=' + '.join(gf.name for gf in gfactors),
            ))
        else:
            merged.extend(gfactors)

    return merged


def apply_factor_chain(prior: Tuple[float, float, float],
                       raw_factors: List[FactorResult],
                       is_extreme: bool = False,
                       crush_index: float = 0.0,
                       big_sell_volume: float = 0.0) -> FactorPosterior:
    """
    V4.0 因子乘法链主入口。

    Args:
        prior: (win%, draw%, lose%) from Poisson
        raw_factors: list of FactorResult from all signal detectors
        is_extreme: True if EXTREME gap
        crush_index: 碾压指数 (0-1)
        big_sell_volume: 大额卖单总金额

    Returns:
        FactorPosterior with prediction and confidence
    """
    # ── Step 0: EXTREME 碾压 → 跳过市场类因子 ──
    if is_extreme and crush_index >= CONF.factor_extreme_full_crush:
        filtered = []
        for f in raw_factors:
            if f.group in ('flow',):
                continue  # 跳过市场因子
            if f.group in ('context',):
                f.weight *= CONF.factor_extreme_context_boost  # 赛事因子加倍
            filtered.append(f)
        raw_factors = filtered

    # ── Step 1: 时效衰减 + 低置信过滤 ──
    active = []
    for f in raw_factors:
        if not f.is_active:
            continue
        decay = get_data_decay(f)
        effective_conf = f.confidence * decay
        if effective_conf < CONF.factor_min_confidence:
            continue
        f.confidence = effective_conf  # 更新为有效置信度
        active.append(f)

    # ── Step 2: 因子分组去重 ──
    merged = group_factors(active)

    # ── Step 3: Logit空间组合 ──
    logits = [prob_to_logit(p) for p in prior]  # [win_logit, draw_logit, lose_logit]

    for f in merged:
        logit_shift_win = math.log(max(f.bf_win, 0.001))
        logit_shift_draw = math.log(max(f.bf_draw, 0.001))
        logit_shift_lose = math.log(max(f.bf_lose, 0.001))

        # 裁剪单因子logit位移
        lo = math.log(CONF.factor_bf_single_min)
        hi = math.log(CONF.factor_bf_single_max)
        logit_shift_win = clamp(logit_shift_win, lo, hi)
        logit_shift_draw = clamp(logit_shift_draw, lo, hi)
        logit_shift_lose = clamp(logit_shift_lose, lo, hi)

        logits[0] += logit_shift_win * f.weight
        logits[1] += logit_shift_draw * f.weight
        logits[2] += logit_shift_lose * f.weight

    # ── Step 3b: 先验收缩 ──
    if CONF.factor_prior_shrinkage < 1.0:
        for i in range(3):
            logits[i] *= CONF.factor_prior_shrinkage

    # ── Step 3c: 总链最终保险裁剪 ──
    total_lo = math.log(CONF.factor_chain_bf_min)
    total_hi = math.log(CONF.factor_chain_bf_max)
    original_logits = [prob_to_logit(p) for p in prior]
    for i in range(3):
        delta = logits[i] - original_logits[i]
        delta = clamp(delta, total_lo, total_hi)
        logits[i] = original_logits[i] + delta

    # ── Step 4: 转回概率 → 归一化 ──
    probs = [logit_to_prob(l) for l in logits]
    total = sum(probs)
    posterior = tuple(p / total * 100 for p in probs)

    # ── Step 4b: 平局出线特殊处理 ──
    # 不再做后处理 ×1.5，改为由 context 因子在管道内处理

    # ── Step 4c: 大额卖单硬约束 ──
    win, draw, lose = posterior
    if big_sell_volume >= CONF.big_sell_hard_cap:
        max_win = 60
        if win > max_win:
            excess = win - max_win
            win = max_win
            draw += excess * 0.6
            lose += excess * 0.4
            posterior = (win, draw, lose)

    # ── Step 5: 预测方向 + 弃权检测 + 熵锐度置信度 ──
    max_prob = max(posterior)
    margin = max_prob - sorted(posterior)[1]

    # 🆕 V4.1: 动态弃权阈值 — 早期小组赛更自信·MD3+淘汰赛更谨慎
    # matchday从raw_factors中推断(取context因子的matchday)
    _matchday = 2  # default
    for f in raw_factors:
        if f.name == 'context' and hasattr(f, 'detail'):
            # detail可能包含'小组末轮'→MD3
            _matchday = 3 if '末轮' in f.detail else _matchday

    abstain_margin = 7.0 if _matchday == 3 else 4.0  # MD3更宽松

    # 弃权条件: margin<阈值 且 最大概率<45% (双重保险)
    if margin < abstain_margin and max_prob < 45.0:
        prediction = 'ABSTAIN'
        confidence = 0
    else:
        if posterior[2] == max_prob:
            prediction = '客胜'
        elif posterior[1] == max_prob:
            prediction = '平局倾向'
        else:
            prediction = '主胜'
        confidence = entropy_sharpness(posterior)

    # 总BF (胜率方向·供诊断)
    prior_win = prior[0]
    total_bf_win = posterior[0] / prior_win if prior_win > 0 else 1.0

    return FactorPosterior(
        win=posterior[0], draw=posterior[1], lose=posterior[2],
        prediction=prediction, confidence=confidence,
        total_bf=total_bf_win,
        active_factors=merged,
        factor_details={
            f.name: {'bf_win': f.bf_win, 'bf_draw': f.bf_draw, 'bf_lose': f.bf_lose,
                     'weight': f.weight, 'confidence': f.confidence}
            for f in merged
        },
    )


# ── 独立测试 ──
if __name__ == '__main__':
    print("V4.0 因子乘法链")
    print(f"  单因子边界: [{CONF.factor_bf_single_min}, {CONF.factor_bf_single_max}]")
    print(f"  总链边界:   [{CONF.factor_chain_bf_min}, {CONF.factor_chain_bf_max}]")
    print(f"  时效半衰:   市场{CONF.factor_decay_market_half_life}h / 状态{CONF.factor_decay_form_half_life}h")
    print(f"  先验收缩:   {CONF.factor_prior_shrinkage}")
    print(f"  熵锐度范围: [{CONF.factor_sharpness_floor}-{CONF.factor_sharpness_ceiling}]")
    print()

    # 波黑VS卡塔尔 模拟
    print("=== 波黑VS卡塔尔 模拟 ===")
    prior = (58.0, 24.0, 18.0)

    factors = [
        calc_hot_factor(cold=30, gap_level='close', form_diff=1.6, hot_side='home'),
        calc_pnl_factor(home_pnl=-4_649_483, away_pnl=0, draw_pnl=0, hot_side='home', cold=30),
        calc_consensus_factor(consensus_pct=-96, consensus_direction='bullish', hot_side='home', unanimity=0.96),
        calc_context_factor(motivation_diff=0, home_mot=10, away_mot=10, matchday=3),
        calc_form_factor(form_diff=1.6),
        calc_d12_factor(books_structure={'is_real_hot': False, 'hot_index': 15, 'pnl_confidence': 0.6}, is_real_hot=True),
        calc_threat_factor(has_elite_fw=False, threat_count=1),
        calc_trap_factor(trap_score=0, trap_level='none'),
    ]

    result = apply_factor_chain(prior, factors)
    print(f'先验: {prior}')
    print(f'后验: [{result.win:.1f}%, {result.draw:.1f}%, {result.lose:.1f}%]')
    print(f'预测: {result.prediction}  置信度: {result.confidence:.0f}%')
    print(f'总BF(胜率): {result.total_bf:.3f}')
    for f in result.active_factors:
        print(f'  {f.name}: W{f.bf_win:.3f} D{f.bf_draw:.3f} L{f.bf_lose:.3f} (w{f.weight}) [{f.detail}]')

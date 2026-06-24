# -*- coding: utf-8 -*-
"""
V3.41 诱盘检测模块 (Trap Odds Detection)

6维度诱盘评分:
  1. 竞彩官方背离 (25%) — 非商业机构逆势操作
  2. PnL-赔率矛盾 (25%) — 庄家盈亏与赔率走势相反
  3. 大资金-赔率背离 (20%) — 聪明钱逆势买入
  4. Pinnacle极端偏离 (15%) — 最敏锐庄家大幅偏离
  5. 叙事-资金矛盾 (10%) — 公众叙事与真实资金背离
  6. 亚盘水位矛盾 (5%)  — 经典诱盘水位模式

输出: TrapOddsResult (trap_score, direction, level, confidence_adj, signals, warning)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from config import CONF


@dataclass
class TrapOddsResult:
    """诱盘检测结果"""
    trap_score: float = 0.0              # 0-100 综合诱盘评分
    trap_direction: str = 'none'         # 'fade_favorite' / 'fade_underdog' / 'none'
    trap_level: str = 'none'             # 'severe'(≥70) / 'moderate'(≥40) / 'mild'(≥20) / 'none'
    confidence_adj: int = 0              # -15 to +5
    signals: Dict[str, dict] = field(default_factory=dict)
    warning: str = ''                    # 报告用摘要


# ── 辅助函数 ──

def _safe_float(val, default=0.0) -> float:
    """安全转float"""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _market_avg_change(bookmakers: list, key: str) -> float:
    """计算所有博彩公司的平均变动%"""
    changes = []
    for b in bookmakers:
        v = _safe_float(b.get(key, 0))
        if v != 0:
            changes.append(v)
    if not changes:
        return 0.0
    return sum(changes) / len(changes)


def _count_direction(bookmakers: list, key: str, threshold: float = 1.0) -> Tuple[int, int]:
    """统计升/降公司数 (绝对值>threshold才计入)"""
    up, down = 0, 0
    for b in bookmakers:
        v = _safe_float(b.get(key, 0))
        if v > threshold:
            up += 1
        elif v < -threshold:
            down += 1
    return up, down


# ── 六大检测信号 ──

def _signal_jingcai_divergence(euro_bookmakers: list, jingcai_euro: Optional[dict],
                                hot_side: str, xls_consensus_direction: str) -> dict:
    """
    信号1: 竞彩官方背离 (权重25)

    竞彩官方是非商业机构(政府彩票), 不参与诱盘。
    当竞彩逆势操作(降赔)而市场集体反向(升赔)时, 竞彩的信号更干净。
    """
    if not jingcai_euro:
        return {'score': 0, 'detail': '无竞彩欧赔数据', 'direction': 'none'}

    jc_change = _safe_float(jingcai_euro.get('win_change', 0))
    market_avg = _market_avg_change(euro_bookmakers, 'win_change')

    # 竞彩与市场的方向差
    gap = abs(jc_change - market_avg)

    if gap < CONF.trap_jingcai_divergence_threshold:
        return {'score': 0, 'detail': f'竞彩与市场一致(差{gap:.1f}%)', 'direction': 'none'}

    # 竞彩降赔 + 市场升赔 = 竞彩看好主胜, 市场看衰
    # 竞彩升赔 + 市场降赔 = 竞彩看衰主胜, 市场看好
    # 注意: 竞彩变动幅度天然小于商业公司, 使用方向判断而非独立阈值
    jc_down = jc_change < -1.0   # 竞彩≥1%降赔即为降
    jc_up = jc_change > 1.0      # 竞彩≥1%升赔即为升
    mkt_up = market_avg > CONF.trap_jingcai_divergence_threshold
    mkt_down = market_avg < -CONF.trap_jingcai_divergence_threshold

    score = 0
    direction = 'none'
    detail = ''

    if jc_down and mkt_up:
        # 竞彩降主胜赔(看好主胜) vs 市场升主胜赔(看衰主胜)
        # → 诱盘方向: 市场在诱空主胜
        score = min(100, gap * 3)
        direction = 'fade_favorite' if hot_side == 'home' else 'fade_underdog'
        detail = (f'竞彩降主胜{jc_change:+.1f}% vs 市场升{market_avg:+.1f}%'
                  f' → 非商业机构逆势看好主胜·差{gap:.1f}%')
    elif jc_up and mkt_down:
        # 竞彩升主胜赔(看衰主胜) vs 市场降主胜赔(看好主胜)
        score = min(100, gap * 3)
        direction = 'fade_favorite' if hot_side == 'away' else 'fade_underdog'
        detail = (f'竞彩升主胜{jc_change:+.1f}% vs 市场降{market_avg:+.1f}%'
                  f' → 非商业机构逆势看衰主胜·差{gap:.1f}%')
    elif gap >= CONF.trap_jingcai_divergence_threshold:
        # 大偏离但同向: 竞彩幅度与市场显著不同
        detail = (f'竞彩{jc_change:+.1f}% vs 市场{market_avg:+.1f}%'
                  f' → 同向但幅度差{gap:.1f}%·无背离')
    else:
        detail = f'竞彩{jc_change:+.1f}% vs 市场{market_avg:+.1f}%(同向·无背离)'

    # 公司数加权: 市场同向的公司越多, 背离越显著
    win_up, win_down = _count_direction(euro_bookmakers, 'win_change')
    total = len(euro_bookmakers) if euro_bookmakers else 1
    unanimity = max(win_up, win_down) / total
    if unanimity > 0.8:
        score = min(100, score * 1.3)
        detail += f' | {unanimity:.0%}公司同向·背离更显著'

    return {'score': round(score), 'detail': detail, 'direction': direction}


def _signal_pnl_contradiction(betfair_snapshots: list, hot_side: str,
                                euro_bookmakers: list) -> dict:
    """
    信号2: PnL-赔率矛盾 (权重25)

    庄家在某方亏损严重(>1M) 但 赔率仍在上升 → 庄家利益与赔率暗示相反。
    如果庄家真的看衰该方, 他们会降赔以减少亏损, 而非升赔吸引更多投注。
    """
    if not betfair_snapshots:
        return {'score': 0, 'detail': '无必发快照数据', 'direction': 'none'}

    latest = betfair_snapshots[-1].get('betfair', {})
    if not latest:
        return {'score': 0, 'detail': '必发数据为空', 'direction': 'none'}

    # 找到庄家亏损最严重的一方
    pnls = {
        'home': latest.get('home_pnl', 0) or 0,
        'draw': latest.get('draw_pnl', 0) or 0,
        'away': latest.get('away_pnl', 0) or 0,
    }
    # 庄家亏损 = 负PnL (庄家赔钱) → 取最小的(最负的)
    worst_side = min(pnls, key=pnls.get)
    worst_pnl = pnls[worst_side]

    if worst_pnl > -CONF.trap_pnl_contradiction_threshold:
        return {'score': 0, 'detail': f'庄家亏损未达阈值({worst_pnl:,.0f})', 'direction': 'none'}

    # 该方赔率是否在上升?
    market_avg = _market_avg_change(euro_bookmakers, f'{worst_side}_change' if worst_side != 'draw' else 'draw_change')
    if worst_side == 'home':
        mkt_change = _market_avg_change(euro_bookmakers, 'win_change')
    elif worst_side == 'away':
        mkt_change = _market_avg_change(euro_bookmakers, 'lose_change')
    else:
        mkt_change = _market_avg_change(euro_bookmakers, 'draw_change')

    if mkt_change <= CONF.trap_jingcai_divergence_threshold:
        return {'score': 0, 'detail': f'庄家亏{worst_pnl:,.0f}但赔率未升(变动{mkt_change:+.1f}%)', 'direction': 'none'}

    # 矛盾: 庄家在某方大亏 + 该方赔率上升
    # → 庄家在"邀请"更多投注到他们亏损的方向 → 可能是诱盘
    score = min(100, abs(worst_pnl) / CONF.trap_pnl_contradiction_threshold * 25)

    side_cn = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[worst_side]

    # 判断诱盘方向: 庄家亏损方 = 他们不希望发生的结果
    # 赔率上升 = 他们在引导资金离开该方
    # → 诱盘方向是让公众远离庄家亏损方
    if worst_side == hot_side:
        direction = 'fade_favorite'
    elif worst_side != 'draw':
        direction = 'fade_underdog'
    else:
        direction = 'fade_favorite'

    detail = (f'庄家在{side_cn}亏{abs(worst_pnl):,.0f}'
              f'却升赔{mkt_change:+.1f}%'
              f' → 赔率走势与庄家利益矛盾·诱盘嫌疑')

    return {'score': round(score), 'detail': detail, 'direction': direction}


def _signal_volume_odds_divergence(betfair_snapshots: list, euro_bookmakers: list,
                                     hot_side: str) -> dict:
    """
    信号3: 大资金-赔率背离 (权重20)

    必发成交量在某方急升(>500K) 且 赔率上升(>10%) → 聪明钱逆势买入。
    如果市场真的看衰该方, 资金不会涌入。
    """
    if not betfair_snapshots or len(betfair_snapshots) < 3:
        return {'score': 0, 'detail': '快照不足(需≥3)', 'direction': 'none'}

    # 取首尾快照对比成交量变化
    first = betfair_snapshots[0].get('betfair', {})
    last = betfair_snapshots[-1].get('betfair', {})

    vol_keys = {'home': 'home_volume', 'draw': 'draw_volume', 'away': 'away_volume'}
    price_keys = {'home': 'home_price', 'draw': 'draw_price', 'away': 'away_price'}

    best_score = 0
    best_detail = ''
    best_direction = 'none'

    for side, vol_key in vol_keys.items():
        vol_first = first.get(vol_key, 0) or 0
        vol_last = last.get(vol_key, 0) or 0
        vol_increase = vol_last - vol_first

        # 成交量需急升 >500K
        if vol_increase < 500_000:
            continue

        # 该方赔率需上升 >10%
        price_first = first.get(price_keys[side], 0) or 0
        price_last_val = last.get(price_keys[side], 0) or 0
        if price_first <= 0:
            continue
        price_change_pct = (price_last_val - price_first) / price_first * 100

        if price_change_pct < CONF.trap_volume_odds_divergence_min:
            continue

        # 背离: 量大增 + 赔率上升
        score = min(100, (vol_increase / 500_000) * 15 + price_change_pct * 2)

        side_cn = {'home': '主胜', 'draw': '平局', 'away': '客胜'}[side]
        direction = 'fade_favorite' if side == hot_side else 'fade_underdog'

        detail = (f'{side_cn}成交量增{vol_increase:,.0f}(+{vol_increase/vol_first*100:.0f}%)'
                  f'但赔率升{price_change_pct:+.1f}%'
                  f' → 大资金逆势买入·背离显著')

        if score > best_score:
            best_score = score
            best_detail = detail
            best_direction = direction

    if best_score == 0:
        return {'score': 0, 'detail': '成交量与赔率同向·无背离', 'direction': 'none'}

    return {'score': round(best_score), 'detail': best_detail, 'direction': best_direction}


def _signal_pinnacle_divergence(euro_bookmakers: list, hot_side: str,
                                  xls_consensus_direction: str) -> dict:
    """
    信号4: Pinnacle极端偏离 (权重15)

    Pinnacle(平博)是全球最敏锐的博彩公司(最低抽水·最高信息效率)。
    当Pinnacle的赔率变动大幅偏离市场均值(>15%), 是重要信号。
    """
    # 找到Pinnacle
    pinnacle = None
    for b in euro_bookmakers:
        name = b.get('name', '')
        if 'pinnacle' in name.lower() or '平博' in name:
            pinnacle = b
            break

    if not pinnacle:
        return {'score': 0, 'detail': '未找到Pinnacle数据', 'direction': 'none'}

    # Pinnacle的变动 vs 市场平均
    p_wc = _safe_float(pinnacle.get('win_change', 0))
    p_dc = _safe_float(pinnacle.get('draw_change', 0))
    p_lc = _safe_float(pinnacle.get('lose_change', 0))

    m_wc = _market_avg_change(euro_bookmakers, 'win_change')
    m_dc = _market_avg_change(euro_bookmakers, 'draw_change')
    m_lc = _market_avg_change(euro_bookmakers, 'lose_change')

    # 计算各方向Pinnacle偏离度
    divergences = {
        'home': abs(p_wc - m_wc),
        'draw': abs(p_dc - m_dc),
        'away': abs(p_lc - m_lc),
    }
    max_side = max(divergences, key=divergences.get)
    max_div = divergences[max_side]

    if max_div < CONF.trap_pinnacle_divergence_threshold:
        return {'score': 0, 'detail': f'Pinnacle与市场一致(最大偏离{max_div:.1f}%)', 'direction': 'none'}

    # Pinnacle偏离方向
    if max_side == 'home':
        p_direction = 'fade_home' if p_wc > m_wc else 'back_home'
    elif max_side == 'away':
        p_direction = 'fade_away' if p_lc > m_lc else 'back_away'
    else:
        p_direction = 'draw_signal'

    score = min(100, (max_div - CONF.trap_pinnacle_divergence_threshold) * 4)

    # Pinnacle看衰热门 vs 看衰冷门
    if (p_direction == 'fade_home' and hot_side == 'home') or \
       (p_direction == 'fade_away' and hot_side == 'away'):
        direction = 'fade_favorite'
        detail = (f'Pinnacle{max_side}变动{p_wc if max_side=="home" else p_lc:+.1f}%'
                  f' vs 市场{m_wc if max_side=="home" else m_lc:+.1f}%'
                  f' → 最敏锐庄家看衰热门·偏离{max_div:.1f}%')
    elif (p_direction == 'back_home' and hot_side == 'home') or \
         (p_direction == 'back_away' and hot_side == 'away'):
        direction = 'none'  # Pinnacle支持热门, 正常
        score = score * 0.3  # 降权
        detail = (f'Pinnacle看好热门(变动更积极)'
                  f' → 市场信号可信·偏离{max_div:.1f}%')
    else:
        direction = 'fade_underdog'
        detail = (f'Pinnacle{max_side}偏离市场{max_div:.1f}%'
                  f' → 最敏锐庄家异常操作')

    return {'score': round(score), 'detail': detail, 'direction': direction}


def _signal_narrative_divergence(betfair_snapshots: list, match_context: dict,
                                   hot_side: str) -> dict:
    """
    信号5: 叙事-资金矛盾 (权重10)

    当公众叙事("双方平局出线")与真实资金流向矛盾时, 叙事的可信度存疑。
    检测: draw_advance_both=True + 平局热度显著下降(>15点)
    """
    if not betfair_snapshots or len(betfair_snapshots) < 3:
        return {'score': 0, 'detail': '快照不足', 'direction': 'none'}

    draw_advance = match_context.get('draw_advance_both', False)
    if not draw_advance:
        return {'score': 0, 'detail': '非平局出线场景', 'direction': 'none'}

    # 检测平局热度趋势
    first_heat = betfair_snapshots[0].get('betfair', {}).get('draw_heat', 0) or 0
    last_heat = betfair_snapshots[-1].get('betfair', {}).get('draw_heat', 0) or 0
    heat_drop = first_heat - last_heat

    if heat_drop < CONF.trap_narrative_heat_divergence:
        return {'score': 0, 'detail': f'平局热度稳定(变动{heat_drop:+.0f})', 'direction': 'none'}

    # 叙事说平局, 但资金离开平局 → 叙事可能是烟雾弹
    score = min(100, (heat_drop - CONF.trap_narrative_heat_divergence) * 3)

    # 判断资金流向: 热度从平局流向哪一方?
    first_home_heat = betfair_snapshots[0].get('betfair', {}).get('home_heat', 0) or 0
    last_home_heat = betfair_snapshots[-1].get('betfair', {}).get('home_heat', 0) or 0
    home_heat_rise = last_home_heat - first_home_heat

    if home_heat_rise > CONF.trap_narrative_heat_divergence:
        direction = 'fade_favorite' if hot_side == 'home' else 'fade_underdog'
        detail = (f'平局热度降{heat_drop:.0f}点→资金流向主胜(+{home_heat_rise:.0f})'
                  f' → "平局出线"叙事与资金背离·诱平嫌疑')
    else:
        direction = 'fade_favorite'
        detail = (f'平局热度降{heat_drop:.0f}点→资金撤离平局'
                  f' → "平局出线"叙事可能为烟雾弹')

    return {'score': round(score), 'detail': detail, 'direction': direction}


def _signal_asian_water_contradiction(asian_companies: list) -> dict:
    """
    信号6: 亚盘水位矛盾 (权重5)

    经典诱盘模式:
    - 升盘+降水 = 真信心 (强方确实强)
    - 升盘+升水 = 诱盘嫌疑 (强方被造热)
    - 降盘+降水 = 真看衰
    - 降盘+升水 = 诱盘嫌疑 (诱导投注弱方)
    """
    if not asian_companies or len(asian_companies) < 5:
        return {'score': 0, 'detail': '亚盘公司数据不足', 'direction': 'none'}

    # 统计盘口变动方向和水位变动方向
    line_up_water_up = 0
    line_up_water_down = 0
    line_down_water_up = 0
    line_down_water_down = 0
    stable_count = 0

    for comp in asian_companies:
        init_line = _safe_float(comp.get('init_line', 0))
        inst_line = _safe_float(comp.get('instant_line', 0))
        init_water_h = _safe_float(comp.get('init_water_home', 0))
        inst_water_h = _safe_float(comp.get('instant_water_home', 0))

        if init_line == 0 or inst_line == 0:
            continue

        line_change = inst_line - init_line
        water_change = inst_water_h - init_water_h

        if abs(line_change) < 0.05:
            stable_count += 1
        elif line_change > 0:  # 升盘
            if water_change > 0.01:
                line_up_water_up += 1
            elif water_change < -0.01:
                line_up_water_down += 1
        else:  # 降盘
            if water_change > 0.01:
                line_down_water_up += 1
            elif water_change < -0.01:
                line_down_water_down += 1

    total = len(asian_companies)
    trap_water_up = line_up_water_up + line_down_water_up  # 升水 = 诱盘模式
    normal_water = line_up_water_down + line_down_water_down  # 降水 = 真实信号

    # 如果升水(诱盘模式)显著多于降水(真实信号)
    if trap_water_up <= normal_water or trap_water_up < total * 0.15:
        return {'score': 0, 'detail': '亚盘水位正常·无明显矛盾', 'direction': 'none'}

    score = min(100, trap_water_up / total * 100 * 1.5)

    # 判断诱盘方向
    if line_down_water_up > line_up_water_up:
        # 降盘+升水: 诱导投注弱方
        direction = 'fade_underdog'
        detail = (f'降盘升水{line_down_water_up}家·升盘升水{line_up_water_up}家'
                  f' → {trap_water_up}/{total}公司水位异常·诱盘模式')
    else:
        # 升盘+升水: 诱导投注强方
        direction = 'fade_favorite'
        detail = (f'升盘升水{line_up_water_up}家·降盘升水{line_down_water_up}家'
                  f' → {trap_water_up}/{total}公司水位异常·诱盘模式')

    return {'score': round(score), 'detail': detail, 'direction': direction}


# ── 主入口 ──

def detect_trap_odds(
    euro_bookmakers: List[dict],
    betfair_snapshots: List[dict],
    xls_consensus_direction: str,
    hot_side: str,
    asian_companies: List[dict] = None,
    jingcai_euro: Optional[dict] = None,
    match_context: Optional[dict] = None,
) -> TrapOddsResult:
    """
    诱盘检测主入口 — 6维度加权评分。

    Args:
        euro_bookmakers: 欧赔逐家公司数据 [{name, win_change, draw_change, lose_change}, ...]
        betfair_snapshots: 必发快照序列 [{betfair: {home_heat, home_volume, home_pnl, ...}}, ...]
        xls_consensus_direction: XLS共识方向 'bullish'/'bearish'/'neutral'
        hot_side: 必发热方 'home'/'draw'/'away'
        asian_companies: 亚盘逐家公司 [{init_line, instant_line, init_water_home, instant_water_home}, ...]
        jingcai_euro: 竞彩官方欧赔 {init_win, now_win, win_change, ...}
        match_context: 比赛上下文 {home, away, gap_level, draw_advance_both}

    Returns:
        TrapOddsResult: 诱盘评分、方向、等级、置信度调整、详细信号、报告摘要
    """
    if not CONF.trap_enabled:
        return TrapOddsResult()

    asian_companies = asian_companies or []
    match_context = match_context or {}
    betfair_snapshots = betfair_snapshots or []

    # ── 六大信号评分 ──
    signals = {}

    # 信号1: 竞彩官方背离 (权重25)
    s1 = _signal_jingcai_divergence(euro_bookmakers, jingcai_euro, hot_side, xls_consensus_direction)
    signals['jingcai_divergence'] = {**s1, 'weight': 25}

    # 信号2: PnL-赔率矛盾 (权重25)
    s2 = _signal_pnl_contradiction(betfair_snapshots, hot_side, euro_bookmakers)
    signals['pnl_contradiction'] = {**s2, 'weight': 25}

    # 信号3: 大资金-赔率背离 (权重20)
    s3 = _signal_volume_odds_divergence(betfair_snapshots, euro_bookmakers, hot_side)
    signals['volume_odds_divergence'] = {**s3, 'weight': 20}

    # 信号4: Pinnacle极端偏离 (权重15)
    s4 = _signal_pinnacle_divergence(euro_bookmakers, hot_side, xls_consensus_direction)
    signals['pinnacle_divergence'] = {**s4, 'weight': 15}

    # 信号5: 叙事-资金矛盾 (权重10)
    s5 = _signal_narrative_divergence(betfair_snapshots, match_context, hot_side)
    signals['narrative_divergence'] = {**s5, 'weight': 10}

    # 信号6: 亚盘水位矛盾 (权重5)
    s6 = _signal_asian_water_contradiction(asian_companies)
    signals['asian_water_contradiction'] = {**s6, 'weight': 5}

    # ── 加权综合 ──
    total_weight = 0
    weighted_score = 0
    direction_votes = {'fade_favorite': 0, 'fade_underdog': 0, 'none': 0}

    for name, s in signals.items():
        w = s['weight']
        score = s['score']
        weighted_score += score * w
        total_weight += w
        if score > 0:
            direction_votes[s['direction']] += w

    trap_score = weighted_score / total_weight if total_weight > 0 else 0

    # 确定方向 (加权多数)
    max_dir = max(direction_votes, key=direction_votes.get)
    if direction_votes[max_dir] > direction_votes.get('none', 0) + 5:
        trap_direction = max_dir
    else:
        trap_direction = 'none'

    # ── 等级 ──
    if trap_score >= CONF.trap_severe_threshold:
        trap_level = 'severe'
    elif trap_score >= CONF.trap_moderate_threshold:
        trap_level = 'moderate'
    elif trap_score >= CONF.trap_mild_threshold:
        trap_level = 'mild'
    else:
        trap_level = 'none'
        trap_direction = 'none'

    # ── 置信度调整 ──
    # 诱盘 → 市场信号不可靠 → 降低置信度
    if trap_level == 'severe':
        confidence_adj = -15
    elif trap_level == 'moderate':
        confidence_adj = -10
    elif trap_level == 'mild':
        confidence_adj = -5
    else:
        confidence_adj = 0

    # 如果有明显反诱盘信号(多个信号支持热门), 略微增加置信度
    if trap_direction == 'none' and trap_score < 10:
        # 检查是否有信号支持热门(反诱盘)
        back_signals = sum(1 for s in signals.values()
                          if s['score'] > 20 and s['direction'] == 'none')
        if back_signals >= 2:
            confidence_adj = 3

    # 确保在范围内
    confidence_adj = max(CONF.trap_confidence_adj_range[0],
                         min(CONF.trap_confidence_adj_range[1], confidence_adj))

    # ── 警告摘要 ──
    warning_parts = []
    active_signals = [(n, s) for n, s in signals.items() if s['score'] >= 20]
    active_signals.sort(key=lambda x: x[1]['score'], reverse=True)

    for name, s in active_signals[:3]:  # 最多3个
        signal_cn = {
            'jingcai_divergence': '竞彩背离',
            'pnl_contradiction': 'PnL矛盾',
            'volume_odds_divergence': '资金背离',
            'pinnacle_divergence': 'Pinnacle偏离',
            'narrative_divergence': '叙事矛盾',
            'asian_water_contradiction': '水位异常',
        }.get(name, name)
        warning_parts.append(f'{signal_cn}({s["score"]:.0f})')

    if trap_level == 'severe':
        warning = (f'🚨 诱盘警报(严重·{trap_score:.0f}分): '
                   + ' | '.join(warning_parts)
                   + f' → 市场信号可信度严重降低·置信度{confidence_adj:+d}%')
    elif trap_level == 'moderate':
        warning = (f'⚠️ 诱盘预警(中度·{trap_score:.0f}分): '
                   + ' | '.join(warning_parts)
                   + f' → 市场信号需谨慎解读·置信度{confidence_adj:+d}%')
    elif trap_level == 'mild':
        warning = (f'🟡 诱盘迹象(轻度·{trap_score:.0f}分): '
                   + ' | '.join(warning_parts)
                   + f' → 注意市场信号可靠性')
    else:
        warning = ''

    return TrapOddsResult(
        trap_score=round(trap_score, 1),
        trap_direction=trap_direction,
        trap_level=trap_level,
        confidence_adj=confidence_adj,
        signals={name: {'score': s['score'], 'detail': s['detail'], 'direction': s['direction'],
                         'weight': s['weight']} for name, s in signals.items()},
        warning=warning,
    )


# ── 独立测试 ──
if __name__ == '__main__':
    print("V3.41 诱盘检测模块")
    print(f"  严重阈值: {CONF.trap_severe_threshold}")
    print(f"  中度阈值: {CONF.trap_moderate_threshold}")
    print(f"  轻度阈值: {CONF.trap_mild_threshold}")
    print(f"  竞彩背离阈值: {CONF.trap_jingcai_divergence_threshold}%")
    print(f"  Pinnacle偏离阈值: {CONF.trap_pinnacle_divergence_threshold}%")
    print(f"  庄家亏损阈值: {CONF.trap_pnl_contradiction_threshold:,.0f}")
    print(f"  置信度调整范围: {CONF.trap_confidence_adj_range}")
    print()
    print("此模块需要从 pre_match_report.py 调用, 传入 XLS + 必发数据。")

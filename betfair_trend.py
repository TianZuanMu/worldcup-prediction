# -*- coding: utf-8 -*-
"""
🆕 V4.5 P2: 必发跨版本趋势分析

从 betfair_data/ JSON 的 snapshots 数组中提取趋势信号:
- 冷热趋势 (heating/cooling/stable)
- 庄家盈亏趋势 (worsening/improving/stable)
- 大额卖单新增
- 资金方向稳定性
- 综合 alert_level → 报告摘要标签
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BetfairTrendResult:
    """必发趋势分析结果"""
    versions_analyzed: int = 0
    cold_trend: str = 'stable'         # 'heating' | 'cooling' | 'stable'
    cold_change: float = 0.0           # 冷热变化量 (latest - earliest)
    cold_early: float = 0.0
    cold_late: float = 0.0
    pnl_trend: str = 'stable'          # 'worsening' | 'improving' | 'stable'
    pnl_change: float = 0.0            # PnL变化量 (latest - earliest)
    big_sell_new: int = 0              # 最近阶段新增的大额卖单
    money_side_stable: bool = True     # 资金方向是否跨版本一致
    alert_level: str = 'none'          # 'none' | 'watch' | 'warning'
    summary: str = ''                  # 趋势解读摘要


def analyze_betfair_trend(snapshots: List[dict]) -> Optional[BetfairTrendResult]:
    """
    从快照序列中提取必发趋势。

    Args:
        snapshots: betfair_data JSON 的 snapshots 数组

    Returns:
        BetfairTrendResult 或 None (快照不足3个时)
    """
    if not snapshots or len(snapshots) < 3:
        return None

    # 过滤有效快照
    valid = []
    for s in snapshots:
        bf = s.get('betfair', {})
        hp = bf.get('home_price', 0) or 0
        ap = bf.get('away_price', 0) or 0
        if hp > 0 and ap > 0:
            valid.append(s)

    if len(valid) < 3:
        return None

    result = BetfairTrendResult()
    result.versions_analyzed = len(valid)

    # ═══ 1. 冷热趋势 ═══
    # 取热方冷热值 (取绝对值的max)
    def _get_hot_heat(snap):
        bf = snap.get('betfair', {})
        heats = [bf.get('home_heat', 0) or 0, bf.get('draw_heat', 0) or 0, bf.get('away_heat', 0) or 0]
        return max(heats)  # 最正=最热

    # 三段法: 早期·中期·晚期
    n = len(valid)
    seg = max(n // 3, 1)
    early = valid[:seg]
    late = valid[-seg:]

    early_heat = sum(_get_hot_heat(s) for s in early) / len(early)
    late_heat = sum(_get_hot_heat(s) for s in late) / len(late)

    result.cold_early = round(early_heat)
    result.cold_late = round(late_heat)
    result.cold_change = late_heat - early_heat

    if result.cold_change >= 30:
        result.cold_trend = 'surging'
    elif result.cold_change >= 10:
        result.cold_trend = 'heating'
    elif result.cold_change <= -20:
        result.cold_trend = 'fading'
    elif result.cold_change <= -10:
        result.cold_trend = 'cooling'
    else:
        result.cold_trend = 'stable'

    # ═══ 2. 庄家盈亏趋势 ═══
    def _get_hot_pnl(snap):
        bf = snap.get('betfair', {})
        # 取热方的PnL
        heats = [bf.get('home_heat', 0) or 0, bf.get('draw_heat', 0) or 0, bf.get('away_heat', 0) or 0]
        pnls = [bf.get('home_pnl', 0) or 0, bf.get('draw_pnl', 0) or 0, bf.get('away_pnl', 0) or 0]
        hot_idx = heats.index(max(heats))
        return pnls[hot_idx]

    early_pnl = sum(_get_hot_pnl(s) for s in early) / len(early)
    late_pnl = sum(_get_hot_pnl(s) for s in late) / len(late)
    result.pnl_change = late_pnl - early_pnl

    if result.pnl_change < -500000:
        result.pnl_trend = 'worsening'
    elif result.pnl_change > 500000:
        result.pnl_trend = 'improving'
    else:
        result.pnl_trend = 'stable'

    # ═══ 3. 大额卖单新增 ═══
    early_trades = []
    for s in early:
        for t in s.get('big_trades', []):
            if t.get('direction') == '卖' and t.get('volume', 0) > 50000:
                early_trades.append(t.get('volume', 0))
    late_trades = []
    for s in late:
        for t in s.get('big_trades', []):
            if t.get('direction') == '卖' and t.get('volume', 0) > 50000:
                late_trades.append(t.get('volume', 0))
    result.big_sell_new = max(0, len(late_trades) - len(early_trades))

    # ═══ 4. 资金方向稳定性 ═══
    hot_sides = []
    for s in valid:
        bf = s.get('betfair', {})
        heats = [bf.get('home_heat', 0) or 0, bf.get('draw_heat', 0) or 0, bf.get('away_heat', 0) or 0]
        hot_sides.append(['home', 'draw', 'away'][heats.index(max(heats))])
    # 检查是否所有版本资金方向一致
    result.money_side_stable = len(set(hot_sides)) == 1

    # ═══ 5. 综合 alert_level ═══
    warning_signals = 0
    watch_signals = 0

    if result.cold_trend in ('surging', 'fading'):
        watch_signals += 1
    if result.pnl_trend == 'worsening':
        watch_signals += 1
    if result.big_sell_new >= 2:
        watch_signals += 1
    if not result.money_side_stable:
        watch_signals += 1

    # 恶化: 冷热骤变 + PnL恶化 + 新增卖单
    if result.cold_trend == 'surging' and result.pnl_trend == 'worsening' and result.big_sell_new >= 1:
        result.alert_level = 'warning'
        result.summary = '⚠️ 资金趋势恶化·警惕市场分歧'
    elif watch_signals >= 2:
        result.alert_level = 'watch'
        result.summary = '资金趋势异常·建议关注'
    else:
        result.alert_level = 'none'
        result.summary = '资金趋势稳定'

    return result

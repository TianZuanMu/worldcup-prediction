# -*- coding: utf-8 -*-
"""
V2.15 XLS跨版本历史趋势分析

填补空白: pre_match_report 此前仅使用最新XLS的单版本开盘→即时变化,
          未利用多次下载积累的历史版本进行趋势追踪。

新增:
  1. 穿盘率跨版本趋势 (连续下降/上升预警)
  2. 欧赔共识加速/减速/反转检测
  3. 赔率突然跳变检测 (单版本变化>2σ)
  4. 大小球盘口漂移追踪

用法:
  from xls_trend_analysis import analyze_xls_trend
  trend = analyze_xls_trend('葡萄牙VS民主刚果')
  # → XlsTrendResult with signals, metrics, confidence adjustments
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
import math

from config import CONF
from xls_reader_xlrd import read_all_versions


@dataclass
class XlsTrendResult:
    """XLS跨版本趋势分析结果"""
    match_name: str
    total_versions: int = 0
    analyzed: bool = False          # 是否有足够版本做分析

    # 穿盘率趋势
    cover_rate_trend: str = ''       # 'declining'/'rising'/'stable'
    cover_rate_first: float = 0
    cover_rate_last: float = 0
    cover_rate_change: float = 0     # 累计变化(百分点)
    cover_rate_warning: bool = False
    cover_rate_detail: str = ''

    # 欧赔共识趋势
    consensus_trend: str = ''        # 'accelerating'/'decelerating'/'reversing'/'stable'
    consensus_first: float = 0
    consensus_last: float = 0
    consensus_accelerating: bool = False
    consensus_detail: str = ''

    # 欧赔即时值趋势
    odds_home_trend: str = ''        # 'shortening'/'lengthening'/'stable'
    odds_home_first: float = 0
    odds_home_last: float = 0
    odds_home_change: float = 0

    # 大小球趋势
    totals_trend: str = ''           # 'shrinking'/'growing'/'stable'
    totals_line_first: float = 0
    totals_line_last: float = 0

    # 跳变检测
    has_jump: bool = False
    jump_detail: str = ''

    # 综合信号
    signals: List[str] = field(default_factory=list)
    confidence_adjustment: float = 0   # -5 to +5
    alert_level: str = ''              # 'none'/'info'/'warning'/'critical'


def analyze_xls_trend(match_name: str) -> XlsTrendResult:
    """
    主入口: 分析XLS跨版本历史趋势

    Args:
        match_name: '葡萄牙VS民主刚果' 格式

    Returns:
        XlsTrendResult 包含所有趋势信号
    """
    result = XlsTrendResult(match_name=match_name)

    try:
        data = read_all_versions(match_name)
    except Exception as e:
        result.signals.append(f'XLS趋势加载失败: {e}')
        return result

    # ── 1. 穿盘率趋势 ──
    _analyze_cover_rate(result, data.get('handicap_index', []))

    # ── 2. 欧赔共识趋势 ──
    _analyze_euro_consensus(result, data.get('european', []))

    # ── 3. 欧赔即时值趋势 ──
    _analyze_euro_instant(result, data.get('european', []))

    # ── 4. 大小球趋势 ──
    _analyze_totals(result, data.get('totals', []))

    # ── 5. 跳变检测 ──
    _detect_jumps(result, data.get('european', []))

    # ── 综合评估 ──
    _synthesize(result)

    result.total_versions = max(
        len(data.get('european', [])),
        len(data.get('handicap_index', [])),
    )
    result.analyzed = result.total_versions >= CONF.xls_trend_min_versions

    return result


def _analyze_cover_rate(result: XlsTrendResult, versions: list):
    """穿盘率跨版本趋势"""
    valid = []
    for v in versions:
        d = v.get('data', {})
        bl = d.get('by_line', {})
        primary = d.get('primary_line', None)
        if primary and primary in bl:
            cr = bl[primary].get('avg_win_prob', 0)
            if cr > 0:
                valid.append((v['version'], v['mtime'], cr))

    if len(valid) < CONF.xls_trend_min_versions:
        return

    result.cover_rate_first = valid[0][2]
    result.cover_rate_last = valid[-1][2]
    result.cover_rate_change = result.cover_rate_last - result.cover_rate_first

    # 趋势判断
    recent_3 = [v[2] for v in valid[-3:]]
    if len(recent_3) >= 3:
        if all(recent_3[i] > recent_3[i+1] for i in range(len(recent_3)-1)):
            result.cover_rate_trend = 'declining'
            if abs(result.cover_rate_change) >= CONF.xls_trend_cover_decline_warn:
                result.cover_rate_warning = True
                result.cover_rate_detail = (
                    f'穿盘率持续下降: {result.cover_rate_first:.1f}%→{result.cover_rate_last:.1f}%'
                    f' ({result.cover_rate_change:+.1f}百分点·{len(valid)}版本)'
                )
                result.signals.append(f'🔴 XLS穿盘率连续下降: {result.cover_rate_change:+.1f}pp')
        elif all(recent_3[i] < recent_3[i+1] for i in range(len(recent_3)-1)):
            result.cover_rate_trend = 'rising'
        else:
            result.cover_rate_trend = 'stable'

    # 陡降检测
    if len(valid) >= 2:
        last_drop = valid[-2][2] - valid[-1][2]
        if last_drop >= CONF.xls_trend_cover_steep:
            result.signals.append(f'🟡 穿盘率陡降{last_drop:.1f}pp (最新版)')


def _analyze_euro_consensus(result: XlsTrendResult, versions: list):
    """欧赔共识趋势 (win_up - win_down) / total"""
    valid = []
    for v in versions:
        d = v.get('data', {})
        stats = d.get('stats', {})
        up = stats.get('win_up_count', 0)
        down = stats.get('win_down_count', 0)
        bk_list = d.get('bookmakers', [])
        total = len(bk_list) if bk_list else 0
        if total > 0:
            pct = (up - down) / total * 100
            valid.append((v['version'], v['mtime'], pct, up, down, total))

    if len(valid) < CONF.xls_trend_min_versions:
        return

    result.consensus_first = valid[0][2]
    result.consensus_last = valid[-1][2]
    consensus_change = result.consensus_last - result.consensus_first

    # 加速检测: 后N/2版本的均变化速率 vs 前N/2版本
    n = len(valid)
    first_half_range = 0.0
    second_half_range = 0.0
    if n >= 4:
        half = n // 2
        first_half_range = abs(valid[half-1][2] - valid[0][2])
        second_half_range = abs(valid[-1][2] - valid[half][2])
        if second_half_range > first_half_range * CONF.xls_trend_consensus_accel and second_half_range > 3:
            result.consensus_accelerating = True
            result.consensus_trend = '持续增强'  # 🆕 V4.5 P2: 中文标签
            result.consensus_detail = (
                f'共识加速: 前{half}版变动{first_half_range:.1f}pp→后{half}版{second_half_range:.1f}pp'
            )
            result.signals.append(f'📈 XLS共识加速移动 (+{second_half_range:.1f}pp)')

    # 反转检测
    if n >= 2:
        prev = valid[-2][2]
        curr = valid[-1][2]
        # 方向反转: 正→负 或 负→正
        if (prev > 3 and curr < -3) or (prev < -3 and curr > 3):
            result.consensus_trend = 'reversing'
            result.consensus_detail = f'共识反转: {prev:+.1f}%→{curr:+.1f}%'
            result.signals.append(f'⚠️ XLS共识方向反转 ({prev:+.1f}%→{curr:+.1f}%)')

    if not result.consensus_trend:
        if abs(consensus_change) < 3:
            result.consensus_trend = '趋稳'
        else:
            result.consensus_trend = '增强放缓' if first_half_range > second_half_range * 1.5 else '趋稳'  # 🆕 V4.5 P2


def _analyze_euro_instant(result: XlsTrendResult, versions: list):
    """欧赔即时值趋势 (主胜赔率变化)"""
    valid = []
    for v in versions:
        d = v.get('data', {})
        inst = d.get('summary', {}).get('instant', {})
        w = inst.get('win')
        if w is not None:
            valid.append((v['version'], v['mtime'], float(w)))

    if len(valid) < CONF.xls_trend_min_versions:
        return

    result.odds_home_first = valid[0][2]
    result.odds_home_last = valid[-1][2]
    result.odds_home_change = result.odds_home_last - result.odds_home_first

    if result.odds_home_change < -0.05:
        result.odds_home_trend = 'shortening'
    elif result.odds_home_change > 0.05:
        result.odds_home_trend = 'lengthening'
    else:
        result.odds_home_trend = 'stable'


def _analyze_totals(result: XlsTrendResult, versions: list):
    """大小球盘口趋势"""
    valid = []
    for v in versions:
        d = v.get('data', {})
        la = d.get('line_analysis', {})
        line = la.get('instant_line')
        if line is not None:
            valid.append((v['version'], v['mtime'], float(line)))

    if len(valid) < CONF.xls_trend_min_versions:
        return

    result.totals_line_first = valid[0][2]
    result.totals_line_last = valid[-1][2]
    change = result.totals_line_last - result.totals_line_first

    if change < -0.15:
        result.totals_trend = 'shrinking'
        result.signals.append(f'📉 大小球持续退盘: {result.totals_line_first:.2f}→{result.totals_line_last:.2f}')
    elif change > 0.15:
        result.totals_trend = 'growing'
    else:
        result.totals_trend = 'stable'


def _detect_jumps(result: XlsTrendResult, versions: list):
    """检测单版本异常跳变"""
    # 收集所有版本的 win_avg_change
    changes = []
    for v in versions:
        d = v.get('data', {})
        stats = d.get('stats', {})
        wc = stats.get('win_avg_change', 0)
        if wc != 0:
            changes.append((v['version'], wc))

    if len(changes) < 4:
        return

    values = [c[1] for c in changes]
    mean = sum(values) / len(values)
    std = math.sqrt(sum((x - mean)**2 for x in values) / len(values))
    if std < 0.5:
        return

    # 检查最新版本是否超过2σ
    last_val = values[-1]
    if abs(last_val - mean) > CONF.xls_trend_jump_sigma * std:
        result.has_jump = True
        direction = '上升' if last_val > mean else '下降'
        result.jump_detail = (
            f'赔率跳变: 最新版主胜变动{last_val:+.1f}%'
            f' (均值{mean:+.1f}%±{std:.1f}%·{direction}异常)'
        )
        result.signals.append(f'⚡ XLS赔率跳变检测: {result.jump_detail}')


def _synthesize(result: XlsTrendResult):
    """综合评估: 汇总信号, 计算置信度调整和预警级别"""
    if not result.analyzed:
        result.alert_level = 'none'
        return

    adjustment = 0.0
    alerts = 0
    critical = 0

    # 穿盘率下降 → 降低热门穿盘信心
    if result.cover_rate_warning:
        adjustment -= 3
        alerts += 1

    # 共识加速 → 信号可靠性增强/减弱
    if result.consensus_accelerating:
        if result.consensus_last > 0:
            adjustment -= 2  # 看空加速
        else:
            adjustment += 2  # 看多加速
        alerts += 1

    # 🆕 V3.4: 共识反转 → 方向决定信号
    if result.consensus_trend == 'reversing':
        # 从看衰转为看好热队(bearish→bullish) → 强牛信号
        if result.consensus_first > 30 and result.consensus_last < -10:
            adjustment += 5  # 市场倒戈热队·强牛
        # 从看好转为看衰(bullish→bearish) → 危险信号
        elif result.consensus_first < -30 and result.consensus_last > 10:
            adjustment -= 5  # 市场倒戈冷门·警惕
        else:
            adjustment -= 2  # 一般反转·轻微不确定

    # 跳变 → 市场异常
    if result.has_jump:
        adjustment -= 2
        alerts += 1

    # 大小球退盘
    if result.totals_trend == 'shrinking':
        alerts += 1

    result.confidence_adjustment = max(CONF.xls_trend_adj_range[0], min(CONF.xls_trend_adj_range[1], adjustment))

    if critical > 0:
        result.alert_level = 'critical'
    elif alerts >= 3:
        result.alert_level = 'warning'
    elif alerts >= 1:
        result.alert_level = 'info'
    else:
        result.alert_level = 'none'


def trend_summary(result: XlsTrendResult) -> str:
    """生成趋势分析一句话摘要"""
    if not result.analyzed:
        return f'XLS趋势: 版本不足({result.total_versions}<{CONF.xls_trend_min_versions})'

    parts = []
    if result.cover_rate_trend == 'declining':
        parts.append(f'穿盘率↓{result.cover_rate_change:+.1f}pp')
    if result.consensus_accelerating:
        parts.append('共识加速')
    if result.consensus_trend == 'reversing':
        parts.append('⚠️共识反转')
    if result.has_jump:
        parts.append('⚡跳变')
    if result.totals_trend == 'shrinking':
        parts.append('大小球↓')

    signals_str = ' | '.join(parts) if parts else '无异常趋势'
    adj = result.confidence_adjustment
    adj_str = f' [调整{adj:+.0f}%]' if adj != 0 else ''
    return f'XLS趋势({result.total_versions}版): {signals_str}{adj_str}'


# ── 命令行测试 ──
if __name__ == '__main__':
    import sys
    match = sys.argv[1] if len(sys.argv) > 1 else '葡萄牙VS民主刚果'
    result = analyze_xls_trend(match)
    print(f'\n{"="*60}')
    print(f'  XLS跨版本趋势: {match}')
    print(f'{"="*60}')
    print(f'  版本数: {result.total_versions}')
    print(f'  可分析: {result.analyzed}')
    print()
    print(f'  ── 穿盘率 ──')
    print(f'  趋势: {result.cover_rate_trend}')
    print(f'  变化: {result.cover_rate_first:.1f}%→{result.cover_rate_last:.1f}% ({result.cover_rate_change:+.1f}pp)')
    print(f'  预警: {result.cover_rate_warning}')
    print()
    print(f'  ── 欧赔共识 ──')
    print(f'  趋势: {result.consensus_trend}')
    print(f'  变化: {result.consensus_first:+.1f}%→{result.consensus_last:+.1f}%')
    print(f'  加速: {result.consensus_accelerating}')
    print()
    print(f'  ── 主胜赔率 ──')
    print(f'  趋势: {result.odds_home_trend}')
    print(f'  变化: {result.odds_home_first:.2f}→{result.odds_home_last:.2f}')
    print()
    print(f'  ── 大小球 ──')
    print(f'  趋势: {result.totals_trend}')
    print(f'  变化: {result.totals_line_first:.2f}→{result.totals_line_last:.2f}')
    print()
    print(f'  ── 综合 ──')
    print(f'  信号: {result.signals}')
    print(f'  调整: {result.confidence_adjustment:+.0f}%')
    print(f'  级别: {result.alert_level}')
    print(f'  摘要: {trend_summary(result)}')

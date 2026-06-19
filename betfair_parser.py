# -*- coding: utf-8 -*-
"""
必发数据解析器 — 自动解析用户粘贴的原始必发数据

输入: 原始必发热度分析表 + 大额交易明细 (纯文本)
输出: 结构化 dict，含冷热指数、庄家盈亏、共识污染、大单方向

用法:
  from betfair_parser import parse_betfair_text
  data = parse_betfair_text(raw_text)
  print(data['summary'])  # 一键摘要
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class BetfairMatch:
    """解析后的必发比赛数据"""
    match_name: str = ""
    parsed_at: str = ""

    # 热度数据
    home_odds: float = 0.0
    draw_odds: float = 0.0
    away_odds: float = 0.0
    home_prob: float = 0.0
    draw_prob: float = 0.0
    away_prob: float = 0.0
    home_trade_ratio: float = 0.0
    draw_trade_ratio: float = 0.0
    away_trade_ratio: float = 0.0
    home_bf_price: float = 0.0
    draw_bf_price: float = 0.0
    away_bf_price: float = 0.0
    home_volume: float = 0.0
    draw_volume: float = 0.0
    away_volume: float = 0.0
    home_pnl: float = 0.0
    draw_pnl: float = 0.0
    away_pnl: float = 0.0
    home_cold: float = 0.0      # 冷热指数
    draw_cold: float = 0.0
    away_cold: float = 0.0
    home_profit_idx: float = 0.0  # 盈亏指数
    draw_profit_idx: float = 0.0
    away_profit_idx: float = 0.0

    # 大额交易
    big_trades: list = field(default_factory=list)

    # 分析结果
    hot_side: str = ""           # 'home'/'draw'/'away'
    hot_index: float = 0.0       # 热门方向冷热指数
    is_real_hot: bool = False    # 真过热 (冷热>=30 + 庄亏)
    is_overheat: bool = False    # 冷热>=30
    is_severe_overheat: bool = False  # 冷热>=50
    consensus_pollution: bool = False  # 欧赔共识污染
    pollution_gap: float = 0.0   # 交易比例-欧赔概率差
    big_sell_warning: bool = False  # 大额卖单警告
    big_sell_detail: str = ""
    big_sell_count: int = 0            # 🆕 大额卖单笔数
    big_sell_total_volume: float = 0.0 # 🆕 大额卖单总金额
    data_tip: str = ""


def parse_betfair_text(text: str, match_name: str = "") -> BetfairMatch:
    """解析必发原始文本，返回结构化数据"""
    m = BetfairMatch(match_name=match_name or _extract_match_name(text))
    m.parsed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = text.strip().split('\n')

    # ── 解析热度表行 ──
    _parse_heat_rows(m, lines)

    # ── 解析数据提点 ──
    _parse_tips(m, lines)

    # ── 检测共识污染 ──
    _detect_pollution(m)

    # ── 判定过热 ──
    _classify_hot(m)

    # ── 解析大额交易 ──
    _parse_big_trades(m, lines)

    # ── 大单警告 ──
    _check_big_sell(m)

    return m


def _extract_match_name(text: str) -> str:
    """从文本首行提取比赛名"""
    first_line = text.strip().split('\n')[0]
    # 清理常见前缀
    first_line = re.sub(r'^#+\s*', '', first_line)
    return first_line.strip()[:50]


def _parse_heat_rows(m: BetfairMatch, lines: list):
    """解析热度表的三行数据 (主胜/平局/客胜)——按首词自动识别"""
    parsed_sides = set()
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        first_word = line.split()[0] if line.split() else ''

        # 跳过非数据行
        if first_word in ('赔率', '百家欧赔', '热度分析', '综合'):
            continue
        # 跳过标题行 (含vs)
        if 'vs' in line.lower() or 'VS' in line:
            continue
        # 跳过纯数值开头的行
        if re.match(r'^[\d.]+', first_word):
            continue

        # 识别: 平局行
        if first_word in ('平局', '平'):
            if 'draw' not in parsed_sides:
                _parse_one_row(m, line, 'draw')
                parsed_sides.add('draw')
            continue

        # 其余: 队名行 → 按顺序分配 home → away
        if 'home' not in parsed_sides:
            _parse_one_row(m, line, 'home')
            parsed_sides.add('home')
        elif 'away' not in parsed_sides:
            _parse_one_row(m, line, 'away')
            parsed_sides.add('away')


def _parse_one_row(m: BetfairMatch, line: str, side: str):
    """解析一行热度数据——从行尾提取冷热/盈亏，从行首提取赔率"""
    # 移除队名标签（行首非数字部分）
    cleaned = line.strip()

    # 提取所有数值（含负号、含逗号的千分位）
    tokens = re.findall(r'-?[\d,]+\.?\d*%?', cleaned)
    values = []
    for t in tokens:
        t = t.replace(',', '').replace('%', '')
        try:
            values.append(float(t))
        except ValueError:
            continue

    if len(values) < 7:
        return

    # 列顺序: 赔率, 概率, (北单), 必发比例, 成交价, 成交量, 庄家盈亏, (必发指数), 冷热, 盈亏指数
    # 因为有被过滤的'-'列，所以实际位置取决于'-'的数量
    # 稳妥策略: 从后往前读 (冷热和盈亏指数总是在最后)
    # values[-2] = 冷热指数, values[-1] = 盈亏指数
    # values[-3] = 庄家盈亏
    # 从前往后: values[0]=赔率, values[1]=概率

    try:
        odds = values[0]
        prob = values[1] / 100 if values[1] > 1 else values[1]

        # 从后往前定位
        profit_idx = values[-1]
        cold = values[-2]
        pnl = values[-3]
        volume = values[-4]
        bf_price = values[-5]
        trade = values[-6] / 100 if values[-6] > 1 else values[-6]

        if side == 'home':
            m.home_odds, m.home_prob = odds, prob
            m.home_trade_ratio, m.home_bf_price = trade, bf_price
            m.home_volume, m.home_pnl = volume, pnl
            m.home_cold, m.home_profit_idx = cold, profit_idx
        elif side == 'draw':
            m.draw_odds, m.draw_prob = odds, prob
            m.draw_trade_ratio, m.draw_bf_price = trade, bf_price
            m.draw_volume, m.draw_pnl = volume, pnl
            m.draw_cold, m.draw_profit_idx = cold, profit_idx
        elif side == 'away':
            m.away_odds, m.away_prob = odds, prob
            m.away_trade_ratio, m.away_bf_price = trade, bf_price
            m.away_volume, m.away_pnl = volume, pnl
            m.away_cold, m.away_profit_idx = cold, profit_idx
    except (ValueError, IndexError):
        pass


def _parse_tips(m: BetfairMatch, lines: list):
    """提取数据提点"""
    for line in lines:
        if '数据提点' in line:
            m.data_tip = line.split('数据提点', 1)[-1].strip()
            break


def _detect_pollution(m: BetfairMatch):
    """共识污染检测: 交易比例与欧赔概率差>15% + 冷热>=30 + 庄亏"""
    for side, trade, prob, cold, pnl in [
        ('home', m.home_trade_ratio, m.home_prob, m.home_cold, m.home_pnl),
        ('draw', m.draw_trade_ratio, m.draw_prob, m.draw_cold, m.draw_pnl),
        ('away', m.away_trade_ratio, m.away_prob, m.away_cold, m.away_pnl),
    ]:
        gap = abs(trade - prob) * 100  # 百分比点
        m.pollution_gap = max(m.pollution_gap, gap)
        if gap > 15 and cold >= 30 and pnl < 0:
            m.consensus_pollution = True


def _classify_hot(m: BetfairMatch):
    """判定真/假过热 (正冷热=过热方向)"""
    sides = [('home', m.home_cold, m.home_pnl),
             ('draw', m.draw_cold, m.draw_pnl),
             ('away', m.away_cold, m.away_pnl)]

    # 找冷热指数最高的方向 (正=热)
    max_cold = max(s[1] for s in sides)
    for side, cold, pnl in sides:
        if cold == max_cold:
            m.hot_side = side
            m.hot_index = cold
            m.is_overheat = cold >= 30
            m.is_severe_overheat = cold >= 50
            m.is_real_hot = (cold >= 30 and pnl < 0)
            break


def _parse_big_trades(m: BetfairMatch, lines: list):
    """解析大额交易明细表"""
    in_table = False
    for line in lines:
        line = line.strip()
        if '综合' in line and '属性' in line:
            in_table = True
            continue
        if not in_table:
            continue
        if not line or '必发大额' in line or '数据提点' in line:
            continue

        # 解析: 主/平/客 | 买/卖 | 成交量 | 时间 | 比例
        parts = line.split()
        if len(parts) >= 4:
            try:
                direction = parts[0]
                action = parts[1]
                volume = float(parts[2])
                time_str = parts[3] if len(parts) > 3 else ''
                ratio = parts[4] if len(parts) > 4 else ''

                m.big_trades.append({
                    'direction': direction,
                    'action': action,
                    'volume': volume,
                    'time': time_str,
                    'ratio': ratio,
                })
            except (ValueError, IndexError):
                continue


def _check_big_sell(m: BetfairMatch):
    """检测大额卖单 (Lay)"""
    if m.hot_side == 'home':
        sell_side = '主'
    elif m.hot_side == 'away':
        sell_side = '客'
    else:
        return

    big_sells = [t for t in m.big_trades
                 if t['direction'] == sell_side and t['action'] == '卖' and t['volume'] > 50000]
    if big_sells:
        m.big_sell_warning = True
        m.big_sell_count = len(big_sells)
        m.big_sell_total_volume = sum(t['volume'] for t in big_sells)
        m.big_sell_detail = f"{sell_side}胜大额卖单 {m.big_sell_count}笔, 共{m.big_sell_total_volume:,.0f}"


def summary(m: BetfairMatch) -> str:
    """一键摘要"""
    lines = [
        f"📋 {m.match_name} 必发解析",
        f"{'='*50}",
        f"冷热: 主{m.home_cold:+.0f} 平{m.draw_cold:+.0f} 客{m.away_cold:+.0f}",
        f"庄亏: 主{m.home_pnl:+,.0f} 平{m.draw_pnl:+,.0f} 客{m.away_pnl:+,.0f}",
        f"热门: {m.hot_side} (冷热{m.hot_index:+.0f})",
        f"过热: {'真过热' if m.is_real_hot else '假过热' if m.is_overheat else '未过热'}",
        f"共识污染: {'⚠️ 是' if m.consensus_pollution else '✅ 否'} (差{m.pollution_gap:.1f}%)",
    ]
    if m.big_sell_warning:
        lines.append(f"🔴 大单警告: {m.big_sell_detail}")
    if m.data_tip:
        lines.append(f"💡 {m.data_tip[:80]}")
    return '\n'.join(lines)


# ── 命令行测试 ──
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    result = parse_betfair_text(text)
    print(summary(result))
    print(f"\n大额交易: {len(result.big_trades)}笔")
    for t in result.big_trades[:5]:
        print(f"  {t['direction']}{t['action']} {t['volume']:,.0f} @ {t['time']}")

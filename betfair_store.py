# -*- coding: utf-8 -*-
"""
必发数据存储模块 —— 自动保存·多时段追踪·趋势对比

每次用户提供必发数据时自动调用 save_betfair()。
同一场比赛多次提供 → 自动追加新快照·保留历史。
支持 P1(24h)→P2(6h)→P3(2h)→P4(90min) 渐进预测。

存储位置: C:/Users/A/PyCharmMiscProject/betfair_data/{match_name}.json

用法:
  from betfair_store import save_betfair, load_betfair, compare_snapshots

  # 保存
  data = {
      'odds': {'home': 2.04, 'draw': 3.43, 'away': 3.63},
      'betfair': {
          'home_price': 2.14, 'draw_price': 3.60, 'away_price': 3.95,
          'home_volume': 4179426, 'draw_volume': 989767, 'away_volume': 1223025,
          'home_pnl': -2.55, 'draw_pnl': 2.83, 'away_pnl': 1.56,
          'home_heat': 40, 'draw_heat': -44, 'away_heat': -27,
      },
      'big_trades': [...],
      'notes': '数据提点内容',
  }
  save_betfair('荷兰VS日本', data, kickoff='2026-06-15T04:00')

  # 对比
  compare_snapshots('荷兰VS日本')
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any


DATA_DIR = Path(r"C:\Users\A\PyCharmMiscProject\betfair_data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 北京时区
CST = timezone(timedelta(hours=8))


def _match_file(match_name: str) -> Path:
    """获取比赛数据文件路径"""
    safe_name = match_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
    return DATA_DIR / f"{safe_name}.json"


def _now_cst() -> str:
    """当前北京时间 ISO 格式"""
    return datetime.now(CST).strftime('%Y-%m-%dT%H:%M:%S')


def _detect_phase(kickoff_str: str) -> str:
    """
    根据距开球时间自动检测预测阶段。

    P1: >12h before kickoff
    P2: 4-12h before
    P3: 1.5-4h before
    P4: <1.5h before
    POST: after kickoff
    """
    if not kickoff_str:
        return 'P1'

    try:
        # 解析开球时间 (北京时间)
        if 'T' in kickoff_str:
            kickoff = datetime.fromisoformat(kickoff_str)
        else:
            kickoff = datetime.strptime(kickoff_str, '%Y-%m-%d %H:%M')

        # 如果 kickoff 没有时区信息，假设为北京时间
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=CST)

        now = datetime.now(CST)
        hours_before = (kickoff - now).total_seconds() / 3600

        if hours_before < 0:
            return 'POST'   # 已开赛
        elif hours_before < 1.5:
            return 'P4'     # 赛前90分钟内
        elif hours_before < 4:
            return 'P3'     # 赛前2-4小时
        elif hours_before < 12:
            return 'P2'     # 赛前6-12小时
        else:
            return 'P1'     # 赛前24小时+
    except (ValueError, TypeError):
        return 'P1'


def save_betfair(
    match_name: str,
    odds: Dict[str, float],
    betfair: Dict[str, Any],
    big_trades: Optional[List[Dict]] = None,
    notes: str = '',
    kickoff: str = '',
    source: str = '',
) -> Dict[str, Any]:
    """
    保存一次必发数据快照。

    参数:
      match_name: 比赛名称 (如 '荷兰VS日本')
      odds: 百家欧赔 {'home': 2.04, 'draw': 3.43, 'away': 3.63}
      betfair: 必发数据 {
          'home_price': 2.14, 'draw_price': 3.60, 'away_price': 3.95,
          'home_volume': 4179426, 'draw_volume': 989767, 'away_volume': 1223025,
          'home_pnl': -2.55, 'draw_pnl': 2.83, 'away_pnl': 1.56,  # 单位: M
          'home_heat': 40, 'draw_heat': -44, 'away_heat': -27,
      }
      big_trades: 大额交易列表 [{'side':'主','direction':'买','volume':6869,'time':'23:09'}, ...]
      notes: 数据提点文字
      kickoff: 开球时间 '2026-06-15T04:00'
      source: 数据来源

    返回: 保存后的完整数据
    """
    fpath = _match_file(match_name)
    now = _now_cst()
    phase = _detect_phase(kickoff)

    # 加载已有数据
    if fpath.exists():
        with open(fpath, 'r', encoding='utf-8') as f:
            stored = json.load(f)
    else:
        stored = {
            'match_name': match_name,
            'kickoff': kickoff,
            'created': now,
            'snapshots': [],
        }
        # 更新 kickoff（如果之前没设置）
        if kickoff and not stored.get('kickoff'):
            stored['kickoff'] = kickoff

    # 构建新快照
    snapshot = {
        'timestamp': now,
        'phase': phase,
        'odds': odds,
        'betfair': betfair,
        'big_trades': big_trades or [],
        'notes': notes,
        'source': source,
        'index': len(stored['snapshots']) + 1,
    }

    # 追加
    stored['snapshots'].append(snapshot)
    stored['updated'] = now
    stored['snapshot_count'] = len(stored['snapshots'])

    # 写入
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(stored, f, ensure_ascii=False, indent=2)

    # 简短确认
    prev_count = len(stored['snapshots']) - 1
    if prev_count > 0:
        print(f"💾 必发数据已保存: {match_name} [{phase}] → 共 {len(stored['snapshots'])} 个快照 (+1)")
    else:
        print(f"💾 必发数据已保存: {match_name} [{phase}] → 首次录入")

    return stored


def load_betfair(match_name: str) -> Optional[Dict[str, Any]]:
    """加载一场比赛的全部必发快照"""
    fpath = _match_file(match_name)
    if not fpath.exists():
        return None
    with open(fpath, 'r', encoding='utf-8') as f:
        return json.load(f)


def latest_snapshot(match_name: str) -> Optional[Dict[str, Any]]:
    """获取最新的必发快照"""
    data = load_betfair(match_name)
    if not data or not data.get('snapshots'):
        return None
    return data['snapshots'][-1]


def compare_snapshots(match_name: str) -> str:
    """
    对比同一场比赛的所有必发快照，输出趋势报告。

    类似赔率变化.py 的输出格式。
    """
    data = load_betfair(match_name)
    if not data or len(data.get('snapshots', [])) < 1:
        return f"⚠️ {match_name}: 无必发数据"

    snaps = data['snapshots']
    lines = []
    lines.append(f"📊 {match_name} 必发趋势 ({len(snaps)}个快照)")
    lines.append(f"   开球: {data.get('kickoff', '未知')}")
    lines.append(f"   {'─' * 50}")

    if len(snaps) == 1:
        s = snaps[0]
        bf = s['betfair']
        lines.append(f"   [{s['phase']}] {s['timestamp']}")
        lines.append(f"   成交价: 主{bf['home_price']}/平{bf['draw_price']}/客{bf['away_price']}")
        lines.append(f"   成交量: 主{bf['home_volume']:,}/平{bf['draw_volume']:,}/客{bf['away_volume']:,}")
        lines.append(f"   庄家盈亏: 主{bf['home_pnl']:+.2f}M/平{bf['draw_pnl']:+.2f}M/客{bf['away_pnl']:+.2f}M")
        lines.append(f"   冷热指数: 主{bf['home_heat']:+d}/平{bf['draw_heat']:+d}/客{bf['away_heat']:+d}")
        return '\n'.join(lines)

    # 多快照对比
    first = snaps[0]
    last = snaps[-1]
    bf_first = first['betfair']
    bf_last = last['betfair']

    lines.append(f"   时间跨度: {first['timestamp']} → {last['timestamp']}")
    lines.append(f"   阶段: {first['phase']} → {last['phase']}")
    lines.append(f"")

    # 成交价变动
    lines.append(f"   【成交价变动】")
    for side, label in [('home_price', '主胜'), ('draw_price', '平局'), ('away_price', '客胜')]:
        f_val = bf_first[side]
        l_val = bf_last[side]
        change = l_val - f_val
        pct = (change / f_val * 100) if f_val else 0
        arrow = '⬆️' if change > 0.02 else ('⬇️' if change < -0.02 else '➡️')
        lines.append(f"   {label}: {f_val:.2f} → {l_val:.2f} ({change:+.2f} / {pct:+.1f}%) {arrow}")

    # 成交量变动
    lines.append(f"   【成交量变动】")
    for side, label in [('home_volume', '主胜'), ('draw_volume', '平局'), ('away_volume', '客胜')]:
        f_val = bf_first[side]
        l_val = bf_last[side]
        change = l_val - f_val
        pct = (change / f_val * 100) if f_val else 0
        lines.append(f"   {label}: {f_val:,.0f} → {l_val:,.0f} ({change:+,.0f} / {pct:+.1f}%)")

    # 庄家盈亏变动
    lines.append(f"   【庄家盈亏变动】")
    for side, label in [('home_pnl', '主胜'), ('draw_pnl', '平局'), ('away_pnl', '客胜')]:
        f_val = bf_first[side]
        l_val = bf_last[side]
        change = l_val - f_val
        direction = '🟢恶化' if change < -1 else ('🔴改善' if change > 1 else '➡️')
        lines.append(f"   {label}: {f_val:+.2f}M → {l_val:+.2f}M ({change:+.2f}M) {direction}")

    # 冷热指数变动
    lines.append(f"   【冷热指数变动】")
    for side, label in [('home_heat', '主胜'), ('draw_heat', '平局'), ('away_heat', '客胜')]:
        f_val = bf_first[side]
        l_val = bf_last[side]
        change = l_val - f_val
        direction = '升温' if change > 5 else ('降温' if change < -5 else '稳定')
        lines.append(f"   {label}: {f_val:+d} → {l_val:+d} ({change:+d}) {direction}")

    # 关键变化总结
    lines.append(f"")
    lines.append(f"   【关键变化】")

    # 检测庄家盈亏方向翻转
    for side, label in [('home_pnl', '主胜'), ('draw_pnl', '平局'), ('away_pnl', '客胜')]:
        if bf_first[side] * bf_last[side] < 0:
            flip = '盈→亏' if bf_first[side] > 0 else '亏→盈'
            lines.append(f"   🚩 {label}庄家盈亏翻转: {flip}!")

    # 检测冷热方向翻转
    for side, label in [('home_heat', '主胜'), ('draw_heat', '平局'), ('away_heat', '客胜')]:
        if bf_first[side] * bf_last[side] < 0:
            flip = '热→冷' if bf_first[side] > 0 else '冷→热'
            lines.append(f"   🔥 {label}冷热翻转: {flip}!")

    # 各阶段快照一览
    lines.append(f"")
    lines.append(f"   【各阶段快照】")
    for s in snaps:
        bf = s['betfair']
        # 计算成交占比
        total_vol = bf['home_volume'] + bf['draw_volume'] + bf['away_volume']
        home_pct = bf['home_volume'] / total_vol * 100 if total_vol > 0 else 0
        lines.append(
            f"   [{s['phase']}] {s['timestamp'][:16]} | "
            f"成交价{bf['home_price']}/{bf['draw_price']}/{bf['away_price']} | "
            f"主成交{home_pct:.1f}% | "
            f"盈亏{bf['home_pnl']:+.1f}/{bf['draw_pnl']:+.1f}/{bf['away_pnl']:+.1f}M"
        )

    return '\n'.join(lines)


def list_all_matches() -> List[str]:
    """列出所有已保存的比赛"""
    matches = []
    for fpath in DATA_DIR.glob('*.json'):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            name = data.get('match_name', fpath.stem)
            count = data.get('snapshot_count', len(data.get('snapshots', [])))
            matches.append(f"{name} ({count}个快照)")
        except:
            matches.append(fpath.stem)
    return sorted(matches)


# ── 测试 ──
if __name__ == "__main__":
    # 测试保存
    print("=" * 60)
    print("必发存储模块 测试")
    print("=" * 60)

    # 模拟用户输入的荷兰vs日本数据
    test_data = {
        'odds': {'home': 2.04, 'draw': 3.43, 'away': 3.63},
        'betfair': {
            'home_price': 2.14, 'draw_price': 3.60, 'away_price': 3.95,
            'home_volume': 4179426, 'draw_volume': 989767, 'away_volume': 1223025,
            'home_pnl': -2.55, 'draw_pnl': 2.83, 'away_pnl': 1.56,
            'home_heat': 40, 'draw_heat': -44, 'away_heat': -27,
        },
        'big_trades': [
            {'side': '客', 'direction': '卖', 'volume': 2789, 'time': '23:09'},
            {'side': '主', 'direction': '买', 'volume': 6869, 'time': '23:09'},
            {'side': '平', 'direction': '卖', 'volume': 3252, 'time': '23:09'},
            {'side': '主', 'direction': '买', 'volume': 13511, 'time': '23:06'},
            {'side': '主', 'direction': '卖', 'volume': 15248, 'time': '23:03'},
        ],
        'notes': '本场比赛必发成交量倾向于主胜,与百家欧赔概率相差较大，谨防主胜过热',
    }

    # 保存 P1 快照
    save_betfair('荷兰VS日本', **test_data, kickoff='2026-06-15T04:00', source='用户手动输入')
    print()

    # 对比（当前只有1个快照）
    print(compare_snapshots('荷兰VS日本'))
    print()

    # 模拟 P2 快照（数据略有变化）
    test_data_p2 = {
        'odds': {'home': 2.06, 'draw': 3.40, 'away': 3.58},
        'betfair': {
            'home_price': 2.18, 'draw_price': 3.55, 'away_price': 3.90,
            'home_volume': 4580123, 'draw_volume': 1102567, 'away_volume': 1356789,
            'home_pnl': -3.10, 'draw_pnl': 3.20, 'away_pnl': 1.80,
            'home_heat': 45, 'draw_heat': -48, 'away_heat': -30,
        },
        'big_trades': [],
        'notes': '热度持续升温·荷兰成交占比进一步扩大',
    }
    save_betfair('荷兰VS日本', **test_data_p2, kickoff='2026-06-15T04:00', source='用户手动输入')
    print()

    # 对比（2个快照）
    print(compare_snapshots('荷兰VS日本'))
    print()

    # 列出所有比赛
    print("已保存的比赛:")
    for m in list_all_matches():
        print(f"  📁 {m}")

    print()
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

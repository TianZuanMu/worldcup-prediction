# -*- coding: utf-8 -*-
"""
V2.11 市场心理周期因子

逻辑:
  当近期连续出现冷门 → 公众心理转向搏冷 → 博彩公司bearish信号部分来自
  公众资金而非真实价值判断 → 需对当前bearish信号打折扣

触发条件: 近8场中冷门≥4场
折扣幅度: 冷门率越高折扣越大, 最高-10%
"""

import json
from pathlib import Path
from typing import Dict, Optional
from config import CONF

BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
MATCHES_FILE = BACKTEST_DIR / "matches.json"


def _is_upset(match: dict) -> bool:
    """
    判断一场已完赛的比赛是否是冷门(从公众/市场心理角度)。

    冷门定义: 被市场看好的热门方未能赢球(输或平)。
    热门方从模型预测方向反推(模型预测代表市场共识方向)。

    关键: 对于 'home_not_win' / 'away_not_win' 预测,
    模型已经在看衰热门, 但公众仍然认为该队是热门。
    如果该热门确实输了/平了 → 公众眼中就是冷门。

    排除: EXTREME强制回避场次(结果随机, 不作参考)。
    """
    actual = match.get('actual', {}).get('result', '')
    gap = match.get('features', {}).get('strength_gap', '')
    pred_dir = match.get('prediction', {}).get('direction', '')

    # 只统计有结果的比赛
    if actual == 'pending' or not actual:
        return False

    # EXTREME级别被强制回避, 不计入
    if gap == 'extreme':
        return False

    # ── 推断公众热门方 ──
    # 如果预测方向包含 'home_win' → 公众看好主队
    # 如果预测方向包含 'away_win' → 公众看好客队
    # 如果预测 'home_not_win' → 公众仍看好主队, 但模型看衰
    # 如果预测 'away_not_win' → 公众仍看好客队, 但模型看衰
    # 如果预测 'draw' → 双方接近, 不以热门论

    if 'home_win' in pred_dir:
        # 主队是公众热门
        return actual in ('draw', 'away')
    elif 'away_win' in pred_dir:
        # 客队是公众热门
        return actual in ('draw', 'home')
    elif pred_dir == 'home_not_win':
        # 公众认为主队是热门, 模型看衰
        # 主队输/平 → 公众冷门
        return actual in ('draw', 'away')
    elif pred_dir == 'away_not_win':
        # 公众认为客队是热门, 模型看衰
        # 客队输/平 → 公众冷门
        return actual in ('draw', 'home')
    elif pred_dir == 'draw':
        # 平局预测 → 双方实力接近, 任何结果都不算冷门
        return False

    return False


def get_cold_streak_factor(window: int = 8) -> Dict:
    """
    计算近期冷门频率及市场心理修正因子。

    Args:
        window: 回溯窗口(场次数)

    Returns:
        {
            'recent_matches': int,        # 窗口内有效比赛数
            'upsets': int,                # 冷门数
            'upset_rate': float,          # 冷门率 0-1
            'cold_chasing': bool,         # 是否处于搏冷模式
            'confidence_adj': int,        # 置信度调整值(-10 ~ 0)
            'discount_note': str,         # 说明文字
        }
    """
    if not MATCHES_FILE.exists():
        return {
            'recent_matches': 0, 'upsets': 0, 'upset_rate': 0,
            'cold_chasing': False, 'confidence_adj': 0,
            'discount_note': '无回测数据·跳过市场心理分析',
        }

    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        matches = json.load(f)

    # 只取已完赛的(排除pending)
    completed = [m for m in matches if m.get('actual', {}).get('result', 'pending') != 'pending']

    # 取最近window场
    recent = completed[-window:] if len(completed) >= window else completed

    if len(recent) < 3:
        return {
            'recent_matches': len(recent), 'upsets': 0, 'upset_rate': 0,
            'cold_chasing': False, 'confidence_adj': 0,
            'discount_note': f'完赛数据不足(仅{len(recent)}场)·跳过',
        }

    upsets = sum(1 for m in recent if _is_upset(m))
    upset_rate = upsets / len(recent)

    # 冷门率 >= 阈值 → 市场进入搏冷模式
    cold_chasing = upset_rate >= CONF.cold_chasing_threshold

    if cold_chasing:
        # 冷门率越高, 折扣越大
        # 50%冷门率 → -5%, 100%冷门率 → -10%
        confidence_adj = -int(upset_rate * 10)
        confidence_adj = max(-10, min(0, confidence_adj))

        upset_names = []
        for m in recent:
            if _is_upset(m):
                upset_names.append(f"{m['match_name']}({m['actual']['score']})")

        discount_note = (
            f'📉 市场搏冷心理: 近{len(recent)}场{upsets}冷({upset_rate:.0%})'
            f'→ bearish信号可靠性打折·置信度{confidence_adj}%'
        )
    else:
        confidence_adj = 0
        discount_note = f'近{len(recent)}场仅{upsets}冷({upset_rate:.0%})·市场心理正常'

    return {
        'recent_matches': len(recent),
        'upsets': upsets,
        'upset_rate': round(upset_rate, 2),
        'cold_chasing': cold_chasing,
        'confidence_adj': confidence_adj,
        'discount_note': discount_note,
    }


def get_market_adjustment() -> int:
    """快捷接口: 直接返回置信度调整值"""
    return get_cold_streak_factor()['confidence_adj']


def get_market_note() -> str:
    """快捷接口: 返回说明文字"""
    return get_cold_streak_factor()['discount_note']


# ── 独立测试 ──
if __name__ == '__main__':
    result = get_cold_streak_factor()
    print(f"近{result['recent_matches']}场 | 冷门: {result['upsets']} | 冷门率: {result['upset_rate']:.0%}")
    print(f"搏冷模式: {'🔴 是' if result['cold_chasing'] else '✅ 否'}")
    print(f"置信度调整: {result['confidence_adj']:+.0f}%")
    print(f"说明: {result['discount_note']}")

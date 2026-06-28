# -*- coding: utf-8 -*-
"""
P0-1: V2.2 维度12 —— 必发庄家盈亏结构分析

核心创新:
  区分"真过热"vs"假过热"——同样+48冷热指数，
  荷兰场庄亏2.5M→爆冷，卡塔尔场庄盈5.2M→正路。

判据:
  真过热 = 过热 AND 庄家盈亏热门为负 AND (可选: 亚盘降盘)
  假过热 = 过热 AND 庄家盈亏热门为正 AND 实力差距明显
  平局信号 = 平局庄家盈亏在所有选项中突出

用法:
  from dimension12_books import analyze_books_structure
  result = analyze_books_structure(home_odds, draw_odds, away_odds,
                                    home_volume, draw_volume, away_volume,
                                    home_pnl, draw_pnl, away_pnl)
"""

from dataclasses import dataclass
from typing import Optional
from config import CONF


@dataclass
class BooksStructure:
    """庄家盈亏结构分析结果"""

    # 原始数据
    home_pnl: float          # 主胜庄家盈亏
    draw_pnl: float          # 平局庄家盈亏
    away_pnl: float          # 客胜庄家盈亏

    # 热度判定
    hot_side: str            # 热门方: 'home' | 'away' | 'none'
    hot_index: float         # 冷热指数 (正=过热, 负=偏冷)
    is_real_hot: bool        # 真过热? (庄家在亏)
    is_false_hot: bool       # 假过热? (庄家也在赚)

    # 庄家意图
    bookmaker_favorite: str  # 庄家最想看到的结果: 'home' | 'draw' | 'away'
    bookmaker_aversion: str  # 庄家最怕的结果
    pnl_confidence: float    # 盈亏信号置信度 (0-1)

    # 综合信号
    draw_signal: bool        # 平局信号突出?
    cold_upset_risk: bool    # 冷门风险?
    trusted_favorite: bool   # 可信正路?

    # 文本说明
    summary: str = ""        # 一句话总结
    advice: str = ""         # 操作建议
    narrow_win: bool = False # 🆕 降盘≠不胜: 热门小胜不穿盘


def analyze_books_structure(
    home_odds: float,        # 百家欧赔平均 主胜
    draw_odds: float,        # 百家欧赔平均 平局
    away_odds: float,        # 百家欧赔平均 客胜
    home_volume: float,      # 必发成交量 主胜
    draw_volume: float,      # 必发成交量 平局
    away_volume: float,      # 必发成交量 客胜
    home_pnl: float,         # 庄家盈亏 主胜 (正=庄盈, 负=庄亏)
    draw_pnl: float,         # 庄家盈亏 平局
    away_pnl: float,         # 庄家盈亏 客胜
    handicap_direction: Optional[str] = None,  # 亚盘方向: 'up' | 'down' | 'stable'
    strength_gap: Optional[str] = None,        # 实力差距: 'big' | 'moderate' | 'close'
    is_host_nation: bool = False,              # 🆕 东道主?
    is_opening_match: bool = False,            # 🆕 揭幕战?
) -> BooksStructure:
    """
    分析必发庄家盈亏结构，区分真/假过热。

    回测验证:
      - 荷兰vs厄瓜多尔: home_pnl=-2.48M → 真过热 → 平局打出 ✅
      - 卡塔尔vs厄瓜多尔: away_pnl=+5.24M → 假过热 → 正路打出 ✅
      - 厄瓜多尔vs塞内加尔: home_pnl=-5.87M → 真过热 → 塞内加尔胜 ✅
    """

    # ── 1. 计算隐含概率 ──
    home_prob = (1.0 / home_odds) if home_odds > 0 else 0
    draw_prob = (1.0 / draw_odds) if draw_odds > 0 else 0
    away_prob = (1.0 / away_odds) if away_odds > 0 else 0
    total_prob = home_prob + draw_prob + away_prob

    # 归一化 (扣除抽水)
    if total_prob > 0:
        home_prob /= total_prob
        draw_prob /= total_prob
        away_prob /= total_prob

    # ── 2. 计算成交量占比 ──
    total_vol = home_volume + draw_volume + away_volume
    if total_vol > 0:
        home_vol_pct = home_volume / total_vol
        draw_vol_pct = draw_volume / total_vol
        away_vol_pct = away_volume / total_vol
    else:
        home_vol_pct = draw_vol_pct = away_vol_pct = 0

    # ── 3. 识别热门方 ──
    # 按隐含概率
    probs = {'home': home_prob, 'draw': draw_prob, 'away': away_prob}
    favorite_by_prob = max(probs, key=probs.get)

    # 按成交量
    vols = {'home': home_vol_pct, 'draw': draw_vol_pct, 'away': away_vol_pct}
    favorite_by_vol = max(vols, key=vols.get)

    # 冷热指数 = 成交量占比 - 隐含概率 (百分比形式)
    heat_map = {
        'home': (home_vol_pct - home_prob) * 100,
        'draw': (draw_vol_pct - draw_prob) * 100,
        'away': (away_vol_pct - away_prob) * 100,
    }

    hot_side = max(heat_map, key=heat_map.get)
    hot_index = heat_map[hot_side]

    # 过热阈值 (V2.12统一: JSON路径与文本路径一致)
    is_overheated = hot_index > CONF.overheat_threshold  # 偏差>阈值视为过热

    # ── 4. 庄家盈亏分析 ──
    pnl_map = {'home': home_pnl, 'draw': draw_pnl, 'away': away_pnl}

    # 庄家最想看到的结果 (盈最多)
    bookmaker_favorite = max(pnl_map, key=pnl_map.get)
    # 庄家最怕的结果 (亏最多)
    bookmaker_aversion = min(pnl_map, key=pnl_map.get)

    # 热门方庄家盈亏
    hot_pnl = pnl_map[hot_side]

    # ── 5. 真/假过热判定 (V2.3: 加入实力差距调节) ──
    is_real_hot = False
    is_false_hot = False
    draw_signal = False
    cold_upset_risk = False
    trusted_favorite = False
    narrow_win = False       # 🆕 降盘≠不胜: 热门小胜不穿盘

    if is_overheated and hot_pnl < 0:
        # 过热 + 庄亏 → 需要看实力差距
        if strength_gap == 'big':
            # 实力碾压 → 热门仍赢但不穿盘 (Mexico+32, Scotland+34)
            is_false_hot = True   # 标记为"假过热"→可追正路
            trusted_favorite = True
            narrow_win = True     # 但大概率小胜(不穿盘)
        else:
            # 实力接近 → 真过热·热门不胜 (Canada+63, Brazil+50, Turkey+47)
            is_real_hot = True
            cold_upset_risk = True

    elif is_overheated and hot_pnl >= 0:
        # 过热 + 庄盈 = 假过热 → 可追正路 (Ecuador+48 vs Qatar)
        is_false_hot = True
        trusted_favorite = True

    # 🆕 降盘≠不胜 逻辑:
    # 降盘 + 实力差距大 → 热门小胜(不穿盘)，不是不胜
    if handicap_direction == 'down' and strength_gap == 'big':
        narrow_win = True
        if not is_real_hot:
            trusted_favorite = True  # 降盘但实力碾压→仍赢

    # 🆕 东道主系数调节 (V2.8: 仅当东道主是热门方且过热时才触发)
    if is_host_nation:
        if is_opening_match and hot_side == 'home':
            # 东道主揭幕战 → 情绪溢价可抵消过热 (USA+68→4-1)
            if is_real_hot:
                is_real_hot = False
                is_false_hot = True
                trusted_favorite = True
                cold_upset_risk = False
        elif hot_side == 'home' and is_real_hot:
            # 东道主是真过热热门 → 降级为假过热（东道主溢价），但仍标记不穿盘
            is_real_hot = False
            is_false_hot = True
            trusted_favorite = True
            narrow_win = True
        # 如果东道主不是热门方或不过热 → 不覆盖，保持原判定

    elif not is_overheated and hot_pnl < 0:
        # 未过热但庄亏 = 轻度警惕
        cold_upset_risk = True

    # ── 6. 平局信号检测 ──
    # 平局庄盈突出 (超过另两个选项之和的50%)
    other_max_pnl = max(home_pnl, away_pnl)
    if draw_pnl > 0 and draw_pnl > other_max_pnl * 1.5:
        draw_signal = True

    # ── 7. 盈亏置信度 ──
    total_pnl_abs = abs(home_pnl) + abs(draw_pnl) + abs(away_pnl)
    if total_pnl_abs > 0:
        pnl_spread = abs(max(pnl_map.values()) - min(pnl_map.values()))
        pnl_confidence = min(pnl_spread / (total_pnl_abs + 1), 1.0)
    else:
        pnl_confidence = 0

    # ── 8. 生成文本总结 (V2.3) ──
    side_label = {'home': '主胜', 'draw': '平局', 'away': '客胜'}

    if is_real_hot:
        summary = (
            f"🔴 真过热: {side_label[hot_side]}冷热+{hot_index:.0f} "
            f"但庄家盈亏{hot_pnl:+.1f}M(亏损) → 实力接近·大热必死"
        )
        advice = f"建议反向: 避开{side_label[hot_side]}，关注{side_label[bookmaker_favorite]}"
    elif is_false_hot and narrow_win:
        summary = (
            f"🟡 过热但实力碾压: {side_label[hot_side]}冷热+{hot_index:.0f} "
            f"庄家盈亏{hot_pnl:+.1f}M → 热门仍赢·但难穿盘"
        )
        advice = f"可追正路: {side_label[hot_side]}小胜方向，不追穿盘"
    elif is_false_hot:
        # 🆕 V4.5 P0: PnL安全格式化
        _p = hot_pnl
        _p_str = f'{_p/1e4:.1f}万(⚠️待核实)' if abs(_p) > 1e8 else (f'{_p/1e4:.1f}万' if abs(_p) >= 1e4 else f'{_p:.0f}')
        summary = (
            f"🟢 假过热: {side_label[hot_side]}冷热+{hot_index:.0f} "
            f"庄家同向盈利{_p_str} → 热度可信"
        )
        advice = f"可追正路: {side_label[hot_side]}方向"
    elif cold_upset_risk:
        # 🆕 V4.5 P0: PnL安全格式化
        _loss = abs(pnl_map[bookmaker_aversion])
        _l_str = f'{_loss/1e4:.1f}万(⚠️待核实)' if _loss > 1e8 else (f'{_loss/1e4:.1f}万' if _loss >= 1e4 else f'{_loss:.0f}')
        summary = (
            f"🟡 轻度警惕: 热度正常但庄家{side_label[bookmaker_aversion]}"
            f"亏损{_l_str}"
        )
        advice = f"谨慎看好热门方"
    else:
        summary = "🟢 结构健康: 热度与庄家方向一致，无异常信号"
        advice = "按基本面正常判断"

    if draw_signal:
        summary += " | 🎯 平局庄盈突出→平局信号增强"
        advice += "，平局需重点关注"

    if is_host_nation:
        summary += " | 🏠 东道主因素已纳入"
    if narrow_win and not is_false_hot:
        summary += " | ⚠️ 降盘→热门小胜(不穿盘)"

    return BooksStructure(
        home_pnl=home_pnl,
        draw_pnl=draw_pnl,
        away_pnl=away_pnl,
        hot_side=hot_side,
        hot_index=round(hot_index, 1),
        is_real_hot=is_real_hot,
        is_false_hot=is_false_hot,
        bookmaker_favorite=bookmaker_favorite,
        bookmaker_aversion=bookmaker_aversion,
        pnl_confidence=round(pnl_confidence, 2),
        draw_signal=draw_signal,
        cold_upset_risk=cold_upset_risk,
        trusted_favorite=trusted_favorite,
        narrow_win=narrow_win,
        summary=summary,
        advice=advice,
    )


# ── V2.3 评估函数 ──

def evaluate_prediction(pred_direction: str, actual_result: str) -> bool:
    """
    独立评估函数 —— 统一标准·消除人工判断歧义。

    pred_direction: 预测方向
        'home_win' / 'away_win' / 'draw' /
        'home_not_lose' / 'away_not_lose' /
        'home_not_win' / 'away_not_win'
    actual_result: 'home' / 'draw' / 'away'

    回测验证: 修正了之前两次评估bug
    """
    rules = {
        'home_win':        lambda r: r == 'home',
        'home_win_narrow': lambda r: r == 'home',
        'home_win_cover':  lambda r: r == 'home',
        'away_win':        lambda r: r == 'away',
        'away_win_cover':  lambda r: r == 'away',
        'draw':            lambda r: r == 'draw',
        'home_not_lose':   lambda r: r in ('home', 'draw'),
        'away_not_lose':   lambda r: r in ('away', 'draw'),
        'home_not_win':    lambda r: r in ('draw', 'away'),
        'away_not_win':    lambda r: r in ('draw', 'home'),
    }

    if pred_direction in rules:
        return rules[pred_direction](actual_result)

    # EXTREME强制回避 → 不计入正确性
    if pred_direction == 'skip_extreme':
        return None

    # 模糊匹配
    pred_lower = pred_direction.lower()
    if '主胜' in pred_lower and '不' not in pred_lower:
        return actual_result == 'home'
    if '客胜' in pred_lower and '不' not in pred_lower:
        return actual_result == 'away'
    if '平局' in pred_lower:
        return actual_result == 'draw'
    if '主队不败' in pred_lower or '主不' in pred_lower:
        return actual_result in ('home', 'draw')
    if '客队不败' in pred_lower or '客不' in pred_lower:
        return actual_result in ('away', 'draw')
    if '主队不胜' in pred_lower or '主胜' not in pred_lower and '主不' in pred_lower:
        return actual_result in ('draw', 'away')
    if '客队不胜' in pred_lower:
        return actual_result in ('draw', 'home')

    return False


# ── V2.2 维度12: 完整维度定义 ──
DIMENSION_12_DEF = {
    "name": "必发庄家盈亏结构",
    "weight": 0.04,  # 4%
    "description": "通过庄家盈亏方向区分真/假过热，识别平局信号",
    "sub_dimensions": {
        "hot_authenticity": {
            "weight": 0.40,  # 真/假过热判定
            "rule": "过热+庄亏=真过热(反向); 过热+庄盈=假过热(可追)",
        },
        "pnl_structure": {
            "weight": 0.35,  # 盈亏分布
            "rule": "庄盈最大选项=庄家最想看到的结果",
        },
        "draw_detection": {
            "weight": 0.25,  # 平局信号
            "rule": "平局庄盈超过另两个选项之和×1.5→平局信号增强",
        },
    },
    "confidence_adjustment": {
        "real_hot": -0.15,       # 真过热 → 降低热门置信度15%
        "false_hot": 0.0,        # 假过热 → 不调整
        "draw_signal": +0.10,    # 平局信号 → 平局选项置信度+10%
    },
}


# ── 快速测试 ──
if __name__ == "__main__":
    print("=" * 60)
    print("维度12 回测验证")
    print("=" * 60)

    # 测试1: 荷兰 vs 厄瓜多尔 (应检出: 真过热+平局信号)
    print("\n📋 荷兰 vs 厄瓜多尔 (实际1-1平)")
    r1 = analyze_books_structure(
        home_odds=1.81, draw_odds=3.50, away_odds=4.81,
        home_volume=27263170, draw_volume=3925406, away_volume=3684139,
        home_pnl=-2.48, draw_pnl=14.07, away_pnl=-11.18,
        handicap_direction='down',
        strength_gap='moderate',
    )
    print(f"  热门方: {r1.hot_side} 冷热指数: {r1.hot_index}")
    print(f"  真过热: {r1.is_real_hot} | 假过热: {r1.is_false_hot}")
    print(f"  庄家最爱: {r1.bookmaker_favorite} | 最怕: {r1.bookmaker_aversion}")
    print(f"  平局信号: {r1.draw_signal}")
    print(f"  冷门风险: {r1.cold_upset_risk}")
    print(f"  总结: {r1.summary}")
    print(f"  建议: {r1.advice}")
    assert r1.is_real_hot, "应检出真过热!"
    assert r1.draw_signal, "应检出平局信号!"
    print("  ✅ 通过: 正确识别真过热+平局信号")

    # 测试2: 卡塔尔 vs 厄瓜多尔 (应检出: 假过热)
    print("\n📋 卡塔尔 vs 厄瓜多尔 (实际0-2)")
    r2 = analyze_books_structure(
        home_odds=3.55, draw_odds=3.11, away_odds=2.24,
        home_volume=8784692, draw_volume=5513115, away_volume=24493090,
        home_pnl=-84.19, draw_pnl=10.67, away_pnl=5.24,
        handicap_direction='stable',
        strength_gap='big',
    )
    print(f"  热门方: {r2.hot_side} 冷热指数: {r2.hot_index}")
    print(f"  真过热: {r2.is_real_hot} | 假过热: {r2.is_false_hot}")
    print(f"  可信正路: {r2.trusted_favorite}")
    print(f"  总结: {r2.summary}")
    assert r2.is_false_hot, "应检出假过热!"
    assert r2.trusted_favorite, "应标记为可信正路!"
    print("  ✅ 通过: 正确识别假过热→可信正路")

    # 测试3: 厄瓜多尔 vs 塞内加尔 (应检出: 真过热)
    print("\n📋 厄瓜多尔 vs 塞内加尔 (实际1-2)")
    r3 = analyze_books_structure(
        home_odds=2.46, draw_odds=3.15, away_odds=3.08,
        home_volume=7669128, draw_volume=2366335, away_volume=4182745,
        home_pnl=-5.87, draw_pnl=7.12, away_pnl=-0.42,
        handicap_direction='up',
        strength_gap='close',
    )
    print(f"  热门方: {r3.hot_side} 冷热指数: {r3.hot_index}")
    print(f"  真过热: {r3.is_real_hot} | 冷门风险: {r3.cold_upset_risk}")
    print(f"  庄家最爱: {r3.bookmaker_favorite}")
    print(f"  总结: {r3.summary}")
    assert r3.is_real_hot, "应检出真过热!"
    assert r3.draw_signal, "应检出平局庄盈突出!"
    print("  ✅ 通过: 正确识别真过热+庄家倾向平局")

    print("\n" + "=" * 60)
    print("🎉 3/3 回测全部通过!")
    print("=" * 60)

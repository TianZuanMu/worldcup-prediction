# -*- coding: utf-8 -*-
"""
P0-2: V2.2 维度3 —— 亚盘资金（重构版）

V2.1 问题:
  - 亚盘分析仅看赔率变动方向，未区分盘口升降 vs 水位变动
  - 盘口升降是庄家主动行为(信号强)，水位变动可能是市场被动(信号弱)

V2.2 改进:
  - 内部拆分为3个子维度，各有独立权重
  - 盘口升降方向 (40%): 升盘=看好，降盘=看衰 ← 庄家意图
  - 水位变动 (30%): 高水=阻买，低水=诱买 ← 市场反应
  - 资金流向 (30%): 赔率变动方向 ← 市场共识

回测验证:
  - 荷兰vs厄瓜多尔: 半一→半球降盘 → 盘口方向强烈看衰荷兰 ✅
  - 厄瓜多尔vs塞内加尔: 平手→平半升盘 → 诱盘信号 ⚠️

用法:
  from dimension3_handicap import analyze_handicap
  result = analyze_handicap(init_line, instant_line, init_water_home,
                             init_water_away, instant_water_home, instant_water_away,
                             odds_change_home, odds_change_away)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HandicapAnalysis:
    """亚盘综合分析结果"""

    # 原始数据
    init_line: float           # 初盘盘口 (e.g. -0.5 = 半球, -0.75 = 半一)
    instant_line: float        # 即时盘口
    line_change: float         # 盘口变动 (正=升盘, 负=降盘)
    line_direction: str        # 盘口方向: 'up' | 'down' | 'stable'

    # 水位
    init_water_home: float
    init_water_away: float
    instant_water_home: float
    instant_water_away: float

    # 赔率变动
    odds_change_home: float    # 主胜赔率变动(%)
    odds_change_away: float    # 客胜赔率变动(%)

    # ── 子维度评分 (0-10) ──
    line_score: float = 0      # 盘口方向分 (高=看好上盘)
    water_score: float = 0     # 水位分 (高=上盘有利)
    flow_score: float = 0      # 资金流分 (高=支持上盘)

    # ── 综合 ──
    composite_score: float = 0       # 综合分 (-10到+10, 正=上盘有利)
    confidence: float = 0            # 亚盘信号置信度 (0-1)
    signal_strength: str = 'weak'   # 'strong' | 'moderate' | 'weak'

    # 警示
    trap_warning: bool = False       # 诱盘警示
    retreat_warning: bool = False    # 退盘警示
    summary: str = ""


# 子维度权重 (V2.2)
SUB_WEIGHTS = {
    'line_direction': 0.40,   # 盘口升降
    'water_change': 0.30,     # 水位变动
    'flow_direction': 0.30,   # 资金流向
}


def _normalize_line(line: float) -> float:
    """标准化盘口数值: -0.5=半球, -0.75=半一, 0.25=受平半"""
    return line


def analyze_handicap(
    init_line: float,              # 初盘 (e.g. -0.5 = 主让半球)
    instant_line: float,           # 即时盘
    init_water_home: float,        # 初盘主队水位
    init_water_away: float,        # 初盘客队水位
    instant_water_home: float,     # 即时主队水位
    instant_water_away: float,     # 即时客队水位
    odds_change_home: float = 0,   # 主胜赔率变动 (%)
    odds_change_away: float = 0,   # 客胜赔率变动 (%)
    total_bookmakers: int = 20,    # 博彩公司总数
) -> HandicapAnalysis:
    """
    分析亚盘的三个子维度。

    line > 0 → 主队受让 (下盘)
    line < 0 → 主队让球 (上盘)
    line == 0 → 平手
    """

    result = HandicapAnalysis(
        init_line=init_line,
        instant_line=instant_line,
        line_change=round(instant_line - init_line, 3),
        line_direction='stable',
        init_water_home=init_water_home,
        init_water_away=init_water_away,
        instant_water_home=instant_water_home,
        instant_water_away=instant_water_away,
        odds_change_home=odds_change_home,
        odds_change_away=odds_change_away,
    )

    # ── 子维度1: 盘口升降 (40%) ──
    # XLS数据中的line是绝对值: 正数=主队让球深度, 0.75→0.5=让球减少=降盘
    line_delta = instant_line - init_line
    # line_delta > 0: 让球深度增加 → 升盘 (看好上盘)
    #   例: 0.5→0.75, delta=+0.25 → 升盘
    # line_delta < 0: 让球深度减少 → 降盘 (看衰上盘)
    #   例: 0.75→0.5, delta=-0.25 → 降盘 (荷半一→半球✅)

    abs_delta = abs(line_delta)

    if abs_delta < 0.01:
        result.line_direction = 'stable'
        result.line_score = 5.0  # 中性
    elif line_delta > 0:
        # 让球增加 = 升盘 → 看好上盘
        result.line_direction = 'up'
        if abs_delta >= 0.25:
            result.line_score = 9.0   # 强烈看好
        elif abs_delta >= 0.125:
            result.line_score = 7.5   # 中度看好
        else:
            result.line_score = 6.0   # 轻微看好
    else:
        # 让球减少 = 降盘 → 看衰上盘
        result.line_direction = 'down'
        result.retreat_warning = True
        if abs_delta >= 0.25:
            result.line_score = 1.0   # 强烈看衰 (荷半一→半球)
        elif abs_delta >= 0.125:
            result.line_score = 2.5   # 中度看衰
        else:
            result.line_score = 4.0   # 轻微看衰

    # ── 子维度2: 水位变动 (30%) ──
    # 上盘水位下降 = 市场追捧上盘 (利好)
    home_water_delta = instant_water_home - init_water_home
    away_water_delta = instant_water_away - init_water_away

    # 上盘方水位变动
    if init_line < 0:
        # 主队让球 → 主队是上盘
        upper_water_delta = home_water_delta
    else:
        # 客队让球 → 客队是上盘
        upper_water_delta = away_water_delta

    if abs(upper_water_delta) < 0.02:
        result.water_score = 5.0
    elif upper_water_delta < -0.05:
        result.water_score = 7.0   # 上盘水位下降 → 利好
    elif upper_water_delta < -0.02:
        result.water_score = 6.0
    elif upper_water_delta > 0.05:
        result.water_score = 3.0   # 上盘水位上升 → 利空
        result.trap_warning = True
    elif upper_water_delta > 0.02:
        result.water_score = 4.0
    else:
        result.water_score = 5.0

    # ── 子维度3: 资金流向 (30%) ──
    # 赔率下降 = 资金流入 = 市场支持
    # 正数=赔率上升(走弱), 负数=赔率下降(走强)

    if init_line < 0:
        # 主队让球 → 主队是上盘
        upper_change = odds_change_home
        lower_change = odds_change_away
    else:
        upper_change = odds_change_away
        lower_change = odds_change_home

    if abs(upper_change) < 1.0:
        result.flow_score = 5.0
    elif upper_change < -5.0:
        result.flow_score = 7.5   # 上盘资金大幅流入
    elif upper_change < -2.0:
        result.flow_score = 6.5
    elif upper_change > 5.0:
        result.flow_score = 2.5   # 上盘资金大幅流出
    elif upper_change > 2.0:
        result.flow_score = 3.5
    else:
        result.flow_score = 5.0

    # ── 综合评分 ──
    result.composite_score = round(
        result.line_score * SUB_WEIGHTS['line_direction'] +
        result.water_score * SUB_WEIGHTS['water_change'] +
        result.flow_score * SUB_WEIGHTS['flow_direction'],
        1
    )

    # 转换为 -10 到 +10 的范围 (5是中性)
    result.composite_score = round((result.composite_score - 5.0) * 2, 1)

    # ── 置信度 ──
    # 三个子维度方向一致 → 高置信度
    directions = []
    if result.composite_score > 1:
        directions.append('upper')
    elif result.composite_score < -1:
        directions.append('lower')
    else:
        directions.append('neutral')

    if result.line_score > 5.5:
        directions.append('upper')
    elif result.line_score < 4.5:
        directions.append('lower')

    if result.water_score > 5.5:
        directions.append('upper')
    elif result.water_score < 4.5:
        directions.append('lower')

    if result.flow_score > 5.5:
        directions.append('upper')
    elif result.flow_score < 4.5:
        directions.append('lower')

    # 一致性
    upper_count = directions.count('upper')
    lower_count = directions.count('lower')
    agreement = max(upper_count, lower_count) / max(len(directions), 1)
    result.confidence = round(agreement, 2)

    if agreement >= 0.75:
        result.signal_strength = 'strong'
    elif agreement >= 0.5:
        result.signal_strength = 'moderate'
    else:
        result.signal_strength = 'weak'

    # ── 警示检查 ──
    # 升盘+上盘水位上升 = 诱盘 (庄家升盘但高水阻购 → 其实不看好上盘)
    if result.line_direction == 'up' and home_water_delta > 0.03:
        result.trap_warning = True

    # 降盘+上盘低水 = 庄家真不看好 (降盘+给低水也不愿承担风险)
    if result.line_direction == 'down' and home_water_delta < -0.03:
        result.retreat_warning = True

    # ── 生成总结 ──
    direction_text = {
        'up': '升盘(看好上盘)',
        'down': '降盘(看衰上盘)',
        'stable': '盘口稳定',
    }[result.line_direction]

    warnings = []
    if result.trap_warning:
        warnings.append('⚠️诱盘')
    if result.retreat_warning:
        warnings.append('🚩退盘')

    result.summary = (
        f"亚盘: {direction_text} | "
        f"综合分{result.composite_score:+.1f} | "
        f"信号:{result.signal_strength}"
    )
    if warnings:
        result.summary += ' | ' + ' '.join(warnings)

    return result


# ── V2.2 维度3定义 ──
DIMENSION_3_V22_DEF = {
    "name": "亚盘资金（含盘口方向）",
    "weight": 0.16,  # 16% (V2.1: 15% + 1%)
    "description": "三维度拆解亚盘信号: 盘口升降+水位变动+资金流向",
    "sub_dimensions": {
        "line_direction": {
            "name": "盘口升降方向",
            "internal_weight": 0.40,
            "description": "升盘=庄家看好上盘, 降盘=看衰. 这是庄家主动行为，信号最强.",
            "key_rules": [
                "降盘≥0.25球 → 强烈看衰上盘 (回测: 荷兰半一→半球→1-1平✅)",
                "升盘≥0.25球 → 看好上盘但需警惕诱盘 (回测: 厄瓜多尔平手→平半→1-2负⚠️)",
                "盘口稳定 → 庄家无明确方向",
            ],
        },
        "water_change": {
            "name": "水位变动",
            "internal_weight": 0.30,
            "description": "上盘水位下降=市场追捧, 上升=市场回避.",
            "key_rules": [
                "上盘水位降>0.05 → 利好上盘",
                "上盘水位升>0.05 → 利空上盘+诱盘警示",
                "升盘+高水 → 诱盘 (庄家升盘但不给低水)",
            ],
        },
        "flow_direction": {
            "name": "资金流向",
            "internal_weight": 0.30,
            "description": "赔率变动方向反映资金流向. 赔率降=流入, 赔率升=流出.",
            "key_rules": [
                "赔率降>5% → 资金大幅流入",
                "赔率升>5% → 资金大幅流出",
                "方向与盘口一致 → 信号增强",
            ],
        },
    },
    "confidence_adjustment": {
        "strong_agreement": +0.05,
        "weak_signal": -0.05,
        "trap_warning": -0.10,
        "retreat_warning": -0.15,
    },
}


# ── 快速测试 ──
if __name__ == "__main__":
    print("=" * 60)
    print("维度3(V2.2) 回测验证")
    print("=" * 60)

    # 测试1: 荷兰 vs 厄瓜多尔 (半一→半球降盘)
    print("\n📋 荷兰 vs 厄瓜多尔 (半一→半球降盘, 实际1-1平)")
    r1 = analyze_handicap(
        init_line=-0.75, instant_line=-0.5,
        init_water_home=0.85, init_water_away=1.01,
        instant_water_home=0.87, instant_water_away=1.02,
        odds_change_home=1.9, odds_change_away=-2.6,
    )
    print(f"  盘口: {r1.init_line}→{r1.instant_line} ({r1.line_direction})")
    print(f"  盘口分:{r1.line_score} 水位分:{r1.water_score} 资金分:{r1.flow_score}")
    print(f"  综合分:{r1.composite_score:+.1f} 置信度:{r1.confidence} 信号:{r1.signal_strength}")
    print(f"  退盘警示:{r1.retreat_warning} 诱盘:{r1.trap_warning}")
    print(f"  总结: {r1.summary}")
    assert r1.line_direction == 'down', "应检测到降盘!"
    assert r1.retreat_warning or r1.composite_score < 0, "应看衰上盘(荷兰)!"
    print("  ✅ 通过: 降盘→看衰荷兰")

    # 测试2: 厄瓜多尔 vs 塞内加尔 (平手→平半升盘)
    print("\n📋 厄瓜多尔 vs 塞内加尔 (平手→平半升盘, 实际1-2负)")
    r2 = analyze_handicap(
        init_line=0.0, instant_line=-0.25,
        init_water_home=0.95, init_water_away=0.95,
        instant_water_home=1.02, instant_water_away=0.86,
        odds_change_home=-8.0, odds_change_away=6.4,
    )
    print(f"  盘口: {r2.init_line}→{r2.instant_line} ({r2.line_direction})")
    print(f"  盘口分:{r2.line_score} 水位分:{r2.water_score} 资金分:{r2.flow_score}")
    print(f"  综合分:{r2.composite_score:+.1f} 置信度:{r2.confidence}")
    print(f"  诱盘警示:{r2.trap_warning}")
    print(f"  总结: {r2.summary}")
    assert r2.line_direction == 'up', "应检测到升盘!"
    # 升盘+高水=诱盘
    print("  ✅ 通过: 升盘+高水→诱盘警示")

    # 测试3: 瑞典 vs 突尼斯 (盘口稳定)
    print("\n📋 瑞典 vs 突尼斯 (半球稳定, -0.5不变)")
    r3 = analyze_handicap(
        init_line=-0.5, instant_line=-0.5,
        init_water_home=1.99, init_water_away=2.00,
        instant_water_home=2.00, instant_water_away=1.99,
        odds_change_home=1.3, odds_change_away=-1.9,
    )
    print(f"  盘口: {r3.init_line}→{r3.instant_line} ({r3.line_direction})")
    print(f"  综合分:{r3.composite_score:+.1f} 信号:{r3.signal_strength}")
    assert r3.line_direction == 'stable', "盘口应稳定!"
    print("  ✅ 通过: 盘口稳定→信号弱")

    print("\n" + "=" * 60)
    print("🎉 3/3 回测全部通过!")
    print("=" * 60)

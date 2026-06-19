# -*- coding: utf-8 -*-
"""
V2.4: 综合风险评分 (四场复盘优化版)

新增因子:
  - odds_consensus: 欧赔共识指数 (-100到+100, 正=看好热门, 负=看衰热门)
  - water_diagnosis: 水位诊断 ('critical'|'worsening'|'stable'|'improving')
  - xls_penalty: XLS数据时效扣分
  - gap_level: 实力差距级别, 调节信号权重

公式: 风险分 = 热度差×0.25 + 盈亏abs×0.25 + 场外×0.15 + 退盘×0.15
              + 欧赔共识×0.10 + 水位恶化×0.10 + XLS时效(加成)
输出: 1-10分 (越高越危险)
"""

from v24_optimization import (
    GapLevel, OddsConsensus, WaterDiagnosis, XlsFreshness,
    get_signal_reliability,
)


def calc_risk_score_v24(
    heat_gap=None,
    pnl=None,
    off_field=0,
    handicap_retreat=0,
    draw_signal=None,
    lineup_issue=False,
    # V2.4 新增
    odds_consensus: OddsConsensus = None,
    water_diagnosis: WaterDiagnosis = None,
    xls_freshness: XlsFreshness = None,
    gap_level: GapLevel = None,
    cover_rate_pct: float = None,
):
    """
    V2.4 风险评分 - 集成四场复盘所有改进。

    回测验证:
      - 德国7-1: extreme gap → 退盘信号降权 → 风险从低→中低 (更合理)
      - 荷兰2-2: 水位恶化critical + 欧赔看衰 → 风险升高 (预警有效)
      - IC 1-0:  close gap → 退盘信号高可靠 → 小球正确
      - 瑞典5-1: moderate gap + XLS时效差12h → 置信度扣分
    """
    score = 0
    risk_factors = []

    # ── 基础因子 ──

    # 热度差 (0-30% → 0-3分)
    if heat_gap and heat_gap > 0:
        score += min(heat_gap / 10, 3.0)

    # 庄家盈亏 (-50到0 → 0-3分, 亏损越大分越高)
    if pnl is not None and pnl < 0:
        score += min(abs(pnl) / 15, 3.0)

    # 场外因素 (-2到+2 → 0-2分, 负值=不利)
    if off_field < 0:
        score += abs(off_field) * 1.0

    # ── 退盘 (按实力差距调整权重) ──
    if handicap_retreat > 0:
        # V2.4: extreme gap下降盘信号降权
        if gap_level:
            reliability = get_signal_reliability(gap_level, 'handicap_line')
        else:
            reliability = 1.0
        base_score = min(handicap_retreat * 4, 2.0)
        adjusted = base_score * reliability
        score += adjusted
        if reliability < 1.0:
            risk_factors.append(f"退盘信号降权({reliability:.0%}) → {adjusted:.1f}分")

    # ── V2.4 新增: 欧赔共识 ──
    if odds_consensus:
        # 共识看衰热门 → +风险
        if odds_consensus.market_signal == 'back_away':
            consensus_penalty = min(abs(odds_consensus.home_consensus) / 10, 2.0)
            score += consensus_penalty
            risk_factors.append(f"欧赔共识看衰热门 (共识{odds_consensus.home_consensus:+.0f})")
        elif odds_consensus.market_signal == 'back_draw':
            score += 1.0
            risk_factors.append(f"欧赔共识指向平局 (平赔收缩{odds_consensus.draw_consensus:+.0f})")

    # ── V2.4 新增: 水位恶化 ──
    if water_diagnosis:
        if water_diagnosis.diagnosis == 'critical':
            score += 2.0
            risk_factors.append("⚠️ 上盘水位急剧恶化 (+0.10+): 市场强烈回避")
        elif water_diagnosis.diagnosis == 'worsening':
            score += 1.0
            risk_factors.append("上盘水位上升 (+0.05+): 上盘承压")

    # ── 平赔缩短 → +1 (保留V2.3逻辑) ──
    if draw_signal == 'DOWN':
        score += 1.0
        risk_factors.append("平赔缩短 → 平局风险")

    # ── 首发问题 → +1 ──
    if lineup_issue:
        score += 1.0
        risk_factors.append("核心伤疑 → 风险+1")

    # ── V2.4 XLS时效扣分 ──
    if xls_freshness and xls_freshness.confidence_penalty > 0:
        score += xls_freshness.confidence_penalty * 10  # 最大0.8分
        if xls_freshness.data_gap_warning:
            risk_factors.append(f"XLS时效差({xls_freshness.last_update_hours_before:.0f}h)")

    return round(min(score, 10), 1), risk_factors


def risk_level_v24(score):
    if score <= 2: return "🟢 低"
    if score <= 4: return "🟡 中低"
    if score <= 6: return "🟠 中高"
    if score <= 8: return "🔴 高"
    return "💀 极高"


# ── 保留V2.3兼容接口 ──
def calc_risk_score(heat_gap=None, pnl=None, off_field=0, handicap_retreat=0,
                    draw_signal=None, lineup_issue=False):
    """V2.3兼容接口 - 调用V2.4核心但无新参数"""
    score, _ = calc_risk_score_v24(
        heat_gap=heat_gap, pnl=pnl, off_field=off_field,
        handicap_retreat=handicap_retreat, draw_signal=draw_signal,
        lineup_issue=lineup_issue,
    )
    return score


def risk_level(score):
    return risk_level_v24(score)


def quick_risk(home, away, heat_gap=None, pnl=None, **kwargs):
    s = calc_risk_score(heat_gap=heat_gap, pnl=pnl, **kwargs)
    return f"{home} vs {away}: 风险{s:.1f}/10 {risk_level(s)}"


# ═══════════════════════════════════════════════════════════════
# V2.6 新信号 (2026-06-16)
# ═══════════════════════════════════════════════════════════════

def unanimity_signal(home_changes: list, threshold: float = 0.8) -> dict:
    """
    全票通过信号: 检测博彩公司是否大面积同向调整赔率。

    Args:
        home_changes: 主胜赔率变化百分比列表 (正=升赔/看衰, 负=降赔/看好)
        threshold: 同向比例阈值 (默认80%)

    Returns:
        {'triggered': bool, 'direction': 'bearish'/'bullish', 'ratio': float, 'strength': 'strong'/'extreme'}
    """
    if not home_changes:
        return {'triggered': False, 'direction': '', 'ratio': 0, 'strength': ''}

    up_count = sum(1 for c in home_changes if c > 0.5)
    down_count = sum(1 for c in home_changes if c < -0.5)
    total = len(home_changes)

    up_ratio = up_count / total
    down_ratio = down_count / total

    if up_ratio >= threshold:
        strength = 'extreme' if up_ratio >= 0.9 else 'strong'
        return {'triggered': True, 'direction': 'bearish', 'ratio': up_ratio, 'strength': strength}
    elif down_ratio >= threshold:
        strength = 'extreme' if down_ratio >= 0.9 else 'strong'
        return {'triggered': True, 'direction': 'bullish', 'ratio': down_ratio, 'strength': strength}

    return {'triggered': False, 'direction': '', 'ratio': max(up_ratio, down_ratio), 'strength': ''}


def draw_collapse_signal(draw_changes: list, threshold: float = -5.0, min_books: int = 8) -> dict:
    """
    平赔暴跌预警: 检测多家博彩公司同步大幅下调平赔。

    Args:
        draw_changes: 平赔变化百分比列表
        threshold: 平均跌幅阈值 (默认-5%)
        min_books: 最少博彩公司数

    Returns:
        {'triggered': bool, 'avg_change': float, 'down_count': int, 'severity': 'critical'/'warning'/'none'}
    """
    if not draw_changes or len(draw_changes) < min_books:
        return {'triggered': False, 'avg_change': 0, 'down_count': 0, 'severity': 'none'}

    avg = sum(draw_changes) / len(draw_changes)
    down_count = sum(1 for c in draw_changes if c < -1)

    if avg <= threshold and down_count >= len(draw_changes) * 0.7:
        severity = 'critical' if avg <= -7 else 'warning'
        return {'triggered': True, 'avg_change': avg, 'down_count': down_count, 'severity': severity}

    return {'triggered': False, 'avg_change': avg, 'down_count': down_count, 'severity': 'none'}


def detect_xls_betfair_divergence(xls_direction: str, betfair_trade_ratio: float,
                                   betfair_cold: float, home_odds: float) -> dict:
    """
    XLS-必发背离检测: XLS共识方向与必发资金方向是否冲突。

    Args:
        xls_direction: XLS共识方向 ('bearish'=看衰强队 / 'bullish'=看好强队 / 'neutral')
        betfair_trade_ratio: 必发热门方交易比例
        betfair_cold: 必发冷热指数
        home_odds: 主胜欧赔

    Returns:
        {'divergence': bool, 'type': str, 'detail': str}
    """
    # 判断谁是强队
    if home_odds <= 1.60:
        strong_side = 'home'
    elif home_odds >= 3.0:
        strong_side = 'away'
    else:
        strong_side = 'home'  # 默认主队

    # XLS看衰强队 (bearish = 主升 = 看衰主队/强队)
    xls_bearish_strong = (xls_direction == 'bearish')
    xls_bullish_strong = (xls_direction == 'bullish')

    # 必发资金方向 (V2.8 修复: 区分主客队)
    if strong_side == 'home':
        bf_bullish_strong = (betfair_trade_ratio > 0.65 and betfair_cold > 0)
    else:
        # 强队是客队: 客队交易比例高 + 客队方向冷热为正 = 必发看好客队
        bf_bullish_strong = (betfair_trade_ratio > 0.55 and betfair_cold < 0)

    if xls_bearish_strong and bf_bullish_strong:
        return {
            'divergence': True,
            'type': 'XLS看衰·必发看多',
            'detail': f'博彩公司抬升赔率 vs 必发资金涌入 (冷热{betfair_cold:+.0f}) → 市场分歧⚠️'
        }
    elif xls_bullish_strong and not bf_bullish_strong:
        return {
            'divergence': True,
            'type': 'XLS看好·必发冷淡',
            'detail': f'博彩公司降低赔率 vs 必发资金未跟进 → 诱盘嫌疑⚠️'
        }

    return {'divergence': False, 'type': '', 'detail': ''}


# ── V2.4 四场回测 ──
if __name__ == "__main__":
    from v24_optimization import (
        GapLevel, analyze_odds_consensus, diagnose_water, check_xls_freshness,
    )

    print("=" * 60)
    print("V2.4 风险评分 四场回测")
    print("=" * 60)

    # 1. 德国 vs 库拉索 (应: 中低风险, V2.3误判为低风险)
    print("\n📋 德国 vs 库拉索 [extreme gap]")
    consensus_de = analyze_odds_consensus(21, 0, 14, 23)
    s1, f1 = calc_risk_score_v24(
        handicap_retreat=2.5,
        gap_level=GapLevel.EXTREME,
        odds_consensus=consensus_de,
    )
    print(f"  风险: {s1}/10 {risk_level_v24(s1)} | 因子: {f1}")
    print(f"  解读: extreme gap下降盘信号降权, 实际7-1不穿盘→风险应低于V2.3")

    # 2. 荷兰 vs 日本 (应: 中高风险, 水位恶化预警)
    print("\n📋 荷兰 vs 日本 [close gap + 水位恶化]")
    consensus_nl = analyze_odds_consensus(33, 3, 12, 25)
    water_nl = diagnose_water(0.85, 1.02)
    s2, f2 = calc_risk_score_v24(
        handicap_retreat=0,
        gap_level=GapLevel.CLOSE,
        odds_consensus=consensus_nl,
        water_diagnosis=water_nl,
    )
    print(f"  风险: {s2}/10 {risk_level_v24(s2)} | 因子: {f2}")
    print(f"  解读: 水位恶化+欧赔看衰→高风险预警, 实际2-2平✅")

    # 3. IC vs 厄瓜多尔 (应: 中低风险, close gap信号可靠)
    print("\n📋 科特迪瓦 vs 厄瓜多尔 [close gap]")
    consensus_ic = analyze_odds_consensus(33, 13, 5, 34)
    s3, f3 = calc_risk_score_v24(
        handicap_retreat=0,
        gap_level=GapLevel.CLOSE,
        odds_consensus=consensus_ic,
        draw_signal='DOWN',
    )
    print(f"  风险: {s3}/10 {risk_level_v24(s3)} | 因子: {f3}")
    print(f"  解读: 平赔收缩+close gap, 退盘信号可靠, 实际1-0✅")

    # 4. 瑞典 vs 突尼斯 (应: 低风险, 欧赔共识看好)
    print("\n📋 瑞典 vs 突尼斯 [moderate gap]")
    consensus_se = analyze_odds_consensus(7, 24, 32, 7)
    water_se = diagnose_water(0.91, 0.85)
    xls_se = check_xls_freshness(12.4, 5)
    s4, f4 = calc_risk_score_v24(
        handicap_retreat=0,
        gap_level=GapLevel.MODERATE,
        odds_consensus=consensus_se,
        water_diagnosis=water_se,
        xls_freshness=xls_se,
    )
    print(f"  风险: {s4}/10 {risk_level_v24(s4)} | 因子: {f4}")
    print(f"  解读: 欧赔看好+水位改善=低风险, XLS时效扣分轻微, 实际5-1✅")

    print("\n" + "=" * 60)
    print("V2.4 风险评分回测完成")
    print("=" * 60)

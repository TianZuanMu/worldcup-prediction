"""
V2.9 比赛时间影响分析
评估: 当地时间段 · 时差/旅途疲劳 · 露水风险 · 室内外差异
依赖: match_context.py (场馆+赛程)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from match_context import get_match, get_venue_for_match, get_team_group, normalize_team_name


# ── 各大洲时区参考 ──
CONF_TIMEZONE_OFFSETS: Dict[str, int] = {
    'UEFA': 1,       # 欧洲中部 UTC+1
    'CONMEBOL': -3,  # 南美 UTC-3
    'CONCACAF': -5,  # 北美/中美 UTC-5
    'AFC': 8,        # 亚洲 UTC+8
    'CAF': 0,        # 非洲 UTC+0
    'OFC': 12,       # 大洋洲 UTC+12
}

# ── 球队所属洲 (从fifa_rank_db模式继承) ──
TEAM_CONFEDERATION: Dict[str, str] = {
    '墨西哥': 'CONCACAF', '南非': 'CAF', '韩国': 'AFC', '捷克': 'UEFA',
    '加拿大': 'CONCACAF', '波黑': 'UEFA', '卡塔尔': 'AFC', '瑞士': 'UEFA',
    '巴西': 'CONMEBOL', '摩洛哥': 'CAF', '巴拿马': 'CONCACAF', '加纳': 'CAF',
    '德国': 'UEFA', '荷兰': 'UEFA', '日本': 'AFC', '科特迪瓦': 'CAF',
    '英格兰': 'UEFA', '克罗地亚': 'UEFA', '美国': 'CONCACAF', '海地': 'CONCACAF',
    '葡萄牙': 'UEFA', '刚果民主共和国': 'CAF', '苏格兰': 'UEFA', '匈牙利': 'UEFA',
    '西班牙': 'UEFA', '佛得角': 'CAF', '土耳其': 'UEFA', '塞尔维亚': 'UEFA',
    '意大利': 'UEFA', '乌拉圭': 'CONMEBOL', '伊朗': 'AFC', '乌兹别克斯坦': 'AFC',
    '法国': 'UEFA', '塞内加尔': 'CAF', '伊拉克': 'AFC', '挪威': 'UEFA',
    '阿根廷': 'CONMEBOL', '阿尔及利亚': 'CAF', '奥地利': 'UEFA', '约旦': 'AFC',
    '比利时': 'UEFA', '哥伦比亚': 'CONMEBOL', '澳大利亚': 'AFC', '新西兰': 'OFC',
    '智利': 'CONMEBOL', '埃及': 'CAF', '阿联酋': 'AFC', '哥斯达黎加': 'CONCACAF',
}


@dataclass
class TimeImpact:
    """比赛时间影响评估"""
    time_category: str          # 'noon'|'afternoon'|'evening'|'late_night'
    local_hour: int             # 当地时间(小时, 0-23)
    venue_indoor: bool          # 室内场馆标志
    venue_altitude_m: int       # 海拔

    # 风险评分 (0-1)
    heat_risk: float = 0.0
    fatigue_risk: float = 0.0
    dew_risk: float = 0.0
    altitude_risk: float = 0.0

    # 时差影响
    home_jetlag: float = 0.0
    away_jetlag: float = 0.0

    # 综合
    overall_adjustment: float = 0.0   # -5 to +5
    recommendations: List[str] = field(default_factory=list)


# 🆕 V3.3: 时差衰减系数 (球队提前1-2周抵达赛区·已基本适应)
JETLAG_DECAY = {1: 0.30, 2: 0.10, 3: 0.00}  # MD1→30%, MD2→10%, MD3→0%


def analyze_match_time(match_name: str, matchday: int = 1) -> TimeImpact:
    """
    分析比赛时间对双方的影响
    Args:
        match_name: '法国VS塞内加尔' 格式
        matchday: 比赛日编号 (1/2/3), 用于时差衰减
    Returns:
        TimeImpact dataclass
    """
    m = get_match(match_name=match_name)
    if not m:
        return TimeImpact(time_category='unknown', local_hour=15,
                          venue_indoor=False, venue_altitude_m=0,
                          recommendations=['比赛未在赛程中找到'])

    venue = get_venue_for_match(match_name=match_name)
    indoor = venue['indoor'] if venue else False
    altitude = venue['altitude_m'] if venue else 0

    hour = m.local_hour

    # ── 时间段分类 ──
    if 12 <= hour < 14:
        time_cat = 'noon'
    elif 14 <= hour < 17:
        time_cat = 'afternoon'
    elif 17 <= hour < 21:
        time_cat = 'evening'
    else:
        time_cat = 'late_night'

    impact = TimeImpact(
        time_category=time_cat,
        local_hour=hour,
        venue_indoor=indoor,
        venue_altitude_m=altitude,
    )

    # ── 高温风险 (仅室外) ──
    if not indoor:
        if time_cat == 'noon':
            impact.heat_risk = 0.7
        elif time_cat == 'afternoon':
            impact.heat_risk = 0.4
        elif time_cat == 'evening':
            impact.heat_risk = 0.1
        else:
            impact.heat_risk = 0.0
    # 室内: heat_risk = 0 (恒温)

    # ── 疲劳风险 ──
    if hour >= 21:
        impact.fatigue_risk = 0.5
    elif hour >= 23:
        impact.fatigue_risk = 0.7
    elif hour <= 13:
        impact.fatigue_risk = 0.2  # 早场比赛需要早起

    # ── 露水风险 (深夜室外) ──
    if not indoor and hour >= 21:
        impact.dew_risk = 0.6
        if hour >= 23:
            impact.dew_risk = 0.8

    # ── 海拔风险 ──
    if altitude >= 2000:
        impact.altitude_risk = 0.8
    elif altitude >= 1500:
        impact.altitude_risk = 0.5
    elif altitude >= 1000:
        impact.altitude_risk = 0.2

    # ── 时差影响 ──
    home_conf = TEAM_CONFEDERATION.get(m.home, 'UEFA')
    away_conf = TEAM_CONFEDERATION.get(m.away, 'UEFA')
    venue_offset = venue['utc_offset'] if venue else -5

    home_offset = CONF_TIMEZONE_OFFSETS.get(home_conf, 0)
    away_offset = CONF_TIMEZONE_OFFSETS.get(away_conf, 0)

    home_tz_diff = abs(home_offset - venue_offset)
    away_tz_diff = abs(away_offset - venue_offset)

    # 时差>6小时 → 显著影响
    impact.home_jetlag = min(1.0, home_tz_diff / 10)
    impact.away_jetlag = min(1.0, away_tz_diff / 10)

    # ── 综合调整 ──
    adj = 0.0

    # 热风险: 只影响不适应高温的球队(欧洲/高纬度)
    if impact.heat_risk > 0.3:
        recs = []
        if home_conf == 'UEFA':
            adj -= 2
            recs.append(f'欧洲主队{m.home}不适应午场高温')
        if away_conf == 'UEFA':
            adj += 1  # 客队是欧洲队更吃亏 (偏主队)
            recs.append(f'欧洲客队{m.away}午场高温劣势')
        if home_conf in ('CAF', 'CONCACAF'):
            adj += 0.5  # 非洲/北美队适应高温
            recs.append(f'{m.home}习惯高温条件')
        if away_conf in ('CAF', 'CONCACAF'):
            adj -= 0.5
            recs.append(f'{m.away}习惯高温条件')
        impact.recommendations.extend(recs)

    # 深夜&露水
    if impact.dew_risk > 0.5:
        adj -= 1
        impact.recommendations.append(f'深夜{hour}:00开球·露水影响球速+疲劳')
        impact.recommendations.append('球速加快→对技术传控队不利→失误率上升')

    # 高海拔
    if impact.altitude_risk > 0.3:
        # 检查双方是否来自高海拔国家
        home_high = home_conf == 'CONMEBOL'  # 南美有高海拔城市
        away_high = away_conf == 'CONMEBOL'
        if not home_high:
            adj -= impact.altitude_risk * 3
            impact.recommendations.append(f'{m.home}不适应高海拔({altitude}m)')
        if not away_high:
            adj += impact.altitude_risk * 2
            impact.recommendations.append(f'{m.away}客场高海拔({altitude}m)劣势')

    # 时差 (🆕 V3.3: 衰减 MD1→30% MD2→10% MD3→0%)
    decay = JETLAG_DECAY.get(matchday, 0.10)
    if impact.away_jetlag > 0.6:
        raw_adj = round(2 * decay)
        if raw_adj > 0:
            adj += raw_adj  # 客队有时差 → 主队优势
            impact.recommendations.append(f'{m.away}跨{away_tz_diff}时区→时差影响(已衰减至{decay:.0%})')
    if impact.home_jetlag > 0.6 and impact.home_jetlag > impact.away_jetlag:
        raw_adj = round(-1 * decay)
        if raw_adj < 0:
            adj += raw_adj
            impact.recommendations.append(f'{m.home}同样受时差影响(已衰减至{decay:.0%})')

    # 理想条件
    if time_cat == 'evening' and not indoor and altitude < 500:
        impact.recommendations.append('傍晚开球·理想比赛条件·无偏向')

    impact.overall_adjustment = max(-5, min(5, adj))
    return impact


def get_timezone_diff(team_name: str, venue_utc_offset: int) -> int:
    """计算球队与场馆的时区差"""
    conf = TEAM_CONFEDERATION.get(team_name, 'UEFA')
    team_offset = CONF_TIMEZONE_OFFSETS.get(conf, 0)
    return abs(team_offset - venue_utc_offset)


# ── 独立测试 ──
if __name__ == '__main__':
    test_matches = ['法国VS塞内加尔', '伊拉克VS挪威', '阿根廷VS阿尔及利亚', '奥地利VS约旦']

    for mn in test_matches:
        print(f"\n{'='*60}")
        impact = analyze_match_time(mn)
        print(f"  🕐 {mn}")
        print(f"  当地时间: {impact.local_hour}:00 ({impact.time_category})")
        print(f"  场馆: {'室内' if impact.venue_indoor else '室外'} | 海拔: {impact.venue_altitude_m}m")
        print(f"  热风险: {impact.heat_risk:.1f} | 疲劳: {impact.fatigue_risk:.1f} | 露水: {impact.dew_risk:.1f} | 海拔: {impact.altitude_risk:.1f}")
        print(f"  时差: 主{impact.home_jetlag:.1f} / 客{impact.away_jetlag:.1f}")
        print(f"  综合调整: {impact.overall_adjustment:+.1f}%")
        for r in impact.recommendations:
            print(f"    → {r}")

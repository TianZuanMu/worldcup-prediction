"""
V2.9 天气实时追踪
获取: 比赛城市实时天气 → 温度/湿度/风速/降水
评估: 对比赛的影响(体能/球速/战术)
依赖: match_context.py (场馆+城市)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from config import CONF


# ── 天气数据结构 ──

@dataclass
class WeatherData:
    temperature_c: float = 20.0
    humidity_pct: float = 50.0
    wind_speed_kmh: float = 10.0
    precipitation_mm: float = 0.0
    condition: str = 'clear'       # clear/rain/cloudy/storm/overcast
    fetched_at: str = ''
    source: str = 'fallback'       # 'live' | 'cache_Nh' | 'fallback' | 'indoor'
    confidence: float = 0.5        # 0-1, fallback的置信度低
    note: str = ''                 # 数据来源说明·降级原因


@dataclass
class WeatherImpact:
    score: float = 0.0                # -10 to +10, negative=bad for home
    over_under_adjustment: float = 0.0  # -0.2 to +0.2
    temp_impact: float = 0.0
    humidity_impact: float = 0.0
    wind_impact: float = 0.0
    precipitation_impact: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ── 天气缓存 (TTL由CONF.weather_cache_ttl_hours控制) ──

_WEATHER_CACHE: Dict[str, tuple] = {}  # key → (WeatherData, expiry_time)


# ── 季节平均天气 (6月·各城市fallback) ──

SEASONAL_AVERAGES: Dict[str, dict] = {
    'Mexico City':     {'temp': 23, 'humidity': 45, 'wind': 8,  'rain_prob': 0.3, 'note': '高原·午后阵雨可能'},
    'Monterrey':       {'temp': 32, 'humidity': 55, 'wind': 10, 'rain_prob': 0.1, 'note': '炎热干燥'},
    'Guadalajara':     {'temp': 28, 'humidity': 50, 'wind': 8,  'rain_prob': 0.2, 'note': '高原·温和'},
    'Toronto':         {'temp': 22, 'humidity': 55, 'wind': 12, 'rain_prob': 0.3, 'note': '温和·湖风'},
    'Vancouver':       {'temp': 18, 'humidity': 65, 'wind': 10, 'rain_prob': 0.4, 'note': '凉爽·可能小雨'},
    'East Rutherford (NYC)': {'temp': 26, 'humidity': 60, 'wind': 10, 'rain_prob': 0.3, 'note': '夏季温暖'},
    'Arlington (Dallas)':    {'temp': 33, 'humidity': 55, 'wind': 12, 'rain_prob': 0.1, 'note': '炎热·室内恒温'},
    'Kansas City':     {'temp': 28, 'humidity': 60, 'wind': 12, 'rain_prob': 0.3, 'note': '中西部夏季'},
    'Houston':         {'temp': 32, 'humidity': 70, 'wind': 10, 'rain_prob': 0.3, 'note': '高温高湿·室内恒温'},
    'Atlanta':         {'temp': 29, 'humidity': 65, 'wind': 8,  'rain_prob': 0.3, 'note': '南方夏季·室内恒温'},
    'Inglewood (LA)':  {'temp': 24, 'humidity': 55, 'wind': 8,  'rain_prob': 0.05,'note': '典型加州天气·完美'},
    'Santa Clara (SF)':{'temp': 22, 'humidity': 60, 'wind': 12, 'rain_prob': 0.1, 'note': '湾区·海风·下午凉爽'},
    'Philadelphia':    {'temp': 27, 'humidity': 58, 'wind': 10, 'rain_prob': 0.3, 'note': '东北夏季'},
    'Seattle':         {'temp': 20, 'humidity': 65, 'wind': 10, 'rain_prob': 0.3, 'note': '凉爽·可能小雨'},
    'Foxborough (Boston)': {'temp': 24, 'humidity': 58, 'wind': 12, 'rain_prob': 0.3, 'note': '新英格兰夏季'},
    'Miami Gardens':   {'temp': 30, 'humidity': 72, 'wind': 10, 'rain_prob': 0.4, 'note': '高温高湿·午后雷暴可能'},
}


# ── 球队洲际归属 (用于天气适应度判断) ──

TEAM_CONF: Dict[str, str] = {
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


def _get_cache_key(match_name: str) -> str:
    """生成缓存key (按小时窗口)"""
    now = datetime.utcnow()
    hour_block = now.replace(minute=0, second=0, microsecond=0)
    return f"{match_name}_{hour_block.isoformat()}"


def get_weather(match_name: str, force_refresh: bool = False) -> WeatherData:
    """
    获取比赛城市的天气
    优先从缓存获取, 否则使用季节平均值
    (WebSearch版本需要在有网络工具的上下文中调用)
    """
    # 缓存检查
    cache_key = _get_cache_key(match_name)
    if not force_refresh and cache_key in _WEATHER_CACHE:
        data, expiry = _WEATHER_CACHE[cache_key]
        if datetime.utcnow() < expiry:
            # 计算缓存年龄
            if data.fetched_at:
                fetched_dt = datetime.fromisoformat(data.fetched_at)
                age_h = (datetime.utcnow() - fetched_dt).total_seconds() / 3600
            else:
                age_h = CONF.weather_cache_ttl_hours  # 保守假设
            data.source = f'cache_{int(age_h)}h'
            # 缓存越旧置信度越低
            if age_h > CONF.weather_cache_ttl_hours:
                data.confidence = max(0.1, 0.5 - 0.1 * (age_h - CONF.weather_cache_ttl_hours))
                data.note = f'缓存过期{age_h:.1f}h (TTL={CONF.weather_cache_ttl_hours}h)'
            return data

    # 获取场馆
    from match_context import get_venue_for_match
    venue = get_venue_for_match(match_name=match_name)

    if not venue:
        return WeatherData(
            source='fallback', confidence=0.2,
            note='无场馆信息→默认20°C',
        )

    city = venue['city']
    indoor = venue['indoor']

    # 室内场馆 → 恒温假设
    if indoor:
        w = WeatherData(
            temperature_c=22, humidity_pct=45, wind_speed_kmh=0,
            precipitation_mm=0, condition='indoor',
            fetched_at=datetime.utcnow().isoformat(),
            source='live',
            confidence=0.9,
            note='室内恒温·可靠',
        )
    else:
        # 室外 → 季节平均值
        avg = SEASONAL_AVERAGES.get(city, {'temp': 22, 'humidity': 55, 'wind': 10, 'rain_prob': 0.2})
        w = WeatherData(
            temperature_c=avg['temp'],
            humidity_pct=avg['humidity'],
            wind_speed_kmh=avg['wind'],
            precipitation_mm=0,
            condition='clear',
            fetched_at=datetime.utcnow().isoformat(),
            source='fallback',
            confidence=0.5,
            note=f'季节均值估算({city})·非实时天气',
        )

    # 缓存
    expiry = datetime.utcnow() + timedelta(hours=CONF.weather_cache_ttl_hours)
    _WEATHER_CACHE[cache_key] = (w, expiry)
    return w


def update_weather_from_web(match_name: str, temp: float, humidity: float,
                            wind: float, precip: float = 0, condition: str = 'clear'):
    """
    从外部(WebSearch结果)更新天气
    用于在pre_match_report中集成WebSearch工具后调用
    """
    w = WeatherData(
        temperature_c=temp, humidity_pct=humidity,
        wind_speed_kmh=wind, precipitation_mm=precip,
        condition=condition,
        fetched_at=datetime.utcnow().isoformat(),
        source='live',
        confidence=0.85,
        note='WebSearch实时获取',
    )
    cache_key = _get_cache_key(match_name)
    expiry = datetime.utcnow() + timedelta(hours=CONF.weather_cache_ttl_hours)
    _WEATHER_CACHE[cache_key] = (w, expiry)
    return w


def analyze_weather_impact(weather: WeatherData, home: str, away: str) -> WeatherImpact:
    """
    分析天气对双方的影响
    """
    impact = WeatherImpact()
    home_conf = TEAM_CONF.get(home, 'UEFA')
    away_conf = TEAM_CONF.get(away, 'UEFA')

    # ── 数据新鲜度警告 ──
    if weather.source == 'fallback':
        impact.warnings.append(f'天气数据为估算值(非实时·置信度{weather.confidence:.0%})')
        if weather.note:
            impact.warnings.append(f'  └ {weather.note}')

    # ── 温度影响 ──
    t = weather.temperature_c
    if t >= 32:
        # 极端高温
        impact.temp_impact = -3 if home_conf == 'UEFA' else 0
        if away_conf == 'UEFA':
            impact.temp_impact += 2  # 客队更惨
            impact.warnings.append(f'高温{t:.0f}°C: 欧洲客队{away}体能消耗+15%')
        if home_conf == 'UEFA':
            impact.warnings.append(f'高温{t:.0f}°C: 欧洲主队{home}也不适应')
        impact.over_under_adjustment -= 0.1  # 高温 → 节奏慢 → Under
    elif t >= 28:
        impact.temp_impact = -1.5 if home_conf == 'UEFA' else 0.5
        if away_conf == 'UEFA':
            impact.temp_impact += 1
            impact.warnings.append(f'偏热{t:.0f}°C: {away}不适应')
        impact.over_under_adjustment -= 0.05
    elif t <= 8:
        impact.warnings.append(f'低温{t:.0f}°C: 可能影响球速')
        impact.over_under_adjustment -= 0.05

    # ── 湿度影响 ──
    h = weather.humidity_pct
    if h >= 75:
        impact.humidity_impact = -1
        impact.warnings.append(f'高湿度{h:.0f}%: 球速变慢·体能消耗大')
        impact.over_under_adjustment -= 0.05
    elif h >= 65:
        impact.humidity_impact = -0.5

    # ── 风速影响 ──
    w = weather.wind_speed_kmh
    if w >= 25:
        impact.wind_impact = -2
        impact.warnings.append(f'大风{w:.0f}km/h: 长传/定位球受影响严重')
        impact.over_under_adjustment -= 0.05
    elif w >= 15:
        impact.wind_impact = -1
        impact.warnings.append(f'有风{w:.0f}km/h: 长传精准度受影响')

    # ── 降水影响 ──
    p = weather.precipitation_mm
    if p >= 5:
        impact.precipitation_impact = -2
        impact.warnings.append(f'大雨{p:.0f}mm: 草皮湿滑·球速加快·失误率↑')
        impact.over_under_adjustment += 0.05  # 雨天 → 球速快 → Over概率↑
    elif p >= 1:
        impact.precipitation_impact = -0.5
        impact.warnings.append(f'小雨{p:.0f}mm: 轻微影响')

    # ── 综合分 ──
    impact.score = (impact.temp_impact + impact.humidity_impact +
                    impact.wind_impact + impact.precipitation_impact)
    impact.score = max(-5, min(5, impact.score))
    impact.over_under_adjustment = max(-0.2, min(0.2, impact.over_under_adjustment))

    if not impact.warnings:
        impact.warnings.append('天气理想·无特殊影响')

    return impact


def clear_cache():
    """清除天气缓存"""
    _WEATHER_CACHE.clear()


# ── 独立测试 ──
if __name__ == '__main__':
    test_matches = ['法国VS塞内加尔', '伊拉克VS挪威', '阿根廷VS阿尔及利亚', '奥地利VS约旦']

    for mn in test_matches:
        print(f"\n{'='*60}")
        parts = mn.split('VS')
        home, away = parts[0], parts[1]

        weather = get_weather(mn)
        impact = analyze_weather_impact(weather, home, away)

        print(f"  🌡️ {mn}")
        from match_context import get_venue_for_match
        venue = get_venue_for_match(match_name=mn)
        city = venue['city'] if venue else '?'
        indoor = venue['indoor'] if venue else False
        print(f"  城市: {city} | {'室内' if indoor else '室外'}")
        print(f"  天气: {weather.temperature_c}°C | 湿度{weather.humidity_pct}% | 风速{weather.wind_speed_kmh}km/h | {weather.condition}")
        print(f"  来源: {weather.source} (置信度{weather.confidence:.0%})")
        if weather.note:
            print(f"  说明: {weather.note}")
        print(f"  综合影响: {impact.score:+.1f} | 大小球修正: {impact.over_under_adjustment:+.2f}")
        for w in impact.warnings:
            print(f"    → {w}")

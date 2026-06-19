"""
V2.9 比赛场地与赛程数据库
提供: 16个场馆信息 · 48场小组赛程 · 32队分组映射
用途: 天气追踪/出线形势/比赛时间影响等模块的数据基础
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime


# ── 场馆数据库 (2026世界杯16座场馆) ──

VENUE_DB: Dict[str, dict] = {
    # ═══ 墨西哥 (3座) ═══
    'Estadio Azteca': {
        'name': 'Estadio Azteca', 'city': 'Mexico City', 'country': 'Mexico',
        'altitude_m': 2250, 'grass_type': 'natural', 'indoor': False,
        'capacity': 87523, 'timezone': 'America/Mexico_City', 'utc_offset': -6,
    },
    'Estadio BBVA': {
        'name': 'Estadio BBVA', 'city': 'Monterrey', 'country': 'Mexico',
        'altitude_m': 540, 'grass_type': 'natural', 'indoor': False,
        'capacity': 53500, 'timezone': 'America/Monterrey', 'utc_offset': -6,
    },
    'Estadio Akron': {
        'name': 'Estadio Akron', 'city': 'Guadalajara', 'country': 'Mexico',
        'altitude_m': 1566, 'grass_type': 'natural', 'indoor': False,
        'capacity': 48100, 'timezone': 'America/Mexico_City', 'utc_offset': -6,
    },
    # ═══ 加拿大 (2座) ═══
    'BMO Field': {
        'name': 'BMO Field', 'city': 'Toronto', 'country': 'Canada',
        'altitude_m': 76, 'grass_type': 'hybrid', 'indoor': False,
        'capacity': 45500, 'timezone': 'America/Toronto', 'utc_offset': -4,
    },
    'BC Place': {
        'name': 'BC Place', 'city': 'Vancouver', 'country': 'Canada',
        'altitude_m': 4, 'grass_type': 'artificial', 'indoor': True,
        'capacity': 54500, 'timezone': 'America/Vancouver', 'utc_offset': -7,
    },
    # ═══ 美国 (11座) ═══
    'MetLife Stadium': {
        'name': 'MetLife Stadium', 'city': 'East Rutherford (NYC)', 'country': 'USA',
        'altitude_m': 3, 'grass_type': 'natural', 'indoor': False,
        'capacity': 82500, 'timezone': 'America/New_York', 'utc_offset': -4,
    },
    'AT&T Stadium': {
        'name': 'AT&T Stadium', 'city': 'Arlington (Dallas)', 'country': 'USA',
        'altitude_m': 180, 'grass_type': 'artificial', 'indoor': True,
        'capacity': 80000, 'timezone': 'America/Chicago', 'utc_offset': -5,
    },
    'Arrowhead Stadium': {
        'name': 'Arrowhead Stadium', 'city': 'Kansas City', 'country': 'USA',
        'altitude_m': 277, 'grass_type': 'natural', 'indoor': False,
        'capacity': 76416, 'timezone': 'America/Chicago', 'utc_offset': -5,
    },
    'NRG Stadium': {
        'name': 'NRG Stadium', 'city': 'Houston', 'country': 'USA',
        'altitude_m': 15, 'grass_type': 'natural', 'indoor': True,
        'capacity': 72220, 'timezone': 'America/Chicago', 'utc_offset': -5,
    },
    'Mercedes-Benz Stadium': {
        'name': 'Mercedes-Benz Stadium', 'city': 'Atlanta', 'country': 'USA',
        'altitude_m': 320, 'grass_type': 'artificial', 'indoor': True,
        'capacity': 71000, 'timezone': 'America/New_York', 'utc_offset': -4,
    },
    'SoFi Stadium': {
        'name': 'SoFi Stadium', 'city': 'Inglewood (LA)', 'country': 'USA',
        'altitude_m': 30, 'grass_type': 'artificial', 'indoor': True,
        'capacity': 70240, 'timezone': 'America/Los_Angeles', 'utc_offset': -7,
    },
    'Levi\'s Stadium': {
        'name': "Levi's Stadium", 'city': 'Santa Clara (SF)', 'country': 'USA',
        'altitude_m': 4, 'grass_type': 'natural', 'indoor': False,
        'capacity': 68500, 'timezone': 'America/Los_Angeles', 'utc_offset': -7,
    },
    'Lincoln Financial Field': {
        'name': 'Lincoln Financial Field', 'city': 'Philadelphia', 'country': 'USA',
        'altitude_m': 12, 'grass_type': 'natural', 'indoor': False,
        'capacity': 67594, 'timezone': 'America/New_York', 'utc_offset': -4,
    },
    'Lumen Field': {
        'name': 'Lumen Field', 'city': 'Seattle', 'country': 'USA',
        'altitude_m': 50, 'grass_type': 'artificial', 'indoor': False,
        'capacity': 68740, 'timezone': 'America/Los_Angeles', 'utc_offset': -7,
    },
    'Gillette Stadium': {
        'name': 'Gillette Stadium', 'city': 'Foxborough (Boston)', 'country': 'USA',
        'altitude_m': 70, 'grass_type': 'natural', 'indoor': False,
        'capacity': 65878, 'timezone': 'America/New_York', 'utc_offset': -4,
    },
    'Hard Rock Stadium': {
        'name': 'Hard Rock Stadium', 'city': 'Miami Gardens', 'country': 'USA',
        'altitude_m': 2, 'grass_type': 'natural', 'indoor': False,
        'capacity': 65326, 'timezone': 'America/New_York', 'utc_offset': -4,
    },
}

# ── 球队-小组映射 (12组×4队=48队, 仅收录已确认参赛队) ──

TEAM_GROUPS: Dict[str, str] = {
    # A组: 墨西哥、南非、韩国、捷克
    '墨西哥': 'A', '南非': 'A', '韩国': 'A', '捷克': 'A',
    # B组: 加拿大、波黑、卡塔尔、瑞士
    '加拿大': 'B', '波黑': 'B', '卡塔尔': 'B', '瑞士': 'B',
    # C组: 巴西、摩洛哥、海地、苏格兰
    '巴西': 'C', '摩洛哥': 'C', '海地': 'C', '苏格兰': 'C',
    # D组: 美国、巴拉圭、澳大利亚、土耳其
    '美国': 'D', '巴拉圭': 'D', '澳大利亚': 'D', '土耳其': 'D',
    # E组: 德国、库拉索、科特迪瓦、厄瓜多尔
    '德国': 'E', '库拉索': 'E', '科特迪瓦': 'E', '厄瓜多尔': 'E',
    # F组: 荷兰、日本、瑞典、突尼斯
    '荷兰': 'F', '日本': 'F', '瑞典': 'F', '突尼斯': 'F',
    # G组: 比利时、埃及、伊朗、新西兰
    '比利时': 'G', '埃及': 'G', '伊朗': 'G', '新西兰': 'G',
    # H组: 西班牙、佛得角、沙特阿拉伯、乌拉圭
    '西班牙': 'H', '佛得角': 'H', '沙特阿拉伯': 'H', '乌拉圭': 'H',
    # I组: 法国、塞内加尔、伊拉克、挪威
    '法国': 'I', '塞内加尔': 'I', '伊拉克': 'I', '挪威': 'I',
    # J组: 阿根廷、阿尔及利亚、奥地利、约旦
    '阿根廷': 'J', '阿尔及利亚': 'J', '奥地利': 'J', '约旦': 'J',
    # K组: 葡萄牙、民主刚果、乌兹别克斯坦、哥伦比亚
    '葡萄牙': 'K', '民主刚果': 'K', '乌兹别克斯坦': 'K', '哥伦比亚': 'K',
    # L组: 英格兰、克罗地亚、加纳、巴拿马
    '英格兰': 'L', '克罗地亚': 'L', '加纳': 'L', '巴拿马': 'L',
}


# ── 赛程数据库 (72场小组赛) ──

@dataclass
class GroupMatch:
    """单场小组赛数据"""
    match_id: int           # 1-72
    home: str               # 主队(中文)
    away: str               # 客队(中文)
    kickoff_utc: str        # UTC时间 ISO格式
    kickoff_bj: str         # 北京时间
    kickoff_local: str      # 当地时间
    venue_name: str         # 场馆名(VENUE_DB key)
    group: str              # A-L
    matchday: int           # 1/2/3
    local_hour: int = 0     # 当地时间(小时, 0-23)

    def __post_init__(self):
        if not self.local_hour:
            try:
                dt = datetime.fromisoformat(self.kickoff_local)
                self.local_hour = dt.hour
            except (ValueError, TypeError):
                self.local_hour = 15  # default afternoon


# 2026世界杯完整小组赛程 (72场: MD1×24 + MD2×24 + MD3×24)
# 时间格式: 北京时间 = UTC+8, 美西 = UTC-7, 美东 = UTC-4, 中美 = UTC-5
MATCH_SCHEDULE_V29: List[GroupMatch] = [
    # ════════════════════════════════════════════════════════════
    # MD1 · 6月12日 (周四)
    # ════════════════════════════════════════════════════════════
    GroupMatch(1, '墨西哥', '南非', '2026-06-11T19:00:00Z',
               '2026-06-12 03:00', '2026-06-11 13:00', 'Estadio Azteca', 'A', 1),
    GroupMatch(2, '韩国', '捷克', '2026-06-12T02:00:00Z',
               '2026-06-12 10:00', '2026-06-11 20:00', 'Estadio Azteca', 'A', 1),

    # ════════════════════════════════════════════════════════════
    # MD1 · 6月13日 (周五)
    # ════════════════════════════════════════════════════════════
    GroupMatch(3, '加拿大', '波黑', '2026-06-12T19:00:00Z',
               '2026-06-13 03:00', '2026-06-12 14:00', 'BMO Field', 'B', 1),
    GroupMatch(4, '美国', '巴拉圭', '2026-06-13T01:00:00Z',
               '2026-06-13 09:00', '2026-06-12 21:00', 'SoFi Stadium', 'D', 1),

    # ════════════════════════════════════════════════════════════
    # MD1 · 6月14日 (周六)
    # ════════════════════════════════════════════════════════════
    GroupMatch(5, '卡塔尔', '瑞士', '2026-06-13T19:00:00Z',
               '2026-06-14 03:00', '2026-06-13 14:00', "Levi's Stadium", 'B', 1),
    GroupMatch(6, '巴西', '摩洛哥', '2026-06-13T22:00:00Z',
               '2026-06-14 06:00', '2026-06-13 16:00', 'AT&T Stadium', 'C', 1),
    GroupMatch(7, '海地', '苏格兰', '2026-06-14T01:00:00Z',
               '2026-06-14 09:00', '2026-06-13 21:00', 'NRG Stadium', 'C', 1),
    GroupMatch(8, '澳大利亚', '土耳其', '2026-06-14T04:00:00Z',
               '2026-06-14 12:00', '2026-06-13 22:00', 'MetLife Stadium', 'D', 1),

    # ════════════════════════════════════════════════════════════
    # MD1 · 6月15日 (周日)
    # ════════════════════════════════════════════════════════════
    GroupMatch(9, '德国', '库拉索', '2026-06-14T17:00:00Z',
               '2026-06-15 01:00', '2026-06-14 13:00', 'MetLife Stadium', 'E', 1),
    GroupMatch(10, '荷兰', '日本', '2026-06-14T20:00:00Z',
               '2026-06-15 04:00', '2026-06-14 16:00', 'Arrowhead Stadium', 'F', 1),
    GroupMatch(11, '科特迪瓦', '厄瓜多尔', '2026-06-14T23:00:00Z',
               '2026-06-15 07:00', '2026-06-14 18:00', 'Lincoln Financial Field', 'E', 1),
    GroupMatch(12, '瑞典', '突尼斯', '2026-06-15T02:00:00Z',
               '2026-06-15 10:00', '2026-06-14 21:00', 'NRG Stadium', 'F', 1),

    # ════════════════════════════════════════════════════════════
    # MD1 · 6月16日 (周一)
    # ════════════════════════════════════════════════════════════
    GroupMatch(13, '西班牙', '佛得角', '2026-06-15T16:00:00Z',
               '2026-06-16 00:00', '2026-06-15 12:00', 'Hard Rock Stadium', 'H', 1),
    GroupMatch(14, '比利时', '埃及', '2026-06-15T19:00:00Z',
               '2026-06-16 03:00', '2026-06-15 15:00', 'Mercedes-Benz Stadium', 'G', 1),
    GroupMatch(15, '沙特阿拉伯', '乌拉圭', '2026-06-15T22:00:00Z',
               '2026-06-16 06:00', '2026-06-15 17:00', 'Lumen Field', 'H', 1),
    GroupMatch(16, '伊朗', '新西兰', '2026-06-16T01:00:00Z',
               '2026-06-16 09:00', '2026-06-15 21:00', 'BC Place', 'G', 1),

    # ════════════════════════════════════════════════════════════
    # MD1 · 6月17日 (周二)
    # ════════════════════════════════════════════════════════════
    GroupMatch(17, '法国', '塞内加尔', '2026-06-16T19:00:00Z',
               '2026-06-17 03:00', '2026-06-16 14:00', 'NRG Stadium', 'I', 1),
    GroupMatch(18, '伊拉克', '挪威', '2026-06-16T22:00:00Z',
               '2026-06-17 06:00', '2026-06-16 16:00', 'Arrowhead Stadium', 'I', 1),
    GroupMatch(19, '阿根廷', '阿尔及利亚', '2026-06-17T01:00:00Z',
               '2026-06-17 09:00', '2026-06-16 21:00', 'Hard Rock Stadium', 'J', 1),
    GroupMatch(20, '奥地利', '约旦', '2026-06-17T04:00:00Z',
               '2026-06-17 12:00', '2026-06-16 23:00', 'Estadio Akron', 'J', 1),

    # ════════════════════════════════════════════════════════════
    # MD1 · 6月18日 (周三) ⚡ K+L组首轮
    # ════════════════════════════════════════════════════════════
    GroupMatch(21, '葡萄牙', '刚果(金)', '2026-06-17T17:00:00Z',
               '2026-06-18 01:00', '2026-06-17 12:00', 'Gillette Stadium', 'K', 1),
    GroupMatch(22, '英格兰', '克罗地亚', '2026-06-17T20:00:00Z',
               '2026-06-18 04:00', '2026-06-17 15:00', 'MetLife Stadium', 'L', 1),
    GroupMatch(23, '加纳', '巴拿马', '2026-06-17T23:00:00Z',
               '2026-06-18 07:00', '2026-06-17 18:00', 'Estadio Azteca', 'L', 1),
    GroupMatch(24, '乌兹别克斯坦', '哥伦比亚', '2026-06-18T02:00:00Z',
               '2026-06-18 10:00', '2026-06-17 21:00', 'SoFi Stadium', 'K', 1),

    # ════════════════════════════════════════════════════════════
    # MD2 · 6月19日 (周四) · A+B组
    # ════════════════════════════════════════════════════════════
    GroupMatch(25, '捷克', '南非', '2026-06-18T16:00:00Z',
               '2026-06-19 00:00', '2026-06-18 11:00', 'Estadio BBVA', 'A', 2),
    GroupMatch(26, '瑞士', '波黑', '2026-06-18T19:00:00Z',
               '2026-06-19 03:00', '2026-06-18 14:00', 'Lumen Field', 'B', 2),
    GroupMatch(27, '加拿大', '卡塔尔', '2026-06-18T22:00:00Z',
               '2026-06-19 06:00', '2026-06-18 17:00', 'BC Place', 'B', 2),
    GroupMatch(28, '墨西哥', '韩国', '2026-06-19T01:00:00Z',
               '2026-06-19 09:00', '2026-06-18 19:00', 'Estadio Azteca', 'A', 2),

    # ════════════════════════════════════════════════════════════
    # MD2 · 6月20日 (周五) · C+D组
    # ════════════════════════════════════════════════════════════
    GroupMatch(29, '美国', '澳大利亚', '2026-06-19T19:00:00Z',
               '2026-06-20 03:00', '2026-06-19 15:00', 'SoFi Stadium', 'D', 2),
    GroupMatch(30, '苏格兰', '摩洛哥', '2026-06-19T22:00:00Z',
               '2026-06-20 06:00', '2026-06-19 18:00', 'AT&T Stadium', 'C', 2),
    GroupMatch(31, '巴西', '海地', '2026-06-20T00:30:00Z',
               '2026-06-20 08:30', '2026-06-19 20:30', 'Hard Rock Stadium', 'C', 2),
    GroupMatch(32, '土耳其', '巴拉圭', '2026-06-20T03:00:00Z',
               '2026-06-20 11:00', '2026-06-19 23:00', 'Mercedes-Benz Stadium', 'D', 2),

    # ════════════════════════════════════════════════════════════
    # MD2 · 6月21日 (周六) · E+F组
    # ════════════════════════════════════════════════════════════
    GroupMatch(33, '荷兰', '瑞典', '2026-06-20T17:00:00Z',
               '2026-06-21 01:00', '2026-06-20 13:00', 'Arrowhead Stadium', 'F', 2),
    GroupMatch(34, '德国', '科特迪瓦', '2026-06-20T20:00:00Z',
               '2026-06-21 04:00', '2026-06-20 16:00', 'MetLife Stadium', 'E', 2),
    GroupMatch(35, '厄瓜多尔', '库拉索', '2026-06-21T00:00:00Z',
               '2026-06-21 08:00', '2026-06-20 20:00', 'Lincoln Financial Field', 'E', 2),
    GroupMatch(36, '突尼斯', '日本', '2026-06-21T04:00:00Z',
               '2026-06-21 12:00', '2026-06-20 23:00', 'NRG Stadium', 'F', 2),

    # ════════════════════════════════════════════════════════════
    # MD2 · 6月22日 (周日) · G+H组
    # ════════════════════════════════════════════════════════════
    GroupMatch(37, '西班牙', '沙特阿拉伯', '2026-06-21T16:00:00Z',
               '2026-06-22 00:00', '2026-06-21 12:00', 'Hard Rock Stadium', 'H', 2),
    GroupMatch(38, '比利时', '伊朗', '2026-06-21T19:00:00Z',
               '2026-06-22 03:00', '2026-06-21 15:00', "Levi's Stadium", 'G', 2),
    GroupMatch(39, '乌拉圭', '佛得角', '2026-06-21T22:00:00Z',
               '2026-06-22 06:00', '2026-06-21 18:00', 'Lumen Field', 'H', 2),
    GroupMatch(40, '新西兰', '埃及', '2026-06-22T01:00:00Z',
               '2026-06-22 09:00', '2026-06-21 21:00', 'Gillette Stadium', 'G', 2),

    # ════════════════════════════════════════════════════════════
    # MD2 · 6月23日 (周一) · I+J组
    # ════════════════════════════════════════════════════════════
    GroupMatch(41, '阿根廷', '奥地利', '2026-06-22T17:00:00Z',
               '2026-06-23 01:00', '2026-06-22 13:00', 'Estadio Akron', 'J', 2),
    GroupMatch(42, '法国', '伊拉克', '2026-06-22T21:00:00Z',
               '2026-06-23 05:00', '2026-06-22 17:00', 'AT&T Stadium', 'I', 2),
    GroupMatch(43, '挪威', '塞内加尔', '2026-06-23T00:00:00Z',
               '2026-06-23 08:00', '2026-06-22 20:00', 'BC Place', 'I', 2),
    GroupMatch(44, '约旦', '阿尔及利亚', '2026-06-23T03:00:00Z',
               '2026-06-23 11:00', '2026-06-22 23:00', 'MetLife Stadium', 'J', 2),

    # ════════════════════════════════════════════════════════════
    # MD2 · 6月24日 (周二) · K+L组
    # ════════════════════════════════════════════════════════════
    GroupMatch(45, '葡萄牙', '乌兹别克斯坦', '2026-06-23T17:00:00Z',
               '2026-06-24 01:00', '2026-06-23 13:00', 'Gillette Stadium', 'K', 2),
    GroupMatch(46, '英格兰', '加纳', '2026-06-23T20:00:00Z',
               '2026-06-24 04:00', '2026-06-23 16:00', 'Arrowhead Stadium', 'L', 2),
    GroupMatch(47, '巴拿马', '克罗地亚', '2026-06-23T23:00:00Z',
               '2026-06-24 07:00', '2026-06-23 19:00', 'NRG Stadium', 'L', 2),
    GroupMatch(48, '哥伦比亚', '刚果(金)', '2026-06-24T02:00:00Z',
               '2026-06-24 10:00', '2026-06-23 22:00', 'SoFi Stadium', 'K', 2),

    # ════════════════════════════════════════════════════════════
    # MD3 · 6月23日 (周二) · A+B组 (同组两场同时开球)
    # ════════════════════════════════════════════════════════════
    # A组: Mexico venues (UTC-6) · 16:00 local = 22:00 UTC
    GroupMatch(49, '墨西哥', '捷克', '2026-06-23T22:00:00Z',
               '2026-06-24 06:00', '2026-06-23 16:00', 'Estadio Azteca', 'A', 3),
    GroupMatch(50, '韩国', '南非', '2026-06-23T22:00:00Z',
               '2026-06-24 06:00', '2026-06-23 16:00', 'Estadio BBVA', 'A', 3),
    # B组: Eastern venues (UTC-4) · 14:00 local = 18:00 UTC
    GroupMatch(51, '加拿大', '瑞士', '2026-06-23T18:00:00Z',
               '2026-06-24 02:00', '2026-06-23 14:00', 'BMO Field', 'B', 3),
    GroupMatch(52, '波黑', '卡塔尔', '2026-06-23T18:00:00Z',
               '2026-06-24 02:00', '2026-06-23 14:00', 'Gillette Stadium', 'B', 3),

    # ════════════════════════════════════════════════════════════
    # MD3 · 6月24日 (周三) · C+D组 (同组两场同时开球)
    # ════════════════════════════════════════════════════════════
    # C组: Eastern venues (UTC-4) · 16:00 local = 20:00 UTC
    GroupMatch(53, '巴西', '苏格兰', '2026-06-24T20:00:00Z',
               '2026-06-25 04:00', '2026-06-24 16:00', 'Hard Rock Stadium', 'C', 3),
    GroupMatch(54, '海地', '摩洛哥', '2026-06-24T20:00:00Z',
               '2026-06-25 04:00', '2026-06-24 16:00', 'Mercedes-Benz Stadium', 'C', 3),
    # D组: Pacific venues (UTC-7) · 19:00 local = 02:00+1 UTC
    GroupMatch(55, '美国', '土耳其', '2026-06-25T02:00:00Z',
               '2026-06-25 10:00', '2026-06-24 19:00', 'SoFi Stadium', 'D', 3),
    GroupMatch(56, '澳大利亚', '巴拉圭', '2026-06-25T02:00:00Z',
               '2026-06-25 10:00', '2026-06-24 19:00', "Levi's Stadium", 'D', 3),

    # ════════════════════════════════════════════════════════════
    # MD3 · 6月25日 (周四) · E+F组 (同组两场同时开球)
    # ════════════════════════════════════════════════════════════
    # E组: Eastern venues (UTC-4) · 16:00 local = 20:00 UTC
    GroupMatch(57, '德国', '厄瓜多尔', '2026-06-25T20:00:00Z',
               '2026-06-26 04:00', '2026-06-25 16:00', 'MetLife Stadium', 'E', 3),
    GroupMatch(58, '科特迪瓦', '库拉索', '2026-06-25T20:00:00Z',
               '2026-06-26 04:00', '2026-06-25 16:00', 'Lincoln Financial Field', 'E', 3),
    # F组: Central venues (UTC-5) · 16:00 local = 21:00 UTC
    GroupMatch(59, '荷兰', '突尼斯', '2026-06-25T21:00:00Z',
               '2026-06-26 05:00', '2026-06-25 16:00', 'Arrowhead Stadium', 'F', 3),
    GroupMatch(60, '日本', '瑞典', '2026-06-25T21:00:00Z',
               '2026-06-26 05:00', '2026-06-25 16:00', 'NRG Stadium', 'F', 3),

    # ════════════════════════════════════════════════════════════
    # MD3 · 6月26日 (周五) · G+H组 (同组两场同时开球)
    # ════════════════════════════════════════════════════════════
    # G组: Pacific venues (UTC-7) · 19:00 local = 02:00+1 UTC
    GroupMatch(61, '比利时', '新西兰', '2026-06-27T02:00:00Z',
               '2026-06-27 10:00', '2026-06-26 19:00', 'BC Place', 'G', 3),
    GroupMatch(62, '伊朗', '埃及', '2026-06-27T02:00:00Z',
               '2026-06-27 10:00', '2026-06-26 19:00', 'Lumen Field', 'G', 3),
    # H组: Eastern venues (UTC-4) · 14:00 local = 18:00 UTC
    GroupMatch(63, '西班牙', '乌拉圭', '2026-06-26T18:00:00Z',
               '2026-06-27 02:00', '2026-06-26 14:00', 'Hard Rock Stadium', 'H', 3),
    GroupMatch(64, '佛得角', '沙特阿拉伯', '2026-06-26T18:00:00Z',
               '2026-06-27 02:00', '2026-06-26 14:00', 'Mercedes-Benz Stadium', 'H', 3),

    # ════════════════════════════════════════════════════════════
    # MD3 · 6月27日 (周六) · I+J组 (同组两场同时开球)
    # ════════════════════════════════════════════════════════════
    # I组: Central venues (UTC-5) · 16:00 local = 21:00 UTC
    GroupMatch(65, '法国', '挪威', '2026-06-27T21:00:00Z',
               '2026-06-28 05:00', '2026-06-27 16:00', 'AT&T Stadium', 'I', 3),
    GroupMatch(66, '塞内加尔', '伊拉克', '2026-06-27T21:00:00Z',
               '2026-06-28 05:00', '2026-06-27 16:00', 'Arrowhead Stadium', 'I', 3),
    # J组: Pacific venues (UTC-7) · 19:00 local = 02:00+1 UTC
    GroupMatch(67, '阿根廷', '约旦', '2026-06-28T02:00:00Z',
               '2026-06-28 10:00', '2026-06-27 19:00', 'SoFi Stadium', 'J', 3),
    GroupMatch(68, '阿尔及利亚', '奥地利', '2026-06-28T02:00:00Z',
               '2026-06-28 10:00', '2026-06-27 19:00', "Levi's Stadium", 'J', 3),

    # ════════════════════════════════════════════════════════════
    # MD3 · 6月28日 (周日) · K+L组 (同组两场同时开球)
    # ════════════════════════════════════════════════════════════
    # K组: Eastern venues (UTC-4) · 14:00 local = 18:00 UTC
    GroupMatch(69, '葡萄牙', '哥伦比亚', '2026-06-28T18:00:00Z',
               '2026-06-29 02:00', '2026-06-28 14:00', 'Gillette Stadium', 'K', 3),
    GroupMatch(70, '刚果(金)', '乌兹别克斯坦', '2026-06-28T18:00:00Z',
               '2026-06-29 02:00', '2026-06-28 14:00', 'MetLife Stadium', 'K', 3),
    # L组: Mexico venues (UTC-6) · 16:00 local = 22:00 UTC
    GroupMatch(71, '英格兰', '巴拿马', '2026-06-28T22:00:00Z',
               '2026-06-29 06:00', '2026-06-28 16:00', 'Estadio Azteca', 'L', 3),
    GroupMatch(72, '克罗地亚', '加纳', '2026-06-28T22:00:00Z',
               '2026-06-29 06:00', '2026-06-28 16:00', 'Estadio BBVA', 'L', 3),
]


# ── 中文名规范化 ──

# 中文到英文映射 (用于跨模块查找)
CN_TO_EN: Dict[str, str] = {
    '墨西哥': 'Mexico', '南非': 'South Africa', '韩国': 'South Korea', '捷克': 'Czech Republic',
    '加拿大': 'Canada', '波黑': 'Bosnia', '卡塔尔': 'Qatar', '瑞士': 'Switzerland',
    '巴西': 'Brazil', '摩洛哥': 'Morocco', '海地': 'Haiti', '苏格兰': 'Scotland',
    '美国': 'USA', '巴拉圭': 'Paraguay', '澳大利亚': 'Australia', '土耳其': 'Turkey',
    '德国': 'Germany', '库拉索': 'Curacao', '科特迪瓦': "Cote d'Ivoire", '厄瓜多尔': 'Ecuador',
    '荷兰': 'Netherlands', '日本': 'Japan', '瑞典': 'Sweden', '突尼斯': 'Tunisia',
    '比利时': 'Belgium', '埃及': 'Egypt', '伊朗': 'Iran', '新西兰': 'New Zealand',
    '西班牙': 'Spain', '佛得角': 'Cape Verde', '沙特阿拉伯': 'Saudi Arabia', '乌拉圭': 'Uruguay',
    '法国': 'France', '塞内加尔': 'Senegal', '伊拉克': 'Iraq', '挪威': 'Norway',
    '阿根廷': 'Argentina', '阿尔及利亚': 'Algeria', '奥地利': 'Austria', '约旦': 'Jordan',
    '葡萄牙': 'Portugal', '民主刚果': 'DR Congo', '刚果民主共和国': 'DR Congo', '刚果(金)': 'DR Congo',
    '乌兹别克斯坦': 'Uzbekistan', '哥伦比亚': 'Colombia',
    '英格兰': 'England', '克罗地亚': 'Croatia', '加纳': 'Ghana', '巴拿马': 'Panama',
}

EN_TO_CN: Dict[str, str] = {v: k for k, v in CN_TO_EN.items()}


# ── 球队名别名规范化 ──
TEAM_NAME_ALIASES: Dict[str, str] = {
    '刚果民主共和国': '民主刚果',
    '刚果(金)': '民主刚果',
    '民主刚果': '民主刚果',
    'DR Congo': '民主刚果',
    '刚果金': '民主刚果',
    '沙特': '沙特阿拉伯',
    '沙特阿拉伯': '沙特阿拉伯',
    'Saudi Arabia': '沙特阿拉伯',
}


def normalize_team_name(name: str) -> str:
    """统一球队名: 别名→标准中文名"""
    name = name.strip()
    # 先查别名表
    if name in TEAM_NAME_ALIASES:
        return TEAM_NAME_ALIASES[name]
    # 英文→中文
    if name in EN_TO_CN:
        return EN_TO_CN[name]
    return name


# ── 核心查询函数 ──

def get_venue(venue_name: str) -> Optional[dict]:
    """根据场馆名查询"""
    return VENUE_DB.get(venue_name)


def get_match(match_name: str = None, home: str = None, away: str = None,
              match_id: int = None) -> Optional[GroupMatch]:
    """查比赛: 支持'法国VS塞内加尔'格式或分别传home/away"""
    if match_id:
        for m in MATCH_SCHEDULE_V29:
            if m.match_id == match_id:
                return m
        return None

    if match_name:
        # 解析 "主队VS客队" 格式
        parts = match_name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
        if len(parts) == 2:
            home = normalize_team_name(parts[0].strip())
            away = normalize_team_name(parts[1].strip())

    if home and away:
        home_n = normalize_team_name(home)
        away_n = normalize_team_name(away)
        for m in MATCH_SCHEDULE_V29:
            if normalize_team_name(m.home) == home_n and normalize_team_name(m.away) == away_n:
                return m
        # 反向匹配(主客互换)
        for m in MATCH_SCHEDULE_V29:
            if normalize_team_name(m.home) == away_n and normalize_team_name(m.away) == home_n:
                return m

    return None


def get_team_group(team_name: str) -> Optional[str]:
    """查询球队所在小组 (自动归一化名称)"""
    return TEAM_GROUPS.get(normalize_team_name(team_name))


def get_group_matches(group: str) -> List[GroupMatch]:
    """获取某小组全部比赛"""
    return [m for m in MATCH_SCHEDULE_V29 if m.group == group]


def get_matches_by_matchday(matchday: int) -> List[GroupMatch]:
    """获取某个比赛日的全部比赛"""
    return [m for m in MATCH_SCHEDULE_V29 if m.matchday == matchday]


def get_all_matches() -> List[GroupMatch]:
    """获取全部72场小组赛"""
    return MATCH_SCHEDULE_V29


def get_venue_for_match(match_name: str = None, home: str = None, away: str = None) -> Optional[dict]:
    """根据比赛获取场馆信息"""
    m = get_match(match_name=match_name, home=home, away=away)
    if m:
        return VENUE_DB.get(m.venue_name)
    return None


def get_upcoming_matches(hours_ahead: int = 24) -> List[GroupMatch]:
    """获取未来N小时内开球的比赛"""
    now = datetime.utcnow()
    upcoming = []
    for m in MATCH_SCHEDULE_V29:
        try:
            dt = datetime.fromisoformat(m.kickoff_utc)
            delta_h = (dt - now).total_seconds() / 3600
            if 0 <= delta_h <= hours_ahead:
                upcoming.append(m)
        except (ValueError, TypeError):
            continue
    return sorted(upcoming, key=lambda x: x.kickoff_utc)


# ── 独立测试 ──
if __name__ == '__main__':
    print("=== 2026世界杯场馆数据库 ===\n")
    for vname, v in VENUE_DB.items():
        indoor_mark = '🏠室内' if v['indoor'] else '🌳室外'
        print(f"  {v['name']:30s} | {v['city']:25s} | 海拔{v['altitude_m']:>4d}m | {v['grass_type']:10s} | {indoor_mark}")

    print(f"\n=== 32队分组 ({len(TEAM_GROUPS)}队) ===\n")
    from collections import defaultdict
    groups = defaultdict(list)
    for team, grp in TEAM_GROUPS.items():
        groups[grp].append(team)
    for grp in sorted(groups.keys()):
        print(f"  {grp}组: {', '.join(groups[grp])}")

    print(f"\n=== 赛程 ({len(MATCH_SCHEDULE_V29)}场) ===\n")
    for m in MATCH_SCHEDULE_V29[:10]:
        print(f"  #{m.match_id:2d} {m.home}VS{m.away} | {m.group}组 MD{m.matchday} | {m.kickoff_bj} BJT | {m.venue_name}")

    print(f"\n=== 当前预测场次查询 ===\n")
    for mn in ['法国VS塞内加尔', '伊拉克VS挪威', '阿根廷VS阿尔及利亚', '奥地利VS约旦']:
        gm = get_match(match_name=mn)
        v = get_venue_for_match(match_name=mn)
        if gm:
            print(f"  {mn}: {gm.group}组 MD{gm.matchday} | {gm.kickoff_bj}BJT | {v['city'] if v else '?'} | {v['name'] if v else '?'} | 当地{gm.local_hour}:00 | {'室内' if v and v['indoor'] else '室外'} | 海拔{v['altitude_m'] if v else '?'}m")

    print(f"\n=== 未来24h比赛 ===\n")
    upcoming = get_upcoming_matches(24)
    for m in upcoming:
        print(f"  {m.home}VS{m.away} | {m.kickoff_bj} BJT")

"""
V2.10 近期状态分析
评估: 近5场战绩·对手实力加权·主力出战率·含金量打分
依赖: match_context.py (球队名映射)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import date as date_type, datetime
import json
from pathlib import Path

from config import CONF


@dataclass
class RecentMatch:
    """单场近期比赛"""
    opponent: str           # 对手(中文)
    result: str             # 'W'|'D'|'L'
    score: str              # '2-0'
    opponent_rank: int      # 对手FIFA排名
    home_away: str          # 'home'|'away'|'neutral'
    is_official: bool       # 正式比赛 vs 友谊赛
    key_players_played: int # 主力出战数 (0-11)
    date: str = ""


@dataclass
class RecentForm:
    """近期状态分析结果"""
    team: str
    matches: List[dict] = field(default_factory=list)
    form_string: str = ""           # 'WWDLW'
    points_last5: int = 0           # 近5场积分 (15分制)
    avg_goals_scored: float = 0.0
    avg_goals_conceded: float = 0.0
    opponent_quality_avg: float = 50  # 对手平均排名
    quality_weighted_score: float = 0.0  # 对手实力加权分 (0-10)
    key_player_participation: float = 1.0  # 主力出战率
    form_score: float = 5.0          # 综合状态分 (0-10)
    decay_applied: bool = False      # 是否应用了时间衰减加权
    opponent_quality_adjustment: float = 1.0  # 🆕 V3.3: 对手质量调整系数
    notes: List[str] = field(default_factory=list)


# ── 32队近5场战绩 (2026年6月至今) ──

# Auto-generated from 近期状态.txt
# 46 teams, updated 2026-06-21
RECENT_RESULTS = {
    "乌兹别克斯坦": [
        {"opponent": "荷兰", "result": "L", "score": "1-2", "opponent_rank": 8, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-09"},
        {"opponent": "加拿大", "result": "L", "score": "0-2", "opponent_rank": 30, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-02"},
        {"opponent": "委内瑞拉", "result": "D", "score": "0-0", "opponent_rank": 64, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-30"},
        {"opponent": "加蓬", "result": "W", "score": "3-1", "opponent_rank": 76, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
        {"opponent": "伊朗", "result": "D", "score": "0-0", "opponent_rank": 20, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-11-19"},
    ],
    "乌拉圭": [
        {"opponent": "阿尔及利亚", "result": "D", "score": "0-0", "opponent_rank": 28, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "英格兰", "result": "D", "score": "1-1", "opponent_rank": 4, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
        {"opponent": "美国", "result": "L", "score": "1-5", "opponent_rank": 31, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-11-19"},
        {"opponent": "墨西哥", "result": "D", "score": "0-0", "opponent_rank": 14, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-11-16"},
    ],
    "伊拉克": [
        {"opponent": "挪威", "result": "L", "score": "1-4", "opponent_rank": 38, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-17"},
        {"opponent": "委内瑞拉", "result": "L", "score": "0-2", "opponent_rank": 64, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "西班牙", "result": "D", "score": "1-1", "opponent_rank": 2, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "安道尔", "result": "W", "score": "1-0", "opponent_rank": 200, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-05-30"},
        {"opponent": "玻利维亚", "result": "W", "score": "2-1", "opponent_rank": 87, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
    ],
    "伊朗": [
        {"opponent": "新西兰", "result": "D", "score": "2-2", "opponent_rank": 80, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-16"},
        {"opponent": "马里", "result": "W", "score": "2-0", "opponent_rank": 70, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-05"},
        {"opponent": "冈比亚", "result": "W", "score": "3-1", "opponent_rank": 89, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-29"},
        {"opponent": "哥斯达黎加", "result": "W", "score": "5-0", "opponent_rank": 81, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "尼日利亚", "result": "L", "score": "1-2", "opponent_rank": 68, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "佛得角": [
        {"opponent": "西班牙", "result": "D", "score": "0-0", "opponent_rank": 2, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "百慕大群岛", "result": "W", "score": "3-0", "opponent_rank": 195, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "塞尔维亚", "result": "W", "score": "3-0", "opponent_rank": 42, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "芬兰", "result": "D", "score": "1-1", "opponent_rank": 79, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-30"},
        {"opponent": "智利", "result": "L", "score": "2-4", "opponent_rank": 66, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "克罗地亚": [
        {"opponent": "斯洛文尼亚", "result": "W", "score": "2-1", "opponent_rank": 53, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "比利时", "result": "L", "score": "0-2", "opponent_rank": 9, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-02"},
        {"opponent": "巴西", "result": "L", "score": "1-3", "opponent_rank": 5, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "哥伦比亚", "result": "W", "score": "2-1", "opponent_rank": 13, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-26"},
        {"opponent": "黑山", "result": "W", "score": "3-2", "opponent_rank": 94, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-11-17"},
    ],
    "刚果(金)": [
        {"opponent": "智利", "result": "L", "score": "1-2", "opponent_rank": 66, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-09"},
        {"opponent": "丹麦", "result": "D", "score": "0-0", "opponent_rank": 34, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-03"},
        {"opponent": "牙买加", "result": "W", "score": "1-0", "opponent_rank": 88, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "百慕大", "result": "W", "score": "2-0", "opponent_rank": 195, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-25"},
        {"opponent": "阿尔及利亚", "result": "L", "score": "0-1", "opponent_rank": 28, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-01-06"},
    ],
    "加拿大": [
        {"opponent": "波黑", "result": "D", "score": "1-1", "opponent_rank": 47, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-12"},
        {"opponent": "爱尔兰", "result": "D", "score": "1-1", "opponent_rank": 49, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-05"},
        {"opponent": "乌兹别克斯坦", "result": "W", "score": "2-0", "opponent_rank": 50, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-01"},
        {"opponent": "冰岛", "result": "D", "score": "2-2", "opponent_rank": 78, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-15"},
        {"opponent": "突尼斯", "result": "D", "score": "0-0", "opponent_rank": 45, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-15"},
    ],
    "加纳": [
        {"opponent": "威尔士", "result": "D", "score": "1-1", "opponent_rank": 51, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-03"},
        {"opponent": "墨西哥", "result": "L", "score": "0-2", "opponent_rank": 14, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-05-23"},
        {"opponent": "德国", "result": "L", "score": "1-2", "opponent_rank": 7, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "奥地利", "result": "L", "score": "1-5", "opponent_rank": 32, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-28"},
        {"opponent": "南非", "result": "L", "score": "0-1", "opponent_rank": 60, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-12-16"},
    ],
    "南非": [
        {"opponent": "墨西哥", "result": "W", "score": "2-0", "opponent_rank": 14, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-11"},
        {"opponent": "尼加拉瓜", "result": "D", "score": "0-0", "opponent_rank": 97, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-05-29"},
        {"opponent": "巴拿马", "result": "W", "score": "2-1", "opponent_rank": 48, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "巴拿马", "result": "D", "score": "1-1", "opponent_rank": 48, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
        {"opponent": "喀麦隆", "result": "L", "score": "1-2", "opponent_rank": 69, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-01-04"},
    ],
    "卡塔尔": [
        {"opponent": "萨尔瓦多", "result": "D", "score": "0-0", "opponent_rank": 84, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "阿根廷", "result": "D", "score": "0-0", "opponent_rank": 3, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "塞尔维亚", "result": "D", "score": "0-0", "opponent_rank": 42, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-26"},
    ],
    "厄瓜多尔": [
        {"opponent": "科特迪瓦", "result": "W", "score": "1-0", "opponent_rank": 58, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "危地马拉", "result": "W", "score": "3-0", "opponent_rank": 85, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-08"},
        {"opponent": "沙特阿拉伯", "result": "W", "score": "2-1", "opponent_rank": 61, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "荷兰", "result": "D", "score": "1-1", "opponent_rank": 8, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "摩洛哥", "result": "D", "score": "1-1", "opponent_rank": 26, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "哥伦比亚": [
        {"opponent": "约旦", "result": "W", "score": "2-0", "opponent_rank": 55, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "哥斯达黎加", "result": "W", "score": "3-1", "opponent_rank": 81, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-01"},
        {"opponent": "法国", "result": "L", "score": "1-3", "opponent_rank": 1, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-29"},
        {"opponent": "克罗地亚", "result": "L", "score": "1-2", "opponent_rank": 11, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-26"},
        {"opponent": "澳大利亚", "result": "W", "score": "3-0", "opponent_rank": 36, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-11-19"},
    ],
    "土耳其": [
        {"opponent": "澳大利亚", "result": "W", "score": "2-0", "opponent_rank": 36, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-14"},
        {"opponent": "委内瑞拉", "result": "W", "score": "2-1", "opponent_rank": 64, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "北马其顿", "result": "W", "score": "4-0", "opponent_rank": 93, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-02"},
        {"opponent": "科索沃", "result": "W", "score": "1-0", "opponent_rank": 90, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "罗马尼亚", "result": "W", "score": "1-0", "opponent_rank": 44, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "埃及": [
        {"opponent": "巴西", "result": "L", "score": "1-2", "opponent_rank": 5, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "俄罗斯", "result": "W", "score": "1-0", "opponent_rank": 19, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-29"},
        {"opponent": "西班牙", "result": "D", "score": "0-0", "opponent_rank": 2, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "沙特阿拉伯", "result": "W", "score": "4-0", "opponent_rank": 61, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "塞内加尔": [
        {"opponent": "法国", "result": "W", "score": "3-1", "opponent_rank": 1, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-17"},
        {"opponent": "沙特阿拉伯", "result": "D", "score": "0-0", "opponent_rank": 61, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-09"},
        {"opponent": "美国", "result": "L", "score": "2-3", "opponent_rank": 31, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "冈比亚", "result": "W", "score": "3-1", "opponent_rank": 89, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "秘鲁", "result": "W", "score": "2-0", "opponent_rank": 65, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "墨西哥": [
        {"opponent": "南非", "result": "W", "score": "2-0", "opponent_rank": 60, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-11"},
        {"opponent": "塞尔维亚", "result": "W", "score": "5-1", "opponent_rank": 42, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-04"},
        {"opponent": "澳大利亚", "result": "W", "score": "1-0", "opponent_rank": 36, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-30"},
        {"opponent": "加纳", "result": "W", "score": "2-0", "opponent_rank": 73, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-22"},
        {"opponent": "比利时", "result": "D", "score": "1-1", "opponent_rank": 9, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
    ],
    "奥地利": [
        {"opponent": "约旦", "result": "W", "score": "3-1", "opponent_rank": 55, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-17"},
        {"opponent": "突尼斯", "result": "W", "score": "1-0", "opponent_rank": 45, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-02"},
        {"opponent": "韩国", "result": "W", "score": "1-0", "opponent_rank": 25, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "加纳", "result": "W", "score": "5-1", "opponent_rank": 73, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "巴拉圭": [
        {"opponent": "美国", "result": "W", "score": "4-1", "opponent_rank": 31, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-13"},
        {"opponent": "尼加拉瓜", "result": "W", "score": "4-0", "opponent_rank": 97, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-06"},
        {"opponent": "摩洛哥", "result": "W", "score": "2-1", "opponent_rank": 26, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "希腊", "result": "W", "score": "1-0", "opponent_rank": 43, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
        {"opponent": "墨西哥", "result": "W", "score": "2-1", "opponent_rank": 14, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-15"},
    ],
    "巴拿马": [
        {"opponent": "波黑", "result": "D", "score": "1-1", "opponent_rank": 47, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "多米尼加共和国", "result": "W", "score": "4-2", "opponent_rank": 96, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-04"},
        {"opponent": "巴西", "result": "W", "score": "6-2", "opponent_rank": 5, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-01"},
        {"opponent": "南非", "result": "W", "score": "2-1", "opponent_rank": 60, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "南非", "result": "D", "score": "1-1", "opponent_rank": 60, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "巴西": [
        {"opponent": "摩洛哥", "result": "D", "score": "1-1", "opponent_rank": 26, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-13"},
        {"opponent": "埃及", "result": "W", "score": "2-1", "opponent_rank": 29, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "巴拿马", "result": "W", "score": "6-2", "opponent_rank": 48, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-31"},
    ],
    "库拉索": [
        {"opponent": "德国", "result": "L", "score": "1-7", "opponent_rank": 7, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "阿鲁巴", "result": "W", "score": "4-0", "opponent_rank": 200, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "苏格兰", "result": "L", "score": "1-4", "opponent_rank": 37, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-05-30"},
        {"opponent": "澳大利亚", "result": "L", "score": "1-5", "opponent_rank": 36, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "中国", "result": "L", "score": "0-2", "opponent_rank": 63, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "德国": [
        {"opponent": "库拉索", "result": "W", "score": "7-1", "opponent_rank": 82, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "美国", "result": "W", "score": "2-1", "opponent_rank": 31, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "芬兰", "result": "W", "score": "4-0", "opponent_rank": 79, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-01"},
        {"opponent": "加纳", "result": "W", "score": "2-1", "opponent_rank": 73, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "瑞士", "result": "W", "score": "4-3", "opponent_rank": 35, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "挪威": [
        {"opponent": "摩洛哥", "result": "D", "score": "1-1", "opponent_rank": 26, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "瑞典", "result": "W", "score": "3-1", "opponent_rank": 27, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-01"},
        {"opponent": "瑞士", "result": "D", "score": "0-0", "opponent_rank": 35, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "荷兰", "result": "L", "score": "1-2", "opponent_rank": 8, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "捷克": [
        {"opponent": "韩国", "result": "W", "score": "2-1", "opponent_rank": 25, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-12"},
        {"opponent": "危地马拉", "result": "W", "score": "3-1", "opponent_rank": 85, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-05"},
        {"opponent": "科索沃", "result": "W", "score": "2-1", "opponent_rank": 90, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "丹麦", "result": "D", "score": "1-1", "opponent_rank": 34, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "爱尔兰", "result": "D", "score": "2-2", "opponent_rank": 49, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "摩洛哥": [
        {"opponent": "巴西", "result": "D", "score": "1-1", "opponent_rank": 5, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-13"},
        {"opponent": "挪威", "result": "D", "score": "1-1", "opponent_rank": 38, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "马达加斯加", "result": "W", "score": "4-0", "opponent_rank": 98, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-02"},
        {"opponent": "巴拉圭", "result": "W", "score": "2-1", "opponent_rank": 39, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "厄瓜多尔", "result": "D", "score": "1-1", "opponent_rank": 23, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "新西兰": [
        {"opponent": "伊朗", "result": "D", "score": "2-2", "opponent_rank": 20, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-16"},
        {"opponent": "英格兰", "result": "W", "score": "1-0", "opponent_rank": 4, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "海地", "result": "W", "score": "4-0", "opponent_rank": 71, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-03"},
        {"opponent": "智利", "result": "W", "score": "4-1", "opponent_rank": 66, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-30"},
        {"opponent": "芬兰", "result": "L", "score": "0-2", "opponent_rank": 79, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "日本": [
        {"opponent": "荷兰", "result": "D", "score": "2-2", "opponent_rank": 8, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "日本U19", "result": "W", "score": "2-1", "opponent_rank": 200, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "冰岛", "result": "W", "score": "1-0", "opponent_rank": 78, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "英格兰", "result": "W", "score": "1-0", "opponent_rank": 4, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "苏格兰", "result": "W", "score": "1-0", "opponent_rank": 37, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-29"},
    ],
    "比利时": [
        {"opponent": "埃及", "result": "D", "score": "1-1", "opponent_rank": 29, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-16"},
        {"opponent": "突尼斯", "result": "W", "score": "5-0", "opponent_rank": 45, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-06"},
        {"opponent": "克罗地亚", "result": "W", "score": "2-0", "opponent_rank": 11, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-03"},
        {"opponent": "墨西哥", "result": "D", "score": "1-1", "opponent_rank": 14, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "美国", "result": "W", "score": "5-2", "opponent_rank": 31, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-29"},
    ],
    "沙特阿拉伯": [
        {"opponent": "乌拉圭", "result": "D", "score": "1-1", "opponent_rank": 16, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "塞内加尔", "result": "D", "score": "0-0", "opponent_rank": 15, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-10"},
        {"opponent": "波多黎各", "result": "W", "score": "3-0", "opponent_rank": 200, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-06"},
        {"opponent": "厄瓜多尔", "result": "L", "score": "1-2", "opponent_rank": 23, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "塞尔维亚", "result": "L", "score": "1-2", "opponent_rank": 42, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
    ],
    "波黑": [
        {"opponent": "加拿大", "result": "D", "score": "1-1", "opponent_rank": 30, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-13"},
        {"opponent": "巴拿马", "result": "D", "score": "1-1", "opponent_rank": 48, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "北马其顿", "result": "D", "score": "0-0", "opponent_rank": 93, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-30"},
        {"opponent": "意大利", "result": "D", "score": "1-1", "opponent_rank": 10, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "威尔士", "result": "D", "score": "1-1", "opponent_rank": 51, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "海地": [
        {"opponent": "苏格兰", "result": "L", "score": "0-1", "opponent_rank": 37, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-14"},
        {"opponent": "秘鲁", "result": "L", "score": "1-2", "opponent_rank": 65, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-06"},
        {"opponent": "新西兰", "result": "W", "score": "4-0", "opponent_rank": 80, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-03"},
        {"opponent": "冰岛", "result": "D", "score": "1-1", "opponent_rank": 78, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "突尼斯", "result": "L", "score": "0-1", "opponent_rank": 45, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "澳大利亚": [
        {"opponent": "瑞士", "result": "D", "score": "1-1", "opponent_rank": 35, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "库拉索", "result": "W", "score": "5-1", "opponent_rank": 82, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "喀麦隆", "result": "W", "score": "1-0", "opponent_rank": 69, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "瑞典": [
        {"opponent": "突尼斯", "result": "W", "score": "5-1", "opponent_rank": 45, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "希腊", "result": "D", "score": "2-2", "opponent_rank": 43, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-05"},
        {"opponent": "挪威", "result": "L", "score": "1-3", "opponent_rank": 38, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-02"},
        {"opponent": "波兰", "result": "W", "score": "3-2", "opponent_rank": 41, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "乌克兰", "result": "W", "score": "3-1", "opponent_rank": 33, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-27"},
    ],
    "瑞士": [
        {"opponent": "卡塔尔", "result": "D", "score": "1-1", "opponent_rank": 56, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-13"},
        {"opponent": "澳大利亚", "result": "D", "score": "1-1", "opponent_rank": 36, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "挪威", "result": "D", "score": "0-0", "opponent_rank": 38, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "德国", "result": "L", "score": "3-4", "opponent_rank": 7, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-27"},
        {"opponent": "科索沃", "result": "D", "score": "1-1", "opponent_rank": 90, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-11-18"},
    ],
    "科特迪瓦": [
        {"opponent": "厄瓜多尔", "result": "W", "score": "1-0", "opponent_rank": 23, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "费城联合B队", "result": "W", "score": "2-0", "opponent_rank": 200, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-09"},
        {"opponent": "法国", "result": "W", "score": "2-1", "opponent_rank": 1, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-05"},
        {"opponent": "苏格兰", "result": "W", "score": "1-0", "opponent_rank": 37, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "韩国", "result": "W", "score": "4-0", "opponent_rank": 25, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "突尼斯": [
        {"opponent": "瑞典", "result": "L", "score": "1-5", "opponent_rank": 27, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "比利时", "result": "L", "score": "0-5", "opponent_rank": 9, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-06"},
        {"opponent": "奥地利", "result": "L", "score": "0-1", "opponent_rank": 32, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-02"},
        {"opponent": "加拿大", "result": "D", "score": "0-0", "opponent_rank": 30, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "海地", "result": "W", "score": "1-0", "opponent_rank": 71, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-29"},
    ],
    "约旦": [
        {"opponent": "奥地利", "result": "W", "score": "3-1", "opponent_rank": 32, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-17"},
        {"opponent": "哥伦比亚", "result": "W", "score": "2-0", "opponent_rank": 13, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "瑞士", "result": "W", "score": "4-1", "opponent_rank": 35, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "尼日利亚", "result": "D", "score": "2-2", "opponent_rank": 68, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "哥斯达黎加", "result": "D", "score": "2-2", "opponent_rank": 81, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "苏格兰": [
        {"opponent": "海地", "result": "W", "score": "1-0", "opponent_rank": 71, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-14"},
        {"opponent": "玻利维亚", "result": "W", "score": "4-0", "opponent_rank": 87, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-06"},
        {"opponent": "库拉索", "result": "W", "score": "4-1", "opponent_rank": 82, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-30"},
        {"opponent": "科特迪瓦", "result": "L", "score": "0-1", "opponent_rank": 58, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "日本", "result": "L", "score": "0-1", "opponent_rank": 24, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "英格兰": [
        {"opponent": "哥斯达黎加", "result": "W", "score": "3-0", "opponent_rank": 81, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-11"},
        {"opponent": "新西兰", "result": "W", "score": "1-0", "opponent_rank": 80, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "日本", "result": "L", "score": "0-1", "opponent_rank": 24, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "乌拉圭", "result": "D", "score": "1-1", "opponent_rank": 16, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-28"},
        {"opponent": "阿尔巴尼亚", "result": "W", "score": "2-0", "opponent_rank": 92, "home_away": "away", "is_official": True, "key_players": 11, "date": "2025-11-17"},
    ],
    "荷兰": [
        {"opponent": "日本", "result": "D", "score": "2-2", "opponent_rank": 24, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "乌兹别克斯坦", "result": "W", "score": "2-1", "opponent_rank": 50, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-09"},
        {"opponent": "阿尔及利亚", "result": "L", "score": "0-1", "opponent_rank": 28, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-04"},
        {"opponent": "厄瓜多尔", "result": "D", "score": "1-1", "opponent_rank": 23, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "挪威", "result": "W", "score": "2-1", "opponent_rank": 38, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "葡萄牙": [
        {"opponent": "尼日利亚", "result": "W", "score": "2-1", "opponent_rank": 68, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-11"},
        {"opponent": "智利", "result": "W", "score": "2-1", "opponent_rank": 66, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "美国", "result": "W", "score": "2-0", "opponent_rank": 31, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "墨西哥", "result": "D", "score": "0-0", "opponent_rank": 14, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-03-29"},
        {"opponent": "亚美尼亚", "result": "W", "score": "9-1", "opponent_rank": 91, "home_away": "home", "is_official": True, "key_players": 11, "date": "2025-11-16"},
    ],
    "西班牙": [
        {"opponent": "佛得角", "result": "D", "score": "0-0", "opponent_rank": 67, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-15"},
        {"opponent": "秘鲁", "result": "W", "score": "3-1", "opponent_rank": 65, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-09"},
        {"opponent": "伊拉克", "result": "D", "score": "1-1", "opponent_rank": 57, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-05"},
        {"opponent": "埃及", "result": "D", "score": "0-0", "opponent_rank": 29, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "塞尔维亚", "result": "W", "score": "3-0", "opponent_rank": 42, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "阿尔及利亚": [
        {"opponent": "阿根廷", "result": "W", "score": "3-0", "opponent_rank": 3, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-17"},
        {"opponent": "玻利维亚", "result": "W", "score": "4-0", "opponent_rank": 87, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-11"},
        {"opponent": "荷兰", "result": "L", "score": "0-1", "opponent_rank": 8, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-06-04"},
        {"opponent": "乌拉圭", "result": "D", "score": "0-0", "opponent_rank": 16, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-31"},
        {"opponent": "危地马拉", "result": "W", "score": "7-0", "opponent_rank": 85, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "阿根廷": [
        {"opponent": "阿尔及利亚", "result": "W", "score": "3-0", "opponent_rank": 28, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-17"},
        {"opponent": "冰岛", "result": "W", "score": "3-0", "opponent_rank": 78, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-10"},
        {"opponent": "洪都拉斯", "result": "W", "score": "2-0", "opponent_rank": 83, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-07"},
        {"opponent": "赞比亚", "result": "W", "score": "5-0", "opponent_rank": 75, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "毛里塔尼亚", "result": "W", "score": "2-1", "opponent_rank": 99, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
    "韩国": [
        {"opponent": "捷克", "result": "W", "score": "2-1", "opponent_rank": 40, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-12"},
        {"opponent": "萨尔瓦多", "result": "W", "score": "1-0", "opponent_rank": 84, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-06-04"},
        {"opponent": "特立尼达和多巴哥", "result": "W", "score": "5-0", "opponent_rank": 86, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-05-31"},
        {"opponent": "奥地利", "result": "L", "score": "0-1", "opponent_rank": 32, "home_away": "away", "is_official": True, "key_players": 11, "date": "2026-04-01"},
        {"opponent": "科特迪瓦", "result": "L", "score": "0-4", "opponent_rank": 58, "home_away": "home", "is_official": True, "key_players": 11, "date": "2026-03-28"},
    ],
}



def weigh_by_recency(matches: List[dict], half_life_days: float = None,
                     competition_weights: dict = None) -> List[float]:
    """
    Compute time-decay weights for recent matches.

    Each match gets weight = 2^(-days_ago / half_life) × competition_weight,
    so a match exactly one half-life old contributes half as much as a match today.

    The single most recent match receives an additional multiplier
    (CONF.form_recent_weight_boost, default 2x).

    🆕 V4.5: competition_weight — 赛事类型加成 (淘汰赛>小组赛>预选赛>友谊赛).
    从 match['_source'] 推断: 'worldcup_backtest'→小组赛, 'cache'→预选赛, else→友谊赛.

    Args:
        matches: list of match dicts, each with optional 'date' and 'is_official' keys.
        half_life_days: decay half-life in days. Defaults to CONF.form_decay_half_life_days (30).
        competition_weights: dict mapping competition type → weight multiplier.

    Returns:
        List of floats, one weight per match, same order as input.
    """
    if half_life_days is None:
        half_life_days = CONF.form_decay_half_life_days
    if competition_weights is None:
        competition_weights = CONF.form_competition_weight

    today = date_type.today()
    weights: List[float] = []
    has_dates = False

    for m in matches:
        date_str = m.get('date', '')
        if date_str:
            try:
                match_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                days_ago = max(0.0, (today - match_date).days)
                weight = 2.0 ** (-days_ago / half_life_days)
                has_dates = True
            except (ValueError, TypeError):
                weight = 1.0
        else:
            weight = 1.0

        # 🆕 V4.5: 赛事类型加权
        comp_weight = 1.0
        source = m.get('_source', '')
        is_official = m.get('is_official', True)
        if source == 'worldcup_backtest':
            comp_weight = competition_weights.get('world_cup_group', 1.2)
        elif source == 'cache' or is_official:
            comp_weight = competition_weights.get('qualifier', 1.0)
        else:
            comp_weight = competition_weights.get('friendly', 0.6)

        weight *= comp_weight
        weights.append(weight)

    # Backward compatibility: if no date data at all, equal weights
    if not has_dates:
        return [1.0] * len(matches)

    # Most recent match (highest raw weight = smallest days_ago) gets a bonus
    if len(weights) > 0:
        max_idx = max(range(len(weights)), key=lambda i: weights[i])
        weights[max_idx] *= CONF.form_recent_weight_boost

    return weights


def analyze_recent_form(team: str) -> RecentForm:
    """
    分析球队近期状态
    综合考虑: 战绩·对手实力·主力出战率·比赛含金量
    """
    results = RECENT_RESULTS.get(team, [])
    if not results:
        # 模糊匹配
        for key in RECENT_RESULTS:
            if team in key or key in team:
                results = RECENT_RESULTS[key]
                break

    if not results:
        return RecentForm(team=team, form_score=5.0, form_string='?????',
                          notes=['无近期数据·使用默认值'])

    recent5 = results[:5]

    # ── 时间衰减加权 ──
    decay_weights = weigh_by_recency(recent5)
    total_weight = sum(decay_weights)
    # decay was actually applied when weights differ from uniform 1.0
    decay_applied = any(abs(w - 1.0) > 0.001 for w in decay_weights)

    form = RecentForm(team=team, matches=recent5, decay_applied=decay_applied)

    # 1. 基础战绩 (15分制·时间衰减加权)
    form.form_string = ''.join([m['result'] for m in recent5])
    weighted_points = sum(
        {'W': 3, 'D': 1, 'L': 0}[m['result']] * w
        for m, w in zip(recent5, decay_weights)
    )
    # Normalize to 0-15 scale: weighted_points / total_weight * 5
    form.points_last5 = (weighted_points / total_weight) * 5 if total_weight > 0 else 0

    # 2. 进球/失球 (时间衰减加权)
    weighted_gf = 0.0
    weighted_ga = 0.0
    for m, w in zip(recent5, decay_weights):
        parts = m['score'].split('-')
        if len(parts) == 2:
            weighted_gf += int(parts[0]) * w
            weighted_ga += int(parts[1]) * w
    form.avg_goals_scored = weighted_gf / total_weight if total_weight > 0 else 0.0
    form.avg_goals_conceded = weighted_ga / total_weight if total_weight > 0 else 0.0

    # 3. 对手质量 (排名越低=越强, 时间衰减加权)
    weighted_rank = sum(m['opponent_rank'] * w for m, w in zip(recent5, decay_weights))
    form.opponent_quality_avg = weighted_rank / total_weight if total_weight > 0 else 50.0
    # 🆕 V4.2 P0: quality_bonus 已移除 — 对手质量调整统一由 _adjust_form_for_opponent_quality 处理
    # (原: quality_bonus = max(0, (80 - form.opponent_quality_avg) / 15)  # 0-3分)

    # 4. 含金量加权 (正式比赛=1.0, 友谊赛=0.5, 时间衰减加权)
    weighted_official = sum(
        (1.0 if m['is_official'] else 0.5) * w
        for m, w in zip(recent5, decay_weights)
    )
    quality_weight = weighted_official / total_weight if total_weight > 0 else 1.0

    # 5. 主力出战率 (时间衰减加权)
    weighted_participation = sum(
        (m['key_players'] / 11) * w
        for m, w in zip(recent5, decay_weights)
    )
    form.key_player_participation = weighted_participation / total_weight if total_weight > 0 else 1.0

    # 6. 综合分: 权重来自config (默认70/20/10·待回测校准)
    # 🆕 V4.2 P0: 删除 quality_bonus (对手质量已由 _adjust_form_for_opponent_quality 独立处理)
    # 🆕 V4.5: 权重常量移到config
    w_pts = CONF.form_weight_points
    w_qual = CONF.form_weight_quality
    w_play = CONF.form_weight_players
    total_w = w_pts + w_qual + w_play
    pts_score = (form.points_last5 / 15) * (10 * w_pts / total_w)
    official_score = quality_weight * (10 * w_qual / total_w)
    player_score = form.key_player_participation * (10 * w_play / total_w)

    form.form_score = min(10, pts_score + official_score + player_score)  # 🆕 V3.17: 上限10

    # 🆕 V4.2 P0: 样本量惩罚 — 比赛数<5时每少一场扣0.4分 (config可调)
    n_matches = len(recent5)
    if n_matches < 5:
        sample_penalty = (5 - n_matches) * CONF.form_sample_penalty_per_missing
        form.form_score = max(0, form.form_score - sample_penalty)
        form.notes.append(f'📉 仅{n_matches}场样本·扣{sample_penalty:.1f}分→{form.form_score:.1f}/10')

    # 🆕 V3.32fix: 样本不足时向均值5.0回归
    # 🆕 V3.32: 样本不足标记 (不自动修正·提示人工补充)
    if n_matches < 3:
        form.notes.append(f'⚠️ 仅{n_matches}场样本·状态分{form.form_score:.1f}不可靠·建议人工补充赛前数据')

    form.quality_weighted_score = form.form_score

    # 7. 备注
    if form.points_last5 >= 12:
        form.notes.append(f'近5场{form.points_last5:.1f}/15分·状态极佳')
    elif form.points_last5 >= 9:
        form.notes.append(f'近5场{form.points_last5:.1f}/15分·状态良好')
    elif form.points_last5 <= 3:
        form.notes.append(f'近5场仅{form.points_last5:.1f}/15分·状态低迷')

    if form.opponent_quality_avg < 30:
        form.notes.append(f'对手平均排名{form.opponent_quality_avg:.0f}·赛程强度高')
    elif form.opponent_quality_avg > 60:
        form.notes.append(f'对手平均排名{form.opponent_quality_avg:.0f}·赛程偏弱·含金量存疑')

    if form.key_player_participation < 0.7:
        form.notes.append(f'主力出战率仅{form.key_player_participation:.0%}·状态参考性降低')

    # 🆕 V3.3 P0-3: 应用对手质量调整 (修正"虐菜刷分"vs"强队输球"的偏差)
    adj_score, adj_factor = _adjust_form_for_opponent_quality(form.form_score, form.opponent_quality_avg)
    form.opponent_quality_adjustment = adj_factor
    if adj_factor != 1.0:
        form.form_score = min(10, adj_score)  # 🆕 V3.17: 上限10
        form.quality_weighted_score = form.form_score

    return form


def _adjust_form_for_opponent_quality(form_score: float, opponent_quality_avg: float) -> tuple:
    """
    🆕 V3.3 P0-3 + V4.2 P0: 按对手平均排名调整状态分

    问题: 巴拿马9.2(虐菜)vs加纳7.2(对手强), 状态分反向
    修复: 对手越弱→状态分打折, 对手越强→状态分溢价
    V4.2 P0: 乘性折扣改为加性修正, 避免超调和截断

    Returns:
        (adjusted_form_score, bonus_applied)
    """
    # V4.2: 加性修正, 范围 -0.6 ~ +0.6 (V4.5: 显式clamp)
    opponent_bonus = (80 - opponent_quality_avg) * 0.008  # rank50→+0.24, rank20→+0.48, rank80→0
    opponent_bonus = max(-0.6, min(0.6, opponent_bonus))  # 🆕 V4.5: 防御性边界

    adjusted = form_score + opponent_bonus
    return adjusted, opponent_bonus


def get_form_diff(home: str, away: str) -> dict:
    """
    两队近期状态对比
    Returns:
        {'home_form', 'away_form', 'form_edge': float, 'confidence_adj': float}
    """
    home_form = analyze_recent_form(home)
    away_form = analyze_recent_form(away)

    # 状态差距 (-5~+5, 正数=主队占优)
    edge = home_form.form_score - away_form.form_score

    # 置信度调整 (V3.0回测校准: 差≥3=100%准确 → 使用满权重)
    if abs(edge) >= 3.0:
        adj = 10 if edge > 0 else -10    # 100%准确·满权重
    elif abs(edge) >= 2.0:
        adj = 6 if edge > 0 else -6     # 强信号
    elif abs(edge) >= 1.0:
        adj = 3 if edge > 0 else -3     # 中等信号
    else:
        adj = 0                           # 均势·无预测力

    return {
        'home_form': home_form,
        'away_form': away_form,
        'form_edge': edge,
        'confidence_adj': adj,
        'home_adj_factor': home_form.opponent_quality_adjustment,
        'away_adj_factor': away_form.opponent_quality_adjustment,
        'note': f'{home}状态{home_form.form_score:.1f}/10 vs {away}{away_form.form_score:.1f}/10 → 差{edge:+.1f}'
    }


# ── V3.0 P0: 世界杯赛果自动回填 ──

def auto_fill_worldcup_results():
    """
    从 backtest/matches.json 自动提取世界杯完赛数据，
    注入 RECENT_RESULTS，解决32队无近期状态的问题。
    """
    import json
    from pathlib import Path
    from match_context import normalize_team_name
    from fifa_rank_db import get_team_info

    backtest_file = Path(__file__).parent / 'backtest' / 'matches.json'
    if not backtest_file.exists():
        return 0

    with open(backtest_file, 'r', encoding='utf-8') as f:
        matches = json.load(f)

    added = 0
    for m in matches:
        if m['actual']['result'] == 'pending':
            continue
        name = m['match_name']
        parts = name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
        if len(parts) != 2:
            continue
        home_raw = parts[0].strip()
        away_raw = parts[1].strip()
        home = normalize_team_name(home_raw)
        away = normalize_team_name(away_raw)

        score = m['actual']['score']
        try:
            hg, ag = map(int, score.split('-'))
        except (ValueError, AttributeError):
            continue

        result_home = 'W' if hg > ag else ('D' if hg == ag else 'L')
        result_away = 'W' if ag > hg else ('D' if ag == hg else 'L')

        # Get opponent ranks
        away_info = get_team_info(away) if get_team_info else {'rank': 50}
        home_info = get_team_info(home) if get_team_info else {'rank': 50}
        away_rank = away_info.get('rank', 50) if away_info else 50
        home_rank = home_info.get('rank', 50) if home_info else 50

        # Extract date from match ID or use kickoff schedule
        from match_context import get_match
        gm = get_match(match_name=name)
        match_date = '2026-06-17'  # default
        if gm:
            # Parse UTC date
            try:
                from datetime import datetime
                utc_str = gm.kickoff_utc.replace('Z', '+00:00')
                match_date = datetime.fromisoformat(utc_str).strftime('%Y-%m-%d')
            except Exception:
                pass

        # Build match entries
        home_entry = {
            'opponent': away, 'result': result_home, 'score': score,
            'opponent_rank': away_rank, 'home_away': 'home',  # World Cup: listed first = home
            'is_official': True, 'key_players': 10, 'date': match_date,
            '_source': 'worldcup_backtest',
        }
        away_entry = {
            'opponent': home, 'result': result_away, 'score': f'{ag}-{hg}',
            'opponent_rank': home_rank, 'home_away': 'away',
            'is_official': True, 'key_players': 10, 'date': match_date,
            '_source': 'worldcup_backtest',
        }

        # Merge into RECENT_RESULTS (prepend World Cup results)
        for team, entry in [(home, home_entry), (away, away_entry)]:
            if team not in RECENT_RESULTS:
                RECENT_RESULTS[team] = []
            # Avoid duplicates
            existing = RECENT_RESULTS[team]
            if not any(e.get('_source') == 'worldcup_backtest' and e['opponent'] == entry['opponent'] for e in existing):
                RECENT_RESULTS[team].insert(0, entry)
                added += 1

    # Sort: World Cup results first, then original data
    for team in RECENT_RESULTS:
        wc = [e for e in RECENT_RESULTS[team] if e.get('_source') == 'worldcup_backtest']
        orig = [e for e in RECENT_RESULTS[team] if e.get('_source') != 'worldcup_backtest']
        RECENT_RESULTS[team] = wc + orig

    return added


# Load from persistent cache (generated by import_recent_form.py)
def _load_cache():
    cache_file = Path(__file__).parent / 'recent_form_cache.json'
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            for team, matches in cached.items():
                if team not in RECENT_RESULTS:
                    RECENT_RESULTS[team] = []
                # Prepend cached data (only if not already loaded from this source)
                existing_opponents = {(m.get('opponent'), m.get('date')) for m in RECENT_RESULTS[team]}
                for m in matches:
                    key = (m.get('opponent'), m.get('date'))
                    if key not in existing_opponents:
                        RECENT_RESULTS[team].insert(0, m)
                        existing_opponents.add(key)
            return len(cached)
        except Exception:
            pass
    return 0

_cached_loaded = _load_cache()

# Auto-fill World Cup results from backtest (incremental)
_auto_filled = auto_fill_worldcup_results()

# 🆕 V3.32: 去重 — 移除(opponent, date)完全相同的重复条目
for _team in RECENT_RESULTS:
    _seen = set()
    _deduped = []
    for _m in RECENT_RESULTS[_team]:
        _key = (_m.get('opponent'), _m.get('date'))
        if _key not in _seen:
            _seen.add(_key)
            _deduped.append(_m)
    RECENT_RESULTS[_team] = _deduped


# ── 独立测试 ──
if __name__ == '__main__':
    test_teams = ['法国', '塞内加尔', '伊拉克', '挪威', '阿根廷', '阿尔及利亚', '奥地利', '约旦']

    for team in test_teams:
        form = analyze_recent_form(team)
        print(f"\n{'='*50}")
        print(f"  📈 {team} 近期状态: {form.form_string}  [衰减: {'ON' if form.decay_applied else 'OFF'}]")
        print(f"  积分: {form.points_last5:.1f}/15 | 进球: {form.avg_goals_scored:.1f}/场 | 失球: {form.avg_goals_conceded:.1f}/场")
        print(f"  对手均排名: {form.opponent_quality_avg:.0f} | 主力出战率: {form.key_player_participation:.0%}")
        print(f"  综合状态分: {form.form_score:.1f}/10")
        for n in form.notes:
            print(f"    → {n}")

    print(f"\n{'='*60}")
    print("  两队对比:")
    for home, away in [('法国', '塞内加尔'), ('伊拉克', '挪威'), ('阿根廷', '阿尔及利亚'), ('奥地利', '约旦')]:
        diff = get_form_diff(home, away)
        print(f"\n  {home} vs {away}")
        print(f"  {diff['note']}")
        print(f"  调整: {diff['confidence_adj']:+d}%")

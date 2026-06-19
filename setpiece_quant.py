# -*- coding: utf-8 -*-
"""
V3.0 定位球量化分析
超越文本标签 — 将定位球威胁转化为可量化的置信度调整和大小球影响。

规则:
  - 身高/空中优势 + 大风 → 优势放大
  - 弱防守(frail) vs 强进攻 → 惩罚
  - 影响大小球总进球线
  - 所有数据保存在 SETPIECE_DB

用法:
  from setpiece_quant import analyze_setpiece
  result = analyze_setpiece('德国', '日本', 'windy')
  print(result.confidence_adj)  # -3 to +3
  print(result.total_goals_adj) # -0.3 to +0.3
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import CONF


# ══════════════════════════════════════════════════════════════════
# 定位球数据
# ══════════════════════════════════════════════════════════════════
# height_advantage: -1 (矮小) → +1 (高大)
# aerial_threat:    -1 (无空中威胁) → +1 (顶级争顶)
# corner_goals_pct: 角球进球占总进球比例 (世界杯均值 ~28%)
# fk_goals_per_game: 场均任意球进球 (世界杯均值 ~0.15)
#
# "frail" 标记: 定位球防守存在结构性漏洞 (身高不足/区域防守差)
# ──────────────────────────────────────────────────────────────────

SETPIECE_DB: Dict[str, dict] = {

    # ── 顶级定位球强队 (>35% 定位球进球) ──
    '德国':   {'corner_goals_pct': 0.38, 'fk_goals_per_game': 0.22,
               'height_advantage': 1.0, 'aerial_threat': 1.0,
               'notes': '定位球大师·角球战术丰富·2014/2018角球进球占比38%'},
    '英格兰': {'corner_goals_pct': 0.40, 'fk_goals_per_game': 0.20,
               'height_advantage': 1.0, 'aerial_threat': 1.0,
               'notes': '2018角球之王·马奎尔/凯恩头球威胁·定位球占比40%'},
    '乌拉圭': {'corner_goals_pct': 0.36, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.8, 'aerial_threat': 1.0,
               'notes': '戈丁/吉梅内斯头球双塔·传统定位球强队'},
    '摩洛哥': {'corner_goals_pct': 0.35, 'fk_goals_per_game': 0.18,
               'height_advantage': 0.5, 'aerial_threat': 0.8,
               'notes': '2022恩内斯里头球破门·定位球占比35%+'},

    # ── 高大·空中威胁强队 ──
    '挪威':   {'corner_goals_pct': 0.33, 'fk_goals_per_game': 0.18,
               'height_advantage': 1.0, 'aerial_threat': 1.0,
               'notes': '哈兰德(1.94m)世界顶级争顶·定位球战术核心'},
    '塞尔维亚': {'corner_goals_pct': 0.32, 'fk_goals_per_game': 0.16,
               'height_advantage': 1.0, 'aerial_threat': 0.9,
               'notes': '米特罗维奇/弗拉霍维奇双塔·东欧传统空中优势'},
    '比利时': {'corner_goals_pct': 0.32, 'fk_goals_per_game': 0.17,
               'height_advantage': 0.7, 'aerial_threat': 0.8,
               'notes': '卢卡库支柱·费莱尼时代延续·角球威胁'},
    '波兰':   {'corner_goals_pct': 0.30, 'fk_goals_per_game': 0.16,
               'height_advantage': 0.7, 'aerial_threat': 0.8,
               'notes': '莱万头球威胁·东欧身体优势'},

    # ── 身体强队 (定位球能力中上) ──
    '克罗地亚': {'corner_goals_pct': 0.30, 'fk_goals_per_game': 0.16,
               'height_advantage': 0.6, 'aerial_threat': 0.5,
               'notes': '中场高大·莫德里奇精准传中'},
    '丹麦':   {'corner_goals_pct': 0.30, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.6, 'aerial_threat': 0.5,
               'notes': '安德森/维斯特高双塔·北欧身体优势'},
    '荷兰':   {'corner_goals_pct': 0.29, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.5, 'aerial_threat': 0.5,
               'notes': '范戴克头球威胁·但非定位球核心战术'},
    '法国':   {'corner_goals_pct': 0.30, 'fk_goals_per_game': 0.16,
               'height_advantage': 0.4, 'aerial_threat': 0.6,
               'notes': '姆巴佩非头球型·但防线高大·定位球威胁中上'},
    '葡萄牙': {'corner_goals_pct': 0.29, 'fk_goals_per_game': 0.17,
               'height_advantage': 0.3, 'aerial_threat': 0.5,
               'notes': 'C罗头球历史顶级(但老龄化)·B费任意球威胁'},
    '塞内加尔': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.4, 'aerial_threat': 0.5,
               'notes': '身体对抗强·库利巴利头球·定位球中上'},
    '瑞士':   {'corner_goals_pct': 0.29, 'fk_goals_per_game': 0.16,
               'height_advantage': 0.3, 'aerial_threat': 0.3,
               'notes': '组织严密·定位球防守好·进攻中规中矩'},
    '奥地利': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.3, 'aerial_threat': 0.3,
               'notes': '朗尼克体系·定位球中等'},
    '澳大利亚': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.3, 'aerial_threat': 0.4,
               'notes': '英式传统·身体对抗好·定位球中等'},
    '捷克':   {'corner_goals_pct': 0.30, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.5, 'aerial_threat': 0.5,
               'notes': '东欧身体优势·绍切克头球威胁'},
    '苏格兰': {'corner_goals_pct': 0.29, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.4, 'aerial_threat': 0.4,
               'notes': '英式足球传统·定位球中上'},
    '匈牙利': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.3, 'aerial_threat': 0.3,
               'notes': '索博斯洛伊任意球·定位球中等'},
    '土耳其': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.3, 'aerial_threat': 0.3,
               'notes': '恰尔汗奥卢任意球专家·定位球中等'},
    '意大利': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.2, 'aerial_threat': 0.3,
               'notes': '传统防守好·定位球进攻非核心'},
    '巴西':   {'corner_goals_pct': 0.26, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.0, 'aerial_threat': 0.2,
               'notes': '技术流·头球非强项·但定位球技术好'},
    '阿根廷': {'corner_goals_pct': 0.25, 'fk_goals_per_game': 0.15,
               'height_advantage': -0.3, 'aerial_threat': -0.2,
               'notes': '梅西时代身材偏矮·角球威胁低于均值'},
    '西班牙': {'corner_goals_pct': 0.25, 'fk_goals_per_game': 0.15,
               'height_advantage': -0.3, 'aerial_threat': -0.3,
               'notes': 'Tiki-taka短传·定位球非战术核心·身材偏小'},
    '哥伦比亚': {'corner_goals_pct': 0.27, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.0, 'aerial_threat': 0.2,
               'notes': 'J罗传中精准·定位球中等'},
    '智利':   {'corner_goals_pct': 0.25, 'fk_goals_per_game': 0.14,
               'height_advantage': -0.2, 'aerial_threat': -0.2,
               'notes': '桑切斯时代后身材偏小·定位球一般'},

    # ── 非洲球队 (身体好但定位球战术不足) ──
    '加纳':   {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.2, 'aerial_threat': 0.2,
               'notes': '身体对抗好·定位球中规中矩'},
    '科特迪瓦': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.2, 'aerial_threat': 0.3,
               'notes': '德罗巴时代后身体优势仍在·定位球中等'},
    '阿尔及利亚': {'corner_goals_pct': 0.27, 'fk_goals_per_game': 0.14,
               'height_advantage': -0.1, 'aerial_threat': 0.0,
               'notes': '马赫雷斯技术好·非头球型·定位球一般'},
    '埃及':   {'corner_goals_pct': 0.26, 'fk_goals_per_game': 0.14,
               'height_advantage': -0.1, 'aerial_threat': -0.1,
               'notes': '萨拉赫非头球型·定位球一般'},
    '刚果民主共和国': {'corner_goals_pct': 0.27, 'fk_goals_per_game': 0.13,
               'height_advantage': 0.1, 'aerial_threat': 0.1,
               'notes': '身体好但战术不足·定位球中等偏下'},
    '佛得角': {'corner_goals_pct': 0.26, 'fk_goals_per_game': 0.13,
               'height_advantage': -0.1, 'aerial_threat': 0.0,
               'notes': '定位球中等偏下'},
    '南非':   {'corner_goals_pct': 0.27, 'fk_goals_per_game': 0.14,
               'height_advantage': -0.2, 'aerial_threat': -0.1,
               'notes': '定位球一般'},

    # ── 亚洲球队 ──
    '日本':   {'corner_goals_pct': 0.22, 'fk_goals_per_game': 0.14,
               'height_advantage': -1.0, 'aerial_threat': -1.0,
               'notes': '身材矮小·角球防守天然劣势·frail标记', 'frail': True},
    '沙特':   {'corner_goals_pct': 0.22, 'fk_goals_per_game': 0.12,
               'height_advantage': -1.0, 'aerial_threat': -1.0,
               'notes': '身材矮小·定位球攻防均弱·frail标记', 'frail': True},
    '伊朗':   {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.2, 'aerial_threat': 0.3,
               'notes': '亚洲身体最强·定位球中等'},
    '韩国':   {'corner_goals_pct': 0.25, 'fk_goals_per_game': 0.14,
               'height_advantage': -0.2, 'aerial_threat': 0.0,
               'notes': '孙兴慜/金玟哉提升身高·整体仍偏矮'},
    '卡塔尔': {'corner_goals_pct': 0.24, 'fk_goals_per_game': 0.13,
               'height_advantage': -0.5, 'aerial_threat': -0.5,
               'notes': '身材偏矮·2022东道主·定位球劣势'},
    '乌兹别克斯坦': {'corner_goals_pct': 0.27, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.0, 'aerial_threat': 0.0,
               'notes': '定位球中等偏下'},
    '伊拉克': {'corner_goals_pct': 0.26, 'fk_goals_per_game': 0.13,
               'height_advantage': -0.2, 'aerial_threat': -0.1,
               'notes': '定位球一般'},
    '约旦':   {'corner_goals_pct': 0.25, 'fk_goals_per_game': 0.13,
               'height_advantage': -0.3, 'aerial_threat': -0.2,
               'notes': '定位球偏弱'},
    '阿联酋': {'corner_goals_pct': 0.25, 'fk_goals_per_game': 0.13,
               'height_advantage': -0.3, 'aerial_threat': -0.2,
               'notes': '定位球偏弱'},

    # ── CONCACAF ──
    '墨西哥': {'corner_goals_pct': 0.24, 'fk_goals_per_game': 0.14,
               'height_advantage': -1.0, 'aerial_threat': -0.8,
               'notes': '传统身材偏矮·角球防守障碍·frail标记', 'frail': True},
    '美国':   {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.15,
               'height_advantage': 0.3, 'aerial_threat': 0.4,
               'notes': '普利西奇/麦肯尼·身体对抗好·定位球中上'},
    '加拿大': {'corner_goals_pct': 0.26, 'fk_goals_per_game': 0.13,
               'height_advantage': 0.1, 'aerial_threat': 0.1,
               'notes': '戴维斯速度型·整体定位球一般'},
    '哥斯达黎加': {'corner_goals_pct': 0.26, 'fk_goals_per_game': 0.14,
               'height_advantage': -0.2, 'aerial_threat': -0.1,
               'notes': '纳瓦斯守门好·定位球攻防一般'},
    '巴拿马': {'corner_goals_pct': 0.26, 'fk_goals_per_game': 0.13,
               'height_advantage': -0.3, 'aerial_threat': -0.2,
               'notes': '定位球一般'},
    '海地':   {'corner_goals_pct': 0.25, 'fk_goals_per_game': 0.12,
               'height_advantage': -0.3, 'aerial_threat': -0.3,
               'notes': '定位球偏弱'},

    # ── 其他 ──
    '波黑':   {'corner_goals_pct': 0.29, 'fk_goals_per_game': 0.16,
               'height_advantage': 0.5, 'aerial_threat': 0.5,
               'notes': '哲科头球·东欧身体优势·定位球中上'},
    '新西兰': {'corner_goals_pct': 0.28, 'fk_goals_per_game': 0.14,
               'height_advantage': 0.4, 'aerial_threat': 0.4,
               'notes': '英式橄榄球身体·定位球中等'},
}

# ── 弱防守标记补全 (SETPIECE_DB中未明确frail的球队默认False) ──
_KNOWN_FRAIL: set = {'日本', '沙特', '墨西哥'}


# ══════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════

@dataclass
class SetPieceResult:
    """定位球量化结果"""
    home_corner_pct: float = CONF.setpiece_default_goals_pct
    away_corner_pct: float = CONF.setpiece_default_goals_pct
    home_aerial_adv: float = 0.0       # -1 to +1
    away_aerial_adv: float = 0.0       # -1 to +1
    total_goals_adj: float = 0.0       # -0.3 to +0.3 on totals line
    confidence_adj: float = 0.0        # -3 to +3 on prediction confidence
    notes: List[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════
# 核心分析函数
# ══════════════════════════════════════════════════════════════════

def _get_team_data(team: str) -> dict:
    """获取球队定位球数据, 不存在则返回默认值"""
    if team in SETPIECE_DB:
        return SETPIECE_DB[team]
    return {
        'corner_goals_pct': CONF.setpiece_default_goals_pct,
        'fk_goals_per_game': 0.15,
        'height_advantage': 0.0,
        'aerial_threat': 0.0,
        'notes': f'{team}无定位球数据→使用默认值',
        'frail': False,
    }


def _team_setpiece_score(team_data: dict) -> float:
    """
    综合定位球得分: -1.0 (极弱) → +1.0 (极强)
    权重: 角球进球占比(0.35) + 任意球(0.25) + 身高(0.20) + 空中威胁(0.20)
    """
    # 标准化角球占比: 0.22→-0.5, 0.28→0, 0.40→+1
    corner_norm = (team_data['corner_goals_pct'] - 0.28) / 0.12
    # 标准化任意球: 0.12→-0.5, 0.15→0, 0.22→+1
    fk_norm = (team_data['fk_goals_per_game'] - 0.15) / 0.07

    score = (0.35 * corner_norm +
             0.25 * fk_norm +
             0.20 * team_data['height_advantage'] +
             0.20 * team_data['aerial_threat'])
    return max(-1.0, min(1.0, score))


def _is_frail(team: str, team_data: dict) -> bool:
    """判断球队定位球防守是否有结构性漏洞"""
    if team_data.get('frail', False):
        return True
    if team in _KNOWN_FRAIL:
        return True
    # 推断: 身高优势 < -0.7 + 空中威胁 < -0.5 → 很可能frail
    if team_data['height_advantage'] <= -0.7 and team_data['aerial_threat'] <= -0.5:
        return True
    return False


def analyze_setpiece(home_team: str, away_team: str,
                     weather_condition: Optional[str] = 'clear') -> SetPieceResult:
    """
    量化定位球对比赛的预期影响

    Args:
        home_team: 主队名 (中文)
        away_team: 客队名 (中文)
        weather_condition: 天气状况 ('clear', 'rain', 'windy', 'storm', 'cloudy',
                           'overcast', 'indoor', 或任意含'wind'/'rain'的描述)

    Returns:
        SetPieceResult 包含:
        - confidence_adj: 预测置信度调整 (-3~+3), 正值=主队受益
        - total_goals_adj: 大小球线调整 (-0.3~+0.3), 正值=更倾向大球
        - notes: 可读的调整说明
    """
    result = SetPieceResult()

    home_data = _get_team_data(home_team)
    away_data = _get_team_data(away_team)

    home_score = _team_setpiece_score(home_data)
    away_score = _team_setpiece_score(away_data)

    result.home_corner_pct = home_data['corner_goals_pct']
    result.away_corner_pct = away_data['corner_goals_pct']
    result.home_aerial_adv = home_data['height_advantage']
    result.away_aerial_adv = away_data['height_advantage']

    home_frail = _is_frail(home_team, home_data)
    away_frail = _is_frail(away_team, away_data)

    # ── 天气解析 ──
    weather_lower = (weather_condition or 'clear').lower()
    is_windy = any(kw in weather_lower for kw in ('wind', '大风', 'storm', '暴风'))
    is_rainy = any(kw in weather_lower for kw in ('rain', '雨', 'storm', '暴'))
    is_storm = any(kw in weather_lower for kw in ('storm', '暴'))

    # ── 1. 基础定位球差距 ──
    raw_diff = home_score - away_score  # 正值=主队更强

    # ── 2. 天气放大效应 ──
    weather_multiplier = 1.0
    if is_windy:
        # 大风 → 比赛更多用高空球 → 空中优势放大
        weather_multiplier *= 1.5
        if is_storm:
            weather_multiplier *= 2.0
        result.notes.append(f'大风天气: 空中优势价值放大{weather_multiplier:.1f}x')

    if is_rainy:
        # 雨天 → 球速快+湿滑 → 门将脱手概率↑ → 定位球二次进攻↑
        weather_multiplier *= 1.2
        if not is_windy:
            result.notes.append('雨天: 门将脱手概率↑·定位球二点球机会↑')

    # ── 3. 弱防守惩罚 ──
    frail_penalty = 0.0
    if home_frail and away_score > 0.3:
        frail_penalty -= 1.0
        result.notes.append(
            f'{home_team}定位球防守弱(frail) vs {away_team}定位球强攻')
    if away_frail and home_score > 0.3:
        frail_penalty += 1.0
        result.notes.append(
            f'{away_team}定位球防守弱(frail) vs {home_team}定位球强攻')

    # ── 4. 极端不对称 ──
    asymmetry_penalty = 0.0
    if home_score > 0.5 and away_score < -0.3:
        asymmetry_penalty += 0.8
        result.notes.append(
            f'定位球极端不对称: {home_team}(强) vs {away_team}(弱)')
    if away_score > 0.5 and home_score < -0.3:
        asymmetry_penalty -= 0.8
        result.notes.append(
            f'定位球极端不对称: {away_team}(强) vs {home_team}(弱)')

    # ── 5. 综合置信度调整 ──
    raw_adj = (raw_diff * 3.0 * weather_multiplier) + frail_penalty + asymmetry_penalty
    result.confidence_adj = max(-3.0, min(3.0, raw_adj))
    result.confidence_adj = round(result.confidence_adj, 1)

    # ── 6. 大小球调整 ──
    avg_score = (home_score + away_score) / 2
    if avg_score > 0.4:
        goals_adj = 0.1 + (avg_score - 0.4) * 0.5
    elif avg_score < -0.2:
        goals_adj = (avg_score + 0.2) * 0.5
    else:
        goals_adj = 0.0

    # 天气叠加
    if is_windy:
        goals_adj += 0.05
    if is_rainy:
        goals_adj += 0.03

    # 弱防守+强进攻→定位球失球↑→Over
    if home_frail or away_frail:
        if (home_frail and away_score > 0.2) or (away_frail and home_score > 0.2):
            goals_adj += 0.08

    result.total_goals_adj = max(-0.3, min(0.3, round(goals_adj, 2)))

    # ── 7. 数据来源注释 ──
    if home_team not in SETPIECE_DB:
        result.notes.append(f'{home_team}使用默认定位球数据')
    if away_team not in SETPIECE_DB:
        result.notes.append(f'{away_team}使用默认定位球数据')

    # 如果没有任何显著影响
    if abs(result.confidence_adj) < 0.3 and abs(result.total_goals_adj) < 0.05:
        result.notes.append('定位球无明显不对称·双方差距小')

    return result


# ══════════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════════

def get_team_setpiece_profile(team: str) -> Optional[dict]:
    """获取单支球队的定位球数据, 用于仪表盘展示"""
    return SETPIECE_DB.get(team)


def list_frail_teams() -> List[str]:
    """列出所有定位球防守有结构性漏洞的球队"""
    frail_list = list(_KNOWN_FRAIL)
    for team, data in SETPIECE_DB.items():
        if data.get('frail') and team not in frail_list:
            frail_list.append(team)
    return sorted(frail_list)


def list_aerial_threats(min_threat: float = 0.5) -> List[str]:
    """列出空中威胁超过指定阈值的球队"""
    return sorted([
        team for team, data in SETPIECE_DB.items()
        if data['aerial_threat'] >= min_threat
    ])


def setpiece_h2h_summary(home_team: str, away_team: str) -> str:
    """两队定位球对比摘要 (文本)"""
    home_data = _get_team_data(home_team)
    away_data = _get_team_data(away_team)
    home_score = _team_setpiece_score(home_data)
    away_score = _team_setpiece_score(away_data)

    def label(score: float) -> str:
        if score > 0.5: return '强'
        if score > 0.2: return '中上'
        if score > -0.2: return '中等'
        if score > -0.5: return '偏弱'
        return '弱'

    lines = [
        f'{home_team} 定位球: {label(home_score)} (角球{home_data["corner_goals_pct"]:.0%}'
        f'·身高{home_data["height_advantage"]:+.0f})',
        f'{away_team} 定位球: {label(away_score)} (角球{away_data["corner_goals_pct"]:.0%}'
        f'·身高{away_data["height_advantage"]:+.0f})',
    ]
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════
# 独立测试
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 65)
    print("V3.0 定位球量化分析 — 测试")
    print("=" * 65)

    # 测试1: 典型不对称
    print("\n[1] 德国(强) vs 日本(弱·frail) — 晴天")
    r = analyze_setpiece('德国', '日本', 'clear')
    print(f"  置信度调整: {r.confidence_adj:+.1f} (德国受益)")
    print(f"  大小球调整: {r.total_goals_adj:+.2f}")
    for n in r.notes:
        print(f"    -> {n}")

    # 测试2: 大风天气放大
    print("\n[2] 德国(强) vs 日本(弱) — 大风")
    r = analyze_setpiece('德国', '日本', 'windy')
    print(f"  置信度调整: {r.confidence_adj:+.1f} (大风放大)")
    print(f"  大小球调整: {r.total_goals_adj:+.2f}")
    for n in r.notes:
        print(f"    -> {n}")

    # 测试3: 势均力敌
    print("\n[3] 英格兰 vs 德国 — 晴天")
    r = analyze_setpiece('英格兰', '德国', 'clear')
    print(f"  置信度调整: {r.confidence_adj:+.1f}")
    print(f"  大小球调整: {r.total_goals_adj:+.2f}")
    for n in r.notes:
        print(f"    -> {n}")

    # 测试4: 弱对弱
    print("\n[4] 日本 vs 沙特 — 晴天")
    r = analyze_setpiece('日本', '沙特', 'clear')
    print(f"  置信度调整: {r.confidence_adj:+.1f}")
    print(f"  大小球调整: {r.total_goals_adj:+.2f}")
    for n in r.notes:
        print(f"    -> {n}")

    # 测试5: 挪威vs弱队
    print("\n[5] 挪威(哈兰德·强) vs 阿联酋(弱) — 雨天")
    r = analyze_setpiece('挪威', '阿联酋', 'rain')
    print(f"  置信度调整: {r.confidence_adj:+.1f}")
    print(f"  大小球调整: {r.total_goals_adj:+.2f}")
    for n in r.notes:
        print(f"    -> {n}")

    # 测试6: 未知球队
    print("\n[6] UnknownTeam vs 德国 — 晴天")
    r = analyze_setpiece('UnknownTeam', '德国', 'clear')
    print(f"  置信度调整: {r.confidence_adj:+.1f}")
    print(f"  大小球调整: {r.total_goals_adj:+.2f}")
    for n in r.notes:
        print(f"    -> {n}")

    # ── 汇总 ──
    print("\n" + "=" * 65)
    print("定位球强队 (>0.5):", list_aerial_threats(0.5))
    print("Frail 球队:", list_frail_teams())
    print(f"数据库球队数: {len(SETPIECE_DB)}")
    print("=" * 65)

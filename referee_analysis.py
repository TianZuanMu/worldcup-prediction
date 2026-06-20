"""
V2.10 裁判因素分析
评估: 执法严格度·出牌频率·历史执法记录·对比赛风格的影响
依赖: match_context.py (球队名映射)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class RefereeProfile:
    """裁判档案"""
    name: str
    nationality: str
    confederation: str          # UEFA/CONMEBOL/AFC/CAF/CONCACAF/OFC
    age: int
    experience_years: int       # 国际级裁判年限
    matches_this_tournament: int = 0
    avg_yellows: float = 3.5    # 场均黄牌
    avg_reds: float = 0.2       # 场均红牌
    avg_fouls: float = 22.0     # 场均吹罚犯规
    pen_given_per_match: float = 0.2  # 场均点球
    strictness: str = 'medium'  # 'lenient'|'medium'|'strict'|'very_strict'
    var_usage: str = 'moderate' # 'minimal'|'moderate'|'heavy'
    notable_matches: List[str] = field(default_factory=list)
    style_impact: str = ''      # 对比赛风格的影响描述


# ── 裁判数据库 (2026世界杯部分裁判) ──

REFEREE_DB: Dict[str, RefereeProfile] = {
    'Szymon Marciniak': RefereeProfile(
        name='Szymon Marciniak', nationality='波兰', confederation='UEFA',
        age=45, experience_years=11, matches_this_tournament=1,
        avg_yellows=3.8, avg_reds=0.15, avg_fouls=23, pen_given_per_match=0.2,
        strictness='medium', var_usage='moderate',
        notable_matches=['2022世界杯决赛', '2023欧冠决赛'],
        style_impact='不轻易出牌·允许身体对抗·大赛经验丰富',
    ),
    'Daniele Orsato': RefereeProfile(
        name='Daniele Orsato', nationality='意大利', confederation='UEFA',
        age=50, experience_years=14, matches_this_tournament=0,
        avg_yellows=4.2, avg_reds=0.25, avg_fouls=25, pen_given_per_match=0.25,
        strictness='strict', var_usage='heavy',
        notable_matches=['2020欧冠决赛', '2022世界杯半决赛'],
        style_impact='执法严格·频繁中断比赛·VAR倾向高·对防守型球队不利',
    ),
    'Cesar Ramos': RefereeProfile(
        name='Cesar Ramos', nationality='墨西哥', confederation='CONCACAF',
        age=41, experience_years=8, matches_this_tournament=1,
        avg_yellows=3.2, avg_reds=0.1, avg_fouls=20, pen_given_per_match=0.15,
        strictness='lenient', var_usage='minimal',
        notable_matches=['2022世界杯', '中北美金杯决赛'],
        style_impact='宽松执法·比赛流畅·身体对抗允许度高',
    ),
    'Facundo Tello': RefereeProfile(
        name='Facundo Tello', nationality='阿根廷', confederation='CONMEBOL',
        age=43, experience_years=6, matches_this_tournament=0,
        avg_yellows=5.0, avg_reds=0.35, avg_fouls=28, pen_given_per_match=0.3,
        strictness='very_strict', var_usage='heavy',
        notable_matches=['南美解放者杯决赛'],
        style_impact='出牌频率极高·比赛节奏碎片化·定位球增多·高空球队受益',
    ),
    'Wilmar Roldan': RefereeProfile(
        name='Wilmar Roldan', nationality='哥伦比亚', confederation='CONMEBOL',
        age=46, experience_years=13, matches_this_tournament=1,
        avg_yellows=4.5, avg_reds=0.3, avg_fouls=26, pen_given_per_match=0.25,
        strictness='strict', var_usage='moderate',
        notable_matches=['2018世界杯', '2022世界杯', '美洲杯决赛'],
        style_impact='南美风格·对恶意犯规零容忍·高身体对抗比赛控制好',
    ),
    'Istvan Kovacs': RefereeProfile(
        name='Istvan Kovacs', nationality='罗马尼亚', confederation='UEFA',
        age=41, experience_years=7, matches_this_tournament=0,
        avg_yellows=3.5, avg_reds=0.2, avg_fouls=22, pen_given_per_match=0.2,
        strictness='medium', var_usage='moderate',
        notable_matches=['欧联杯决赛', '2024欧洲杯'],
        style_impact='均衡执法·无明显偏向·对技术型球队中性',
    ),
    'Salima Mukansanga': RefereeProfile(
        name='Salima Mukansanga', nationality='卢旺达', confederation='CAF',
        age=37, experience_years=4, matches_this_tournament=0,
        avg_yellows=3.0, avg_reds=0.1, avg_fouls=20, pen_given_per_match=0.1,
        strictness='medium', var_usage='minimal',
        notable_matches=['2022世界杯(第四官员)', '非洲杯'],
        style_impact='执法经验相对有限·重大比赛可能存在压力',
    ),
    'Yoshimi Yamashita': RefereeProfile(
        name='Yoshimi Yamashita', nationality='日本', confederation='AFC',
        age=39, experience_years=5, matches_this_tournament=0,
        avg_yellows=2.8, avg_reds=0.08, avg_fouls=18, pen_given_per_match=0.12,
        strictness='lenient', var_usage='minimal',
        notable_matches=['2022世界杯', '亚冠决赛'],
        style_impact='执法宽松·比赛流畅度高·亚洲技术流受益',
    ),
}


# ── 比赛-裁判指派 (模拟) ──

MATCH_REFEREE: Dict[str, str] = {
    # V2.10 当前比赛日
    '法国VS塞内加尔': 'Szymon Marciniak',
    '伊拉克VS挪威': 'Yoshimi Yamashita',
    '阿根廷VS阿尔及利亚': 'Facundo Tello',
    '奥地利VS约旦': 'Cesar Ramos',
    # V2.10 6/15回测
    '德国VS库拉索': 'Daniele Orsato',
    '荷兰VS日本': 'Wilmar Roldan',
    '科特迪瓦VS厄瓜多尔': 'Cesar Ramos',
    '瑞典VS突尼斯': 'Istvan Kovacs',
    # 其他
    '巴西VS摩洛哥': 'Wilmar Roldan',
    '德国VS荷兰': 'Daniele Orsato',
    '英格兰VS克罗地亚': 'Istvan Kovacs',
    '西班牙VS佛得角': 'Salima Mukansanga',
    '意大利VS乌拉圭': 'Szymon Marciniak',
}


def get_referee(match_name: str) -> Optional[RefereeProfile]:
    """获取比赛执法裁判"""
    ref_name = MATCH_REFEREE.get(match_name)
    if ref_name:
        return REFEREE_DB.get(ref_name)
    return None


def analyze_referee_impact(match_name: str, home: str = '', away: str = '') -> dict:
    """
    分析裁判对比赛的影响
    Returns:
        {'referee': RefereeProfile or None, 'over_under_adj': float,
         'card_risk': str, 'style_impact': str, 'notes': []}
    """
    ref = get_referee(match_name)

    if not ref:
        return {
            'referee': None, 'over_under_adj': 0, 'confidence_adj': 0,
            'card_risk': 'unknown', 'style_impact': '无裁判数据',
            'notes': ['裁判信息不可用'],
        }

    notes = []
    cards_adj = 0
    ou_adj = 0.0
    confidence_adj = 0

    # 🆕 V3.15: 检测两队风格 (技术型 vs 力量型)
    TECH_TEAMS = {'阿根廷', '西班牙', '葡萄牙', '巴西', '法国', '荷兰', '德国', '日本',
                  '英格兰', '比利时', '克罗地亚', '乌拉圭', '哥伦比亚'}
    PHYS_TEAMS = {'阿尔及利亚', '塞内加尔', '摩洛哥', '科特迪瓦', '民主刚果', '加纳',
                  '尼日利亚', '喀麦隆', '南非', '塞尔维亚', '波兰', '瑞典', '丹麦',
                  '挪威', '奥地利', '瑞士', '捷克', '斯洛伐克'}
    home_is_tech = home in TECH_TEAMS
    away_is_tech = away in TECH_TEAMS
    home_is_phys = home in PHYS_TEAMS
    away_is_phys = away in PHYS_TEAMS

    # 1. 出牌频率分析 (V3.15: 差异化技术/力量队影响)
    if ref.avg_yellows >= 5.0:
        cards_adj = -3
        notes.append(f'🔴 裁判{ref.name}场均黄牌{ref.avg_yellows:.1f}张·极高')
        # 高出牌→比赛碎片化→技术型队受损更重
        if home_is_tech: confidence_adj -= 3
        elif home_is_phys: confidence_adj += 2
        if away_is_tech: confidence_adj += 3  # 对手技术队受损 → 主队受益
        elif away_is_phys and not home_is_tech: confidence_adj -= 2
        # 大小球: 高出牌→比赛碎片化→小球
        ou_adj -= 0.08
    elif ref.avg_yellows >= 4.0:
        cards_adj = -1
        notes.append(f'🟡 裁判{ref.name}出牌偏多({ref.avg_yellows:.1f}张/场)')
        if home_is_tech: confidence_adj -= 1
        elif home_is_phys: confidence_adj += 1
        ou_adj -= 0.04
    elif ref.avg_yellows <= 2.5:
        cards_adj = 1
        notes.append(f'🟢 裁判{ref.name}执法宽松({ref.avg_yellows:.1f}张/场)')
        ou_adj += 0.02

    # 2. 点球频率
    if ref.pen_given_per_match >= 0.3:
        notes.append(f'⚽ 点球偏多({ref.pen_given_per_match:.1f}/场)·禁区内需谨慎')
        ou_adj += 0.05

    # 3. 红牌频率
    if ref.avg_reds >= 0.3:
        notes.append(f'🟥 红牌风险偏高({ref.avg_reds:.1f}/场)')

    # 4. 对比赛风格的影响
    if ref.strictness in ('strict', 'very_strict'):
        notes.append(f'严格执法: 比赛中断多·定位球机会↑·对控球方不利')
        ou_adj -= 0.03
    elif ref.strictness == 'lenient':
        notes.append(f'宽松执法: 比赛流畅·身体对抗允许·对技术队有利')
        ou_adj += 0.02

    # 综合: 无差异化时使用基础card_adj
    if confidence_adj == 0:
        if cards_adj <= -3:
            confidence_adj = -2
        elif cards_adj >= 1:
            confidence_adj = 0

    notes.append(ref.style_impact)

    return {
        'referee': ref,
        'over_under_adj': ou_adj,
        'confidence_adj': confidence_adj,
        'card_risk': ref.strictness,
        'style_impact': ref.style_impact,
        'notes': notes,
    }


def get_card_probability_adjustment(match_name: str) -> float:
    """
    获取红黄牌概率调整 (-5 to +5)
    正数=牌少(流畅), 负数=牌多(碎片化)
    """
    ref = get_referee(match_name)
    if not ref:
        return 0

    # 基准3.5张/场, 每偏差0.5张调整1
    return (3.5 - ref.avg_yellows) * 0.5


# ── 独立测试 ──
if __name__ == '__main__':
    test_matches = ['法国VS塞内加尔', '伊拉克VS挪威', '阿根廷VS阿尔及利亚', '奥地利VS约旦']

    for mn in test_matches:
        parts = mn.split('VS')
        home, away = parts[0], parts[1]

        result = analyze_referee_impact(mn, home, away)
        ref = result['referee']
        print(f"\n{'='*50}")
        print(f"  🟨 {mn}")
        if ref:
            print(f"  裁判: {ref.name} ({ref.nationality}·{ref.confederation})")
            print(f"  场均黄牌: {ref.avg_yellows:.1f} | 场均红牌: {ref.avg_reds:.1f} | 场均犯规: {ref.avg_fouls:.0f}")
            print(f"  执法风格: {ref.strictness} | VAR使用: {ref.var_usage}")
            print(f"  大赛经验: {ref.experience_years}年 | 曾执法: {', '.join(ref.notable_matches[:2])}")
            for n in result['notes']:
                print(f"    → {n}")
            print(f"  置信度调整: {result['confidence_adj']:+d}% | 大小球修正: {result['over_under_adj']:+.2f}")
        else:
            print(f"  裁判: 未指派")

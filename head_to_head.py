"""
V2.10 历史交锋 & 球队恩怨分析
评估: 历史战绩·心理优势·风格克制·恩怨加成
依赖: match_context.py (球队名映射)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class H2HRecord:
    """两队历史交锋记录"""
    home: str
    away: str
    total_matches: int
    home_wins: int
    draws: int
    away_wins: int
    home_goals: int
    away_goals: int
    last_meeting: str          # '2024-03-15'
    last_result: str           # '法国2-1塞内加尔'
    notable_matches: List[str] = field(default_factory=list)  # 经典比赛
    rivalry_level: str = 'none'  # 'none'|'low'|'medium'|'high'|'historic'
    psychological_edge: str = ''  # 心理优势方


# ── 历史交锋数据库 ──

H2H_DB: Dict[str, H2HRecord] = {}

def _init_h2h():
    """初始化历史交锋数据"""
    global H2H_DB
    if H2H_DB:
        return

    records = [
        # ═══ 当前比赛日 ═══
        H2HRecord(
            home='法国', away='塞内加尔', total_matches=1, home_wins=1, draws=0, away_wins=0,
            home_goals=1, away_goals=0, last_meeting='2002-05-31', last_result='法国0-1塞内加尔',
            notable_matches=[],
            rivalry_level='none', psychological_edge='',
        ),
        H2HRecord(
            home='伊拉克', away='挪威', total_matches=0, home_wins=0, draws=0, away_wins=0,
            home_goals=0, away_goals=0, last_meeting='首次交锋', last_result='N/A',
            notable_matches=[], rivalry_level='none', psychological_edge='',
        ),
        H2HRecord(
            home='阿根廷', away='阿尔及利亚', total_matches=2, home_wins=1, draws=1, away_wins=0,
            home_goals=5, away_goals=3, last_meeting='2014-06-21', last_result='阿根廷2-1阿尔及利亚',
            notable_matches=['2014世界杯: 阿尔及利亚1-1逼平阿根廷·加时赛才落败', '阿尔及利亚打出德国级防守'],
            rivalry_level='medium', psychological_edge='阿尔及利亚',
        ),
        H2HRecord(
            home='奥地利', away='约旦', total_matches=0, home_wins=0, draws=0, away_wins=0,
            home_goals=0, away_goals=0, last_meeting='首次交锋', last_result='N/A',
            notable_matches=[], rivalry_level='none', psychological_edge='',
        ),

        # ═══ 其他重要交锋 ═══
        H2HRecord(
            home='巴西', away='摩洛哥', total_matches=3, home_wins=2, draws=0, away_wins=1,
            home_goals=5, away_goals=3, last_meeting='2023-03-25', last_result='摩洛哥2-1巴西',
            notable_matches=['2023友谊赛: 摩洛哥2-1巴西(历史首胜)', '摩洛哥29场不败始于巴西'],
            rivalry_level='medium', psychological_edge='摩洛哥',
        ),
        H2HRecord(
            home='德国', away='荷兰', total_matches=47, home_wins=18, draws=17, away_wins=12,
            home_goals=84, away_goals=73, last_meeting='2024-09-10', last_result='德国2-1荷兰',
            notable_matches=['1974世界杯决赛: 德国2-1荷兰', '欧陆经典宿敌', '近10场平分秋色'],
            rivalry_level='historic', psychological_edge='德国',
        ),
        H2HRecord(
            home='英格兰', away='克罗地亚', total_matches=11, home_wins=6, draws=2, away_wins=3,
            home_goals=24, away_goals=13, last_meeting='2024-06-16', last_result='英格兰1-0克罗地亚',
            notable_matches=['2018世界杯半决赛: 克罗地亚2-1逆转英格兰', '2021欧洲杯: 英格兰1-0复仇'],
            rivalry_level='high', psychological_edge='克罗地亚',
        ),
        H2HRecord(
            home='西班牙', away='佛得角', total_matches=1, home_wins=0, draws=1, away_wins=0,
            home_goals=0, away_goals=0, last_meeting='2026-06-14', last_result='西班牙0-0佛得角',
            notable_matches=['2026世界杯小组赛: 佛得角0-0逼平西班牙·EXTREME冷门'],
            rivalry_level='low', psychological_edge='佛得角',
        ),
        H2HRecord(
            home='意大利', away='乌拉圭', total_matches=6, home_wins=2, draws=3, away_wins=1,
            home_goals=7, away_goals=5, last_meeting='2026-06-14', last_result='意大利0-0乌拉圭',
            notable_matches=['历史交锋多以平局收场', '两队均以防守著称'],
            rivalry_level='medium', psychological_edge='',
        ),
        H2HRecord(
            home='阿根廷', away='巴西', total_matches=110, home_wins=42, draws=27, away_wins=41,
            home_goals=165, away_goals=162, last_meeting='2025-11-18', last_result='阿根廷1-0巴西',
            notable_matches=['南美德比·百年恩怨', '2021美洲杯决赛: 阿根廷1-0巴西', '梅西vs内马尔时代'],
            rivalry_level='historic', psychological_edge='阿根廷',
        ),
        H2HRecord(
            home='葡萄牙', away='西班牙', total_matches=40, home_wins=8, draws=17, away_wins=15,
            home_goals=45, away_goals=62, last_meeting='2024-06-05', last_result='葡萄牙1-2西班牙',
            notable_matches=['2018世界杯: 葡萄牙3-3西班牙(C罗帽子戏法)', '伊比利亚德比'],
            rivalry_level='historic', psychological_edge='西班牙',
        ),
        H2HRecord(
            home='墨西哥', away='美国', total_matches=77, home_wins=36, draws=16, away_wins=25,
            home_goals=142, away_goals=88, last_meeting='2025-10-14', last_result='墨西哥2-0美国',
            notable_matches=['北美经典德比·百年恩怨', '2026东道主德比'],
            rivalry_level='historic', psychological_edge='墨西哥',
        ),
        H2HRecord(
            home='美国', away='英格兰', total_matches=12, home_wins=3, draws=2, away_wins=7,
            home_goals=10, away_goals=37, last_meeting='2022-11-25', last_result='英格兰0-0美国',
            notable_matches=['1950世界杯: 美国1-0英格兰(世纪冷门)', '2022世界杯: 英格兰0-0美国'],
            rivalry_level='high', psychological_edge='美国',
        ),
        H2HRecord(
            home='法国', away='意大利', total_matches=42, home_wins=12, draws=12, away_wins=18,
            home_goals=46, away_goals=56, last_meeting='2024-03-23', last_result='法国0-0意大利',
            notable_matches=['2006世界杯决赛: 意大利点球胜(齐达内头顶)', '欧洲经典豪门恩怨'],
            rivalry_level='historic', psychological_edge='意大利',
        ),
        # ═══ V2.10 6/15回测 ═══
        H2HRecord(
            home='德国', away='库拉索', total_matches=0, home_wins=0, draws=0, away_wins=0,
            home_goals=0, away_goals=0, last_meeting='首次交锋', last_result='N/A',
            notable_matches=[], rivalry_level='none', psychological_edge='',
        ),
        H2HRecord(
            home='荷兰', away='日本', total_matches=3, home_wins=2, draws=1, away_wins=0,
            home_goals=6, away_goals=2, last_meeting='2022-11-25', last_result='荷兰2-0日本',
            notable_matches=['2022世界杯: 荷兰2-0日本', '日本从未赢过荷兰'],
            rivalry_level='low', psychological_edge='荷兰',
        ),
        H2HRecord(
            home='科特迪瓦', away='厄瓜多尔', total_matches=0, home_wins=0, draws=0, away_wins=0,
            home_goals=0, away_goals=0, last_meeting='首次交锋', last_result='N/A',
            notable_matches=[], rivalry_level='none', psychological_edge='',
        ),
        H2HRecord(
            home='瑞典', away='突尼斯', total_matches=1, home_wins=1, draws=0, away_wins=0,
            home_goals=1, away_goals=0, last_meeting='2018-06-23', last_result='瑞典1-0突尼斯',
            notable_matches=['2018世界杯: 瑞典1-0突尼斯'],
            rivalry_level='low', psychological_edge='瑞典',
        ),
    ]

    for r in records:
        key = _make_key(r.home, r.away)
        H2H_DB[key] = r


def _make_key(home: str, away: str) -> str:
    return f'{home}###{away}'


def get_h2h(home: str, away: str) -> Optional[H2HRecord]:
    """
    查询两队历史交锋
    支持双向查询
    """
    _init_h2h()
    key = _make_key(home, away)
    if key in H2H_DB:
        return H2H_DB[key]
    # 反向查询
    rev_key = _make_key(away, home)
    if rev_key in H2H_DB:
        r = H2H_DB[rev_key]
        # 交换主客
        return H2HRecord(
            home=r.away, away=r.home,
            total_matches=r.total_matches,
            home_wins=r.away_wins, draws=r.draws, away_wins=r.home_wins,
            home_goals=r.away_goals, away_goals=r.home_goals,
            last_meeting=r.last_meeting, last_result=r.last_result,
            notable_matches=r.notable_matches,
            rivalry_level=r.rivalry_level,
            psychological_edge=r.psychological_edge,
        )
    return None


def analyze_h2h_impact(home: str, away: str) -> dict:
    """
    分析历史交锋对比赛的影响
    Returns:
        {'h2h': H2HRecord or None, 'impact_score': float,
         'confidence_adj': float, 'underdog_boost': float, 'notes': []}
    """
    h2h = get_h2h(home, away)

    if not h2h or h2h.total_matches == 0:
        return {
            'h2h': None, 'impact_score': 0, 'confidence_adj': 0,
            'underdog_boost': 0, 'notes': ['两队无历史交锋记录'],
        }

    notes = []
    impact = 0
    underdog_boost = 0

    # 1. 心理优势
    if h2h.psychological_edge:
        edge_team = h2h.psychological_edge
        if edge_team == home:
            notes.append(f'{home}有心理优势 (历史交锋占优)')
            impact += 1
        elif edge_team == away:
            notes.append(f'{away}有心理优势 (历史交锋占优)')
            impact -= 1

    # 2. 冷门传统
    if h2h.rivalry_level in ('historic', 'high'):
        # 检查是否有弱队爆冷史
        for nm in h2h.notable_matches:
            if '爆冷' in nm or '逼平' in nm or '逆转' in nm or '世纪冷门' in nm:
                notes.append(f'⚡ 历史爆冷基因: {nm[:50]}...')
                underdog_boost += 1
                break

    # 3. 首次交锋 → 更多不确定性 → 微弱降权
    if h2h.last_meeting == '首次交锋':
        impact -= 0.5
        notes.append('首次交锋·缺乏历史参照·不确定性↑')

    # 4. 宿敌加成 → 比赛更激烈
    if h2h.rivalry_level == 'historic':
        notes.append('🔥 历史宿敌·比赛强度可能超出常规')
        impact += 0.5 if h2h.psychological_edge == home else (-0.5 if h2h.psychological_edge == away else 0)

    # 5. 近期交锋结果 (最近一场)
    if h2h.last_result != 'N/A' and h2h.last_result != '首次交锋':
        notes.append(f'上次交锋: {h2h.last_result}')

    # 综合调整
    if underdog_boost >= 1:
        confidence_adj = -3  # 降权 (冷门风险)
    elif impact >= 1:
        confidence_adj = 2
    elif impact <= -1:
        confidence_adj = -2
    else:
        confidence_adj = 0

    return {
        'h2h': h2h,
        'impact_score': impact,
        'confidence_adj': confidence_adj,
        'underdog_boost': underdog_boost,
        'notes': notes,
    }


# ── 独立测试 ──
if __name__ == '__main__':
    test_pairs = [
        ('法国', '塞内加尔'), ('伊拉克', '挪威'),
        ('阿根廷', '阿尔及利亚'), ('奥地利', '约旦'),
        ('巴西', '摩洛哥'), ('英格兰', '克罗地亚'),
        ('西班牙', '佛得角'), ('美国', '英格兰'),
    ]

    for home, away in test_pairs:
        print(f"\n{'='*50}")
        result = analyze_h2h_impact(home, away)
        h2h = result['h2h']
        if h2h:
            print(f"  ⚔️ {home} vs {away}")
            print(f"  总交锋: {h2h.total_matches}场 | 主{h2h.home_wins}胜/{h2h.draws}平/客{h2h.away_wins}胜")
            print(f"  进球: {h2h.home_goals}-{h2h.away_goals}")
            print(f"  恩怨等级: {h2h.rivalry_level}")
            print(f"  心理优势: {h2h.psychological_edge or '无'}")
            print(f"  上次: {h2h.last_result}")
            for n in result['notes']:
                print(f"    → {n}")
            print(f"  影响分: {result['impact_score']:+.1f} | 置信度调整: {result['confidence_adj']:+d}%")
        else:
            print(f"  {home} vs {away}: 无交锋数据")

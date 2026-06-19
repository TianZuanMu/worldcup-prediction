"""
V2.9 首发阵容修正
激活条件: 赛前60-90分钟 (首发公布时间)
功能: 核心缺阵检测·阵型变动·置信度修正
依赖: match_context.py (赛程+时间)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone


# ── 阵容数据结构 ──

@dataclass
class LineupData:
    team: str
    formation: str = '4-4-2'
    starting_xi: List[str] = field(default_factory=list)
    key_absences: List[str] = field(default_factory=list)
    surprise_inclusions: List[str] = field(default_factory=list)
    fetched_at: str = ''
    source: str = 'unavailable'      # web_search / manual / expected / unavailable
    is_confirmed: bool = False       # True = 官方首发


@dataclass
class LineupImpact:
    home_impact: float = 0.0          # -10 to +10
    away_impact: float = 0.0
    confidence_adj: float = 0.0       # -15 to 0 (总是负或零)
    home_adjustments: List[str] = field(default_factory=list)
    away_adjustments: List[str] = field(default_factory=list)
    summary: str = '首发数据不可用'


# ── 预期首发 & 核心球员 (32队) ──

EXPECTED_XI: Dict[str, dict] = {
    '法国': {
        'formation': '4-2-3-1',
        'key_players': ['Mbappe', 'Griezmann', 'Tchouameni', 'Kounde', 'Maignan'],
        'typical_xi': ['Maignan', 'Hernandez', 'Upamecano', 'Konate', 'Kounde',
                       'Tchouameni', 'Rabiot', 'Griezmann', 'Dembele', 'Mbappe', 'Kolo Muani'],
    },
    '塞内加尔': {
        'formation': '4-3-3',
        'key_players': ['Mane', 'Koulibaly', 'Jakson', 'Mendy'],
        'typical_xi': ['Mendy', 'Jakobs', 'Koulibaly', 'Niakhate', 'Sabaly',
                       'Gueye', 'Kouyate', 'Sarr', 'Mane', 'Jakson', 'Dia'],
    },
    '伊拉克': {
        'formation': '4-4-2',
        'key_players': ['Ali Jassim', 'Hussein Ali'],
        'typical_xi': ['Hassan', 'Adnan', 'Natiq', 'Ibrahim', 'Ali',
                       'Jassim', 'Amari', 'Bayesh', 'Hussein', 'Hamadi', 'Iqbal'],
    },
    '挪威': {
        'formation': '4-3-3',
        'key_players': ['Haaland', 'Odegaard', 'Sorloth', 'Berge'],
        'typical_xi': ['Nyland', 'Meling', 'Ostigard', 'Ajer', 'Ryerson',
                       'Berge', 'Odegaard', 'Aursnes', 'Sorloth', 'Haaland', 'Bob'],
    },
    '阿根廷': {
        'formation': '4-3-3',
        'key_players': ['Messi', 'Alvarez', 'Fernandez', 'Romero', 'Martinez'],
        'typical_xi': ['Martinez', 'Acuna', 'Romero', 'Otamendi', 'Molina',
                       'Fernandez', 'Mac Allister', 'De Paul', 'Alvarez', 'Messi', 'Garnacho'],
    },
    '阿尔及利亚': {
        'formation': '4-2-3-1',
        'key_players': ['Mahrez', 'Bennacer', 'Ait-Nouri', 'Amoura'],
        'typical_xi': ['Mandrea', 'Ait-Nouri', 'Bensebaini', 'Touba', 'Atal',
                       'Bennacer', 'Zerrouki', 'Mahrez', 'Chaibi', 'Amoura', 'Bounedjah'],
    },
    '奥地利': {
        'formation': '4-2-3-1',
        'key_players': ['Sabitzer', 'Laimer', 'Baumgartner', 'Alaba', 'Schlager'],
        'typical_xi': ['Schlager', 'Wober', 'Lienhart', 'Alaba', 'Posch',
                       'Seiwald', 'Laimer', 'Sabitzer', 'Baumgartner', 'Arnautovic', 'Gregoritsch'],
    },
    '约旦': {
        'formation': '4-4-2',
        'key_players': ['Al-Taamari', 'Olwan'],
        'typical_xi': ['Al-Layla', 'Naseeb', 'Al-Arab', 'Al-Ajalin', 'Haddad',
                       'Al-Taamari', 'Rashdan', 'Ayed', 'Olwan', 'Al-Naimat', 'Rizq'],
    },
    # ── 补充其他关键球队 ──
    '巴西': {
        'formation': '4-3-3',
        'key_players': ['Vinicius Jr', 'Rodrygo', 'Marquinhos', 'Alisson', 'Guimaraes'],
        'typical_xi': ['Alisson', 'Arana', 'Marquinhos', 'Militao', 'Vanderson',
                       'Guimaraes', 'Joelinton', 'Paqueta', 'Vinicius Jr', 'Rodrygo', 'Endrick'],
    },
    '德国': {
        'formation': '4-2-3-1',
        'key_players': ['Musiala', 'Wirtz', 'Kimmich', 'Rudiger', 'Ter Stegen'],
        'typical_xi': ['Ter Stegen', 'Raum', 'Rudiger', 'Schlotterbeck', 'Kimmich',
                       'Andrich', 'Gross', 'Wirtz', 'Musiala', 'Sane', 'Havertz'],
    },
    '英格兰': {
        'formation': '4-2-3-1',
        'key_players': ['Kane', 'Bellingham', 'Foden', 'Rice', 'Saka'],
        'typical_xi': ['Pickford', 'Shaw', 'Stones', 'Guehi', 'James',
                       'Rice', 'Bellingham', 'Foden', 'Palmer', 'Saka', 'Kane'],
    },
    '西班牙': {
        'formation': '4-3-3',
        'key_players': ['Lamine Yamal', 'Pedri', 'Rodri', 'Carvajal', 'Olmo'],
        'typical_xi': ['Simon', 'Cucurella', 'Le Normand', 'Torres', 'Carvajal',
                       'Rodri', 'Pedri', 'Ruiz', 'Williams', 'Olmo', 'Lamine Yamal'],
    },
    '葡萄牙': {
        'formation': '4-3-3',
        'key_players': ['C. Ronaldo', 'Bruno Fernandes', 'Leao', 'Dias', 'Silva'],
        'typical_xi': ['Costa', 'Mendes', 'Dias', 'Inacio', 'Dalot',
                       'Vitinha', 'Fernandes', 'Neves', 'Leao', 'Ronaldo', 'Silva'],
    },
    '意大利': {
        'formation': '4-3-3',
        'key_players': ['Donnarumma', 'Barella', 'Bastoni', 'Chiesa', 'Tonali'],
        'typical_xi': ['Donnarumma', 'Dimarco', 'Bastoni', 'Buongiorno', 'Di Lorenzo',
                       'Barella', 'Tonali', 'Frattesi', 'Chiesa', 'Scamacca', 'Raspadori'],
    },
    '荷兰': {
        'formation': '4-3-3',
        'key_players': ['Van Dijk', 'Gakpo', 'De Jong', 'Simons', 'Dumfries'],
        'typical_xi': ['Verbruggen', 'Ake', 'Van Dijk', 'De Vrij', 'Dumfries',
                       'De Jong', 'Reijnders', 'Simons', 'Gakpo', 'Depay', 'Malen'],
    },
    '比利时': {
        'formation': '4-2-3-1',
        'key_players': ['De Bruyne', 'Lukaku', 'Doku', 'Onana'],
        'typical_xi': ['Casteels', 'De Cuyper', 'Faes', 'Debast', 'Meunier',
                       'Onana', 'Tielemans', 'Doku', 'De Bruyne', 'Trossard', 'Lukaku'],
    },
    '克罗地亚': {
        'formation': '4-3-3',
        'key_players': ['Modric', 'Gvardiol', 'Kovacic', 'Perisic'],
        'typical_xi': ['Livakovic', 'Gvardiol', 'Sutalo', 'Erlic', 'Stanisic',
                       'Kovacic', 'Modric', 'Brozovic', 'Perisic', 'Kramaric', 'Majer'],
    },
    '乌拉圭': {
        'formation': '4-2-3-1',
        'key_players': ['Valverde', 'Araujo', 'Nunez', 'Bentancur'],
        'typical_xi': ['Rochet', 'Olivera', 'Araujo', 'Caceres', 'Varela',
                       'Ugarte', 'Valverde', 'Bentancur', 'Pellistri', 'Nunez', 'Araujo'],
    },
    '摩洛哥': {
        'formation': '4-3-3',
        'key_players': ['Hakimi', 'Amrabat', 'En-Nesyri', 'Ziyech'],
        'typical_xi': ['Bono', 'Mazraoui', 'Aguerd', 'Saiss', 'Hakimi',
                       'Amrabat', 'Ounahi', 'Ziyech', 'Boufal', 'En-Nesyri', 'Harit'],
    },
    '美国': {
        'formation': '4-3-3',
        'key_players': ['Pulisic', 'McKennie', 'Reyna', 'Turner', 'Balogun'],
        'typical_xi': ['Turner', 'Robinson', 'Ream', 'Richards', 'Dest',
                       'Adams', 'McKennie', 'Reyna', 'Pulisic', 'Balogun', 'Weah'],
    },
    '哥伦比亚': {
        'formation': '4-3-3',
        'key_players': ['Luis Diaz', 'James Rodriguez', 'Mina'],
        'typical_xi': ['Vargas', 'Mojica', 'Lucumi', 'Mina', 'Munoz',
                       'Lerma', 'Carrascal', 'James', 'Diaz', 'Cordoba', 'Duran'],
    },
    '日本': {
        'formation': '4-2-3-1',
        'key_players': ['Mitoma', 'Kubo', 'Endo', 'Tomiyasu'],
        'typical_xi': ['Suzuki', 'Ito', 'Tomiyasu', 'Itakura', 'Sugawara',
                       'Endo', 'Morita', 'Kubo', 'Minamino', 'Mitoma', 'Ueda'],
    },
    '韩国': {
        'formation': '4-4-2',
        'key_players': ['Son Heung-min', 'Kim Min-jae', 'Hwang Hee-chan', 'Lee Kang-in'],
        'typical_xi': ['Kim Seung-gyu', 'Kim Jin-su', 'Kim Min-jae', 'Kwon Kyung-won', 'Kim Moon-hwan',
                       'Son Heung-min', 'Hwang In-beom', 'Paik Seung-ho', 'Lee Kang-in',
                       'Cho Gue-sung', 'Hwang Hee-chan'],
    },
    '埃及': {
        'formation': '4-3-3',
        'key_players': ['Salah', 'Marmoush', 'Hegazi'],
        'typical_xi': ['Shenawy', 'Fotouh', 'Hegazi', 'Abdelmonem', 'Hany',
                       'Fathi', 'Elneny', 'Zizo', 'Salah', 'Marmoush', 'Mohamed'],
    },
    '墨西哥': {
        'formation': '4-3-3',
        'key_players': ['Gimenez', 'Lozano', 'Ochoa'],
        'typical_xi': ['Ochoa', 'Gallardo', 'Vasquez', 'Montes', 'Sanchez',
                       'Alvarez', 'Chavez', 'Rodriguez', 'Lozano', 'Gimenez', 'Huerta'],
    },
    '加拿大': {
        'formation': '4-4-2',
        'key_players': ['Davies', 'David', 'Buchanan'],
        'typical_xi': ['Crepeau', 'Davies', 'Cornelius', 'Miller', 'Johnston',
                       'Buchanan', 'Eustaquio', 'Kone', 'Millar', 'David', 'Larin'],
    },
    '瑞士': {
        'formation': '4-2-3-1',
        'key_players': ['Akanji', 'Xhaka', 'Embolo', 'Ndoye'],
        'typical_xi': ['Sommer', 'Rodriguez', 'Akanji', 'Schar', 'Widmer',
                       'Xhaka', 'Freuler', 'Vargas', 'Rieder', 'Ndoye', 'Embolo'],
    },
    '土耳其': {
        'formation': '4-2-3-1',
        'key_players': ['Calhanoglu', 'Guler', 'Yildiz'],
        'typical_xi': ['Gunok', 'Kadioglu', 'Bardakci', 'Demiral', 'Celik',
                       'Calhanoglu', 'Ozcan', 'Guler', 'Yildiz', 'Akgun', 'Yilmaz'],
    },
    '塞尔维亚': {
        'formation': '3-5-2',
        'key_players': ['Mitrovic', 'Vlahovic', 'Milinkovic-Savic'],
        'typical_xi': ['Rajkovic', 'Pavlovic', 'Milenkovic', 'Veljkovic',
                       'Kostic', 'Milinkovic-Savic', 'Lukic', 'Tadic', 'Zivkovic',
                       'Mitrovic', 'Vlahovic'],
    },
    '科特迪瓦': {
        'formation': '4-3-3',
        'key_players': ['Haller', 'Kessie', 'Fofana'],
        'typical_xi': ['Fofana', 'Konan', 'Ndicka', 'Boly', 'Aurier',
                       'Kessie', 'Sangare', 'Fofana', 'Adingra', 'Haller', 'Pepe'],
    },
}


# ── 默认fallback ──
DEFAULT_XI = {
    'formation': '4-4-2',
    'key_players': [],
    'typical_xi': [],
}


def is_lineup_window(match_name: str) -> bool:
    """
    检查是否在首发公布窗口内 (赛前60-90分钟)
    返回 True 表示应该获取首发数据
    """
    from match_context import get_match as get_group_match

    m = get_group_match(match_name=match_name)
    if not m:
        return False

    try:
        utc_str = m.kickoff_utc.replace('Z', '+00:00')
        kickoff = datetime.fromisoformat(utc_str)
        now = datetime.now(timezone.utc)
        if kickoff.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        elif kickoff.tzinfo is None and now.tzinfo is not None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        minutes_to_ko = (kickoff - now).total_seconds() / 60

        # 赛前30-120分钟 → 激活 (FIFA规定赛前75分钟公布首发)
        return 30 <= minutes_to_ko <= 120
    except (ValueError, TypeError, AttributeError):
        return False


def minutes_to_kickoff(match_name: str) -> Optional[float]:
    """距开球的分钟数"""
    from match_context import get_match as get_group_match

    m = get_group_match(match_name=match_name)
    if not m:
        return None

    try:
        utc_str = m.kickoff_utc.replace('Z', '+00:00')
        kickoff = datetime.fromisoformat(utc_str)
        now = datetime.now(timezone.utc)
        return (kickoff - now).total_seconds() / 60
    except (ValueError, TypeError, AttributeError):
        return None


def get_expected_lineup(team: str) -> dict:
    """获取预期首发"""
    if team in EXPECTED_XI:
        return EXPECTED_XI[team]
    # 模糊匹配
    for key in EXPECTED_XI:
        if team in key or key in team:
            return EXPECTED_XI[key]
    return DEFAULT_XI


def compare_lineup(team: str, actual_xi: List[str] = None,
                   actual_formation: str = None) -> dict:
    """
    对比实际首发与预期首发
    Returns:
        {'absences': [...], 'formation_changed': bool, 'severity': 'low'|'medium'|'high'|'critical'}
    """
    expected = get_expected_lineup(team)
    key_players = expected.get('key_players', [])
    typical_xi = expected.get('typical_xi', [])
    expected_formation = expected.get('formation', '4-4-2')

    absences = []
    severity = 'low'

    if actual_xi:
        # 检查核心球员是否在首发中
        for kp in key_players:
            found = any(kp.lower() in p.lower() for p in actual_xi)
            if not found:
                absences.append(kp)
    else:
        # 无实际首发数据 → 无法对比
        return {'absences': [], 'formation_changed': False, 'severity': 'none',
                'note': '无实际首发数据'}

    formation_changed = False
    if actual_formation and actual_formation != expected_formation:
        formation_changed = True

    # 严重度判定
    star_count = len([a for a in absences if a in key_players[:3]])  # 前3核心
    total_absences = len(absences)

    if star_count >= 2:
        severity = 'critical'
    elif star_count >= 1 or total_absences >= 3:
        severity = 'high'
    elif total_absences >= 1 or formation_changed:
        severity = 'medium'

    return {
        'absences': absences,
        'formation_changed': formation_changed,
        'severity': severity,
        'star_absences': star_count,
        'total_absences': total_absences,
    }


def get_match_lineup_impact(match_name: str) -> LineupImpact:
    """
    获取一场比赛的阵容影响评估
    赛前60-90分钟窗口外 → 返回中性
    """
    parts = match_name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
    if len(parts) != 2:
        return LineupImpact()

    home = parts[0].strip()
    away = parts[1].strip()

    impact = LineupImpact()

    # 检查窗口
    mins = minutes_to_kickoff(match_name)
    in_window = is_lineup_window(match_name)

    if not in_window:
        if mins is not None and mins > 0:
            impact.summary = f'距开球{mins:.0f}分钟·未到首发公布窗口'
        elif mins is not None and mins < 0:
            impact.summary = '比赛已开始或已结束'
        else:
            impact.summary = '赛程数据不可用'
        return impact

    # 窗口内但没有实际数据 → 预期首发作为基准
    home_lineup = get_expected_lineup(home)
    away_lineup = get_expected_lineup(away)

    impact.summary = f'赛前{mins:.0f}分钟·使用预期首发(无实时数据)'
    impact.source = 'expected'

    # 检查是否有已知伤病 (从opponent_db或其他来源)
    # 这里简化: 无实时数据 → 返回中性
    impact.confidence_adj = 0

    return impact


def apply_lineup_changes(match_name: str, home_absences: List[str] = None,
                         away_absences: List[str] = None,
                         home_formation: str = None,
                         away_formation: str = None) -> LineupImpact:
    """
    手动应用阵容变动 (当有实际首发数据时调用)
    """
    parts = match_name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
    if len(parts) != 2:
        return LineupImpact()

    home = parts[0].strip()
    away = parts[1].strip()

    home_result = compare_lineup(home, actual_xi=home_absences, actual_formation=home_formation)
    away_result = compare_lineup(away, actual_xi=away_absences, actual_formation=away_formation)

    impact = LineupImpact()
    impact.source = 'manual'

    # 主队调整
    sev_map = {'none': 0, 'low': -1, 'medium': -3, 'high': -7, 'critical': -10}
    home_sev = home_result.get('severity', 'none')
    away_sev = away_result.get('severity', 'none')

    impact.home_impact = sev_map.get(home_sev, 0)
    impact.away_impact = sev_map.get(away_sev, 0)

    # 置信度调整 (只降不升, 上限-15%)
    conf_adj = impact.home_impact + impact.away_impact
    impact.confidence_adj = max(-15, min(0, conf_adj))

    # 调整说明
    if home_result['absences']:
        names = ', '.join(home_result['absences'][:3])
        impact.home_adjustments.append(f'{home}核心缺阵: {names} ({home_sev})')
    if home_result.get('formation_changed'):
        impact.home_adjustments.append(f'{home}阵型变动: {home_formation}')

    if away_result['absences']:
        names = ', '.join(away_result['absences'][:3])
        impact.away_adjustments.append(f'{away}核心缺阵: {names} ({away_sev})')
    if away_result.get('formation_changed'):
        impact.away_adjustments.append(f'{away}阵型变动: {away_formation}')

    impact.summary = f'主{home_sev}/客{away_sev}·置信度调整{impact.confidence_adj:+.0f}%'

    return impact


# ── 独立测试 ──
if __name__ == '__main__':
    test_matches = ['法国VS塞内加尔', '伊拉克VS挪威', '阿根廷VS阿尔及利亚', '奥地利VS约旦']

    for mn in test_matches:
        print(f"\n{'='*60}")
        parts = mn.split('VS')
        home, away = parts[0], parts[1]

        mins = minutes_to_kickoff(mn)
        in_win = is_lineup_window(mn)

        print(f"  👥 {mn}")
        print(f"  距开球: {mins:.0f}分钟" if mins else "  距开球: 未知")
        print(f"  首发窗口: {'✅ 是' if in_win else '❌ 否'}")

        impact = get_match_lineup_impact(mn)
        print(f"  状态: {impact.summary}")

        # 显示预期首发
        home_xi = get_expected_lineup(home)
        away_xi = get_expected_lineup(away)
        print(f"  {home} 预期: {home_xi['formation']} | 核心: {', '.join(home_xi['key_players'][:4])}")
        print(f"  {away} 预期: {away_xi['formation']} | 核心: {', '.join(away_xi['key_players'][:4])}")

        # 模拟一个核心缺阵的测试
        if home == '法国':
            test_impact = apply_lineup_changes(mn,
                home_absences=['Mbappe'], home_formation='4-4-2',
            )
            print(f"  [模拟] 法国Mbappe缺阵+变阵 → 调整{test_impact.confidence_adj:+.0f}%")
            for adj in test_impact.home_adjustments + test_impact.away_adjustments:
                print(f"    → {adj}")

"""
V2.13 赛程影响增强 — 小组出线形势 + 淘汰赛路径完整分析

V2.12及之前: 仅基础战意评分 + 模拟积分
V2.13新增:
  1. 自动加载实际赛果 (从回测DB) 替代模拟数据
  2. 净胜球场景分析: 需大胜 vs 小胜即可
  3. 淘汰赛路径投影: 当前排名对应的实际对手
  4. "避强"动力: 小组第2有时路径更优
  5. 已出线轮换风险: 已确保出线的球队可能留力
  6. 已淘汰球队的"荣誉之战"因子
  7. 同组另一场比赛对双方的间接影响

依赖: match_context.py + backtest/matches.json
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple  # noqa: F401
import json
from pathlib import Path
from config import CONF

from match_context import get_team_group, get_group_matches, TEAM_GROUPS

BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
MATCHES_FILE = BACKTEST_DIR / "matches.json"


# ══════════════════════════════════════════════════════════════
# 淘汰赛路径
# ══════════════════════════════════════════════════════════════

# 🆕 V3.34: 基于真实R32对阵规则更新 (来源: FIFA 2026官方 bracket)
KNOCKOUT_PATH = {
    # 头名 → 对手 (Match 74,75,76,77,79,80,81,82,84 + 推断)
    'A1': '3rd(C/E/F/H/I)',   # Match 79: A1 vs 3rd
    'B1': '3rd(?)',            # 缺失·暂用通用3rd
    'C1': 'F2',                # Match 76: C1 vs F2
    'D1': '3rd(B/E/F/I/J)',   # Match 81: D1 vs 3rd
    'E1': '3rd(A/B/C/D/F)',   # Match 74: E1 vs 3rd
    'F1': 'C2',                # Match 75: F1 vs C2
    'G1': '3rd(A/E/H/I/J)',   # Match 82: G1 vs 3rd
    'H1': 'J2',                # Match 84: H1 vs J2
    'I1': '3rd(C/D/F/G/H)',   # Match 77: I1 vs 3rd
    'J1': '3rd(?)',            # 缺失·暂用通用3rd
    'K1': 'H2',                # 推断: K1 vs H2
    'L1': '3rd(E/H/I/J/K)',   # Match 80: L1 vs 3rd
    # 次名 → 对手
    'A2': 'B2',                # Match 73: A2 vs B2
    'B2': 'A2',                # Match 73
    'C2': 'F1',                # Match 75: F1 vs C2 → C2 vs F1
    'D2': 'G2',                # 推断: D2 vs G2
    'E2': 'I2',                # Match 78: E2 vs I2
    'F2': 'C1',                # Match 76: C1 vs F2 → F2 vs C1
    'G2': 'D2',                # 推断: G2 vs D2
    'H2': 'K1',                # 推断: H2 vs K1
    'I2': 'E2',                # Match 78: I2 vs E2
    'J2': 'H1',                # Match 84: H1 vs J2 → J2 vs H1
    'K2': 'L2',                # Match 83: K2 vs L2
    'L2': 'K2',                # Match 83
}

# 强队列表 (用于评估淘汰赛对手强度)
STRONG_KNOCKOUT_TEAMS = {
    '法国', '阿根廷', '巴西', '英格兰', '西班牙', '德国', '葡萄牙', '荷兰',
    '意大利', '比利时', '克罗地亚', '乌拉圭',
}

# 🆕 V3.34: 基于真实R32对手难度重算 (对手越强分越高)
# A1→3rd(2) A2→瑞士(6.5) | B1→3rd(2) B2→韩国(5) | C1→日本(6.5) C2→荷兰(8.5)
# D1→3rd(2) D2→伊朗(4.5) | E1→3rd(2) E2→挪威(5.5) | F1→摩洛哥(7) F2→巴西(10)
# G1→3rd(2) G2→澳大利亚(4) | H1→奥地利(6) H2→哥伦比亚(7.5) | I1→3rd(2) I2→科特迪瓦(5)
# J1→3rd(2) J2→西班牙(9.5) | K1→佛得角(3) K2→克罗地亚(7) | L1→3rd(2) L2→葡萄牙(8.5)
GROUP_PATH_RATING = {
    # (pos1_difficulty, pos2_difficulty) — 0=easy, 10=hard
    'A': (2, 7),   # 3rd vs 瑞士 — 头名显著更优
    'B': (2, 5),   # 3rd vs 韩国
    'C': (7, 9),   # 日本 vs 荷兰 — 头名更优
    'D': (2, 5),   # 3rd vs 伊朗
    'E': (2, 6),   # 3rd vs 挪威
    'F': (7, 10),  # 摩洛哥 vs 巴西 — 次名极其凶险!
    'G': (2, 4),   # 3rd vs 澳大利亚
    'H': (6, 8),   # 奥地利 vs 哥伦比亚 — 头名略优
    'I': (2, 5),   # 3rd vs 科特迪瓦
    'J': (2, 10),  # 3rd vs 西班牙 — 🔥次名极其凶险! 最大头名动机
    'K': (3, 7),   # 佛得角 vs 克罗地亚 — 头名显著更优
    'L': (2, 9),   # 3rd vs 葡萄牙 — 次名极其凶险!
}


# ══════════════════════════════════════════════════════════════
# 积分表 (全局状态)
# ══════════════════════════════════════════════════════════════

GROUP_STANDINGS: Dict[str, Dict[str, dict]] = {}
_real_results_loaded = False


def _init_empty_standings():
    """初始化空积分表"""
    global GROUP_STANDINGS
    if GROUP_STANDINGS:
        return
    for grp in 'ABCDEFGHIJKL':
        GROUP_STANDINGS[grp] = {}
        teams = [t for t, g in TEAM_GROUPS.items() if g == grp]
        for t in teams:
            GROUP_STANDINGS[grp][t] = {'pts': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'played': 0}


def _set_result(group: str, home: str, away: str, home_goals: int, away_goals: int):
    """录入一场赛果到积分表"""
    if group not in GROUP_STANDINGS:
        GROUP_STANDINGS[group] = {}
    for t in [home, away]:
        if t not in GROUP_STANDINGS[group]:
            GROUP_STANDINGS[group][t] = {'pts': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'played': 0}

    GROUP_STANDINGS[group][home]['gf'] += home_goals
    GROUP_STANDINGS[group][home]['ga'] += away_goals
    GROUP_STANDINGS[group][home]['played'] += 1
    GROUP_STANDINGS[group][away]['gf'] += away_goals
    GROUP_STANDINGS[group][away]['ga'] += home_goals
    GROUP_STANDINGS[group][away]['played'] += 1

    if home_goals > away_goals:
        GROUP_STANDINGS[group][home]['pts'] += 3
    elif home_goals < away_goals:
        GROUP_STANDINGS[group][away]['pts'] += 3
    else:
        GROUP_STANDINGS[group][home]['pts'] += 1
        GROUP_STANDINGS[group][away]['pts'] += 1

    for t in [home, away]:
        s = GROUP_STANDINGS[group][t]
        s['gd'] = s['gf'] - s['ga']


def _load_actual_results():
    """
    仅从回测DB加载实际完赛结果。不使用任何模拟数据。
    积分表仅包含有真实赛果的比赛。
    """
    global _real_results_loaded, GROUP_STANDINGS
    if _real_results_loaded:
        return

    _init_empty_standings()

    if not MATCHES_FILE.exists():
        _real_results_loaded = True
        return

    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        matches = json.load(f)

    loaded = 0
    for m in matches:
        if m['actual']['result'] == 'pending':
            continue

        name = m['match_name']
        parts = name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
        if len(parts) != 2:
            continue

        home = parts[0].strip()
        away = parts[1].strip()
        score = m['actual']['score']

        # 🆕 V4.2: 队名归一化 — 消除"刚果(金)"="民主刚果"等别名重复
        from match_context import normalize_team_name
        home = normalize_team_name(home)
        away = normalize_team_name(away)

        try:
            hg, ag = map(int, score.split('-'))
        except (ValueError, AttributeError):
            continue

        grp = _find_group(home, away)
        if not grp:
            continue

        _set_result(grp, home, away, hg, ag)
        loaded += 1

    _real_results_loaded = True


def _find_group(home: str, away: str) -> Optional[str]:
    """根据对阵双方查找小组"""
    hg = get_team_group(home)
    ag = get_team_group(away)
    if hg and ag and hg == ag:
        return hg
    if hg:
        return hg
    if ag:
        return ag
    # 回退: 遍历所有小组查找
    for grp in 'ABCDEFGHIJKL':
        teams = [t for t, g in TEAM_GROUPS.items() if g == grp]
        if home in teams and away in teams:
            return grp
    return None


# ══════════════════════════════════════════════════════════════
# 增强场景分析
# ══════════════════════════════════════════════════════════════

def _get_standings_sorted(group: str) -> List[Tuple[str, dict]]:
    """获取小组排名 (按pts, gd, gf排序)"""
    if group not in GROUP_STANDINGS:
        return []
    # 🆕 V4.5 P3: 公平竞赛分占位 (第6排序键·数据源待接入)
    return sorted(
        GROUP_STANDINGS[group].items(),
        key=lambda x: (x[1]['pts'], x[1]['gd'], x[1]['gf'],
                       x[1].get('h2h_pts', 0), x[1].get('h2h_gd', 0),
                       x[1].get('fair_play', 0)),  # 🆕 占位·当前均为0
        reverse=True
    )


def _get_position(group: str, team: str) -> int:
    """获取当前排名"""
    sorted_teams = _get_standings_sorted(group)
    for i, (t, _) in enumerate(sorted_teams):
        if t == team:
            return i + 1
    return 1


def _get_remaining_match(group: str, team: str) -> Optional[dict]:
    """获取该队剩余的小组赛对手"""
    all_matches = get_group_matches(group)
    played_as = set()  # 已对阵的对手
    # 从积分表推断已对阵的对手 (played场次)
    if group in GROUP_STANDINGS and team in GROUP_STANDINGS[group]:
        played = GROUP_STANDINGS[group][team]['played']
    else:
        played = 0

    # 从赛程中找未进行的比赛
    for m in all_matches:
        if m.home == team or m.away == team:
            opponent = m.away if m.home == team else m.home
            # 检查这个对手是否已出现在积分表中
            if _count_matchup(group, team, opponent) == 0:
                return {'opponent': opponent, 'matchday': m.matchday, 'home': m.home == team}
    return None


def _count_matchup(group: str, team1: str, team2: str) -> int:
    """检查两队是否已有交锋记录 (通过积分表的played推断)"""
    # 简化: 检查两队played是否>=1 且 是相互的对手
    # 由于我们不存储对阵历史, 用played字段推断
    s1 = GROUP_STANDINGS.get(group, {}).get(team1, {})
    s2 = GROUP_STANDINGS.get(group, {}).get(team2, {})
    min_played = min(s1.get('played', 0), s2.get('played', 0))
    return min_played


# ═══ V4.2: H2H锁定检测 — 世界杯小组赛同分先比H2H ═══
_H2H_CACHE: Dict[str, Dict[str, str]] = {}  # {group: {team_pair: 'win'|'draw'|'loss'}}


def _build_h2h_cache():
    """从回测DB构建H2H结果缓存"""
    global _H2H_CACHE
    if _H2H_CACHE:
        return
    if not MATCHES_FILE.exists():
        return
    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        matches = json.load(f)
    for m in matches:
        if m['actual']['result'] == 'pending':
            continue
        name = m['match_name']
        parts = name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
        if len(parts) != 2:
            continue
        home, away = parts[0].strip(), parts[1].strip()
        # 🆕 V4.2: 队名归一化
        from match_context import normalize_team_name
        home = normalize_team_name(home)
        away = normalize_team_name(away)
        grp = _find_group(home, away)
        if not grp:
            continue
        try:
            hg, ag = map(int, m['actual']['score'].split('-'))
        except (ValueError, AttributeError):
            continue
        if grp not in _H2H_CACHE:
            _H2H_CACHE[grp] = {}
        if hg > ag:
            _H2H_CACHE[grp][f'{home}>{away}'] = 'win'
            _H2H_CACHE[grp][f'{away}<{home}'] = 'loss'
        elif ag > hg:
            _H2H_CACHE[grp][f'{away}>{home}'] = 'win'
            _H2H_CACHE[grp][f'{home}<{away}'] = 'loss'
        else:
            _H2H_CACHE[grp][f'{home}={away}'] = 'draw'
            _H2H_CACHE[grp][f'{away}={home}'] = 'draw'


def _check_position_locked(team: str, group: str, pos: int, pts: int) -> Tuple[bool, str]:
    """
    🆕 V4.2: 检查球队是否已通过H2H锁定当前排名。

    世界杯小组赛同分先比H2H(胜负关系), 再比GD。
    如果一队H2H胜所有可能追平积分的对手, 则排名已锁定。
    """
    _build_h2h_cache()
    h2h = _H2H_CACHE.get(group, {})
    standings = _get_standings_sorted(group)
    reason = ''

    # 收集可能追平积分的对手 (pts差≤3)
    threats = []
    for t, st in standings:
        if t == team:
            continue
        if st['pts'] + 3 >= pts:  # 最后一轮可追3分
            threats.append((t, st))

    if not threats:
        return True, '无对手可追平积分'

    # 检查H2H是否全胜所有威胁
    all_h2h_win = True
    for t, st in threats:
        key = f'{team}>{t}'
        result = h2h.get(key, '')
        if result != 'win':
            all_h2h_win = False
            if st['pts'] + 3 == pts:  # 可能同分
                if result == 'loss':
                    return False, f'H2H负于{t}·若同分排名会掉'
                elif result == 'draw':
                    return False, f'H2H平{t}·若同分需比GD'
                else:
                    return False, f'未与{t}交手或结果未知'

    if all_h2h_win and threats:
        threat_names = ', '.join(t for t, _ in threats)
        reason = f'H2H胜{threat_names}→排名已锁定'
        return True, reason

    return False, ''


def determine_scenario_enhanced(team: str, group: str, matchday: int) -> dict:
    """
    增强版场景分析 (V2.13 + V4.2 H2H锁定)

    Returns:
        {
            'scenario': str,
            'motivation_base': float (0-10),
            'need_goals': bool,        # 是否需要刷净胜球
            'rotation_risk': float,    # 轮换风险0-1
            'knockout_opponent': str,  # 当前排名的淘汰赛对手
            'alt_path_better': bool,   # 第二名路径是否更优
            'detail': str,
        }
    """
    _load_actual_results()

    pos = _get_position(group, team)
    s = GROUP_STANDINGS.get(group, {}).get(team, {'pts': 0, 'gd': 0, 'gf': 0, 'ga': 0, 'played': 0})
    pts = s['pts']
    gd = s['gd']
    played = s['played']

    standings = _get_standings_sorted(group)

    result = {
        'scenario': 'undecided',
        'motivation_base': 6,
        'need_goals': False,
        'rotation_risk': 0.0,
        'knockout_opponent': _get_knockout_opponent(group, pos),
        'alt_path_better': _check_alt_path_better(group, pos),
        'detail': '',
    }

    if matchday == 1:
        result['scenario'] = 'undecided'
        result['motivation_base'] = 6
        result['detail'] = f'{team}: MD1·全力争胜 ({pos}位·{pts}分)'

    elif matchday == 2:
        if pts >= 6:
            result['scenario'] = 'almost_qualified'
            result['motivation_base'] = 4.5
            result['rotation_risk'] = 0.15
            result['detail'] = f'{team}: 接近出线·巩固即可 ({pos}位·{pts}分·GD{gd:+d})'
        elif pts == 0:
            result['scenario'] = 'near_eliminated'
            result['motivation_base'] = 7.5
            result['detail'] = f'{team}: 濒临淘汰·背水一战 ({pos}位·{pts}分·需全胜)'
        elif pts == 3:
            result['scenario'] = 'undecided'
            result['motivation_base'] = 7
            result['detail'] = f'{team}: 需拿分确保主动 ({pos}位·{pts}分)'
        else:
            result['scenario'] = 'undecided'
            result['motivation_base'] = 6
            result['detail'] = f'{team}: 出线未定 ({pos}位·{pts}分)'

        # 净胜球需求: 同分时GD决定排名
        if len(standings) >= 2:
            # 检查是否与前后球队同分或接近
            for i, (t, st) in enumerate(standings):
                if t == team:
                    if i > 0:
                        above = standings[i-1]
                        if above[1]['pts'] == pts and above[1]['gd'] > gd:
                            result['need_goals'] = True
                            result['detail'] += f' | 需追GD: {above[0]}(GD{above[1]["gd"]:+d})'
                    if i < len(standings) - 1:
                        below = standings[i+1]
                        if below[1]['pts'] == pts and below[1]['gd'] < gd:
                            result['detail'] += f' | GD领先{below[0]}'
                    break

    elif matchday == 3:
        if len(standings) >= 3:
            others = [(t, st) for t, st in standings if t != team]
            max_other_pts = max(st['pts'] for _, st in others)

            if pts >= 6 and pts > max_other_pts + 2:
                # 🆕 V4.2: 检查是否已通过H2H锁定当前排名
                pos_locked, lock_reason = _check_position_locked(team, group, pos, pts)
                if pos_locked:
                    result['scenario'] = 'position_locked'
                    result['motivation_base'] = 2.0
                    result['rotation_risk'] = 0.8
                    result['detail'] = f'{team}: 已锁定第{pos}名·可全轮换 ({lock_reason})'
                else:
                    result['scenario'] = 'already_qualified'
                    result['motivation_base'] = 3.5
                    result['rotation_risk'] = 0.5
                    result['detail'] = f"{team}: 已确保出线·需保排名 ({pos}位·{pts}分·{lock_reason or 'H2H未锁定'})"
            elif pts == 0 and max_other_pts >= 6:
                # 🆕 V4.5 P1: 第三名晋级概率替代二值判断
                third_prob = _estimate_third_place_prob(team, group)
                mapping = _map_prob_to_motivation(third_prob)
                result['scenario'] = 'must_win_best_third'
                result['motivation_base'] = mapping['motivation_base']
                result['need_goals'] = True
                result['detail'] = f'{team}: 必须赢球+刷净胜球·争最佳第3名 ({pos}位·{pts}分·晋级概率{third_prob:.0f}%·{mapping["label"]})'
            elif pts == 1 and max_other_pts >= 6:
                third_prob = _estimate_third_place_prob(team, group)
                mapping = _map_prob_to_motivation(third_prob)
                result['scenario'] = 'must_win_best_third'
                result['motivation_base'] = mapping['motivation_base']
                result['need_goals'] = True
                result['detail'] = f'{team}: 必须赢球·最佳第3名 ({pos}位·{pts}分·晋级概率{third_prob:.0f}%·{mapping["label"]})'
            elif pts >= 3 and pts + 3 > max_other_pts:
                # 🆕 V4.5: 检查是否已确保前3 (48队赛制·第3名大概率晋级)
                # 如果4th名最大可能分数 ≤ 当前分数 → 已锁定前3
                min_pts_for_top3 = 0
                if len(standings) >= 4:
                    fourth = standings[3]
                    min_pts_for_top3 = fourth[1]['pts'] + 3  # 第4名最多再拿3分
                already_top3 = (len(standings) >= 4 and pts > min_pts_for_top3)

                if already_top3:
                    # 已确保前3但排名未锁定·需评估L2 vs L3路径
                    result['scenario'] = 'top3_locked'
                    result['motivation_base'] = 5.0  # 高于already_qualified·低于must_win
                    result['rotation_risk'] = 0.3
                    result['detail'] = f'{team}: 已确保前3·排名未锁定 ({pos}位·{pts}分·可争L1或L3)'
                else:
                    result['scenario'] = 'draw_enough'
                    result['motivation_base'] = 7
                    result['detail'] = f'{team}: 平局即可出线 ({pos}位·{pts}分)'
            else:
                result['scenario'] = 'must_win'
                result['motivation_base'] = 10
                result['need_goals'] = True
                result['detail'] = f'{team}: 必须赢球 ({pos}位·{pts}分·需刷GD)'

    # 🆕 V4.5: 路径倒挂修正 — 低排名反而有更优淘汰赛路径
    if matchday == 3:
        path_info = _is_path_inverted(group)
        if path_info['inverted']:
            if result['scenario'] == 'draw_enough' and pos == 3:
                # 平局=L3最优路径·赢了反而落入L2地狱
                result['motivation_base'] = 4.0
                result['detail'] += f' | 平局=L3最优路径(难度{path_info["l3"]:.0f})·赢球落入L2(难度{path_info["l2"]:.0f})'
            elif result['scenario'] == 'must_win' and pos == 3:
                # 必须赢但赢了可能路径更差·先确保出线再考虑
                result['motivation_base'] = 8.0
                result['detail'] += f' | 赢球=L2(难度{path_info["l2"]:.0f}>L3难度{path_info["l3"]:.0f})·路径更差但必须先确保出线'

    return result


def _get_knockout_opponent(group: str, pos: int) -> str:
    """获取当前排名对应的淘汰赛对手"""
    if pos == 3:
        # 🆕 V4.5 P2: 第三名对手取决于8/12晋级组合·用期望难度
        diff = _estimate_third_path_difficulty(group)
        return f'最佳第三(期望难度{diff:.0f}/10)'
    key = f'{group}{pos}'
    return KNOCKOUT_PATH.get(key, '未知')


def _check_alt_path_better(group: str, current_pos: int) -> bool:
    """
    检查另一条出线路径是否更优。
    例如: 小组第2的对手比小组第1的对手更容易 → True
    """
    if current_pos not in (1, 2):
        return False

    alt_pos = 2 if current_pos == 1 else 1
    rating = GROUP_PATH_RATING.get(group, (5, 5))
    current_difficulty = rating[current_pos - 1]
    alt_difficulty = rating[alt_pos - 1]

    return alt_difficulty < current_difficulty - 1  # 至少差2分才算显著


# ══════════════════════════════════════════════════════════════
# 🆕 V4.5: 小组第三晋级概率 + 路径难度
# ══════════════════════════════════════════════════════════════

def _estimate_third_place_prob(team: str, group: str) -> float:
    """
    🆕 V4.5 P1: 估算球队以小组第三晋级的概率 (0-100%).

    方法: 静态快照 — 基于已完赛数据比较该队 vs 其他11组第三名。
    不模拟剩余比赛，仅做"如果现在是第三·排第几"的排序。

    Returns:
        0-100 概率值。前两名锁定者返回0。
    """
    _load_actual_results()

    pos = _get_position(group, team)
    # 前两名 → 不参与第三名竞争
    if pos <= 2:
        return 0.0

    s = GROUP_STANDINGS.get(group, {}).get(team, {'pts': 0, 'gd': 0, 'gf': 0})
    pts = s['pts']
    gd = s['gd']
    gf = s['gf']

    # 收集全部12组的第三名数据
    all_thirds = []
    for grp in 'ABCDEFGHIJKL':
        standings = _get_standings_sorted(grp)
        if len(standings) >= 3:
            third_team, third_st = standings[2]  # index 2 = 第三名
            all_thirds.append({
                'team': third_team,
                'group': grp,
                'pts': third_st['pts'],
                'gd': third_st['gd'],
                'gf': third_st['gf'],
                'played': third_st['played'],
            })

    if not all_thirds:
        return 50.0  # 无数据·中性

    # 按 pts → gd → gf 排序 (第三名虚拟积分榜)
    all_thirds.sort(key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)

    # 找到该队排名
    rank = 13  # default: last
    for i, t in enumerate(all_thirds):
        if t['team'] == team and t['group'] == group:
            rank = i + 1
            break

    # 🆕 V4.5: 边界拦截 — 已完赛3场且排名>8 → 0%
    if s.get('played', 0) >= 3 and rank > 8:
        return 0.0

    # 静态概率: 排名在前8 → 高概率; 排名在后4 → 低概率
    if rank <= 6:
        return 85.0
    elif rank <= 8:
        return 65.0
    elif rank <= 9:
        return 35.0
    elif rank <= 10:
        return 15.0
    else:
        return 5.0


def _estimate_third_path_difficulty(group: str) -> float:
    """
    🆕 V4.5 P2: 估算小组第三晋级后的期望对手难度 (0-10)。

    方法: 12组第三抢8席，对手必是某组第一。
    取12个头名难度的中位数 — 比算术均值更稳健，不受极端值影响。

    Returns:
        float 难度评分 (0=极易, 10=极难)
    """
    import statistics
    all_winner_difficulties = []
    for grp in 'ABCDEFGHIJKL':
        rating = GROUP_PATH_RATING.get(grp, (5, 5))
        all_winner_difficulties.append(rating[0])  # pos=1 difficulty

    try:
        return statistics.median(all_winner_difficulties)
    except Exception:
        return 5.0  # fallback


def _map_prob_to_motivation(prob: float) -> dict:
    """
    🆕 V4.5 P1b: 第三名晋级概率 → 战意非线性映射。

    避免概率小波动导致战意剧烈变化。
    """
    if prob >= 60:
        return {'level': 'high', 'motivation_base': 9, 'label': '高概率晋级'}
    elif prob >= 30:
        return {'level': 'medium', 'motivation_base': 7, 'label': '观望·取决于实时比分'}
    else:
        return {'level': 'low', 'motivation_base': 5, 'label': '低概率·可能轮换'}


# ══════════════════════════════════════════════════════════════
# 🆕 V4.5: 路径倒挂检测 — 低排名反而有更优淘汰赛路径
# ══════════════════════════════════════════════════════════════

def _is_path_inverted(group: str) -> dict:
    """
    检测淘汰赛路径是否出现倒挂: 低排名反而有更优路径。

    例: L组 pos2(难度9·碰葡萄牙) >> pos3(难度2·碰第三名球队)
         J组 pos2(难度10·碰西班牙) >> pos3(难度2·碰第三名球队)

    触发条件: l2难度 > l1+4 AND l2难度 > l3+4 (双重条件·仅极端倒挂)
    """
    rating = GROUP_PATH_RATING.get(group, (5, 5))
    l1, l2 = rating[0], rating[1]
    l3 = _estimate_third_path_difficulty(group)

    inverted = (l2 > l1 + 4) and (l2 > l3 + 4)

    best_path_at = 1
    worst_path_at = 2
    if inverted:
        if l1 <= l3:
            best_path_at = 1
        else:
            best_path_at = 3
        worst_path_at = 2  # L2永远是最差路径(触发条件保证)

    return {
        'inverted': inverted,
        'best_path_at': best_path_at,
        'worst_path_at': worst_path_at,
        'l1': l1, 'l2': l2, 'l3': l3,
    }


# ══════════════════════════════════════════════════════════════
# 核心API (向后兼容)
# ══════════════════════════════════════════════════════════════

@dataclass
class TeamMotivation:
    team: str
    group: str
    pts: int
    gd: int
    played: int
    position: int
    scenario: str
    motivation_score: float
    path_difficulty: float
    scenario_detail: str
    # V2.13 新增
    need_goals: bool = False
    rotation_risk: float = 0.0
    knockout_opponent: str = ''
    alt_path_better: bool = False


@dataclass
class MatchMotivation:
    home_motivation: TeamMotivation
    away_motivation: TeamMotivation
    differential: float
    confidence_adjustment: float    # -10 to +10
    prediction_bias: str            # home_boost/away_boost/neutral
    # V2.13 新增
    same_group_impact: str = ''     # 同组另一场比赛对本场的影响
    tournament_note: str = ''       # 赛程层面的注意事项


def calculate_motivation(team: str, matchday: int = 2) -> TeamMotivation:
    """增强版战意计算"""
    _load_actual_results()

    grp = get_team_group(team)
    if not grp:
        return TeamMotivation(
            team=team, group='?', pts=0, gd=0, played=0, position=1,
            scenario='unknown', motivation_score=5, path_difficulty=5,
            scenario_detail='未知小组',
        )

    pos = _get_position(grp, team)
    s = GROUP_STANDINGS.get(grp, {}).get(team, {'pts': 0, 'gd': 0, 'gf': 0, 'ga': 0, 'played': 0})

    enhanced = determine_scenario_enhanced(team, grp, matchday)

    # 淘汰赛路径难度
    rating = GROUP_PATH_RATING.get(grp, (5, 5))
    # 🆕 V4.5 P2: pos=3 用期望难度替代兜底9
    path = rating[pos - 1] if pos in (1, 2) else (_estimate_third_path_difficulty(grp) if pos == 3 else 10)

    # 排名修正
    rank_bonus = 0
    if pos == 1:
        rank_bonus = 0.8
    elif pos == 3:
        rank_bonus = 0.5

    # 🆕 V4.5: L3路径评估 (pos=2时·第三名可能优于第二名)
    l3_difficulty = _estimate_third_path_difficulty(grp) if pos == 2 else 10
    l2_difficulty = rating[1] if len(rating) > 1 else 5
    l3_better_than_l2 = (pos == 2 and l3_difficulty < l2_difficulty - 2)

    # 避强动力: 如果另一条路径更优, 调整动机
    avoidance_bonus = 0
    if enhanced['alt_path_better'] and pos == 1:
        avoidance_bonus = -0.5  # 小组第一反而路径更硬 → 保头名动力稍降
    elif l3_better_than_l2 and pos == 2:
        # 🆕 V4.5: L3路径优于L2 → 赢球=L1(最优)·输球=L3(次优)·平局=L2(最差)
        # 避L2动力极强·比普通alt_path_better更激进
        avoidance_bonus = 2.0
    elif enhanced['alt_path_better'] and pos == 2:
        avoidance_bonus = 1.5   # 小组第一路径更优 → 争胜动力 (alt_path_better=第一比第二容易得多)

    # 🆕 V4.5: 路径倒挂 — 当前站在最差/最优排名上的动机调整
    path_info = _is_path_inverted(grp)
    if path_info['inverted']:
        if pos == path_info['worst_path_at']:
            # 站在最差路径上(L2) → 拼命离开·无论向上(L1)还是向下(L3)
            avoidance_bonus += 1.5
        elif pos == path_info['best_path_at']:
            # 已经站在最优路径上 → 守住当前位置
            avoidance_bonus += 0.5

    # 净胜球动力
    gd_bonus = 1.0 if enhanced['need_goals'] else 0

    motivation = min(10, enhanced['motivation_base'] + rank_bonus + avoidance_bonus + gd_bonus)

    return TeamMotivation(
        team=team,
        group=grp,
        pts=s['pts'],
        gd=s.get('gd', 0),
        played=s['played'],
        position=pos,
        scenario=enhanced['scenario'],
        motivation_score=round(motivation, 1),
        path_difficulty=path,
        scenario_detail=enhanced['detail'],
        need_goals=enhanced['need_goals'],
        rotation_risk=enhanced['rotation_risk'],
        knockout_opponent=enhanced['knockout_opponent'],
        alt_path_better=enhanced['alt_path_better'],
    )


def get_match_motivation(match_name: str) -> Optional[MatchMotivation]:
    """增强版双方战意分析"""
    from match_context import get_match as get_group_match

    parts = match_name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
    if len(parts) != 2:
        return None

    home = parts[0].strip()
    away = parts[1].strip()

    m = get_group_match(match_name=match_name)
    matchday = m.matchday if m else 2
    grp = m.group if m else _find_group(home, away) or '?'

    home_mot = calculate_motivation(home, matchday)
    away_mot = calculate_motivation(away, matchday)

    diff = home_mot.motivation_score - away_mot.motivation_score

    # 调整
    if diff >= 4:
        adj = 8
        bias = 'home_boost'
    elif diff >= 2:
        adj = 4
        bias = 'home_boost'
    elif diff <= -4:
        adj = -8
        bias = 'away_boost'
    elif diff <= -2:
        adj = -4
        bias = 'away_boost'
    else:
        adj = 0
        bias = 'neutral'

    # 同组影响
    same_group_impact = _analyze_same_group_impact(grp, home, away, matchday)

    # 赛程备注
    tournament_note = ''
    if home_mot.rotation_risk > 0.3 or away_mot.rotation_risk > 0.3:
        risk_team = home if home_mot.rotation_risk > 0.3 else away
        tournament_note = f'⚠️ {risk_team}可能轮换 (已确保出线)'
    if home_mot.alt_path_better or away_mot.alt_path_better:
        alt_teams = []
        if home_mot.alt_path_better:
            alt_teams.append(f'{home}({home_mot.knockout_opponent})')
        if away_mot.alt_path_better:
            alt_teams.append(f'{away}({away_mot.knockout_opponent})')
        tournament_note += f' | 🔀 争第一路径更优: {", ".join(alt_teams)}'

    return MatchMotivation(
        home_motivation=home_mot,
        away_motivation=away_mot,
        differential=diff,
        confidence_adjustment=adj,
        prediction_bias=bias,
        same_group_impact=same_group_impact,
        tournament_note=tournament_note.strip(' |'),
    )


def _analyze_same_group_impact(group: str, home: str, away: str, matchday: int) -> str:
    """分析同组另一场比赛对双方的间接影响"""
    if matchday == 1:
        return ''

    all_matches = get_group_matches(group)
    other_match = None
    for m in all_matches:
        if m.matchday == matchday and m.home != home and m.away != away:
            if m.home != away and m.away != home:
                other_match = m
                break

    if not other_match:
        return ''

    # 简化分析: 如果同组另一场是弱弱对话, 对本场强队有利
    home_pos = _get_position(group, home)
    away_pos = _get_position(group, away)

    if home_pos <= 2 and away_pos <= 2:
        return f'同组: {other_match.home}vs{other_match.away} → 胜者可能威胁出线位置'

    return ''


# ══════════════════════════════════════════════════════════════
# 公开API (向后兼容)
# ══════════════════════════════════════════════════════════════

def update_result(group: str, home: str, away: str, home_goals: int, away_goals: int):
    """手动更新赛果"""
    _load_actual_results()
    _set_result(group, home, away, home_goals, away_goals)


def get_group_table(group: str) -> List[dict]:
    """获取小组积分榜"""
    _load_actual_results()
    if group not in GROUP_STANDINGS:
        return []
    return sorted(
        [{'team': t, **s} for t, s in GROUP_STANDINGS[group].items()],
        key=lambda x: (x['pts'], x['gd'], x['gf']),
        reverse=True
    )


def refresh_standings():
    """强制刷新积分表 (新赛果录入后调用)"""
    global _real_results_loaded, GROUP_STANDINGS
    GROUP_STANDINGS = {}
    _real_results_loaded = False
    _load_actual_results()


# ══════════════════════════════════════════════════════════════
# 独立测试
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    refresh_standings()

    print("=== 小组积分榜 (自动加载实际赛果) ===\n")
    for grp in 'IJ':
        print(f"  {grp}组:")
        table = get_group_table(grp)
        for row in table:
            print(f"    {row['team']:10s} | {row['played']}场 | {row['pts']}分 | GD{row['gd']:+d} | GF{row['gf']}/GA{row['ga']}")
        print()

    test_matches = ['法国VS塞内加尔', '伊拉克VS挪威', '阿根廷VS阿尔及利亚', '奥地利VS约旦']

    for mn in test_matches:
        print(f"\n{'='*60}")
        result = get_match_motivation(mn)
        if result:
            hm = result.home_motivation
            am = result.away_motivation
            print(f"  ⚔️ {mn}")
            print(f"  🏠 {hm.scenario_detail} | 战意: {hm.motivation_score:.0f}/10 | 路径: {hm.path_difficulty:.0f}/10")
            if hm.need_goals:
                print(f"     🎯 需要刷净胜球")
            if hm.rotation_risk > 0:
                print(f"     🔄 轮换风险: {hm.rotation_risk:.0%}")
            if hm.alt_path_better:
                print(f"     🔀 第二条路径更优: 淘汰赛对手{hm.knockout_opponent}")
            print(f"  🛫 {am.scenario_detail} | 战意: {am.motivation_score:.0f}/10 | 路径: {am.path_difficulty:.0f}/10")
            if am.need_goals:
                print(f"     🎯 需要刷净胜球")
            if am.rotation_risk > 0:
                print(f"     🔄 轮换风险: {am.rotation_risk:.0%}")
            if am.alt_path_better:
                print(f"     🔀 第二条路径更优: 淘汰赛对手{am.knockout_opponent}")
            print(f"  战意差: {result.differential:+.0f} | 调整: {result.confidence_adjustment:+d}% | 偏向: {result.prediction_bias}")
            if result.tournament_note:
                print(f"  📋 {result.tournament_note}")
            if result.same_group_impact:
                print(f"  📊 {result.same_group_impact}")


# ══════════════════════════════════════════════════════════
# 🆕 V3.3 P2-8: 淘汰赛特殊规则
# ══════════════════════════════════════════════════════════

def is_knockout_match(match_name: str) -> bool:
    """
    检测是否为淘汰赛阶段比赛。

    通过赛程数据判断: matchday >= 4 即为淘汰赛 (小组赛为1-3)。
    """
    try:
        from match_context import get_match as get_group_match
        m = get_group_match(match_name=match_name)
        if m and hasattr(m, 'matchday'):
            return m.matchday >= 4
    except Exception:
        pass
    return False


def calculate_knockout_motivation(match_name: str) -> dict:
    """
    计算淘汰赛阶段特殊调整。

    Returns:
        {
            'is_knockout': bool,
            'draw_tendency_boost': float,
            'score_dampen_factor': float,
            'notes': List[str],
        }
    """
    if not is_knockout_match(match_name):
        return {
            'is_knockout': False,
            'draw_tendency_boost': 1.0,
            'score_dampen_factor': 1.0,
            'notes': [],
        }

    notes = [
        f'🏆 淘汰赛: 平局概率+{(CONF.knockout_draw_tendency-1)*100:.0f}%·'
        f'总进球衰减{(1-CONF.knockout_score_dampen)*100:.0f}%',
    ]

    return {
        'is_knockout': True,
        'draw_tendency_boost': CONF.knockout_draw_tendency,
        'score_dampen_factor': CONF.knockout_score_dampen,
        'notes': notes,
    }

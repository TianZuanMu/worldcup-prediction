# -*- coding: utf-8 -*-
"""
V3.0 超巨里程碑检测 (P1#4)
检测球员里程碑场次 (如梅西200场) 对比赛结果的潜在影响。

覆盖:
  1. 出场里程碑: 100场/150场/200场 (阈值来自 CONF.milestone_caps)
  2. 进球里程碑: 50球/100球 (阈值来自 CONF.milestone_goal_records)
  3. 特殊事件: 退役告别赛·冲击历史纪录·世界杯首秀

用法:
  from milestone_detection import detect_milestones
  r = detect_milestones('阿根廷', '阿根廷VS阿尔及利亚')
  # → {'has_milestone': True, 'players': [...], 'boost': 20, 'detail': '...'}
"""

from config import CONF

# ── 里程碑 boost 映射 ──
# 根据触发的阈值返回对应 boost (百分比点数)
# CONF.milestone_caps 的 key 是出场次数阈值
_CAP_BOOST = {
    100: 2,     # 100场里程碑 +2% (温和·V3.0下调)
    150: 4,    # 150场里程碑 +4% (显著·V3.0下调)
    200: 5,    # 200场里程碑 +5% (上限·V3.0下调)
}

# CONF.milestone_goal_records 的 key 是进球数阈值
_GOAL_BOOST = {
    50: 5,      # 国家队50球 +5%
    100: 10,    # 国家队100球 +10%
}

# 总 boost 上限 (来自 milestone_adj_range 语义·此处硬上限 20)
_MAX_BOOST = 20


# ══════════════════════════════════════════════════════════════
# 里程碑数据库
# ══════════════════════════════════════════════════════════════
# 字段说明:
#   caps              : 赛前已有国家队出场次数
#   goals             : 赛前已有国家队进球数
#   next_match_caps   : 本场后出场数 (为里程碑阈值时触发 boost)
#   next_match_goals  : 本场后可能达到的进球里程碑 (距阈值≤2球时检测)
#   notable_events    : 特殊事件列表 [{event, boost_override, detail}]
#   note              : 背景说明

MILESTONE_DB = {
    '阿根廷': {
        'Messi': {
            'caps': 199, 'goals': 99,
            'next_match_caps': 200,
            'next_match_goals_record': '100th goal',
            'notable_events': [
                {'event': 'cap_200', 'boost': 20,
                 'detail': '梅西200场国家队里程碑·历史性时刻·超巨爆发概率极高'},
                {'event': 'goal_100', 'boost': 10,
                 'detail': '梅西冲击国家队100球·双重里程碑叠加'},
            ],
            'note': 'GOAT·卫冕冠军核心·200场+100球双里程碑',
        },
    },
    '葡萄牙': {
        'Ronaldo': {
            'caps': 210, 'goals': 135,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'retirement_tournament', 'boost': 5,
                 'detail': 'C罗最后一届世界杯·告别演出动力'},
            ],
            'note': '已过200场·现役射手王·最后一届世界杯',
        },
    },
    '法国': {
        'Mbappe': {
            'caps': 86, 'goals': 56,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [],
            'note': '冲击100场·下一代领袖',
        },
        'Griezmann': {
            'caps': 142, 'goals': 49,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [],
            'note': '姆巴佩冲金靴·全队健康',
        },
    },
    '巴西': {
        'Neymar': {
            'caps': 130, 'goals': 80,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'chasing_record', 'boost': 3,
                 'detail': '内马尔追逐贝利国家队进球纪录(95球)'},
            ],
            'note': '冲击巴西队史射手王·贝利95球纪录',
        },
    },
    '英格兰': {
        'Kane': {
            'caps': 107, 'goals': 72,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'chasing_record', 'boost': 3,
                 'detail': '凯恩追逐鲁尼英格兰进球纪录(53→已破)·现冲击70+'},
            ],
            'note': '队长·冲击80球',
        },
    },
    '克罗地亚': {
        'Modric': {
            'caps': 185, 'goals': 27,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'retirement_tournament', 'boost': 5,
                 'detail': '莫德里奇最后一届世界杯·传奇告别'},
            ],
            'note': '传奇中场·接近200场·最后一届世界杯',
        },
    },
    '比利时': {
        'De Bruyne': {
            'caps': 112, 'goals': 30,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'retirement_tournament', 'boost': 3,
                 'detail': '黄金一代最后机会'},
            ],
            'note': '黄金一代核心·最后机会',
        },
    },
    '乌拉圭': {
        'Suarez': {
            'caps': 145, 'goals': 70,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'retirement_tournament', 'boost': 5,
                 'detail': '苏亚雷斯最后一届世界杯·传奇告别'},
            ],
            'note': '传奇前锋·最后一届世界杯·150场在望',
        },
    },
    '德国': {
        'Muller': {
            'caps': 132, 'goals': 46,
            'next_match_caps': None,
            'next_match_goals_record': '50th goal',
            'notable_events': [
                {'event': 'goal_50', 'boost': 5,
                 'detail': '穆勒冲击国家队50球'},
            ],
            'note': '空间阅读者·冲击50球',
        },
    },
    '西班牙': {
        'Morata': {
            'caps': 85, 'goals': 38,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [],
            'note': '接近100场·队长',
        },
    },
    '荷兰': {
        'Van Dijk': {
            'caps': 82, 'goals': 9,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'retirement_tournament', 'boost': 3,
                 'detail': '范戴克黄金期最后机会'},
            ],
            'note': '防线核心·队长·黄金期最后世界杯',
        },
    },
    '意大利': {
        'Donnarumma': {
            'caps': 75, 'goals': 0,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [],
            'note': '年轻门将·冲击100场',
        },
    },
    '波兰': {
        'Lewandowski': {
            'caps': 160, 'goals': 85,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [
                {'event': 'retirement_tournament', 'boost': 5,
                 'detail': '莱万最后一届世界杯·波兰传奇告别'},
            ],
            'note': '波兰射手王·最后一届世界杯',
        },
    },
    '塞内加尔': {
        'Mane': {
            'caps': 110, 'goals': 45,
            'next_match_caps': None,
            'next_match_goals_record': '50th goal',
            'notable_events': [
                {'event': 'goal_50', 'boost': 5,
                 'detail': '马内冲击国家队50球'},
            ],
            'note': '塞内加尔核心·冲击50球',
        },
    },
    '摩洛哥': {
        'Hakimi': {
            'caps': 82, 'goals': 10,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [],
            'note': '后防核心·2022四强成员',
        },
    },
    '日本': {
        'Mitoma': {
            'caps': 42, 'goals': 10,
            'next_match_caps': None,
            'next_match_goals_record': None,
            'notable_events': [],
            'note': '新生代核心',
        },
    },
}

# 有里程碑级球员的其他球队 (占位条目·避免 KeyError 的同时标记关注)
_PLACEHOLDER_TEAMS = [
    '墨西哥', '美国', '加拿大', '卡塔尔', '沙特', '伊朗', '澳大利亚',
    '突尼斯', '摩洛哥', '加纳', '喀麦隆', '塞内加尔', '科特迪瓦',
    '韩国', '日本', '挪威', '瑞典', '丹麦', '瑞士', '奥地利',
    '塞尔维亚', '匈牙利', '捷克', '波兰', '乌克兰', '土耳其',
    '智利', '哥伦比亚', '厄瓜多尔', '秘鲁', '巴拉圭',
    '埃及', '阿尔及利亚', '尼日利亚', '南非',
    '哥斯达黎加', '巴拿马', '海地', '库拉索', '新西兰',
]
for _team in _PLACEHOLDER_TEAMS:
    if _team not in MILESTONE_DB:
        MILESTONE_DB[_team] = {}


# ══════════════════════════════════════════════════════════════
# 检测函数
# ══════════════════════════════════════════════════════════════

def detect_milestones(team: str, match_name: str = '') -> dict:
    """
    检测球队是否有超巨里程碑球员。

    Args:
        team: 球队名称 (中文, 如 '阿根廷')
        match_name: 比赛名称 (可选, 用于日志)

    Returns:
        {
            has_milestone: bool,
            players: [str],        # 人类可读的球员描述
            boost: float,          # 0 到 20 的置信度加成 (百分比点数)
            detail: str,           # 单行摘要
        }
    """
    result = {
        'has_milestone': False,
        'players': [],
        'boost': 0.0,
        'detail': '',
    }

    players = MILESTONE_DB.get(team, {})
    if not players:
        return result

    # ── 获取已配置的里程碑阈值 ──
    # CONF.milestone_caps:     {'100': 50, '150': 100, '200': 200}
    # CONF.milestone_goal_records: {'50': 50, '100': 100}
    cap_thresholds = sorted(int(k) for k in CONF.milestone_caps.keys())
    goal_thresholds = sorted(int(k) for k in CONF.milestone_goal_records.keys())

    for name, data in players.items():
        player_boost = 0.0
        player_details = []

        # ── 1. 出场里程碑检测 ──
        next_caps = data.get('next_match_caps')
        if next_caps is not None:
            # 找到 next_caps 命中的最高阈值
            for threshold in sorted(cap_thresholds, reverse=True):
                if next_caps == threshold:
                    boost_val = _CAP_BOOST.get(threshold, 0)
                    player_boost = max(player_boost, boost_val)
                    player_details.append(
                        f'{name}第{threshold}场里程碑·+{boost_val}%'
                    )
                    break  # 只取最高命中
                elif next_caps > threshold:
                    # next_caps 已过该阈值但未精确命中 → 检测是否刚过
                    # 如果 current caps < threshold <= next_caps, 说明本场就是达到阈值的那场
                    # 但 next_caps > threshold 且不等于任何阈值, 说明已错过
                    pass

        # ── 2. 进球里程碑检测 ──
        next_goals_record = data.get('next_match_goals_record')
        current_goals = data.get('goals', 0)

        if next_goals_record:
            # 解析 "50th goal" / "100th goal" → 提取数字
            import re
            goal_match = re.search(r'(\d+)', str(next_goals_record))
            if goal_match:
                target_goals = int(goal_match.group(1))
                if target_goals in goal_thresholds:
                    boost_val = _GOAL_BOOST.get(target_goals, 0)
                    player_boost = max(player_boost, boost_val)
                    player_details.append(
                        f'{name}冲击{target_goals}球里程碑·+{boost_val}%'
                    )
        else:
            # 自动检测: 当前进球数+1 或 +2 是否命中阈值
            for threshold in goal_thresholds:
                goals_needed = threshold - current_goals
                if 1 <= goals_needed <= 2:
                    # 本场有较大概率达成进球里程碑 → 给予较小 boost
                    boost_val = _GOAL_BOOST.get(threshold, 0) * 0.5
                    player_boost = max(player_boost, boost_val)
                    player_details.append(
                        f'{name}距{threshold}球差{goals_needed}球·+{boost_val:.0f}%'
                    )
                    break  # 只报告最近的一个

        # ── 3. 特殊事件检测 ──
        for event in data.get('notable_events', []):
            event_boost = event.get('boost', 0)
            if event_boost > 0:
                player_boost = max(player_boost, event_boost)
                player_details.append(event.get('detail', event.get('event', '')))

        # ── 4. 汇总该球员的 boost ──
        if player_boost > 0:
            result['has_milestone'] = True
            result['players'].append(f'{name}: {data.get("note", "")}')
            result['boost'] += player_boost
            if player_details:
                result['detail'] = ' | '.join(player_details)

    # ── 5. 上限裁剪 ──
    result['boost'] = min(result['boost'], _MAX_BOOST)
    result['boost'] = round(result['boost'], 1)

    return result


# ══════════════════════════════════════════════════════════════
# 便捷批量函数
# ══════════════════════════════════════════════════════════════

def batch_detect(team_match_pairs: list) -> dict:
    """
    批量检测多场比赛的里程碑。

    Args:
        team_match_pairs: [(team_name, match_name), ...]

    Returns:
        {team_name: detect_milestones_result, ...}
    """
    results = {}
    for team, match_name in team_match_pairs:
        results[team] = detect_milestones(team, match_name)
    return results


# ══════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 60)
    print('超巨里程碑检测 — 自检')
    print('=' * 60)

    test_cases = [
        ('阿根廷', '阿根廷VS阿尔及利亚'),
        ('葡萄牙', '葡萄牙VS摩洛哥'),
        ('法国', '法国VS突尼斯'),
        ('巴西', '巴西VS塞尔维亚'),
        ('英格兰', '英格兰VS伊朗'),
        ('克罗地亚', '克罗地亚VS比利时'),
        ('乌拉圭', '乌拉圭VS加纳'),
        ('比利时', '比利时VS克罗地亚'),
        ('德国', '德国VS西班牙'),
        ('荷兰', '荷兰VS卡塔尔'),
        ('波兰', '波兰VS阿根廷'),
        ('塞内加尔', '塞内加尔VS荷兰'),
    ]

    for team, match in test_cases:
        r = detect_milestones(team, match)
        if r['has_milestone']:
            print(f'\n{team} ({match})')
            print(f'  Has milestone: {r["has_milestone"]}')
            print(f'  Players: {r["players"]}')
            print(f'  Boost: +{r["boost"]}%')
            print(f'  Detail: {r["detail"]}')
        else:
            print(f'\n{team} ({match}): 无里程碑')

    print(f'\n{"=" * 60}')
    print('批量检测测试:')
    pairs = [('阿根廷', 'test'), ('法国', 'test'), ('巴西', 'test')]
    batch = batch_detect(pairs)
    for team, r in batch.items():
        status = f'+{r["boost"]}%' if r['has_milestone'] else 'none'
        print(f'  {team}: {status}')

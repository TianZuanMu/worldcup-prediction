# -*- coding: utf-8 -*-
"""
对手质量数据库 + BIG三条件自动检查 (V3.3: 球员身价感知)

用法:
  from opponent_db import check_three_conditions, opponent_quality, get_team_value_breakdown
  result = check_three_conditions('乌兹别克斯坦')
  # → {'all_pass': True, ...}  # Shomurodov(€0M)不再误判为顶级射手

🆕 V3.3: 48队174名球员真实身价+位置+俱乐部数据
"""

# ── 对手数据库 (V3.3: 真实球员身价) ──
# rank: FIFA排名
# giant_killings: 世界杯历史爆冷记录
# pre_goals_per_game: 预选赛场均进球
# total_value_m: 核心球员总身价(百万欧)
# top5_attackers: 五大联赛高价值攻击手数量(身价≥€10M)
# players: 球员列表 [{'name', 'value_m', 'club', 'top5', 'pos'}]

OPPONENT_DB = {
    '墨西哥': {
        'rank': 15,
        'pre_goals_per_game': 1.3,
        'total_value_m': 40,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '埃德松·阿尔瓦雷斯', 'value_m': 15, 'club': '费内巴切', 'top5': False, 'pos': 'MF'},
            {'name': '塞萨尔·蒙特斯', 'value_m': 7.5, 'club': '莫斯科火车头', 'top5': False, 'pos': 'CB'},
            {'name': '豪尔赫·桑切斯', 'value_m': 2.2, 'club': '塞萨洛尼基', 'top5': False, 'pos': 'RB'},
            {'name': '路易斯·罗莫', 'value_m': 3, 'club': '瓜达拉哈拉', 'top5': False, 'pos': 'MF'},
            {'name': '奥韦林·皮内达', 'value_m': 7, 'club': '雅典AEK', 'top5': False, 'pos': 'MF'},
            {'name': '劳尔·希门尼斯', 'value_m': 5, 'club': '富勒姆', 'top5': True, 'pos': 'FW'},
            {'name': '吉列尔莫·奥乔亚', 'value_m': 0.2, 'club': 'AEL利马索尔', 'top5': False, 'pos': 'GK'},
        ],
    },
    '南非': {
        'rank': 70,
        'pre_goals_per_game': 0.7,
        'total_value_m': 8,
        'top5_count': 1,
        'top5_attackers': 0,
        'giant_killings': [],
        'players': [
            {'name': '莱尔·福斯特', 'value_m': 8, 'club': '伯恩利', 'top5': True, 'pos': 'FW'},
        ],
    },
    '韩国': {
        'rank': 25,
        'pre_goals_per_game': 1.8,
        'total_value_m': 57,
        'top5_count': 3,
        'top5_attackers': 1,
        'giant_killings': ['2022淘汰葡萄牙'],
        'players': [
            {'name': '孙兴慜', 'value_m': 15, 'club': '洛杉矶FC', 'top5': False, 'pos': 'FW'},
            {'name': '金玟哉', 'value_m': 25, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'CB'},
            {'name': '黄仁范', 'value_m': 8, 'club': '费耶诺德', 'top5': False, 'pos': 'MF'},
            {'name': '黄喜灿', 'value_m': 6, 'club': '狼队', 'top5': True, 'pos': 'FW'},
            {'name': '李在城', 'value_m': 2, 'club': '美因茨', 'top5': True, 'pos': 'MF'},
            {'name': '赵贤祐', 'value_m': 0.7, 'club': '蔚山HD', 'top5': False, 'pos': 'GK'},
        ],
    },
    '捷克': {
        'rank': 30,
        'pre_goals_per_game': 1.4,
        'total_value_m': 32,
        'top5_count': 2,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '帕特里克·希克', 'value_m': 20, 'club': '勒沃库森', 'top5': True, 'pos': 'FW'},
            {'name': '托马斯·绍切克', 'value_m': 12, 'club': '西汉姆联', 'top5': True, 'pos': 'MF'},
        ],
    },
    '加拿大': {
        'rank': 40,
        'pre_goals_per_game': 1.5,
        'total_value_m': 95,
        'top5_count': 3,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '阿方索·戴维斯', 'value_m': 40, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'LB'},
            {'name': '乔纳森·戴维', 'value_m': 30, 'club': '尤文图斯', 'top5': True, 'pos': 'FW'},
            {'name': '伊斯梅尔·科内', 'value_m': 25, 'club': '萨索洛', 'top5': True, 'pos': 'MF'},
        ],
    },
    '波黑': {
        'rank': 55,
        'pre_goals_per_game': 1.2,
        'total_value_m': 30,
        'top5_count': 2,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '埃尔梅丁·德米罗维奇', 'value_m': 22, 'club': '斯图加特', 'top5': True, 'pos': 'FW'},
            {'name': '埃丁·哲科', 'value_m': 1.5, 'club': '沙尔克04', 'top5': False, 'pos': 'FW'},
            {'name': '塞亚德·科拉希纳茨', 'value_m': 6, 'club': '亚特兰大', 'top5': True, 'pos': 'CB'},
        ],
    },
    '卡塔尔': {
        'rank': 60,
        'pre_goals_per_game': 1,
        'total_value_m': 11,
        'top5_count': 0,
        'top5_attackers': 0,
        'giant_killings': [],
        'players': [
            {'name': '阿克拉姆·阿菲夫', 'value_m': 8, 'club': '阿尔萨德', 'top5': False, 'pos': 'FW'},
            {'name': '布瓦勒姆·胡希', 'value_m': 0.2, 'club': '阿尔萨德', 'top5': False, 'pos': 'CB'},
            {'name': '阿尔莫兹·阿里', 'value_m': 2.4, 'club': '杜海勒', 'top5': False, 'pos': 'FW'},
        ],
    },
    '瑞士': {
        'rank': 18,
        'pre_goals_per_game': 1.6,
        'total_value_m': 75,
        'top5_count': 4,
        'top5_attackers': 3,
        'giant_killings': [],
        'players': [
            {'name': '格拉尼特·扎卡', 'value_m': 10, 'club': '桑德兰', 'top5': True, 'pos': 'MF'},
            {'name': '曼努埃尔·阿坎吉', 'value_m': 18, 'club': '曼城', 'top5': True, 'pos': 'CB'},
            {'name': '布雷尔·恩博洛', 'value_m': 12, 'club': '摩纳哥', 'top5': True, 'pos': 'FW'},
            {'name': '丹·恩多耶', 'value_m': 35, 'club': '诺丁汉森林', 'top5': True, 'pos': 'FW'},
        ],
    },
    '巴西': {
        'rank': 2,
        'pre_goals_per_game': 2,
        'total_value_m': 414,
        'top5_count': 7,
        'top5_attackers': 4,
        'giant_killings': [],
        'players': [
            {'name': '维尼修斯', 'value_m': 140, 'club': '皇家马德里', 'top5': True, 'pos': 'FW'},
            {'name': '加布里埃尔', 'value_m': 75, 'club': '阿森纳', 'top5': True, 'pos': 'CB'},
            {'name': '拉菲尼亚', 'value_m': 70, 'club': '巴塞罗那', 'top5': True, 'pos': 'FW'},
            {'name': '吉马良斯', 'value_m': 70, 'club': '纽卡斯尔联', 'top5': True, 'pos': 'MF'},
            {'name': '内马尔', 'value_m': 8, 'club': '桑托斯', 'top5': False, 'pos': 'FW'},
            {'name': '阿利松', 'value_m': 17, 'club': '利物浦', 'top5': True, 'pos': 'GK'},
            {'name': '马尔基尼奥斯', 'value_m': 28, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'CB'},
            {'name': '卡塞米罗', 'value_m': 6, 'club': '曼联', 'top5': True, 'pos': 'MF'},
        ],
    },
    '摩洛哥': {
        'rank': 20,
        'pre_goals_per_game': 1.5,
        'total_value_m': 133,
        'top5_count': 3,
        'top5_attackers': 0,
        'giant_killings': ['2022四强·淘汰葡萄牙+西班牙'],
        'players': [
            {'name': '阿什拉夫·哈基米', 'value_m': 80, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'RB'},
            {'name': '纳耶夫·阿格尔德', 'value_m': 35, 'club': '西汉姆联', 'top5': True, 'pos': 'CB'},
            {'name': '马兹拉维', 'value_m': 18, 'club': '曼联', 'top5': True, 'pos': 'RB'},
        ],
    },
    '苏格兰': {
        'rank': 35,
        'pre_goals_per_game': 1.4,
        'total_value_m': 65,
        'top5_count': 2,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '斯科特·麦克托米奈', 'value_m': 40, 'club': '那不勒斯', 'top5': False, 'pos': 'MF'},
            {'name': '安迪·罗伯逊', 'value_m': 10, 'club': '利物浦', 'top5': True, 'pos': 'LB'},
            {'name': '约翰·麦金', 'value_m': 15, 'club': '阿斯顿维拉', 'top5': True, 'pos': 'MF'},
        ],
    },
    '海地': {
        'rank': 85,
        'pre_goals_per_game': 0.5,
        'total_value_m': 18,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '威尔逊·伊西多尔', 'value_m': 18, 'club': '雷恩', 'top5': True, 'pos': 'FW'},
        ],
    },
    '美国': {
        'rank': 14,
        'pre_goals_per_game': 1.7,
        'total_value_m': 139,
        'top5_count': 4,
        'top5_attackers': 3,
        'giant_killings': [],
        'players': [
            {'name': '克里斯蒂安·普利希奇', 'value_m': 40, 'club': 'AC米兰', 'top5': False, 'pos': 'FW'},
            {'name': '韦斯顿·麦肯尼', 'value_m': 30, 'club': '尤文图斯', 'top5': True, 'pos': 'MF'},
            {'name': '弗拉林·巴洛贡', 'value_m': 40, 'club': '摩纳哥', 'top5': True, 'pos': 'FW'},
            {'name': '乔·雷纳', 'value_m': 4, 'club': '门兴格拉德巴赫', 'top5': True, 'pos': 'MF'},
            {'name': '泰勒·亚当斯', 'value_m': 25, 'club': '伯恩茅斯', 'top5': True, 'pos': 'MF'},
        ],
    },
    '巴拉圭': {
        'rank': 48,
        'pre_goals_per_game': 1.1,
        'total_value_m': 74,
        'top5_count': 3,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '胡利奥·恩西索', 'value_m': 25, 'club': '斯特拉斯堡', 'top5': True, 'pos': 'FW'},
            {'name': '迭戈·戈麦斯', 'value_m': 25, 'club': '布莱顿', 'top5': True, 'pos': 'MF'},
            {'name': '米格尔·阿尔米隆', 'value_m': 9, 'club': '亚特兰大联', 'top5': False, 'pos': 'FW'},
            {'name': '奥马尔·阿尔德雷特', 'value_m': 15, 'club': '桑德兰', 'top5': True, 'pos': 'CB'},
        ],
    },
    '澳大利亚': {
        'rank': 32,
        'pre_goals_per_game': 1.3,
        'total_value_m': 24,
        'top5_count': 2,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '乔丹·博斯', 'value_m': 12, 'club': '费耶诺德', 'top5': False, 'pos': 'LB'},
            {'name': '亚历山德罗·奇尔卡蒂', 'value_m': 12, 'club': '帕尔马', 'top5': True, 'pos': 'CB'},
            {'name': '内斯托里·伊兰昆达', 'value_m': 0, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'FW'},
        ],
    },
    '土耳其': {
        'rank': 28,
        'pre_goals_per_game': 1.6,
        'total_value_m': 181,
        'top5_count': 3,
        'top5_attackers': 3,
        'giant_killings': [],
        'players': [
            {'name': '阿尔达·居莱尔', 'value_m': 90, 'club': '皇家马德里', 'top5': True, 'pos': 'MF'},
            {'name': '哈坎·恰尔汗奥卢', 'value_m': 16, 'club': '国际米兰', 'top5': True, 'pos': 'MF'},
            {'name': '凯南·伊尔迪兹', 'value_m': 75, 'club': '尤文图斯', 'top5': True, 'pos': 'FW'},
        ],
    },
    '德国': {
        'rank': 8,
        'pre_goals_per_game': 2.3,
        'total_value_m': 300,
        'top5_count': 6,
        'top5_attackers': 4,
        'giant_killings': [],
        'players': [
            {'name': '贾马尔·穆西亚拉', 'value_m': 100, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'MF'},
            {'name': '弗洛里安·维尔茨', 'value_m': 100, 'club': '利物浦', 'top5': True, 'pos': 'MF'},
            {'name': '约书亚·基米希', 'value_m': 35, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'MF'},
            {'name': '曼努埃尔·诺伊尔', 'value_m': 4, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'GK'},
            {'name': '凯·哈弗茨', 'value_m': 55, 'club': '阿森纳', 'top5': True, 'pos': 'FW'},
            {'name': '安东尼奥·吕迪格', 'value_m': 6, 'club': '皇家马德里', 'top5': True, 'pos': 'CB'},
        ],
    },
    '厄瓜多尔': {
        'rank': 22,
        'pre_goals_per_game': 1.2,
        'total_value_m': 243,
        'top5_count': 4,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '莫伊塞斯·凯塞多', 'value_m': 100, 'club': '切尔西', 'top5': True, 'pos': 'MF'},
            {'name': '威廉·帕乔', 'value_m': 80, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'CB'},
            {'name': '因卡皮耶', 'value_m': 50, 'club': '阿森纳', 'top5': True, 'pos': 'CB'},
            {'name': '佩尔维斯·埃斯图皮南', 'value_m': 12, 'club': 'AC米兰', 'top5': True, 'pos': 'LB'},
            {'name': '恩纳·瓦伦西亚', 'value_m': 1, 'club': '帕丘卡', 'top5': False, 'pos': 'FW'},
        ],
    },
    '科特迪瓦': {
        'rank': 38,
        'pre_goals_per_game': 1.3,
        'total_value_m': 50,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '阿马德·迪亚洛', 'value_m': 50, 'club': '曼联', 'top5': True, 'pos': 'FW'},
        ],
    },
    '库拉索': {
        'rank': 178,
        'pre_goals_per_game': 0.3,
        'total_value_m': 0,
        'top5_count': 0,
        'top5_attackers': 0,
        'giant_killings': [],
        'players': [
            {'name': '朱里恩·科梅嫩西亚', 'value_m': 0, 'club': '—', 'top5': False, 'pos': 'CB'},
        ],
    },
    '荷兰': {
        'rank': 7,
        'pre_goals_per_game': 2,
        'total_value_m': 198,
        'top5_count': 4,
        'top5_attackers': 3,
        'giant_killings': [],
        'players': [
            {'name': '瑞安·赫拉芬贝赫', 'value_m': 80, 'club': '利物浦', 'top5': True, 'pos': 'MF'},
            {'name': '范戴克', 'value_m': 15, 'club': '利物浦', 'top5': True, 'pos': 'CB'},
            {'name': '弗兰基·德容', 'value_m': 35, 'club': '巴塞罗那', 'top5': True, 'pos': 'MF'},
            {'name': '加克波', 'value_m': 60, 'club': '利物浦', 'top5': True, 'pos': 'FW'},
            {'name': '孟菲斯·德佩', 'value_m': 8, 'club': '科林蒂安', 'top5': False, 'pos': 'FW'},
        ],
    },
    '日本': {
        'rank': 19,
        'pre_goals_per_game': 1.8,
        'total_value_m': 82,
        'top5_count': 5,
        'top5_attackers': 2,
        'giant_killings': ['2022胜德国+西班牙'],
        'players': [
            {'name': '久保建英', 'value_m': 30, 'club': '皇家社会', 'top5': True, 'pos': 'FW'},
            {'name': '远藤航', 'value_m': 4, 'club': '利物浦', 'top5': True, 'pos': 'MF'},
            {'name': '长友佑都', 'value_m': 0.1, 'club': 'FC东京', 'top5': False, 'pos': 'LB'},
            {'name': '伊藤洋辉', 'value_m': 18, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'CB'},
            {'name': '镰田大地', 'value_m': 10, 'club': '水晶宫', 'top5': True, 'pos': 'MF'},
            {'name': '铃木彩艳', 'value_m': 20, 'club': '帕尔马', 'top5': True, 'pos': 'GK'},
        ],
    },
    '瑞典': {
        'rank': 27,
        'pre_goals_per_game': 1.7,
        'total_value_m': 190,
        'top5_count': 2,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '亚历山大·伊萨克', 'value_m': 85, 'club': '纽卡斯尔联', 'top5': True, 'pos': 'FW'},
            {'name': '维克托·约克雷斯', 'value_m': 75, 'club': '葡萄牙体育', 'top5': False, 'pos': 'FW'},
            {'name': '亚辛·阿亚里', 'value_m': 30, 'club': '布莱顿', 'top5': True, 'pos': 'MF'},
        ],
    },
    '突尼斯': {
        'rank': 42,
        'pre_goals_per_game': 1,
        'total_value_m': 15,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '汉尼拔·梅布里', 'value_m': 15, 'club': '伯恩利', 'top5': True, 'pos': 'MF'},
        ],
    },
    '比利时': {
        'rank': 4,
        'pre_goals_per_game': 2,
        'total_value_m': 141,
        'top5_count': 5,
        'top5_attackers': 4,
        'giant_killings': [],
        'players': [
            {'name': '凯文·德布劳内', 'value_m': 27, 'club': '曼城', 'top5': True, 'pos': 'MF'},
            {'name': '杰里米·多库', 'value_m': 75, 'club': '曼城', 'top5': True, 'pos': 'FW'},
            {'name': '罗梅卢·卢卡库', 'value_m': 6, 'club': '那不勒斯', 'top5': True, 'pos': 'FW'},
            {'name': '蒂博·库尔图瓦', 'value_m': 15, 'club': '皇家马德里', 'top5': True, 'pos': 'GK'},
            {'name': '莱安德罗·特罗萨德', 'value_m': 18, 'club': '阿森纳', 'top5': True, 'pos': 'FW'},
        ],
    },
    '埃及': {
        'rank': 33,
        'pre_goals_per_game': 1.5,
        'total_value_m': 81,
        'top5_count': 2,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '穆罕默德·萨拉赫', 'value_m': 30, 'club': '利物浦', 'top5': True, 'pos': 'FW'},
            {'name': '马尔穆什', 'value_m': 50, 'club': '法兰克福', 'top5': True, 'pos': 'FW'},
            {'name': '卢卡·齐达内', 'value_m': 1, 'club': '格拉纳达', 'top5': False, 'pos': 'GK'},
        ],
    },
    '伊朗': {
        'rank': 36,
        'pre_goals_per_game': 1.2,
        'total_value_m': 7.8,
        'top5_count': 0,
        'top5_attackers': 0,
        'giant_killings': [],
        'players': [
            {'name': '迈赫迪·塔雷米', 'value_m': 2.5, 'club': '奥林匹亚科斯', 'top5': False, 'pos': 'FW'},
            {'name': '阿里雷扎·贾汉巴赫什', 'value_m': 0.6, 'club': '登德', 'top5': False, 'pos': 'FW'},
            {'name': '迈赫迪·加耶迪', 'value_m': 4, 'club': '卡尔巴联盟', 'top5': False, 'pos': 'MF'},
            {'name': '阿里雷萨·贝兰万德', 'value_m': 0.7, 'club': '大不里士拖拉机', 'top5': False, 'pos': 'GK'},
        ],
    },
    '新西兰': {
        'rank': 90,
        'pre_goals_per_game': 0.6,
        'total_value_m': 7.5,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '克里斯·伍德', 'value_m': 5, 'club': '诺丁汉森林', 'top5': True, 'pos': 'FW'},
            {'name': '埃利亚·贾斯特', 'value_m': 2.5, 'club': '马瑟韦尔', 'top5': False, 'pos': 'FW'},
        ],
    },
    '西班牙': {
        'rank': 3,
        'pre_goals_per_game': 2.2,
        'total_value_m': 520,
        'top5_count': 5,
        'top5_attackers': 3,
        'giant_killings': [],
        'players': [
            {'name': '拉明·亚马尔', 'value_m': 200, 'club': '巴塞罗那', 'top5': True, 'pos': 'FW'},
            {'name': '佩德里', 'value_m': 150, 'club': '巴塞罗那', 'top5': True, 'pos': 'MF'},
            {'name': '罗德里', 'value_m': 65, 'club': '曼城', 'top5': True, 'pos': 'MF'},
            {'name': '乌奈·西蒙', 'value_m': 25, 'club': '毕尔巴鄂竞技', 'top5': True, 'pos': 'GK'},
            {'name': '库巴西', 'value_m': 80, 'club': '巴塞罗那', 'top5': True, 'pos': 'CB'},
        ],
    },
    '乌拉圭': {
        'rank': 16,
        'pre_goals_per_game': 1.6,
        'total_value_m': 173,
        'top5_count': 4,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '费德里科·巴尔韦德', 'value_m': 90, 'club': '皇家马德里', 'top5': True, 'pos': 'MF'},
            {'name': '罗纳德·阿劳霍', 'value_m': 20, 'club': '巴塞罗那', 'top5': True, 'pos': 'CB'},
            {'name': '达尔文·努涅斯', 'value_m': 25, 'club': '利雅得新月', 'top5': False, 'pos': 'FW'},
            {'name': '曼努埃尔·乌加特', 'value_m': 25, 'club': '曼联', 'top5': True, 'pos': 'MF'},
            {'name': '何塞·马里亚·希梅内斯', 'value_m': 12, 'club': '马德里竞技', 'top5': True, 'pos': 'CB'},
            {'name': '费尔南多·穆斯莱拉', 'value_m': 0.7, 'club': '拉普拉塔大学生', 'top5': False, 'pos': 'GK'},
        ],
    },
    '佛得角': {
        'rank': 72,
        'pre_goals_per_game': 0.5,
        'total_value_m': 15,
        'top5_count': 1,
        'top5_attackers': 0,
        'giant_killings': [],
        'players': [
            {'name': '洛甘·科斯塔', 'value_m': 15, 'club': '比利亚雷亚尔', 'top5': True, 'pos': 'CB'},
            {'name': '沃齐尼亚', 'value_m': 0.1, 'club': '沙维斯', 'top5': False, 'pos': 'GK'},
        ],
    },
    '沙特阿拉伯': {
        'rank': 55,
        'pre_goals_per_game': 1.1,
        'total_value_m': 2.8,
        'top5_count': 0,
        'top5_attackers': 0,
        'giant_killings': ['2022胜阿根廷'],
        'players': [
            {'name': '萨勒姆·多萨里', 'value_m': 1.5, 'club': '利雅得新月', 'top5': False, 'pos': 'FW'},
            {'name': '穆罕默德·奥韦斯', 'value_m': 0.3, 'club': '利雅得新月', 'top5': False, 'pos': 'GK'},
            {'name': '阿卜杜拉·阿姆里', 'value_m': 1, 'club': '利雅得胜利', 'top5': False, 'pos': 'CB'},
        ],
    },
    '法国': {
        'rank': 1,
        'pre_goals_per_game': 2.5,
        'total_value_m': 670,
        'top5_count': 6,
        'top5_attackers': 4,
        'giant_killings': [],
        'players': [
            {'name': '基利安·姆巴佩', 'value_m': 180, 'club': '皇家马德里', 'top5': True, 'pos': 'FW'},
            {'name': '迈克尔·奥利塞', 'value_m': 150, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'MF'},
            {'name': '奥斯曼·登贝莱', 'value_m': 100, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'FW'},
            {'name': '威廉·萨利巴', 'value_m': 100, 'club': '阿森纳', 'top5': True, 'pos': 'CB'},
            {'name': '德西雷·杜埃', 'value_m': 120, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'MF'},
            {'name': '迈尼昂', 'value_m': 20, 'club': 'AC米兰', 'top5': True, 'pos': 'GK'},
        ],
    },
    '挪威': {
        'rank': 11,
        'pre_goals_per_game': 1.9,
        'total_value_m': 265,
        'top5_count': 2,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '埃尔林·哈兰德', 'value_m': 200, 'club': '曼城', 'top5': True, 'pos': 'FW'},
            {'name': '马丁·厄德高', 'value_m': 65, 'club': '阿森纳', 'top5': True, 'pos': 'MF'},
        ],
    },
    '塞内加尔': {
        'rank': 23,
        'pre_goals_per_game': 1.4,
        'total_value_m': 62,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '萨迪奥·马内', 'value_m': 7, 'club': '利雅得胜利', 'top5': False, 'pos': 'FW'},
            {'name': '伊利曼·恩迪亚耶', 'value_m': 55, 'club': '埃弗顿', 'top5': True, 'pos': 'FW'},
        ],
    },
    '伊拉克': {
        'rank': 70,
        'pre_goals_per_game': 0.8,
        'total_value_m': 1.9,
        'top5_count': 0,
        'top5_attackers': 0,
        'giant_killings': [],
        'players': [
            {'name': '艾曼·侯赛因', 'value_m': 0.5, 'club': '阿尔卡尔马', 'top5': False, 'pos': 'FW'},
            {'name': '阿里·哈马迪', 'value_m': 1.5, 'club': '卢顿', 'top5': False, 'pos': 'FW'},
        ],
    },
    '阿根廷': {
        'rank': 5,
        'pre_goals_per_game': 2,
        'total_value_m': 300,
        'top5_count': 6,
        'top5_attackers': 3,
        'giant_killings': [],
        'players': [
            {'name': '莱昂内尔·梅西', 'value_m': 15, 'club': '迈阿密国际', 'top5': False, 'pos': 'FW'},
            {'name': '胡利安·阿尔瓦雷斯', 'value_m': 100, 'club': '马德里竞技', 'top5': True, 'pos': 'FW'},
            {'name': '劳塔罗·马丁内斯', 'value_m': 85, 'club': '国际米兰', 'top5': True, 'pos': 'FW'},
            {'name': '埃米利亚诺·马丁内斯', 'value_m': 15, 'club': '阿斯顿维拉', 'top5': True, 'pos': 'GK'},
            {'name': '恩佐·费尔南德斯', 'value_m': 0, 'club': '切尔西', 'top5': True, 'pos': 'MF'},
            {'name': '克里斯蒂安·罗梅罗', 'value_m': 45, 'club': '热刺', 'top5': True, 'pos': 'CB'},
            {'name': '利桑德罗·马丁内斯', 'value_m': 40, 'club': '曼联', 'top5': True, 'pos': 'CB'},
        ],
    },
    '奥地利': {
        'rank': 24,
        'pre_goals_per_game': 1.7,
        'total_value_m': 44,
        'top5_count': 4,
        'top5_attackers': 2,
        'giant_killings': [],
        'players': [
            {'name': '马尔科·阿瑙托维奇', 'value_m': 3.5, 'club': '国际米兰', 'top5': True, 'pos': 'FW'},
            {'name': '马塞尔·萨比策', 'value_m': 6, 'club': '多特蒙德', 'top5': True, 'pos': 'MF'},
            {'name': '大卫·阿拉巴', 'value_m': 3, 'club': '皇家马德里', 'top5': True, 'pos': 'CB'},
            {'name': '康拉德·莱默尔', 'value_m': 32, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'MF'},
        ],
    },
    '阿尔及利亚': {
        'rank': 37,
        'pre_goals_per_game': 1.3,
        'total_value_m': 14,
        'top5_count': 2,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '利雅德·马赫雷斯', 'value_m': 8, 'club': '吉达国民', 'top5': False, 'pos': 'FW'},
            {'name': '艾萨·曼迪', 'value_m': 1, 'club': '里尔', 'top5': True, 'pos': 'CB'},
            {'name': '纳比勒·本塔莱布', 'value_m': 5, 'club': '里尔', 'top5': True, 'pos': 'MF'},
        ],
    },
    '约旦': {
        'rank': 80,
        'pre_goals_per_game': 0.6,
        'total_value_m': 10,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '穆萨·塔马里', 'value_m': 10, 'club': '里尔', 'top5': True, 'pos': 'FW'},
            {'name': '阿里·乌勒万', 'value_m': 0.5, 'club': '豪尔', 'top5': False, 'pos': 'FW'},
        ],
    },
    '葡萄牙': {
        'rank': 6,
        'pre_goals_per_game': 2.2,
        'total_value_m': 467,
        'top5_count': 5,
        'top5_attackers': 4,
        'giant_killings': [],
        'players': [
            {'name': '克里斯蒂亚诺·罗纳尔多', 'value_m': 10, 'club': '利雅得胜利', 'top5': False, 'pos': 'FW'},
            {'name': '维蒂尼亚', 'value_m': 140, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'MF'},
            {'name': '若昂·内维斯', 'value_m': 140, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'MF'},
            {'name': '贝尔纳多·席尔瓦', 'value_m': 22, 'club': '曼城', 'top5': True, 'pos': 'MF'},
            {'name': '布鲁诺·费尔南德斯', 'value_m': 35, 'club': '曼联', 'top5': True, 'pos': 'MF'},
            {'name': '迪奥戈·科斯塔', 'value_m': 40, 'club': '波尔图', 'top5': False, 'pos': 'GK'},
            {'name': '努诺·门德斯', 'value_m': 80, 'club': '巴黎圣日耳曼', 'top5': True, 'pos': 'LB'},
        ],
    },
    '哥伦比亚': {
        'rank': 13,
        'pre_goals_per_game': 1.5,
        'total_value_m': 90,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '路易斯·迪亚斯', 'value_m': 70, 'club': '利物浦', 'top5': True, 'pos': 'FW'},
            {'name': '哈梅斯·罗德里格斯', 'value_m': 2, 'club': '明尼苏达联', 'top5': False, 'pos': 'MF'},
            {'name': '达文森·桑切斯', 'value_m': 18, 'club': '加拉塔萨雷', 'top5': False, 'pos': 'CB'},
            {'name': '戴维·奥斯皮纳', 'value_m': 0.2, 'club': '国民竞技', 'top5': False, 'pos': 'GK'},
        ],
    },
    '刚果(金)': {
        'rank': 65,
        'pre_goals_per_game': 0.5,
        'total_value_m': 28,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '约安·维萨', 'value_m': 28, 'club': '布伦特福德', 'top5': True, 'pos': 'FW'},
        ],
    },
    '乌兹别克斯坦': {
        'rank': 50,
        'pre_goals_per_game': 0.8,
        'total_value_m': 54,
        'top5_count': 2,
        'top5_attackers': 0,
        'giant_killings': [],
        'players': [
            {'name': '阿卜杜科迪尔·胡桑诺夫', 'value_m': 50, 'club': '曼城', 'top5': True, 'pos': 'CB'},
            {'name': '肖穆罗多夫', 'value_m': 4, 'club': '罗马', 'top5': True, 'pos': 'FW'},
        ],
    },
    '英格兰': {
        'rank': 4,
        'pre_goals_per_game': 2.3,
        'total_value_m': 450,
        'top5_count': 6,
        'top5_attackers': 4,
        'giant_killings': [],
        'players': [
            {'name': '裘德·贝林厄姆', 'value_m': 130, 'club': '皇家马德里', 'top5': True, 'pos': 'MF'},
            {'name': '德克兰·赖斯', 'value_m': 120, 'club': '阿森纳', 'top5': True, 'pos': 'MF'},
            {'name': '布卡约·萨卡', 'value_m': 110, 'club': '阿森纳', 'top5': True, 'pos': 'FW'},
            {'name': '哈里·凯恩', 'value_m': 60, 'club': '拜仁慕尼黑', 'top5': True, 'pos': 'FW'},
            {'name': '乔丹·皮克福德', 'value_m': 15, 'club': '埃弗顿', 'top5': True, 'pos': 'GK'},
            {'name': '约翰·斯通斯', 'value_m': 15, 'club': '曼城', 'top5': True, 'pos': 'CB'},
        ],
    },
    '克罗地亚': {
        'rank': 12,
        'pre_goals_per_game': 1.5,
        'total_value_m': 91,
        'top5_count': 3,
        'top5_attackers': 1,
        'giant_killings': ['2018亚军·2022季军'],
        'players': [
            {'name': '卢卡·莫德里奇', 'value_m': 4, 'club': '皇家马德里', 'top5': True, 'pos': 'MF'},
            {'name': '约什科·格瓦迪奥尔', 'value_m': 70, 'club': '曼城', 'top5': True, 'pos': 'CB'},
            {'name': '马特奥·科瓦契奇', 'value_m': 12, 'club': '曼城', 'top5': True, 'pos': 'MF'},
            {'name': '多米尼克·利瓦科维奇', 'value_m': 4, 'club': '萨格勒布迪纳摩', 'top5': False, 'pos': 'GK'},
            {'name': '伊万·佩里西奇', 'value_m': 1.3, 'club': '埃因霍温', 'top5': False, 'pos': 'FW'},
        ],
    },
    '加纳': {
        'rank': 45,
        'pre_goals_per_game': 1.3,
        'total_value_m': 65,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '安托万·塞门约', 'value_m': 65, 'club': '曼城', 'top5': True, 'pos': 'FW'},
        ],
    },
    '巴拿马': {
        'rank': 58,
        'pre_goals_per_game': 0.7,
        'total_value_m': 7,
        'top5_count': 1,
        'top5_attackers': 1,
        'giant_killings': [],
        'players': [
            {'name': '迈克尔·穆里略', 'value_m': 7, 'club': '马赛', 'top5': True, 'pos': 'MF'},
            {'name': '伊斯梅尔·迪亚斯', 'value_m': 0, 'club': '—', 'top5': False, 'pos': 'FW'},
            {'name': '奥兰多·莫斯克拉', 'value_m': 0, 'club': '—', 'top5': False, 'pos': 'GK'},
        ],
    },
}

def opponent_quality(team_name: str) -> dict:
    """获取对手质量数据 (支持中/英文名)

    🆕 V3.3: 返回数据包含 players (球员详情) + top5_players (向后兼容别名)
    """
    # 内部函数: 补充兼容字段
    def _normalize(data):
        if 'players' in data and 'top5_players' not in data:
            # 向后兼容: 从players提取旧格式的top5_players列表
            data['top5_players'] = [
                f"{p['name']}({p['pos']}/{p['club']})"
                for p in data['players']
            ]
        elif 'players' not in data:
            data['players'] = []
            data['top5_players'] = data.get('top5_players', [])
            data['total_value_m'] = data.get('total_value_m', 0)
            data['top5_attackers'] = data.get('top5_attackers', 0)
        return data

    if team_name in OPPONENT_DB:
        return _normalize(OPPONENT_DB[team_name].copy())

    # 英文名→中文名映射
    EN_MAP = {
        'South Africa': '南非', 'Czech Republic': '捷克', 'Czech': '捷克',
        'Bosnia & Herzegovina': '波黑', 'Bosnia': '波黑',
        'Paraguay': '巴拉圭', 'Qatar': '卡塔尔', 'Morocco': '摩洛哥',
        'Haiti': '海地', 'Turkey': '土耳其', 'Tunisia': '突尼斯',
        'Curaçao': '库拉索', 'Japan': '日本', 'Ecuador': '厄瓜多尔',
        'Cape Verde': '佛得角', 'Egypt': '埃及', 'Saudi Arabia': '沙特阿拉伯',
        'Uruguay': '乌拉圭', 'New Zealand': '新西兰', 'Iran': '伊朗',
        'Senegal': '塞内加尔', 'Iraq': '伊拉克', 'Algeria': '阿尔及利亚',
        'Jordan': '约旦', 'DR Congo': '民主刚果', 'Congo DR': '民主刚果',
        'Croatia': '克罗地亚', 'Ghana': '加纳', 'Panama': '巴拿马',
        'Colombia': '哥伦比亚', 'Uzbekistan': '乌兹别克斯坦',
        'Norway': '挪威', 'Scotland': '苏格兰', 'Austria': '奥地利',
        'Switzerland': '瑞士', 'South Korea': '韩国', 'Korea Republic': '韩国',
        'Australia': '澳大利亚', 'Canada': '加拿大',
        'Portugal': '葡萄牙', 'England': '英格兰', 'France': '法国', 'Brazil': '巴西',
        'Argentina': '阿根廷', 'Spain': '西班牙', 'Mexico': '墨西哥', 'USA': '美国',
    }
    cn = EN_MAP.get(team_name, team_name)
    if cn in OPPONENT_DB:
        return _normalize(OPPONENT_DB[cn].copy())

    # 模糊匹配中文 (使用翻译后的中文名)
    for name, data in OPPONENT_DB.items():
        if cn in name or name in cn:
            return _normalize(data.copy())

    return _normalize({
        'rank': 50, 'players': [], 'top5_players': [], 'giant_killings': [],
        'pre_goals_per_game': 1.0, 'total_value_m': 0, 'top5_attackers': 0,
        'notes': '无数据·使用默认值'
    })


def check_three_conditions(team_name: str) -> dict:
    """
    BIG三条件检查 (V3.3: 球员身价感知)

    条件:
      (a) 对手排名50+ (FIFA排名)
      (b) 无五大联赛高价值射手 (身价≥€10M 且 五大联赛)
      (c) 无世界杯爆冷历史

    Returns:
      {'all_pass': bool, 'passed': int, 'total': 3,
       'conditions': {a/b/c}, 'fail_reason': str, 'quality_score': int}
    """
    data = opponent_quality(team_name)

    a_pass = data['rank'] >= 50  # V3.2: 60→50

    # 🆕 V3.3: 条件b — 球员身价感知
    # 仅计算五大联赛+身价≥€10M的进攻球员
    # 身价未知(—)的球员不自动视为威胁 (如Shomurodov/罗马替补)
    DEFENSIVE_POS = {'CB', 'LB', 'RB', 'GK', 'DF', 'WB', 'SW'}
    MIN_ATTACKER_VALUE = 5  # 🆕 V3.3: 仅过滤已知低身价(0<€<5M)·未知身价(€0)保留
    scorers = []
    # 🆕 V3.3: 优先使用 players (dict格式·含身价), 回退到 top5_players (旧string格式)
    player_list = data.get('players', data.get('top5_players', []))
    for p in player_list:
        if isinstance(p, dict):
            pos = p.get('pos', '')
            value_m = p.get('value_m', 0)
            top5 = p.get('top5', False)
            # 🆕 V3.3: 未知身价(€0=—)保留·仅过滤已知低身价(0<€<5M)
            if pos not in DEFENSIVE_POS and top5 and (value_m == 0 or value_m >= MIN_ATTACKER_VALUE):
                scorers.append(f"{p['name']}({pos}/€{value_m:.0f}M)")
        else:
            # 旧格式兼容
            parts = p.split('(')
            pos = parts[-1].replace(')', '').split('/')[0] if len(parts) >= 2 else ''
            if pos not in DEFENSIVE_POS:
                scorers.append(p)

    if len(scorers) == 0:
        b_pass = True
    elif len(scorers) == 1 and data['pre_goals_per_game'] < 1.0:
        # 🆕 V3.3: 单攻击手+弱攻击力→例外 (阈值0.8→1.0)
        b_pass = True
    else:
        b_pass = False

    c_pass = len(data['giant_killings']) == 0

    passed = sum([a_pass, b_pass, c_pass])
    fail_reasons = []
    if not a_pass:
        fail_reasons.append(f"排名{data['rank']}<50")
    if not b_pass:
        fail_reasons.append(f"五大射手: {', '.join(scorers)}")
    if not c_pass:
        fail_reasons.append(f"巨人杀手血统: {', '.join(data['giant_killings'])}")

    # V2.6规则: 三项全满足 → 热门仍赢; 缺一 → 热门不胜
    rule = '热门仍赢·不穿盘 (唯一例外)' if passed == 3 else '默认热门不胜'

    return {
        'all_pass': passed == 3,
        'passed': passed,
        'total': 3,
        'conditions': {
            'a_rank60plus': a_pass,
            'b_no_top5_scorer': b_pass,
            'c_no_giant_killing': c_pass,
        },
        'fail_reason': ' | '.join(fail_reasons) if fail_reasons else '三项全满足',
        'rule': rule,
        'quality_score': 3 - passed,  # 0=最弱(全满足), 3=最强(全不满足)
        'scorers': scorers,  # 🆕 V3.4: 过滤后的五大射手列表 (供显示用)
        'data': data,
    }


def check_moderate_opponent(team_name: str) -> dict:
    """
    MODERATE对手质量过滤: 检测是否有萨拉赫级攻击手
    """
    data = opponent_quality(team_name)
    has_threat = len(data['top5_players']) > 0 and data['pre_goals_per_game'] >= 1.5

    return {
        'has_goal_threat': has_threat,
        'top_players': data['top5_players'],
        'goals_per_game': data['pre_goals_per_game'],
        'rule': '热门不胜' if has_threat else '热门仍赢·可能穿盘',
    }


# ── 命令行 ──
if __name__ == '__main__':
    import sys
    teams = sys.argv[1:] if len(sys.argv) > 1 else ['沙特', '海地', '摩洛哥', '新西兰', '伊拉克']
    for team in teams:
        result = check_three_conditions(team)
        mod = check_moderate_opponent(team)
        print(f'{team}: 三条件 {result["passed"]}/3 [{result["fail_reason"]}] → {result["rule"]}')
        if mod['has_goal_threat']:
            print(f'  MOD: ⚠️ 有进攻威胁 ({", ".join(mod["top_players"])})')

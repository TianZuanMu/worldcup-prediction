# -*- coding: utf-8 -*-
"""V3: 简化解析器 - 按结构分割, 逐队精确提取"""
import re, json
from pathlib import Path
from collections import OrderedDict

txt = Path(r"C:\Users\A\PyCharmMiscProject\近期状态.txt").read_text(encoding='utf-8')

RANK = {
    '法国':1,'西班牙':2,'阿根廷':3,'英格兰':4,'巴西':5,'葡萄牙':6,'德国':7,'荷兰':8,
    '比利时':9,'意大利':10,'克罗地亚':11,'哥伦比亚':13,'墨西哥':14,'塞内加尔':15,
    '乌拉圭':16,'俄罗斯':19,'伊朗':20,'土耳其':22,'厄瓜多尔':23,'日本':24,
    '韩国':25,'摩洛哥':26,'瑞典':27,'阿尔及利亚':28,'埃及':29,'加拿大':30,
    '美国':31,'奥地利':32,'乌克兰':33,'丹麦':34,'瑞士':35,'澳大利亚':36,
    '苏格兰':37,'挪威':38,'巴拉圭':39,'捷克':40,'波兰':41,'塞尔维亚':42,
    '希腊':43,'罗马尼亚':44,'突尼斯':45,'刚果(金)':46,'波黑':47,'巴拿马':48,
    '爱尔兰':49,'乌兹别克斯坦':50,'威尔士':51,'北爱尔兰':52,'斯洛文尼亚':53,
    '约旦':55,'卡塔尔':56,'伊拉克':57,'科特迪瓦':58,'南非':60,'沙特阿拉伯':61,
    '中国':63,'委内瑞拉':64,'秘鲁':65,'智利':66,'佛得角':67,'尼日利亚':68,
    '喀麦隆':69,'马里':70,'海地':71,'加纳':73,'冰岛':78,'芬兰':79,
    '新西兰':80,'哥斯达黎加':81,'库拉索':82,'洪都拉斯':83,'萨尔瓦多':84,
    '危地马拉':85,'特立尼达和多巴哥':86,'玻利维亚':87,'牙买加':88,'冈比亚':89,
    '科索沃':90,'北马其顿':93,'赞比亚':75,'加蓬':76,'多米尼加共和国':96,
    '尼加拉瓜':97,'马达加斯加':98,'毛里塔尼亚':99,'安道尔':200,'百慕大群岛':195,
    '阿鲁巴':200,'波多黎各':200,'日本U19':200,'费城联合B队':200,'百慕大':195,
    '黑山':94,'亚美尼亚':91,'阿尔巴尼亚':92,
}

# 队伍名称别名 (文本中出现 → 标准名)
ALIAS = {
    '沙特队': '沙特阿拉伯', '沙特': '沙特阿拉伯',
    '刚果（金）': '刚果(金)',
}

def canonical(team):
    return ALIAS.get(team, team)

def parse_all():
    """扫描所有行, 找到队伍段落后解析比赛表格"""
    lines = txt.split('\n')
    results = OrderedDict()
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 检测队伍段落标题: "XX队近5场", "XX国家队近5场", "XX在近5场"
        m = re.match(r'^(.+?)(?:国家)?队?(?:在)?(?:近5场|近期).*(?:比赛|战绩|状态)', line)
        if not m:
            i += 1
            continue

        team_raw = m.group(1).strip()
        team = canonical(team_raw)

        # 跳过已处理的队伍
        if team in results:
            i += 1
            continue

        # 收集该队伍的比赛行(直到空行或下一队伍)
        j = i + 1
        match_lines = []
        while j < len(lines):
            nl = lines[j].strip()
            # 遇到下一队伍标题则停止
            if re.match(r'^(.+?)(?:国家)?队?(?:在)?(?:近5场|近期).*(?:比赛|战绩|状态)', nl):
                break
            # tab分隔的行=比赛数据行
            if '\t' in nl:
                parts = nl.split('\t')
                if len(parts) >= 3:
                    match_lines.append(parts)
            j += 1

        # 解析比赛数据
        matches = []
        for parts in match_lines:
            # 日期
            ds = parts[0].strip()
            dm = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', ds)
            if dm:
                date = f"{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
            else:
                dm2 = re.search(r'(\d{4})年(\d{1,2})月', ds)
                if dm2:
                    date = f"{int(dm2.group(1)):04d}-{int(dm2.group(2)):02d}-15"
                else:
                    continue

            if int(date[:4]) < 2025:
                continue

            # 对阵
            matchup = parts[1].strip()
            vs_parts = re.split(r'\s+vs\s+', matchup, flags=re.IGNORECASE)
            if len(vs_parts) != 2:
                continue
            team_a, team_b = vs_parts[0].strip(), vs_parts[1].strip()

            # 比分
            score_str = parts[2].strip()
            sm = re.search(r'(\d+)\s*[-–—]\s*(\d+)', score_str)
            if not sm:
                continue
            g1, g2 = int(sm.group(1)), int(sm.group(2))

            # 判断方向
            if team in team_a or team_a in team or team_a == team:
                opponent = canonical(team_b)
                home_away = 'home'
                my_goals, opp_goals = g1, g2
            elif team in team_b or team_b in team or team_b == team:
                opponent = canonical(team_a)
                home_away = 'away'
                my_goals, opp_goals = g2, g1
            else:
                continue

            result = 'W' if my_goals > opp_goals else ('D' if my_goals == opp_goals else 'L')
            opp_rank = RANK.get(opponent, 50)

            matches.append({
                'opponent': opponent, 'result': result,
                'score': f'{my_goals}-{opp_goals}',
                'opponent_rank': opp_rank, 'home_away': home_away,
                'is_official': True, 'key_players': 11, 'date': date,
            })

        # 去重+排序+取最近5场
        seen = set()
        unique = []
        for m in sorted(matches, key=lambda x: x['date'], reverse=True):
            key = (m['date'], m['opponent'])
            if key not in seen:
                seen.add(key)
                unique.append(m)

        if unique:
            results[team] = unique[:5]

        i = j  # 跳过已处理的队伍段落

    return results

all_data = parse_all()
print(f"Found {len(all_data)} teams\n")

for team, matches in all_data.items():
    print(f"{team} ({len(matches)} matches):")
    for m in matches:
        print(f"  {m['date']} {m['home_away']:4s} vs {m['opponent']:12s} {m['score']:5s} ({m['result']}) r={m['opponent_rank']}")

# 输出Python代码
print("\n\n# ===== RECENT_RESULTS UPDATE =====")
print("RECENT_RESULTS = {")
for team in sorted(all_data.keys()):
    matches = all_data[team]
    print(f'    "{team}": [')
    for m in matches:
        print(f'        {{"opponent": "{m["opponent"]}", "result": "{m["result"]}", '
              f'"score": "{m["score"]}", "opponent_rank": {m["opponent_rank"]}, '
              f'"home_away": "{m["home_away"]}", "is_official": True, '
              f'"key_players": 11, "date": "{m["date"]}"}},')
    print('    ],')
print("}")

total = sum(len(v) for v in all_data.values())
print(f"\n# Total: {len(all_data)} teams, {total} matches")
missing5 = [(t, len(m)) for t, m in all_data.items() if len(m) < 5]
if missing5:
    print(f"# <5 matches: {missing5}")

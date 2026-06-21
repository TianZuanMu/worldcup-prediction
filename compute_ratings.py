# -*- coding: utf-8 -*-
"""
V3.30: 48队三维评分计算引擎
P0: 联赛分级替代top5二元标记
P1: 顶级边卫攻防双贡献加成
P2: 国家队出场经验加权

用法:
  python compute_ratings.py          # 打印评分表
  python compute_ratings.py --save   # 更新team_ratings.py
"""

import sys, math, json, os

# ═══════════════════════════════════════════════════════════════
# P0: 联赛分级 (替代top5二元标记)
# ═══════════════════════════════════════════════════════════════
# Tier 1: 五大联赛精英俱乐部
# Tier 2: 五大联赛其他俱乐部
# Tier 3: 非五大但欧冠常客 (Celtic, Ajax, Porto, Benfica, 萨尔茨堡等)
# Tier 4: 其他联赛

ELITE_CLUBS = {
    '皇家马德里': 1.5, '曼城': 1.5, '拜仁慕尼黑': 1.5, '巴塞罗那': 1.4,
    '阿森纳': 1.35, '利物浦': 1.35, '巴黎圣日耳曼': 1.35, '切尔西': 1.3,
    '国际米兰': 1.3, '尤文图斯': 1.25, '曼联': 1.2, '热刺': 1.15,
    '那不勒斯': 1.15, '多特蒙德': 1.15, '马德里竞技': 1.2, '勒沃库森': 1.15,
}

# P0: 非五大但具欧冠/欧联竞争力的俱乐部 (替代一刀切的0.7惩罚)
UCL_REGULARS = {
    '凯尔特人', '流浪者', '阿贾克斯', '埃因霍温', '费耶诺德',
    '波尔图', '本菲卡', '葡萄牙体育', '萨尔茨堡红牛', '萨格勒布迪纳摩',
    '布鲁日', '亨克', '顿涅茨克矿工', '加拉塔萨雷', '哥本哈根',
    '奥林匹亚科斯', '贝尔格莱德红星', '布拉格斯拉维亚',
}

def get_league_tier(club: str, top5: bool) -> float:
    """
    P0: 联赛分级权重
    Tier1 (精英): 1.0 · Tier2 (五大): 0.85 · Tier3 (欧冠常客): 0.80 · Tier4 (其他): 0.7
    """
    if club in ELITE_CLUBS:
        return 1.0
    if top5:
        return 0.85
    if club in UCL_REGULARS:
        return 0.80
    return 0.7


# ═══════════════════════════════════════════════════════════════
# 从opponent_db加载数据
# ═══════════════════════════════════════════════════════════════

def load_team_data():
    """加载48队数据"""
    import opponent_db
    return opponent_db.OPPONENT_DB


# ═══════════════════════════════════════════════════════════════
# 核心计算
# ═══════════════════════════════════════════════════════════════

def compute_all_ratings():
    """计算全部48队三维评分"""
    teams = load_team_data()
    from midfield_quality import get_midfield_rating

    results = []
    for team_name, data in teams.items():
        rank = data.get('rank', 99)
        total_val = data.get('total_value_m', 0)
        top5_count = data.get('top5_count', 0)
        pre_gpg = data.get('pre_goals_per_game', 0)
        giant_killings = data.get('giant_killings', [])
        players = data.get('players', [])

        atk_weighted = 0.0; atk_elite = 0
        def_weighted = 0.0; def_elite = 0
        gk_best_val = 0; gk_best_mult = 1.0

        for p in players:
            pos = p.get('pos', 'XX')
            val = p.get('value_m', 0) or 0
            t5 = p.get('top5', False)
            club = p.get('club', '')
            sg = p.get('season_goals', 0) or 0
            ig = p.get('intl_goals', 0) or 0
            caps = p.get('intl_caps', 0) or 0

            # P0: 联赛分级权重 + 精英俱乐部叠加
            league_mult = get_league_tier(club, t5)
            elite_mult = ELITE_CLUBS.get(club, 1.0)  # 精英俱乐部额外加成
            combined_mult = league_mult * elite_mult

            if pos in ('FW','ST','CF','LW','RW','WG','SS'):
                atk_weighted += val * combined_mult + (sg*2.5 + ig*3.0) * combined_mult
                if elite_mult >= 1.3: atk_elite += 1
            elif pos in ('MF','AM','DM','CM','AMF'):
                gc = sg*2.5 + ig*3.0
                if gc >= 20:
                    atk_weighted += val*combined_mult*0.7 + gc*combined_mult*0.6
                    if elite_mult >= 1.3: atk_elite += 1
                elif gc >= 10:
                    atk_weighted += gc*combined_mult*0.5
            elif pos in ('CB','RB','LB','DF'):
                # P1: 顶级边卫攻防双贡献 — FB身价≥20M+精英俱乐部→轻量加成
                fb_bonus = 1.10 if (pos in ('RB','LB') and val >= 20 and league_mult >= 0.85) else 1.0
                # P2: 国家队出场经验加权 (caps>=80→+12%, caps>=50→+8%)
                caps_bonus = 1.12 if caps >= 80 else (1.08 if caps >= 50 else 1.0)
                # 身价分层
                if val >= 30: tier = 1.3
                elif val >= 15: tier = 1.0
                else: tier = 0.7
                weighted = val * combined_mult * tier * fb_bonus * caps_bonus
                def_weighted += weighted
                if val >= 30: def_elite += 1
            elif pos == 'GK':
                if val > gk_best_val:
                    gk_best_val = val; gk_best_mult = league_mult * elite_mult

        # === ATTACK (V3.28逻辑·保持不变) ===
        atk_log = math.log(atk_weighted + 1) / math.log(1700) * 8.0 if atk_weighted > 5 else atk_weighted / 20 * 3.0
        atk_score = min(10.0, max(0.5, atk_log*0.55 + min(3.0, pre_gpg*1.2) + min(2.5, atk_elite*0.7) + min(1.5, len(giant_killings)*0.5)))

        # === DEFENSE (P0-P2已融入def_weighted) ===
        def_log = math.log(def_weighted + 1) / math.log(380) * 7.5 if def_weighted > 5 else def_weighted / 20 * 3.0
        gk_score = math.log(gk_best_val*gk_best_mult + 1) / math.log(30) * 2.2
        def_score = min(10.0, max(0.5, def_log*0.55 + min(2.5, def_elite*0.7) + gk_score))

        # === MIDFIELD ===
        mf_score = get_midfield_rating(team_name)

        # === OVERALL ===
        overall = round((atk_score*0.35 + mf_score*0.35 + def_score*0.30), 1)

        results.append((
            rank, team_name, total_val,
            round(atk_score,1), round(mf_score,1), round(def_score,1), overall,
            round(def_weighted,0), def_elite
        ))

    results.sort(key=lambda x: x[0])
    return results


# ═══════════════════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════════════════

def print_table(results):
    print(f" {'#':>3s} {'球队':<10s} {'身价M':>6s} {'攻击':>5s} {'中场':>5s} {'防守':>5s} {'综合':>5s}  Tier | defW  eD")
    print('─' * 75)
    for r in results:
        rank, name, val, atk, mf, df, ov, dw, ed = r
        tier = 'S' if ov>=8.5 else ('A' if ov>=7.5 else ('B+' if ov>=6.5 else ('B' if ov>=5.5 else ('C' if ov>=4.0 else 'D'))))
        print(f'{rank:3d} {name:<10s} {val:6.0f} {atk:5.1f} {mf:5.1f} {df:5.1f} {ov:5.1f}  {tier:<2s} | {dw:4.0f} {ed:2d}')

    tiers = {'S': [], 'A': [], 'B+': [], 'B': [], 'C': [], 'D': []}
    for r in results:
        ov = r[6]; t = 'S' if ov>=8.5 else ('A' if ov>=7.5 else ('B+' if ov>=6.5 else ('B' if ov>=5.5 else ('C' if ov>=4.0 else 'D'))))
        tiers[t].append((r[1], ov))
    print()
    for t in ['S','A','B+','B','C','D']:
        items = tiers[t]
        if items:
            print(f'{t} ({len(items)}队): {", ".join(f"{n} {v:.1f}" for n,v in sorted(items, key=lambda x: -x[1]))}')


def save_to_team_ratings(results):
    """更新team_ratings.py静态表"""
    path = os.path.join(os.path.dirname(__file__), 'team_ratings.py')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到_RAW列表并替换
    import re
    lines = []
    for r in results:
        rank, name, val, atk, mf, df, ov, dw, ed = r
        tier = 'S' if ov>=8.5 else ('A' if ov>=7.5 else ('B+' if ov>=6.5 else ('B' if ov>=5.5 else ('C' if ov>=4.0 else 'D'))))
        lines.append(f"    ({rank:3d},  '{name}',{' '*(15-len(name))}{val:5.0f},    {atk:.1f},  {mf:.1f},  {df:.1f},  {ov:.1f},  '{tier}'),")

    # 替换_RAW数组内容
    pattern = r'(_RAW = \[).*?(\]$)'
    new_raw = '_RAW = [\n' + '\n'.join(lines) + '\n]'
    content = re.sub(pattern, new_raw, content, flags=re.MULTILINE | re.DOTALL)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✅ 已更新 {path}')


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    results = compute_all_ratings()
    print_table(results)

    if '--save' in sys.argv:
        save_to_team_ratings(results)

    # 关键对比
    print()
    print('=== P0-P2 关键球队对比 ===')
    for t in ['苏格兰', '英格兰', '加拿大', '挪威', '墨西哥']:
        for r in results:
            if r[1] == t:
                old = {'苏格兰': 3.2, '英格兰': 6.7, '加拿大': 4.9, '挪威': 3.6, '墨西哥': 3.3}.get(t, 0)
                print('%s: 防守 %.1f→%.1f (%+.1f) | defW=%.0f eD=%d' % (t, old, r[5], r[5]-old, r[7], r[8]))
                break

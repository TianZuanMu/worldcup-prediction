# -*- coding: utf-8 -*-
"""
P2增强模块
P2-1: 淘汰赛路径量化评分
P2-2: 无必发场次热度估算
P2-3: 首轮谨慎系数
"""

# ── P2-1: 淘汰赛路径量化 ──
# 基于FIFA排名估算对手强度分 (1-10, 越高越难)
FIFA_RANK = {
    "阿根廷": 1, "法国": 2, "西班牙": 3, "英格兰": 4, "巴西": 5,
    "葡萄牙": 6, "荷兰": 7, "德国": 8, "比利时": 9, "克罗地亚": 10,
    "意大利": 11, "摩洛哥": 12, "乌拉圭": 13, "哥伦比亚": 14, "墨西哥": 15,
    "日本": 18, "韩国": 25, "澳大利亚": 27, "伊朗": 30, "瑞典": 25,
    "埃及": 30, "科特迪瓦": 50, "厄瓜多尔": 35, "加纳": 60, "突尼斯": 35,
    "沙特": 55, "约旦": 70, "库拉索": 84, "海地": 83, "南非": 60,
    "巴拿马": 65, "新西兰": 80, "佛得角": 70, "民主刚果": 65,
    "伊拉克": 68, "挪威": 12, "塞内加尔": 20, "阿尔及利亚": 32,
    "奥地利": 28, "乌兹别克": 55,
}

def opponent_strength(team_name):
    """基于FIFA排名估算对手强度分 1-10"""
    rank = FIFA_RANK.get(team_name, 50)
    if rank <= 10: return 9
    if rank <= 20: return 7
    if rank <= 30: return 5
    if rank <= 50: return 3
    return 2

def knockout_path_score(group_pos, possible_opponents):
    """
    淘汰赛路径评分 (1-10, 越高越难)
    group_pos: '1st'/'2nd'/'3rd'
    possible_opponents: [对手名列表]
    """
    if not possible_opponents:
        return 5  # unknown

    # 取对手强度平均
    scores = [opponent_strength(o) for o in possible_opponents]
    avg = sum(scores) / len(scores)

    # 小组排名修正
    if group_pos == '1st':
        avg *= 0.7   # 小组第一打第三/第二, 路径轻松
    elif group_pos == '2nd':
        avg *= 1.1   # 小组第二打第二/第一, 路径中等
    else:
        avg *= 1.5   # 小组第三打第一, 路径硬

    return round(min(avg, 10), 1)


def path_motivation(path1_score, path2_score):
    """路径差驱动的战意加成 (0-5分)"""
    diff = path2_score - path1_score
    if diff >= 3: return 5   # 极端动力(如C1vsC2差3档)
    if diff >= 2: return 4
    if diff >= 1: return 2
    return 0


# ── P2-2: 无必发场次热度估算 ──
def estimate_heat(initial_implied_pct, is_world_cup=True):
    """
    基于初盘隐胜估算临场热度
    世界杯散户溢价约+10-15%
    """
    if not initial_implied_pct:
        return None, "no_data"
    heat = float(initial_implied_pct.replace('%', '')) * 1.12
    confidence = "low"  # 估算值·低可信度
    return round(heat, 1), confidence


# ── P2-3: 首轮谨慎系数 ──
def first_round_under_modifier(is_first_round=True):
    """
    首轮比赛进球预期修正
    7/8场首轮≤3球, 场均1.86球(去美巴异常)
    """
    if is_first_round:
        return 1.10  # Under信号增强10%
    return 1.0


# ── 测试 ──
if __name__ == "__main__":
    # P2-1
    print("=== 淘汰赛路径评分 ===")
    # B1 vs 3rd(E/F/G/I/J)
    score_b1 = knockout_path_score('1st', ['科特迪瓦','伊朗','加纳','瑞典','约旦'])
    # B2 vs A2
    score_b2 = knockout_path_score('2nd', ['韩国'])
    print(f"瑞士 B1: {score_b1}/10, B2: {score_b2}/10, 动力: {path_motivation(score_b1, score_b2)}/5")

    # C1 vs F2
    score_c1 = knockout_path_score('1st', ['埃及'])
    # C2 vs F1
    score_c2 = knockout_path_score('2nd', ['比利时'])
    print(f"巴西/摩 C1: {score_c1}/10, C2: {score_c2}/10, 动力: {path_motivation(score_c1, score_c2)}/5")

    # P2-2
    print(f"\n=== 热度估算 ===")
    h, c = estimate_heat('52.8%')
    print(f"隐胜52.8% → 估热{h}% (可信度:{c})")

    # P2-3
    print(f"\n=== 首轮系数 ===")
    print(f"Under修正: ×{first_round_under_modifier()}")

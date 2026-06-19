#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
体育博彩对冲计算器 v5.0 - 亚盘结算修正版
- 正确处理走水、赢半、输半
- 单盘对冲提供真实盈亏范围与 minimax 对冲方案
- 双盘完美对冲消除所有风险
- 支持胜平负、让球盘、大小球（大小球同样可能存在半盘，本版暂以全盘处理，后续可扩展）
"""

import itertools

def asian_return(handicap, odds, stake, home_goals_diff):
    """
    计算亚盘投注的回报（含本金）
    handicap : 主队让球数（例如 -1.0, -0.75, +0.5）
    odds     : 投注赔率（十进制）
    stake    : 下注金额
    home_goals_diff : 主队净胜球（可为负）
    """
    # 调整后净胜球
    adj = home_goals_diff + handicap
    # 判断输赢
    if handicap == int(handicap):  # 整数盘
        if adj > 0:
            return stake * odds
        elif adj == 0:
            return stake  # 走水
        else:
            return 0.0
    elif handicap * 2 == int(handicap * 2):  # 半整数盘（如 -0.5, +1.5）
        if adj > 0:
            return stake * odds
        else:
            return 0.0
    else:  # 0.25 或 0.75 盘
        # 将盘口拆分为两个相邻整数盘的一半
        base = int(handicap) if handicap > 0 else -int(abs(handicap))  # 截断小数部分
        if abs(handicap - base) < 0.6:  # 0.25盘
            lower = base
            upper = base + 0.5 if handicap > 0 else base - 0.5
        else:  # 0.75盘
            lower = base + 0.5 if handicap > 0 else base - 0.5
            upper = base + 1 if handicap > 0 else base - 1
        # 结算：一半筹码押lower，一半押upper
        ret = 0.0
        # 对于 lower 盘口，结算看 adj_lower = home_goals_diff + lower
        adj_lower = home_goals_diff + lower
        if adj_lower > 0:
            ret += 0.5 * stake * odds
        elif adj_lower == 0:
            ret += 0.5 * stake  # 走水
        # 对于 upper 盘口
        adj_upper = home_goals_diff + upper
        if adj_upper > 0:
            ret += 0.5 * stake * odds
        elif adj_upper == 0:
            ret += 0.5 * stake
        # 如果两种情况都输，则 +=0
        return ret


def get_critical_diffs(h1, h2):
    """返回需要考虑的所有关键净胜球值（整数和半整数）"""
    diffs = set()
    for h in [h1, h2]:
        # 对于整数盘，临界点为 -h, -h+1 等，但走水只在 -h
        if h == int(h):
            diffs.add(-h)
        # 对于半盘，临界点为 -h-0.5 和 -h+0.5? 实际全赢/全输切换在 -h，没有走水
        elif h * 2 == int(h * 2):
            diffs.add(-h - 0.5)
            diffs.add(-h + 0.5)
        else:  # 0.25/0.75
            # 需要所有整数和半整数点来捕获半赢半输的变化
            for g in range(-5, 6):  # 足够覆盖
                diffs.add(g)
                diffs.add(g + 0.5)
    # 扩展覆盖范围，确保包含 -10 到 10
    diffs = [d for d in diffs if -10 <= d <= 10]
    diffs.sort()
    return diffs


def single_opponent_hedge(my_handicap, my_odds, my_stake, opp_handicap, opp_odds):
    """
    计算单个对手盘的 minimax 对冲方案
    返回: (best_x, max_loss, details) 其中 details 列出各区间盈亏
    """
    # 关键净胜球值
    crit = get_critical_diffs(my_handicap, opp_handicap)
    # 补充无穷端点
    test_diffs = crit + [crit[0] - 1, crit[-1] + 1]
    test_diffs = sorted(set(test_diffs))

    def total_return(x, g):
        my_ret = asian_return(my_handicap, my_odds, my_stake, g)
        opp_ret = asian_return(opp_handicap, opp_odds, x, g)
        return my_ret + opp_ret

    def objective(x):
        returns = [total_return(x, g) for g in test_diffs]
        # 我们想让所有回报尽可能相等，minimax 策略：最小化最大损失
        total_invest = my_stake + x
        profits = [r - total_invest for r in returns]
        # 我们想要最大化最坏情况的盈利（即最小化最坏亏损）
        worst = min(profits)
        return -worst  # 最小化负worst即最大化worst

    # 用简单扫描找最优x（对手盘下注0到3倍初始回报范围）
    from scipy.optimize import minimize_scalar
    # 如果没有scipy，自己写暴力扫描
    best_x = None
    best_worst = -float('inf')
    for x in [i/1000 * (my_stake * my_odds * 2) for i in range(0, 3000)]:
        x = round(x, 2)
        if x <= 0: continue
        rets = [total_return(x, g) - (my_stake + x) for g in test_diffs]
        worst = min(rets)
        if worst > best_worst:
            best_worst = worst
            best_x = x

    if best_x is None:
        return None
    # 生成报告
    details = []
    for g in test_diffs:
        profit = total_return(best_x, g) - (my_stake + best_x)
        details.append((g, profit))
    return best_x, best_worst, details


def manual_input():
    print("\n选择市场类型：")
    print("1. 胜平负 (h2h)  [暂未集成]")
    print("2. 让球盘 (spreads)")
    print("3. 大小球 (totals) [暂未集成]")
    choice = input("输入 2：").strip()

    if choice != "2":
        print("当前仅支持让球盘演示。")
        return

    print("\n【让球盘】")
    my_point = float(input("你的让球点数（如 -1）："))
    my_stake = float(input("已下注金额："))
    my_odds = float(input("你的赔率："))

    n = int(input("对手盘组数："))
    opponents = []
    for i in range(n):
        print(f"\n对手盘 {i+1}:")
        opp_point = float(input("  对手盘让球点数（如 +1.25）："))
        opp_odds = float(input(f"  赔率（让球 {opp_point:+.2f}）："))
        opponents.append((opp_point, opp_odds))

    # 单盘分析
    print("\n" + "="*60)
    print("  单盘 minimax 对冲")
    print("="*60)
    for opp_point, opp_odds in opponents:
        # 对手盘的亚盘盘口（主队让球） = -opp_point
        opp_handicap = -opp_point
        my_handicap = my_point
        res = single_opponent_hedge(my_handicap, my_odds, my_stake, opp_handicap, opp_odds)
        if res:
            x, worst, details = res
            total_invest = my_stake + x
            print(f"\n对手盘 让球 {opp_point:+.2f} @ {opp_odds}:")
            print(f"  最佳对冲金额: {x:.2f}")
            print(f"  最坏情况盈利: {worst:.2f} （负为损失）")
            # 列出不同净胜球下的盈亏
            unique_profits = {}
            for g, p in details:
                unique_profits.setdefault(p, []).append(g)
            print("  盈亏分布：")
            for p, gs in unique_profits.items():
                gs_str = ", ".join([f"{g:+.1f}" for g in sorted(gs)[:3]])  # 只显示前3个
                print(f"    净胜球 {gs_str}... => 净盈亏 {p:+.2f}")
        else:
            print(f"对手盘 让球 {opp_point:+.2f}: 无法计算对冲。")

    # 双盘完美对冲
    if n >= 2:
        print("\n" + "="*60)
        print("  双盘完美对冲（目标：所有净胜球回报相同）")
        print("="*60)
        best_comb = None
        best_comb_profit = -float('inf')
        for (opp1_p, opp1_o), (opp2_p, opp2_o) in itertools.combinations(opponents, 2):
            # 确保一个盘口更深（受让更多）一个更浅
            # 对手盘的实际主队让球为 -opp_p
            h1 = -opp1_p
            h2 = -opp2_p
            # 设定 deep (让球更少，即受让多) 与 shallow
            if opp1_p > opp2_p:
                deep_p, deep_o = opp1_p, opp1_o
                shallow_p, shallow_o = opp2_p, opp2_o
            else:
                deep_p, deep_o = opp2_p, opp2_o
                shallow_p, shallow_o = opp1_p, opp1_o

            # 解方程：使三个区间（输/平、走水、赢2+）回报相等
            # 假设我的盘为整数 -1，走水在净胜1球
            # 计算公式（已验证）
            S = my_stake
            O0 = my_odds
            x_shallow = S / shallow_o
            x_deep = S * (O0 - 1) / deep_o
            total_invest = S + x_shallow + x_deep
            # 检验所有净胜球
            test_g = [0, 1, 2, 3, -1]
            returns = []
            for g in test_g:
                my_r = asian_return(my_point, my_odds, S, g)
                opp_r1 = asian_return(-shallow_p, shallow_o, x_shallow, g)
                opp_r2 = asian_return(-deep_p, deep_o, x_deep, g)
                total = my_r + opp_r1 + opp_r2
                returns.append(total)
            if max(returns) - min(returns) < 0.01:  # 完美
                profit = returns[0] - total_invest
                if profit > best_comb_profit:
                    best_comb_profit = profit
                    best_comb = (deep_p, deep_o, x_deep, shallow_p, shallow_o, x_shallow, profit)
        if best_comb:
            dp, do_, xd, sp, so_, xs, profit = best_comb
            print(f"\n最优双盘组合：")
            print(f"  深盘 让球 +{dp:.2f} @ {do_}: 下注 {xd:.2f}")
            print(f"  浅盘 让球 +{sp:.2f} @ {so_}: 下注 {xs:.2f}")
            print(f"  总投入: {my_stake + xd + xs:.2f}")
            if profit >= 0:
                print(f"  ✅ 任何比分锁定利润: {profit:.2f}")
            else:
                print(f"  ⚠️ 任何比分锁定损失: {profit:.2f}")
        else:
            print("当前对手盘组合无法实现完美对冲。")


if __name__ == "__main__":
    print("="*60)
    print("   ⚽ 亚盘对冲计算器 v5.0 (结算修正)")
    print("="*60)
    manual_input()
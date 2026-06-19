#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
体育博彩对冲计算器 v3.1
- 修正核心对冲公式（正确基准：S * O_A）
- 让球盘、大小球支持多组对手盘输入，分别计算对冲方案
- 胜平负市场保持原逻辑（固定两个对冲结果）
- 支持部分对冲
"""


def calculate_hedge(initial_stake, initial_odds, other_odds, portion=1.0):
    """
    计算对冲方案
    参数:
        initial_stake (float): 已下注金额
        initial_odds (float): 已下注选项的赔率（十进制）
        other_odds (list): 其他所有可能结果的当前赔率列表
        portion (float): 对冲比例，1.0表示完全对冲，0.5表示只对冲一半
    返回:
        dict: 包含完全对冲和部分对冲的详细结果
    """
    if not other_odds:
        return {"error": "至少需要一个对冲选项的赔率"}

    guaranteed_return = initial_stake * initial_odds
    full_hedge_stakes = [guaranteed_return / odd for odd in other_odds]
    total_full_hedge = sum(full_hedge_stakes)

    total_invest = initial_stake + total_full_hedge
    guaranteed_profit = guaranteed_return - total_invest

    if portion < 1.0:
        partial_hedge_stakes = [s * portion for s in full_hedge_stakes]
        total_partial_hedge = sum(partial_hedge_stakes)
        profit_original = initial_stake * initial_odds - (initial_stake + total_partial_hedge)
        profit_hedges = [s * odd - (initial_stake + total_partial_hedge)
                         for s, odd in zip(partial_hedge_stakes, other_odds)]
    else:
        partial_hedge_stakes = []
        total_partial_hedge = 0
        profit_original = guaranteed_profit
        profit_hedges = []

    return {
        "initial_stake": initial_stake,
        "initial_odds": initial_odds,
        "other_odds": other_odds,
        "portion": portion,
        "full_hedge_stakes": full_hedge_stakes,
        "total_full_hedge": total_full_hedge,
        "total_invest": total_invest,
        "guaranteed_profit": guaranteed_profit,
        "partial_hedge_stakes": partial_hedge_stakes,
        "total_partial_hedge": total_partial_hedge,
        "profit_original": profit_original,
        "profit_hedges": profit_hedges,
    }


def print_single_result(result, market_type, opp_desc):
    """打印单个对手盘的对冲结果"""
    if "error" in result:
        print(f"  错误：{result['error']}")
        return

    print(f"\n  {'='*45}")
    print(f"  对手盘：{opp_desc}")
    print(f"  {'='*45}")
    print(f"  已下注：{result['initial_stake']:.2f} @ {result['initial_odds']}")
    # 完全对冲
    print("\n  --- 完全对冲 ---")
    # 这里 other_odds 只有一个元素，因为我们是对单个对手盘计算
    for i, (odd, stake) in enumerate(zip(result['other_odds'], result['full_hedge_stakes'])):
        print(f"  对冲 {opp_desc}：下注 {stake:.2f} @ {odd}")
    profit = result['guaranteed_profit']
    if profit >= 0:
        print(f"  ✅ 锁定利润：{profit:.2f}")
    else:
        print(f"  ⚠️ 锁定损失：{profit:.2f}")
    print(f"  总投入：{result['total_invest']:.2f}")

    # 部分对冲
    if result['portion'] < 1.0:
        print(f"\n  --- 部分对冲（{result['portion']*100:.0f}%） ---")
        for i, (odd, stake) in enumerate(zip(result['other_odds'], result['partial_hedge_stakes'])):
            print(f"  对冲 {opp_desc}：下注 {stake:.2f} @ {odd}")
        print(f"  原选项赢 → 净盈利：{result['profit_original']:.2f}")
        for i, p in enumerate(result['profit_hedges']):
            print(f"  对手盘赢 → 净盈利：{p:.2f}")


def manual_input():
    """手动输入模式（支持多组对手盘）"""
    print("\n请选择市场类型：")
    print("  1. 胜平负 (h2h)")
    print("  2. 让球盘 (spreads)")
    print("  3. 大小球 (totals)")
    market_choice = input("输入 1、2 或 3：").strip()

    # ---------- 胜平负（维持原样，两个固定对冲结果） ----------
    if market_choice == "1":
        market_type = "h2h"
        print("\n【胜平负市场】一场比赛有 主胜/平局/客胜 三个结果。")
        initial_stake = float(input("已下注金额："))
        initial_odds = float(input("已下注选项赔率（十进制，例如 1.76）："))
        other_odds = []
        print("请输入其他两个结果的当前赔率：")
        other_odds.append(float(input("  结果1（平局或另一队胜）赔率：")))
        other_odds.append(float(input("  结果2（最后一队胜或平局）赔率：")))
        portion = float(input("\n对冲比例（0~1，1为完全对冲）："))
        result = calculate_hedge(initial_stake, initial_odds, other_odds, portion)
        # 打印结果（沿用原格式）
        print("\n" + "=" * 55)
        print(f"   📊 对冲计算结果（市场：胜平负）")
        print("=" * 55)
        print(f"  已下注：{initial_stake:.2f} @ {initial_odds}")
        print("\n--- 完全对冲方案（所有结果回报相同）---")
        for i, (odd, stake) in enumerate(zip(other_odds, result['full_hedge_stakes'])):
            print(f"  对冲选项{i+1}：下注 {stake:.2f} @ {odd}")
        profit = result['guaranteed_profit']
        if profit >= 0:
            print(f"  ✅ 无论谁赢，锁定利润：{profit:.2f}")
        else:
            print(f"  ⚠️ 无论谁赢，最小化损失：{profit:.2f}")
        print(f"  总投入：{result['total_invest']:.2f}")
        if portion < 1.0:
            print(f"\n--- 部分对冲（{portion*100:.0f}% 对冲）---")
            for i, (odd, stake) in enumerate(zip(other_odds, result['partial_hedge_stakes'])):
                print(f"  对冲选项{i+1}：下注 {stake:.2f} @ {odd}")
            print(f"  原选项赢 → 净盈利：{result['profit_original']:.2f}")
            for i, p in enumerate(result['profit_hedges']):
                print(f"  对冲选项{i+1}赢 → 净盈利：{p:.2f}")
        print("=" * 55 + "\n")
        return

    # ---------- 让球盘 / 大小球（支持多组对手盘） ----------
    if market_choice == "2":
        market_type = "spreads"
        print("\n【让球盘市场】点数可能不对称，请输入你的下注信息。")
        my_point = float(input("你下注选项的让球点数（例如 -1 或 +1.5）："))
    elif market_choice == "3":
        market_type = "totals"
        print("\n【大小球市场】请输入你的下注信息。")
        line = float(input("大小球界限值（例如 2.5）："))
        side = input("你下注大球(Over)还是小球(Under)？(输入 O 或 U)：").strip().upper()
        while side not in ("O", "U"):
            side = input("输入无效，请重新输入 O 或 U：").strip().upper()
        my_side = "Over" if side == "O" else "Under"
    else:
        print("无效选择，退出。")
        return

    initial_stake = float(input("已下注金额："))
    initial_odds = float(input("你下注选项的赔率（十进制）："))

    # 输入多组对手盘
    n = int(input("\n对手盘有几组？"))
    opponents = []  # 每个元素为 (描述, 赔率)
    for i in range(n):
        print(f"\n--- 对手盘 {i+1} ---")
        if market_type == "spreads":
            opp_point = float(input("  对手盘的让球点数（例如 +1.25）："))
            opp_desc = f"让球 {opp_point:+.2f}"
        else:  # totals
            opp_side = "Under" if my_side == "Over" else "Over"
            opp_desc = f"{opp_side} {line}"
        opp_odds = float(input(f"  对手盘赔率（{opp_desc}）："))
        opponents.append((opp_desc, opp_odds))

    portion = float(input("\n对冲比例（0~1，1为完全对冲）："))

    # 分别计算每组对手盘
    print("\n" + "=" * 55)
    print(f"   📊 多组对手盘对冲分析（市场：{'让球盘' if market_type=='spreads' else '大小球'}）")
    if market_type == "spreads":
        print(f"  你的下注：让球 {my_point:+.2f}，{initial_stake:.2f} @ {initial_odds}")
    else:
        print(f"  你的下注：{my_side} {line}，{initial_stake:.2f} @ {initial_odds}")
    print("=" * 55)

    for opp_desc, opp_odds in opponents:
        result = calculate_hedge(initial_stake, initial_odds, [opp_odds], portion)
        print_single_result(result, market_type, opp_desc)

    print("\n" + "=" * 55 + "\n")


def auto_from_csv(csv_file, my_bet_team, initial_stake, portion=1.0):
    """从 CSV 自动读取最新赔率并计算对冲（仅支持 h2h）"""
    try:
        import pandas as pd
    except ImportError:
        print("需要安装 pandas 库：pip install pandas")
        return

    df = pd.read_csv(csv_file)
    h2h = df[df['市场类型'] == 'h2h']

    match_rows = h2h[(h2h['主队'] == my_bet_team) | (h2h['客队'] == my_bet_team)]
    if match_rows.empty:
        print(f"未在 {csv_file} 中找到 {my_bet_team} 的比赛")
        return

    match = match_rows.iloc[0]
    home = match['主队']
    away = match['客队']
    print(f"自动读取比赛：{home} vs {away}")

    bet_row = h2h[(h2h['主队'] == home) & (h2h['客队'] == away) & (h2h['选项'] == my_bet_team)]
    if bet_row.empty:
        print(f"未找到 {my_bet_team} 胜的赔率")
        return
    initial_odds = float(bet_row['赔率'].iloc[0])

    other_odds = []
    draw_row = h2h[(h2h['主队'] == home) & (h2h['客队'] == away) & (h2h['选项'] == 'Draw')]
    if not draw_row.empty:
        other_odds.append(float(draw_row['赔率'].iloc[0]))
    other_team = away if my_bet_team == home else home
    other_row = h2h[(h2h['主队'] == home) & (h2h['客队'] == away) & (h2h['选项'] == other_team)]
    if not other_row.empty:
        other_odds.append(float(other_row['赔率'].iloc[0]))

    if len(other_odds) < 2:
        print("警告：未找到全部两种对冲结果，数据可能不完整")
        return

    result = calculate_hedge(initial_stake, initial_odds, other_odds, portion)
    print_results(result, market_type="h2h")


if __name__ == "__main__":
    print("=" * 55)
    print("         ⚽ 体育博彩对冲计算器 v3.1")
    print("=" * 55)
    print("1. 手动输入赔率（胜平负/让球盘/大小球，支持多组对手盘）")
    print("2. 从 CSV 文件自动读取（仅胜平负）")
    choice = input("请选择模式 (1/2)：").strip()

    if choice == "1":
        manual_input()
    elif choice == "2":
        csv_file = input("CSV 文件名（例如 worldcup_odds_20260611.csv）：")
        team = input("你投注的队伍名（必须与 CSV 中选项名称一致）：")
        stake = float(input("已下注金额："))
        portion = float(input("对冲比例（0~1，1为完全对冲）："))
        auto_from_csv(csv_file, team, stake, portion)
    else:
        print("无效选择，退出。")
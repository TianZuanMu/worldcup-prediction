# -*- coding: utf-8 -*-
"""
V4.5 淘汰赛动态系数调整器 — 替代固定±15%

三因子模型 (GAP × STYLE × STAGE):
  - GAP:   实力差距越大 → 淘汰赛保守效应越小 (强队仍能破门)
  - STYLE: 两队进攻效率越高 → 进球衰减越小 (对攻战不会变0-0)
  - STAGE: 决赛比1/8决赛更保守 → 平局倾向随轮次递增

设计原则:
  - 阶段映射基于日期硬编码 (赛程确定后不变)
  - 开关默认关闭·第一阶段仅双轨输出对比
  - 季军战(stage=0)不应用任何淘汰赛调整

用法:
  from knockout_adjuster import apply_knockout_adjustment, get_stage
  draw_boost, goal_decay = apply_knockout_adjustment(
      pure_xg_total=2.44, fifa_rank_gap=30, stage=1, use_dynamic=True
  )
"""


def get_stage(month: int, day: int) -> int:
    """
    基于日期返回淘汰赛阶段权重。

    返回值:
      0 = 季军战 (不应用调整)
      1 = 1/16决赛
      2 = 1/8决赛
      3 = 1/4决赛
      4 = 半决赛
      5 = 决赛 (最高保守)
    """
    if (month, day) == (7, 19):
        return 0   # 季军战
    if (month, day) == (7, 20):
        return 5   # 决赛
    if (month, day) >= (7, 15):
        return 4   # 半决赛
    if (month, day) >= (7, 10):
        return 3   # 1/4决赛
    if (month, day) >= (7, 5):
        return 2   # 1/8决赛
    if month >= 7 or (month == 6 and day >= 29):
        return 1   # 1/16决赛
    return 0       # 小组赛/未知


def _fifa_to_approx_elo(fifa_rank: int) -> int:
    """FIFA排名 → 近似Elo (线性映射·供GAP因子使用)"""
    return 1500 + (80 - max(1, min(200, fifa_rank))) * 5


def apply_knockout_adjustment(
    pure_xg_total: float,
    fifa_rank_gap: int,
    stage: int,
    use_dynamic: bool = False,
) -> tuple:
    """
    计算淘汰赛动态调整系数。

    Args:
        pure_xg_total: 纯净xG总进球 (两队合计·来自_calc_pure_xg)
        fifa_rank_gap: FIFA排名差 (绝对值)
        stage: 阶段权重 (来自get_stage·0=季军战5=决赛)
        use_dynamic: 是否启用动态系数 (默认False→返回固定系数)

    Returns:
        (draw_boost, goal_decay):
          draw_boost: 平局概率乘数 (1.0=不调整)
          goal_decay: 总进球乘数 (1.0=不调整)
    """
    # ── 固定系数 (默认生效) ──
    if not use_dynamic:
        return 1.15, 0.85

    # ── 季军战: 不应用调整 ──
    if stage == 0:
        return 1.0, 1.0

    # ── 动态系数计算 ──

    # 1. 实力均衡度 (parity): 0=碾压, 1=完全均衡
    #    FIFA排名差150≈实力完全不在同一档·调整阈值从300降至150
    parity = 1.0 - min(fifa_rank_gap / 150.0, 1.0)

    # 2. 进攻效率因子: 场均xG越高·衰减越小
    #    锚点1.5≈世界杯单队场均xG上四分位数
    offense_factor = min(pure_xg_total / 2.0 / 1.5, 1.0)  # pure_xg_total是两队合计·除2得场均

    # 3. 阶段保守乘数: 决赛>半决赛>...>1/16决赛
    stage_multiplier = 1.0 + (stage - 1) * 0.03  # stage=1→1.0, stage=5→1.12

    # ── 平局概率加成 ──
    #   实力越接近+轮次越深 → 加成越大
    #   范围: 1.0(碾压+1/16) ~ 1.28(均衡+决赛)
    draw_boost = 1.0 + parity * 0.25 * stage_multiplier
    draw_boost = min(1.30, draw_boost)

    # ── 总进球衰减 ──
    #   基础-10%, 进攻强队减小, 差距大减小, 轮次深加大
    BASE_DECAY = 0.90
    offense_bonus = offense_factor * 0.05       # 最大+5%回补
    gap_bonus = (1.0 - parity) * 0.05           # 碾压局+5%回补
    stage_penalty = (stage - 1) * 0.015         # 每轮次-1.5%
    decay_factor = BASE_DECAY + offense_bonus + gap_bonus - stage_penalty
    decay_factor = max(0.80, min(1.0, decay_factor))

    return round(draw_boost, 3), round(decay_factor, 3)

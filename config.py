# -*- coding: utf-8 -*-
"""
V3.0 统一配置中心
集中管理所有阈值、常量和可调参数，替代散落在各文件中的硬编码。

用法:
  from config import CONF
  if cold_hot >= CONF.overheat_threshold: ...
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Config:
    """V3.0 全局配置 — 单一真相来源"""

    # ══════════════════════════════════════════════════════════
    # 过热 & 信号阈值
    # ══════════════════════════════════════════════════════════
    overheat_threshold: float = 20.0        # 真过热冷热阈值 (V2.12统一)
    pollution_threshold: float = 20.0       # 共识污染阈值
    cold_chasing_threshold: float = 0.375   # 搏冷模式触发 (近8场冷门率>37.5%)
    big_sell_warning: float = 0.15          # 大额卖单检测阈值

    # CLOSE级别专属 (P0#1)
    close_overheat_threshold: float = 32.0  # CLOSE实力接近时过热阈值 (V3.3: 27→32·连续失败3次)
    close_unanimity_boost: float = 1.5      # CLOSE时全票通过信号权重加倍

    # BIG级别专属 (V3.2: BIG回测55%→73%)
    big_overheat_threshold: float = 30.0    # BIG实力差距大时过热阈值更高
    big_away_hot_conf_discount: int = 15    # BIG客队热时置信度折扣
    big_no_overheat_rank_gap: int = 50      # BIG无过热时客队实力优势阈值

    # 顶级强队过热例外 (V3.2: MOD/BIG精英队温和过热→实力碾压)
    elite_team_max_rank: int = 5            # 顶级强队FIFA排名上限
    elite_moderate_cold_max: float = 55.0   # V3.5: 40→55 (球员DB更新后冷热值普涨·英格兰+46/阿根廷+44需覆盖)

    # CLOSE级别精英例外 (V3.3: 扩展精英例外到CLOSE·修复韩国/英格兰/加纳)
    close_elite_rank_threshold: int = 10    # 热方FIFA排名≤10视为精英(比MOD/BIG宽松)
    close_elite_cold_max: float = 35.0      # 冷热<35视为温和过热

    # ══════════════════════════════════════════════════════════
    # 实力差距四级 (V2.6)
    # ══════════════════════════════════════════════════════════
    gap_close_max_rank: int = 10            # 排名差<10为CLOSE
    gap_close_max_value_ratio: float = 3.0  # 身价比<3x为CLOSE
    gap_moderate_max_rank: int = 25
    gap_moderate_max_value_ratio: float = 12.0
    gap_big_max_rank: int = 60
    gap_big_max_value_ratio: float = 25.0

    # ══════════════════════════════════════════════════════════
    # 置信度边界
    # ══════════════════════════════════════════════════════════
    confidence_floor: float = 5.0            # 最低置信度
    confidence_ceiling: float = 88.0         # 最高置信度 (V3.3: 95→88·高置信度准确率仅20%)
    calibration_ceiling: float = 85.0        # 贝叶斯校准天花板 (V3.3: 92→85·收紧)
    no_betfair_confidence_cap: float = 65.0  # 🆕 V3.3: 无必发数据时置信度上限
    calibration_prior_strength: int = 6     # 🆕 V3.3: 贝叶斯平滑先验强度 (4→6·更强收缩)

    # ══════════════════════════════════════════════════════════
    # 维度调整幅度 (V2.9-V2.15)
    # ══════════════════════════════════════════════════════════
    weather_adj_range: Tuple[float, float] = (-4, 4)
    motivation_adj_range: Tuple[float, float] = (-10, 10)
    lineup_adj_range: Tuple[float, float] = (-20, 5)       # V3.0↑ 首发阵容·扩大幅度
    tactical_adj_range: Tuple[float, float] = (-5, 5)
    coach_adj_range: Tuple[float, float] = (-3, 3)
    time_adj_range: Tuple[float, float] = (-3, 3)
    form_adj_range: Tuple[float, float] = (-10, 10)        # V3.0↑ 近期状态·扩大幅度
    h2h_adj_range: Tuple[float, float] = (-3, 2)
    referee_adj_range: Tuple[float, float] = (-2, 1)
    market_psych_adj_range: Tuple[float, float] = (-10, 0)
    xls_trend_adj_range: Tuple[float, float] = (-5, 5)    # V2.15
    cover_rate_adj_range: Tuple[float, float] = (-8, 5)   # 穿盘率修正
    sub_depth_adj_range: Tuple[float, float] = (-5, 5)    # V3.0 替补深度
    setpiece_adj_range: Tuple[float, float] = (-3, 3)    # V3.0 定位球
    milestone_adj_range: Tuple[float, float] = (0, 5)     # V3.0↓ 超巨里程碑·降低上限

    # ══════════════════════════════════════════════════════════
    # 动态穿盘率 (V2.14 → V3.0)
    # ══════════════════════════════════════════════════════════
    cover_rate_cap: float = 80.0             # 穿盘率上限
    cover_defense_weak_factor: float = 1.35  # 对手排名>80防守弱
    cover_defense_strong_factor: float = 0.75 # 对手排名≤15防守强
    cover_attack_hot_factor: float = 1.20    # 场均≥2.5球攻击力强
    cover_attack_cold_factor: float = 0.80   # 场均<1.0球攻击乏力
    cover_motivation_factor: float = 1.25    # 已淘汰对手战意低
    cover_motivation_near_factor: float = 1.15 # 濒临淘汰对手

    # V3.0 新增穿盘率因子
    cover_line_momentum_factor: float = 0.90  # 盘口连续退盘→穿盘更难
    cover_venue_factor_indoor: float = 0.95   # 室内→小球→更难穿盘

    # ══════════════════════════════════════════════════════════
    # 近期状态 (V3.0 时间衰减)
    # ══════════════════════════════════════════════════════════
    form_decay_half_life_days: float = 30.0   # 半衰期30天
    form_recent_weight_boost: float = 2.0     # 最近1场权重加倍

    # ══════════════════════════════════════════════════════════
    # 天气
    # ══════════════════════════════════════════════════════════
    weather_default_temp: float = 20.0
    weather_cache_ttl_hours: float = 3.0     # 天气缓存3小时

    # ══════════════════════════════════════════════════════════
    # XLS趋势 (V2.15)
    # ══════════════════════════════════════════════════════════
    xls_trend_min_versions: int = 3
    xls_trend_cover_decline_warn: float = 3.0  # 穿盘率累计下降≥3pp→预警
    xls_trend_cover_steep: float = 1.5         # 单版陡降≥1.5pp
    xls_trend_consensus_accel: float = 1.5     # 共识加速倍数
    xls_trend_jump_sigma: float = 2.0          # 跳变检测σ

    # ══════════════════════════════════════════════════════════
    # 替补深度 (V3.0) — 5换时代
    # ══════════════════════════════════════════════════════════
    sub_impact_threshold: float = 0.3          # 轮换风险>30%触发
    sub_quality_gap_threshold: float = 1.5     # 首发/替补身价比>1.5x有影响

    # ══════════════════════════════════════════════════════════
    # 定位球 (V3.0)
    # ══════════════════════════════════════════════════════════
    setpiece_default_goals_pct: float = 0.28   # 世界杯定位球进球占比28%
    setpiece_corner_rate_default: float = 0.05 # 默认角球转化率5%

    # ══════════════════════════════════════════════════════════
    # 超巨里程碑 (V3.0)
    # ══════════════════════════════════════════════════════════
    milestone_caps: Dict[str, int] = field(default_factory=lambda: {
        '100': 20,   # 100场+ → +2% (温和)
        '150': 40,   # 150场+ → +4% (显著)
        '200': 50,   # 200场+ → +5% (梅西级·上限降低)
    })
    milestone_goal_records: Dict[str, int] = field(default_factory=lambda: {
        '50': 50,    # 国家队50球
        '100': 100,  # 国家队100球
    })

    # ══════════════════════════════════════════════════════════
    # 纪律风险 (V3.3)
    # ══════════════════════════════════════════════════════════
    discipline_risk_adj_range: Tuple[float, float] = (-5, 0)  # 纪律风险置信度调整范围
    discipline_risk_threshold: float = 0.3  # 触发调整的红牌风险概率阈值

    # ══════════════════════════════════════════════════════════
    # 淘汰赛特殊规则 (V3.3)
    # ══════════════════════════════════════════════════════════
    knockout_draw_tendency: float = 1.15      # 淘汰赛平局倾向+15%
    knockout_score_dampen: float = 0.85       # 淘汰赛总进球衰减15%

    # ══════════════════════════════════════════════════════════
    # 🆕 V3.20 深度审计修复 (海地VS苏格兰审计·5项结构性风险)
    # ══════════════════════════════════════════════════════════
    # 风险1: 赔率变动与XLS共识方向矛盾 → 强制扣减
    odds_consensus_contradiction_penalty: int = 12  # 赔率反向变动+XLS背离同时存在时扣减
    odds_contradiction_threshold: float = 5.0       # 赔率变动>5%触发方向矛盾检测
    # 风险2: 平赔暴跌+热门仍赢 → 平局信号不应被完全压制
    draw_collapse_hotwin_cap: int = 8               # 热门仍赢时平赔暴跌置信度加成上限(原12-20)
    # 风险3: 三条件近阈值检测 (球员差<20%过线)
    three_conditions_near_threshold_ratio: float = 0.20  # 差<20%视为近阈值
    three_conditions_near_threshold_penalty: int = 5     # 近阈值扣减
    # 风险4: 关键维度数据缺失不确定性惩罚
    data_missing_uncertainty_factor: float = 0.97   # 每缺失一个关键维度×0.97
    # 风险5: 低穿盘率+高置信度悖论天花板
    low_cover_high_conf_ceiling: int = 65           # 穿盘率<50%时置信度上限
    low_cover_threshold: float = 50.0               # 低穿盘率阈值
    # 🆕 V3.22: 市场熔断封顶 — 惩罚链激活时回拨上限(防止熔断覆盖风险定价)
    meltdown_cap_with_penalties: int = 50           # V3.20惩罚激活时·均值回拨上限50%
    # 🆕 V3.25: 模型-泊松背离熔断 — 决策树与泊松对立时强制定墙
    poisson_model_divergence_threshold: int = 30    # 模型信度-泊松胜率>30点触发
    poisson_model_cap: int = 55                     # 背离触发时置信度上限
    poisson_hotwin_min_threshold: float = 38.0      # 泊松热方胜率<38%视为严重看衰

    # 🆕 V3.36: 大小球-泊松xG背离仲裁
    totals_xg_divergence_critical: float = 0.30     # 背离>30% → 严重·大幅降信
    totals_xg_divergence_moderate: float = 0.15     # 背离>15% → 中度·降信
    totals_xg_divergence_hard_reject: float = 0.50  # 背离>50% → 硬拒绝·放弃预测
    totals_xg_diverge_conf_penalty_critical: int = 25  # 严重背离扣信
    totals_xg_diverge_conf_penalty_moderate: int = 12  # 中度背离扣信
    totals_xg_diverge_conf_ceiling: int = 50           # 方向冲突时上限
    totals_line_move_significant: float = 0.05         # 盘口变动>5%视为主动行为

    # ══════════════════════════════════════════════════════════
    # 回测 & 数据
    # ══════════════════════════════════════════════════════════
    backtest_dir: str = r"C:\Users\A\PyCharmMiscProject\backtest"
    data_archive_dir: str = r"C:\Users\A\PyCharmMiscProject\archive"
    odds_snapshot_glob: str = "worldcup_odds_*.csv"
    xls_archive_pattern: str = r"D:\*.xls"


# 全局单例
CONF = Config()


# ── 便捷函数 ──

def get_gap_thresholds(level: str) -> dict:
    """获取指定实力级别的阈值"""
    if level == 'close':
        return {'max_rank': CONF.gap_close_max_rank, 'max_value_ratio': CONF.gap_close_max_value_ratio}
    elif level == 'moderate':
        return {'max_rank': CONF.gap_moderate_max_rank, 'max_value_ratio': CONF.gap_moderate_max_value_ratio}
    elif level == 'big':
        return {'max_rank': CONF.gap_big_max_rank, 'max_value_ratio': CONF.gap_big_max_value_ratio}
    return {'max_rank': 999, 'max_value_ratio': 999}


def get_overheat_threshold(gap_level: str) -> float:
    """根据实力差距级别返回过热阈值"""
    if gap_level == 'close':
        return CONF.close_overheat_threshold
    if gap_level == 'big':
        return CONF.big_overheat_threshold
    return CONF.overheat_threshold


# ── 测试 ──
if __name__ == '__main__':
    print("V3.0 配置中心")
    print(f"  过热阈值: {CONF.overheat_threshold} (CLOSE: {CONF.close_overheat_threshold}, BIG: {CONF.big_overheat_threshold})")
    print(f"  置信度范围: {CONF.confidence_floor}-{CONF.confidence_ceiling}%")
    print(f"  穿盘率上限: {CONF.cover_rate_cap}%")
    print(f"  状态半衰期: {CONF.form_decay_half_life_days}天")
    print(f"  XLS趋势最小版本: {CONF.xls_trend_min_versions}")
    print(f"  替补轮换阈值: {CONF.sub_impact_threshold*100:.0f}%")

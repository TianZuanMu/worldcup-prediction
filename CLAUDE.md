# 世界杯预测模型 V3.17 (回测 29/29=100%)

> 📅 2026-06-21 · 球员DB 1250人/48队·intl_caps 82%覆盖 · 29场回测 · 决策树六条路径全部验证 · 方向-泊松冲突检测

## 环境与快速开始

```bash
pip install playwright beautifulsoup4 lxml xlrd requests
cd "C:/Users/A/PyCharmMiscProject"

# 0a. 刷新比赛ID
PYTHONIOENCODING=utf-8 python -c "from auto_fetch_xls import discover_match_ids; discover_match_ids()"
# 0b. 获取 XLS + 必发
PYTHONIOENCODING=utf-8 python auto_fetch.py --all
# 1. 赔率管道
PYTHONIOENCODING=utf-8 python "赔率获取.py" && PYTHONIOENCODING=utf-8 python "赔率变化.py"
# 2. 赛程更新 (新比赛日)
PYTHONIOENCODING=utf-8 python generate_schedule.py --update
# 3. 一键赛前报告
PYTHONIOENCODING=utf-8 python -c "
from pre_match_report import batch_report
print(batch_report(['法国VS塞内加尔', '阿根廷VS阿尔及利亚']))
"
```

## ⏰ 数据调度

| 模块 | 频率 | 窗口 |
|------|------|------|
| `赛前高频赔率.py` | 每10分钟 | 赛前2h |
| `auto_fetch.py --cron` | 每30分钟 | 赛前48h |

## V3.17 核心阈值

| 阈值 | 值 | 说明 |
|------|:--:|------|
| 标准过热 | **20** | MOD级别 |
| CLOSE过热 | **32** | 连续失败3次后收紧 |
| BIG真过热 | **≥30** | 真过热→热门不胜 |
| BIG弱过热 | **20-29** | 方向保留·权重降低 |
| EXTREME碾压 | **指数>0.80** | 跳过泊松·直接实力预测 |
| 共识污染 | **20** | 与过热统一 |
| 置信度天花板 | **85%** | Bayes平滑·先验强度6 |
| 高置信度惩罚 | **>80%→×0.80** | 历史准确率仅20% |
| 金三角约束 | **>75%需全票+冷热≤35+穿盘≥50%** |  |
| 泊松-市场熔断 | **背离>35点→强制≤50%** |  |
| 方向-泊松冲突 | **客胜>主胜+5%→降级+信≤50%** | V3.17 |
| 大小球不推荐 | **信<50%** |  |
| xG下限 | **0.50** (世界杯正赛) |  |
| 状态分上限 | **10.0** | V3.17 |

## 核心规则

### 过热判定 (V3.15 三级体系)
```
BIG级别:
  真过热(冷热≥30+庄亏) → 默认热门不胜
    例外(三条件全满足): (a)对手rank≥50 (b)无威胁射手 (c)无世界杯爆冷 → 热门仍赢
  弱过热(冷热20-29+庄亏) → 方向保留·权重降低·倾向冷门 🆕
  无过热(<20) → 正常按实力预测

MODERATE级别:
  真过热(冷热≥20+庄亏) + 精英队(FIFA≤5) + 温和过热(冷热<55) → 实力碾压(精英例外)
  真过热 + 非精英 → 对手质量过滤

CLOSE级别:
  真过热(冷热≥32+庄亏) → 热门不胜
  精英例外: 热方FIFA≤10 + 冷热<35 → 实力碾压

EXTREME → 强制回避
假过热(冷热≥20+庄盈) → 可信正路
```

### V3.17 决策树六条路径
```
① 精英例外: MOD/CLOSE + 真过热 + FIFA前5(10) + 温和过热 → 热门胜
② 三条件例外: BIG + 真过热 + 3/3全满足 → 热门仍赢
③ 默认弱过热: BIG + 弱过热(20-29) + 三条件不足 → 热门不胜
④ 实力优先: MOD + 真过热 + 攻防差双优 + 对手有火力 → 热门胜(折扣减半)
⑤ 实力阈值豁免: BIG + 真过热 + 中场/攻击/防线达标 → 热门胜(实力碾压)
⑥ EXTREME碾压: EXTREME + 碾压指数>0.80 → 跳过泊松·实力预测

🆕 V3.17: 方向-泊松冲突检测 — 泊松客胜>主胜+5%时自动降级+信≤50%
```

### 实力差距四级

| 级别 | FIFA排名差 | 身价比 | 信号可靠性 |
|:--:|:--:|:--:|:--:|
| Close | <10 | <3x | 85-90% |
| Moderate | 10-25 | 3-12x | 60-80% |
| Big | 25-60 | 12-25x | 30-50% |
| Extreme | >60 | >25x | 0% |

## V3.15 置信度乘法链

```
基础置信度(70%MOD/65%CLOSE/60%BIG)
  × weather(0.96~1.04) × motivation(0.90~1.10)
  × lineup(0.85~1.00)  × tactical(0.95~1.05)
  × coach(0.97~1.03)   × time(0.97~1.03)    ← 时差衰减
  × recent_form(0.90~1.10) × h2h(0.97~1.02)
  × referee(0.97~1.03) × market_psych(1.00~0.90)  ← V3.15: 裁判技术/力量差异化
  × xls_trend(0.95~1.05) × sub_depth(0.95~1.05)
  × setpiece(0.97~1.03) × milestone(1.00~1.05)
  × injury(0.80~1.00)  × knockout(0.95)
  × discipline(0.95~1.00)
  → apply_signals:
    · 平赔暴跌分级: critical≥7%→+20 | strong≥5%→+12 | moderate→+7  ← V3.15
    · 全票通过强化
    · 共识污染/大额卖单
    · 冷热趋势分析
  → BIG过热分级 (真/弱/无) ← V3.15
  → Bayes校准(天花板85%)
  → 高置信度惩罚(>80%→×0.80) ← V3.13
  → 金三角约束(>75%需全票+冷热≤35+穿盘≥50%) ← V3.13
  → 泊松-市场熔断(|泊松-市场|>35→强制≤50%) ← V3.15
  → 最终: 5-88%
```

## 比分预测链

```
赔率隐含λ → 实力差距 → 预测方向 → 对手质量 → 穿盘率
  → 大小球联动(信≥60%→等比缩放; <50%→不推荐) ← V3.14
  → 近期状态 → 泊松分布 → xG下限0.50 ← V3.14
  → 弱队xG反直觉约束(≤强队×90%) ← V3.15
  → 穿盘率一致性校验(偏离>15%→调整) ← V3.14
  → 方向-穿盘率冲突校验(热门不胜+穿盘>40%→下调) ← V3.15
  → Top3比分概率
```

## 模块索引

**核心**: `pre_match_report.py` · `dimension12_books.py` · `v24_optimization.py` · `xls_reader_xlrd.py` · `risk_score.py`
**维度**: `match_context.py` · `match_time_impact.py` · `team_profiles.py` · `weather_tracking.py` · `lineup_correction.py` · `recent_form.py` · `head_to_head.py` · `referee_analysis.py`
**V3.x**: `config.py` · `market_psychology.py` · `confidence_calibration.py` · `knockout_motivation.py` · `xls_trend_analysis.py` · `milestone_detection.py` · `sub_depth.py` · `setpiece_quant.py` · `score_prediction.py` · `discipline_risk.py` · `injury_tracker.py` · `opponent_db.py` · `midfield_quality.py`
**自动化**: `auto_fetch.py` · `auto_fetch_xls.py` · `auto_post_match.py` · `backtest_runner.py` · `generate_schedule.py` · `import_recent_form.py`
**数据**: `worldcup_odds_*.csv` · `betfair_data/` · `backtest/matches.json`

## 自检清单

```
□ XLS+必发? → python auto_fetch.py --all
□ 赔率管道? → 赔率获取.py && 赔率变化.py
□ 新比赛日? → generate_schedule.py --update
□ 预测? → batch_report([...])
□ 赛后? → python auto_post_match.py
□ 回测? → python backtest_runner.py
□ 积分? → knockout_motivation.refresh_standings()
□ 伤病? → from injury_tracker import check_injuries
```

## 版本演进 (V3.11→V3.17)

| 版本 | 日期 | 关键变更 |
|------|------|------|
| V3.12 | 06-21 | 老将大赛经验系数·巨人杀手时间衰减·穿盘率一致性校验·低置信度翻转抑制 |
| V3.13 | 06-21 | 高置信度×0.80惩罚·金三角约束(>75%需三信号齐备) |
| V3.14 | 06-21 | xG下限0.50·穿盘率-比分偏离>15%校验·大小球<50%不推荐·AFC预选赛加权 |
| V3.15 | 06-21 | 泊松-市场熔断(>35点)·方向-穿盘率冲突校验·弱队xG反直觉约束·平赔暴跌分级(+20)·裁判技术/力量差异化 |
| V3.16 | 06-21 | 裁判因子输出透明化(显式调整+V29确认)·信号矩阵增加裁判状态·大小球裁判修正 |
| V3.17 | 06-21 | 方向-泊松背离降级(客胜>主胜+5%→降级+信≤50%)·状态分上限10.0·小盘口穿盘量化标注 |

## 相关记忆

- [[v34-upgrade-summary]] — V3.4 优化详情 (42项)
- [[calibration-tracker]] — 回测逐场详情
- [[v311-external-review]] — V3.11外部评审·88分·V3.12四项修复
- [[v312-review-v313-direction]] — V3.12评审·V3.13方向
- [[v313-uzbekistan-colombia-review]] — V3.13评审·85分·V3.14四项修复
- [[v314-argentina-algeria-review]] — V3.14评审·87分·V3.15六项修复
- [[prediction-methodology-v2]] — 12维度体系详解
- [[opponent-db]] — 对手DB+三条件
- [[auto-fetch-setup]] — 数据获取自动化

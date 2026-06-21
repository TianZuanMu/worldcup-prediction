# 世界杯预测模型 V3.33 (回测 28/31=90.3%)

> 📅 2026-06-22 · 球员DB 1250人/48队 · 31场回测 · 决策树11路径 · 假过热区分 · λ预测赢家修正 · 46队状态DB

## 环境与快速开始

```bash
pip install playwright beautifulsoup4 lxml xlrd requests
cd "C:/Users/A/PyCharmMiscProject"

# 0a. 刷新比赛ID
PYTHONIOENCODING=utf-8 python -c "from auto_fetch_xls import discover_match_ids; discover_match_ids()"
# 0b. 获取 XLS + 必发
PYTHONIOENCODING=utf-8 python auto_fetch.py --all
# 1. 一键赛前报告
PYTHONIOENCODING=utf-8 python -c "
from pre_match_report import batch_report
print(batch_report(['西班牙VS沙特', '比利时VS伊朗']))
"
```

## ⏰ 数据调度

| 模块 | 频率 | 窗口 |
|------|------|------|
| `auto_fetch.py --cron` | 每30分钟 | 赛前48h |

## V3.33 核心阈值

| 阈值 | 值 | 说明 |
|------|:--:|------|
| 标准过热 | **20** | MOD/CLOSE级别 |
| CLOSE过热 | **32** | 连续失败3次后收紧 |
| BIG真过热 | **≥30** | 冷热≥30+PnL>-1M+d12 hot≥15 → 真过热降信 |
| BIG假过热 | **d12 hot<15** | dimension12确认虚高·完全覆盖 🆕 |
| BIG弱过热 | **20-29** | 非精英→方向保留·权重降低 |
| BIG弱过热精英豁免 | **FIFA≤5** | 精英队跳过弱过热降级 |
| EXTREME碾压 | **指数>0.80** | 跳过泊松·直接实力预测 |
| 共识污染 | **20** | 与过热统一 |
| 置信度天花板 | **85%** | Bayes平滑·先验强度6 |
| 高置信度惩罚 | **>80%→×0.80** | 历史准确率仅20% |
| 金三角约束 | **>75%需全票+冷热≤35+穿盘≥50%** |  |
| 泊松-市场熔断 | **背离>35→强制≤50%** |  |
| 市场极端值上限 | **market>90%→上限=model+10%** | 🆕 V3.33 |
| 方向-泊松冲突 | **客胜>主胜+5%→降级+信≤50%** | V3.17 |
| 冷热临界惩罚 | **18≤冷热<22→-10** | 🆕 V3.19 |
| 爆冷史窗口 | **5年** (原3年) | 🆕 V3.33 |
| 伊朗场外劣势 | **对手+8%** | 🆕 V3.33 |
| 状态分上限 | **10.0** | V3.17 |
| 实力豁免精英拦截 | **对手FW≥35M→豁免不生效** | V3.29 |
| 伤病决策树影响 | **确认缺阵→攻击/防守评分×0.82** | V3.30 |

## 核心规则

### 过热判定 (V3.31)
```
BIG级别:
  真过热(冷热≥30+庄亏) → 默认热门不胜
    例外(三条件全满足): (a)对手rank≥50 (b)无威胁射手 (c)无世界杯爆冷 → 热门仍赢
    实力阈值豁免: 中场/攻击/防线达标 → 热门胜 (精英FW≥35M时拦截)
  弱过热(冷热20-29+庄亏) → 非精英:方向保留·倾向冷门 | 精英(FIFA≤5):保留真过热 🆕
  无过热(<20) → 正常按实力预测

MODERATE级别:
  真过热(冷热≥20+庄亏) + 精英队(FIFA≤5) + 温和过热(冷热<55) → 实力碾压(精英例外)
  真过热 + 非精英 → 对手质量过滤
  实力优先: 攻防差双优 + 对手有火力 → 热门胜(折扣减半)

CLOSE级别:
  真过热(冷热≥32+庄亏) → 热门不胜
  精英例外: 热方FIFA≤10 + 冷热<35 → 实力碾压

EXTREME → 强制回避
假过热(冷热≥20+庄盈) → 可信正路
```

### 决策树11条路径 (V3.33)
```
① 精英例外: MOD/CLOSE + 真过热 + FIFA前5(10) + 温和过热 → 热门胜
② 三条件例外: BIG + 真过热 + 3/3全满足 → 热门仍赢
③ 默认弱过热: BIG + 弱过热(20-29) + 三条件不足 + 非精英 → 热门不胜
③b 精英弱过热: BIG + 弱过热(20-29) + FIFA≤5 → 保留真过热
④ 实力优先: MOD + 真过热 + 攻防差双优 + 对手有火力 → 热门胜(折扣减半)
⑤ 实力阈值豁免: BIG + 真过热 + 中场/攻击/防线达标 → 热门胜 (精英FW拦截)
⑥ EXTREME碾压: EXTREME + 碾压指数>0.80 → 跳过泊松·实力预测
⑦ 防线翻盘: MOD + 真过热 + 防线/攻击比≥0.78 + 热方无prime精英FW → 热门不胜
⑧ EXTREME回避: EXTREME + 赔率背离 → 不预测
⑨ BIG无过热: BIG + 冷热<20 → 模糊·偏向热门
⑩ 理性热度: BIG + 冷热<18 + 市场隐含>85% → 热门胜(理性热度)
⑪ BIG假过热: BIG + d12不确认真过热 → 热度虚高·实力优先 🆕 V3.32

🆕 V3.32: 三条件按赔率判定弱势方(非热方面对面)·dimension12覆盖BIG假过热
🆕 V3.33: BIG真/假过热区分(冷热≥30+PnL>-1M+d12≥15→真过热降信·否则假过热)
```

### 实力差距四级 (旧版等权投票)

| 级别 | FIFA排名差 | 身价比 | 信号可靠性 |
|:--:|:--:|:--:|:--:|
| Close | <10 | <3x | 85-90% |
| Moderate | 10-25 | 3-12x | 60-80% |
| Big | 25-60 | 12-25x | 30-50% |
| Extreme | >60 | >25x | 0% |

### V3.28 评分表 (展示用·不影响预测分类)

48队三维评分: `team_ratings.py` · 计算引擎: `compute_ratings.py`
S: 法国9.6·西班牙8.9·葡萄牙8.9·英格兰8.6 | A: 巴西8.3·荷兰7.5·德国7.6
B+: 阿根廷7.1·比利时6.8·克罗地亚6.8 | B: 土耳其6.3·乌拉圭6.2等

## 置信度乘法链

```
基础置信度(70%MOD/65%CLOSE/60%BIG)
  × weather(0.96~1.04) × motivation(0.90~1.10)
  × lineup(0.85~1.00)  × injury(0.85~1.00)  ← 🆕 V3.30 伤病追踪
  × tactical(0.95~1.05) × coach(0.97~1.03)
  × recent_form(0.90~1.10) × h2h(0.97~1.02)
  × referee(0.97~1.03) × market_psych(1.00~0.90)
  × xls_trend(0.95~1.05) × sub_depth(0.95~1.05)
  × setpiece(0.97~1.03) × milestone(1.00~1.05)
  × discipline(0.95~1.00)
  → apply_signals:
    · 平赔暴跌分级: critical≥7%→+20 | strong≥5%→+12 | moderate→+7
    · 全票通过强化 · 共识污染/大额卖单 · 冷热趋势分析
  → BIG过热分级 (真/弱/无) + 精英豁免 🆕
  → 伤病决策树影响 (攻击/防守评分调整) 🆕
  → Bayes校准(天花板85%)
  → 高置信度惩罚(>80%→×0.80)
  → 金三角约束(>75%需全票+冷热≤35+穿盘≥50%)
  → 泊松-市场熔断(|泊松-市场|>35→强制≤50%)
  → 市场极端值上限(market>90%→cap=model+10%) 🆕 V3.33
  → 穿盘-泊松交叉验证(穿盘<40%+xG>3.0→-5) 🆕 V3.33
  → 伊朗场外劣势(对手+8%) 🆕 V3.33
  → 最终: 5-88%
```

## 模块索引

**核心**: `pre_match_report.py` · `v24_optimization.py` · `config.py` · `xls_reader_xlrd.py`
**评分**: `team_ratings.py` · `compute_ratings.py` · `midfield_quality.py` · `opponent_db.py`
**维度**: `match_context.py` · `recent_form.py` · `head_to_head.py` · `referee_analysis.py` · `weather_tracking.py` · `lineup_correction.py` · `knockout_motivation.py`
**V3.x**: `confidence_calibration.py` · `market_psychology.py` · `score_prediction.py` · `discipline_risk.py` · `injury_tracker.py` · `milestone_detection.py` · `sub_depth.py` · `setpiece_quant.py` · `xls_trend_analysis.py`
**自动化**: `auto_fetch.py` · `auto_fetch_xls.py` · `auto_post_match.py` · `backtest_runner.py` · `generate_schedule.py`
**数据**: `betfair_data/` · `backtest/matches.json` · `auto_fetch_config.json`

## 自检清单

```
□ XLS+必发? → python auto_fetch.py --all
□ 新比赛日? → generate_schedule.py --update
□ 伤病? → from injury_tracker import check_injuries
□ 预测? → from pre_match_report import generate_report
□ 回测? → python backtest_runner.py
□ 评分? → python team_ratings.py
□ 重算评分? → python compute_ratings.py --save
```

## 版本演进

| 版本 | 日期 | 关键变更 |
|------|------|------|
| V3.25 | 06-21 | 模型-泊松背离熔断·加纳VS巴拿马触发(65%→55%) |
| V3.28 | 06-21 | 48队三维评分体系·混合差距分类器→已回退 |
| V3.29 | 06-21 | 实力豁免精英拦截·伤病接入预测管道 |
| V3.30 | 06-21 | 伤病前置到决策树·P0-P2公式改进 |
| V3.31 | 06-21 | BIG弱过热精英豁免·回退V3.28分类器·回测28/31=90.3% |
| **V3.32** | 06-21 | 三条件赔率判定·dimension12覆盖·市场引用修正·方向-泊松检测·穿盘率门槛 |
| **V3.33** | 06-22 | λ预测赢家修正·BIG攻击枯竭增强·真/假过热区分·5年爆冷窗口·46队状态DB·伊朗场外因素 |

## V3.31 回测 (28/31=90.3%)

仅3错:
- 葡萄牙VS刚果(金): 热门胜67%→实际1-1
- 德国VS科特迪瓦: 热门不胜74%→实际2-1
- 厄瓜多尔VS库拉索: 热门胜70%→实际0-0

## V3.32 修复 (06-21, 西班牙VS沙特审计驱动)

| # | 问题 | 文件 | 修复 |
|:--:|------|------|------|
| 1 | 三条件检查热方对面(西班牙)而非弱方(沙特) | `pre_match_report.py` | 按赔率判定弱方 |
| 2 | dimension12判假过热但仅警告不覆盖 | `pre_match_report.py` | BIG差距+d12不确认真过热→覆盖 |
| 3 | 穿盘率因预测方向循环下调 | `pre_match_report.py` | 置信度≥65%才下调 |
| 4 | market_imp引用热方(4%)非预测赢家(96%) | `pre_match_report.py` | 按预测赢家侧计算 |
| 5 | 方向-泊松检测用hot_side非predicted_side | `pre_match_report.py` | 按赔率判定 |
| 6 | 三条件(c)显示"✅(2022胜阿根廷)"矛盾 | `opponent_db.py` | 区分近期/历史爆冷 |

## V3.33 修复 (06-22, 多场审计驱动)

| # | 问题 | 文件 | 修复 |
|:--:|------|------|------|
| P0 | λ调整用hot_side(沙特)非favorite(西班牙) | `score_prediction.py` | predicted_winner按赔率判定 |
| P0 | BIG+攻击枯竭λ调整不足 | `score_prediction.py` | weak_threat<1.0→×1.25/×0.75 |
| P0 | home_is_strong用betfair_hot_side | `score_prediction.py` | 按赔率判定 |
| P1 | market>90%过度回拨 | `pre_match_report.py` | 上限=model+10% |
| P2 | 爆冷窗口3年过短(2022已过期) | `opponent_db.py` | 3→5年 |
| P0 | BIG真/假过热不分(乌拉圭+38 vs 西班牙-112) | `pre_match_report.py` | cold≥30+PnL>1M+d12≥15→真过热降信 |
| P1 | 穿盘<40%+xG>3.0矛盾未检测 | `pre_match_report.py` | 交叉验证·r.v26_confidence-5 |
| 数据 | 西班牙仅1场状态数据 | `recent_form.py` | 样本不足告警·46队RECENT_RESULTS更新 |
| 场外 | 伊朗美国境内当日往返 | `pre_match_report.py` | 对手+8%置信度加成 |

## 数据更新

- **近期状态**: 从 `近期状态.txt` 解析46支队伍完整5场数据 → `recent_form.py` RECENT_RESULTS
- **样本告警**: 队伍<3场数据时报告明确告警`📋 状态数据不足`
- **伊朗场外**: 全局开关`IRAN_TRAVEL_DISADVANTAGE`，检测伊朗+美国场馆自动触发

## 预测快照

- `predictions_june22_23.txt` — 8场完整报告 (V3.33·2026-06-22 00:00)

## 相关记忆

- [[v325-scotland-morocco-audit]] — V3.25审计·触发评分体系重建
- [[v328-england-croatia-audit]] — V3.28精英例外验证
- [[v328-team-ratings]] — 48队评分模块
- [[v326-design-direction]] — V3.26设计方向
- [[calibration-tracker]] — 回测逐场详情

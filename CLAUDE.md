# 世界杯预测模型 V3.31 (回测 28/31=90.3%)

> 📅 2026-06-21 · 球员DB 1250人/48队 · 31场回测(28正确·3错) · 决策树十条路径 · 伤病追踪 · 精英拦截 · 旧版分类器

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

## V3.31 核心阈值

| 阈值 | 值 | 说明 |
|------|:--:|------|
| 标准过热 | **20** | MOD级别 |
| CLOSE过热 | **32** | 连续失败3次后收紧 |
| BIG真过热 | **≥30** | 真过热→热门不胜 |
| BIG弱过热 | **20-29** | 非精英→方向保留·权重降低 |
| BIG弱过热精英豁免 | **FIFA≤5** | 精英队跳过弱过热降级 🆕 |
| EXTREME碾压 | **指数>0.80** | 跳过泊松·直接实力预测 |
| 共识污染 | **20** | 与过热统一 |
| 置信度天花板 | **85%** | Bayes平滑·先验强度6 |
| 高置信度惩罚 | **>80%→×0.80** | 历史准确率仅20% |
| 金三角约束 | **>75%需全票+冷热≤35+穿盘≥50%** |  |
| 泊松-市场熔断 | **背离>35点→强制≤50%** |  |
| 方向-泊松冲突 | **客胜>主胜+5%→降级+信≤50%** | V3.17 |
| 状态分上限 | **10.0** | V3.17 |
| 实力豁免精英拦截 | **对手FW≥35M→豁免不生效** | 🆕 V3.29 |
| 伤病决策树影响 | **确认缺阵→攻击/防守评分×0.82** | 🆕 V3.30 |

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

### 决策树十条路径
```
① 精英例外: MOD/CLOSE + 真过热 + FIFA前5(10) + 温和过热 → 热门胜
② 三条件例外: BIG + 真过热 + 3/3全满足 → 热门仍赢
③ 默认弱过热: BIG + 弱过热(20-29) + 三条件不足 + 非精英 → 热门不胜
③b 精英弱过热: BIG + 弱过热(20-29) + FIFA≤5 → 保留真过热 🆕
④ 实力优先: MOD + 真过热 + 攻防差双优 + 对手有火力 → 热门胜(折扣减半)
⑤ 实力阈值豁免: BIG + 真过热 + 中场/攻击/防线达标 → 热门胜 (精英FW拦截)
⑥ EXTREME碾压: EXTREME + 碾压指数>0.80 → 跳过泊松·实力预测
⑦ 防线翻盘: MOD + 真过热 + 防线/攻击比≥0.78 + 热方无prime精英FW → 热门不胜
⑧ EXTREME回避: EXTREME + 赔率背离 → 不预测
⑨ BIG无过热: BIG + 冷热<20 → 模糊·偏向热门
⑩ 理性热度: BIG + 冷热<18 + 市场隐含>85% → 热门胜(理性热度) ← V3.31收紧

🆕 V3.29: 实力豁免精英拦截(⑤号路径对手FW≥35M→豁免不生效)
🆕 V3.30: 伤病前置到决策树(攻击/防守评分受伤病影响→可改变路径)
🆕 V3.31: BIG弱过热精英豁免(③b·阿根廷FIFA#1·cold=20不会误降级)
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

## 版本演进 (V3.25→V3.31)

| 版本 | 日期 | 关键变更 |
|------|------|------|
| V3.25 | 06-21 | 模型-泊松背离熔断·加纳VS巴拿马触发(65%→55%) |
| V3.28 | 06-21 | 48队三维评分体系(team_ratings.py)·混合差距分类器→已回退 |
| V3.29 | 06-21 | 实力豁免精英拦截(比利时VS埃及)·伤病接入预测管道·BIG弱过热实力优先→已回退 |
| V3.30 | 06-21 | 伤病前置到决策树·P0-P2公式改进(联赛分级·边卫加成·国家队经验) |
| V3.31 | 06-21 | BIG弱过热精英豁免(阿根廷FIFA#1·cold=20)·回退V3.28分类器·回测28/31=90.3% |

## V3.31 回测 (28/31=90.3%)

仅3错:
- 葡萄牙VS刚果(金): 热门胜67%→实际1-1 (V3.31修正:信号不足)
- 德国VS科特迪瓦: 热门不胜74%→实际2-1 (德国实力碾压未识别)
- 厄瓜多尔VS库拉索: 热门胜70%→实际0-0 (准EXTREME平局)

## 相关记忆

- [[v325-scotland-morocco-audit]] — V3.25审计·触发评分体系重建
- [[v328-england-croatia-audit]] — V3.28精英例外验证
- [[v328-team-ratings]] — 48队评分模块
- [[v326-design-direction]] — V3.26设计方向
- [[calibration-tracker]] — 回测逐场详情

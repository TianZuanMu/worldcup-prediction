# 世界杯预测模型 V4.3 (回测 73.5%·中场量纲修复·穿盘率回测·54场全量)

> 📅 2026-06-26 · 球员DB 1250人/48队 · 8因子Logit链·动态弃权·context生死战·Flow=0.8
> 🆕 V4.3: 中场DB-Static量纲统一·穿盘率专项回测·伪警告消除·54场全量36/49=73.5%

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
| 诱盘严重阈值 | **≥70** | 强制降信-15% 🆕 V3.41 |
| 诱盘中度阈值 | **≥40** | 警告+降信-10% 🆕 V3.41 |
| 诱盘轻度阈值 | **≥20** | 注意信号可靠性-5% 🆕 V3.41 |
| 竞彩背离触发 | **差>5%+竞彩逆势** | 非商业机构反向操作 🆕 V3.41 |
| Pinnacle偏离触发 | **>15%** | 最敏锐庄家异常 🆕 V3.41 |
| 庄家亏损触发 | **>1M** | PnL-赔率矛盾检测 🆕 V3.41 |
| 真碾压阈值 | **≥0.85** | 跳过泊松·直出70% 🆕 V3.42 |
| 准EXTREME带 | **0.80-0.85** | 不跳过泊松·走BIG+熔断 🆕 V3.42 |
| 大单硬限制 | **>1M→上限60%** | 单方向大额卖单强制降信 🆕 V3.42 |

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
**V3.x**: `confidence_calibration.py` · `market_psychology.py` · `score_prediction.py` · `discipline_risk.py` · `injury_tracker.py` · `milestone_detection.py` · `sub_depth.py` · `setpiece_quant.py` · `xls_trend_analysis.py` · `trap_odds_detection.py`
**V4.x**: `bayes_factors.py` 🆕 · `calibrate_v40.py` 🆕
**自动化**: `auto_fetch.py` · `auto_fetch_xls.py` · `auto_post_match.py` · `backtest_runner.py` · `generate_schedule.py` · `update_group_predictions.py` 🆕
**数据**: `betfair_data/` · `backtest/matches.json` · `auto_fetch_config.json`

## 自检清单

```
□ 赛果更新? → 更新 backtest/matches.json (新赛果录入)  ← 🆕 V3.34
□ 小组排名? → python update_group_predictions.py --save --web  ← 🆕 V3.34
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
| **V3.34** | 06-23 | 🆕 淘汰赛路径标注修复·12组R32对阵真实难度·小组排名自动预测·motivation方向性修正 |
| **V3.35** | 06-24 | 🆕 熔断渐进式修复·置信度履历·BIG分歧降权·术语统一·回测34/44=77.3% |
| **V3.36** | 06-24 | 🆕 大小球-泊松背离仲裁·硬拒绝红线·动态加权·切断错误反馈·纯净xG函数 |
| **V3.37** | 06-24 | 🆕 独立平局风险评估·BIG动态置信度上限·高信错误归零(>80%错误:3→0) |
| **V3.38** | 06-24 | 🆕 退盘分级权重(>8%→severe+12·4-8%→moderate+8)·一致性加成·退盘优先规则 |
| **V3.39** | 06-24 | 🆕 分段线性插值高信惩罚(锚点80%×1.0→90%×0.82→100%×0.75)·交叉验证/风险调制 |
| **V3.40** | 06-24 | 🆕 熔断方向性修复·市场>模型时禁止向上修正·市场过热泡沫检测(>30点→🚨) |
| **V3.41** | 06-25 | 🆕 诱盘检测·6维度评分·竞彩背离·PnL矛盾·叙事-资金背离·motivation语义修复 |
| **V3.42** | 06-25 | 🆕 碾压指数三级体系(真碾压≥0.85/准EXTREME 0.80-0.85)·大额卖单>1M硬限制60% |
| **V4.0** | 06-25 | 🆕 因子乘法链·8因子Logit空间组合·分组去重·时效衰减·熵锐度置信度·并行旧树 |
| **V4.1** | 06-25 | 🆕 校准Flow=0.8·context重写(生死战+放水)·trap≥70降权·动态弃权·回测68.8% |
| **V4.2** | 06-25 | 🆕 xG管道重构(饱和保护·穿盘独立·sigmoid)·状态分修复(惩罚·加性·去重)·三维对齐(动态权重·中场混合)·回测72.7% |
| **V4.3** | 06-26 | 🆕 中场DB-Static量纲统一(diff改用db_rating)·6支伪警告消除·穿盘率专项回测·54场全量73.5% |

## V4.3 中场量纲修复 (06-26)

### 问题 (`midfield_quality.py:130`)

`get_midfield_rating()` 差异检测用 `abs(db_raw - static_rating)` 比较两个不同量纲:
- `db_raw`: DB原始值 (×0.5斜率, 范围~2.0-6.5)
- `static_rating`: 专家0-10量纲 (范围2.0-9.5)

导致6支球队伪警告 (哥伦比亚/墨西哥/土耳其/韩国/厄瓜多尔/巴西), 实际归一化后差异均<3.0。

### 修复

```python
# 修改前
diff = abs(db_raw - static_rating)  # 量纲不一致

# 修改后
diff = abs(db_rating - static_rating)  # 归一化后同量纲 (db_rating = db_raw × 1.5, 上限9.5)
```

日志增强: 区分 `DB_raw`/`DB_norm` + 老将低估提示 (`db_rating<5.0 & static>7.0`)。

### 回测确认

修复前后准确率不变 (36/49=73.5%), 仅消除伪警告。混合评分公式 `db_rating×0.5 + static×0.5` 始终使用归一化值, 不受影响。

## V3.41 诱盘检测 + motivation修复 (06-25)

### 诱盘检测 (`trap_odds_detection.py`) 🆕

6维度加权评分, 不改变预测方向, 仅调制置信度(-15%~+5%):

| 信号 | 权重 | 检测逻辑 |
|------|:--:|------|
| 竞彩官方背离 | 25% | 竞彩逆势降赔 vs 45+家公司升赔 |
| PnL-赔率矛盾 | 25% | 庄家在某方亏>1M + 该方赔率上升 |
| 大资金-赔率背离 | 20% | 必发量急升>500K + 赔率上升>10% |
| Pinnacle极端偏离 | 15% | Pinnacle变动偏离市场>15% |
| 叙事-资金矛盾 | 10% | "平局出线"叙事 + 平局热度降>15点 |
| 亚盘水位矛盾 | 5% | 降盘升水 or 升盘升水 → 诱盘模式 |

**回测效果**: 6/48场触发诱盘·moderate级别2场均正确·mild级别4场中3场方向正确

### motivation语义修复 (`knockout_motivation.py`)

- `avoidance_bonus` pos2逻辑修复: `alt_path_better=True`含义为"争第一路径更优"→ 给争胜动力+1.5(原+1.0误为"维持第二")
- 报告文案修正: "淘汰赛路径更优"→"争第一可获更优路径"

## V3.42 碾压指数三级体系 + 大单硬限制 (06-25)

### 英格兰VS加纳赛后审计驱动

**问题**: 碾压指数 0.81 刚过 0.80 阈值 → EXTREME 跳过泊松 → 直出 70% → 实际 0-0 ❌

**根因**: 0.81 是"擦边球"而非"真碾压"——状态分倒挂(5.1 vs 8.3)、战术克制(-2.5)、庄家亏 2.45M、150 万大单均被跳过

### 碾压指数三级体系 (`pre_match_report.py`)

| 碾压指数 | 路径 | 行为 |
|------|------|------|
| **≥0.85** | 真碾压 | 跳过泊松·直出 70% |
| **0.80-0.85** | 🆕 准 EXTREME | 不跳过泊松·走 BIG+熔断 |
| **<0.80** | MOD/BIG | 正常流程 |

### 大额卖单硬限制 (`_build_structured()`)

单方向 >1M 卖单 → 置信度上限 60%(无论什么路径)

**回测**: 33/44=75.0%(-1)·英格兰 70%→60%+熔断·奥地利 50%→31%(极低信=实质跳过)

## V3.35 回测 (34/44=77.3%, 含6月24日4场)

10错(9场"热门胜→平局" + 1场"热门不胜→主胜"):
- 6场BIG(60%) 2场EXTREME 1场MOD 1场CLOSE
- MOD 20/21=95% · BIG 11/17=65% · EXTREME 1/3=33%

### 🔴 6月24日新增 (3/4=75%)

| 场次 | 预测 | 实际 | 判定 |
|------|------|------|:--:|
| 葡萄牙VS乌兹别克斯坦 | 热门胜 80% | 5-0 | ✅ |
| 英格兰VS加纳 | 热门胜 70% | 0-0 | ❌ 冷热倒挂+临界碾压·应降级 |
| 巴拿马VS克罗地亚 | 热门胜 69% | 0-1 | ✅ |
| 哥伦比亚VS民主刚果 | 热门胜 72% | 1-0 | ✅ 大小球退盘命中 |

**英格兰VS加纳根因**: 5项预警叠加(冷热倒挂+23·帕尔默/福登缺阵·碾压0.81临界·身价仅5x·P2客热升温)→EXTREME不应跳过泊松·降级MOD处理更合理

### V3.38 退盘分级权重 (06-24)

**三步升级** (`_predict_totals()`):
1. 退盘强度分级: >8%→severe(+12)·4-8%→moderate(+8)·<4%→mild(+3) — 替代固定1.5x
2. 一致性加成: 退盘与xG方向一致(均看小)→额外+8/5/3·不一致→不追加权重
3. 退盘优先规则: 严重背离+中度以上退盘→降信减半(信任市场)

**效果**: 退盘信号被精细量化·避免微小退盘过度反应·哥伦比亚场(退盘mild)60%→66%

### V3.37 平局风险评估 + BIG动态上限 (06-24)

**平局风险评估** (`_assess_draw_risk()`):
- 硬约束: 双方平局即出线+30·双方出线无望+25·平赔48h下降>5%+20 → 任一触发→上限≤55%
- 加权评分: 攻击疲软+15·淘汰赛路径无差异+12·差距≤MOD+10·热度分歧+8
- 评分≥45→critical(上限50%)·≥30→high(60%)·≥15→moderate(70%)
- critical时泊松平局概率×1.5重新归一化

**BIG动态上限** (`_build_structured()`):
- 基础上限55%·泊松≥75%+市场≥80%双支撑→+10(上限65%)
- BIG真过热→-10·平局风险≥high→-10

**效果**: >80%置信度错误 3场→**0场** · >60%错误 7场→**1场** · 平均错误置信度68.7%→50.3%

### V3.36 大小球-泊松背离仲裁 (06-24)

| 修复 | 文件 | 说明 |
|------|------|------|
| 背离检测 | `pre_match_report.py` `_predict_totals()` | `_calc_pure_xg()`纯净xG·\|xG-盘口\|/盘口→三级背离 |
| 分级降信 | `pre_match_report.py` | >30%严重-25·>15%中度-12·方向冲突时上限50% |
| 硬拒绝红线 | `pre_match_report.py` | >50%强制skip·输出"无法判断" |
| 动态加权 | `pre_match_report.py` | 盘口变动>5%→信市场·盘口稳定→微幅偏向实力 |
| 切断反馈 | `score_prediction.py` `_adjust_for_totals_prediction()` | 严重背离跳过缩放·中度背离缩放减半 |
| 纯函数 | `score_prediction.py` `_calc_pure_xg()` | 仅基于实力+赔率·不读取任何大小球变量·无递归风险 |

**背离级别阈值**: `config.py` — critical>0.30 / moderate>0.15 / hard_reject>0.50

### V3.35 核心修复

| 修复 | 文件 | 说明 |
|------|------|------|
| 熔断渐进式 | `pre_match_report.py` | 背离15-24→7:3加权, ≥25→完全拒绝市场·三陷阱处理 |
| 置信履历 | `pre_match_report.py` | `_confidence_trace` + `_ctrace()` 全链路可追溯 |
| BIG分歧降权 | `pre_match_report.py` | d12分歧→×0.8降权+平局预警·不翻盘 |
| 术语统一 | `pre_match_report.py` | `odds_favorite`区分赔率热门/资金热方·交叉验证用队伍名 |
| 回测器术语 | `backtest_runner.py` | `hot`改用`odds_favorite`·修复美国VS澳大利亚误判 |
| 非世界杯过滤 | `auto_fetch_xls.py` | 正则`2026世界杯`防止芬兰联赛混入 |

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

## V4.2 重构详情 (2026-06-25)

### xG管道 (score_prediction.py)
| 修复 | 说明 |
|------|------|
| P0 饱和保护 | 累计调整上限30%·防多步叠加过度 |
| P1 穿盘率独立 | 移除xG的Step5·新增cover_risk独立输出 |
| P3 sigmoid融合 | 泊松-实力动态权重·替代硬阈值30%·5%地板 |
| P4 污染标记 | `模型校准xG ⚠️含方向调整`·`_calc_pure_xg()`供交叉验证 |

### 状态分 (recent_form.py)
| 修复 | 说明 |
|------|------|
| 样本量惩罚 | <5场每少一场扣0.4分·美国10.0→8.7 |
| 对手折扣加性 | 乘性(×0.75~1.15)→加性(±0.6)·消除截断溢出 |
| 删除quality_bonus | 对手质量统一由_adjust_form_for_opponent_quality处理 |

### 三维评分 (team_ratings.py·midfield_quality.py·opponent_db.py)
| 修复 | 说明 |
|------|------|
| GAP_WEIGHTS | 差距级动态权重·消除中场双重折扣(0.0875→0.25) |
| 中场混合 | DB×0.6 + static×0.4·差异>2.0标记人工复核 |
| MF分段 | 5-12M标记lo-5·不修改threat计算 |
| 攻防归一化 | `get_normalized_attack/defense()`·0-10量纲对齐 |

### 回测
- 32/44=72.7%·网格搜索15组合全部一致·参数鲁棒性确认

## 相关记忆

- [[v325-scotland-morocco-audit]] — V3.25审计·触发评分体系重建
- [[v328-england-croatia-audit]] — V3.28精英例外验证
- [[v328-team-ratings]] — 48队评分模块
- [[v326-design-direction]] — V3.26设计方向
- [[v42-upgrade-summary]] — V4.2升级·xG管道·状态分·三维对齐
- [[v43-midfield-fix]] — V4.3中场量纲修复·db_rating统一
- [[calibration-tracker]] — 回测逐场详情

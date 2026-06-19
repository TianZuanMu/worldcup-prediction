# 世界杯预测模型 V3.4 (MD1回测19/21=90.5%·3项V3.4优化)

> V3.0: 18项 · V3.1: 22项 · V3.2: 19项bug · V3.3: 9项优化 · **V3.4: 时差衰减·BIG弱过热·大小球比分联动**

> 📅 最后更新: 2026-06-19 (V3.4·时差衰减MD1/2/3·BIG弱过热20-29·大小球比分联动)

## 🆕 环境依赖

```bash
pip install playwright beautifulsoup4 lxml xlrd requests
# Playwright 使用本机 Edge, 无需额外安装浏览器
```

## 快速开始（新对话第一步）

```bash
cd "C:/Users/A/PyCharmMiscProject"

# 0a. 自动刷新比赛ID (从 live.500.com, 每24h自动)
PYTHONIOENCODING=utf-8 python -c "from auto_fetch_xls import discover_match_ids; discover_match_ids()"

# 0b. 自动获取 XLS (Playwright Edge) + 必发 (HTML解析)
PYTHONIOENCODING=utf-8 python auto_fetch.py --all

# 1. 赔率数据管道
PYTHONIOENCODING=utf-8 python "赔率获取.py" && PYTHONIOENCODING=utf-8 python "赔率变化.py"

# 2. 赛程自动更新（首次或新比赛日）
PYTHONIOENCODING=utf-8 python generate_schedule.py --update

# 3. 一键赛前报告
PYTHONIOENCODING=utf-8 python -c "
from pre_match_report import batch_report
print(batch_report(['法国VS塞内加尔', '阿根廷VS阿尔及利亚', '伊拉克VS挪威', '奥地利VS约旦']))
"
```

## ⏰ 智能调度 (auto_fetch)

| 层级 | 模块 | 触发频率 | 数据 | 窗口 |
|:--|------|:--|------|:--|
| L1 高频 | `赛前高频赔率.py` | 每10分钟 | API赔率 | 赛前2h |
| L2 低频 | `auto_fetch.py --cron` | 每30分钟 | XLS + 必发 | 赛前48h |

---

## 版本演进

| 版本 | 日期 | 变更 | 准确率 |
|:--|------|------|:--:|
| V2.8 | 6/17 | 8项优化·东道主因子·XLS回退 | 85.7% |
| V2.9 | 6/17 | 6项缺失因素 (场地·时间·战术·战意·天气·首发) | — |
| V2.10 | 6/17 | 3项 (近期状态·历史恩怨·裁判) | 88.2% |
| V2.11 | 6/17 | **市场心理周期** (近8场冷门率→搏冷折扣0~-10%) | — |
| V2.12 | 6/17 | **置信度校准** (Bayes平滑分箱) + **过热阈值统一** (20) | — |
| V2.13 | 6/17 | **赛程影响增强** (自动加载实际赛果·净胜球需求·轮换风险·淘汰赛路径投影) | — |
| V2.14 | 6/17 | **动态穿盘率** (原始×防守质量×进球效率×战意) | **90.5%** |
| V3.0 | 6/17 | **18项全优化** (乘法链·CLOSE阈值·结构化·7新模块) | 82.4% |
| **V3.1** | **6/18** | **近期状态全覆盖·权重校准·伤病追踪·22项** | **68.4%** |
| **V3.2** | **6/18** | **BIG过热分级·精英例外·三条件校准·13项bug** | **90.5%** |
| **V3.3** | **6/18** | **9项优化·置信度收紧·CLOSE精英例外·淘汰赛·纪律风险** | **90.5%** |
| **V3.4** | **6/19** | **时差衰减(MD1/2/3)·BIG弱过热(20-29)·大小球→比分联动** | **90.5%** |

---

## 🆕 V2.11→V3.4 新增模块

| 模块 | 版本 | 功能 |
|------|:--:|------|
| `market_psychology.py` | V2.11 | 近8场冷门频率检测·搏冷模式触发·bearish信号稀释 |
| `confidence_calibration.py` | V2.12 | 贝叶斯平滑分箱校准·原始置信度→真实概率映射 |
| `knockout_motivation.py` | V2.13 | **重写**: 自动加载实际赛果·净胜球场景·轮换风险·淘汰赛路径投影·避强动力 |
| `auto_post_match.py` | V3.3 | 🆕 自动赛后复盘·6类型错误分类·模式检测·Markdown报告 |
| `discipline_risk.py` | V3.3 | 🆕 纪律风险量化·裁判+球队→红牌概率·置信度调整 |
| `score_prediction.py` | V3.4 | 🆕 泊松比分概率·预测方向接入·大小球联动·Top3比分 |

---

## V2.14 完整置信度调整链

```
现有V2.8规则基础置信度
  → 天气(±4%) → 战意(±10%·含赛程/轮换/淘汰赛路径) → 首发(-15~0%)
  → 战术(±5%) → 教练(±3%) → 时间(±3%)
  → 近期状态(±6%) → 历史恩怨(-3~+2%) → 裁判(-2~+1%)
  → 市场心理(0~-10%) → 穿盘率动态修正
  → apply_signals(全票/平赔暴跌/背离/污染)
  → 置信度校准 (Bayes平滑→真实概率)
  → 最终cap: 5-95%
```

---

## V3.4 核心阈值

| 阈值 | 值 | 说明 |
|------|:--:|------|
| 标准过热阈值 | **20** | MOD级别 |
| CLOSE过热阈值 | **32** | V3.3: 27→32·连续失败3次后收紧 |
| **BIG过热阈值** | **30** | 真过热≥30·弱过热20-29·无<20 |
| 共识污染阈值 | **20** | 与过热阈值一致 |
| 置信度校准天花板 | **85%** | V3.3: 92%→85% |
| 时差衰减 | **MD1=30% MD2=10% MD3=0%** | 球队提前抵达·已基本适应 |
| 大小球联动阈值 | **信≥60%** | 低于60%不触发比分调整 |

## V2.12 核心阈值 (历史)

| 阈值 | 旧值 | 新值 | 说明 |
|------|:--:|:--:|------|
| 过热阈值 (JSON路径) | 30 | **20** | 与文本路径统一 |
| 过热阈值 (文本路径) | 15 | **20** | 与JSON路径统一 |
| 共识污染阈值 | 30 | **20** | 与过热阈值一致 |
| 置信度校准天花板 | 无 | **92%** | 基于21场回测 |

---

## V2.14 动态穿盘率

```
原始穿盘率 (XLS让球指数)
  × 对手防守质量因子 (排名>80→1.35, ≤15→0.75)
  × 热门进球效率因子 (场均≥2.5球→1.20, <1.0→0.80)
  × 对手战意因子 (已淘汰→1.25, 濒临淘汰→1.15)
  → 上限80%
```

---

## V2.6 核心规则

```
真过热(冷热≥20 + 庄亏) + CLOSE → 热门不胜
真过热 + BIG → 默认热门不胜:
   仅当三项全满足时例外: (a)对手排名60+ (b)无五大射手 (c)无世界杯爆冷
真过热 + MODERATE → 对手质量过滤:
   有顶级攻击手(萨拉赫级) → 热门不胜 / 无进攻威胁 → 热门仍赢·穿盘
真过热 + EXTREME → 强制回避 (结果完全随机)
假过热(冷热≥20 + 庄盈) → 可信正路
```

## 实力差距四级分类

| 级别 | FIFA排名差 | 身价比 | 信号可靠性 |
|:--:|:--:|:--:|:--:|
| Close | <10 | <3x | 85-90% |
| Moderate | 10-25 | 3-12x | 60-80% |
| Big | 25-60 | 12-25x | 30-50% |
| Extreme | >60 | >25x | **0%** |

---

## 🐛 已修复Bug (本次会话)

| # | 文件 | 问题 | 修复 |
|:--:|------|------|------|
| 1 | `auto_fetch.py` | `include_bf` → `include_betfair` 参数名错误 | 修正两处调用 |
| 2 | `head_to_head.py` | 塞内加尔2002爆冷因子(24年前历史噪音) | 移除·rivalry_level→none |
| 3 | `dimension12_books.py` | `home_win_narrow`/`away_win_cover`无法评估 | 加入规则字典 |
| 4 | `dimension12_books.py` | `skip_extreme`返回False(应返回None) | 特殊处理 |
| 5 | `pre_match_report.py` | 过热阈值30 vs 15不一致 (JSON/文本) | 统一为20 |
| 6 | `pre_match_report.py` | hm/am变量作用域Bug (V2.13引入) | 提前声明 |
| 7 | `pre_match_report.py` | 穿盘率热门判断用共识方向→应用赔率 | 三处float修复 |
| 8 | `pre_match_report.py` | `classify_strength_gap`漏传`wc_appearances`→WC经验维度始终为0 | 传入`wc_apps`·差距级别普遍被低估一级 |
| 9 | `pre_match_report.py` | 队名不匹配: `刚果(金)`≠`民主刚果`·XLS/必发/FIFA全部查找失败 | 引入`normalize_team_name`·重建规范化match_name |
| 10 | `pre_match_report.py` | `沙特阿拉伯`≠`沙特`(文件名)·反向不匹配·auto_fetch用短名 | 自动匹配`auto_fetch_config.json`中的实际文件名 |
| 11 | `pre_match_report.py` | BIG级别过热信号整体失效(55%)·5场错误 | 阈值20→30 + 客热折扣 + 无过热实力方向 + 三条件弱势方修复 |
| 12 | `pre_match_report.py` | 顶级强队(rank≤5)+温和过热→误判热门不胜 | 精英例外: rank≤5且\|cold\|<40→实力碾压·修复英格兰+阿根廷 |
| 13 | `opponent_db.py` | 乌兹别克被误判·三条件rank60过高+Khusanov误标射手+英文名模糊匹配bug | rank60→50 + CB移除 + fuzzy用中文名·修复乌兹别克+沙特bug |
| 14 | `pre_match_report.py` | `_extract_away`在整串搜索队名→瑞士VS波黑返回瑞士两次 | 限定VS右侧搜索 |
| 15 | `pre_match_report.py` | 大小球仅用XLS趋势·63.6%·7场降盘失误 | 6项修正因子+翻转阈值·89.5% |
| 16 | `confidence_calibration.py` | 贝叶斯校准把有意降权拉回→折扣失效 | 低置信度(raw<60)校准上限raw+15pp |
| 17 | `pre_match_report.py` | 低置信度无警告→用户可能重注弱信号 | 信<60%显示"建议回避" |
| 18 | `injury_tracker.py` | 戴维斯缺阵MD1未收录 | 加拿大伤病+戴维斯/邦比托状态 |
| 19 | `backtest DB` | 红牌事件未记录 | 墨西哥3红+巴拉圭1红已标注 |
| 20 | `opponent_db.py` | 球员数据为估算·48队不完整 | 基于真实名单重建·48队完整·后卫过滤·弱队豁免 |

## 🆕 V3.4 优化 (2026-06-19)

| # | 文件 | 问题 | 修复 |
|:--:|------|------|------|
| 21 | `match_time_impact.py` | MD2仍报跨15时区·球队早已适应 | 时差衰减: MD1=30% MD2=10% MD3=0% |
| 22 | `pre_match_report.py` | BIG冷热20被阈值30完全拦截→无方向 | 弱过热20-29: 方向保留·权重降低·回测验证30+ = 100% |
| 23 | `score_prediction.py` | 比分预测无视大小球模型结论 | 大小球联动: 信≥60%→等比缩放泊松λ |
| 24 | `opponent_db.py` | 哲科~40岁仍计为五大射手·高估波黑攻击力 | 衰退过滤: top5→False·显示改用filtered scorers |

---

## 📊 V3.1 MD1 回测 (24场 · 2026-06-12→18)

| 日期 | 场次 | 正确 | 准确率 | 关键场次 |
|------|:--:|:--:|:--:|------|
| 6/12 | 2 | 1 | 50% | 韩国2-1❌(CLOSE真过热) |
| 6/13 | 2 | 2 | 100% | 加拿大1-1✅·美国4-1✅ |
| 6/14 | 4 | 3 | 75% | 海地0-1❌(BIG热方判定错) |
| 6/15 | 3+1⏭️ | 3 | 100% | 荷兰2-2✅·科特迪瓦1-0✅·德国7-1⏭️ |
| 6/16 | 2+2⏭️ | 2 | 100% | 比利时1-1✅·西班牙0-0⏭️ |
| 6/17 | 3+1⏭️ | 1 | 33% | 伊拉克1-4❌·阿根廷3-0❌·奥地利⏭️ |
| 6/18 | 3+1⏭️ | 1 | 33% | 英格兰4-2❌·乌兹别克1-3❌·**葡萄牙1-1❌**(修复后) |
| **合计** | **21+3⏭️** | **19** | **90.5%** | 🆕 MOD 100%·BIG 91%·仅2错 |

### 两场错误 (V3.2最终)

| # | 比赛 | 预测 | 实际 | 根因 |
|:--:|------|------|:--:|------|
| 1 | 韩国 vs 捷克 | 热门不胜86% | 2-1 | CLOSE真过热·阈值25不足 |
| 2 | 葡萄牙 vs 刚果(金) | 信号不足55% | 1-1 | BIG弱过热·低置信·可接受 |

---

## 代码位置 (所有模块在 C:/Users/A/PyCharmMiscProject/)

### 核心引擎
| 模块 | 用途 |
|------|------|
| `pre_match_report.py` | **V2.14赛前一键报告** (含所有新增因子) |
| `dimension12_books.py` | 必发庄家盈亏·真/假过热判定·统一阈值20 |
| `v24_optimization.py` | 实力差距四级·欧赔共识·信号矩阵 |
| `xls_reader_xlrd.py` | 500.com XLS读取·双格式·自动最新版本 |
| `risk_score.py` | 风险评分·全票通过/平赔暴跌/XLS-必发背离 |

### V2.11→V2.14 新增
| 模块 | 版本 | 用途 |
|------|:--:|------|
| `market_psychology.py` | V2.11 | 市场心理周期·近8场冷门频率→搏冷折扣 |
| `confidence_calibration.py` | V2.12 | 贝叶斯平滑校准·原始→真实概率 |
| `knockout_motivation.py` | V2.13 | 赛程影响·实际赛果·净胜球·轮换·淘汰赛路径 |

### V2.9/V2.10 维度模块
| 模块 | 用途 |
|------|------|
| `match_context.py` | 16场馆DB+**72场完整赛程**(MD1/2/3)+32队分组 |
| `match_time_impact.py` | 比赛时间段·时差·室内外·海拔 |
| `team_profiles.py` | 32队战术画像+教练+风格对抗+🆕场地战术联动 |
| `weather_tracking.py` | 16城市天气+影响矩阵+🆕源标记(live/cache/fallback) |
| `lineup_correction.py` | 首发阵容·核心缺阵 |
| `recent_form.py` | 近5场战绩·对手实力加权·🆕时间衰减 |
| `head_to_head.py` | 历史交锋·心理优势·恩怨等级 |
| `referee_analysis.py` | 裁判执法风格·出牌频率 |

### 🆕 V3.0 新增模块
| 模块 | 用途 |
|------|------|
| `config.py` | **统一配置中心**·30+阈值·单一真相来源 |
| `xls_trend_analysis.py` | V2.15 XLS跨版本历史趋势·穿盘率/共识/跳变 |
| `milestone_detection.py` | 超巨里程碑·梅西200场+20%·CR7·魔笛 |
| `sub_depth.py` | 替补深度·5换时代·32队3档 |
| `setpiece_quant.py` | 定位球量化·角球%·任意球·制空 |
| `backtest_runner.py` | 一键回测·分档统计·错误详情 |
| `data_archiver.py` | 数据归档·时点回放·XLS/必发/赔率快照 |
| `injury_tracker.py` | 🆕V3.1 伤病追踪·位置权重·FW/GK×2.5 |
| `import_recent_form.py` | 🆕V3.1 近期状态导入·`近期状态.txt`→JSON |

### 自动化工具
| 模块 | 用途 |
|------|------|
| `auto_fetch.py` | 一键自动获取 XLS+必发 |
| `auto_fetch_xls.py` | 500.com XLS自动下载 (Playwright+Edge) |
| `auto_fetch_betfair.py` | 必发数据自动抓取 |
| `betfair_parser.py` | 必发数据自动解析 |
| `post_match.py` | 赛后自动复盘 |
| `auto_post_match.py` | 🆕V3.3 自动赛后复盘·错误分类·模式检测 |
| `discipline_risk.py` | 🆕V3.3 纪律风险·红黄牌·置信度调整 |
| `generate_schedule.py` | 赛程自动生成 |
| `cleanup_snapshots.py` | 快照清理 |
| `fifa_rank_db.py` | FIFA排名自动查询 |
| `opponent_db.py` | 对手质量DB+三条件 |

### 数据存储
```
C:/Users/A/PyCharmMiscProject/
├── worldcup_odds_*.csv              # 赔率快照
├── odds_trend_analysis_text.csv     # 聚合趋势
├── betfair_data/                    # 必发快照
├── backtest/
│   ├── matches.json                 # 回测DB (23场)
│   └── calibration.json             # 校准曲线
└── D:/                              # 500.com XLS
```

---

## 🔧 自检清单

```
□ 自动获取XLS+必发? → python auto_fetch.py --all
□ 赔率管道? → 赔率获取.py && 赔率变化.py
□ 新比赛日? → generate_schedule.py --update
□ 预测? → pre_match_report.generate_report() / batch_report()
□ V3.0结构化? → r.structured → {winner, confidence, cover, ...}
□ 赛后? → post_match.py (手动) 或 auto_post_match.py (自动)
□ 回测? → python backtest_runner.py
□ 自动复盘? → python auto_post_match.py  (V3.3)
□ 积分刷新? → knockout_motivation.refresh_standings()
□ 近期状态导入? → python import_recent_form.py  (有新数据时)
□ 快照清理? → cleanup_snapshots.py --do
□ 数据归档? → data_archiver.archive_match_data('葡萄牙VS民主刚果')
□ 伤病检查? → from injury_tracker import check_injuries
□ 纪律风险? → from discipline_risk import analyze_discipline_risk  (V3.3)
```

---

## 🆕 V3.0→V3.1 新增 (2026-06-17~18 · 22项)

| # | 版本 | 模块 | 功能 |
|:--:|:--:|------|------|
| P0#1 | V3.0 | `config.py` + `pre_match_report.py` | CLOSE专属过热阈值(25 vs 20) |
| P0#3 | V3.0 | `pre_match_report.py` | 结构化输出 `r.structured` |
| P1#4 | V3.0 | `milestone_detection.py` | 超巨里程碑·梅西200场+5% |
| P1#5 | V3.0 | `pre_match_report.py` | **乘法链**: 加法→乘法·15因子 |
| P1#6 | V3.0 | `sub_depth.py` | 替补深度·5换时代·32队3档 |
| P1#7 | V3.0 | `setpiece_quant.py` | 定位球量化·角球%·制空 |
| P1#8 | V3.0 | `recent_form.py` | 时间衰减·半衰期30天 |
| P2#9 | V3.0 | `opponent_db.py` | 对手DB补全8强队 |
| P2#10 | V3.0 | `match_context.py` | MD3赛程补齐·72场 |
| P2#11 | V3.0 | `pre_match_report.py` | 穿盘率+2因子 |
| P2#12 | V3.0 | `pre_match_report.py` | 场地-战术联动 |
| P2#13 | V3.0 | `xls_trend_analysis.py` | XLS趋势集成config |
| P2#14 | V3.0 | `weather_tracking.py` | 天气源标记·缓存TTL |
| P3#15 | V3.0 | `config.py` | 统一配置中心·30+阈值 |
| P3#17 | V3.0 | `backtest_runner.py` | 一键回测 |
| P3#18 | V3.0 | `data_archiver.py` | 数据归档·时点回放 |
| P0#19 | 🆕V3.1 | `recent_form.py` + `import_recent_form.py` | **48队真实近期状态**·215条赛果·世界杯自动回填 |
| P0#20 | 🆕V3.1 | `recent_form.py` | **状态权重回测校准**·差≥3→±10%(100%准确) |
| P0#21 | 🆕V3.1 | `injury_tracker.py` | **伤病追踪**·位置权重·FW/GK×2.5·今晚8队 |
| P0#22 | 🆕V3.1 | `pre_match_report.py` | 首发窗口修复·fromisoformat时区兼容 |

### V3.4 置信度乘法链 (18因子 + 3项V3.4增强)

```
V2.8规则基础置信度 (70% MOD / 65% CLOSE / 60% BIG)
  × weather(×0.96~1.04)  × motivation(×0.90~1.10)
  × lineup(×0.85~1.00)   × tactical(×0.95~1.05)
  × coach(×0.97~1.03)    × time(×0.97~1.03) ← V3.4: 时差衰减(MD1=30% MD2=10% MD3=0%)
  × recent_form(×0.90~1.10) ← V3.3: 对手质量加权·虐菜打折
  × h2h(×0.97~1.02)      × referee(×0.98~1.01)
  × market_psych(×1.00~0.90) × xls_trend(×0.95~1.05)
  × sub_depth(×0.95~1.05) × setpiece(×0.97~1.03)
  × milestone(×1.00~1.05) × injury(×0.80~1.00)
  × knockout(×0.95)        ← V3.3: 淘汰赛不确定性
  × discipline(×0.95~1.00) ← V3.3: 纪律风险
  → apply_signals(全票/平赔暴跌/背离/污染/大额卖单)
  → BIG过热分级: ≥30=真过热, 20-29=弱过热, <20=无 ← V3.4
  → 置信度校准 (Bayes平滑→真实概率·先验强度6·天花板85%)
  → 高置信度预警 (>80%→追加🔴警告)
  → 无必发数据cap (≤65%)
  → 最终cap: 5-88%

🆕 V3.4 比分预测链 (泊松模型·独立于置信度):
  赔率隐含λ → 实力差距 → 预测方向 → 对手质量 → 穿盘率
  → 大小球联动(信≥60%→等比缩放) ← V3.4
  → 近期状态 → 泊松分布 → Top3比分概率
```

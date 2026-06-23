# 2026 FIFA World Cup Prediction Model V3.35

Multi-dimensional prediction system combining decision tree rules, Poisson score modeling, dimension12 bookmaker analysis, and cross-validation.

**Backtest: 28/31 = 90.3%** · 决策树11路径 · 46队状态DB

## Quick Start

```bash
cd "C:/Users/A/PyCharmMiscProject"

# 1. Fetch XLS + Betfair
PYTHONIOENCODING=utf-8 python auto_fetch.py --all

# 2. Predict
PYTHONIOENCODING=utf-8 python -c "
from pre_match_report import batch_report
print(batch_report(['阿根廷VS奥地利', '法国VS伊拉克', '挪威VS塞内加尔', '约旦VS阿尔及利亚']))
"
```

## Features

- **11-Path Decision Tree**: Overheat detection (true/false/weak) across CLOSE/MOD/BIG/EXTREME levels
- **Poisson Score Prediction**: 7-layer λ adjustment chain (odds → gap → direction → quality → form → cover → totals)
- **dimension12 Cross-Validation**: Betfair bookmaker PnL analysis · true vs false overheat distinction
- **48-Team Player Database**: Real values, clubs, positions, top-5 league classification
- **Auto Data Pipeline**: XLS (500.com) + Betfair (必发) via Playwright
- **Chinese Lottery Integration**: 竞彩 handicap odds auto-extracted · totals odds manual config
- **Group Standings Prediction**: 🆕 Auto-load results → strength-based unplayed → 12-group final ranking
- **Knockout Path Analysis**: 🆕 Real R32 bracket difficulty · alt_path_better detection · motivation asymmetry

## Architecture

```
XLS Data (500.com)          Betfair Data (必发)
       │                          │
       └──────────┬───────────────┘
                  │
         pre_match_report.py  ←── Rule Engine (11 paths)
                  │                  • Overheat classification
                  │                  • Three-condition check
       ┌──────────┼──────────┐
       │          │          │
  score_prediction.py   dimension12_books.py
  (Poisson 7-layer λ)   (Bookmaker PnL)
       │          │          │
       └──────────┼──────────┘
                  │
          Cross-Validation
          (direction-score-cover)
                  │
            Final Report
```

## Core Modules

| Module | Description |
|--------|-------------|
| `pre_match_report.py` | Main engine · report generation · confidence chain |
| `score_prediction.py` | Poisson λ adjustment · predicted-winner targeting |
| `opponent_db.py` | 48-team quality · three-condition · V3.34 FW≥5M check |
| `dimension12_books.py` | Betfair PnL · true/false overheat · draw signal |
| `config.py` | Centralized thresholds |
| `recent_form.py` | 46-team last-5 · sample-size warning |
| `knockout_motivation.py` | 🆕 R32真实对阵 · 淘汰赛路径动机 · 战意分析 |
| `update_group_predictions.py` | 🆕 12组排名自动预测 · --save --web |
| `injury_tracker.py` | Injury impact · position-weighted |
| `auto_fetch.py` | XLS + Betfair pipeline |
| `weather_tracking.py` | 16-city weather · impact matrix |

## Strength Gap

| Level | FIFA Gap | Value Ratio | Reliability |
|:-----:|:--------:|:----------:|:----------:|
| CLOSE | <10 | <3x | 85-90% |
| MODERATE | 10-25 | 3-12x | 60-80% |
| BIG | 25-60 | 12-25x | 30-50% |
| EXTREME | >60 | >25x | **0%** (skip) |

## Odds Sources

| Market | Source | Method |
|--------|--------|--------|
| 胜平负 | 百家欧赔 (52 companies) | XLS auto |
| 让球胜平负 | 竞彩官方 (竞*官*) | XLS handicap_index auto |
| 总进球 | 竞彩** | `totals_odds_config.json` manual |
| 比分 | Estimated | — |

## Version History

| Ver | Date | Key Changes |
|-----|------|-------------|
| V3.2 | 06-18 | BIG overheat grading · 13 bugfixes | 
| V3.31 | 06-21 | BIG弱过热精英豁免 · 28/31=90.3% |
| **V3.32** | 06-21 | 三条件赔率判定 · dimension12覆盖 · market引用修正 |
| **V3.33** | 06-22 | λ预测赢家修正 · BIG攻击枯竭 · 真/假过热 · 5年爆冷 · 46队DB |
| **V3.34** | 06-23 | 淘汰赛路径标注修复 · R32对阵真实难度 · 小组排名预测 · motivation方向性修正 |
| **V3.35** | 06-23 | 🆕 置信度履历公开 · 熔断渐进式修复 · BIG分歧降权 · 术语统一(赔率热门≠资金热方) |

## License

MIT

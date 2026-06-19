# 2026 FIFA World Cup Prediction Model V3.4

A multi-dimensional machine learning prediction system for the 2026 FIFA World Cup, combining 12 analytical dimensions with Poisson score modeling, Over/Under integration, and cross-validation.

**Backtest: 20/28 = 71%** (MD1: 19/24 = 79% · MD2: 1/4)

## Features

- **12-Dimensional Analysis**: Strength gap, market consensus, betting heat, team quality, venue, weather, timezone, recent form, head-to-head, referee, tactics, lineup
- **Overheat Detection**: True/false/weak overheat classification with BIG/MOD/CLOSE-level thresholds
- **Poisson Score Prediction**: Top-3 score probabilities with integrated Over/Under model feedback
- **Cross-Validation**: Dual-model consistency check between rule engine and Poisson model
- **Jet Lag Decay**: Matchday-aware timezone impact (MD1=30% → MD2=10% → MD3=0%)
- **48-Team Player Database**: Real player values, clubs, positions, and top-5 league classification
- **Auto Data Pipeline**: XLS odds + Betfair data auto-fetch via Playwright

## Quick Start

```bash
cd "C:/Users/A/PyCharmMiscProject"

# 1. Auto-fetch XLS + Betfair data
PYTHONIOENCODING=utf-8 python auto_fetch.py --all

# 2. Odds pipeline
PYTHONIOENCODING=utf-8 python "赔率获取.py" && PYTHONIOENCODING=utf-8 python "赔率变化.py"

# 3. Predict
PYTHONIOENCODING=utf-8 python -c "
from pre_match_report import batch_report
print(batch_report(['捷克VS南非', '瑞士VS波黑', '加拿大VS卡塔尔', '墨西哥VS韩国']))
"
```

## Dependencies

```bash
pip install playwright beautifulsoup4 lxml xlrd requests
# Playwright uses system Edge browser, no extra install needed
```

## Architecture

```
XLS Data (500.com)          Betfair Data (必发)
       │                          │
       └──────────┬───────────────┘
                  │
         pre_match_report.py  ←── V2.6 Rule Engine
                  │                  • Overheat detection
                  │                  • Three-condition check
                  │                  • Strength gap classification
       ┌──────────┼──────────┐
       │          │          │
  score_prediction.py   _predict_totals()
  (Poisson model)       (Over/Under model)
       │          │          │
       └──────────┼──────────┘
                  │
          Cross-Validation
                  │
            Final Report
```

## Core Modules

| Module | Description |
|--------|-------------|
| `pre_match_report.py` | **Main engine** — one-click pre-match report with all factors |
| `score_prediction.py` | Poisson score probabilities · Over/Under integration |
| `match_time_impact.py` | Venue · timezone (with matchday decay) · altitude · indoor/outdoor |
| `opponent_db.py` | 48-team quality DB · three-condition checker · player values |
| `dimension12_books.py` | Betfair bookmaker PnL · true/false overheat classification |
| `config.py` | Centralized thresholds (30+ config values) |
| `market_psychology.py` | Bearish sentiment detection · cold streak discount |
| `confidence_calibration.py` | Bayesian smoothing calibration |
| `knockout_motivation.py` | Group standings · advancement scenarios · rotation risk |
| `discipline_risk.py` | Referee + team discipline · red card probability |
| `recent_form.py` | Last-5 match form · opponent-strength weighted |
| `head_to_head.py` | Historical matchups · rivalry level |
| `referee_analysis.py` | Referee style · card frequency |
| `weather_tracking.py` | 16-city real-time weather · impact matrix |
| `team_profiles.py` | Tactical profiles · coach impact · style matchups |
| `auto_fetch.py` | One-click XLS + Betfair data pipeline |
| `backtest_runner.py` | Backtesting suite · gap-level statistics |

## Strength Gap Classification

| Level | FIFA Rank Gap | Value Ratio | Signal Reliability |
|:-----:|:------------:|:----------:|:------------------:|
| CLOSE | <10 | <3x | 85-90% |
| MODERATE | 10-25 | 3-12x | 60-80% |
| BIG | 25-60 | 12-25x | 30-50% |
| EXTREME | >60 | >25x | **0%** |

## Overheat Tiers (BIG Level)

| Range | Classification | Action |
|:-----:|:-------------:|--------|
| ≥30 | True Overheat | Full weight |
| 20-29 | Weak Overheat | Direction preserved · weight reduced |
| <20 | No Overheat | Signal insufficient |

## Prediction Output

```
比赛                   | 差距     | 共识    | 冷热 | 三条件 | 预测              | 信  | 比分
捷克VS南非             | big     | -52%  | +58 | 3/3  | 热门仍赢·不穿盘    | 75% | 1-0(15%) 2-0(13%)
瑞士VS波黑             | big     | -37%  | +42 | 2/3  | ⚠️ 热门不胜       | 85% | 1-1(13%) 1-0(11%)
加拿大VS卡塔尔          | moderate| -71%  | +16 | 3/3  | 热门胜            | 88% | 1-0(14%) 2-0(13%)
墨西哥VS韩国            | moderate| +98%  | +48 | 0/3  | ⚠️ 热门不胜       | 40% | 1-1(11%) 2-1(10%)
```

## Version History

| Version | Date | Changes | Accuracy |
|---------|------|---------|:-------:|
| V2.8 | 6/17 | 8 optimizations · host factor · XLS fallback | 85.7% |
| V2.14 | 6/17 | Dynamic cover rate | **90.5%** |
| V3.0 | 6/17 | 18 optimizations · CLOSE threshold · structured output | 82.4% |
| V3.1 | 6/18 | 22 optimizations · 48-team form · injury tracking | 68.4% |
| V3.2 | 6/18 | BIG overheat grading · elite exception · 13 bugfixes | **90.5%** |
| V3.3 | 6/18 | 9 optimizations · knockout rules · discipline risk | **90.5%** |
| **V3.4** | **6/19** | **Jet lag decay · BIG weak overheat · O/U ↔ Score link** | **71%** |

## License

MIT

# -*- coding: utf-8 -*-
"""
赛前一键汇总报告 — 整合XLS+赔率趋势+必发+V2.6规则

输入: 比赛名 (如 "法国VS塞内加尔")
输出: 完整的赛前分析报告

用法:
  from pre_match_report import generate_report
  report = generate_report("法国VS塞内加尔", betfair_text=raw_betfair)
  print(report)
"""

import csv, json, os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

# 复用现有模块
from v24_optimization import classify_strength_gap, GapLevel, get_host_discount
from xls_reader_xlrd import read_all_xls, quick_summary

# V2.6 新模块
from risk_score import unanimity_signal, draw_collapse_signal, detect_xls_betfair_divergence
from opponent_db import check_three_conditions, check_moderate_opponent, opponent_quality
from fifa_rank_db import get_gap_info, get_team_info

# V2.9 新模块 (6项缺失因素)
from match_context import get_venue_for_match, get_match as get_group_match, get_team_group, normalize_team_name
from match_time_impact import analyze_match_time, TimeImpact
from team_profiles import get_team_profile, analyze_tactical_matchup, analyze_coach, get_tactical_edge, analyze_venue_tactic_interaction, get_venue_tactic_adj
from knockout_motivation import get_match_motivation, MatchMotivation, refresh_standings
from weather_tracking import get_weather, analyze_weather_impact, WeatherData, WeatherImpact
from lineup_correction import get_match_lineup_impact, LineupImpact

# V2.10 新模块 (近期状态·历史恩怨·裁判)
from recent_form import analyze_recent_form, get_form_diff, RecentForm
from head_to_head import analyze_h2h_impact, get_h2h
from referee_analysis import analyze_referee_impact, get_referee
from config import CONF, get_overheat_threshold
from market_psychology import get_cold_streak_factor
from confidence_calibration import calibrate as calibrate_confidence
from xls_trend_analysis import analyze_xls_trend, trend_summary, XlsTrendResult
from score_prediction import predict_score_from_report, format_score_output, format_score_output_compact, ScorePrediction

# V3.0 新模块 (预导入·容错)
try:
    from milestone_detection import detect_milestones
except ImportError:
    detect_milestones = None
    import sys; print('⚠️ V3.3: milestone_detection 导入失败 → 超巨里程碑维度将跳过', file=sys.stderr)
try:
    from sub_depth import analyze_sub_depth
except ImportError:
    analyze_sub_depth = None
    import sys; print('⚠️ V3.3: sub_depth 导入失败 → 替补深度维度将跳过', file=sys.stderr)
try:
    from setpiece_quant import analyze_setpiece
except ImportError:
    analyze_setpiece = None
    import sys; print('⚠️ V3.3: setpiece_quant 导入失败 → 定位球维度将跳过', file=sys.stderr)
try:
    from team_profiles import analyze_venue_tactic_interaction
except ImportError:
    analyze_venue_tactic_interaction = None
    import sys; print('⚠️ V3.3: team_profiles.analyze_venue_tactic_interaction 导入失败 → 场地战术联动将跳过', file=sys.stderr)
try:
    from injury_tracker import get_match_injury_impact
except ImportError:
    get_match_injury_impact = None
    import sys; print('⚠️ V3.3: injury_tracker 导入失败 → 伤病维度将跳过', file=sys.stderr)

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")
TREND_FILE = PROJECT_DIR / "odds_trend_analysis_text.csv"


@dataclass
class PreMatchReport:
    match_name: str = ""
    generated_at: str = ""

    # 实力差距
    gap_level: str = ""
    fifa_rank_gap: int = 0
    squad_value_ratio: float = 0.0
    hot_team_fifa_rank: int = 0       # 🆕 V3.2: 热方FIFA排名
    _totals_prediction: dict = field(default_factory=dict)  # 🆕 V3.2: 大小球预测
    midfield_comparison: dict = field(default_factory=dict)  # 🆕 V3.2: 中场对比
    books_structure: dict = field(default_factory=dict)       # 🆕 V3.3: dimension12交叉验证
    # 🆕 V3.3: dimension12_books原始数据 (用于analyze_books_structure交叉验证)
    _bf_raw_odds: dict = field(default_factory=dict)
    _bf_raw_volumes: dict = field(default_factory=dict)
    _bf_raw_pnls: dict = field(default_factory=dict)
    gap_detail: str = ""

    # XLS数据
    xls_summary: str = ""
    xls_consensus_pct: float = 0.0
    xls_consensus_direction: str = ""   # 'bullish'/'bearish'/'neutral'
    xls_consensus_source: str = ""      # 'XLS_stats'/'API_trend'/'manual'
    xls_consensus_confidence: str = ""  # 'high'/'medium'/'low'
    xls_handicap: str = ""
    xls_totals: str = ""
    _totals_line: float = 2.5  # 🆕 大小球实际数值
    xls_cover_rate: float = 0.0
    xls_cover_rate_raw: float = 0.0  # V2.14 原始XLS值
    xls_bookmakers: int = 0
    xls_trend: Optional[XlsTrendResult] = None  # V2.15 XLS跨版本趋势

    # 赔率趋势
    odds_home_chg: float = 0.0
    odds_draw_chg: float = 0.0
    odds_away_chg: float = 0.0
    odds_signals: list = field(default_factory=list)

    # 必发 (来自 betfair_parser)
    betfair_cold: float = 0.0
    betfair_hot_side: str = ""
    betfair_is_real_hot: bool = False
    big_weak_overheat: bool = False      # 🆕 V3.3: BIG级别弱过热 (冷热20-29)
    _late_surge: bool = False            # 🆕 V3.4: 冷热晚期飙升 (0→40+反向指标)
    _late_surge_early: float = 0.0
    _late_surge_late: float = 0.0
    betfair_pollution: bool = False
    betfair_pollution_gap: float = 0.0
    betfair_big_sell: bool = False
    betfair_big_sell_count: int = 0         # 🆕 V3.5: 大额卖单笔数
    betfair_big_sell_volume: float = 0.0    # 🆕 V3.5: 大额卖单总金额

    # V2.6 新信号
    unanimity: dict = field(default_factory=dict)
    draw_collapse: dict = field(default_factory=dict)
    xls_bf_divergence: dict = field(default_factory=dict)
    three_conditions: dict = field(default_factory=dict)
    moderate_threat: dict = field(default_factory=dict)

    # V2.6规则匹配
    v26_rule: str = ""
    v26_prediction: str = ""
    v26_confidence: int = 0
    v26_score_predictions: list = field(default_factory=list)
    v26_warnings: list = field(default_factory=list)
    score_prediction: Optional[ScorePrediction] = None  # 🆕 V3.3: 泊松比分概率

    # V3.0 结构化输出 (P0#3 + P3#16)
    structured: Optional[dict] = None

    # 信号矩阵
    signal_matrix: dict = field(default_factory=dict)

    # ── V2.9 新维度 ──
    # 场地与赛程
    venue: Optional[dict] = None
    team_group_home: str = ""
    team_group_away: str = ""
    matchday: int = 0

    # 比赛时间影响
    time_impact: Optional[TimeImpact] = None

    # 天气
    weather: Optional[WeatherData] = None
    weather_impact: Optional[WeatherImpact] = None

    # 出线形势
    match_motivation: Optional[MatchMotivation] = None

    # 首发阵容 (赛前60-90分钟窗口)
    lineup_impact: Optional[LineupImpact] = None

    # 战术 & 教练
    tactical_edge: float = 0.0
    coach_impact: float = 0.0
    style_clash_note: str = ""

    # ── V2.10 新维度 ──
    # 近期状态
    home_recent_form: Optional[dict] = None
    away_recent_form: Optional[dict] = None
    form_diff: dict = field(default_factory=dict)

    # 历史恩怨
    h2h_result: dict = field(default_factory=dict)

    # 裁判因素
    referee_result: dict = field(default_factory=dict)

    # 🆕 V2.11 市场心理周期
    market_psychology: dict = field(default_factory=dict)


def generate_report(match_name: str,
                    betfair_text: str = "",
                    xls_version: int = None,
                    fifa_rank_home: Optional[int] = None,
                    fifa_rank_away: Optional[int] = None,
                    squad_value_home: Optional[float] = None,
                    squad_value_away: Optional[float] = None) -> PreMatchReport:
    """生成完整的赛前分析报告"""
    r = PreMatchReport(match_name=match_name)
    r.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 0. 队名规范化 + 自动匹配auto_fetch配置的文件名
    home_cn_raw = match_name.split('VS')[0].strip()
    away_cn_raw = match_name.split('VS')[-1].strip() if 'VS' in match_name else ''
    home_cn = normalize_team_name(home_cn_raw)
    away_cn = normalize_team_name(away_cn_raw)
    match_name_normalized = f'{home_cn}VS{away_cn}'

    # 0b. 如果规范化名称与auto_fetch配置的文件名不一致, 优先使用配置名 (XLS/必发文件以此命名)
    try:
        import json as _json
        _cfg = _json.load(open(PROJECT_DIR / 'auto_fetch_config.json', 'r', encoding='utf-8'))
        for _cfg_name in _cfg.get('matches', {}):
            _cfg_home = normalize_team_name(_cfg_name.split('VS')[0].strip())
            _cfg_away = normalize_team_name(_cfg_name.split('VS')[-1].strip())
            if _cfg_home == home_cn and _cfg_away == away_cn and _cfg_name != match_name_normalized:
                match_name_normalized = _cfg_name  # 使用实际文件名 (如 沙特VS乌拉圭)
                break
    except Exception:
        pass  # auto_fetch_config.json 不存在或格式错误, 使用规范化名称

    # 1. XLS数据 (V3.0: 支持指定历史版本) — 使用规范化名称
    _load_xls(r, match_name_normalized, xls_version=xls_version)

    # 1b. 🆕 V2.15 XLS跨版本历史趋势
    r.xls_trend = analyze_xls_trend(match_name_normalized)

    # 2. 赔率趋势
    _load_odds_trend(r, match_name_normalized)

    # 3. 必发解析 — 使用规范化名称
    _load_betfair(r, betfair_text, match_name_normalized)

    # 4. 实力差距 (自动从DB填充·使用规范化队名)
    wc_apps_home = 0
    wc_apps_away = 0
    if not fifa_rank_home:
        info = get_team_info(home_cn)
        fifa_rank_home = info['rank']
        squad_value_home = info['value_m']
        wc_apps_home = info.get('wc_apps', 0)
    if not fifa_rank_away:
        info = get_team_info(away_cn)
        fifa_rank_away = info['rank']
        squad_value_away = info['value_m']
        wc_apps_away = info.get('wc_apps', 0)

    if fifa_rank_home and fifa_rank_away:
        gap = classify_strength_gap(
            fifa_rank_home=fifa_rank_home,
            fifa_rank_away=fifa_rank_away,
            squad_value_home=squad_value_home,
            squad_value_away=squad_value_away,
            wc_appearances_home=wc_apps_home,
            wc_appearances_away=wc_apps_away,
        )
        r.gap_level = gap.level.value
        r.fifa_rank_gap = gap.fifa_rank_gap
        r.squad_value_ratio = gap.squad_value_ratio
        r.gap_detail = str(gap.level)
        # 🆕 V3.2: 记录热方FIFA排名 (精英队过热例外)
        if r.betfair_hot_side == 'home':
            r.hot_team_fifa_rank = fifa_rank_home
        elif r.betfair_hot_side == 'away':
            r.hot_team_fifa_rank = fifa_rank_away

    # 4b. 🆕 V2.9 场地与赛程上下文
    try:
        r.venue = get_venue_for_match(match_name=match_name)
        gm = get_group_match(match_name=match_name)
        if gm:
            r.matchday = gm.matchday
            r.team_group_home = get_team_group(home_cn) or ''
            r.team_group_away = get_team_group(away_cn) or ''
    except Exception:
        pass

    # 4c. 🆕 V2.9 比赛时间影响
    try:
        r.time_impact = analyze_match_time(match_name, matchday=getattr(r, 'matchday', 1))
    except Exception:
        pass

    # 4d. 🆕 V2.9 天气追踪
    try:
        r.weather = get_weather(match_name)
        if r.weather:
            r.weather_impact = analyze_weather_impact(r.weather, home_cn, away_cn)
    except Exception:
        pass

    # 4e. 🆕 V2.9 战术与教练
    try:
        r.tactical_edge = get_tactical_edge(home_cn, away_cn)
        coach = analyze_coach(home_cn, away_cn)
        r.coach_impact = coach.get('impact', 0)
        matchup = analyze_tactical_matchup(home_cn, away_cn)
        r.style_clash_note = matchup.get('note', '')

        # 🆕 V3.0 P2#12: 场地-战术联动
        if analyze_venue_tactic_interaction and r.venue:
            try:
                hp = get_team_profile(home_cn)
                ap = get_team_profile(away_cn)
                vti = analyze_venue_tactic_interaction(r.venue, hp, ap)
                if vti.get('confidence_adj', 0) != 0:
                    r.tactical_edge += vti.get('confidence_adj', 0) * 0.5
                    for fct in vti.get('factors', [])[:2]:
                        r.v26_warnings.append(f'🏟️ {fct}')
            except Exception:
                pass
    except Exception:
        pass

    # 4f. 🆕 V2.13 出线形势 (自动加载实际赛果)
    try:
        refresh_standings()  # V2.13: 每次预测前刷新积分表
        r.match_motivation = get_match_motivation(match_name)
    except Exception:
        pass

    # 4g. 🆕 V2.9 首发阵容 (仅在窗口内激活)
    try:
        r.lineup_impact = get_match_lineup_impact(match_name)
    except Exception:
        pass

    # 4h. 🆕 V2.10 近期状态
    try:
        r.home_recent_form = analyze_recent_form(home_cn).__dict__ if analyze_recent_form(home_cn) else None
        r.away_recent_form = analyze_recent_form(away_cn).__dict__ if analyze_recent_form(away_cn) else None
        r.form_diff = get_form_diff(home_cn, away_cn)
    except Exception:
        pass

    # 4i. 🆕 V2.10 历史恩怨
    try:
        r.h2h_result = analyze_h2h_impact(home_cn, away_cn)
    except Exception:
        pass

    # 4j. 🆕 V2.10 裁判因素
    try:
        r.referee_result = analyze_referee_impact(match_name, home_cn, away_cn)
    except Exception:
        pass

    # 5. XLS-必发背离检测
    if betfair_text and r.xls_consensus_direction:
        try:
            from betfair_parser import parse_betfair_text
            bf = parse_betfair_text(betfair_text, match_name)
            home_odds = r._home_odds if hasattr(r, '_home_odds') else 1.5
            # 判断强队交易比例
            if home_odds <= 1.60:
                strong_trade = bf.home_trade_ratio
            else:
                strong_trade = bf.away_trade_ratio
            r.xls_bf_divergence = detect_xls_betfair_divergence(
                r.xls_consensus_direction, strong_trade,
                bf.hot_index, home_odds
            )
        except Exception:
            pass

    # 🆕 V2.8: XLS加载失败时，从赔率趋势构造替代共识信号
    if r.xls_consensus_source == 'fallback' and r.odds_home_chg != 0:
        # 用赔率趋势方向替代XLS共识
        if r.odds_home_chg > 3:
            r.xls_consensus_direction = 'bearish'
            r.xls_consensus_pct = min(r.odds_home_chg * 5, 80)
        elif r.odds_home_chg < -3:
            r.xls_consensus_direction = 'bullish'
            r.xls_consensus_pct = max(r.odds_home_chg * 5, -80)
        elif r.odds_away_chg > 3:
            r.xls_consensus_direction = 'bearish'
            r.xls_consensus_pct = min(r.odds_away_chg * 3, 60)
        elif r.odds_away_chg < -3:
            r.xls_consensus_direction = 'bullish'
            r.xls_consensus_pct = max(r.odds_away_chg * 3, -60)
        else:
            r.xls_consensus_direction = 'neutral'
            r.xls_consensus_pct = 0
        r.xls_consensus_source = 'odds_trend_fallback'
        r.v26_warnings.append('⚠️ XLS数据缺失·使用赔率趋势替代 (置信度-10%)')

    # 5b. 🆕 V2.14 动态穿盘率修正
    _adjust_cover_rate(r, home_cn, away_cn)

    # 6. V2.6规则匹配
    _apply_v26_rules(r)

    return r


def _load_xls(r: PreMatchReport, match_name: str, xls_version: int = None):
    """加载XLS数据 (V3.0: xls_version指定历史版本)"""
    try:
        if xls_version is not None:
            data = read_all_xls(match_name, use_version=xls_version)
        else:
            data = read_all_xls(match_name, use_latest=True)
        r.xls_summary = quick_summary(data)

        # 提取欧赔共识
        if data and 'european' in data:
            euro = data['european']
            # V2.14: 存储即时赔率供穿盘率计算使用
            inst = euro.get('summary', {}).get('instant', {})
            if inst:
                r._home_odds = float(inst.get('win', 2.0))
                r._away_odds = float(inst.get('lose', 2.0))
            stats = euro.get('stats', {})
            win_up = stats.get('win_up_count', 0)
            win_down = stats.get('win_down_count', 0)
            bk_list = euro.get('bookmakers', [])
            total = len(bk_list) if bk_list else 0
            r.xls_bookmakers = total
            if total > 0:
                r.xls_consensus_pct = (win_up - win_down) / total * 100
                r.xls_consensus_source = 'XLS_stats'
                # 共识置信度: 基于博彩公司数量和新鲜度
                if total >= 40 and abs(r.xls_consensus_pct) > 30:
                    r.xls_consensus_confidence = 'high'
                elif total >= 30:
                    r.xls_consensus_confidence = 'medium'
                else:
                    r.xls_consensus_confidence = 'low'

                if r.xls_consensus_pct > 15:
                    r.xls_consensus_direction = 'bearish'
                elif r.xls_consensus_pct < -15:
                    r.xls_consensus_direction = 'bullish'
                else:
                    r.xls_consensus_direction = 'neutral'

        # 提取穿盘率
        if data and 'handicap_index' in data:
            hi = data['handicap_index']
            by_line = hi.get('by_line', {})
            primary = hi.get('primary_line', None)
            if primary and primary in by_line:
                r.xls_cover_rate = by_line[primary].get('avg_win_prob', 0)

        # 提取亚盘/大小球方向
        if data and 'asian' in data:
            asian = data['asian']
            la = asian.get('line_analysis', {})
            r.xls_handicap = la.get('direction', '')
        if data and 'totals' in data:
            tot = data['totals']
            la = tot.get('line_analysis', {})
            r.xls_totals = la.get('direction', '')
            # 🆕 存储实际大小球数值
            r._totals_line = la.get('instant_line', 2.5)

    except Exception as e:
        r.xls_summary = f"XLS加载失败: {e}"
        # V2.8: XLS加载失败时，从赔率趋势构造替代共识信号
        # 防止沙特vs乌拉圭式的数据缺失导致置信度断崖
        r.xls_consensus_source = 'fallback'
        r.xls_consensus_confidence = 'low'
        r.xls_bookmakers = 0


def _load_odds_trend(r: PreMatchReport, match_name: str):
    """加载赔率趋势数据 + V2.6新信号"""
    if not TREND_FILE.exists():
        return

    home_team = _extract_home(match_name)
    away_team = _extract_away(match_name)

    # 🆕 V3.4: 中文→英文映射 (CSV使用英文队名)
    try:
        from match_context import CN_TO_EN
        home_en = CN_TO_EN.get(home_team, home_team)
        away_en = CN_TO_EN.get(away_team, away_team)
    except Exception:
        home_en = home_team
        away_en = away_team

    try:
        with open(TREND_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            h2h = {}
            home_changes = []  # 每家博彩公司的主胜变化
            draw_changes_all = []
            for row in reader:
                row_home = row['主队']
                row_away = row['客队']
                # 同时匹配中文和英文名
                if (row_home in (home_team, home_en) and
                    row_away in (away_team, away_en)):
                    if row['市场类型'] == 'h2h':
                        outcome = row['选项']
                        chg = float(row['变化百分比'])
                        if outcome not in h2h:
                            h2h[outcome] = []
                        h2h[outcome].append(chg)

            # 🆕 V3.4: 同时匹配中英文队名 (CSV选项使用英文)
            home_key = home_en if home_en in h2h else (home_team if home_team in h2h else None)
            away_key = away_en if away_en in h2h else (away_team if away_team in h2h else None)
            if home_key:
                r.odds_home_chg = sum(h2h[home_key]) / len(h2h[home_key])
                home_changes = h2h[home_key]
            if 'Draw' in h2h:
                r.odds_draw_chg = sum(h2h['Draw']) / len(h2h['Draw'])
                draw_changes_all = h2h['Draw']
            if away_key:
                r.odds_away_chg = sum(h2h[away_key]) / len(h2h[away_key])

            # V2.6 新信号
            r.unanimity = unanimity_signal(home_changes)
            r.draw_collapse = draw_collapse_signal(draw_changes_all)

            # 传统信号
            if r.odds_home_chg > 2:
                r.odds_signals.append(f"主胜赔率上升{r.odds_home_chg:+.1f}%")
            if r.odds_draw_chg < -2:
                r.odds_signals.append(f"平赔下降{r.odds_draw_chg:+.1f}%·平局预警")
            if r.odds_away_chg > 2:
                r.odds_signals.append(f"客胜赔率上升{r.odds_away_chg:+.1f}%")

            # 新信号描述
            if r.unanimity.get('triggered'):
                r.odds_signals.append(f"🔴 全票通过: {r.unanimity['ratio']:.0%}博彩公司同向·{r.unanimity['strength']}")
            if r.draw_collapse.get('triggered'):
                r.odds_signals.append(f"🔴🔴 平赔暴跌: {r.draw_collapse['avg_change']:.1f}% ({r.draw_collapse['down_count']}家)·{r.draw_collapse['severity']}")

    except Exception as e:
        r.odds_signals.append(f"趋势加载失败: {e}")


def _load_betfair(r: PreMatchReport, betfair_text: str, match_name: str):
    """加载必发数据 — 🆕 JSON优先 (避免文本解析Bug)"""
    # 🆕 V3.3 P0-2: 默认标记为fallback，JSON成功则清除
    r._betfair_from_fallback = True
    # 1. 优先从 betfair_data/ JSON 读取
    try:
        # betfair_store 将文件名中的 / \ 空格 替换为 _
        safe_name = match_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        bf_file = PROJECT_DIR / 'betfair_data' / f'{safe_name}.json'
        if bf_file.exists():
            import json
            with open(bf_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('snapshots'):
                snap = data['snapshots'][-1]
                bf = snap['betfair']
                r.betfair_cold = bf.get('home_heat', 0)
                # 找出热方: 取最大值 (正=热, 负=冷)
                colds = [bf.get('home_heat',0), bf.get('draw_heat',0), bf.get('away_heat',0)]
                max_c = max(colds)  # 最正=最热
                r.betfair_hot_side = ['home','draw','away'][colds.index(max_c)]
                r.betfair_is_real_hot = (max_c >= 20 and
                    [bf.get('home_pnl',0), bf.get('draw_pnl',0), bf.get('away_pnl',0)][colds.index(max_c)] < 0)
                # 共识污染
                trade = [bf.get('home_trade',0), bf.get('draw_trade',0), bf.get('away_trade',0)]
                prob = [bf.get('home_prob',0), bf.get('draw_prob',0), bf.get('away_prob',0)]
                if any(t > 0 for t in trade) and any(p > 0 for p in prob):
                    gaps = [abs(trade[i]-prob[i])*100 for i in range(3)]
                    r.betfair_pollution_gap = max(gaps)
                    r.betfair_pollution = any(g > CONF.pollution_threshold and abs(colds[i]) >= CONF.overheat_threshold and
                        [bf.get('home_pnl',0),bf.get('draw_pnl',0),bf.get('away_pnl',0)][i] < 0
                        for i, g in enumerate(gaps))
                # 大单
                trades = snap.get('big_trades', [])
                big_sells = [t for t in trades if t.get('direction') == '卖' and t['volume'] > 50000]
                r.betfair_big_sell = len(big_sells) > 0
                r.betfair_big_sell_count = len(big_sells)
                r.betfair_big_sell_volume = sum(t['volume'] for t in big_sells)
                r._betfair_from_fallback = False  # 🆕 V3.3: JSON成功·数据可靠
                # 🆕 V3.4: 冷热晚期飙升检测 (回测: 0→40+ 三场全错)
                all_snaps = data.get('snapshots', [])
                if len(all_snaps) >= 3:
                    early_colds = []
                    late_colds = []
                    for s in all_snaps:
                        b = s.get('betfair', {})
                        ch = max(b.get('home_heat', 0) or 0, b.get('away_heat', 0) or 0)
                        if ch > 0:
                            # 粗略分组: 前1/3为早期, 后1/3为晚期
                            pass
                    # 取第1个和最后2个快照的冷热
                    first_val = 0
                    for s in all_snaps[:1]:
                        b = s.get('betfair', {})
                        first_val = max(b.get('home_heat', 0) or 0, b.get('away_heat', 0) or 0)
                    last_vals = []
                    for s in all_snaps[-2:]:
                        b = s.get('betfair', {})
                        ch = max(b.get('home_heat', 0) or 0, b.get('away_heat', 0) or 0)
                        last_vals.append(ch)
                    last_avg = sum(last_vals) / 2 if last_vals else 0
                    # 检测: 最初无热(≤5) → 最终极热(≥40)
                    if first_val <= 5 and last_avg >= 40:
                        r._late_surge = True
                        r._late_surge_early = round(first_val)
                        r._late_surge_late = round(last_avg)
                # 🆕 V3.3: 存储原始数据供 dimension12_books 交叉验证
                r._bf_raw_odds = {'home': bf.get('home_price', 0) or bf.get('home_odds', 0),
                                  'draw': bf.get('draw_price', 0) or bf.get('draw_odds', 0),
                                  'away': bf.get('away_price', 0) or bf.get('away_odds', 0)}
                r._bf_raw_volumes = {'home': bf.get('home_volume', 0), 'draw': bf.get('draw_volume', 0), 'away': bf.get('away_volume', 0)}
                r._bf_raw_pnls = {'home': bf.get('home_pnl', 0), 'draw': bf.get('draw_pnl', 0), 'away': bf.get('away_pnl', 0)}
                return  # JSON成功，跳过文本解析
    except Exception:
        pass

    # 2. 回退: 文本解析 (兼容旧接口)
    if betfair_text:
        try:
            from betfair_parser import parse_betfair_text
            bf = parse_betfair_text(betfair_text, match_name)
            r.betfair_cold = bf.hot_index
            r.betfair_hot_side = bf.hot_side
            r.betfair_is_real_hot = bf.is_real_hot
            r.betfair_pollution = bf.consensus_pollution
            r.betfair_pollution_gap = bf.pollution_gap
            r.betfair_big_sell = bf.big_sell_warning
            r.betfair_big_sell_count = bf.big_sell_count
            r.betfair_big_sell_volume = bf.big_sell_total_volume
        except Exception:
            pass


def _adjust_cover_rate(r: PreMatchReport, home_cn: str, away_cn: str):
    """
    V2.14 动态穿盘率修正

    原始穿盘率仅从XLS让球指数静态读取, 不考虑:
    - 对手防守质量 (排名越高防守越好 → 更难穿盘)
    - 热门近期进球效率 (进球多 → 更易穿盘)
    - 对手战意 (已淘汰/濒临淘汰 → 末段易崩盘)

    修正公式: adjusted = raw × defense_factor × attack_factor × motivation_factor
    """
    if r.xls_cover_rate <= 0:
        return

    raw = r.xls_cover_rate
    factors = []
    notes = []

    # ── 1. 对手防守质量因子 ──
    # 用赔率判断谁是热门方 (赔率低的=热门), 取其对手排名评估防守质量
    try:
        from fifa_rank_db import get_team_info
        home_info = get_team_info(home_cn)
        away_info = get_team_info(away_cn)

        home_rank = home_info.get('rank', 50) if home_info else 50
        away_rank = away_info.get('rank', 50) if away_info else 50

        # 用欧赔判断热门: 赔率低=热门
        home_odds = float(getattr(r, '_home_odds', 2.0))
        away_odds = float(getattr(r, '_away_odds', 2.0))
        if home_odds > 0 and away_odds > 0:
            if home_odds < away_odds:
                opp_rank = away_rank  # 主队热门 → 对手是客队
            else:
                opp_rank = home_rank  # 客队热门 → 对手是主队
        else:
            # 回退: 用共识方向
            if r.xls_consensus_direction == 'bullish':
                opp_rank = away_rank
            elif r.xls_consensus_direction == 'bearish':
                opp_rank = home_rank
            else:
                opp_rank = max(home_rank, away_rank)  # 用排名较差的(防守较弱)

        if opp_rank > 80:
            defense_factor = 1.35
            notes.append(f'对手排名{opp_rank}(>80·防守弱)')
        elif opp_rank > 60:
            defense_factor = 1.20
            notes.append(f'对手排名{opp_rank}(>60)')
        elif opp_rank > 40:
            defense_factor = 1.05
        elif opp_rank <= 15:
            defense_factor = 0.75
            notes.append(f'对手排名{opp_rank}(≤15·防守强)')
        elif opp_rank <= 30:
            defense_factor = 0.85
            notes.append(f'对手排名{opp_rank}(≤30)')
        else:
            defense_factor = 1.0
        factors.append(defense_factor)
    except Exception:
        defense_factor = 1.0

    # ── 2. 热门近期进球效率因子 ──
    # 用赔率判断热门方, 取其近期进球率
    try:
        home_odds = float(getattr(r, '_home_odds', 2.0))
        away_odds = float(getattr(r, '_away_odds', 2.0))
        home_is_favorite = (home_odds > 0 and away_odds > 0 and home_odds < away_odds)

        if home_is_favorite and r.home_recent_form:
            avg_goals = r.home_recent_form.get('avg_goals_scored', 1.5)
        elif not home_is_favorite and r.away_recent_form:
            avg_goals = r.away_recent_form.get('avg_goals_scored', 1.5)
        else:
            avg_goals = 1.5

        if avg_goals >= 3.0:
            attack_factor = 1.30
            notes.append(f'热门场均{avg_goals:.1f}球(≥3.0)')
        elif avg_goals >= 2.5:
            attack_factor = 1.20
            notes.append(f'热门场均{avg_goals:.1f}球(≥2.5)')
        elif avg_goals >= 2.0:
            attack_factor = 1.10
        elif avg_goals < 1.0:
            attack_factor = 0.80
            notes.append(f'热门场均{avg_goals:.1f}球(<1.0·攻击乏力)')
        else:
            attack_factor = 1.0
        factors.append(attack_factor)
    except Exception:
        attack_factor = 1.0

    # ── 3. 对手战意因子 ──
    # 对手已淘汰/濒临淘汰 → 末段容易崩盘 → 穿盘更容易
    try:
        if r.match_motivation:
            home_odds = float(getattr(r, '_home_odds', 2.0))
            away_odds = float(getattr(r, '_away_odds', 2.0))
            home_is_favorite = (home_odds > 0 and away_odds > 0 and home_odds < away_odds)

            if home_is_favorite:
                opp_mot = r.match_motivation.away_motivation
            else:
                opp_mot = r.match_motivation.home_motivation

            if opp_mot.scenario in ('eliminated',):
                motivation_factor = 1.25
                notes.append(f'{opp_mot.team}已淘汰·末段防守松懈')
            elif opp_mot.scenario == 'near_eliminated':
                motivation_factor = 1.15
                notes.append(f'{opp_mot.team}濒临淘汰·可能崩盘')
            elif opp_mot.rotation_risk > 0.3:
                motivation_factor = 1.15
                notes.append(f'{opp_mot.team}可能轮换')
            else:
                motivation_factor = 1.0
            factors.append(motivation_factor)
    except Exception:
        motivation_factor = 1.0

    # ── 4. 🆕 V3.0 盘口变动动量因子 ──
    # 亚盘连续退盘 → 穿盘更难; 连续升盘 → 穿盘更易
    try:
        if r.xls_trend and r.xls_trend.analyzed:
            if r.xls_trend.cover_rate_trend == 'declining':
                momentum_factor = CONF.cover_line_momentum_factor  # 0.90
                notes.append('盘口连续退盘·穿盘更难')
            elif r.xls_trend.cover_rate_trend == 'rising':
                momentum_factor = 1.10
            else:
                momentum_factor = 1.0
            factors.append(momentum_factor)
    except Exception:
        momentum_factor = 1.0

    # ── 5. 🆕 V3.0 场馆因子 ──
    # 室内场馆 → 节奏慢 → 小球 → 更难穿盘
    try:
        if r.venue:
            if r.venue.get('indoor'):
                venue_factor = CONF.cover_venue_factor_indoor  # 0.95
                notes.append('室内场馆·节奏偏慢')
            else:
                venue_factor = 1.0
            factors.append(venue_factor)
    except Exception:
        venue_factor = 1.0

    # ── 6. 🆕 V3.4: 精英攻击力因子 ──
    # 热门拥有多名五大联赛攻击手 → 穿盘更容易
    try:
        from opponent_db import opponent_quality
        home_odds = float(getattr(r, '_home_odds', 2.0))
        away_odds = float(getattr(r, '_away_odds', 2.0))
        home_is_favorite = (home_odds > 0 and away_odds > 0 and home_odds < away_odds)

        fav_team = home_cn if home_is_favorite else away_cn
        fav_data = opponent_quality(fav_team)
        fav_attackers = fav_data.get('top5_attackers', 0)

        if fav_attackers >= 4:
            elite_attack_factor = 1.20
            notes.append(f'{fav_team}精英攻击群({fav_attackers}人)')
        elif fav_attackers >= 3:
            elite_attack_factor = 1.12
            notes.append(f'{fav_team}多名攻击手({fav_attackers}人)')
        elif fav_attackers >= 2:
            elite_attack_factor = 1.06
        else:
            elite_attack_factor = 1.0
        factors.append(elite_attack_factor)
    except Exception:
        elite_attack_factor = 1.0

    # ── 7. 🆕 V3.4: 实力差距因子 ──
    # BIG差距 → 强队更可能穿盘; CLOSE → 更难穿盘
    gap = getattr(r, 'gap_level', 'moderate')
    if gap == 'big':
        gap_cover_factor = 1.10
        notes.append('BIG差距·穿盘更易')
    elif gap == 'moderate':
        gap_cover_factor = 1.05
    elif gap == 'close':
        gap_cover_factor = 0.92
        notes.append('CLOSE差距·穿盘更难')
    else:
        gap_cover_factor = 1.0
    factors.append(gap_cover_factor)

    # ── 8. 🆕 V3.4: 盘口深度因子 ──
    # 小盘口(让<0.5球) → 1-0即穿盘 → 大幅提升穿盘率
    # 大盘口(让>2.0球)  → 需大胜 → 降低穿盘率
    # 数据来源: 亚盘.xls 即时盘口 (非让球指数)
    try:
        from xls_reader_xlrd import read_all_xls
        xls_data = read_all_xls(r.match_name)
        if xls_data:
            asian_data = xls_data.get('asian', {})
            inst_line_str = asian_data.get('summary', {}).get('avg', {}).get('instant_line', '')
            if inst_line_str:
                actual_handicap = abs(float(inst_line_str))
                if actual_handicap < 0.25:
                    depth_factor = 1.50
                    notes.append(f'盘口仅{actual_handicap:.1f}球·平手盘极易穿')
                elif actual_handicap < 0.5:
                    depth_factor = 1.35
                    notes.append(f'盘口{actual_handicap:.1f}球·极易穿盘')
                elif actual_handicap < 0.75:
                    depth_factor = 1.20
                    notes.append(f'盘口{actual_handicap:.1f}球·较易穿盘')
                elif actual_handicap > 2.5:
                    depth_factor = 0.85
                    notes.append(f'盘口{actual_handicap:.1f}球·极难穿盘')
                elif actual_handicap > 2.0:
                    depth_factor = 0.92
                    notes.append(f'盘口{actual_handicap:.1f}球·较难穿盘')
                else:
                    depth_factor = 1.0
                factors.append(depth_factor)

                # 🆕 小盘口强制边缘: 让球<0.75时, 穿盘/不穿盘信号不可靠
                # 回测验证: 3场小盘判定全部错误 (64% vs 88%)
                # 原因: 1-0即穿盘·1-1即不穿·单球决定·纯随机
                if actual_handicap < 0.75 and not getattr(r, '_cover_depth_forced', False):
                    r._cover_depth_forced = True
                    r.v26_warnings.append(
                        f'🎲 小盘口({actual_handicap:.1f}球<0.75)·穿盘信号不可靠·强制边缘'
                    )
    except Exception:
        pass

    # ── 计算调整后穿盘率 ──
    adjusted = raw
    for f in factors:
        adjusted *= f

    # 上限80% (穿盘总有偶然性)
    adjusted = min(80, adjusted)

    if adjusted != raw:
        r.xls_cover_rate_raw = raw  # 保存原始值
        r.xls_cover_rate = round(adjusted, 1)  # 替换为调整后
        note_str = '·'.join(notes) if notes else ''
        r.v26_warnings.append(
            f'📐 穿盘率: {raw:.0f}%→{adjusted:.0f}% ({note_str})' if note_str
            else f'📐 穿盘率: {raw:.0f}%→{adjusted:.0f}%'
        )
    else:
        r.xls_cover_rate_raw = raw


def _apply_v26_rules(r: PreMatchReport):
    """V2.7 规则引擎: 信号矩阵 + 动态置信度 + 比分预测"""
    gap = r.gap_level
    cold = r.betfair_cold
    is_real_hot = r.betfair_is_real_hot
    # 🆕 V3.0 P0#1: CLOSE级别使用更高过热阈值 (25 vs 20)
    if gap == 'close' and not is_real_hot:
        close_threshold = get_overheat_threshold('close')
        if cold >= CONF.overheat_threshold and cold < close_threshold:
            is_real_hot = False  # 确认不触发真过热
            r.v26_warnings.append(f'CLOSE级别·过热阈值提高至{close_threshold}→不触发真过热')
    # 🆕 V3.2→V3.3: BIG级别过热分级 (30=真过热, 20-29=弱过热, <20=无)
    if gap == 'big':
        big_threshold = get_overheat_threshold('big')  # 30
        if is_real_hot and abs(cold) < big_threshold:
            if abs(cold) >= 20:
                # 🆕 V3.3: 冷热20-29 → 弱过热 (保留部分信号, 降低权重)
                is_real_hot = False
                r.big_weak_overheat = True
                r.v26_warnings.append(f'BIG级别·弱过热(冷热{abs(cold):.0f}∈[20,{big_threshold}))→方向信号保留·权重降低')
            else:
                # 冷热<20 → 完全无过热
                is_real_hot = False
                r.v26_warnings.append(f'BIG级别·过热阈值提高至{big_threshold}→冷热{abs(cold):.0f}不足·降级')
    has_bf = r.betfair_cold != 0 or r.betfair_hot_side != ''  # 是否有有效必发数据
    # 🆕 V3.3 P0-2: 必发数据质量评估 (无JSON或fallback→数据不足)
    betfair_weak = not has_bf or getattr(r, '_betfair_from_fallback', True)

    # 提前提取队名 (供交叉验证和东道主检测使用)
    away_team = _extract_away(r.match_name)
    home_team = _extract_home(r.match_name)

    # 🆕 V2.8: 东道主因子检测 (提前至交叉验证之前)
    # 2026世界杯联合主办: 美国、加拿大、墨西哥
    HOST_NATIONS = {'USA': 'co_host', 'Canada': 'co_host', 'Mexico': 'co_host'}
    home_host = HOST_NATIONS.get(home_team, None)
    away_host = HOST_NATIONS.get(away_team, None)
    is_host_match = home_host or away_host

    # 🆕 V3.3 Fix#1: dimension12_books 交叉验证 (庄家盈亏结构分析)
    if has_bf and not betfair_weak and r._bf_raw_odds:
        try:
            from dimension12_books import analyze_books_structure
            bs = analyze_books_structure(
                home_odds=r._bf_raw_odds.get('home', 0) or 2.0,
                draw_odds=r._bf_raw_odds.get('draw', 0) or 3.5,
                away_odds=r._bf_raw_odds.get('away', 0) or 4.0,
                home_volume=r._bf_raw_volumes.get('home', 0),
                draw_volume=r._bf_raw_volumes.get('draw', 0),
                away_volume=r._bf_raw_volumes.get('away', 0),
                home_pnl=r._bf_raw_pnls.get('home', 0),
                draw_pnl=r._bf_raw_pnls.get('draw', 0),
                away_pnl=r._bf_raw_pnls.get('away', 0),
                handicap_direction=r.xls_handicap_direction if hasattr(r, 'xls_handicap_direction') else None,
                strength_gap=gap,
                is_host_nation=is_host_match,
                is_opening_match=(r.match_name and '揭幕' in str(r.match_context) if hasattr(r, 'match_context') else False),
            )
            r.books_structure = {
                'hot_side': bs.hot_side,
                'hot_index': bs.hot_index,
                'is_real_hot': bs.is_real_hot,
                'is_false_hot': bs.is_false_hot,
                'pnl_confidence': bs.pnl_confidence,
                'draw_signal': bs.draw_signal,
                'summary': bs.summary,
            }
            # 交叉验证: 若dimension12与内置判定不一致, 追加警告
            if bs.is_real_hot != is_real_hot and gap != 'extreme':
                r.v26_warnings.append(
                    f'📚 庄家结构交叉验证: dimension12判定{"真过热" if bs.is_real_hot else "假过热"}'
                    f' vs 内置判定{"真过热" if is_real_hot else "假过热"}'
                    f' → {bs.summary[:80]}'
                )
            # 平局信号检测
            if bs.draw_signal:
                r.v26_warnings.append(f'📚 庄家盈亏平局信号: 平局PNL突出→平局概率上升')
        except Exception:
            pass

    # 对手质量检查 (检查热门的对手=弱势方, 而非固定检查客队)
    # (away_team/home_team 已在交叉验证之前提取)
    # 确定弱势方: 热方对面的队伍
    underdog_team = away_team  # 默认
    if r.betfair_hot_side == 'away' and home_team:
        underdog_team = home_team  # 热方=客, 弱势方=主
    elif r.betfair_hot_side == 'home' and away_team:
        underdog_team = away_team  # 热方=主, 弱势方=客
    if underdog_team:
        r.three_conditions = check_three_conditions(underdog_team)
        r.moderate_threat = check_moderate_opponent(underdog_team)

    # 确定共识是否看衰东道主 (用于host discount matrix)
    # (is_host_match/home_host/away_host/HOST_NATIONS 已在交叉验证之前定义)
    if is_host_match:
        host_side = 'home' if home_host else 'away'
        if host_side == 'home':
            host_faded = r.xls_consensus_direction == 'bearish'
            host_backed = r.xls_consensus_direction == 'bullish'
        else:
            host_faded = r.xls_consensus_direction == 'bullish'
            host_backed = r.xls_consensus_direction == 'bearish'
        host_consensus = 'fading_host' if host_faded else ('backing_host' if host_backed else 'back_draw')
        host_gap = getattr(GapLevel, r.gap_level.upper(), None) if r.gap_level else None
        if host_gap:
            host_discount = get_host_discount(
                is_co_host=(home_host == 'co_host' or away_host == 'co_host'),
                gap_level=host_gap,
                consensus_direction=host_consensus,
            )
        else:
            host_discount = {'consensus_mult': 1.0, 'totals_mult': 1.0, 'cover_mult': 1.0}
        # V2.8: 东道主折扣只在我们跟随市场看衰时才降低置信度
        # 如果我们逆市看好东道主 → 这是更强的信号 (历史东道主超常表现)
        host_apply_discount = False
        host_boost = False

    # ── 初始化信号矩阵 ──
    uni_triggered = r.unanimity.get('triggered', False)
    uni_dir = r.unanimity.get('direction', '')
    dc_triggered = r.draw_collapse.get('triggered', False)
    diverge = r.xls_bf_divergence.get('divergence', False)

    r.signal_matrix = {
        'XLS共识': f"{r.xls_consensus_pct:+.1f}%→{r.xls_consensus_direction}",
        '赔率趋势': f"主{r.odds_home_chg:+.1f}% 平{r.odds_draw_chg:+.1f}% 客{r.odds_away_chg:+.1f}%",
        '冷热': f"{cold:+.0f}",
        '全票通过': f"{'⚠️ '+uni_dir if uni_triggered else '否'}",
        '平赔暴跌': f"{'🔴 '+r.draw_collapse.get('severity','') if dc_triggered else '否'}",
        'XLS-必发背离': f"{'⚠️ 是' if diverge else '否'}",
        '共识污染': '是' if r.betfair_pollution else '否',
        '穿盘率': f"{r.xls_cover_rate:.0f}%",
        '三条件': f"{r.three_conditions.get('passed','?')}/3 {r.three_conditions.get('fail_reason','')}" if r.three_conditions else 'N/A',
    }

    # ── 辅助函数: 信号调整置信度 ──
    def apply_signals(base_conf, prediction_type):
        """根据信号矩阵调整置信度"""
        adj = 0
        # 全票通过: 与预测同向→加分, 反向→减分
        if uni_triggered:
            # 🆕 V3.6: CLOSE级别全票通过权重加倍 (共识更可靠)
            boost = int(10 * CONF.close_unanimity_boost) if r.gap_level == 'close' else 10
            if (prediction_type == 'bullish' and uni_dir == 'bullish') or \
               (prediction_type == 'bearish' and uni_dir == 'bearish'):
                adj += boost
                note = f'全票通过强化: {uni_dir}'
                if boost != 10:
                    note += f' (CLOSE×{CONF.close_unanimity_boost})'
                r.v26_warnings.append(note)
            else:
                adj -= boost
                note = f'全票通过反向: {uni_dir} → 诱盘嫌疑'
                if boost != 10:
                    note += f' (CLOSE×{CONF.close_unanimity_boost})'
                r.v26_warnings.append(note)
        # XLS-必发背离: 市场分歧→降级
        if diverge:
            adj -= 15; r.v26_warnings.append('XLS-必发背离: 市场分歧→置信度降级')
        # 平赔暴跌: 平局风险上升
        if dc_triggered:
            adj += 5; r.v26_warnings.append(f'平赔暴跌: {r.draw_collapse.get("avg_change",0):.1f}% → 平局预警')
        # 共识污染: 必发不可信
        if r.betfair_pollution:
            adj -= 10; r.v26_warnings.append('共识污染: 必发信号可靠性下降')
        # 大单卖出: 反向信号 (V3.6: 分级·config联动)
        if r.betfair_big_sell:
            vol = r.betfair_big_sell_volume
            cnt = r.betfair_big_sell_count
            max_penalty = int(CONF.big_sell_warning * 100)  # 0.15 → 15
            # 四级: 按总金额分级, 封顶max_penalty
            if vol >= 2_000_000 or cnt >= 8:
                penalty = max_penalty; tier = 'IV (巨额)'
            elif vol >= 500_000 or cnt >= 5:
                penalty = int(max_penalty * 0.67); tier = 'III (大额)'
            elif vol >= 200_000 or cnt >= 3:
                penalty = int(max_penalty * 0.47); tier = 'II (中额)'
            else:
                penalty = int(max_penalty * 0.27); tier = 'I (小额)'
            adj -= penalty
            r.v26_warnings.append(f'🔴 大额卖单({tier}): {cnt}笔·共{vol:,.0f} → 置信度-{penalty}')
        # 🆕 V3.4: 冷热晚期飙升惩罚 (回测: 0→40+ 三场全错)
        if r._late_surge:
            surge_penalty = 12
            adj -= surge_penalty
            r.v26_warnings.append(
                f'🌊 冷热晚期飙升(早期{r._late_surge_early:.0f}→晚期{r._late_surge_late:.0f})·临场热钱反向指标→置信度-{surge_penalty}')
        return max(5, min(95, base_conf + adj))

    # ── V3.0 乘法调整链 (P1#5: 加法→乘法·防触顶) ──
    def apply_v29_adjustments(base_conf):
        """V3.0乘法链: 各因子相乘而非相加, 防止10因子叠加触顶"""
        multiplier = 1.0

        # 1. 天气影响 (±4%) → ×(0.96~1.04)
        if r.weather_impact and r.weather_impact.score != 0:
            multiplier *= (1.0 + r.weather_impact.score * 0.008)
            for w in r.weather_impact.warnings[:2]:
                if '理想' not in w:
                    r.v26_warnings.append(f'🌡️ {w}')

        # 2. 战意差 (±10%, V2.13增强) → ×(0.90~1.10)
        if r.match_motivation:
            mot = r.match_motivation
            hm = mot.home_motivation
            am = mot.away_motivation
            if mot.confidence_adjustment != 0:
                multiplier *= (1.0 + mot.confidence_adjustment / 100)
                if abs(mot.differential) >= 3:
                    r.v26_warnings.append(
                        f'⚔️ 战意差{mot.differential:+.0f}/10: '
                        f'{hm.team}({hm.motivation_score:.0f}) vs {am.team}({am.motivation_score:.0f}) → {mot.prediction_bias}'
                    )
            rot_risk = max(hm.rotation_risk, am.rotation_risk)
            if rot_risk > 0.3:
                multiplier *= 0.95
                risk_team = hm.team if hm.rotation_risk > 0.3 else am.team
                r.v26_warnings.append(f'🔄 {risk_team}可能轮换→×0.95')
            if mot.tournament_note and '淘汰赛路径' in mot.tournament_note:
                r.v26_warnings.append(f'🔀 淘汰赛路径有更优选择→战意可能受影响')

        # 3. 首发阵容 (仅-15~0%) → ×(0.85~1.00)
        if r.lineup_impact and r.lineup_impact.confidence_adj != 0:
            multiplier *= (1.0 + r.lineup_impact.confidence_adj / 100)
            for a in r.lineup_impact.home_adjustments + r.lineup_impact.away_adjustments:
                r.v26_warnings.append(f'👥 {a}')

        # 4. 战术优势 (±5%) → ×(0.95~1.05)
        if r.tactical_edge != 0:
            multiplier *= (1.0 + r.tactical_edge * 0.005)
            if abs(r.tactical_edge) >= 4:
                r.v26_warnings.append(
                    f'🎯 战术克制: {r.tactical_edge:+.0f}/10 '
                    f'({r.style_clash_note[:40] if r.style_clash_note else ""})'
                )

        # 5. 教练差距 (±3%) → ×(0.97~1.03)
        if r.coach_impact != 0:
            multiplier *= (1.0 + r.coach_impact / 100)
            if abs(r.coach_impact) >= 2:
                r.v26_warnings.append(f'📋 教练经验差距: ×{1+r.coach_impact/100:.2f}')

        # 6. 比赛时间影响 (±3%) → ×(0.97~1.03)
        if r.time_impact and r.time_impact.overall_adjustment != 0:
            multiplier *= (1.0 + r.time_impact.overall_adjustment / 100)
            for rec in r.time_impact.recommendations[:1]:
                r.v26_warnings.append(f'🕐 {rec}')

        # 7. 🆕 V2.10 近期状态差距 (±6%) → ×(0.94~1.06)
        if r.form_diff and r.form_diff.get('confidence_adj', 0) != 0:
            multiplier *= (1.0 + r.form_diff['confidence_adj'] / 100)
            if abs(r.form_diff.get('confidence_adj', 0)) >= 3:
                note_text = r.form_diff.get('note', '')
                r.v26_warnings.append(f'📈 {note_text}')

        # 8. 🆕 V2.10 历史恩怨 (-3% to +2%) → ×(0.97~1.02)
        if r.h2h_result and r.h2h_result.get('confidence_adj', 0) != 0:
            multiplier *= (1.0 + r.h2h_result['confidence_adj'] / 100)
            for note in r.h2h_result.get('notes', [])[:2]:
                if '上次' not in note:
                    r.v26_warnings.append(f'⚔️ {note[:60]}')

        # 9. 🆕 V2.10 裁判因素 (-2% to +1%) → ×(0.98~1.01)
        if r.referee_result and r.referee_result.get('confidence_adj', 0) != 0:
            multiplier *= (1.0 + r.referee_result['confidence_adj'] / 100)
            notes = r.referee_result.get('notes', [])
            if notes:
                r.v26_warnings.append(f'🟨 {notes[0][:60]}')

        # 10. 🆕 V2.11 市场心理周期 (0~-10%) → ×(1.00~0.90)
        cold_streak = get_cold_streak_factor()
        r.market_psychology = cold_streak
        if cold_streak['cold_chasing']:
            multiplier *= (1.0 + cold_streak['confidence_adj'] / 100)
            r.v26_warnings.append(cold_streak['discount_note'])

        # 11. 🆕 V2.15 XLS跨版本历史趋势 (-5% to +5%) → ×(0.95~1.05)
        if r.xls_trend and r.xls_trend.analyzed and r.xls_trend.confidence_adjustment != 0:
            multiplier *= (1.0 + r.xls_trend.confidence_adjustment / 100)
            for sig in r.xls_trend.signals:
                r.v26_warnings.append(f'📊 {sig}')

        # 12. 🆕 V3.0 替补深度 (-5% to +5%) → ×(0.95~1.05)
        if analyze_sub_depth and r.team_group_home:
            try:
                sub = analyze_sub_depth(home_team, away_team,
                    r.match_motivation.home_motivation.rotation_risk if r.match_motivation else 0,
                    r.match_motivation.away_motivation.rotation_risk if r.match_motivation else 0)
                if sub.confidence_adj != 0:
                    multiplier *= (1.0 + sub.confidence_adj / 100)
                    for n in sub.notes[:2]:
                        r.v26_warnings.append(f'🔄 {n}')
            except Exception:
                pass

        # 13. 🆕 V3.0 定位球量化 (-3% to +3%) → ×(0.97~1.03)
        if analyze_setpiece:
            try:
                sp = analyze_setpiece(home_team, away_team, r.weather.condition if r.weather else 'clear')
                if sp.confidence_adj != 0:
                    multiplier *= (1.0 + sp.confidence_adj / 100)
                    for n in sp.notes[:1]:
                        r.v26_warnings.append(f'🎯 {n}')
            except Exception:
                pass

        # 14. 🆕 V3.0 超巨里程碑 (0% to +10%) → ×(1.00~1.10)
        if detect_milestones:
            try:
                hm_ms = detect_milestones(home_team, r.match_name)
                am_ms = detect_milestones(away_team, r.match_name)
                ms_boost = hm_ms.get('boost', 0) - am_ms.get('boost', 0)
                if ms_boost != 0:
                    multiplier *= (1.0 + ms_boost / 100)
                    for p in hm_ms.get('players', []) + am_ms.get('players', []):
                        r.v26_warnings.append(f'⭐ {p}')
            except Exception:
                pass

        # 15. 🆕 V3.4 伤病影响 (来自opponent_db·检查关键球员缺阵)
        try:
            from opponent_db import opponent_quality
            home_inj = opponent_quality(home_team)
            away_inj = opponent_quality(away_team)
            injury_adj = 0
            injury_notes = []
            for team_name, data, is_hot in [(home_team, home_inj, r.betfair_hot_side == 'home'),
                                             (away_team, away_inj, r.betfair_hot_side == 'away')]:
                for p in data.get('players', []):
                    inj = p.get('injury', '')
                    if not inj: continue
                    pos = p.get('pos', '')
                    # 后卫/GK缺阵 → 防线削弱 → 对手更易进球 → 热门胜概率提升
                    if pos in ('CB', 'RB', 'LB', 'GK', 'DF'):
                        if is_hot:
                            injury_adj -= 4  # 热方防线削弱 → 热门不胜风险↑
                            injury_notes.append(f'{team_name}防线{p['name']}({pos})缺阵: {inj}')
                        else:
                            injury_adj += 4  # 弱方防线削弱 → 热门更易胜
                            injury_notes.append(f'{team_name}防线{p['name']}({pos})缺阵→热门利好: {inj}')
                    # FW缺阵 → 进攻削弱
                    elif pos in ('FW', 'ST', 'CF', 'LW', 'RW', 'WG'):
                        if is_hot:
                            injury_adj -= 3  # 热方进攻削弱
                            injury_notes.append(f'{team_name}射手{p['name']}({pos})缺阵: {inj}')
                        else:
                            injury_adj += 3  # 弱方进攻削弱
                            injury_notes.append(f'{team_name}射手{p['name']}({pos})缺阵: {inj}')
            if injury_adj != 0:
                # 转置信度: 每adj点≈1.5% (限制±15%)
                injury_adj = max(-15, min(15, injury_adj * 1.5))
                multiplier *= (1.0 + injury_adj / 100)
                for n in injury_notes[:3]:
                    r.v26_warnings.append(f'🏥 {n}')
        except Exception:
            pass

        # 16. 🆕 V3.2→V3.3 中场实力对比 (CLOSE±5%·MOD±3%·BIG±1.5%)
        if gap in ('close', 'moderate', 'big'):
            try:
                from midfield_quality import compare_midfield
                h_cn = r.match_name.split('VS')[0].strip()
                a_cn = r.match_name.split('VS')[-1].strip() if 'VS' in r.match_name else ''
                mf = compare_midfield(h_cn, a_cn)
                r.midfield_comparison = mf
                if mf['confidence_adj'] != 0:
                    # 🆕 V3.3: 按差距级别分级权重
                    if gap == 'close':
                        weight = 1.0    # CLOSE: 中场差距可定胜负
                    elif gap == 'moderate':
                        weight = 0.5    # MOD: 中场影响减半
                    else:
                        weight = 0.25   # BIG: 实力碾压为主·中场为辅
                    adj = mf['confidence_adj'] * weight
                    multiplier *= (1.0 + adj / 100)
                    hmr = mf['home_rating']
                    amr = mf['away_rating']
                    mf_note = mf['note']
                    level_tag = {'close': '[CLOSE]', 'moderate': '[MOD]', 'big': '[BIG]'}.get(gap, '')
                    r.v26_warnings.append(
                        f'🎮 中场{level_tag}: {h_cn}({hmr:.1f}) vs {a_cn}({amr:.1f}) → {mf_note} '
                        f'(权重×{weight:.0%}→调整{adj:+.1f}%)'
                    )
            except Exception:
                pass

        # 16b. 🆕 V3.3 Fix#1: dimension12 庄家盈亏结构 → ×(0.92~1.03)
        if r.books_structure:
            try:
                pnl_conf = r.books_structure.get('pnl_confidence', 0)
                if pnl_conf > 0:
                    # 盈亏结构清晰→小幅增强信心; 盈亏结构混乱→小幅减弱
                    pnl_factor = 1.0 + (pnl_conf - 0.5) * 0.06  # ±3%
                    multiplier *= pnl_factor
                if r.books_structure.get('draw_signal'):
                    multiplier *= 0.97  # 平局信号→增加不确定性
            except Exception:
                pass

        # 17. 🆕 V3.3 P2-8: 淘汰赛特殊规则 (平局倾向+15%·进球衰减15%)
        try:
            from knockout_motivation import calculate_knockout_motivation
            ko = calculate_knockout_motivation(r.match_name)
            if ko['is_knockout']:
                multiplier *= 0.95  # 淘汰赛不确定性增加→置信度-5%
                for note in ko['notes']:
                    r.v26_warnings.append(note)
        except Exception:
            pass

        # 18. 🆕 V3.3 P2-9: 纪律风险 (红黄牌风险→增加不确定性)
        try:
            from discipline_risk import analyze_discipline_risk
            dr = analyze_discipline_risk(r.match_name, home_team, away_team)
            if dr.confidence_adj != 0:
                multiplier *= (1.0 + dr.confidence_adj / 100)
                for note in dr.notes[:2]:
                    r.v26_warnings.append(note)
        except Exception:
            pass

        # V3.0 乘法链最终输出
        result = base_conf * multiplier
        return max(int(CONF.confidence_floor), min(int(CONF.confidence_ceiling), int(result)))

    # ── 比分预测 (V2.8: 集成gap_level) ──
    def predict_score(is_home_strong, cover_rate, totals_line, gap_level='moderate'):
        """基于穿盘率+大小球+实力差距预测比分"""
        if not totals_line:
            totals_line = 2.5
        goals = round(totals_line)
        # 基础margin
        if cover_rate < 30:
            margin = 1
        elif cover_rate < 50:
            margin = 1 if goals <= 2 else 2
        else:
            margin = 2 if goals >= 3 else 1
        # 🆕 V2.8: gap_level调节margin
        if gap_level == 'extreme':
            margin += 2
        elif gap_level == 'big':
            margin += 1
        elif gap_level == 'close':
            margin = max(1, margin - 1)  # CLOSE比赛差距小
        if is_home_strong:
            if margin >= 3:
                return f'{margin}-0 / {margin+1}-0'
            return f'{margin}-0 / {margin+1}-0' if goals <= 2 else f'{margin+1}-0 / {margin+1}-1'
        else:
            if margin >= 3:
                return f'0-{margin} / 1-{margin+1}'
            return f'0-{margin} / 1-{margin+1}' if goals <= 2 else f'1-{margin} / 1-{margin+1}'

    # ══════════════════════════════════════════
    #  V2.7 核心规则
    # ══════════════════════════════════════════

    # ── 无必发数据降级 ──
    if not has_bf:
        if gap in ('extreme', 'big'):
            r.v26_rule = f'{gap.upper()} + 无必发 → 跳过预测'
            r.v26_prediction = '⚠️ 不预测 (缺少必发数据)'
            r.v26_confidence = 0
            r.v26_warnings.append('无必发数据: BIG/EXTREME风险过高·强制跳过')
            _build_structured(r); return
        else:
            r.v26_warnings.append('无必发数据: 置信度-15%')

    # ── EXTREME ──
    if gap == 'extreme':
        r.v26_rule = 'EXTREME → 强制回避·不预测'
        r.v26_prediction = '⚠️ 不预测 (EXTREME: 0-0↔7-1随机)'
        r.v26_confidence = 0
        r.v26_warnings.append('EXTREME gap: 所有信号降权至0%·结果完全随机')
        _predict_totals(r); _build_structured(r); return

    # 🆕 V3.2: 大小球预测 (所有非EXTREME比赛)
    _predict_totals(r)

    # ── CLOSE ──
    if gap == 'close':
        if is_real_hot:
            # 🆕 V3.3 P1-4: CLOSE精英例外 — 顶级强队温和过热→实力碾压
            if r.hot_team_fifa_rank <= CONF.close_elite_rank_threshold and abs(cold) < CONF.close_elite_cold_max:
                r.v26_rule = 'CLOSE + 真过热 + 精英队 → 实力碾压(精英例外)'
                r.v26_prediction = '热门胜 (实力碾压·精英例外)'
                base_conf = 70
                r.v26_warnings.append(
                    f'精英队(FIFA#{r.hot_team_fifa_rank}≤{CONF.close_elite_rank_threshold})·'
                    f'温和过热(|cold|={abs(cold):.0f}<{CONF.close_elite_cold_max:.0f})→'
                    f'CLOSE精英例外·实力碾压覆盖'
                )
            else:
                r.v26_rule = 'CLOSE + 真过热 → 热门不胜'
                r.v26_prediction = '⚠️ 热门不胜'
                base_conf = 85
            r.score_prediction = predict_score_from_report(r)
            r.v26_score_predictions = [format_score_output_compact(r.score_prediction)]
        else:
            r.v26_rule = 'CLOSE: 按共识方向预测'
            is_home = r.xls_consensus_direction == 'bullish'
            r.v26_prediction = '主胜' if is_home else ('客胜' if r.xls_consensus_direction == 'bearish' else '平局倾向')
            base_conf = 75
            # 🆕 V3.3 P1-5: CLOSE无过热也生成比分预测
            r.score_prediction = predict_score_from_report(r)
            r.v26_score_predictions = [format_score_output_compact(r.score_prediction)]
        # V2.8: 东道主因子调整置信度
        # 关键: 判断模型预测是否看衰东道主
        if is_host_match and host_side == 'home' and host_faded:
            host_mult = host_discount.get('consensus_mult', 1.0)
            # 判断模型预测方向: 看衰东道主(预测主队不胜/客胜) vs 看好东道主(预测主胜)
            pred_fades_host = ('热门不胜' in r.v26_prediction or '客胜' in r.v26_prediction or '主场不胜' in r.v26_prediction)
            pred_backs_host = ('热门胜' in r.v26_prediction or '主胜' in r.v26_prediction or '热门仍赢' in r.v26_prediction)
            if pred_fades_host:
                # 模型跟随市场看衰东道主 → 历史东道主常超预期，降置信度
                base_conf = int(base_conf * host_mult)
                r.v26_warnings.append(f'🏠 东道主看衰折扣: 市场+模型一致看衰·但东道主常超预期·置信度×{host_mult:.0%}')
            elif pred_backs_host:
                # 模型逆市看好东道主 → 东道主溢价强化信号
                boost = 1.0 + (1.0 - host_mult) * 0.5  # half the discount as boost
                base_conf = min(95, int(base_conf * boost))
                r.v26_warnings.append(f'🏠 东道主逆市信号: 市场看衰但模型看好→东道主溢价+{int((boost-1)*100)}%')
        base_conf = apply_v29_adjustments(base_conf)
        raw_conf = apply_signals(base_conf, r.xls_consensus_direction)
        r.v26_confidence, cal_note = calibrate_confidence(raw_conf)
        if '📐' in cal_note:
            r.v26_warnings.append(cal_note)
        # 🆕 V3.3 P0-1: 高置信度预警 (>80%历史准确率仅20%)
        if r.v26_confidence > 80:
            r.v26_warnings.append('🔴 高置信度预警(>80%): 请仔细复核所有信号维度·历史高置信度准确率仅20%')
        # 🆕 V3.3 P0-2: 无必发数据置信度限制
        if betfair_weak and r.v26_confidence > CONF.no_betfair_confidence_cap:
            r.v26_confidence = int(CONF.no_betfair_confidence_cap)
            r.v26_warnings.append('⚠️ 无必发数据·置信度受限(上限65%)')
        _build_structured(r); return

    # ── MODERATE ──
    if gap == 'moderate':
        # 🆕 V3.2: 顶级强队 + 温和过热 → 实力碾压 (市场理性定价)
        if is_real_hot and r.hot_team_fifa_rank <= CONF.elite_team_max_rank and abs(cold) < CONF.elite_moderate_cold_max:
            r.v26_rule = 'MOD + 真过热 + 顶级强队 → 实力碾压'
            r.v26_prediction = '热门胜 (实力碾压)'
            base_conf = 70
            r.v26_warnings.append(f'顶级强队(FIFA#{r.hot_team_fifa_rank})·温和过热(|cold|={abs(cold):.0f}<{CONF.elite_moderate_cold_max:.0f})→实力碾压覆盖')
        elif is_real_hot and r.moderate_threat:
            if r.moderate_threat.get('has_goal_threat'):
                r.v26_rule = 'MOD + 真过热 + 顶级攻击手 → 热门不胜'
                r.v26_prediction = '⚠️ 热门不胜'
                base_conf = 75
                r.v26_warnings.append(f"对手: {', '.join(r.moderate_threat.get('top_players', []))}")
            else:
                r.v26_rule = 'MOD + 真过热 + 无进攻威胁 → 热门仍赢'
                r.v26_prediction = '热门胜'
                base_conf = 65
                # 穿盘率判断
                if r.xls_cover_rate > 0 and r.xls_cover_rate < 30:  # V3.4: 35→30
                    r.v26_prediction += '·不穿盘'
                    r.v26_warnings.append(f'穿盘率仅{r.xls_cover_rate:.0f}% → 大概率不穿盘')
                elif r.xls_cover_rate >= 50:
                    r.v26_prediction += '·可能穿盘'
        elif is_real_hot:
            r.v26_rule = 'MOD + 真过热 (无威胁数据) → 偏向热门不胜'
            r.v26_prediction = '⚠️ 热门不胜'
            base_conf = 70
        else:
            r.v26_rule = 'MOD: 按共识方向'
            r.v26_prediction = '热门胜' if r.xls_consensus_direction in ('bullish', 'neutral') else '客胜倾向'
            base_conf = 70
        # V2.8: 东道主因子调整置信度
        if is_host_match and host_side == 'home' and host_faded:
            host_mult = host_discount.get('consensus_mult', 1.0)
            pred_fades_host = ('热门不胜' in r.v26_prediction or '客胜' in r.v26_prediction)
            pred_backs_host = ('热门胜' in r.v26_prediction or '主胜' in r.v26_prediction or '热门仍赢' in r.v26_prediction)
            if pred_fades_host:
                base_conf = int(base_conf * host_mult)
                r.v26_warnings.append(f'🏠 东道主看衰折扣: 市场+模型一致看衰·置信度×{host_mult:.0%}')
            elif pred_backs_host:
                boost = 1.0 + (1.0 - host_mult) * 0.5
                base_conf = min(95, int(base_conf * boost))
                r.v26_warnings.append(f'🏠 东道主逆市信号: 市场看衰但模型看好→东道主溢价+{int((boost-1)*100)}%')
        base_conf = apply_v29_adjustments(base_conf)
        raw_conf = apply_signals(base_conf, r.xls_consensus_direction)
        r.v26_confidence, cal_note = calibrate_confidence(raw_conf)
        if '📐' in cal_note:
            r.v26_warnings.append(cal_note)
        # 🆕 V3.3 P0-1: 高置信度预警 (>80%历史准确率仅20%)
        if r.v26_confidence > 80:
            r.v26_warnings.append('🔴 高置信度预警(>80%): 请仔细复核所有信号维度·历史高置信度准确率仅20%')
        # 🆕 V3.3 P0-2: 无必发数据置信度限制
        if betfair_weak and r.v26_confidence > CONF.no_betfair_confidence_cap:
            r.v26_confidence = int(CONF.no_betfair_confidence_cap)
            r.v26_warnings.append('⚠️ 无必发数据·置信度受限(上限65%)')
        r.score_prediction = predict_score_from_report(r)
        r.v26_score_predictions = [format_score_output_compact(r.score_prediction)]
        _build_structured(r); return

    # ── BIG ──
    if gap == 'big':
        hot_side = r.betfair_hot_side
        rank_gap = r.fifa_rank_gap

        if is_real_hot:
            # 🆕 V3.2: 顶级强队 + 温和过热 → 实力碾压 (市场理性定价)
            if r.hot_team_fifa_rank <= CONF.elite_team_max_rank and abs(cold) < CONF.elite_moderate_cold_max:
                r.v26_rule = 'BIG + 真过热 + 顶级强队 → 实力碾压'
                r.v26_prediction = '热门胜 (实力碾压)'
                base_conf = 70
                r.v26_warnings.append(f'顶级强队(FIFA#{r.hot_team_fifa_rank})·温和过热(|cold|={abs(cold):.0f}<{CONF.elite_moderate_cold_max:.0f})→实力碾压覆盖')
            elif r.three_conditions and r.three_conditions.get('all_pass'):
                # 🆕 V3.3: 非精英热队+三条件全过 → 降级 (伊朗36>35降级·墨西哥15/苏格兰35保留)
                if r.hot_team_fifa_rank > 35:
                    r.v26_rule = 'BIG + 真过热 + 三条件全满足 + 热队非精英 → 降级'
                    r.v26_prediction = '⚠️ 热门可能不胜 (三条件全过但热队非精英)'
                    base_conf = 55
                    r.v26_warnings.append(
                        f'三条件全满足但热方FIFA#{r.hot_team_fifa_rank}>35非精英→降级为\"热门可能不胜\"'
                    )
                else:
                    r.v26_rule = 'BIG + 真过热 → 三条件全满足·热门仍赢'
                    r.v26_prediction = '热门仍赢 (三条件全满足)'
                    base_conf = 65
                    r.v26_warnings.append('三条件全满足: 唯一例外')
            else:
                r.v26_rule = 'BIG + 真过热 → 默认热门不胜'
                r.v26_prediction = '⚠️ 热门不胜'
                base_conf = 70
                # 🆕 V3.2: BIG客队热时置信度折扣 (客队往往是真正强队)
                if hot_side == 'away':
                    base_conf -= CONF.big_away_hot_conf_discount
                    r.v26_warnings.append(f'⚠️ 客队为真正强队(排名差{rank_gap})·热门不胜信号可靠性下降(-{CONF.big_away_hot_conf_discount}%)')
                if r.three_conditions:
                    r.v26_warnings.append(f"三条件缺{3-r.three_conditions.get('passed',0)}: {r.three_conditions.get('fail_reason','')}")
        elif r.big_weak_overheat:
            # 🆕 V3.3: BIG弱过热 (冷热20-29) → 方向信号保留·权重降低
            cond_pass = r.three_conditions.get('passed', 0) if r.three_conditions else 0
            if cond_pass >= 3:
                r.v26_rule = 'BIG + 弱过热 → 三条件全满足·热门仍赢倾向'
                r.v26_prediction = '热门仍赢·弱信号 (三条件全满足)'
                base_conf = 55
                r.v26_warnings.append('⚠️ 弱过热: 信号保留但权重降低·三条件全满足·倾向热门')
            else:
                r.v26_rule = 'BIG + 弱过热 → 热门不胜倾向'
                r.v26_prediction = '⚠️ 热门不胜·弱信号'
                base_conf = 50
                r.v26_warnings.append('⚠️ 弱过热: 信号保留但权重降低·三条件不足·倾向冷门')
                if r.three_conditions:
                    r.v26_warnings.append(f"三条件缺{3-cond_pass}: {r.three_conditions.get('fail_reason','')}")
        else:
            r.v26_rule = 'BIG + 无过热 → 模糊·需额外信号'
            # 🆕 V3.2: 客队热+排名差距大→客队实力碾压
            if hot_side == 'away' and rank_gap >= CONF.big_no_overheat_rank_gap:
                r.v26_prediction = '客胜倾向 (实力优势)'
                base_conf = 60
                r.v26_warnings.append(f'客队实力优势·排名差{rank_gap}≥{CONF.big_no_overheat_rank_gap}')
            elif uni_triggered and uni_dir == 'bullish':
                r.v26_prediction = '热门胜 (全票看好)'
                base_conf = 65
            elif r.xls_consensus_direction == 'bearish' and abs(r.xls_consensus_pct) > 50:
                r.v26_prediction = '⚠️ 热门可能不胜 (XLS强力看衰)'
                base_conf = 55
            else:
                r.v26_prediction = '信号不足·偏向热门'
                base_conf = 55
        # V2.8: 东道主因子调整置信度 (BIG级别)
        if is_host_match and host_side == 'home' and host_faded:
            host_mult = host_discount.get('consensus_mult', 1.0)
            pred_fades_host = ('热门不胜' in r.v26_prediction or '客胜' in r.v26_prediction)
            pred_backs_host = ('热门胜' in r.v26_prediction or '主胜' in r.v26_prediction or '热门仍赢' in r.v26_prediction)
            if pred_fades_host:
                base_conf = int(base_conf * host_mult)
                r.v26_warnings.append(f'🏠 东道主看衰折扣(BIG): 置信度×{host_mult:.0%}')
            elif pred_backs_host:
                boost = 1.0 + (1.0 - host_mult) * 0.6
                base_conf = min(95, int(base_conf * boost))
                r.v26_warnings.append(f'🏠 东道主逆市信号(BIG): 严重看衰·东道主溢价+{int((boost-1)*100)}%')
        base_conf = apply_v29_adjustments(base_conf)
        raw_conf = apply_signals(base_conf, r.xls_consensus_direction)
        r.v26_confidence, cal_note = calibrate_confidence(raw_conf)
        if '📐' in cal_note:
            r.v26_warnings.append(cal_note)
        # 🆕 V3.3 P0-1: 高置信度预警 (>80%历史准确率仅20%)
        if r.v26_confidence > 80:
            r.v26_warnings.append('🔴 高置信度预警(>80%): 请仔细复核所有信号维度·历史高置信度准确率仅20%')
        # 🆕 V3.3 P0-2: 无必发数据置信度限制
        if betfair_weak and r.v26_confidence > CONF.no_betfair_confidence_cap:
            r.v26_confidence = int(CONF.no_betfair_confidence_cap)
            r.v26_warnings.append('⚠️ 无必发数据·置信度受限(上限65%)')
        r.score_prediction = predict_score_from_report(r)
        r.v26_score_predictions = [format_score_output_compact(r.score_prediction)]
        _build_structured(r); return

    r.v26_rule = '无法判定'
    r.v26_confidence = 40

    # 🆕 V3.0 结构化输出 (P0#3 + P3#16)
    _build_structured(r)


def _predict_totals(r: PreMatchReport):
    """
    V3.4 大小球优化预测 (MD2复盘: 新增大球方向3项防护)

    基础信号: XLS大小球盘口趋势 (升盘→大球, 降盘→小球)
    修正因子 (双向对称):
      1. 双方进攻火力: 两队都有射手+场均≥1.5球 → 小球风险-15 / 大球支撑+10
      2. 精英队火力: 热方rank≤5 → 小球风险-10
      3. 热方进攻力: 热方场均≥2.0球 → 小球风险-10 / 大球支撑+8
      4. 弱势方爆冷基因: 巨人杀手 → 小球风险-10
      5. 低盘口风险: 开盘<2.0 → 小球风险-15
      6. 东道主加成: → 小球风险-5
      🆕 7. 双方进攻疲软: 两队场均<1.3 → 大球风险-10
      🆕 8. BIG差距+弱队死守: 弱队场均<1.0 → 大球风险-7
      🆕 9. 低盘口升盘不可靠: 盘口<2.5+升盘 → 大球风险-7
    翻转阈值: conf_delta ≤ -20
    """
    from opponent_db import opponent_quality

    trend = getattr(r, 'xls_totals', 'stable')
    line = getattr(r, '_totals_line', 2.5) or 2.5
    gap = r.gap_level
    cold = abs(r.betfair_cold)

    # EXTREME强制中立
    if gap == 'extreme':
        r._totals_prediction = {
            'direction': 'neutral', 'confidence': 0, 'line': line, 'trend': trend,
            'adjustments': ['EXTREME差距·大小球完全随机·不预测'],
            'flipped': False, 'flip_note': '', 'both_dangerous': False,
        }
        return

    # 基础预测
    if trend == 'up':
        base_dir = 'over'; base_conf = 65
    elif trend == 'down':
        base_dir = 'under'; base_conf = 60
    else:
        base_dir = 'neutral'; base_conf = 50

    adjustments = []
    conf_delta = 0
    both_dangerous = False

    # 获取两队数据
    home_cn = r.match_name.split('VS')[0].strip()
    away_cn = r.match_name.split('VS')[-1].strip() if 'VS' in r.match_name else ''
    home_data = opponent_quality(home_cn)
    away_data = opponent_quality(away_cn)

    # 确定热方/弱势方数据
    if r.betfair_hot_side == 'home':
        hot_data, underdog_data = home_data, away_data
    else:
        hot_data, underdog_data = away_data, home_data

    hot_goals = hot_data.get('pre_goals_per_game', 1.0)
    underdog_gk = underdog_data.get('giant_killings', [])

    # ── 修正1: 双方进攻火力 ──
    home_attack = len(home_data.get('top5_players', [])) > 0 and home_data.get('pre_goals_per_game', 0) >= 1.5
    away_attack = len(away_data.get('top5_players', [])) > 0 and away_data.get('pre_goals_per_game', 0) >= 1.5

    if home_attack and away_attack:
        both_dangerous = True
        if base_dir == 'under':
            conf_delta -= 15
            adjustments.append('双方均有进攻火力→小球风险')
        elif base_dir == 'over':
            conf_delta += 8
            adjustments.append('双方均有进攻火力→大球支撑')

    # ── 修正2: 精英队火力 ──
    if r.hot_team_fifa_rank <= 5 and cold < 50:
        if base_dir == 'under':
            conf_delta -= 10
            adjustments.append(f'精英队(FIFA#{r.hot_team_fifa_rank})火力强劲→小球风险')

    # ── 修正3: 热方进攻力 ──
    if hot_goals >= 2.0:
        if base_dir == 'under':
            conf_delta -= 10
            adjustments.append(f'热方场均{hot_goals:.1f}球(≥2.0)→大球倾向')
        elif base_dir == 'over':
            conf_delta += 5
            adjustments.append(f'热方场均{hot_goals:.1f}球(≥2.0)→大球支撑')

    # ── 修正4: 弱势方爆冷基因 ──
    if len(underdog_gk) > 0 and base_dir == 'under':
        conf_delta -= 10
        adjustments.append(f'弱势方巨人杀手血统→双方进球风险')

    # ── 修正5: 低盘口风险 ──
    if line < 2.0 and base_dir == 'under':
        conf_delta -= 15
        adjustments.append(f'开盘{line:.1f}球过低→易被击穿')

    # ── 修正6: 东道主加成 ──
    host_side = 'home' if home_cn in ('加拿大', '美国', '墨西哥') else None
    if host_side and base_dir == 'under':
        conf_delta -= 5
        adjustments.append('东道主比赛→倾向大球')

    # 🆕 V3.4: 大球方向对称防护 (MD2捷克1-1复盘)
    home_gpg = home_data.get('pre_goals_per_game', 1.0) or 1.0
    away_gpg = away_data.get('pre_goals_per_game', 1.0) or 1.0
    underdog_gpg = underdog_data.get('pre_goals_per_game', 1.0) or 1.0

    # ── 修正7: 双方进攻疲软 → 大球风险 ──
    # 用两队合计 vs 盘口判断: 总进球预期不足盘口→大球不可靠
    combined_gpg = home_gpg + away_gpg
    if base_dir == 'over' and combined_gpg < line:
        conf_delta -= 10
        adjustments.append(f'双方进攻疲软(合计{combined_gpg:.1f}球<盘口{line:.1f})→大球风险')

    # ── 修正8: BIG差距+弱队死守 → 大球风险 ──
    if base_dir == 'over' and gap == 'big' and underdog_gpg < 1.0:
        conf_delta -= 7
        adjustments.append(f'BIG差距+弱队场均仅{underdog_gpg:.1f}球→大巴战术·大球风险')

    # ── 修正9: 低盘口升盘信号不可靠 → 大球风险 ──
    if base_dir == 'over' and line < 2.5:
        conf_delta -= 7
        adjustments.append(f'低盘口({line:.1f}<2.5)升盘信号弱→大球风险')

    # 计算最终
    final_conf = max(25, min(90, base_conf + conf_delta))

    # 方向翻转检测: conf_delta ≤ -20
    if base_dir == 'under' and conf_delta <= -20:
        final_dir = 'over'; flip_note = '⚠️ 降盘信号被多项因子削弱·翻转预测大球'
    elif base_dir == 'over' and conf_delta <= -20:
        final_dir = 'under'; flip_note = '⚠️ 升盘信号被多项因子削弱·翻转预测小球'
    else:
        final_dir = base_dir; flip_note = ''

    r._totals_prediction = {
        'direction': final_dir, 'confidence': final_conf, 'line': line, 'trend': trend,
        'adjustments': adjustments, 'flipped': final_dir != base_dir,
        'flip_note': flip_note, 'both_dangerous': both_dangerous,
    }


def _cross_validate_score_vs_rules(r: PreMatchReport):
    """
    🆕 V3.4: 比分预测 ↔ V2.6规则 交叉验证

    两个独立模型的方向一致性检测:
    - V2.6规则模型: 基于过热/三条件/共识 → 预测方向
    - 泊松比分模型: 基于赔率隐含λ → 胜负概率

    一致 → 信号互相印证 → 置信度+3~5%
    矛盾 → 信号冲突 → 置信度-5~10% + 警告

    矛盾场景恰恰是模型"逆市场"的核心预测, 调整幅度更大以提示风险
    """
    sp = r.score_prediction
    if not sp:
        return  # 无泊松模型输出, 跳过

    hot = r.betfair_hot_side
    if not hot:
        return

    v26 = r.v26_prediction or ''
    conf = r.v26_confidence

    # 确定V2.6对热方的判断
    v26_hot_wins = any(w in v26 for w in ['热门胜', '热门仍赢', '实力碾压'])
    v26_hot_loses = any(w in v26 for w in ['热门不胜', '热门可能不胜'])
    v26_lean_hot = '偏向热门' in v26

    if not v26_hot_wins and not v26_hot_loses:
        return  # 信号不足/模糊, 不验证

    # 泊松热方胜率
    if hot == 'home':
        poisson_hot_win = sp.home_win_prob
        poisson_opp_win = sp.away_win_prob
    else:
        poisson_hot_win = sp.away_win_prob
        poisson_opp_win = sp.home_win_prob

    poisson_draw = sp.draw_prob

    # ── 一致性判定 (泊松概率为百分比值, 如60=60%) ──
    # 核心原则: 泊松从市场赔率推导, V2.6的核心价值恰在于逆市场发现。
    # 一致时互相印证→适度加分; 分歧时仅标注警告→不扣分(分歧可能是V2.6正确逆势)
    if v26_hot_wins:
        # V2.6说热门赢 → 泊松热方胜率应偏高
        if poisson_hot_win >= 50:
            boost = 3
            r.v26_warnings.append(
                f'🔗 交叉验证✅: 泊松热方胜率{poisson_hot_win:.0f}%≥50%·两模型一致→置信度+{boost}')
            r.v26_confidence = min(92, conf + boost)
        elif poisson_hot_win >= 38:
            r.v26_warnings.append(
                f'🔗 交叉验证🟡: 泊松热方胜率{poisson_hot_win:.0f}%∈[38,50)%·市场未完全定价热门')
        else:
            r.v26_warnings.append(
                f'🔗 交叉验证⚠️: 泊松热方胜率仅{poisson_hot_win:.0f}%<38%·市场看衰热门→V2.6逆势看好·注意风险')

    elif v26_hot_loses:
        # V2.6说热门不胜 → 泊松热方胜率应偏低
        if poisson_hot_win <= 38:
            boost = 5
            r.v26_warnings.append(
                f'🔗 交叉验证✅: 泊松热方胜率仅{poisson_hot_win:.0f}%≤38%·两模型一致→置信度+{boost}')
            r.v26_confidence = min(92, conf + boost)
        elif poisson_hot_win <= 50:
            r.v26_warnings.append(
                f'🔗 交叉验证⚠️: 泊松热方胜率{poisson_hot_win:.0f}%∈(38,50]%·市场仍倾向热门→V2.6逆势信号·注意风险')
        else:
            r.v26_warnings.append(
                f'🔗 交叉验证⚠️: 泊松热方胜率{poisson_hot_win:.0f}%>50%·市场强烈看好热门→V2.6逆势信号·高风险')


def _cross_validate_cover_rate(r: PreMatchReport):
    """
    🆕 V3.4: 穿盘率 ↔ V2.6预测 交叉验证

    检查预测方向与穿盘率是否一致:
    - 热门胜 + 穿盘率低 → 自然一致（小胜不穿盘）
    - 热门胜 + 穿盘率高 → 自然一致（大胜穿盘）
    - 热门不胜 → 跳过（热队输球无所谓穿盘）
    矛盾: 预测说热门不胜但穿盘率极高 → 信号冲突
    """
    cr = r.xls_cover_rate
    if not cr or cr <= 0:
        return

    pred = r.v26_prediction or ''
    hot_wins = any(w in pred for w in ['热门胜', '热门仍赢', '实力碾压'])
    hot_loses = any(w in pred for w in ['热门不胜', '热门可能不胜'])

    if hot_wins:
        # 热门赢 + 小盘口强制边缘 → 正常跳过
        if getattr(r, '_cover_depth_forced', False):
            return
        # 热门赢 + 穿盘率≥50% → 穿盘信号强 → 一致
        if cr >= 50:
            r.v26_warnings.append(
                f'🔗 穿盘交叉✅: 热门胜+穿盘率{cr:.0f}%≥50%→一致·大胜预期')
        # 热门赢 + 穿盘率<30% → 不穿盘信号强 → 一致（小胜）
        elif cr < 30:
            r.v26_warnings.append(
                f'🔗 穿盘交叉✅: 热门胜+穿盘率{cr:.0f}%<30%→一致·小胜预期')
    elif hot_loses:
        # 热门不胜但穿盘率极高 → 矛盾信号
        if cr >= 60:
            r.v26_warnings.append(
                f'🔗 穿盘交叉⚠️: 预测热门不胜但穿盘率{cr:.0f}%≥60%→信号冲突·注意')


def _build_structured(r: PreMatchReport):
    """V3.0: 生成结构化的预测输出"""
    # 🆕 V3.4: 交叉验证 (必须在structured构建前执行)
    _cross_validate_score_vs_rules(r)
    _cross_validate_cover_rate(r)

    # Determine winner
    winner = None
    if '热门胜' in r.v26_prediction and '⚠️' not in r.v26_prediction:
        winner = r.betfair_hot_side if r.betfair_hot_side else 'home'
    elif '⚠️ 热门不胜' in r.v26_prediction:
        winner = 'draw_or_underdog'
    elif '客胜' in r.v26_prediction:
        winner = 'away'

    # Cover assessment
    cover = None
    if r.xls_cover_rate > 0:
        if getattr(r, '_cover_depth_forced', False):
            cover = 'borderline'  # 🆕 V3.4: 小盘口强制边缘 (回测88%)
        elif r.xls_cover_rate >= 50:
            cover = 'likely_cover'
        elif r.xls_cover_rate >= 30:  # V3.4: 35→30 收紧不穿盘阈值
            cover = 'borderline'
        else:
            cover = 'unlikely_cover'

    score_data = None
    if r.score_prediction:
        sp = r.score_prediction
        score_data = {
            'expected_goals': {'home': sp.expected_goals_home, 'away': sp.expected_goals_away, 'total': sp.total_goals_expected},
            'win_probs': {'home': sp.home_win_prob, 'draw': sp.draw_prob, 'away': sp.away_win_prob},
            'most_likely': sp.most_likely,
            'most_likely_prob': sp.most_likely_prob,
            'top_scores': [{'score': s, 'prob': round(p * 100, 1)} for s, p in sp.top_scores[:6]],
        }

    r.structured = {
        'winner': winner or 'unknown',
        'confidence': r.v26_confidence,
        'cover_rate': r.xls_cover_rate,
        'cover_assessment': cover,
        'score_predictions': r.v26_score_predictions,
        'score_probabilities': score_data,  # 🆕 V3.3
        'gap_level': r.gap_level,
        'rule': r.v26_rule,
        'signals': dict(r.signal_matrix),
        'warnings': list(r.v26_warnings),
        'xls_trend_alert': r.xls_trend.alert_level if r.xls_trend else 'none',
    }


def _extract_home(match_name: str) -> str:
    """从中文比赛名提取主队英文名 (仅搜索VS前面的部分)"""
    home_part = match_name.split('VS')[0].strip()

    mapping = {
        '法国': 'France', '塞内加尔': 'Senegal',
        '伊拉克': 'Iraq', '挪威': 'Norway',
        '阿根廷': 'Argentina', '阿尔及利亚': 'Algeria',
        '奥地利': 'Austria', '约旦': 'Jordan',
        '西班牙': 'Spain', '佛得角': 'Cape Verde',
        '比利时': 'Belgium', '埃及': 'Egypt',
        '沙特': 'Saudi Arabia', '乌拉圭': 'Uruguay',
        '伊朗': 'Iran', '新西兰': 'New Zealand',
        '巴西': 'Brazil', '摩洛哥': 'Morocco',
        '海地': 'Haiti', '苏格兰': 'Scotland',
        '澳大利亚': 'Australia', '土耳其': 'Turkey',
        '卡塔尔': 'Qatar', '瑞士': 'Switzerland',
        '加拿大': 'Canada', '波黑': 'Bosnia & Herzegovina',
        '美国': 'USA', '巴拉圭': 'Paraguay',
        '荷兰': 'Netherlands', '日本': 'Japan',
        '德国': 'Germany', '库拉索': 'Curaçao',
        '科特迪瓦': "Ivory Coast", '厄瓜多尔': 'Ecuador',
        '瑞典': 'Sweden', '突尼斯': 'Tunisia',
        '墨西哥': 'Mexico', '南非': 'South Africa',
        '韩国': 'South Korea', '捷克': 'Czech Republic',
        '葡萄牙': 'Portugal', '民主刚果': 'DR Congo',
        '英格兰': 'England', '克罗地亚': 'Croatia',
        '加纳': 'Ghana', '巴拿马': 'Panama',
        '乌兹别克斯坦': 'Uzbekistan', '哥伦比亚': 'Colombia',
    }
    for cn, en in mapping.items():
        if cn in home_part:
            return en
    return home_part


def _extract_away(match_name: str) -> str:
    """从中文比赛名提取客队英文名 (仅搜索VS后面的部分)"""
    parts = match_name.split('VS')
    away_part = parts[-1].strip() if len(parts) > 1 else match_name

    mapping = {
        '塞内加尔': 'Senegal', '挪威': 'Norway',
        '阿尔及利亚': 'Algeria', '约旦': 'Jordan',
        '佛得角': 'Cape Verde', '埃及': 'Egypt',
        '乌拉圭': 'Uruguay', '新西兰': 'New Zealand',
        '摩洛哥': 'Morocco', '苏格兰': 'Scotland',
        '土耳其': 'Turkey', '瑞士': 'Switzerland',
        '波黑': 'Bosnia & Herzegovina', '巴拉圭': 'Paraguay',
        '日本': 'Japan', '库拉索': 'Curaçao',
        '厄瓜多尔': 'Ecuador', '突尼斯': 'Tunisia',
        '南非': 'South Africa', '捷克': 'Czech Republic',
        '民主刚果': 'DR Congo', '克罗地亚': 'Croatia',
        '巴拿马': 'Panama', '哥伦比亚': 'Colombia',
    }
    for cn, en in mapping.items():
        if cn in away_part:
            return en
    return away_part


def format_report(r: PreMatchReport) -> str:
    """格式化输出报告"""
    lines = [
        f"{'='*60}",
        f"  📊 {r.match_name} · V2.10赛前报告",
        f"  生成时间: {r.generated_at}",
        f"{'='*60}",
        "",
        "── 实力差距 ──",
        f"  级别: {r.gap_level.upper() or '(未计算·需手动输入FIFA排名)'}",
    ]
    if r.fifa_rank_gap:
        lines.append(f"  排名差: {r.fifa_rank_gap} · 身价比: {r.squad_value_ratio:.1f}x")

    lines += [
        "",
        "── XLS数据 ──",
        f"  {r.xls_summary or '(无XLS数据)'}",
        f"  共识: {r.xls_consensus_direction} {r.xls_consensus_pct:+.1f}% [{r.xls_consensus_source}/{r.xls_consensus_confidence}]",
        f"  博彩公司: {r.xls_bookmakers}家",
        "",
        "── 赔率趋势 (20家) ──",
        f"  主: {r.odds_home_chg:+.2f}%  平: {r.odds_draw_chg:+.2f}%  客: {r.odds_away_chg:+.2f}%",
    ]

    if r.odds_signals:
        for s in r.odds_signals:
            lines.append(f"  ⚡ {s}")

    lines += [
        "",
        "── 必发数据 ──",
        f"  冷热: {r.betfair_cold:+.0f}  热方: {r.betfair_hot_side}",
        f"  真过热: {'是' if r.betfair_is_real_hot else '否'}",
        f"  共识污染: {'⚠️ 是' if r.betfair_pollution else '✅ 否'} (差{r.betfair_pollution_gap:.1f}%)",
    ]
    if r.betfair_big_sell:
        lines.append(f"  🔴 大额卖单: {r.betfair_big_sell_count}笔·共{r.betfair_big_sell_volume:,.0f}")

    # V2.6 新信号
    if r.unanimity.get('triggered'):
        lines.append(f"  🔴 全票通过: {r.unanimity['ratio']:.0%}博彩公司{r.unanimity['direction']}·{r.unanimity['strength']}")
    if r.draw_collapse.get('triggered'):
        lines.append(f"  🔴🔴 平赔暴跌: {r.draw_collapse['avg_change']:.1f}% ({r.draw_collapse['down_count']}家)·{r.draw_collapse['severity']}")
    if r.xls_bf_divergence.get('divergence'):
        lines.append(f"  ⚠️ XLS-必发背离: {r.xls_bf_divergence['detail']}")

    # 三条件检查
    if r.three_conditions:
        tc = r.three_conditions
        lines += [
            "",
            "── BIG三条件 (对手质量) ──",
            f"  (a) 排名60+: {'✅' if tc['conditions']['a_rank60plus'] else '❌'} (排名{tc['data']['rank']})",
            f"  (b) 无五大射手: {'✅' if tc['conditions']['b_no_top5_scorer'] else '❌'} ({', '.join(tc.get('scorers', tc['data']['top5_players'])) or '无'})",
            f"  (c) 无爆冷史: {'✅' if tc['conditions']['c_no_giant_killing'] else '❌'} ({', '.join(tc['data']['giant_killings']) or '无'})",
            f"  结果: {tc['passed']}/3 → {tc['rule']}",
        ]
        if tc['data'].get('notes'):
            lines.append(f"  📝 {tc['data']['notes']}")

    # MOD威胁
    if r.moderate_threat and r.moderate_threat.get('has_goal_threat'):
        mt = r.moderate_threat
        lines.append(f"  ⚠️ MOD进攻威胁: {', '.join(mt['top_players'])} (场均{mt['goals_per_game']}球) → {mt['rule']}")

    # 🆕 V3.2 大小球预测
    tp = r._totals_prediction
    if tp:
        dir_label = '大球' if tp['direction'] == 'over' else ('小球' if tp['direction'] == 'under' else '均衡')
        flip_mark = '⚠️翻转' if tp.get('flipped') else ''
        lines.append(f"  大小球: {dir_label} {flip_mark} (盘口{tp['line']:.1f}|趋势{'📈升' if tp['trend']=='up' else '📉降' if tp['trend']=='down' else '➡️稳'} | 置信度{tp['confidence']}%)")
        if tp.get('adjustments'):
            for adj in tp['adjustments']:
                lines.append(f"    ↳ {adj}")
        if tp.get('flip_note'):
            lines.append(f"    ↳ {tp['flip_note']}")

    # 🆕 V3.3: 比分概率预测 (泊松模型)
    if r.score_prediction:
        lines.append(f"")
        lines.append(format_score_output(r.score_prediction))
    elif r.v26_score_predictions:
        lines.append(f"  比分参考: {', '.join(r.v26_score_predictions)}")

    lines += [
        "",
        f"── V2.7规则 ──",
        f"  规则: {r.v26_rule}",
        f"  预测: {r.v26_prediction or '(根据额外信号判定)'}",
        f"  置信度: {r.v26_confidence}% (动态·信号加权)",
    ]
    # 🆕 V3.2: 弱信号警告
    if r.v26_confidence < 60 and r.v26_confidence > 0:
        lines.append(f"  ⚠️ 低置信度({r.v26_confidence}%)·信号不足·建议回避或小额试探")
    # 🆕 穿盘率展示
    if r.xls_cover_rate > 0:
        if getattr(r, '_cover_depth_forced', False):
            cover_label = '🎲 小盘口·穿盘信号不可靠'
        elif r.xls_cover_rate < 30:
            cover_label = '🔴 大概率不穿盘'
        elif r.xls_cover_rate < 50:
            cover_label = '🟡 可能不穿盘'
        else:
            cover_label = '🟢 可能穿盘'
        adj_note = f' (原始{r.xls_cover_rate_raw:.0f}%→动态{r.xls_cover_rate:.0f}%)' if r.xls_cover_rate_raw > 0 and abs(r.xls_cover_rate_raw - r.xls_cover_rate) > 1 else ''
        lines.append(f"  穿盘率: {r.xls_cover_rate:.0f}%{adj_note} → {cover_label}")
        # 🆕 V3.4: 小盘口V2.6方向提示
        if getattr(r, '_cover_depth_forced', False):
            pred = r.v26_prediction or ''
            if any(w in pred for w in ['热门胜', '热门仍赢']):
                lines.append(f"    ↳ 🎲 小盘口·V2.6预测热门胜→倾向穿盘(仅供参考)")
            elif any(w in pred for w in ['热门不胜', '热门可能不胜']):
                lines.append(f"    ↳ 🎲 小盘口·V2.6预测热门不胜→倾向不穿(仅供参考)")

    if r.v26_warnings:
        for w in r.v26_warnings:
            lines.append(f"  ⚠️ {w}")

    lines += [
        "",
        "── 信号矩阵 ──",
    ]
    for k, v in r.signal_matrix.items():
        lines.append(f"  {k}: {v}")

    # 🆕 V2.15 XLS跨版本趋势
    if r.xls_trend and r.xls_trend.analyzed:
        lines += [
            "",
            f"── XLS历史趋势 ({r.xls_trend.total_versions}版) ──",
            f"  {trend_summary(r.xls_trend)}",
        ]
        if r.xls_trend.cover_rate_trend != 'stable':
            lines.append(f"  穿盘率: {r.xls_trend.cover_rate_first:.1f}%→{r.xls_trend.cover_rate_last:.1f}% ({r.xls_trend.cover_rate_change:+.1f}pp)")
        if r.xls_trend.consensus_trend not in ('stable', ''):
            lines.append(f"  共识: {r.xls_trend.consensus_first:+.1f}%→{r.xls_trend.consensus_last:+.1f}% [{r.xls_trend.consensus_trend}]")
        if r.xls_trend.totals_trend == 'shrinking':
            lines.append(f"  大小球: {r.xls_trend.totals_line_first:.1f}→{r.xls_trend.totals_line_last:.1f}")
        if r.xls_trend.signals:
            for sig in r.xls_trend.signals:
                lines.append(f"  {sig}")

    # ── V2.9 新增维度 ──
    if r.venue:
        venue = r.venue
        indoor_str = '室内' if venue.get('indoor') else '室外'
        lines += [
            "",
            "── 场地信息 ──",
            f"  场馆: {venue['name']} ({venue['city']})",
            f"  海拔: {venue['altitude_m']}m | 草皮: {venue['grass_type']} | {indoor_str}",
        ]
        if r.team_group_home:
            lines.append(f"  {r.team_group_home}组 MD{r.matchday} | 当地时间: {r.time_impact.local_hour}:00" if r.time_impact else f"  {r.team_group_home}组 MD{r.matchday}")

    if r.time_impact:
        lines += [
            "",
            "── 比赛时间 ──",
            f"  当地时间: {r.time_impact.local_hour}:00 ({r.time_impact.time_category})",
            f"  热风险: {r.time_impact.heat_risk:.0%} | 疲劳: {r.time_impact.fatigue_risk:.0%} | 露水: {r.time_impact.dew_risk:.0%} | 海拔: {r.time_impact.altitude_risk:.0%}",
            f"  调整: {r.time_impact.overall_adjustment:+.0f}%",
        ]

    if r.weather_impact and r.weather:
        lines += [
            "",
            "── 天气追踪 ──",
            f"  {r.weather.temperature_c}°C | 湿度{r.weather.humidity_pct}% | 风速{r.weather.wind_speed_kmh}km/h | {r.weather.condition}",
            f"  影响分: {r.weather_impact.score:+.1f} | 大小球修正: {r.weather_impact.over_under_adjustment:+.2f}",
        ]
        for w in r.weather_impact.warnings[:2]:
            if '理想' not in w:
                lines.append(f"  🌤️ {w}")

    if r.match_motivation:
        hm = r.match_motivation.home_motivation
        am = r.match_motivation.away_motivation
        lines += [
            "",
            "── 出线形势 ──",
            f"  {hm.team}: {hm.scenario_detail} (战意{hm.motivation_score:.0f}/10)",
            f"  {am.team}: {am.scenario_detail} (战意{am.motivation_score:.0f}/10)",
            f"  战意差: {r.match_motivation.differential:+.0f} → {r.match_motivation.prediction_bias}",
        ]
        # V2.13 新增字段
        if hm.need_goals:
            lines.append(f"  🎯 {hm.team}需要刷净胜球")
        if am.need_goals:
            lines.append(f"  🎯 {am.team}需要刷净胜球")
        if hm.rotation_risk > 0.2:
            lines.append(f"  🔄 {hm.team}轮换风险{hm.rotation_risk:.0%}")
        if am.rotation_risk > 0.2:
            lines.append(f"  🔄 {am.team}轮换风险{am.rotation_risk:.0%}")
        if hm.alt_path_better or am.alt_path_better:
            lines.append(f"  🔀 淘汰赛路径有更优选择")
        if r.match_motivation.tournament_note:
            lines.append(f"  📋 {r.match_motivation.tournament_note}")

    if r.lineup_impact and r.lineup_impact.confidence_adj != 0:
        lines += [
            "",
            "── 首发阵容 ──",
            f"  {r.lineup_impact.summary}",
            f"  置信度调整: {r.lineup_impact.confidence_adj:+.0f}%",
        ]
        for a in r.lineup_impact.home_adjustments + r.lineup_impact.away_adjustments:
            lines.append(f"  👥 {a}")

    if r.tactical_edge != 0 or r.coach_impact != 0:
        lines += [
            "",
            "── 战术与教练 ──",
        ]
        if r.tactical_edge != 0:
            lines.append(f"  战术优势: {r.tactical_edge:+.1f}/10 {('('+r.style_clash_note+')') if r.style_clash_note else ''}")
        if r.coach_impact != 0:
            lines.append(f"  教练影响: {int(r.coach_impact):+d}%")

    # ── V2.10 新增维度 ──
    if r.home_recent_form or r.form_diff:
        lines += [
            "",
            "── 近期状态 ──",
        ]
        if r.home_recent_form:
            hf = r.home_recent_form
            lines.append(f"  {hf.get('team','主')}: {hf.get('form_string','?')} | {hf.get('points_last5',0):.1f}/15分 | 状态分{hf.get('form_score',5):.1f}/10")
        if r.away_recent_form:
            af = r.away_recent_form
            lines.append(f"  {af.get('team','客')}: {af.get('form_string','?')} | {af.get('points_last5',0):.1f}/15分 | 状态分{af.get('form_score',5):.1f}/10")
        if r.form_diff:
            lines.append(f"  状态差: {r.form_diff.get('form_edge',0):+.1f} → 调整{r.form_diff.get('confidence_adj',0):+d}%")

    if r.h2h_result and r.h2h_result.get('h2h'):
        h2h = r.h2h_result['h2h']
        lines += [
            "",
            "── 历史交锋 ──",
            f"  {h2h.total_matches}场 | 主{h2h.home_wins}胜/{h2h.draws}平/客{h2h.away_wins}胜",
            f"  上次: {h2h.last_result}",
            f"  恩怨等级: {h2h.rivalry_level} | 心理优势: {h2h.psychological_edge or '无'}",
        ]
        if r.h2h_result.get('notes'):
            for n in r.h2h_result['notes'][:2]:
                lines.append(f"  → {n}")

    if r.referee_result and r.referee_result.get('referee'):
        ref = r.referee_result['referee']
        lines += [
            "",
            "── 裁判因素 ──",
            f"  {ref.name} ({ref.nationality}) | 场均黄牌{ref.avg_yellows:.1f}·红牌{ref.avg_reds:.1f}",
            f"  执法风格: {ref.strictness} | 风格: {ref.style_impact[:50]}...",
        ]
        if r.referee_result.get('notes'):
            for n in r.referee_result['notes'][:2]:
                if '执法' in n or '出牌' in n or '裁判' in n:
                    lines.append(f"  → {n}")

    # 🆕 V2.11 市场心理周期
    if r.market_psychology and r.market_psychology.get('cold_chasing'):
        mp = r.market_psychology
        lines += [
            "",
            "── 市场心理 ──",
            f"  📉 搏冷模式: 近{mp['recent_matches']}场{mp['upsets']}冷({mp['upset_rate']:.0%})",
            f"  → bearish信号可能含公众噪音·置信度{mp['confidence_adj']}%",
        ]

    return '\n'.join(lines)


def batch_report(matches: list, betfair_texts: dict = None) -> str:
    """多场对比视图 — 一键输出所有比赛关键信号对比表"""
    if betfair_texts is None:
        betfair_texts = {}

    reports = []
    for m in matches:
        bf = betfair_texts.get(m, "")
        r = generate_report(m, betfair_text=bf)
        reports.append(r)

    # 构建对比表
    header = f"{'比赛':20s} | {'差距':8s} | {'共识':>6s} | {'冷热':>4s} | {'全票':6s} | {'平赔暴跌':8s} | {'三条件':6s} | {'V2.6规则':26s} | {'预测':18s} | {'信':>3s} | {'比分预测':20s}"
    sep = "-" * len(header)
    lines = [sep, header, sep]

    for r in reports:
        uni = '⚠️' if r.unanimity.get('triggered') else '--'
        dc = '🔴' if r.draw_collapse.get('triggered') else '--'
        tc = f"{r.three_conditions.get('passed','?')}/3" if r.three_conditions else 'N/A'
        pred = r.v26_prediction or '(待定)'
        # 🆕 V3.3 P1-5: 比分预测列
        try:
            from score_prediction import format_score_output_compact
            score_str = format_score_output_compact(r.score_prediction) if r.score_prediction else '—'
        except Exception:
            score_str = '—'

        line = (f"{r.match_name:20s} | {r.gap_level:8s} | "
                f"{r.xls_consensus_pct:+5.0f}% | {r.betfair_cold:+4.0f} | "
                f"{uni:6s} | {dc:8s} | {tc:6s} | "
                f"{r.v26_rule[:26]:26s} | {pred[:18]:18s} | {r.v26_confidence:>2}% | "
                f"{score_str[:20]:20s}")
        lines.append(line)

    lines.append(sep)

    # 详细报告
    lines.append("")
    lines.append("=" * 60)
    for r in reports:
        lines.append(format_report(r))
        lines.append("")

    return '\n'.join(lines)


# ── 命令行 ──
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法:")
        print("  python pre_match_report.py '法国VS塞内加尔' [betfair.txt]")
        print("  python pre_match_report.py --batch '法国,阿根廷,伊拉克,奥地利'")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        matches = sys.argv[2].split(',')
        print(batch_report(matches))
    else:
        match = sys.argv[1]
        bf_text = ""
        if len(sys.argv) > 2:
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                bf_text = f.read()
        report = generate_report(match, betfair_text=bf_text)
        print(format_report(report))

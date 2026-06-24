# -*- coding: utf-8 -*-
"""Generate predictions_june25.html with latest model data"""
from pre_match_report import generate_report
from datetime import datetime

matches_config = [
    ('瑞士VS加拿大', 'B', 'BMO Field · Toronto', '22C · 双方争B1'),
    ('波黑VS卡塔尔', 'B', 'Gillette Stadium · Boston', '24C · 双方都必须赢'),
    ('苏格兰VS巴西', 'C', 'Hard Rock Stadium · Miami', '30C · 巴西争C1'),
    ('摩洛哥VS海地', 'C', 'Mercedes-Benz · Atlanta · 室内', '22C · 摩洛哥争C1'),
    ('捷克VS墨西哥', 'A', 'Estadio Azteca · Mexico City', '2250m · 墨西哥已出线轮换60%'),
    ('南非VS韩国', 'A', 'Estadio BBVA · Monterrey', '32C · 双方都必须赢'),
]

reports = []
for name, grp, venue, note in matches_config:
    print(f'Generating: {name}...')
    r = generate_report(name)
    reports.append((r, grp, venue, note))

def get_scores(r):
    try:
        return r.structured.get('poisson', {}).get('score_probs', [])[:4]
    except:
        return []

def get_triple(r):
    try:
        ps = r.structured.get('poisson', {})
        return ps.get('home_prob', 33), ps.get('draw_prob', 34), ps.get('away_prob', 33)
    except:
        return 33, 34, 33

def get_xg(r):
    try:
        ps = r.structured.get('poisson', {})
        return ps.get('xg_home', 0), ps.get('xg_away', 0)
    except:
        return 0, 0

cards_html = []
summary_rows = []

for r, grp, venue, note in reports:
    name = r.match_name
    gap = r.gap_level
    pred = r.v26_prediction
    conf = r.v26_confidence
    parts = name.replace('vs','VS').split('VS')
    home_team = parts[0].strip()
    away_team = parts[1].strip() if len(parts) > 1 else ''

    # Gap badge
    gap_cls = f'gap-{gap}'
    gap_badge = gap.upper()[:4]

    # Prediction label
    if '热门不胜' in pred:
        pred_cls = 'pred-upset'
        pred_label = '热门不胜'
        pred_short = '热不胜'
    elif '客胜' in pred or 'away' in pred.lower():
        pred_cls = 'pred-away'
        pred_label = '客胜'
        pred_short = '客胜'
    else:
        pred_cls = 'pred-home'
        pred_label = '主胜'
        pred_short = '主胜'

    # Confidence ring
    if conf >= 70:
        conf_cls = 'conf-high'
    elif conf >= 50:
        conf_cls = 'conf-mid'
    else:
        conf_cls = 'conf-low'
    conf_label = '高信' if conf >= 70 else ('中信' if conf >= 50 else '低信')

    # Odds
    home_odds = r._bf_raw_odds.get('home', 0) if hasattr(r, '_bf_raw_odds') else 0
    draw_odds = r._bf_raw_odds.get('draw', 0) if hasattr(r, '_bf_raw_odds') else 0
    away_odds = r._bf_raw_odds.get('away', 0) if hasattr(r, '_bf_raw_odds') else 0

    # Heat
    cold = r.betfair_cold if hasattr(r, 'betfair_cold') else 0
    hot_side = r.betfair_hot_side if hasattr(r, 'betfair_hot_side') else '?'
    heat_label = '真过热' if abs(cold) >= 20 else ''

    # Consensus
    cons_dir = r.xls_consensus_direction or ''
    cons_pct = r.xls_consensus_pct if hasattr(r, 'xls_consensus_pct') else 0

    # Poisson
    scores = get_scores(r)
    xg_h, xg_a = get_xg(r)
    hp, dp, ap = get_triple(r)

    # Trap odds
    trap_html = ''
    trap_score = 0
    trap_level = '无'
    if r.trap_odds and r.trap_odds.trap_level != 'none':
        t = r.trap_odds
        trap_score = t.trap_score
        trap_level = t.trap_level
        active = [f'{n}({s["score"]:.0f})' for n, s in t.signals.items() if s['score'] >= 20]
        trap_html = f'<div class="signal-row" style="color:#ff9100;font-weight:600">🚨 诱盘{t.trap_score:.0f}分({t.trap_level})·方向:{t.trap_direction}·调信{t.confidence_adj:+d}% | {", ".join(active[:3])}</div>'

    # Motivation
    mot_info = ''
    mot_diff = 0
    mot_bias = '?'
    if r.match_motivation:
        hm = r.match_motivation.home_motivation
        am = r.match_motivation.away_motivation
        mot_diff = r.match_motivation.differential
        mot_bias = r.match_motivation.prediction_bias
        mot_info = f'{hm.team}[{hm.motivation_score:.0f}] vs {am.team}[{am.motivation_score:.0f}]'

    # Cover rate
    cover = r.xls_cover_rate if hasattr(r, 'xls_cover_rate') and r.xls_cover_rate else 0

    # Totals
    tp = getattr(r, '_totals_prediction', {}) or {}
    totals_dir = tp.get('direction', '?')
    totals_conf = tp.get('confidence', 0)
    totals_line = tp.get('line', 2.5)
    if totals_dir == 'over':
        totals_pred = '大球'
    elif totals_dir == 'under':
        totals_pred = '小球'
    elif totals_dir == 'neutral':
        totals_pred = '均'
    else:
        totals_pred = str(totals_dir)

    # Path
    path_num = r.structured.get('path_num', '-') if hasattr(r, 'structured') else '-'

    # Score chips
    score_html = ''
    for i, s in enumerate(scores):
        score = s.get('score', '?')
        prob = s.get('prob', 0)
        cls = 'top' if i == 0 else ''
        score_html += f'<div class="score-chip {cls}">{score}<span class="prob" style="display:block;font-size:0.65rem;color:var(--text2)">{prob:.1f}%</span></div>\n            '

    top_score = scores[0].get('score', '?') if scores else '?'
    top_prob = scores[0].get('prob', 0) if scores else 0

    # Decision path color
    path_color = '#ff3d5a' if '热门不胜' in pred else ('#00c853' if '热门胜' in pred else '#ffc107')

    # Hot/Cold CSS
    cold_css = 'red' if abs(cold) >= 30 else ('warn' if abs(cold) >= 20 else '')
    trap_css = 'red' if trap_level in ('severe', 'moderate') else ''

    # Consensus count
    bookmakers = r.xls_bookmakers if hasattr(r, 'xls_bookmakers') else 0

    # Signals summary
    signal_lines = []
    if r.trap_odds and r.trap_odds.trap_level != 'none':
        t = r.trap_odds
        for sn, s in t.signals.items():
            if s['score'] >= 50:
                cn = {'jingcai_divergence':'竞彩背离','pnl_contradiction':'PnL矛盾','volume_odds_divergence':'资金背离','pinnacle_divergence':'Pinnacle偏离','narrative_divergence':'叙事矛盾','asian_water_contradiction':'水位异常'}.get(sn, sn)
                signal_lines.append(f'<div class="signal-row">{cn}({s["score"]:.0f}分): {s["detail"][:80]}</div>')

    card = f'''<!-- {name} -->
<div class="match-card">
  <div class="card-header">
    <div><span class="time">{grp}组 MD3</span><div class="group">{venue}</div></div>
    <div style="display:flex;gap:8px;align-items:center">
      <span class="gap-badge {gap_cls}">{gap_badge}</span>
      <span style="font-size:0.75rem;color:var(--text2)">{note}</span>
    </div>
  </div>
  <div class="teams-row">
    <div class="team"><div class="flag">{home_team[:2]}</div><div class="name">{home_team}</div><div class="rank">{mot_info}</div></div>
    <div class="vs">VS</div>
    <div class="team"><div class="flag">{away_team[:2]}</div><div class="name">{away_team}</div><div class="rank">战意差{mot_diff:+.0f} → {mot_bias}</div></div>
  </div>
  <div class="prediction-bar">
    <span class="pred-label {pred_cls}">{pred_label}</span>
    <div class="conf-ring {conf_cls}">{conf}%</div>
    <span style="font-size:0.8rem;color:var(--text2)">{conf_label}</span>
  </div>
  <div class="score-section">
    <div class="section-title">泊松比分 · xG {xg_h:.2f}–{xg_a:.2f} (总 {xg_h+xg_a:.2f})</div>
    <div class="score-grid">
            {score_html}</div>
    <div class="prob-triple">
      <div class="prob-bar-wrap"><div class="fill fill-home" style="width:{hp:.0f}%"></div><span>主 {hp:.1f}%</span></div>
      <div class="prob-bar-wrap"><div class="fill fill-draw" style="width:{dp:.0f}%"></div><span>平 {dp:.1f}%</span></div>
      <div class="prob-bar-wrap"><div class="fill fill-away" style="width:{ap:.0f}%"></div><span>客 {ap:.1f}%</span></div>
    </div>
  </div>
  <div class="stats-grid">
    <div class="stat-item"><span class="stat-label">欧赔</span><span class="stat-val">{home_odds:.2f} / {draw_odds:.2f} / {away_odds:.2f}</span></div>
    <div class="stat-item"><span class="stat-label">冷热</span><span class="stat-val {cold_css}">{hot_side}{cold:+.0f} {heat_label}</span></div>
    <div class="stat-item"><span class="stat-label">共识</span><span class="stat-val">{cons_dir} {cons_pct:+.0f}% ({bookmakers}家)</span></div>
    <div class="stat-item"><span class="stat-label">大小球</span><span class="stat-val">{totals_pred} {totals_line:.1f}球 (信{totals_conf:.0f}%)</span></div>
    <div class="stat-item"><span class="stat-label">穿盘率</span><span class="stat-val">{cover:.0f}%</span></div>
    <div class="stat-item"><span class="stat-label">诱盘</span><span class="stat-val {trap_css}">{trap_score:.0f}分 {trap_level}</span></div>
    <div class="stat-item"><span class="stat-label">战意差</span><span class="stat-val">{mot_diff:+.0f} → {mot_bias}</span></div>
    <div class="stat-item"><span class="stat-label">热方/共识</span><span class="stat-val">{hot_side}/{cons_dir}</span></div>
  </div>
  <div class="signals">
    {trap_html}
    {''.join(signal_lines)}
  </div>
  <div class="decision-path">
    <span class="path-num">{path_num}</span><span class="arrow"></span>{pred}<span class="arrow"></span><span style="color:{path_color};font-weight:700">{pred}</span>
  </div>
</div>
'''
    cards_html.append(card)

    # Summary row
    conf_color = '#00c853' if conf >= 70 else ('#ffc107' if conf >= 50 else '#ff3d5a')
    trap_note = f'🚨诱盘{trap_score:.0f} ' if trap_level not in ('none', '无') else ''
    summary_rows.append(
        f'<tr><td>{grp}</td><td>{home_team} vs {away_team}</td>'
        f'<td><span class="gap-badge {gap_cls}">{gap_badge}</span></td>'
        f'<td style="font-size:0.75rem">#{path_num} {pred_short}</td>'
        f'<td><span class="pred-label {pred_cls}">{pred_short}</span></td>'
        f'<td>{top_score} {top_prob:.1f}%</td>'
        f'<td><b style="color:{conf_color}">{conf}%</b></td>'
        f'<td style="font-size:0.75rem">{trap_note}冷热{cold:+.0f}·共识{cons_dir}{cons_pct:+.0f}%</td></tr>'
    )

# Build HTML
now = datetime.now().strftime('%Y-%m-%d %H:%M')
now_compact = datetime.now().strftime('%H:%M')

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>世界杯预测报告 — 6月25日</title>
<style>
:root {{
  --bg: #0f1117; --card: #1a1d27; --card2: #212433;
  --border: #2a2d3a; --text: #e1e4ed; --text2: #8b8fa7;
  --green: #00c853; --red: #ff3d5a; --yellow: #ffc107;
  --blue: #448aff; --orange: #ff9100; --accent: #7c4dff;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 24px 16px; }}
.container {{ max-width: 1320px; margin:0 auto; }}
.header {{ text-align: center; padding: 32px 0 40px; border-bottom: 1px solid var(--border); margin-bottom: 32px; }}
.header h1 {{ font-size: 2rem; font-weight: 700; background: linear-gradient(135deg, #7c4dff, #448aff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }}
.header .subtitle {{ color: var(--text2); font-size: 0.95rem; }}
.header .meta {{ display: flex; justify-content: center; gap: 24px; margin-top: 16px; font-size: 0.85rem; color: var(--text2); }}
.header .badge {{ display: inline-block; background: rgba(124,77,255,0.15); color: #b39dff; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }}
.match-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 20px; }}
.match-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid var(--border); background: var(--card2); }}
.card-header .time {{ font-size: 0.8rem; color: var(--text2); }}
.card-header .group {{ font-size: 0.85rem; font-weight: 600; color: var(--accent); margin-top: 2px; }}
.gap-badge {{ font-size: 0.7rem; font-weight: 700; padding: 4px 10px; border-radius: 10px; text-transform: uppercase; }}
.gap-big {{ background: rgba(255,145,0,0.15); color: #ff9100; }}
.gap-extreme {{ background: rgba(255,61,90,0.15); color: #ff3d5a; }}
.gap-moderate {{ background: rgba(255,193,7,0.15); color: #ffc107; }}
.gap-close {{ background: rgba(68,138,255,0.15); color: #448aff; }}
.teams-row {{ display: flex; align-items: center; justify-content: center; padding: 24px; gap: 16px; }}
.team {{ text-align: center; flex: 1; }}
.team .flag {{ font-size: 2.4rem; }}
.team .name {{ font-size: 1.05rem; font-weight: 700; margin-top: 4px; }}
.team .rank {{ font-size: 0.72rem; color: var(--text2); }}
.vs {{ font-size: 1.1rem; font-weight: 700; color: var(--text2); padding: 0 12px; }}
.prediction-bar {{ display: flex; align-items: center; justify-content: center; gap: 12px; padding: 0 24px 14px; }}
.pred-label {{ font-size: 0.82rem; font-weight: 600; padding: 5px 14px; border-radius: 20px; }}
.pred-home {{ background: rgba(0,200,83,0.15); color: #00c853; }}
.pred-away {{ background: rgba(68,138,255,0.15); color: #448aff; }}
.pred-upset {{ background: rgba(255,61,90,0.15); color: #ff3d5a; }}
.conf-ring {{ width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.95rem; border: 3px solid; }}
.conf-high {{ border-color: #00c853; color: #00c853; background: rgba(0,200,83,0.08); }}
.conf-mid {{ border-color: #ffc107; color: #ffc107; background: rgba(255,193,7,0.08); }}
.conf-low {{ border-color: #ff3d5a; color: #ff3d5a; background: rgba(255,61,90,0.08); }}
.score-section {{ padding: 14px 24px; border-top: 1px solid var(--border); background: rgba(0,0,0,0.15); }}
.score-section .section-title {{ font-size: 0.75rem; color: var(--text2); font-weight: 600; text-transform: uppercase; margin-bottom: 10px; }}
.score-grid {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }}
.score-chip {{ font-size: 0.82rem; padding: 5px 10px; border-radius: 8px; background: var(--card2); border: 1px solid var(--border); text-align: center; min-width: 65px; }}
.score-chip.top {{ border-color: var(--accent); background: rgba(124,77,255,0.1); font-weight: 700; }}
.prob-triple {{ display: flex; gap: 6px; margin-top: 8px; }}
.prob-bar-wrap {{ flex:1; position:relative; height:24px; background:var(--card2); border-radius:5px; overflow:hidden; text-align:center; font-size:0.75rem; font-weight:600; line-height:24px; }}
.prob-bar-wrap .fill {{ position:absolute; left:0; top:0; bottom:0; border-radius:5px; opacity:0.25; }}
.fill-home {{ background:#00c853; }} .fill-draw {{ background:#ffc107; }} .fill-away {{ background:#448aff; }}
.prob-bar-wrap span {{ position:relative; z-index:1; }}
.stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 10px 24px 14px; }}
.stat-item {{ display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem; padding: 5px 8px; background: var(--card2); border-radius: 5px; }}
.stat-label {{ color: var(--text2); }} .stat-val {{ font-weight: 600; }} .stat-val.warn {{ color: #ff9100; }} .stat-val.red {{ color: #ff3d5a; }}
.signals {{ padding: 10px 24px 14px; border-top: 1px solid var(--border); }}
.signal-row {{ font-size: 0.78rem; padding: 2px 0; }}
.decision-path {{ padding: 10px 24px; background: rgba(124,77,255,0.06); border-top: 1px solid var(--border); font-size: 0.8rem; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
.decision-path .path-num {{ display:inline-flex; align-items:center; justify-content:center; width:24px;height:24px; border-radius:50%; background:var(--accent); color:#fff; font-size:0.72rem; font-weight:700; flex-shrink:0; }}
.decision-path .arrow {{ color: var(--text2); }}
.summary-table {{ margin-top: 36px; background: var(--card); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }}
.summary-table h3 {{ padding: 14px 24px; font-size: 0.95rem; border-bottom: 1px solid var(--border); background: var(--card2); }}
.summary-table table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
.summary-table th {{ text-align: left; padding: 10px 14px; color: var(--text2); font-weight: 600; font-size: 0.72rem; text-transform: uppercase; border-bottom: 1px solid var(--border); background: var(--card2); }}
.summary-table td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); }}
.note-box {{ margin-top: 24px; padding: 14px 24px; background: rgba(255,145,0,0.06); border: 1px solid rgba(255,145,0,0.2); border-radius: 12px; font-size: 0.8rem; color: var(--text2); }}
.note-box strong {{ color: #ff9100; }}
.kol {{ color: #ff3d5a; font-weight: 700; }}
@media (max-width: 680px) {{ .match-grid {{ grid-template-columns: 1fr; }} .stats-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>世界杯预测报告 — 6月25日</h1>
  <div class="subtitle">V3.41 · 诱盘检测·决策树11路径·motivation修复 · 回测34/44=77.3% · 数据刷新{now_compact} CST</div>
  <div class="meta">
    <span>2026年6月25日 (周四)</span>
    <span>数据更新 {now_compact} CST</span>
    <span class="badge">6场 · MD3 A/B/C组</span>
  </div>
</div>

<div class="match-grid">
{''.join(cards_html)}
</div>

<div class="summary-table">
  <h3>6月25日 六场预测总览 (V3.41 · 数据{now_compact}CST)</h3>
  <table>
    <thead>
      <tr><th>组</th><th>对阵</th><th>差距</th><th>路径</th><th>预测</th><th>比分</th><th>信</th><th>关键信号</th></tr>
    </thead>
    <tbody>
      {''.join(summary_rows)}
    </tbody>
  </table>
</div>

<div class="note-box">
  <strong>V3.41 风险提示 · 诱盘检测已上线</strong><br>
  🚨 <b>瑞士VS加拿大</b>触发诱盘警报(中度45分)——竞彩逆势降赔·叙事-资金背离·庄家亏损矛盾·市场做局诱空瑞士。<br>
  🟡 <b>捷克VS墨西哥</b>战意分化极端(捷克10 vs 墨西哥3·轮换60%)——但墨西哥仍是热门(赔率2.00)·市场无视战意差。<br>
  🟡 <b>波黑VS卡塔尔</b>共识-100%极端看多 vs 冷热+23真过热·CLOSE唯一热门不胜·信仅36%——模型内部矛盾最激烈。<br>
  🔵 <b>苏格兰VS巴西</b>共识+94%严重看空·BIG无过热·巴西实力优先·但信仅45%·穿盘率21%·赢球输盘风险极高。<br>
  🟢 <b>摩洛哥VS海地</b>EXTREME碾压0.98·跳过泊松·直接实力预测·最高信70%。<br>
  🔵 <b>南非VS韩国</b>共识+87%看空·BIG无过热·三条件3/3·冷热-47极冷·韩国热门。<br>
  <strong>数据源: 500.com XLS + 必发 + 竞彩 · V3.41 · 回测34/44=77.3% · 刷新于{now_compact} CST</strong>
</div>

<div style="text-align:center;padding:32px 0;color:var(--text2);font-size:0.78rem">
  V3.41 · 诱盘检测6维度 · motivation语义修复 · <a href="predictions_june24.html" style="color:#b39dff">6月24日预测</a> · <a href="group_predictions.html" style="color:#b39dff">12组排名预测</a>
</div>

</div>
</body>
</html>'''

outpath = r'd:\hyji\预测模型V1.0\predictions_june25.html'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Written: {outpath}')
print(f'Size: {len(html)} bytes')
print('Done!')

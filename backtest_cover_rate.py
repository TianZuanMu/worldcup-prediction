# -*- coding: utf-8 -*-
"""
穿盘率专项回测 — 所有已完赛比赛的穿盘率置信度分析
V4.3: 输出 cover_rate_raw / adjusted / cover_risk / 金三角 / 穿盘-泊松交叉验证
"""
import json, sys, traceback
from pathlib import Path
from datetime import datetime

BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
MATCHES_FILE = BACKTEST_DIR / "matches.json"

def run():
    sys.path.insert(0, str(Path(r"C:\Users\A\PyCharmMiscProject")))
    from pre_match_report import generate_report
    from knockout_motivation import refresh_standings
    from match_context import get_team_group, normalize_team_name

    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        all_matches = json.load(f)

    # Filter valid+completed
    valid = []
    skipped_list = []
    for m in all_matches:
        if m['actual']['result'] == 'pending':
            continue
        name = m['match_name']
        parts = name.replace('vs', 'VS').replace('Vs', 'VS').split('VS')
        if len(parts) != 2:
            continue
        home = normalize_team_name(parts[0].strip())
        away = normalize_team_name(parts[1].strip())
        hg = get_team_group(home)
        ag = get_team_group(away)
        if hg and ag and hg == ag:
            valid.append(m)
        else:
            skipped_list.append(f'{name} ({hg}vs{ag})')

    refresh_standings()

    print(f'{"="*120}')
    print(f'  穿盘率专项回测 — {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  有效场次: {len(valid)} | 跨组过滤: {len(skipped_list)}')
    print(f'{"="*120}')
    print(f'{"比赛":28s} | {"实际":5s} | {"预测":30s} | {"原始穿盘":>6s} | {"调整穿盘":>6s} | {"穿盘风险":>16s} | {"金三角":5s} | {"交叉验证":8s} | {"置信度":>6s} | 判定')
    print(f'{"-"*120}')

    correct = total = errors = 0
    details = []

    for m in valid:
        name = m['match_name']
        actual = m['actual']
        actual_result = actual['result']
        actual_score = actual['score']

        try:
            r = generate_report(name)
        except Exception as e:
            errors += 1
            print(f'  ❌ {name:26s} | {"ERR":5s} | {str(e)[:60]}')
            continue

        # ── 提取穿盘率数据 ──
        raw_cr = getattr(r, 'xls_cover_rate_raw', 0) or 0
        adj_cr = getattr(r, 'xls_cover_rate', 0) or 0

        # cover_risk from score_prediction (nested object)
        sp = getattr(r, 'score_prediction', None)
        cover_risk = getattr(sp, 'cover_risk', '') or '' if sp else ''
        cover_risk_prob = getattr(sp, 'cover_risk_prob', 0) or 0 if sp else 0

        # 金三角是否触发 (置信度>75%被限制)
        golden_triangle = ''
        for w in (r.v26_warnings or []):
            if '金三角' in w:
                golden_triangle = '触发'
                break
        if not golden_triangle:
            golden_triangle = '通过' if r.v26_confidence > 75 else 'N/A'

        # 穿盘率交叉验证
        cross_val = ''
        for w in (r.v26_warnings or []):
            if '穿盘' in w and ('交叉' in w or 'xG' in w or '泊松' in w):
                cross_val = w[:30]
                break

        # 穿盘率相关warnings
        cr_warnings = [w for w in (r.v26_warnings or []) if '穿盘' in w]

        # ── 判定 ──
        hot = r.odds_favorite or r.betfair_hot_side
        pred_text = r.v26_prediction

        if '⚠️ 不预测' in pred_text:
            is_correct = '⏭️'
        elif '热门不胜' in pred_text or '热门可能不胜' in pred_text:
            expected = 'not_' + hot
            is_correct = '✅' if (
                (expected == 'not_home' and actual_result != 'home') or
                (expected == 'not_away' and actual_result != 'away')
            ) else '❌'
        elif '热门胜' in pred_text or '热门仍赢' in pred_text:
            expected = hot
            is_correct = '✅' if actual_result == expected else '❌'
        elif '客胜' in pred_text:
            is_correct = '✅' if actual_result == 'away' else '❌'
        elif '主队不败' in pred_text:
            is_correct = '✅' if actual_result in ('home', 'draw') else '❌'
        elif '平局风险' in pred_text:
            is_correct = '✅' if actual_result == 'draw' else '❌'
        else:
            is_correct = '?'

        if '⏭️' not in is_correct:
            total += 1
            if '✅' in is_correct:
                correct += 1

        # 穿盘风险格式化
        if cover_risk == 'win_but_lose_spread':
            risk_str = f'⚠️ 赢球输盘 {cover_risk_prob:.0f}%'
        elif cover_risk == 'cover_likely':
            risk_str = f'🟢 穿盘 {cover_risk_prob:.0f}%'
        elif cover_risk == 'neutral':
            risk_str = '—'
        else:
            risk_str = str(cover_risk)[:16] if cover_risk else '—'

        # 原始值 0 表示无数据
        raw_str = f'{raw_cr:.0f}%' if raw_cr > 0 else '—'
        adj_str = f'{adj_cr:.0f}%' if adj_cr > 0 else '—'

        # 交叉验证
        cv_short = ''
        for w in (r.v26_warnings or []):
            if '穿盘' in w and 'xG' in w:
                cv_short = 'xG矛盾'
                break
            elif '穿盘-泊松' in w:
                cv_short = '泊松矛盾'
                break
        if not cv_short:
            for w in (r.v26_warnings or []):
                if '穿盘<40%' in w and 'xG>3.0' in w:
                    cv_short = '交叉-5'
                    break

        print(f'{name:28s} | {actual_result:5s} {actual_score:5s} | {pred_text[:30]:30s} | {raw_str:>6s} | {adj_str:>6s} | {risk_str:16s} | {golden_triangle:5s} | {cv_short:8s} | {r.v26_confidence:5.1f}% | {is_correct}')

        # 穿盘率警告
        for w in cr_warnings:
            if '金三角' not in w:
                print(f'{"":30s}  ↳ {w[:100]}')

        details.append({
            'match': name,
            'actual': f'{actual_result} {actual_score}',
            'prediction': pred_text,
            'cover_raw': raw_cr,
            'cover_adjusted': adj_cr,
            'cover_risk': cover_risk,
            'cover_risk_prob': cover_risk_prob,
            'golden_triangle': golden_triangle,
            'confidence': r.v26_confidence,
            'gap': r.gap_level,
            'correct': is_correct,
            'cr_warnings': cr_warnings,
        })

    print(f'{"="*120}')
    acc = f'{correct}/{total} = {correct/total*100:.1f}%' if total > 0 else 'N/A'
    print(f'  准确率: {acc} | 错误: {errors}')

    # ── 按穿盘率分档统计 ──
    print(f'\n{"="*80}')
    print(f'  穿盘率分档准确率')
    print(f'{"="*80}')
    from collections import defaultdict
    bins = [
        (0, 20, '极低 0-20%'),
        (20, 30, '低 20-30%'),
        (30, 40, '中低 30-40%'),
        (40, 50, '中等 40-50%'),
        (50, 60, '中高 50-60%'),
        (60, 100, '高 60-100%'),
    ]
    for lo, hi, label in bins:
        tier = defaultdict(lambda: {'c': 0, 't': 0})
        for d in details:
            cr = d['cover_adjusted'] if d['cover_adjusted'] > 0 else d['cover_raw']
            if lo <= cr < hi:
                tier[label]['t'] += 1
                if '✅' in d['correct']:
                    tier[label]['c'] += 1
        if tier:
            t = tier[label]['t']
            c = tier[label]['c']
            if t > 0:
                bar = '█' * (t * 2)
                print(f'  {label:16s}: {c}/{t} = {c/t*100:.0f}% {bar}')

    # ── 穿盘风险统计 ──
    print(f'\n{"="*80}')
    print(f'  穿盘风险 (cover_risk) 统计')
    print(f'{"="*80}')
    risk_stats = defaultdict(lambda: {'c': 0, 't': 0})
    for d in details:
        risk = d['cover_risk'] or 'unknown'
        risk_stats[risk]['t'] += 1
        if '✅' in d['correct']:
            risk_stats[risk]['c'] += 1
    for risk, s in sorted(risk_stats.items()):
        print(f'  {risk:30s}: {s["c"]}/{s["t"]} = {s["c"]/s["t"]*100:.0f}%' if s["t"] > 0 else f'  {risk:30s}: 0')

    # ── 金三角统计 ──
    print(f'\n{"="*80}')
    print(f'  金三角约束统计')
    print(f'{"="*80}')
    gt_stats = defaultdict(lambda: {'c': 0, 't': 0})
    for d in details:
        gt = d['golden_triangle']
        gt_stats[gt]['t'] += 1
        if '✅' in d['correct']:
            gt_stats[gt]['c'] += 1
    for gt, s in sorted(gt_stats.items()):
        print(f'  {gt:10s}: {s["c"]}/{s["t"]} = {s["c"]/s["t"]*100:.0f}%' if s["t"] > 0 else f'  {gt:10s}: 0')

    print(f'\n回测完成: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

if __name__ == '__main__':
    run()

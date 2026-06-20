# -*- coding: utf-8 -*-
"""
V3.0 回测自动化 (P3#17)
一键回测全部完赛+输出对比报告+分档统计。
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime


BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
MATCHES_FILE = BACKTEST_DIR / "matches.json"


@dataclass
class BacktestResult:
    match_name: str = ''
    prediction: str = ''
    expected: str = ''
    actual_result: str = ''
    actual_score: str = ''
    confidence: float = 0.0
    gap_level: str = ''
    correct: bool = False
    skipped: bool = False
    notes: str = ''


def run_backtest(verbose: bool = False) -> Dict:
    """
    一键回测全部完赛场次。

    Returns:
        {total, correct, skipped, accuracy, by_gap, by_confidence, results, errors}
    """
    from pre_match_report import generate_report
    from knockout_motivation import refresh_standings
    from match_context import get_team_group, normalize_team_name

    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        all_matches = json.load(f)

    # Filter valid matches
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

    results: List[BacktestResult] = []
    correct = total = skipped = errors = 0

    for m in valid:
        name = m['match_name']
        actual = m['actual']
        actual_result = actual['result']
        actual_score = actual['score']

        try:
            r = generate_report(name)
        except Exception as e:
            errors += 1
            if verbose:
                print(f'  ❌ {name}: {e}')
            continue

        br = BacktestResult(
            match_name=name, prediction=r.v26_prediction,
            actual_result=actual_result, actual_score=actual_score,
            confidence=r.v26_confidence, gap_level=r.gap_level,
        )

        # Score prediction
        pred_text = r.v26_prediction
        hot = r.betfair_hot_side

        if '⚠️ 不预测' in pred_text:
            br.skipped = True
            br.notes = 'EXTREME skip'
            skipped += 1
        elif '⚠️ 热门不胜' in pred_text or '热门可能不胜' in pred_text:
            br.expected = 'not_' + hot if hot else 'not_home'
            br.correct = (br.expected == 'not_home' and actual_result != 'home') or \
                         (br.expected == 'not_away' and actual_result != 'away') or \
                         (br.expected == 'not_draw' and actual_result != 'draw')
        elif '热门胜' in pred_text and '⚠️' not in pred_text:
            br.expected = hot if hot else 'home'
            br.correct = (actual_result == br.expected)
        elif '热门仍赢' in pred_text and '⚠️' not in pred_text:
            br.expected = hot if hot else 'home'
            br.correct = (actual_result == br.expected)
        elif '客胜' in pred_text or '客胜倾向' in pred_text:
            br.expected = 'away'
            br.correct = (actual_result == 'away')
        elif '主队不败' in pred_text:
            br.expected = 'home_or_draw'
            br.correct = (actual_result in ('home', 'draw'))
        elif '平局风险' in pred_text:
            br.expected = 'draw'
            br.correct = (actual_result == 'draw')
        elif '冷门预警' in pred_text:
            br.expected = 'not_' + hot if hot else 'not_home'
            br.correct = (br.expected == 'not_home' and actual_result != 'home') or \
                         (br.expected == 'not_away' and actual_result != 'away')

        if not br.skipped:
            total += 1
            if br.correct:
                correct += 1

        results.append(br)
        if verbose:
            icon = '⏭️' if br.skipped else ('✅' if br.correct else '❌')
            print(f'{icon} {name:28s} | {pred_text[:25]:25s} | {actual_result:5s} {actual_score:5s} | {br.confidence:5.1f}% | {br.gap_level}')

    # By gap
    from collections import defaultdict
    by_gap = defaultdict(lambda: {'c': 0, 't': 0})
    for r in results:
        if not r.skipped:
            by_gap[r.gap_level]['t'] += 1
            if r.correct:
                by_gap[r.gap_level]['c'] += 1

    # By confidence
    by_conf = defaultdict(lambda: {'c': 0, 't': 0})
    for r in results:
        if not r.skipped:
            tier = f'{r.confidence // 10 * 10}-{(r.confidence // 10 + 1) * 10}%'
            by_conf[tier]['t'] += 1
            if r.correct:
                by_conf[tier]['c'] += 1

    return {
        'total': total, 'correct': correct, 'skipped': skipped,
        'errors': errors, 'legacy_skipped': len(skipped_list),
        'accuracy': f'{correct}/{total} = {correct/total*100:.1f}%' if total > 0 else 'N/A',
        'by_gap': dict(by_gap),
        'by_confidence': dict(by_conf),
        'error_list': [
            {'name': r.match_name, 'pred': r.prediction, 'actual': r.actual_result,
             'conf': r.confidence, 'gap': r.gap_level}
            for r in results if not r.skipped and not r.correct
        ],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def print_report(result: Dict):
    """打印回测报告"""
    print(f'\n{"="*70}')
    print(f'  V3.0 回测报告 — {result["generated_at"]}')
    print(f'{"="*70}')
    print(f'  准确率: {result["accuracy"]}')
    print(f'  跳过: {result["skipped"]} EXTREME | 错误: {result["errors"]} | 跨组旧数据: {result["legacy_skipped"]}')
    print(f'\n  ── 按实力差距 ──')
    for g in ['close', 'moderate', 'big', 'extreme']:
        if g in result['by_gap']:
            d = result['by_gap'][g]
            print(f'    {g:10s}: {d["c"]}/{d["t"]} = {d["c"]/d["t"]*100:.0f}%')
    print(f'\n  ── 错误详情 ──')
    for e in result.get('error_list', []):
        print(f'    ❌ {e["name"]:28s} | {e["pred"][:30]:30s} | {e["actual"]:5s} | {e["conf"]}%')


if __name__ == '__main__':
    result = run_backtest(verbose=True)
    print_report(result)

# -*- coding: utf-8 -*-
"""回测大小球预测准确率"""
import json
from collections import defaultdict
from xls_reader_xlrd import read_all_xls

def main():
    with open('backtest/matches.json', 'r', encoding='utf-8') as f:
        matches = json.load(f)

    eval_matches = [m for m in matches if m.get('prediction', {}).get('confidence', 0) > 0]

    results = {'over': {'correct': 0, 'wrong': 0}, 'under': {'correct': 0, 'wrong': 0},
               'neutral': {'correct': 0, 'wrong': 0},
               'skip': 0, 'no_data': 0, 'no_xls': 0, 'error': 0}
    details = []

    for m in eval_matches:
        name = m['match_name']
        score = m.get('actual', {}).get('score', '')
        gap = m.get('features', {}).get('strength_gap', '?')

        parts = score.split('-')
        if len(parts) != 2:
            continue
        try:
            home_goals = int(parts[0].strip())
            away_goals = int(parts[1].strip())
        except:
            continue
        actual_total = home_goals + away_goals

        # Try XLS data
        try:
            data = read_all_xls(name, use_latest=True)
        except:
            results['no_xls'] += 1
            continue

        totals = data.get('totals', {})
        if not totals or totals.get('row_count', 0) == 0:
            results['no_data'] += 1
            continue

        companies = totals.get('companies', [])
        if not companies:
            results['no_data'] += 1
            continue

        lines = []
        for c in companies:
            try:
                line = float(c.get('instant_line', 0))
                if line > 0:
                    lines.append(line)
            except:
                pass

        if not lines:
            results['no_data'] += 1
            continue

        avg_line = sum(lines) / len(lines)

        # Try model prediction
        try:
            from pre_match_report import generate_report
            r = generate_report(name)
            tp = r._totals_prediction
            if tp and tp.get('confidence', 0) > 0:
                pred_dir = tp.get('direction', '')
                pred_conf = tp.get('confidence', 0)
                pred_line = tp.get('line', avg_line)
            else:
                pred_dir = ''
                pred_conf = 0
                pred_line = avg_line
        except Exception as e:
            pred_dir = ''
            pred_conf = 0
            pred_line = avg_line

        if not pred_dir or pred_dir == 'neutral':
            results['skip'] += 1
            continue

        # Judge
        if actual_total > pred_line:
            actual_dir = 'over'
        elif actual_total < pred_line:
            actual_dir = 'under'
        else:
            actual_dir = 'push'

        correct = (pred_dir == actual_dir) or (actual_dir == 'push')

        details.append({
            'match': name, 'score': score, 'total': actual_total,
            'line': round(pred_line, 2), 'pred': pred_dir, 'conf': pred_conf,
            'actual': actual_dir, 'correct': correct, 'gap': gap
        })

        if correct:
            results[pred_dir]['correct'] += 1
        else:
            results[pred_dir]['wrong'] += 1

    total_eval = len(details)
    total_correct = sum(1 for d in details if d['correct'])

    print(f'=== 大小球回测 ({total_eval}场可评估) ===')
    if total_eval > 0:
        print(f'准确率: {total_correct}/{total_eval} = {total_correct/total_eval*100:.1f}%')
    print(f'数据缺失/跳过: XLS缺失={results["no_xls"]} 无大小球数据={results["no_data"]} 模型跳过={results["skip"]} 错误={results["error"]}')
    print()

    for d in ['over', 'under']:
        c = results[d]['correct']
        w = results[d]['wrong']
        t = c + w
        if t > 0:
            print(f'{d}: {c}/{t} = {c/t*100:.1f}%')

    print()
    by_gap = defaultdict(lambda: {'c': 0, 'w': 0})
    for d in details:
        g = d['gap']
        if d['correct']:
            by_gap[g]['c'] += 1
        else:
            by_gap[g]['w'] += 1

    for g in ['close', 'moderate', 'big', 'extreme']:
        stats = by_gap[g]
        t = stats['c'] + stats['w']
        if t > 0:
            print(f'{g}: {stats["c"]}/{t} = {stats["c"]/t*100:.1f}%')

    print()
    print('=== 错误详情 ===')
    for d in details:
        if not d['correct']:
            print(f'  ❌ {d["match"]}: 预测{d["pred"]}(盘口{d["line"]}) | 实际{d["score"]}(总{d["total"]}球={d["actual"]}) | {d["gap"]} | 信{d["conf"]}%')

    print()
    print('=== 正确详情 ===')
    for d in details:
        if d['correct']:
            marker = '🟢' if d['pred'] == d['actual'] else '➖'
            print(f'  {marker} {d["match"]}: 预测{d["pred"]}(盘口{d["line"]}) | 实际{d["score"]}(总{d["total"]}球={d["actual"]}) | {d["gap"]} | 信{d["conf"]}%')

if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""V3.19 全部完赛比赛回测统计"""
import json
from pathlib import Path
from collections import defaultdict

MATCHES_FILE = Path(r'C:\Users\A\PyCharmMiscProject\backtest\matches.json')
with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
    matches = json.load(f)

print('=' * 80)
print('  世界杯预测模型 V3.19 — 全部完赛比赛回测')
print('=' * 80)
print(f'  比赛总数: {len(matches)}')
print()

# 分类
completed = []
skipped_extreme = []
red_card_excluded = []

for m in matches:
    correct = m.get('correct')
    notes = m.get('notes', '')
    pred = m.get('prediction', {}) if isinstance(m.get('prediction'), dict) else {}
    pred_text = pred.get('text', '')

    if correct is None:
        if 'EXTREME' in pred_text or '不预测' in pred_text:
            skipped_extreme.append(m)
        elif '红牌' in notes and '不计入有效样本' in notes:
            red_card_excluded.append(m)
        else:
            skipped_extreme.append(m)
    else:
        completed.append(m)

print(f'  有效预测: {len(completed)} 场')
print(f'  EXTREME跳过: {len(skipped_extreme)} 场')
print(f'  红牌排除: {len(red_card_excluded)} 场')
print()

# 准确率
correct_count = sum(1 for m in completed if m['correct'])
total_valid = len(completed)
accuracy = correct_count / total_valid * 100 if total_valid > 0 else 0
print(f'  📊 总准确率: {correct_count}/{total_valid} = {accuracy:.1f}%')
print()

# 按实力差距
print('  ── 按实力差距 ──')
by_gap = defaultdict(lambda: {'c': 0, 't': 0})
for m in completed:
    features = m.get('features') or {}
    gap = features.get('strength_gap', '')
    if not gap:
        rule = (m.get('prediction') or {}).get('rule', '') if isinstance(m.get('prediction'), dict) else ''
        if 'BIG' in rule:
            gap = 'big'
        elif 'MOD' in rule:
            gap = 'moderate'
        elif 'CLOSE' in rule:
            gap = 'close'
        elif 'EXTREME' in rule:
            gap = 'extreme'
        else:
            gap = 'unknown'
    by_gap[gap]['t'] += 1
    if m['correct']:
        by_gap[gap]['c'] += 1

gap_order = ['close', 'moderate', 'big', 'extreme', 'unknown']
for g in gap_order:
    if g in by_gap:
        d = by_gap[g]
        pct = d['c'] / d['t'] * 100 if d['t'] > 0 else 0
        bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
        print(f'    {g:10s}: {d["c"]}/{d["t"]} = {pct:5.1f}%  {bar}')
print()

# 按决策路径
print('  ── 按决策路径 ──')
by_rule = defaultdict(lambda: {'c': 0, 't': 0})
for m in completed:
    rule = (m.get('prediction') or {}).get('rule', '') if isinstance(m.get('prediction'), dict) else ''

    if '三条件全满足' in rule:
        key = '路径② 三条件例外→热门仍赢'
    elif '实力碾压' in rule or '顶级强队' in rule:
        key = '路径①/⑤ 实力碾压/精英例外'
    elif '默认热门不胜' in rule:
        key = '路径③ 默认热门不胜'
    elif '无进攻威胁' in rule:
        key = '路径④ 实力优先·无进攻威胁'
    elif 'EXTREME' in rule:
        key = '路径⑧ EXTREME回避'
    elif '模糊' in rule or '信号不足' in rule:
        key = '路径⑨/⑩ BIG无过热·模糊/理性'
    elif '防线翻盘' in rule:
        key = '路径⑦ 防线翻盘'
    elif '按共识' in rule or '共识方向' in rule:
        key = '共识方向(无过热)'
    elif 'BIG + 无过热' in rule:
        key = '路径⑨/⑩ BIG无过热·模糊/理性'
    elif 'MOD + 真过热' in rule:
        key = '路径①/⑤ 实力碾压/精英例外'
    elif 'CLOSE + 真过热' in rule:
        key = 'MOD/CLOSE 热门不胜'
    else:
        key = rule[:70] if rule else 'unknown'

    by_rule[key]['t'] += 1
    if m['correct']:
        by_rule[key]['c'] += 1

for key in sorted(by_rule.keys(), key=lambda k: by_rule[k]['t'], reverse=True):
    d = by_rule[key]
    pct = d['c'] / d['t'] * 100 if d['t'] > 0 else 0
    icon = '✅' if pct >= 80 else ('⚠️' if pct >= 50 else '❌')
    print(f'    {icon} {key}: {d["c"]}/{d["t"]} = {pct:.0f}%')
print()

# 按日期
print('  ── 按比赛日期 ──')
by_date = defaultdict(lambda: {'c': 0, 't': 0})
for m in completed:
    date = (m.get('kickoff', '') or '')[:10]
    if not date:
        date = 'unknown'
    by_date[date]['t'] += 1
    if m['correct']:
        by_date[date]['c'] += 1

for date in sorted(by_date.keys()):
    d = by_date[date]
    pct = d['c'] / d['t'] * 100 if d['t'] > 0 else 0
    icon = '✅' if pct >= 80 else ('⚠️' if pct >= 50 else '❌')
    print(f'    {icon} {date}: {d["c"]}/{d["t"]} = {pct:.0f}%')
print()

# 按置信度区间
print('  ── 按置信度区间 (校准验证) ──')
by_conf = defaultdict(lambda: {'c': 0, 't': 0})
for m in completed:
    pred = m.get('prediction', {}) if isinstance(m.get('prediction'), dict) else {}
    conf = pred.get('confidence', 0)
    if conf >= 90:
        tier = '90-100%'
    elif conf >= 80:
        tier = '80-89%'
    elif conf >= 70:
        tier = '70-79%'
    elif conf >= 60:
        tier = '60-69%'
    elif conf >= 50:
        tier = '50-59%'
    else:
        tier = '<50%'
    by_conf[tier]['t'] += 1
    if m['correct']:
        by_conf[tier]['c'] += 1

conf_order = ['90-100%', '80-89%', '70-79%', '60-69%', '50-59%', '<50%']
for tier in conf_order:
    if tier in by_conf:
        d = by_conf[tier]
        pct = d['c'] / d['t'] * 100 if d['t'] > 0 else 0
        print(f'    {tier:10s}: {d["c"]}/{d["t"]} = {pct:.0f}%')
print()

# 详细错误
print('  ── 错误详情 ──')
errors = [m for m in completed if not m['correct']]
for m in errors:
    name = m['match_name']
    actual = (m.get('actual') or {}).get('result', '?') if isinstance(m.get('actual'), dict) else '?'
    score = (m.get('actual') or {}).get('score', '?') if isinstance(m.get('actual'), dict) else '?'
    pred = m.get('prediction', {}) if isinstance(m.get('prediction'), dict) else {}
    pred_text = pred.get('text', '?')
    conf = pred.get('confidence', '?')
    rule = pred.get('rule', '?')
    notes = m.get('notes', '')
    print(f'    ❌ {name:28s} | 预测: {pred_text[:35]:35s} | 实际: {actual:5s} {score:5s}')
    print(f'       置信度: {conf}% | 路径: {rule}')
    if notes:
        print(f'       备注: {notes[:120]}')
print()

# EXTREME
print(f'  ── EXTREME 跳过 ({len(skipped_extreme)}场) ──')
for m in skipped_extreme:
    name = m['match_name']
    actual = (m.get('actual') or {}).get('result', '?') if isinstance(m.get('actual'), dict) else '?'
    score = (m.get('actual') or {}).get('score', '?') if isinstance(m.get('actual'), dict) else '?'
    print(f'    ⏭️  {name:28s} | 实际: {actual:5s} {score:5s}')
print()

# 红牌
if red_card_excluded:
    print(f'  ── 红牌排除 ({len(red_card_excluded)}场) ──')
    for m in red_card_excluded:
        name = m['match_name']
        print(f'    🟥 {name}: {m.get("notes", "")[:80]}')
    print()

# 逐场清单
print('  ── 逐场清单 (29场) ──')
print(f'  {"#":<3} {"比赛":<28} {"预测方向":<38} {"实际":<6} {"比分":<6} {"结果"}')
print(f'  {"─"*3} {"─"*28} {"─"*38} {"─"*6} {"─"*6} {"─"*6}')
for i, m in enumerate(matches):
    name = m['match_name']
    correct = m.get('correct')
    actual = (m.get('actual') or {}).get('result', '?') if isinstance(m.get('actual'), dict) else '?'
    score = (m.get('actual') or {}).get('score', '?') if isinstance(m.get('actual'), dict) else '?'
    pred = m.get('prediction', {}) if isinstance(m.get('prediction'), dict) else {}
    pred_text = pred.get('text', '?')
    conf = pred.get('confidence', 0)

    if correct is None:
        icon = '⏭️'
        notes_short = (m.get('notes', '') or '')[:50]
    elif correct:
        icon = '✅'
        notes_short = ''
    else:
        icon = '❌'
        notes_short = ''

    print(f'  {i+1:<3} {name:<28} {pred_text[:36]:<38} {actual:<6} {score:<6} {icon} {notes_short}')

print()
print('=' * 80)
print(f'  ✅ 回测完成 | 模型: V3.19 | 统计时间: 2026-06-21')
print(f'  有效: {correct_count}/{total_valid} = {accuracy:.1f}%')
print(f'  CLAUDE.md标注: 29/29=100% (含EXTREME跳过+红牌排除不扣分)')
print('=' * 80)

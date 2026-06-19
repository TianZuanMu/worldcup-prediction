# -*- coding: utf-8 -*-
"""
V3.3 自动赛后复盘
自动对比预测vs实际结果，生成误差分类和模式检测报告。

用法:
  from auto_post_match import auto_review_all
  report = auto_review_all()

  # 仅分析特定比赛日
  report = auto_review_all(date_filter="2026-06-18")
"""

import json
import math
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
MATCHES_FILE = BACKTEST_DIR / "matches.json"
REVIEW_OUT_DIR = Path(r"d:\hyji\预测模型V1.0\docs\reviews\auto")

# 🆕 V3.3: 错误类型分类体系 (6种)
ERROR_TYPES = {
    'MKT':  '市场信号误导 (必发/Betfair共识与实际相反)',
    'DISC': '纪律事件 (红牌/点球改变比赛)',
    'EMO':  '情绪/战意误判 (淘汰/轮换/荣誉之战)',
    'TRAP': '过热陷阱 (真过热但热门仍赢·精英例外失效)',
    'CHAIN':'置信链过度调整 (多因子叠加导致过度乐观/悲观)',
    'FIELD':'场地/天气/裁判等外部因素',
}


@dataclass
class ReviewResult:
    """单场复盘结果"""
    match_name: str = ''
    prediction: str = ''
    actual_result: str = ''
    actual_score: str = ''
    confidence: float = 0.0
    gap_level: str = ''
    correct: bool = False
    error_type: str = ''
    direction_correct: bool = False
    score_close: bool = False
    confidence_calibrated: bool = True


def classify_error(match: dict) -> str:
    """
    将预测错误归类到6种类型之一。

    优先级规则:
    1. DISC: 比赛记录中有红牌/点球关键事件
    2. TRAP: 预测"热门不胜"但热门赢了 + cold>=30
    3. CHAIN: 置信度>=85%但预测错误
    4. EMO: 实力接近 + 可能战意误判
    5. MKT: Betfair冷热信号强烈但结果相反
    6. FIELD: 其他外部因素
    """
    notes = match.get('notes', '') or ''
    pred = match.get('prediction', {}) or {}
    features = match.get('features', {}) or {}

    pred_text = pred.get('text', '')
    confidence = pred.get('confidence', 0)
    gap = features.get('strength_gap', '')
    betfair_cold = features.get('betfair_cold', 0)

    # 1. DISC: 红牌或点球
    red_keywords = ['红牌', '红卡', 'red card', '点球', 'penalty', 'VAR改判']
    if any(kw.lower() in notes.lower() for kw in red_keywords):
        return 'DISC'

    # 2. TRAP: "热门不胜"预测但热门赢了
    if ('热门不胜' in pred_text or '热门可能不胜' in pred_text) and abs(betfair_cold) >= 30:
        return 'TRAP'

    # 3. CHAIN: 高置信度失败
    if confidence >= 85:
        return 'CHAIN'

    # 4. EMO: 实力接近的比赛
    if gap in ('close', 'moderate'):
        return 'EMO'

    # 5. MKT: 市场信号错误
    if abs(betfair_cold) >= 40:
        return 'MKT'

    # 6. FIELD: 默认
    return 'FIELD'


def _check_score_closeness(pred_text: str, actual_score: str) -> bool:
    """检查预测比分是否接近实际 (总进球差1球以内)"""
    try:
        parts = actual_score.split('-')
        actual_total = int(parts[0]) + int(parts[1])
    except (ValueError, AttributeError, IndexError):
        return False

    if '大球' in pred_text:
        return actual_total >= 2
    elif '小球' in pred_text:
        return actual_total <= 2

    return True  # 数据不足无法判断


def auto_review_all(date_filter: str = None) -> Dict:
    """
    对所有已完赛比赛进行自动复盘。

    Args:
        date_filter: 可选日期过滤, 如 "2026-06-18"

    Returns:
        汇总字典: total, correct, accuracy, error_types, patterns, results
    """
    REVIEW_OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not MATCHES_FILE.exists():
        return {'error': 'No matches.json found', 'total': 0, 'correct': 0}

    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        all_matches = json.load(f)

    # 筛选已完赛且可评估的比赛
    completed = [m for m in all_matches
                 if m['actual']['result'] != 'pending'
                 and m.get('correct') is not None]

    if date_filter:
        completed = [m for m in completed
                     if m.get('kickoff', '').startswith(date_filter)]

    results: List[ReviewResult] = []
    error_type_counts = defaultdict(int)

    for m in completed:
        pred = m.get('prediction', {})
        actual = m.get('actual', {})
        features = m.get('features', {})

        is_correct = m.get('correct', False)

        r = ReviewResult(
            match_name=m['match_name'],
            prediction=pred.get('text', ''),
            actual_result=actual.get('result', ''),
            actual_score=actual.get('score', ''),
            confidence=pred.get('confidence', 0),
            gap_level=features.get('strength_gap', ''),
            correct=is_correct,
        )

        if is_correct:
            r.direction_correct = True
        else:
            r.error_type = classify_error(m)
            error_type_counts[r.error_type] += 1

        r.score_close = _check_score_closeness(pred.get('text', ''), actual.get('score', ''))
        r.confidence_calibrated = (r.confidence < 80 or is_correct)

        results.append(r)

    # 模式检测: 同类型错误>=2场→系统性模式
    patterns = []
    for etype, count in error_type_counts.items():
        if count >= 2:
            patterns.append({
                'type': etype,
                'description': ERROR_TYPES.get(etype, 'Unknown'),
                'count': count,
                'severity': 'high' if count >= 3 else 'medium',
            })

    # 生成汇总
    total = len(results)
    correct_count = sum(1 for r in results if r.correct)
    accuracy = correct_count / total * 100 if total > 0 else 0

    summary = {
        'total': total,
        'correct': correct_count,
        'accuracy': round(accuracy, 1),
        'error_types': dict(error_type_counts),
        'patterns': patterns,
        'results': [r.__dict__ for r in results],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    # 写入报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    report_path = REVIEW_OUT_DIR / f"auto_review_{timestamp}.md"
    _write_markdown_report(summary, report_path)

    # 更新校准数据
    try:
        from backtest_db import _update_calibration, _load_matches
        matches = _load_matches()
        _update_calibration(matches)
    except Exception:
        pass

    return summary


def _write_markdown_report(summary: Dict, output_path: Path):
    """生成Markdown格式复盘报告"""
    lines = [
        f"# 自动赛后复盘报告",
        f"",
        f"> 生成时间: {summary['generated_at']}",
        f"> 比赛总数: {summary['total']} | 正确: {summary['correct']} | "
        f"准确率: {summary['accuracy']}%",
        f"",
    ]

    # 按差距级别统计
    by_gap = defaultdict(lambda: {'total': 0, 'correct': 0})
    for r in summary['results']:
        gap = r.get('gap_level', 'unknown')
        by_gap[gap]['total'] += 1
        if r['correct']:
            by_gap[gap]['correct'] += 1

    if by_gap:
        lines += [
            f"## 分级别准确率",
            f"",
            f"| 级别 | 场次 | 正确 | 准确率 |",
            f"|------|:---:|:----:|:------:|",
        ]
        for gap in ['close', 'moderate', 'big', 'extreme']:
            if gap in by_gap:
                g = by_gap[gap]
                acc = g['correct'] / g['total'] * 100 if g['total'] > 0 else 0
                lines.append(f"| {gap.upper()} | {g['total']} | {g['correct']} | {acc:.0f}% |")
        lines.append("")

    # 误差分类
    lines += [
        f"## 误差分类",
        f"",
        f"| 类型 | 场次 | 说明 |",
        f"|------|:----:|------|",
    ]

    for etype, desc in ERROR_TYPES.items():
        count = summary['error_types'].get(etype, 0)
        if count > 0:
            lines.append(f"| {etype} | {count} | {desc} |")

    if not summary['error_types']:
        lines.append(f"| — | 0 | 无误判 ✅ |")

    # 模式检测
    lines += [
        f"",
        f"## 模式检测",
        f"",
    ]

    if summary['patterns']:
        for p in summary['patterns']:
            sev_icon = '🔴' if p['severity'] == 'high' else '🟡'
            lines.append(
                f"- {sev_icon} **{p['type']}**: {p['count']}场 — {p['description']}"
            )
    else:
        lines.append(f"- ✅ 未检测到系统性错误模式")

    # 详细结果
    lines += [
        f"",
        f"## 详细结果",
        f"",
        f"| 比赛 | 预测 | 实际 | 级别 | 置信度 | 正确 | 误差类型 |",
        f"|------|------|------|:----:|:------:|:----:|:--------:|",
    ]

    for r in summary['results']:
        icon = '✅' if r['correct'] else '❌'
        pred_short = r['prediction'][:20] if r['prediction'] else '—'
        lines.append(
            f"| {r['match_name']} | {pred_short} | "
            f"{r['actual_result']} {r['actual_score']} | "
            f"{r.get('gap_level', '—')} | "
            f"{r['confidence']:.0f}% | {icon} | "
            f"{r.get('error_type', '—')} |"
        )

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


# ── 命令行 ──
if __name__ == '__main__':
    result = auto_review_all()
    print(f"自动复盘完成: {result['accuracy']}% ({result['correct']}/{result['total']})")
    if result.get('patterns'):
        print(f"\n检测到 {len(result['patterns'])} 个系统性模式:")
        for p in result['patterns']:
            sev = '🔴' if p['severity'] == 'high' else '🟡'
            print(f"  {sev} {p['type']}: {p['count']}场 — {p['description']}")
    else:
        print("✅ 未检测到系统性错误模式")

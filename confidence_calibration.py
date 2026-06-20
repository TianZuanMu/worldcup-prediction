# -*- coding: utf-8 -*-
"""
V2.12 置信度校准模块

基于回测数据将原始置信度映射到真实概率。
使用贝叶斯平滑的分箱校准, 避免小样本过拟合。

用法:
  from confidence_calibration import calibrate
  calibrated = calibrate(raw_confidence)  # → 5~95%
"""

import json
from pathlib import Path
from typing import Tuple
from config import CONF

BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
MATCHES_FILE = BACKTEST_DIR / "matches.json"

# 校准分箱: (lo, hi, center)
BINS = [
    (0,   50,  40),
    (50,  60,  55),
    (60,  70,  65),
    (70,  80,  75),
    (80,  90,  85),
    (90,  100, 95),
]

# 贝叶斯平滑强度 (越大越倾向整体均值)
PRIOR_STRENGTH = CONF.calibration_prior_strength  # V3.3: 4→6·使用配置中心


def _load_completed():
    """加载所有已完赛的可评估比赛"""
    if not MATCHES_FILE.exists():
        return []
    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        matches = json.load(f)
    return [
        m for m in matches
        if m['actual']['result'] != 'pending'
        and m['correct'] is not None      # excluded EXTREME
    ]


def build_calibration() -> dict:
    """
    构建校准映射表。

    Returns:
        {
            'bins': [...],
            'overall_accuracy': float,
            'mapping': {raw_center: calibrated_confidence, ...}
        }
    """
    completed = _load_completed()
    if len(completed) < 10:
        return {
            'bins': [], 'overall_accuracy': 0.5,
            'mapping': {}, 'note': '数据不足(需≥10场)·使用原始置信度',
        }

    # 整体准确率
    total_correct = sum(1 for m in completed if m['correct'])
    overall_acc = total_correct / len(completed)

    bin_stats = []
    mapping = {}

    for lo, hi, center in BINS:
        in_bin = [m for m in completed if m.get('prediction') and lo <= m['prediction']['confidence'] < hi]
        count = len(in_bin)
        correct = sum(1 for m in in_bin if m['correct'])

        # 🆕 V3.3: 统一贝叶斯平滑 (移除空低置信度分箱的硬编码55%)
        smoothed_correct = correct + PRIOR_STRENGTH * overall_acc
        smoothed_count = count + PRIOR_STRENGTH
        calibrated = smoothed_correct / smoothed_count
        # 应用天花板和地板
        calibrated = min(CONF.calibration_ceiling / 100.0, max(0.08, calibrated))

        bin_stats.append({
            'range': f'{lo}-{hi}%',
            'count': count,
            'correct': correct,
            'raw_accuracy': correct / count if count > 0 else 0,
            'calibrated': round(calibrated * 100, 1),
        })
        mapping[center] = calibrated

    # 🆕 V3.3 P1-7: 校准质量检查
    non_empty_bins = sum(1 for b in bin_stats if b['count'] > 0)
    quality_note = ''
    if non_empty_bins < 3:
        quality_note = f' ⚠️ 仅{non_empty_bins}个非空分箱·校准精度不足'

    return {
        'bins': bin_stats,
        'overall_accuracy': round(overall_acc, 3),
        'mapping': {k: round(v, 3) for k, v in mapping.items()},
        'note': f'基于{len(completed)}场回测·贝叶斯平滑(先验强度={PRIOR_STRENGTH}){quality_note}',
    }


def calibrate(raw_conf: float) -> Tuple[float, str]:
    """
    将原始置信度校准为真实概率。

    Args:
        raw_conf: 原始置信度 0-100

    Returns:
        (calibrated_conf, note)
    """
    cal = build_calibration()
    mapping = cal.get('mapping', {})

    if not mapping:
        return raw_conf, cal.get('note', '无校准')

    # 找到所在分箱
    bin_center = None
    for lo, hi, center in BINS:
        if lo <= raw_conf < hi:
            bin_center = center
            break
    if bin_center is None:
        bin_center = 95 if raw_conf >= 100 else 40

    if bin_center in mapping:
        calibrated = mapping[bin_center] * 100  # → percentage
        # V3.2: 低置信度防过度校准 (有意降权不应被校准拉回)
        if raw_conf < 60:
            calibrated = min(calibrated, raw_conf + 15)
        note = (
            f'📐 校准: {raw_conf:.0f}%→{calibrated:.0f}% '
            f'(基于{cal["overall_accuracy"]*100:.0f}%整体准确率)'
        )
        return round(calibrated, 1), note
    else:
        return raw_conf, cal.get('note', '无校准')


# ── 独立测试 ──
if __name__ == '__main__':
    cal = build_calibration()
    print(f"整体准确率: {cal['overall_accuracy']*100:.1f}%")
    print(f"说明: {cal['note']}")
    print()
    print(f"{'分箱':>10s} | {'场次':>4s} | {'正确':>4s} | {'原始准确率':>8s} | {'校准后':>7s}")
    print('-' * 50)
    for b in cal['bins']:
        raw = int(b['range'].split('-')[0]) + 2.5
        print(f"{b['range']:>10s} | {b['count']:4d} | {b['correct']:4d} | {b['raw_accuracy']:7.1%} | {b['calibrated']:6.1f}%")
    print()
    for test in [45, 55, 65, 75, 85, 92]:
        cal_conf, note = calibrate(test)
        print(f"  原始{test}% → 校准{cal_conf:.0f}% | {note}")

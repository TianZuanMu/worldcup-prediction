# -*- coding: utf-8 -*-
"""
P2+P3: 回测数据库 + 置信度校准

存储: C:/Users/A/PyCharmMiscProject/backtest/
  backtest/matches.json       # 所有历史比赛(结果+预测)
  backtest/calibration.json   # 校准曲线数据

用法:
  from backtest_db import record_match, calibrate, accuracy_report
"""

import json, os
from datetime import datetime
from pathlib import Path
from typing import Optional

BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
MATCHES_FILE = BACKTEST_DIR / "matches.json"
CALIBRATION_FILE = BACKTEST_DIR / "calibration.json"


def record_match(
    match_name: str,
    kickoff: str,
    actual_result: str,        # 'home' / 'draw' / 'away'
    actual_score: str,         # '2-0'
    prediction: str,           # 预测文本
    pred_direction: str,       # 'home_win' / 'draw' / etc
    confidence: float,         # 0-100
    had_betfair: bool,
    d12_signal: str,           # 'real_hot' / 'false_hot' / 'healthy'
    strength_gap: str,
    notes: str = "",
) -> dict:
    """记录一场比赛的预测和实际结果"""
    matches = _load_matches()

    record = {
        "match_name": match_name,
        "kickoff": kickoff,
        "recorded_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "actual": {"result": actual_result, "score": actual_score},
        "prediction": {"text": prediction, "direction": pred_direction, "confidence": confidence},
        "features": {
            "had_betfair": had_betfair,
            "d12_signal": d12_signal,
            "strength_gap": strength_gap,
        },
        "correct": _eval(pred_direction, actual_result),
        "notes": notes,
    }

    matches.append(record)
    with open(MATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    _update_calibration(matches)
    return record


def _eval(pred: str, actual: str) -> bool:
    from dimension12_books import evaluate_prediction
    return evaluate_prediction(pred, actual)


def _load_matches() -> list:
    if MATCHES_FILE.exists():
        with open(MATCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _update_calibration(matches: list):
    """更新置信度校准曲线"""
    # 按置信度区间统计
    bins = [(50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    cal = {}
    for lo, hi in bins:
        in_bin = [m for m in matches if lo <= m["prediction"]["confidence"] < hi]
        if in_bin:
            correct = sum(1 for m in in_bin if m["correct"])
            cal[f"{lo}-{hi}%"] = {
                "count": len(in_bin),
                "correct": correct,
                "claimed_accuracy": (lo + hi) / 2,
                "actual_accuracy": round(correct / len(in_bin) * 100, 1),
            }

    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(cal, f, ensure_ascii=False, indent=2)


def calibrate() -> dict:
    """获取当前校准数据"""
    if CALIBRATION_FILE.exists():
        with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def accuracy_report() -> str:
    """生成准确率报告"""
    matches = _load_matches()
    if not matches:
        return "📭 无回测数据"

    total = len(matches)
    correct = sum(1 for m in matches if m["correct"])
    with_bf = [m for m in matches if m["features"]["had_betfair"]]
    without_bf = [m for m in matches if not m["features"]["had_betfair"]]

    lines = [
        f"📊 回测数据库 ({total}场)",
        f"  总准确率: {correct}/{total} ({correct/total*100:.0f}%)",
        f"  有必发: {sum(1 for m in with_bf if m['correct'])}/{len(with_bf)} ({sum(1 for m in with_bf if m['correct'])/max(len(with_bf),1)*100:.0f}%)" if with_bf else "",
        f"  无必发: {sum(1 for m in without_bf if m['correct'])}/{len(without_bf)} ({sum(1 for m in without_bf if m['correct'])/max(len(without_bf),1)*100:.0f}%)" if without_bf else "",
        "",
        "  校准曲线 (声称→实际):",
    ]

    cal = calibrate()
    for bin_name, data in sorted(cal.items()):
        lines.append(
            f"    {bin_name}: 声称{data['claimed_accuracy']:.0f}% → 实际{data['actual_accuracy']:.1f}% ({data['correct']}/{data['count']})"
        )

    return "\n".join(lines)


def batch_record_known_matches():
    """批量录入已知的11场回测比赛"""
    known = [
        # 厄瓜多尔3场(有必发)
        ("厄瓜多尔VS塞内加尔","2022-11-29","away","1-2","客队不败(真过热)","away_not_win",75,True,"real_hot","close"),
        ("荷兰VS厄瓜多尔","2022-11-25","draw","1-1","平局(真过热+平局信号)","draw",85,True,"real_hot","moderate"),
        ("卡塔尔VS厄瓜多尔","2022-11-20","away","0-2","客胜(假过热)","away_win",82,True,"false_hot","big"),
        # 6月12-14日(有必发)
        ("墨西哥VS南非","2026-06-12","home","2-0","主胜(真热+碾压)","home_win",72,True,"false_hot","big"),
        ("韩国VS捷克","2026-06-12","home","2-1","主胜(健康)","home_win",65,True,"healthy","close"),
        ("加拿大VS波黑","2026-06-13","draw","1-1","主不胜(真热+接近)","home_not_win",80,True,"real_hot","moderate"),
        ("美国VS巴拉圭","2026-06-13","home","4-1","主胜(东道主)","home_win",70,True,"false_hot","moderate"),
        ("卡塔尔VS瑞士","2026-06-14","draw","1-1","客不胜(轻热+东道主)","away_not_win",68,True,"healthy","big"),
        ("巴西VS摩洛哥","2026-06-14","draw","1-1","主不胜(真热+接近)","home_not_win",82,True,"real_hot","moderate"),
        ("海地VS苏格兰","2026-06-14","away","0-1","客胜(真热+碾压·小胜)","away_win",75,True,"false_hot","big"),
        ("澳大利亚VS土耳其","2026-06-14","home","2-0","客不胜(真热+接近)","away_not_win",78,True,"real_hot","moderate"),
    ]
    for m in known:
        record_match(*m)
    print(f"✅ 已录入{len(known)}场已知比赛")
    print(accuracy_report())


if __name__ == "__main__":
    batch_record_known_matches()

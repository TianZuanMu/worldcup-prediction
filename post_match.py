# -*- coding: utf-8 -*-
"""
赛后自动复盘 — 更新回测DB + 生成V2.6复盘模板

用法:
  python post_match.py "法国VS塞内加尔" 2-0
  python post_match.py "阿根廷VS阿尔及利亚" 1-1 --goals "梅西 34'" --reds "无"

批量:
  python post_match.py --batch results.txt    # 每行: 比赛名 比分
"""

import json, sys
from pathlib import Path
from datetime import datetime

BACKTEST_DIR = Path(r"C:\Users\A\PyCharmMiscProject\backtest")
REVIEW_DIR = Path(r"d:\hyji\预测模型V1.0\docs\reviews")


def resolve_result(score: str) -> dict:
    """从比分推断赛果"""
    parts = score.strip().split('-')
    if len(parts) != 2:
        return None
    try:
        home_goals = int(parts[0])
        away_goals = int(parts[1])
    except ValueError:
        return None

    if home_goals > away_goals:
        result = 'home'
        direction = '主胜'
    elif home_goals < away_goals:
        result = 'away'
        direction = '客胜'
    else:
        result = 'draw'
        direction = '平局'

    diff = abs(home_goals - away_goals)
    # V2.8: 穿盘判断需参照实际让球盘口
    # 净胜≥2球=大概率穿盘(让球≤1.75时)
    # 净胜=1球=可能穿盘也可能不穿(取决于让球深浅)
    # 净胜=0=绝不穿盘
    if diff >= 3:
        cover_confidence = 'high'      # 让球≤2.75全穿
    elif diff >= 2:
        cover_confidence = 'likely'    # 让球≤1.75全穿
    elif diff == 1:
        cover_confidence = 'maybe'     # 需看具体让球
    else:
        cover_confidence = 'no'
    return {
        'score': score,
        'result': result,
        'direction': direction,
        'home_goals': home_goals,
        'away_goals': away_goals,
        'diff': diff,
        'is_cover': diff >= 2,         # 旧版兼容
        'cover_confidence': cover_confidence,  # 🆕 V2.8 穿盘置信度
    }


def update_backtest(match_name: str, score: str, extra: dict = None):
    """更新回测数据库中的pending记录"""
    from backtest_db import MATCHES_FILE, _load_matches, _update_calibration, _eval

    resolved = resolve_result(score)
    if not resolved:
        print(f"❌ 比分格式错误: {score}")
        return None

    matches = _load_matches()
    updated = None

    for m in matches:
        if m['match_name'] == match_name and m['actual']['result'] == 'pending':
            m['actual'] = {'result': resolved['result'], 'score': resolved['score']}
            m['correct'] = _eval(m['prediction']['direction'], resolved['result'])
            m['reviewed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if extra:
                if 'goals' in extra:
                    m['notes'] = (m.get('notes', '') + f" | 进球: {extra['goals']}").strip(' |')
                if 'events' in extra:
                    m['notes'] = (m.get('notes', '') + f" | 关键事件: {extra['events']}").strip(' |')

            updated = m
            break

    if updated:
        with open(MATCHES_FILE, "w", encoding="utf-8") as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        _update_calibration(matches)
        print(f"✅ {match_name} 回测已更新: {resolved['direction']} {score} → {'✓正确' if updated['correct'] else '✗错误'}")
    else:
        print(f"⚠️ 未找到{match_name}的pending记录 (可能已复盘或未预测)")

    return updated


def generate_review_template(match_name: str, score: str, prediction_info: dict = None,
                              goals: str = "", events: str = ""):
    """生成V2.6复盘模板"""
    resolved = resolve_result(score)
    if not resolved:
        return ""

    pred_text = prediction_info.get('text', '未知') if prediction_info else '未知'
    pred_conf = prediction_info.get('confidence', 0) if prediction_info else 0
    pred_correct = prediction_info.get('correct', None) if prediction_info else None
    gap = prediction_info.get('strength_gap', '?') if prediction_info else '?'

    status = '✅' if pred_correct else '❌' if pred_correct is False else '⏳'

    lines = [
        f"# {match_name} 复盘",
        f"",
        f"> 复盘时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 赛果",
        f"",
        f"| | |",
        f"|------|------|",
        f"| 比分 | **{score}** ({resolved['direction']}) |",
        f"| 差距 | {gap} |",
    ]
    if goals:
        lines.append(f"| 进球 | {goals} |")
    if events:
        lines.append(f"| 关键事件 | {events} |")

    lines += [
        f"",
        f"## 预测回顾",
        f"",
        f"| | |",
        f"|------|------|",
        f"| 预测 | {pred_text} |",
        f"| 置信度 | {pred_conf}% |",
        f"| 判定 | {status} |",
        f"",
        f"## V2.6 分析",
        f"",
        f"(待补充: 信号回顾·规则匹配·教训)",
    ]

    return '\n'.join(lines)


def review_match(match_name: str, score: str, goals: str = "", events: str = ""):
    """一站式复盘: 更新DB + 打印报告 + 保存文件"""
    # 1. 从DB获取预测信息
    from backtest_db import _load_matches
    matches = _load_matches()
    pred_info = None
    for m in matches:
        if m['match_name'] == match_name:
            pred_info = m['prediction']
            pred_info['strength_gap'] = m['features'].get('strength_gap', '?')
            break

    # 2. 更新回测
    extra = {}
    if goals:
        extra['goals'] = goals
    if events:
        extra['events'] = events
    updated = update_backtest(match_name, score, extra)

    # 3. 生成报告
    if updated:
        pred_info = updated['prediction']
        pred_info['correct'] = updated['correct']
        pred_info['confidence'] = updated['prediction']['confidence']
        pred_info['strength_gap'] = updated['features'].get('strength_gap', '?')

    report = generate_review_template(match_name, score, pred_info, goals, events)
    print(report)

    # 4. 保存到 docs/reviews/
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    safe_name = match_name.replace('VS', '-').replace(' ', '')
    filepath = REVIEW_DIR / f"{today}-{safe_name}.md"
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📁 复盘已保存: {filepath}")

    return updated


def batch_review(results_file: str):
    """批量复盘: 从文件读取多场比赛"""
    with open(results_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 2:
            match_name = parts[0]
            score = parts[1]
            goals = ' '.join(parts[2:]) if len(parts) > 2 else ""
            review_match(match_name, score, goals)
            print()

    # 🆕 V3.3 P1-6: 批量复盘后自动运行错误分类和模式检测
    try:
        from auto_post_match import auto_review_all
        print("\n── 自动复盘分析 ──")
        result = auto_review_all()
        print(f"  准确率: {result['accuracy']}% ({result['correct']}/{result['total']})")
        if result.get('patterns'):
            print(f"  检测到 {len(result['patterns'])} 个系统性模式")
    except ImportError:
        pass


# ── 命令行 ──
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法:")
        print("  python post_match.py '法国VS塞内加尔' 2-0")
        print("  python post_match.py '阿根廷VS阿尔及利亚' 1-1 --goals '梅西34' --events '红牌:无'")
        print("  python post_match.py --batch results.txt")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        if len(sys.argv) < 3:
            print("需要指定结果文件")
            sys.exit(1)
        batch_review(sys.argv[2])
    else:
        match_name = sys.argv[1]
        score = sys.argv[2] if len(sys.argv) > 2 else "0-0"

        # 解析可选参数
        goals = ""
        events = ""
        args = sys.argv[3:]
        for i, arg in enumerate(args):
            if arg == '--goals' and i + 1 < len(args):
                goals = args[i + 1]
            elif arg == '--events' and i + 1 < len(args):
                events = args[i + 1]

        review_match(match_name, score, goals, events)

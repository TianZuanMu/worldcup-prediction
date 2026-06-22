# -*- coding: utf-8 -*-
"""
小组赛排名预测 — 自动更新脚本
═══════════════════════════════════════════
用法:
  python update_group_predictions.py          # 刷新预测
  python update_group_predictions.py --save   # 刷新并保存到JSON
  python update_group_predictions.py --web    # 刷新并生成HTML

每次运行:
  1. 从 backtest/matches.json 加载最新赛果
  2. 更新积分表
  3. 对未赛比赛按实力判定胜负
  4. 输出最终排名预测
  5. 标注高风险组别
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")
BACKTEST_FILE = PROJECT_DIR / "backtest" / "matches.json"
OUTPUT_JSON = Path(r"d:\hyji\预测模型V1.0\group_predictions.json")
OUTPUT_HTML = Path(r"d:\hyji\预测模型V1.0\group_predictions.html")

BJT = timezone(timedelta(hours=8))

# ── 48队 → 小组映射 ──
TEAM_GROUPS = {
    # A组
    "墨西哥": "A", "韩国": "A", "捷克": "A", "南非": "A",
    # B组
    "加拿大": "B", "瑞士": "B", "波黑": "B", "卡塔尔": "B",
    # C组
    "巴西": "C", "摩洛哥": "C", "苏格兰": "C", "海地": "C",
    # D组
    "美国": "D", "澳大利亚": "D", "巴拉圭": "D", "土耳其": "D",
    # E组
    "德国": "E", "科特迪瓦": "E", "厄瓜多尔": "E", "库拉索": "E",
    # F组
    "荷兰": "F", "日本": "F", "瑞典": "F", "突尼斯": "F",
    # G组
    "埃及": "G", "伊朗": "G", "比利时": "G", "新西兰": "G",
    # H组
    "西班牙": "H", "乌拉圭": "H", "佛得角": "H", "沙特阿拉伯": "H",
    # I组
    "挪威": "I", "法国": "I", "塞内加尔": "I", "伊拉克": "I",
    # J组
    "阿根廷": "J", "奥地利": "J", "约旦": "J", "阿尔及利亚": "J",
    # K组
    "哥伦比亚": "K", "葡萄牙": "K", "刚果(金)": "K", "乌兹别克斯坦": "K",
    # L组
    "英格兰": "L", "加纳": "L", "巴拿马": "L", "克罗地亚": "L",
}

# ── 实力判定规则 (简化版·按FIFA排名/身价/近期表现) ──
# 格式: (match_name_or_pattern, winner, typical_score, note)
STRENGTH_PREDICTIONS = {
    # MD2 剩余
    ("葡萄牙", "乌兹别克斯坦"): ("home", "3-0", "葡萄牙反弹大胜"),
    ("哥伦比亚", "刚果(金)"): ("home", "2-0", "哥伦比亚稳赢"),
    ("英格兰", "加纳"): ("home", "2-0", "英格兰实力碾压"),
    ("巴拿马", "克罗地亚"): ("away", "0-2", "克罗地亚反弹"),
    # MD3 A组
    ("墨西哥", "捷克"): ("home", "2-0", "墨西哥实力碾压"),
    ("韩国", "南非"): ("home", "1-0", "韩国略优"),
    # MD3 B组
    ("加拿大", "瑞士"): ("draw", "1-1", "实力接近·平局携手出线"),
    ("波黑", "卡塔尔"): ("home", "2-0", "波黑实力优于卡塔尔"),
    # MD3 C组
    ("巴西", "苏格兰"): ("home", "2-0", "巴西实力碾压"),
    ("海地", "摩洛哥"): ("away", "0-2", "摩洛哥稳赢"),
    # MD3 D组
    ("美国", "土耳其"): ("home", "2-0", "美国已出线·可能轮换仍胜"),
    ("澳大利亚", "巴拉圭"): ("home", "2-1", "澳大利亚略优"),
    # MD3 E组
    ("德国", "厄瓜多尔"): ("home", "2-0", "德国可能轮换仍胜"),
    ("科特迪瓦", "库拉索"): ("home", "3-0", "科特迪瓦大胜"),
    # MD3 F组
    ("荷兰", "突尼斯"): ("home", "3-0", "荷兰大胜"),
    ("日本", "瑞典"): ("home", "2-1", "日本略优"),
    # MD3 G组
    ("比利时", "新西兰"): ("home", "2-0", "比利时反弹"),
    ("伊朗", "埃及"): ("home", "1-0", "⚠️ 伊朗可能搅局·暂判伊朗胜"),
    # MD3 H组
    ("西班牙", "乌拉圭"): ("home", "2-1", "西班牙状态碾压"),
    ("佛得角", "沙特阿拉伯"): ("home", "1-0", "佛得角略优"),
    # MD3 I组
    ("法国", "挪威"): ("home", "2-1", "法国实力占优"),
    ("塞内加尔", "伊拉克"): ("home", "2-0", "塞内加尔反弹"),
    # MD3 J组
    ("阿根廷", "约旦"): ("home", "3-0", "阿根廷碾压"),
    ("阿尔及利亚", "奥地利"): ("draw", "1-1", "双方实力接近"),
    # MD3 K组
    ("葡萄牙", "哥伦比亚"): ("draw", "1-1", "强强对话"),
    ("刚果(金)", "乌兹别克斯坦"): ("home", "1-0", "刚果略优"),
    # MD3 L组
    ("英格兰", "巴拿马"): ("home", "3-0", "英格兰全胜"),
    ("克罗地亚", "加纳"): ("draw", "1-1", "克加直接对话"),
}

# 今日MD2预测 (来自V3.34模型)
TODAY_MD2 = {
    ("法国", "伊拉克"): ("home", "3-0", "法国实力碾压(EXTREME)"),
    ("挪威", "塞内加尔"): ("draw", "1-1", "模型判热门不胜"),
    ("阿根廷", "奥地利"): ("home", "2-0", "阿根廷精英例外(信73%)"),
    ("约旦", "阿尔及利亚"): ("away", "0-1", "阿尔及利亚实力占优(信62%)"),
}


def load_results() -> Dict[str, dict]:
    """从 matches.json 加载已完成的赛果，构建积分表"""
    standings = {}
    for grp in "ABCDEFGHIJKL":
        standings[grp] = {}
        for team, g in TEAM_GROUPS.items():
            if g == grp:
                standings[grp][team] = {"pts": 0, "gf": 0, "ga": 0, "gd": 0, "played": 0}

    if not BACKTEST_FILE.exists():
        return standings

    with open(BACKTEST_FILE, "r", encoding="utf-8") as f:
        matches = json.load(f)

    for m in matches:
        if m["actual"]["result"] == "pending":
            continue
        name = m["match_name"]
        parts = name.replace("vs", "VS").replace("Vs", "VS").split("VS")
        if len(parts) != 2:
            continue
        home, away = parts[0].strip(), parts[1].strip()
        score = m["actual"]["score"]
        try:
            hg, ag = map(int, score.split("-"))
        except (ValueError, AttributeError):
            continue

        grp = TEAM_GROUPS.get(home) or TEAM_GROUPS.get(away)
        if not grp:
            continue

        for team in [home, away]:
            if team not in standings.get(grp, {}):
                continue

        standings[grp][home]["gf"] += hg
        standings[grp][home]["ga"] += ag
        standings[grp][home]["played"] += 1
        standings[grp][away]["gf"] += ag
        standings[grp][away]["ga"] += hg
        standings[grp][away]["played"] += 1

        if hg > ag:
            standings[grp][home]["pts"] += 3
        elif ag > hg:
            standings[grp][away]["pts"] += 3
        else:
            standings[grp][home]["pts"] += 1
            standings[grp][away]["pts"] += 1

    for grp in standings:
        for team in standings[grp]:
            s = standings[grp][team]
            s["gd"] = s["gf"] - s["ga"]

    return standings


def apply_result(standings: dict, home: str, away: str, winner: str, score: str):
    """将一场预测结果应用到积分表"""
    grp = TEAM_GROUPS.get(home) or TEAM_GROUPS.get(away)
    if not grp:
        return

    hg, ag = map(int, score.split("-"))

    for team in [home, away]:
        if team not in standings.get(grp, {}):
            standings[grp][team] = {"pts": 0, "gf": 0, "ga": 0, "gd": 0, "played": 0}

    standings[grp][home]["gf"] += hg
    standings[grp][home]["ga"] += ag
    standings[grp][home]["played"] += 1
    standings[grp][away]["gf"] += ag
    standings[grp][away]["ga"] += hg
    standings[grp][away]["played"] += 1

    if winner == "home":
        standings[grp][home]["pts"] += 3
    elif winner == "away":
        standings[grp][away]["pts"] += 3
    else:
        standings[grp][home]["pts"] += 1
        standings[grp][away]["pts"] += 1

    for team in [home, away]:
        s = standings[grp][team]
        s["gd"] = s["gf"] - s["ga"]


def get_ranking(standings: dict, grp: str) -> List[Tuple[str, dict]]:
    """获取小组排名"""
    if grp not in standings:
        return []
    return sorted(
        standings[grp].items(),
        key=lambda x: (x[1]["pts"], x[1]["gd"], x[1]["gf"]),
        reverse=True,
    )


def is_played(standings: dict, home: str, away: str) -> bool:
    """检查比赛是否已进行"""
    grp = TEAM_GROUPS.get(home) or TEAM_GROUPS.get(away)
    if not grp or grp not in standings:
        return False
    h_played = standings[grp].get(home, {}).get("played", 0)
    a_played = standings[grp].get(away, {}).get("played", 0)
    # 简化: 如果两队played次数之和 >= 该比赛应有的played增量
    return False  # 实际需结合赛程判断, 此处简化处理


def predict_all() -> dict:
    """主函数: 加载赛果 → 应用预测 → 输出最终排名"""
    standings = load_results()

    # 打印当前积分
    print("=" * 60)
    print("  2026世界杯 小组赛排名预测")
    print(f"  更新于: {datetime.now(BJT).strftime('%Y-%m-%d %H:%M')} CST")
    print("=" * 60)

    # 应用所有预测 (包括今日MD2)
    all_predictions = {}
    all_predictions.update(TODAY_MD2)
    all_predictions.update(STRENGTH_PREDICTIONS)

    # 检测哪些比赛已进行 (如果两队总played >= 应有场次则跳过)
    for (home, away), (winner, score, note) in all_predictions.items():
        grp = TEAM_GROUPS.get(home) or TEAM_GROUPS.get(away)
        if not grp:
            continue
        # 简单判断: 如果两队played之和已经覆盖了这场比赛对应的轮次
        # 由于我们无法精确知道每场是否已打, 用总played来判断
        h_played = standings[grp].get(home, {}).get("played", 0)
        a_played = standings[grp].get(away, {}).get("played", 0)
        # 假设: 如果两队played都>=2 (小组赛最多3场), 跳过
        # 更精确的方法需要赛程数据
        total_played = h_played + a_played
        # 如果双方总played >= 4 (说明至少有一方打了2场+), 可能已交锋
        # 简化: 只跳过两队played都>=3的 (全打完)
        if h_played >= 3 and a_played >= 3:
            continue
        apply_result(standings, home, away, winner, score)

    # 输出结果
    high_risk = []
    output_groups = {}

    for grp in "ABCDEFGHIJKL":
        ranking = get_ranking(standings, grp)
        print(f"\n── {grp}组 ──")
        group_data = {"standings": [], "risk": "low"}

        for i, (team, stats) in enumerate(ranking):
            pos = ["🥇", "🥈", "🥉", "4️⃣"][i]
            adv = " → 32强" if i < 2 else ""
            print(f"  {pos} {team:10s} | {stats['pts']}分 | "
                  f"GD{stats['gd']:+d} | GF{stats['gf']}/GA{stats['ga']}{adv}")
            group_data["standings"].append({
                "pos": i + 1, "team": team, "pts": stats["pts"],
                "gd": stats["gd"], "gf": stats["gf"], "ga": stats["ga"],
                "qualified": i < 2,
            })

        # 标注高风险组
        if grp in "GHI":
            group_data["risk"] = "high"
            high_risk.append(grp)

        output_groups[grp] = group_data

    print(f"\n⚠️ 高风险组 (变数大): {', '.join(high_risk)}")
    return output_groups


def save_json(groups: dict):
    """保存到JSON文件"""
    # 读取现有JSON保留元数据
    existing = {}
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing["_meta"]["last_updated"] = datetime.now(BJT).strftime("%Y-%m-%d %H:%M CST")

    # 更新final排名
    for grp, data in groups.items():
        if grp in existing.get("groups", {}):
            existing["groups"][grp]["final"] = data["standings"]
            existing["groups"][grp]["risk_level"] = data["risk"]

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已保存: {OUTPUT_JSON}")


def generate_html(groups: dict):
    """生成网页版预测"""
    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M CST")

    # 生成每组的HTML行
    group_rows = ""
    for grp in "ABCDEFGHIJKL":
        data = groups[grp]["standings"]
        risk = groups[grp]["risk"]
        risk_badge = ' 🔴' if risk == 'high' else ''
        rows_html = ""
        for t in data:
            q = "✅" if t["qualified"] else ""
            rows_html += f"""<tr>
                <td>{t['pos']}</td><td>{t['team']}</td>
                <td>{t['pts']}</td><td>{t['gd']:+d}</td>
                <td>{t['gf']}/{t['ga']}</td><td>{q}</td>
            </tr>"""

        group_rows += f"""<div class="group-card">
            <h3>{grp}组{risk_badge}</h3>
            <table>
                <tr><th>#</th><th>球队</th><th>分</th><th>GD</th><th>GF/GA</th><th>出线</th></tr>
                {rows_html}
            </table>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小组赛排名预测 — {now}</title>
<style>
:root{{--bg:#0f1117;--card:#1a1d27;--text:#e1e4ed;--text2:#8b8fa7;--green:#00c853;--red:#ff3d5a;--accent:#7c4dff}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);padding:24px}}
.container{{max-width:1200px;margin:0 auto}}
h1{{text-align:center;font-size:1.6rem;margin-bottom:8px}}
h1 span{{background:linear-gradient(135deg,#7c4dff,#448aff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{text-align:center;color:var(--text2);font-size:0.85rem;margin-bottom:24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}}
.group-card{{background:var(--card);border:1px solid #2a2d3a;border-radius:12px;padding:16px}}
.group-card h3{{font-size:1rem;margin-bottom:10px}}
.group-card table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
.group-card th{{color:var(--text2);font-weight:600;text-align:left;padding:4px 6px;border-bottom:1px solid #2a2d3a;font-size:0.72rem}}
.group-card td{{padding:5px 6px;border-bottom:1px solid rgba(255,255,255,0.04)}}
.footer{{text-align:center;color:var(--text2);font-size:0.75rem;margin-top:24px}}
</style>
</head>
<body>
<div class="container">
<h1><span>🌍 小组赛最终排名预测</span></h1>
<div class="sub">更新于 {now} · 未赛按实力判定 · 🔴 高风险组</div>
<div class="grid">{group_rows}</div>
<div class="footer">自动生成 · 每次运行 update_group_predictions.py 刷新</div>
</div>
</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 已保存: {OUTPUT_HTML}")


if __name__ == "__main__":
    groups = predict_all()

    if "--save" in sys.argv or "--web" in sys.argv:
        save_json(groups)

    if "--web" in sys.argv:
        generate_html(groups)

    if "--save" not in sys.argv and "--web" not in sys.argv:
        print("\n💡 提示: 使用 --save 保存JSON | --web 生成HTML")

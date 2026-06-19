# -*- coding: utf-8 -*-
"""
500.com XLS 统一分析器
读取同一场比赛的四个XLS文件，输出整合分析结果
支持多时间版本对比，追踪XLS数据的时间序列变动
"""

import os
import json
import glob
from datetime import datetime
from pathlib import Path

# 通过 PowerShell COM 读取 XLS（xlrd在沙箱被阻止）
XLS_DIR = r"D:"

# 已知的比赛列表
KNOWN_MATCHES = [
    "卡塔尔VS瑞士", "巴西VS摩洛哥", "海地VS苏格兰", "澳大利亚VS土耳其",
    "德国VS库拉索", "荷兰VS日本",
    "比利时VS埃及", "西班牙VS佛得角", "瑞典VS突尼斯", "沙特VS乌拉圭",
    "法国VS塞内加尔", "伊朗VS新西兰",
    "葡萄牙VS民主刚果", "奥地利VS约旦", "阿根廷VS阿尔及利亚", "加纳VS巴拿马",
    "乌兹别克斯坦VS哥伦比亚", "科特迪瓦VS厄瓜多尔",
    "巴拿马VS克罗地亚",
]

FILE_TYPES = ["(世界杯)欧洲数据", "(亚盘)", "(大小)", "(让球指数)"]
# 备用命名：auto-downloader可能使用英文key
ALT_NAMES = {"(世界杯)欧洲数据": ["european"], "(亚盘)": [], "(大小)": [], "(让球指数)": []}


def find_xls_file(match_name, file_type):
    """智能文件查找：先查标准名，再查备用名，选最新修改时间"""
    candidates = []
    # 标准名
    std = os.path.join(XLS_DIR, f"{match_name}{file_type}.xls")
    if os.path.exists(std):
        candidates.append((std, os.path.getmtime(std)))
    # 备用名
    for alt in ALT_NAMES.get(file_type, []):
        alt_path = os.path.join(XLS_DIR, f"{match_name}({alt}).xls")
        if os.path.exists(alt_path):
            candidates.append((alt_path, os.path.getmtime(alt_path)))
    # 选最新的
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    return None


def read_xls_via_com(filepath):
    """通过 PowerShell Excel COM 读取 XLS 文件内容"""
    import subprocess
    ps_script = f'''
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$wb = $excel.Workbooks.Open('{filepath}')
$sh = $wb.Sheets.Item(1)
$rows = $sh.UsedRange.Rows.Count
$cols = $sh.UsedRange.Columns.Count
$data = @()
for ($r = 1; $r -le $rows; $r++) {{
    $row = @()
    for ($c = 1; $c -le $cols; $c++) {{
        $row += $sh.Cells.Item($r, $c).Text
    }}
    $data += ($row -join '|||')
}}
$wb.Close($false)
$excel.Quit()
Write-Output ($data -join ':::')
'''
    result = subprocess.run(
        ['powershell', '-Command', ps_script],
        capture_output=True, text=True, timeout=30,
        encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f"PowerShell error: {result.stderr[:200]}")
    return result.stdout


def parse_european_odds(raw_text):
    """解析欧洲数据XLS，提取关键指标"""
    lines = raw_text.strip().split(':::')
    data = {"rows": len(lines)}

    for i, line in enumerate(lines):
        cells = line.split('|||')
        if i == 2:  # Row 3 (0-indexed): 最大值
            data["max"] = {"win": cells[1], "draw": cells[2], "lose": cells[3],
                           "win_prob": cells[4], "draw_prob": cells[5], "lose_prob": cells[6]}
        if i == 3:  # Row 4: 即时均值
            data["instant"] = {"win": cells[1], "draw": cells[2], "lose": cells[3],
                               "win_prob": cells[4], "draw_prob": cells[5], "lose_prob": cells[6]}
        if i == 4:  # Row 5: 最小值
            data["min"] = {"win": cells[1], "draw": cells[2], "lose": cells[3],
                           "win_prob": cells[4], "draw_prob": cells[5], "lose_prob": cells[6]}
        # 抽样公司
        if 6 <= i <= 12:
            name = cells[0] if cells[0] else f"company_{i}"
            data[f"co_{name}"] = {
                "init_win": cells[4] if len(cells) > 4 else "",
                "init_draw": cells[5] if len(cells) > 5 else "",
                "init_lose": cells[6] if len(cells) > 6 else "",
                "now_win": cells[7] if len(cells) > 7 else "",
                "now_draw": cells[8] if len(cells) > 8 else "",
                "now_lose": cells[9] if len(cells) > 9 else "",
            }
    return data


def parse_asian_handicap(raw_text):
    """解析亚盘XLS"""
    lines = raw_text.strip().split(':::')
    data = {"rows": len(lines)}
    companies = []

    for i, line in enumerate(lines):
        cells = line.split('|||')
        if i == 2:  # 均值
            data["instant_avg"] = {"water_home": cells[1], "line": cells[2], "water_away": cells[3]}
            data["init_avg"] = {"water_home": cells[5] if len(cells)>5 else "",
                                "line": cells[6] if len(cells)>6 else "",
                                "water_away": cells[7] if len(cells)>7 else ""}
        if i >= 5:
            companies.append({
                "name": cells[0],
                "now": f"{cells[1]} {cells[2]} {cells[3]}" if len(cells)>3 else "",
                "change_time": cells[4] if len(cells)>4 else "",
                "init": f"{cells[5]} {cells[6]} {cells[7]}" if len(cells)>7 else "",
            })
    data["companies"] = companies
    return data


def parse_totals(raw_text):
    """解析大小球XLS"""
    lines = raw_text.strip().split(':::')
    data = {"rows": len(lines)}
    companies = []

    for i, line in enumerate(lines):
        cells = line.split('|||')
        if i == 2:
            data["instant_avg"] = {"over": cells[1], "line": cells[2], "under": cells[3]}
            data["init_avg_over"] = cells[5] if len(cells) > 5 else ""
        if i >= 5:
            companies.append({
                "name": cells[0],
                "now": f"O{cells[1]} L{cells[2]} U{cells[3]}" if len(cells)>3 else "",
                "change_time": cells[4] if len(cells)>4 else "",
                "init_over": cells[5] if len(cells)>5 else "",
            })
    data["companies"] = companies
    return data


def parse_handicap_index(raw_text):
    """解析让球指数XLS"""
    lines = raw_text.strip().split(':::')
    data = {"rows": len(lines)}
    companies = []

    for i, line in enumerate(lines):
        cells = line.split('|||')
        if i >= 5:
            companies.append({
                "name": cells[0],
                "line": cells[1] if len(cells) > 1 else "",
                "win": cells[2] if len(cells) > 2 else "",
                "draw": cells[3] if len(cells) > 3 else "",
                "lose": cells[4] if len(cells) > 4 else "",
            })
    data["companies"] = companies
    return data


def analyze_match(match_name, verbose=True):
    """分析单场比赛的所有四个XLS文件"""
    result = {
        "match": match_name,
        "analyzed_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "files": {},
    }

    for ftype in FILE_TYPES:
        short_key = ftype.replace("(世界杯)欧洲数据", "european").replace("(亚盘)", "asian") \
                         .replace("(大小)", "totals").replace("(让球指数)", "handicap_idx")

        fpath = find_xls_file(match_name, ftype)

        if fpath is None:
            result["files"][short_key] = {"status": "missing"}
            if verbose:
                print(f"  ❌ {ftype}: 缺失")
            continue

        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
        fsize = os.path.getsize(fpath)
        if verbose:
            print(f"  ✅ {ftype}: {fsize} bytes · {mtime.strftime('%m-%d %H:%M')}")

        try:
            raw = read_xls_via_com(fpath)  # fpath already validated by find_xls_file

            if "欧洲" in ftype:
                parsed = parse_european_odds(raw)
                instant = parsed.get("instant", {})
                if verbose and instant:
                    print(f"     均值: W{instant.get('win','?')} D{instant.get('draw','?')} L{instant.get('lose','?')}")
                    print(f"     概率: 主{instant.get('win_prob','?')} 平{instant.get('draw_prob','?')} 客{instant.get('lose_prob','?')}")

            elif "亚盘" in ftype:
                parsed = parse_asian_handicap(raw)
                iavg = parsed.get("instant_avg", {})
                init = parsed.get("init_avg", {})
                if verbose and iavg:
                    print(f"     即时: {iavg.get('water_home','?')} / {iavg.get('line','?')} / {iavg.get('water_away','?')}")
                    print(f"     初盘: {init.get('line','?')} → {iavg.get('line','?')} " +
                          ("升盘" if float(iavg.get('line','0') or 0) > float(init.get('line','0') or 0) else "退盘" if float(iavg.get('line','0') or 0) < float(init.get('line','0') or 0) else "不变"))
                # 检查T4临场变动
                companies = parsed.get("companies", [])
                t4_changes = [c for c in companies if c.get("change_time", "") > "06-13 22:00" and c.get("change_time", "")]
                if verbose and t4_changes:
                    print(f"     ⚠️ T4临场变动({len(t4_changes)}家): {t4_changes[0]['change_time']}")

            elif "大小" in ftype:
                parsed = parse_totals(raw)
                iavg = parsed.get("instant_avg", {})
                if verbose and iavg:
                    print(f"     盘口: O{iavg.get('over','?')}/{iavg.get('line','?')}/U{iavg.get('under','?')}")

            elif "让球指数" in ftype:
                parsed = parse_handicap_index(raw)
                companies = parsed.get("companies", [])
                if verbose and companies:
                    c = companies[0]
                    print(f"     {c.get('line','?')}盘: W{c.get('win','?')}/D{c.get('draw','?')}/L{c.get('lose','?')} ({len(companies)}家公司)")

            parsed["file_mtime"] = mtime.strftime('%Y-%m-%d %H:%M:%S')
            parsed["file_size"] = os.path.getsize(fpath)
            result["files"][short_key] = {"status": "ok", "data": parsed}

        except Exception as e:
            result["files"][short_key] = {"status": "error", "error": str(e)[:200]}
            if verbose:
                print(f"     ⚠️ 读取失败: {str(e)[:100]}")

    return result


def analyze_all_matches():
    """分析D盘所有已知比赛的XLS文件"""
    print(f"📊 500.com XLS 统一分析 · {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)

    results = {}
    for match in KNOWN_MATCHES:
        print(f"\n🏆 {match}")
        results[match] = analyze_match(match)

    # 保存JSON
    outpath = os.path.join(r"C:\Users\A\PyCharmMiscProject", "xls_analysis_latest.json")
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✅ 已保存: {outpath}")

    return results


if __name__ == "__main__":
    analyze_all_matches()

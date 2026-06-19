# -*- coding: utf-8 -*-
"""
修复版: parse_european_odds
修正: 配对行结构(奇数行=初盘, 偶数行=即时)
"""
import os, json, subprocess
from datetime import datetime

XLS_DIR = r"D:"

def read_xls_via_com(filepath):
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
    result = subprocess.run(['powershell', '-Command', ps_script],
        capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:200])
    return result.stdout


def parse_european_odds(raw_text):
    """修复版: XLS配对行结构"""
    lines = raw_text.strip().split(':::')
    data = {"rows": len(lines)}

    for i, line in enumerate(lines):
        cells = line.split('|||')
        if i == 2:  # 最大值
            data["max"] = {"win": cells[1], "draw": cells[2], "lose": cells[3],
                           "win_prob": cells[4], "draw_prob": cells[5], "lose_prob": cells[6]}
        if i == 3:  # 即时均值 (行4)
            data["instant"] = {"win": cells[1], "draw": cells[2], "lose": cells[3],
                               "win_prob": cells[4], "draw_prob": cells[5], "lose_prob": cells[6]}
        if i == 4:  # 最小值
            data["min"] = {"win": cells[1], "draw": cells[2], "lose": cells[3],
                           "win_prob": cells[4], "draw_prob": cells[5], "lose_prob": cells[6]}

    # 修复: 配对行结构
    # 奇数行(有公司名, col1非空) = 初盘赔率
    # 偶数行(公司名空, col1为空) = 即时赔率 (配对上奇数行)
    companies = []
    i = 6  # 从第7行(0-indexed=6)开始
    while i < len(lines) - 1:
        cells_a = lines[i].split('|||')
        name = cells_a[0].strip() if len(cells_a) > 0 else ""
        # 跳过汇总行(最大值/最小值/即时/初盘/离散值)
        if not name or name in ['最大值', '最小值', '即时', '初盘', '离散值', '平均值']:
            i += 1
            continue

        # 奇数行: 初盘赔率 (col1=公司名, col2-4=W/D/L)
        init_win = cells_a[1] if len(cells_a) > 1 else ""
        init_draw = cells_a[2] if len(cells_a) > 2 else ""
        init_lose = cells_a[3] if len(cells_a) > 3 else ""

        # 偶数行: 即时赔率 (col1=空, col2-4=W/D/L)
        cells_b = lines[i+1].split('|||')
        now_win = cells_b[1] if len(cells_b) > 1 else ""
        now_draw = cells_b[2] if len(cells_b) > 2 else ""
        now_lose = cells_b[3] if len(cells_b) > 3 else ""

        companies.append({
            "name": name,
            "init_win": init_win, "init_draw": init_draw, "init_lose": init_lose,
            "now_win": now_win, "now_draw": now_draw, "now_lose": now_lose,
        })
        i += 2  # 跳过配对行

    data["companies"] = companies
    return data


def test():
    fpath = r"D:\荷兰VS日本(世界杯)欧洲数据.xls"
    print(f"读取: {fpath}")
    raw = read_xls_via_com(fpath)
    data = parse_european_odds(raw)

    inst = data["instant"]
    print(f"\n即时均值: W{inst['win']} D{inst['draw']} L{inst['lose']}")
    print(f"概率: 主{inst['win_prob']} 平{inst['draw_prob']} 客{inst['lose_prob']}")

    print(f"\n配对行解析结果 (前10家):")
    for c in data["companies"][:10]:
        iw = c['init_win']; idr = c['init_draw']; il = c['init_lose']
        nw = c['now_win']; ndr = c['now_draw']; nl = c['now_lose']
        print(f"  {c['name']}: 初W{iw}/D{idr}/L{il} -> 即W{nw}/D{ndr}/L{nl}")

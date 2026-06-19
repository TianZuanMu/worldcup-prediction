# -*- coding: utf-8 -*-
"""
500.com 下载面板自动生成器
用法: python generate_panel.py
功能: 自动爬取500.com当前比赛→生成download_panel.html
"""

import requests
import os
from datetime import datetime

BASE = "https://odds.500.com"
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_panel.html")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_current_match_ids():
    """从500.com首页获取当前可用的比赛ID"""
    try:
        r = requests.get(BASE + "/", headers=HEADERS, timeout=10)
        ids = set()
        for line in r.text.split('href="'):
            if 'fenxi/ouzhi-' in line:
                mid = line.split('ouzhi-')[1].split('.shtml')[0]
                if mid.isdigit():
                    ids.add(mid)
        return sorted(ids)
    except:
        return []


def get_match_name(mid):
    """获取比赛名称"""
    try:
        r = requests.get(f"{BASE}/fenxi/ouzhi-{mid}.shtml", headers=HEADERS, timeout=8)
        text = r.content.decode('gbk', errors='replace')
        import re
        title = re.search(r'<title>([^<]+)</title>', text)
        if title:
            name = title.group(1)
            name = name.replace('(2026世界杯)-百家欧赔-500彩票网', '')
            name = name.replace('(2026世界杯)', '')
            return name.strip()
    except:
        pass
    return None


def generate():
    print(f"📥 扫描 500.com · {datetime.now().strftime('%H:%M:%S')}")
    ids = get_current_match_ids()
    print(f"   找到 {len(ids)} 个比赛ID: {ids}")

    matches = []
    for mid in ids:
        name = get_match_name(mid)
        if name and '2025' not in name and 'U18' not in name and 'B队' not in name:
            matches.append({"id": mid, "name": name})
            print(f"   ✅ {mid}: {name}")
        else:
            print(f"   ⏭️ {mid}: 跳过({name or '非世界杯'})")

    if not matches:
        print("❌ 没有找到世界杯比赛")
        return

    # 生成HTML
    match_json = ""
    for m in matches:
        match_json += f'  {{name:"{m["name"]}", id:"{m["id"]}"}},\n'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>500.com XLS 下载面板</title>
<style>
  body{{font-family:"Microsoft YaHei",sans-serif;background:#0f1923;color:#e0e6ed;max-width:900px;margin:40px auto;padding:20px}}
  h1{{color:#00d4aa;font-size:20px;margin-bottom:4px}}
  .sub{{color:#8899aa;font-size:12px;margin-bottom:24px}}
  .match{{margin-bottom:10px;background:#1a2634;border-radius:10px;padding:10px 16px;border:1px solid #2a3a4a}}
  .match h2{{font-size:14px;margin-bottom:6px;color:#fff}}
  .btns{{display:flex;gap:6px;flex-wrap:wrap}}
  .btn{{display:inline-block;padding:5px 12px;border-radius:5px;font-size:11px;text-decoration:none;border:none;transition:all .15s;background:rgba(0,212,170,.12);color:#00d4aa;border:1px solid rgba(0,212,170,.25)}}
  .btn:hover{{background:rgba(0,212,170,.3)}}
  .note{{font-size:11px;color:#8899aa;margin-top:20px;padding:12px;background:rgba(255,165,2,.06);border-radius:8px}}
</style></head>
<body>
<h1>📥 500.com XLS 下载面板</h1>
<div class="sub">{len(matches)}场比赛 · 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<script>
const matches = [
{match_json}];
const types=[{{key:"ouzhi",label:"百欧"}},{{key:"yazhi",label:"亚盘"}},{{key:"daxiao",label:"大小"}},{{key:"rangqiu",label:"让球"}}];
matches.forEach(m=>{{
  document.write(`<div class="match"><h2>${{m.name}}</h2><div class="btns">`);
  types.forEach(t=>{{document.write(`<a class="btn" href="https://odds.500.com/fenxi/${{t.key}}-${{m.id}}.shtml" target="_blank">${{t.label}}</a> `);}});
  document.write(`</div></div>`);
}});
</script>
<div class="note">每次运行 <b>python generate_panel.py</b> 自动更新比赛列表</div>
</body>
</html>'''

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n✅ 面板已生成: {OUTPUT} ({len(matches)}场比赛)")


if __name__ == "__main__":
    generate()

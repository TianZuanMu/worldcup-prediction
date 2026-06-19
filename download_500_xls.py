# -*- coding: utf-8 -*-
"""
500.com XLS 自动下载器
用法: python download_500_xls.py --all         (下载全部已知比赛)
      python download_500_xls.py 1359227       (下载指定比赛ID)
"""

import requests
import os
import sys
from datetime import datetime

BASE = "https://odds.500.com/fenxi"

ENDPOINTS = {
    "european":  f"{BASE}/europe_xls.php",
    "asian":     "https://odds.500.com/fenxi1/xls.php",
    "totals":    "https://odds.500.com/fenxi1/xls.php",
    "handicap":  "https://odds.500.com/fenxi1/rangqiu_xls.php",
}

FILE_NAMES = {
    "european": "(世界杯)欧洲数据",
    "asian":    "(亚盘)",
    "totals":   "(大小)",
    "handicap": "(让球指数)",
}

MATCHES = {
    "1359200": "德国VS库拉索",
    "1359203": "荷兰VS日本",
    "1359206": "比利时VS埃及",
    "1359209": "西班牙VS佛得角",
    "1359212": "法国VS塞内加尔",
    "1359215": "阿根廷VS阿尔及利亚",
    "1359218": "葡萄牙VS民主刚果",
    "1359236": "科特迪瓦VS厄瓜多尔",
    "1359239": "瑞典VS突尼斯",
    "1359242": "伊朗VS新西兰",
    "1359245": "沙特VS乌拉圭",
    "1359251": "奥地利VS约旦",
    "1359254": "乌兹别克VS哥伦比亚",
    "1359257": "加纳VS巴拿马",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
}
OUTPUT_DIR = r"D:"


def download_xls(match_id, match_name=None):
    name = match_name or match_id
    results = {}
    for ft, url in ENDPOINTS.items():
        fn = FILE_NAMES.get(ft, ft)
        out = os.path.join(OUTPUT_DIR, f"{name}{fn}.xls").replace("D:", "D:/")
        # P0: 检查是否已有真实文件(>20KB) → 不覆盖
        if os.path.exists(out) and os.path.getsize(out) > 20000:
            print(f"  ⏭️ {ft}: 已有真实数据({os.path.getsize(out)/1024:.0f}KB)·跳过")
            results[ft] = "skipped"
            continue
        try:
            hdrs = {**HEADERS, "Referer": f"{BASE}/ouzhi-{match_id}.shtml"}
            r = requests.post(url, headers=hdrs, data={"id": match_id}, timeout=15)
            # P0: 文件<15KB为空模板·不保存
            if r.status_code == 200 and len(r.content) > 15000:
                # 如果已有文件(可能是空模板)·先删除再保存
                if os.path.exists(out):
                    os.remove(out)
                with open(out, 'wb') as f: f.write(r.content)
                print(f"  ✅ {ft}: {len(r.content)/1024:.1f}KB → {os.path.basename(out)}")
                results[ft] = "ok"
            elif r.status_code == 200 and len(r.content) <= 15000:
                print(f"  ⚠️ {ft}: 空模板({len(r.content)}b)·跳过·保留现有文件")
                results[ft] = "empty_template"
            else:
                print(f"  ❌ {ft}: HTTP {r.status_code} ({len(r.content)}b)")
                results[ft] = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"  ❌ {ft}: {str(e)[:80]}")
            results[ft] = "error"
    return results


def download_all():
    print(f"📥 500.com XLS 自动下载 · {datetime.now().strftime('%H:%M:%S')}")
    print(f"   保存: {OUTPUT_DIR}")
    print("=" * 50)
    ok = 0
    for mid, name in MATCHES.items():
        print(f"\n🏆 {name} (ID:{mid})")
        r = download_xls(mid, name)
        n = sum(1 for v in r.values() if v == "ok")
        ok += n
        print(f"   → {n}/4 成功")
    print(f"\n{'='*50}")
    print(f"✅ {ok}/{len(MATCHES)*4} 文件下载成功")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        download_all()
    elif len(sys.argv) > 1:
        download_xls(sys.argv[1])
    else:
        print("用法: python download_500_xls.py --all")
        print("      python download_500_xls.py 1359227")

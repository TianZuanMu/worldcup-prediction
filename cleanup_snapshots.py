# -*- coding: utf-8 -*-
"""
赔率快照自动清理 — 保留最近N个文件 + 每场比赛的代表性快照

用法:
  python cleanup_snapshots.py           # 预览
  python cleanup_snapshots.py --do      # 执行清理
"""
import os, sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DIR = Path(r"C:\Users\A\PyCharmMiscProject")
KEEP_RECENT = 30          # 保留最近30个快照
KEEP_PER_MATCHDAY = 3     # 每个比赛日保留最早+最晚+中间1个
KEEP_RECENT_HOURS = 24    # 24小时内的全部保留


def analyze():
    """分析快照分布"""
    files = sorted(DIR.glob("worldcup_odds_*.csv"))
    if not files:
        return [], {}

    # 按日期分组
    by_date = defaultdict(list)
    for f in files:
        # worldcup_odds_20260616_214025.csv
        stem = f.stem.replace("worldcup_odds_", "")
        date_str = stem[:8]  # 20260616
        time_str = stem[9:15]  # 214025
        try:
            dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except ValueError:
            continue
        by_date[date_str].append((dt, f))

    return files, by_date


def plan_cleanup(dry_run=True):
    """规划清理，返回要删除的文件列表"""
    files, by_date = analyze()
    if not files:
        print("无快照文件")
        return []

    now = datetime.now()
    keep = set()
    delete = []

    # 1. 24h内全部保留
    cutoff_24h = now - timedelta(hours=KEEP_RECENT_HOURS)

    # 2. 最近N个保留
    recent = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
    for f in recent[:KEEP_RECENT]:
        keep.add(f)

    # 3. 每个比赛日保留代表性快照
    for date_str, entries in sorted(by_date.items()):
        sorted_entries = sorted(entries, key=lambda x: x[0])
        if len(sorted_entries) <= KEEP_PER_MATCHDAY:
            for _, f in sorted_entries:
                keep.add(f)
        else:
            # 保留最早+最晚+中间
            keep.add(sorted_entries[0][1])
            keep.add(sorted_entries[-1][1])
            mid = sorted_entries[len(sorted_entries) // 2][1]
            keep.add(mid)

    # 需要删除的
    for f in files:
        if f not in keep:
            # 额外保护: 24h内不删
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime > cutoff_24h:
                continue
            delete.append(f)

    if dry_run:
        total_size = sum(f.stat().st_size for f in delete) / 1024 / 1024
        print(f"快照总数: {len(files)}")
        print(f"保留: {len(keep)} | 删除: {len(delete)} (释放 {total_size:.1f}MB)")
        print(f"比赛日: {len(by_date)}天")
        if delete:
            print(f"\n将删除 (前10):")
            for f in sorted(delete)[:10]:
                print(f"  {f.name}")
            if len(delete) > 10:
                print(f"  ... 共{len(delete)}个")
    else:
        for f in delete:
            f.unlink()
        print(f"已删除 {len(delete)} 个快照")
        print(f"保留 {len(keep)} 个")

    return delete


if __name__ == "__main__":
    do = "--do" in sys.argv
    plan_cleanup(dry_run=not do)

# -*- coding: utf-8 -*-
"""
V3.0 数据归档器 (P3#18)
归档XLS/必发/赔率快照，支持时点回放回测。

用法:
  from data_archiver import archive_match_data, list_archives, replay_archive, cleanup_archives

  # 归档当前数据
  path = archive_match_data('法国VS塞内加尔')

  # 列出归档
  for a in list_archives('法国VS塞内加尔'):
      print(a['match_name'], a['timestamp'], a['file_count'], a['path'])

  # 回放历史时点
  restored = replay_archive('法国VS塞内加尔')           # 最新快照
  restored = replay_archive('法国VS塞内加尔', '20260617_143000')  # 指定时点
  print(restored['xls_files'])  # 恢复后的文件路径列表

  # 清理过期归档
  n = cleanup_archives(days_old=30)
"""

import json
import os
import shutil
import glob as _glob
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import CONF

# ── 路径常量 ──
ARCHIVE_DIR = Path(CONF.data_archive_dir)
ODDS_DIR = Path(r"C:\Users\A\PyCharmMiscProject")
BETFAIR_DIR = ODDS_DIR / "betfair_data"
ODDS_GLOB = "worldcup_odds_*.csv"

# XLS 五种类型 (按500.com 结构)
XLS_TYPES = ['欧洲数据', '亚盘', '大小', '让球指数', '凯利指数']


# ══════════════════════════════════════════════════════════════════
# 内部工具
# ══════════════════════════════════════════════════════════════════

def _sanitize_name(match_name: str) -> str:
    """将比赛名转为安全的目录名"""
    return match_name.replace('/', '_').replace('\\', '_').replace(' ', '_')


def _find_xls_files(match_name: str) -> List[Path]:
    """查找某场比赛的所有XLS文件 (D: 盘)"""
    found = []
    for xls_type in XLS_TYPES:
        pattern = f'D:/{match_name}*{xls_type}*.xls'
        for fp in _glob.glob(pattern):
            found.append(Path(fp))
    return found


def _find_latest_odds_csv() -> Optional[Path]:
    """返回最新的赔率CSV快照"""
    csvs = sorted(ODDS_DIR.glob(ODDS_GLOB), key=lambda p: p.stat().st_mtime, reverse=True)
    return csvs[0] if csvs else None


def _find_betfair_json(match_name: str) -> Optional[Path]:
    """查找必发JSON (可能以原名或safe名存在)"""
    match_safe = _sanitize_name(match_name)
    # 优先精准匹配原名
    candidates = [
        BETFAIR_DIR / f'{match_name}.json',
        BETFAIR_DIR / f'{match_safe}.json',
    ]
    for c in candidates:
        if c.exists():
            return c
    # fallback: 模糊匹配
    for f in sorted(BETFAIR_DIR.glob('*.json')):
        if match_safe in _sanitize_name(f.stem):
            return f
    return None


def _latest_timestamp_for_match(match_safe: str) -> Optional[str]:
    """返回某场比赛最新归档的时间戳"""
    match_dir = ARCHIVE_DIR / match_safe
    if not match_dir.exists():
        return None
    ts_dirs = sorted(
        [d for d in match_dir.iterdir() if d.is_dir()],
        reverse=True
    )
    return ts_dirs[0].name if ts_dirs else None


# ══════════════════════════════════════════════════════════════════
# 1. 归档
# ══════════════════════════════════════════════════════════════════

def archive_match_data(match_name: str) -> Optional[str]:
    """
    归档当前 XLS + 必发 + 赔率快照到 archive/{match}/{timestamp}/

    Args:
        match_name: 比赛名称, 如 '法国VS塞内加尔'

    Returns:
        归档目录路径; 无文件可归档时返回 None
    """
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    match_safe = _sanitize_name(match_name)
    archive_path = ARCHIVE_DIR / match_safe / ts
    archive_path.mkdir(parents=True, exist_ok=True)

    files_saved: List[str] = []

    # ── XLS 文件 ──
    xls_files = _find_xls_files(match_name)
    for fp in xls_files:
        shutil.copy2(str(fp), str(archive_path / fp.name))
        files_saved.append(fp.name)

    # ── 必发 JSON ──
    bf_file = _find_betfair_json(match_name)
    if bf_file:
        dest_name = f'{match_safe}.json'
        shutil.copy2(str(bf_file), str(archive_path / dest_name))
        files_saved.append(dest_name)

    # ── 赔率 CSV ──
    odds_csv = _find_latest_odds_csv()
    if odds_csv:
        shutil.copy2(str(odds_csv), str(archive_path / odds_csv.name))
        files_saved.append(odds_csv.name)

    if not files_saved:
        # 没有文件可归档, 清理空目录
        archive_path.rmdir()
        match_dir = archive_path.parent
        try:
            match_dir.rmdir()  # 若为空则清理
        except OSError:
            pass
        return None

    # ── 元数据 ──
    meta = {
        'match_name': match_name,
        'timestamp': ts,
        'file_count': len(files_saved),
        'files': files_saved,
        'path': str(archive_path),
    }
    with open(archive_path / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return str(archive_path)


# ══════════════════════════════════════════════════════════════════
# 2. 列表
# ══════════════════════════════════════════════════════════════════

def list_archives(match_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出归档快照。

    Args:
        match_name: 比赛名称; None 则列出所有比赛

    Returns:
        [{match_name, timestamp, file_count, files, path}, ...]
        按时间倒序排列
    """
    if not ARCHIVE_DIR.exists():
        return []

    results: List[Dict[str, Any]] = []

    if match_name:
        match_dirs = [ARCHIVE_DIR / _sanitize_name(match_name)]
    else:
        match_dirs = sorted(ARCHIVE_DIR.iterdir())

    for match_dir in match_dirs:
        if not match_dir.is_dir():
            continue
        ts_dirs = sorted(
            [d for d in match_dir.iterdir() if d.is_dir()],
            reverse=True
        )
        for ts_dir in ts_dirs:
            meta_file = ts_dir / 'metadata.json'
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        entry = json.load(f)
                    # 确保 path 字段存在 (兼容旧归档)
                    if 'path' not in entry:
                        entry['path'] = str(ts_dir)
                    results.append(entry)
                except (json.JSONDecodeError, OSError):
                    continue

    # 按时间戳降序
    results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return results


# ══════════════════════════════════════════════════════════════════
# 3. 回放 (恢复归档到临时目录)
# ══════════════════════════════════════════════════════════════════

def replay_archive(match_name: str, timestamp: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    从归档恢复 XLS 文件到临时目录，供预测模块使用。

    Args:
        match_name: 比赛名称
        timestamp:  归档时间戳 (如 '20260617_143000'); None 则用最新

    Returns:
        {
            'xls_files': [Path, ...],       # 恢复后的 XLS 文件路径
            'odds_csv': Path | None,        # 恢复后的赔率 CSV 路径
            'betfair_json': Path | None,    # 恢复后的必发 JSON 路径
            'temp_dir': Path,               # 临时目录 (用完请清理)
            'metadata': dict,               # 原始 metadata.json 内容
        }
        若归档不存在则返回 None
    """
    match_safe = _sanitize_name(match_name)
    match_dir = ARCHIVE_DIR / match_safe

    if not match_dir.exists():
        return None

    # 确定时间戳
    if timestamp is None:
        ts_dirs = sorted(
            [d for d in match_dir.iterdir() if d.is_dir()],
            reverse=True
        )
        if not ts_dirs:
            return None
        ts_dir = ts_dirs[0]
    else:
        ts_dir = match_dir / timestamp
        if not ts_dir.exists():
            return None

    # 读取元数据
    meta_file = ts_dir / 'metadata.json'
    metadata = {}
    if meta_file.exists():
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix=f'archive_replay_{match_safe}_'))
    xls_files: List[Path] = []
    odds_csv: Optional[Path] = None
    betfair_json: Optional[Path] = None

    # 复制所有文件到临时目录
    for item in ts_dir.iterdir():
        if item.name == 'metadata.json':
            continue
        if item.is_file():
            dest = temp_dir / item.name
            shutil.copy2(str(item), str(dest))

            # 分类
            if item.suffix.lower() == '.xls':
                xls_files.append(dest)
            elif item.suffix.lower() == '.csv':
                odds_csv = dest
            elif item.suffix.lower() == '.json':
                betfair_json = dest

    result = {
        'xls_files': xls_files,
        'odds_csv': odds_csv,
        'betfair_json': betfair_json,
        'temp_dir': temp_dir,
        'metadata': metadata,
    }
    return result


# ══════════════════════════════════════════════════════════════════
# 4. 清理
# ══════════════════════════════════════════════════════════════════

def cleanup_archives(days_old: int = 30) -> int:
    """
    清理超过指定天数的归档。

    Args:
        days_old: 保留天数; 默认 30

    Returns:
        已删除的归档目录数量
    """
    if not ARCHIVE_DIR.exists():
        return 0

    import time
    cutoff = time.time() - days_old * 86400
    removed = 0

    for match_dir in list(ARCHIVE_DIR.iterdir()):
        if not match_dir.is_dir():
            continue
        for ts_dir in list(match_dir.iterdir()):
            if ts_dir.is_dir() and ts_dir.stat().st_mtime < cutoff:
                shutil.rmtree(str(ts_dir))
                removed += 1
        # 清理空的比赛目录
        if not any(match_dir.iterdir()):
            try:
                match_dir.rmdir()
            except OSError:
                pass

    return removed


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys

    def _usage():
        print(__doc__)
        print("CLI 用法:")
        print("  python data_archiver.py archive <比赛名>")
        print("  python data_archiver.py list   [比赛名]")
        print("  python data_archiver.py replay <比赛名> [时间戳]")
        print("  python data_archiver.py cleanup [天数]")

    args = sys.argv[1:]
    if not args:
        _usage()
        sys.exit(0)

    cmd = args[0].lower()

    if cmd == 'archive':
        match = args[1] if len(args) > 1 else None
        if not match:
            print("请指定比赛名称")
            sys.exit(1)
        path = archive_match_data(match)
        if path:
            print(f'归档完成: {path}')
        else:
            print('无文件可归档')

    elif cmd == 'list':
        match = args[1] if len(args) > 1 else None
        archives = list_archives(match)
        if not archives:
            print('(无归档)')
        else:
            for a in archives:
                print(f"  {a.get('match_name','?'):30s} | {a.get('timestamp','?')} | "
                      f"{a.get('file_count',0)} files | {a.get('path','')}")

    elif cmd == 'replay':
        match = args[1] if len(args) > 1 else None
        ts = args[2] if len(args) > 2 else None
        if not match:
            print("请指定比赛名称")
            sys.exit(1)
        result = replay_archive(match, ts)
        if result is None:
            print(f'未找到归档: {match}' + (f' @ {ts}' if ts else ''))
        else:
            print(f"恢复完成: {result['temp_dir']}")
            print(f"  XLS 文件: {len(result['xls_files'])} 个")
            for x in result['xls_files']:
                print(f"    {x}")
            if result['odds_csv']:
                print(f"  赔率 CSV: {result['odds_csv']}")
            if result['betfair_json']:
                print(f"  必发 JSON: {result['betfair_json']}")
            print(f"  元数据: {result['metadata']}")

    elif cmd == 'cleanup':
        days = int(args[1]) if len(args) > 1 else 30
        n = cleanup_archives(days)
        print(f'清理完成: 删除了 {n} 个过期归档 (> {days} 天)')

    else:
        print(f'未知命令: {cmd}')
        _usage()
        sys.exit(1)

# -*- coding: utf-8 -*-
"""
500.com XLS 自动下载器 — 替代人工手动下载

功能:
  1. 从500.com赛程页自动发现比赛ID
  2. 自动下载4个XLS文件到 D:\
  3. 支持手动配置比赛ID映射
  4. 断点续传·版本管理·重复下载检测

用法:
  # 自动发现并下载
  python auto_fetch_xls.py --match "法国VS塞内加尔"

  # 批量下载所有未来比赛
  python auto_fetch_xls.py --all

  # 配置比赛ID映射
  python auto_fetch_xls.py --add "法国VS塞内加尔" --id 1234567

  # 列出已配置的比赛
  python auto_fetch_xls.py --list

架构:
  500.com 比赛页 → 提取XLS下载链接 → requests下载 → D:/{match}{suffix}.xls
  支持两种模式:
    Mode A: 已知match_id → 直接构造下载URL
    Mode B: 未知match_id → 从赛程页抓取
"""

import os
import re
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

# ── 配置 ──

XLS_DIR = Path(r"D:")
CONFIG_FILE = Path(__file__).parent / "auto_fetch_config.json"

# XLS文件后缀映射 (与 xls_reader_xlrd.py 一致)
XLS_SUFFIXES = {
    'european': '(世界杯)欧洲数据.xls',
    'asian': '(亚盘).xls',
    'totals': '(大小).xls',
    'handicap_index': '(让球指数).xls',
}

# 500.com 页面URL模板
URL_500COM = {
    'schedule': 'https://odds.500.com/fenxi/nlz/',          # 赛程列表
    'match_euro': 'https://odds.500.com/fenxi/ouzhi-{mid}.shtml',   # 欧赔分析页
    'match_asian': 'https://odds.500.com/fenxi/yazhi-{mid}.shtml',  # 亚盘分析页
    'match_totals': 'https://odds.500.com/fenxi/daxiao-{mid}.shtml', # 大小球分析页
    # XLS直接下载链接 (常见模式, 可能因500.com改版而变化)
    'xls_downloads': {
        'european': [
            'https://odds.500.com/fenxi1/ouzhi/{mid}.xls',
            'https://odds.500.com/static/fenxi/ouzhi/{mid}.xls',
        ],
        'asian': [
            'https://odds.500.com/fenxi1/yazhi/{mid}.xls',
            'https://odds.500.com/static/fenxi/yazhi/{mid}.xls',
        ],
        'totals': [
            'https://odds.500.com/fenxi1/daxiao/{mid}.xls',
            'https://odds.500.com/static/fenxi/daxiao/{mid}.xls',
        ],
        'handicap_index': [
            'https://odds.500.com/fenxi1/rangqiu/{mid}.xls',
            'https://odds.500.com/static/fenxi/rangqiu/{mid}.xls',
        ],
    },
}

# HTTP请求头 (模拟浏览器)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://odds.500.com/',
}


# ── 配置管理 ──

def load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'matches': {},           # {"法国VS塞内加尔": {"match_id": "xxx", "last_fetch": "..."}}
        'cookie_string': '',     # 可选: 登录cookie
        'download_delay': 2.0,   # 下载间隔(秒)
        'timeout': 30,           # 请求超时(秒)
        'max_retries': 3,        # 最大重试次数
    }


def save_config(config: dict):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ── 比赛ID发现 ──

def discover_match_ids() -> Dict[str, str]:
    """
    从 live.500.com 自动发现世界杯比赛ID和队名。

    方法:
      1. 获取 https://live.500.com/ → 提取 JS 变量 liveOddsList
      2. liveOddsList 的 key 即为 500.com 比赛ID
      3. 对每个ID, 请求 odds.500.com/fenxi/touzhu-{id}.shtml
         从页面标题提取队名 (格式: "墨西哥VS韩国(2026世界杯)...")

    返回: {"墨西哥VS韩国": "1359177", "法国VS塞内加尔": "1359212", ...}
    """
    import re, json, time
    from bs4 import BeautifulSoup

    config = load_config()
    matches = {}

    try:
        # Step 1: 从 live.500.com 获取比赛ID列表
        session = _create_session(config)
        resp = session.get(
            'https://live.500.com/',
            headers=HEADERS,
            timeout=config.get('timeout', 30)
        )
        # 显式使用 GB2312 解码 (避免乱码)
        html = resp.content.decode('gb2312', errors='ignore')

        # 提取 var liveOddsList = {"1359177":{...}, ...};
        odds_match = re.search(r'var liveOddsList = (\{.*?\});', html, re.DOTALL)
        if not odds_match:
            print("⚠️ 未在 live.500.com 找到 liveOddsList 数据")
            return {}

        odds_data = json.loads(odds_match.group(1))
        match_ids = list(odds_data.keys())
        print(f"🔍 live.500.com: 发现 {len(match_ids)} 个比赛ID")

        # Step 2: 对每个ID获取队名
        print("   提取队名...")
        for i, mid in enumerate(match_ids):
            try:
                r = session.get(
                    f'https://odds.500.com/fenxi/touzhu-{mid}.shtml',
                    headers=HEADERS,
                    timeout=config.get('timeout', 30)
                )
                if r.status_code == 200:
                    # 500.com 使用 GB2312 编码, 必须显式解码
                    html = r.content.decode('gb2312', errors='ignore')
                    title_match = re.search(r'<title>(.+?)\(2026世界杯', html)
                    if title_match:
                        match_name = title_match.group(1).strip()
                        matches[match_name] = mid
                        print(f"    [{i+1}/{len(match_ids)}] {mid}: {match_name} ✅")
                    else:
                        # 非世界杯比赛 (如芬兰联赛2026赛季) → 静默跳过
                        pass

            except Exception as e:
                print(f"    [{i+1}/{len(match_ids)}] {mid}: ⚠️ {e}")

            # 礼貌间隔
            if i < len(match_ids) - 1:
                time.sleep(0.3)

        print(f"✅ 发现 {len(matches)} 场世界杯比赛")

    except requests.RequestException as e:
        print(f"⚠️ 无法访问 live.500.com: {e}")
    except json.JSONDecodeError as e:
        print(f"⚠️ liveOddsList JSON 解析失败: {e}")

    # 自动保存到配置文件
    if matches:
        if 'matches' not in config:
            config['matches'] = {}
        new_count = 0
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        for name, mid in matches.items():
            if name not in config['matches']:
                config['matches'][name] = {
                    'match_id': mid,
                    'discovered_at': now_str,
                    'source': 'live.500.com',
                }
                new_count += 1
        if new_count > 0:
            save_config(config)
            print(f"💾 新增 {new_count} 场比赛配置")

    return matches


def find_match_id(match_name: str) -> Optional[str]:
    """
    查找比赛的500.com ID。

    优先级:
      1. 本地配置
      2. 在线发现 (自动从赛程页抓取)
    """
    config = load_config()

    # 1. 本地配置
    if match_name in config.get('matches', {}):
        mid = config['matches'][match_name].get('match_id')
        if mid:
            return mid

    # 2. 在线发现
    discovered = discover_match_ids()
    if match_name in discovered:
        # 自动保存到配置
        if 'matches' not in config:
            config['matches'] = {}
        config['matches'][match_name] = {
            'match_id': discovered[match_name],
            'discovered_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        save_config(config)
        return discovered[match_name]

    return None


# ── Playwright 浏览器下载 ──

def _find_edge() -> str:
    """查找本机Edge浏览器路径"""
    import os as _os
    for candidate in [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]:
        if _os.path.exists(candidate):
            return candidate
    raise FileNotFoundError('未找到 Edge 浏览器')


# 页面类型 → CSS选择器映射 (500.com下载按钮)
_PAGE_SELECTORS = {
    'european':       'a.tb_xiazai_btn.olddownpl',   # 百家欧赔页
    'asian':          'a.tb_xiazai_btn.downpl',       # 亚盘页
    'totals':         'a.tb_xiazai_btn.downpl',       # 大小球页
    'handicap_index': 'a.tb_xiazai_btn.downpl',       # 让球指数页
}

_PAGE_URLS = {
    'european':       'https://odds.500.com/fenxi/ouzhi-{mid}.shtml',
    'asian':          'https://odds.500.com/fenxi/yazhi-{mid}.shtml',
    'totals':         'https://odds.500.com/fenxi/daxiao-{mid}.shtml',
    'handicap_index': 'https://odds.500.com/fenxi/rangqiu-{mid}.shtml',
}


def _download_with_playwright(
    match_name: str,
    file_type: str,
    match_id: str,
    config: dict = None,
) -> DownloadResult:
    """
    使用 Playwright + 本机Edge浏览器，模拟点击下载按钮获取XLS文件。

    Args:
        match_name: 比赛名称
        file_type: 'european'/'asian'/'totals'/'handicap_index'
        match_id: 500.com比赛ID
        config: 配置字典

    返回: DownloadResult
    """
    from playwright.sync_api import sync_playwright

    if config is None:
        config = load_config()

    suffix = XLS_SUFFIXES[file_type]
    url = _PAGE_URLS[file_type].format(mid=match_id)
    selector = _PAGE_SELECTORS[file_type]

    result = DownloadResult(file_type=file_type, success=False, url_used=url)
    result.error = 'Playwright 下载失败'

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=_find_edge(), headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # 导航到分析页
            page.goto(url, timeout=config.get('timeout', 30) * 1000, wait_until='domcontentloaded')

            # 等待下载按钮出现
            page.wait_for_selector(selector, timeout=10000)

            # 点击下载按钮，并捕获下载事件
            with page.expect_download(timeout=30000) as download_info:
                page.click(selector)

            download = download_info.value

            # 构建目标路径
            save_path = _get_next_version_path(XLS_DIR / f'{match_name}{suffix}')

            # 保存文件
            download.save_as(str(save_path))

            file_size = save_path.stat().st_size if save_path.exists() else 0

            result.success = True
            result.file_path = str(save_path)
            result.file_size = file_size
            result.url_used = url
            result.error = f'Playwright: {download.suggested_filename}'

            browser.close()

    except ImportError:
        result.error = 'Playwright 未安装: pip install playwright'
    except Exception as e:
        result.error = f'Playwright: {type(e).__name__}: {e}'
        # 尝试关闭浏览器
        try:
            browser.close()
        except:
            pass

    return result


def _download_xls_batch_playwright(
    match_name: str,
    file_types: List[str],
    match_id: str,
    config: dict = None,
) -> Dict[str, DownloadResult]:
    """
    使用同一个浏览器实例批量下载多个XLS文件 (节省启动开销)。

    Args:
        match_name: 比赛名称
        file_types: 需要下载的文件类型列表
        match_id: 500.com比赛ID
        config: 配置

    返回: {file_type: DownloadResult}
    """
    from playwright.sync_api import sync_playwright

    if config is None:
        config = load_config()

    results = {}
    timeout_ms = config.get('timeout', 30) * 1000

    try:
        with sync_playwright() as p:
            edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
            browser = p.chromium.launch(executable_path=edge_path, headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            for file_type in file_types:
                suffix = XLS_SUFFIXES[file_type]
                url = _PAGE_URLS[file_type].format(mid=match_id)
                selector = _PAGE_SELECTORS[file_type]

                result = DownloadResult(file_type=file_type, success=False, url_used=url)

                try:
                    page.goto(url, timeout=timeout_ms, wait_until='domcontentloaded')
                    page.wait_for_selector(selector, timeout=10000)

                    with page.expect_download(timeout=30000) as download_info:
                        page.click(selector)

                    download = download_info.value
                    save_path = _get_next_version_path(XLS_DIR / f'{match_name}{suffix}')
                    download.save_as(str(save_path))

                    result.success = True
                    result.file_path = str(save_path)
                    result.file_size = save_path.stat().st_size if save_path.exists() else 0
                    result.error = f'OK: {download.suggested_filename}'

                except Exception as e:
                    result.error = f'{type(e).__name__}: {e}'

                results[file_type] = result

            browser.close()

    except ImportError:
        err = DownloadResult(file_type='batch', success=False, error='Playwright 未安装: pip install playwright')
        results = {ft: err for ft in file_types}
    except Exception as e:
        err_result = DownloadResult(file_type='batch', success=False, error=f'Playwright: {e}')
        results = {ft: err_result for ft in file_types}

    return results


# ── HTTP会话 ──

def _create_session(config: dict) -> requests.Session:
    """创建带cookie的HTTP会话"""
    session = requests.Session()
    session.headers.update(HEADERS)

    cookie_str = config.get('cookie_string', '')
    if cookie_str:
        for pair in cookie_str.split(';'):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                session.cookies.set(key.strip(), value.strip())

    return session


# ── XLS下载核心 ──

@dataclass
class DownloadResult:
    """单次下载结果"""
    file_type: str          # 'european' / 'asian' / 'totals' / 'handicap_index'
    success: bool
    file_path: str = ''     # 保存路径
    url_used: str = ''      # 实际使用的下载URL
    file_size: int = 0      # 文件大小(bytes)
    error: str = ''         # 错误信息
    is_duplicate: bool = False  # 是否重复(与已有文件内容相同)


def download_xls(
    match_name: str,
    file_type: str,
    match_id: str,
    config: dict = None,
) -> DownloadResult:
    """
    下载单个XLS文件。

    Args:
        match_name: 比赛名称, 如 '法国VS塞内加尔'
        file_type: 文件类型, 'european'/'asian'/'totals'/'handicap_index'
        match_id: 500.com比赛ID
        config: 配置字典

    返回: DownloadResult
    """
    if config is None:
        config = load_config()

    suffix = XLS_SUFFIXES[file_type]
    save_path = XLS_DIR / f'{match_name}{suffix}'

    result = DownloadResult(file_type=file_type, success=False)
    session = _create_session(config)
    timeout = config.get('timeout', 30)

    # 尝试所有可能的下载URL
    url_patterns = URL_500COM['xls_downloads'][file_type]
    last_error = ''

    for pattern in url_patterns:
        url = pattern.format(mid=match_id)
        result.url_used = url

        for attempt in range(config.get('max_retries', 3)):
            try:
                resp = session.get(url, headers=HEADERS, timeout=timeout)

                if resp.status_code == 200 and len(resp.content) > 500:
                    # 检查是否是有效的XLS文件 (OLE2 header: D0CF11E0)
                    if resp.content[:4] == b'\xD0\xCF\x11\xE0':
                        # 检查是否与已存在文件相同
                        if save_path.exists():
                            existing_hash = hashlib.md5(save_path.read_bytes()).hexdigest()
                            new_hash = hashlib.md5(resp.content).hexdigest()
                            if existing_hash == new_hash:
                                result.success = True
                                result.file_path = str(save_path)
                                result.file_size = len(resp.content)
                                result.is_duplicate = True
                                result.error = '内容相同, 跳过'
                                return result

                        # 处理版本编号 (与500.com下载逻辑一致)
                        final_path = _get_next_version_path(save_path)
                        final_path.write_bytes(resp.content)

                        result.success = True
                        result.file_path = str(final_path)
                        result.file_size = len(resp.content)
                        return result

                    else:
                        # 可能是HTML重定向页面或错误页
                        last_error = f'非XLS格式 (got {resp.content[:20]})'
                        break  # 尝试下一个URL

                elif resp.status_code == 404:
                    last_error = f'404 Not Found: {url}'
                    break  # 尝试下一个URL pattern

                else:
                    last_error = f'HTTP {resp.status_code}'
                    if attempt < config.get('max_retries', 3) - 1:
                        time.sleep(config.get('download_delay', 2))

            except requests.RequestException as e:
                last_error = str(e)
                if attempt < config.get('max_retries', 3) - 1:
                    time.sleep(config.get('download_delay', 2))

    result.error = last_error
    return result


def _get_next_version_path(base_path: Path) -> Path:
    """
    获取下一个可用的版本文件路径。

    与500.com下载逻辑一致:
      基础文件: 法国VS塞内加尔(世界杯)欧洲数据.xls
      第1次重复: 法国VS塞内加尔(世界杯)欧洲数据 (1).xls
      第2次重复: 法国VS塞内加尔(世界杯)欧洲数据 (2).xls
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem   # e.g. "法国VS塞内加尔(世界杯)欧洲数据"
    ext = base_path.suffix  # ".xls"

    version = 1
    while True:
        new_name = f'{stem} ({version}){ext}'
        new_path = base_path.parent / new_name
        if not new_path.exists():
            return new_path
        version += 1


def download_all_xls(
    match_name: str,
    match_id: str = None,
    config: dict = None,
) -> Dict[str, DownloadResult]:
    """
    下载一场比赛的全部4个XLS文件。

    Args:
        match_name: 比赛名称
        match_id: 500.com比赛ID (None=自动查找)
        config: 配置字典

    返回: {'european': DownloadResult, 'asian': ..., 'totals': ..., 'handicap_index': ...}
    """
    if config is None:
        config = load_config()

    # 查找match_id
    if not match_id:
        match_id = find_match_id(match_name)

    if not match_id:
        error_result = DownloadResult(
            file_type='all', success=False,
            error=f'未找到比赛ID: {match_name}。请先配置: python auto_fetch_xls.py --add "{match_name}" --id <500com_id>'
        )
        return {k: error_result for k in XLS_SUFFIXES}

    results = {}

    print(f'📥 下载 {match_name} (ID: {match_id}) ...')

    # 🔴 优先使用 Playwright (本机Edge), 失败则回退到直接HTTP
    pw_failed = False
    try:
        _find_edge()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=_find_edge(), headless=True)
            browser.close()
    except Exception:
        pw_failed = True

    if not pw_failed:
        # 使用Playwright批量下载
        results = _download_xls_batch_playwright(
            match_name,
            list(XLS_SUFFIXES.keys()),
            match_id,
            config,
        )
        for file_type, result in results.items():
            if result.success:
                fname = Path(result.file_path).name
                print(f'  ✅ {file_type}: {fname} ({result.file_size:,} bytes)')
            else:
                print(f'  ❌ {file_type}: {result.error}')
    else:
        # 回退: 直接HTTP尝试
        print('  ⚠️ Playwright/Edge 不可用, 尝试直接HTTP...')
        delay = config.get('download_delay', 2)
        for file_type in XLS_SUFFIXES:
            result = download_xls(match_name, file_type, match_id, config)
            results[file_type] = result
            if result.success:
                status = '🔄 跳过(内容相同)' if result.is_duplicate else '✅ 已保存'
                fname = Path(result.file_path).name
                print(f'  {status} {file_type}: {fname} ({result.file_size:,} bytes)')
            else:
                print(f'  ❌ {file_type}: {result.error}')
            if file_type != list(XLS_SUFFIXES.keys())[-1]:
                time.sleep(delay)

    # 更新最后下载时间
    if match_name in config.get('matches', {}):
        config['matches'][match_name]['last_fetch'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        save_config(config)

    return results


# ── 缺文件检查 ──

def check_missing_files(match_name: str) -> List[str]:
    """
    检查一场比赛缺少哪些XLS文件。

    返回: 缺失的文件类型列表
    """
    missing = []
    for file_type, suffix in XLS_SUFFIXES.items():
        base_path = XLS_DIR / f'{match_name}{suffix}'
        # 检查基础文件和所有版本
        stem = base_path.stem
        pattern = str(XLS_DIR / f'{stem}*.xls')
        import glob
        found = glob.glob(pattern)
        if not found:
            missing.append(file_type)
    return missing


# ── 批量操作 ──

def download_batch(
    match_names: List[str],
    match_ids: Dict[str, str] = None,
    skip_existing: bool = False,
) -> Dict[str, Dict[str, DownloadResult]]:
    """
    批量下载多场比赛的XLS文件。

    Args:
        match_names: 比赛名列表
        match_ids: 预配置的比赛ID映射 (可选)
        skip_existing: 是否跳过已有文件的比赛

    返回: {match_name: {file_type: DownloadResult}}
    """
    config = load_config()

    # 合并match_ids到配置
    if match_ids:
        if 'matches' not in config:
            config['matches'] = {}
        for name, mid in match_ids.items():
            config['matches'][name] = {'match_id': mid, 'added': 'manual'}
        save_config(config)

    all_results = {}
    total = len(match_names)

    for i, match_name in enumerate(match_names, 1):
        print(f'\n[{i}/{total}] {match_name}')

        if skip_existing:
            missing = check_missing_files(match_name)
            if not missing:
                print(f'  ✅ 全部文件已存在, 跳过')
                continue

        results = download_all_xls(match_name, config=config)
        all_results[match_name] = results

    # 汇总
    success_count = sum(
        1 for r in all_results.values()
        for rr in r.values()
        if rr.success and not rr.is_duplicate
    )
    skip_count = sum(
        1 for r in all_results.values()
        for rr in r.values()
        if rr.is_duplicate
    )
    fail_count = sum(
        1 for r in all_results.values()
        for rr in r.values()
        if not rr.success
    )

    print(f'\n{"="*50}')
    print(f'📊 下载汇总: {success_count} 新增 | {skip_count} 跳过 | {fail_count} 失败')
    print(f'{"="*50}')

    return all_results


# ── CLI ──

def main():
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print('\n用法:')
        print('  python auto_fetch_xls.py --match "法国VS塞内加尔"')
        print('  python auto_fetch_xls.py --all')
        print('  python auto_fetch_xls.py --add "法国VS塞内加尔" --id 1234567')
        print('  python auto_fetch_xls.py --list')
        print('  python auto_fetch_xls.py --check "法国VS塞内加尔"')
        print('  python auto_fetch_xls.py --discover   # 从500.com发现所有比赛ID')
        return

    if '--list' in sys.argv:
        config = load_config()
        matches = config.get('matches', {})
        if matches:
            print(f'已配置 {len(matches)} 场比赛:')
            for name, info in matches.items():
                last = info.get('last_fetch', info.get('discovered_at', '未知'))
                print(f'  {name:30s} | ID: {info.get("match_id", "?"):12s} | 上次下载: {last}')
        else:
            print('暂无配置。使用 --add 添加比赛')
        return

    if '--add' in sys.argv and '--id' in sys.argv:
        match_idx = sys.argv.index('--add') + 1
        id_idx = sys.argv.index('--id') + 1
        if match_idx < len(sys.argv) and id_idx < len(sys.argv):
            match_name = sys.argv[match_idx]
            match_id = sys.argv[id_idx]
            config = load_config()
            if 'matches' not in config:
                config['matches'] = {}
            config['matches'][match_name] = {
                'match_id': match_id,
                'added': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }
            save_config(config)
            print(f'✅ 已添加: {match_name} → ID:{match_id}')
        return

    if '--discover' in sys.argv:
        print('🔍 从500.com赛程页发现比赛...')
        discovered = discover_match_ids()
        if discovered:
            print(f'\n发现 {len(discovered)} 场比赛:')
            for name, mid in discovered.items():
                print(f'  {name:30s} → ID: {mid}')

            # 自动保存
            config = load_config()
            if 'matches' not in config:
                config['matches'] = {}
            for name, mid in discovered.items():
                if name not in config['matches']:
                    config['matches'][name] = {
                        'match_id': mid,
                        'discovered_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    }
            save_config(config)
            print(f'\n✅ 已保存到配置文件')
        else:
            print('未发现比赛 (可能需要配置cookie或检查网络)')
        return

    if '--check' in sys.argv:
        idx = sys.argv.index('--check') + 1
        if idx < len(sys.argv):
            match_name = sys.argv[idx]
            missing = check_missing_files(match_name)
            if missing:
                print(f'❌ {match_name} 缺少 {len(missing)} 个文件: {missing}')
            else:
                print(f'✅ {match_name} 全部4个文件已就绪')
        return

    if '--match' in sys.argv:
        idx = sys.argv.index('--match') + 1
        if idx < len(sys.argv):
            match_name = sys.argv[idx]
            results = download_all_xls(match_name)
            return

    if '--all' in sys.argv:
        config = load_config()
        match_names = list(config.get('matches', {}).keys())
        if not match_names:
            print('没有配置的比赛。使用 --add 或 --discover 添加')
            return
        print(f'批量下载 {len(match_names)} 场比赛...')
        download_batch(match_names, skip_existing=True)
        return

    # 默认: 交互模式
    print('请指定操作: --match / --all / --add / --list / --check / --discover')


if __name__ == '__main__':
    main()

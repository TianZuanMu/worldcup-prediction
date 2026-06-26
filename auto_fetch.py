# -*- coding: utf-8 -*-
"""
自动数据获取 — 统一入口

替代人工手动操作:
  1. XLS文件下载 (500.com → D:/)     → auto_fetch_xls
  2. 必发数据抓取 (bfindex/500.com)   → auto_fetch_betfair

一键操作:
  python auto_fetch.py "法国VS塞内加尔"
  python auto_fetch.py --all
  python auto_fetch.py --pipeline     # 完整管道: 获取→分析→报告

自动化完整管道:
  ① 自动获取XLS (500.com)
  ② 自动抓取必发 (bfindex/500.com)
  ③ 自动获取赔率 (the-odds-api)
  ④ 自动生成趋势分析
  ⑤ 自动生成赛前报告 (含V2.6规则匹配)

用法:
  # 单场全自动
  python auto_fetch.py "法国VS塞内加尔"

  # 批量 (所有已配置的比赛)
  python auto_fetch.py --all

  # 仅XLS
  python auto_fetch.py "法国VS塞内加尔" --xls-only

  # 仅必发
  python auto_fetch.py "法国VS塞内加尔" --bf-only

  # 完整管道 (含赔率获取+趋势+报告)
  python auto_fetch.py "法国VS塞内加尔" --full-pipeline

  # 发现新比赛
  python auto_fetch.py --discover

  # 配置比赛
  python auto_fetch.py --add "法国VS塞内加尔" --xls-id 1234567 --bf-url "https://..."

  # 查看状态
  python auto_fetch.py --status
"""

import json
import sys
import subprocess
import time
import glob
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# 🆕 V3.4: 比赛时间均为北京时间(UTC+8)
BJT = timezone(timedelta(hours=8))
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

from auto_fetch_xls import (
    download_all_xls, download_batch, check_missing_files,
    find_match_id, discover_match_ids, load_config, save_config,
    XLS_SUFFIXES,
)
from auto_fetch_betfair import (
    fetch_betfair_data, fetch_batch as bf_batch,
    load_config as bf_load_config,
)

PROJECT_DIR = Path(r"C:\Users\A\PyCharmMiscProject")


# ── 比赛名列表 (从赛程/配置获取) ──

def get_all_configured_matches() -> List[str]:
    """获取所有已配置的比赛 (来自auto_fetch_config.json)"""
    config = load_config()
    return list(config.get('matches', {}).keys())


def get_upcoming_matches(hours_ahead: int = 48) -> List[str]:
    """
    获取即将开始的比赛列表 (从赛前高频赔率.py的赛程表)。

    Args:
        hours_ahead: 未来多少小时内的比赛
    """
    try:
        # 从赛前高频赔率.py导入赛程
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'pre_match_schedule',
            PROJECT_DIR / '赛前高频赔率.py'
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        now = datetime.now(tz=BJT)
        cutoff = now + timedelta(hours=hours_ahead)

        matches = []
        for m in module.MATCH_SCHEDULE:
            month, day, hour, minute, home, away = m
            try:
                ko = datetime(2026, month, day, hour, minute, tzinfo=BJT)
            except ValueError:
                continue
            if now <= ko <= cutoff:
                matches.append(f'{home}VS{away}')
        return matches
    except Exception:
        return []


# ── 统一获取 ──

@dataclass
class FetchResult:
    match_name: str
    xls: dict = None       # {file_type: DownloadResult}
    betfair: dict = None   # saved data dict
    errors: list = field(default_factory=list)

    @property
    def xls_ready(self) -> bool:
        if not self.xls:
            return False
        return all(r.success for r in self.xls.values())

    @property
    def betfair_ready(self) -> bool:
        return self.betfair is not None

    @property
    def all_ready(self) -> bool:
        return self.xls_ready and self.betfair_ready


def fetch_all_for_match(
    match_name: str,
    xls_match_id: str = None,
    bf_source: str = None,
    kickoff: str = '',
    include_xls: bool = True,
    include_betfair: bool = True,
    config: dict = None,
) -> FetchResult:
    """
    为一场比赛获取全部数据 (XLS + 必发)。

    Args:
        match_name: 比赛名称
        xls_match_id: 500.com比赛ID (None=自动查找)
        bf_source: 必发数据源 (None=使用默认)
        kickoff: 开球时间
        include_xls: 是否获取XLS
        include_betfair: 是否获取必发
        config: 配置

    返回: FetchResult
    """
    if config is None:
        config = load_config()

    result = FetchResult(match_name=match_name)

    print(f'\n{"="*60}')
    print(f'  🚀 自动获取: {match_name}')
    print(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'{"="*60}')

    # 1. XLS
    if include_xls:
        print(f'\n📥 [1/2] XLS文件 ...')
        if not xls_match_id:
            xls_match_id = find_match_id(match_name)
        if xls_match_id:
            result.xls = download_all_xls(match_name, match_id=xls_match_id, config=config)
        else:
            from auto_fetch_xls import DownloadResult
            err = DownloadResult(file_type='all', success=False,
                               error=f'未找到500.com比赛ID。请先配置: python auto_fetch.py --add "{match_name}" --xls-id <id>')
            result.xls = {k: err for k in XLS_SUFFIXES}
            result.errors.append('XLS: 无match_id')
    else:
        print(f'\n⏭️  [1/2] XLS: 跳过')

    # 2. 必发
    if include_betfair:
        print(f'\n📊 [2/2] 必发数据 ...')
        bf_result = fetch_betfair_data(
            match_name=match_name,
            match_id=xls_match_id,  # 复用XLS的match_id
            source=bf_source,
            kickoff=kickoff,
            config=config,
        )
        result.betfair = bf_result
        if not bf_result:
            result.errors.append('必发: 获取失败')
    else:
        print(f'\n⏭️  [2/2] 必发: 跳过')

    # 汇总
    print(f'\n{"─"*50}')
    status_parts = []
    if include_xls:
        xls_ok = sum(1 for r in (result.xls or {}).values() if r.success)
        status_parts.append(f'XLS: {xls_ok}/4')
    if include_betfair:
        status_parts.append(f'必发: {"✅" if result.betfair else "❌"}')
    print(f'  📋 {match_name}: {", ".join(status_parts)}')
    print(f'{"─"*50}')

    return result


def fetch_all_matches(
    match_names: List[str] = None,
    hours_ahead: int = 48,
    include_xls: bool = True,
    include_betfair: bool = True,
    config: dict = None,
) -> Dict[str, FetchResult]:
    """
    批量获取所有比赛数据。

    如果未指定match_names, 自动获取即将开始的比赛。
    """
    if config is None:
        config = load_config()

    if not match_names:
        # 自动发现: 已配置 + 即将开始
        configured = set(get_all_configured_matches())
        upcoming = set(get_upcoming_matches(hours_ahead))
        match_names = list(configured | upcoming)

    if not match_names:
        print('❌ 没有可获取的比赛。请先配置: python auto_fetch.py --add ...')
        return {}

    print(f'🎯 准备获取 {len(match_names)} 场比赛的数据')
    print(f'   已配置: {len(get_all_configured_matches())} | 即将开始: {len(get_upcoming_matches(hours_ahead))}')

    results = {}
    delay = config.get('download_delay', 2)

    for i, name in enumerate(match_names, 1):
        xls_id = find_match_id(name)
        ko = ''

        results[name] = fetch_all_for_match(
            match_name=name,
            xls_match_id=xls_id,
            include_xls=include_xls,
            include_betfair=include_betfair,
            config=config,
        )

        if i < len(match_names):
            time.sleep(delay)

    # 汇总
    xls_ok = sum(1 for r in results.values() if r.xls_ready)
    bf_ok = sum(1 for r in results.values() if r.betfair_ready)
    all_ok = sum(1 for r in results.values() if r.all_ready)

    print(f'\n{"="*60}')
    print(f'📊 获取汇总: {len(match_names)} 场比赛')
    print(f'   XLS:  {xls_ok}/{len(match_names)} 就绪')
    print(f'   必发: {bf_ok}/{len(match_names)} 就绪')
    print(f'   全部: {all_ok}/{len(match_names)} 就绪')
    print(f'{"="*60}')

    return results


# ── 完整管道 ──

def run_full_pipeline(match_name: str = None) -> str:
    """
    运行完整自动化管道: 获取→赔率→趋势→报告。
    """
    lines = []

    # Step 1: 数据获取
    if match_name:
        print(f'\n{"#"*60}')
        print(f'# 完整自动化管道: {match_name}')
        print(f'{"#"*60}')

        result = fetch_all_for_match(match_name)
        if result.errors:
            lines.append(f'⚠️ 获取问题: {"; ".join(result.errors)}')

    # Step 2: 赔率获取
    print(f'\n📡 [管道 2/4] 获取赔率 (the-odds-api)...')
    try:
        odds_result = subprocess.run(
            [sys.executable, '赔率获取.py'],
            capture_output=True, text=True, timeout=60,
            cwd=str(PROJECT_DIR),
            encoding='utf-8',
        )
        if odds_result.returncode == 0:
            lines.append('✅ 赔率获取成功')
            print('  ✅ 赔率数据已拉取')
        else:
            lines.append(f'⚠️ 赔率获取失败: {odds_result.stderr[:100]}')
            print(f'  ⚠️ 失败: {odds_result.stderr[:100]}')
    except Exception as e:
        lines.append(f'❌ 赔率获取异常: {e}')

    # Step 3: 趋势分析
    print(f'\n📈 [管道 3/4] 趋势分析...')
    try:
        trend_result = subprocess.run(
            [sys.executable, '赔率变化.py'],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_DIR),
            encoding='utf-8',
        )
        if trend_result.returncode == 0:
            lines.append('✅ 趋势分析完成')
            print('  ✅ 趋势分析已保存')
        else:
            lines.append(f'⚠️ 趋势分析失败')
            print(f'  ⚠️ 失败')
    except Exception as e:
        lines.append(f'❌ 趋势分析异常: {e}')

    # Step 4: 赛前报告
    if match_name:
        print(f'\n📋 [管道 4/4] 生成赛前报告...')
        try:
            # 检查是否有必发数据
            bf_text = ''
            bf_data_dir = PROJECT_DIR / 'betfair_data'
            safe_name = match_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
            bf_file = bf_data_dir / f'{safe_name}.json'
            if bf_file.exists():
                with open(bf_file, 'r', encoding='utf-8') as f:
                    bf_data = json.load(f)
                latest = bf_data.get('snapshots', [{}])[-1].get('betfair', {})
                if latest:
                    bf_text = (f"主 {latest['home_price']} {latest.get('home_volume',0)} "
                              f"平 {latest['draw_price']} {latest.get('draw_volume',0)} "
                              f"客 {latest['away_price']} {latest.get('away_volume',0)} "
                              f"盈亏 主{latest['home_pnl']:+} 平{latest['draw_pnl']:+} 客{latest['away_pnl']:+} "
                              f"冷热 主{latest.get('home_heat',0):+} 平{latest.get('draw_heat',0):+} 客{latest.get('away_heat',0):+}")

            report_code = f"""
from pre_match_report import generate_report, format_report
report = generate_report('{match_name}', betfair_text='''{bf_text}''')
print(format_report(report))
"""
            report_result = subprocess.run(
                [sys.executable, '-c', report_code],
                capture_output=True, text=True, timeout=30,
                cwd=str(PROJECT_DIR),
                encoding='utf-8',
            )
            if report_result.returncode == 0:
                lines.append('✅ 赛前报告已生成')
                print(report_result.stdout)
            else:
                lines.append(f'⚠️ 报告生成失败: {report_result.stderr[:200]}')
                print(f'  ⚠️ {report_result.stderr[:200]}')
        except Exception as e:
            lines.append(f'❌ 报告异常: {e}')

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
#  智能调度层 — 按预测阶段自动触发·避免重复拉取
# ═══════════════════════════════════════════════════════════

# 阶段 → 数据过期阈值 (小时)
# XLS和必发变化慢, 按阶段设定合理的刷新间隔
PHASE_STALENESS = {
    'P1': {'xls': 6.0, 'betfair': 6.0},    # 赛前24h+: 每6小时刷新
    'P2': {'xls': 1.0, 'betfair': 1.0},    # 赛前4-12h: 每1小时刷新
    'P3': {'xls': 1.0, 'betfair': 1.0},    # 赛前1.5-4h: 每1小时刷新
    'P4': {'xls': 0.5, 'betfair': 0.5},    # 赛前<90min: 每30分钟刷新
    'POST': {'xls': 99, 'betfair': 99},     # 已开赛: 不再拉取
}


def get_match_schedule() -> List[Tuple[str, datetime]]:
    """
    从赛程表获取所有未来比赛及其开球时间。

    返回: [(match_name, kickoff_datetime), ...] 按开球时间排序
    """
    matches = []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'pre_match_schedule',
            PROJECT_DIR / '赛前高频赔率.py'
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for m in module.MATCH_SCHEDULE:
            month, day, hour, minute, home, away = m
            if '待更新' in home:
                continue
            try:
                ko = datetime(2026, month, day, hour, minute)
                match_name = f'{home}VS{away}'
                matches.append((match_name, ko))
            except ValueError:
                continue

        matches.sort(key=lambda x: x[1])
    except Exception:
        pass

    return matches


def get_phase(hours_to_kickoff: float) -> str:
    """
    根据距开球时间判定预测阶段。

    P1: >12h  (早期)
    P2: 4-12h (中期)
    P3: 1.5-4h (临场前)
    P4: 0-1.5h (即场)
    POST: <0 (已开赛)
    """
    if hours_to_kickoff < 0:
        return 'POST'
    elif hours_to_kickoff < 1.5:
        return 'P4'
    elif hours_to_kickoff < 4:
        return 'P3'
    elif hours_to_kickoff < 12:
        return 'P2'
    else:
        return 'P1'


def get_data_freshness(match_name: str) -> Dict[str, Optional[float]]:
    """
    检查数据新鲜度 (距上次成功获取的小时数)。

    返回: {'xls': hours_since_last or None, 'betfair': hours_since_last or None}
           None = 从未获取过
    """
    now = datetime.now()
    freshness = {'xls': None, 'betfair': None}

    # XLS: 检查 D:\ 下该比赛的最新文件修改时间
    xls_dir = Path(r'D:')
    newest_mtime = None
    for suffix_key, suffix in XLS_SUFFIXES.items():
        stem = f'{match_name}{suffix}'.replace('.xls', '')
        pattern = str(xls_dir / f'{stem}*.xls')
        for fpath in glob.glob(pattern):
            mtime = os.path.getmtime(fpath)
            if newest_mtime is None or mtime > newest_mtime:
                newest_mtime = mtime

    if newest_mtime:
        age_hours = (now - datetime.fromtimestamp(newest_mtime)).total_seconds() / 3600
        freshness['xls'] = round(age_hours, 1)

    # Betfair: 检查 betfair_data/ 下该比赛的JSON文件
    bf_dir = PROJECT_DIR / 'betfair_data'
    safe_name = match_name.replace('/', '_').replace('\\', '_').replace(' ', '_')
    bf_file = bf_dir / f'{safe_name}.json'

    if bf_file.exists():
        try:
            with open(bf_file, 'r', encoding='utf-8') as f:
                bf_data = json.load(f)
            snapshots = bf_data.get('snapshots', [])
            if snapshots:
                last_ts = snapshots[-1].get('timestamp', '')
                if last_ts:
                    # 解析 ISO 格式时间戳
                    last_dt = datetime.fromisoformat(last_ts)
                    age_hours = (now - last_dt).total_seconds() / 3600
                    freshness['betfair'] = round(age_hours, 1)
        except Exception:
            pass

    return freshness


def is_data_stale(match_name: str, phase: str,
                  freshness: Dict[str, Optional[float]] = None) -> Dict[str, bool]:
    """
    判断数据是否过期, 需要刷新。

    Args:
        match_name: 比赛名
        phase: 当前预测阶段 (P1-P4/POST)
        freshness: 预计算的新鲜度 (可选, 避免重复计算)

    返回: {'xls': bool, 'betfair': bool}
    """
    if freshness is None:
        freshness = get_data_freshness(match_name)

    thresholds = PHASE_STALENESS.get(phase, PHASE_STALENESS['P1'])
    stale = {}

    for dtype in ('xls', 'betfair'):
        age = freshness.get(dtype)
        if age is None:
            # 从未获取过 → 需要拉取
            stale[dtype] = True
        elif age >= thresholds[dtype]:
            # 超过阈值 → 过期
            stale[dtype] = True
        else:
            # 数据还新鲜
            stale[dtype] = False

    return stale


def auto_fetch_scheduled(config: dict = None, force: bool = False) -> Dict:
    """
    🔴 智能调度入口 — 供 cron/任务计划程序调用。

    逻辑:
      1. 获取所有比赛的赛程
      2. 对每场比赛: 判定阶段 → 检查数据新鲜度 → 仅拉取过期数据
      3. POST阶段(已开赛)自动跳过
      4. 无过期数据时静默退出

    Args:
        config: 配置字典
        force: 强制刷新 (忽略过期阈值)

    建议调度频率: 每30分钟 (cron: */30 * * * *)

    返回: {'checked': N, 'fetched_xls': [...], 'fetched_bf': [...], 'skipped': [...]}
    """
    if config is None:
        config = load_config()

    now = datetime.now()

    # ── 每24h自动刷新比赛ID ──
    last_discovery = config.get('last_discovery', '')
    should_discover = True
    if last_discovery:
        try:
            last_dt = datetime.fromisoformat(last_discovery)
            if (now - last_dt).total_seconds() / 3600 < 23:
                should_discover = False
        except ValueError:
            pass
    if should_discover:
        try:
            from auto_fetch_xls import discover_match_ids
            discovered = discover_match_ids()
            if discovered:
                config['last_discovery'] = now.strftime('%Y-%m-%d %H:%M:%S')
                save_config(config)
        except Exception:
            pass

    schedule = get_match_schedule()

    if not schedule:
        return {'checked': 0, 'fetched_xls': [], 'fetched_bf': [], 'skipped': [],
                'message': '无赛程数据'}

    fetched_xls = []
    fetched_bf = []
    skipped = []
    errors = []

    # 🆕 V4.2: 加载完赛结果·自动排除已完赛比赛
    completed_matches = set()
    completed_filtered = 0
    try:
        import json
        from pathlib import Path
        backtest_file = Path(__file__).parent / 'backtest' / 'matches.json'
        if backtest_file.exists():
            with open(backtest_file, 'r', encoding='utf-8') as f:
                bm = json.load(f)
            for m in bm:
                if m.get('actual', {}).get('result', 'pending') != 'pending':
                    completed_matches.add(m['match_name'])
    except Exception:
        pass

    # 只关注: 赛前48h内 + 赛后2h内 + 未完赛
    active_matches = []
    completed_filtered = 0
    for name, ko in schedule:
        if name in completed_matches:
            completed_filtered += 1
            continue
        hours_to_ko = (ko - now).total_seconds() / 3600
        if hours_to_ko < 48 and hours_to_ko > -2:  # 赛前48h ~ 赛后2h
            phase = get_phase(hours_to_ko)
            active_matches.append((name, ko, phase, hours_to_ko))

    if not active_matches:
        return {'checked': len(schedule), 'fetched_xls': [], 'fetched_bf': [],
                'skipped': [m[0] for m in schedule],
                'message': '无活跃比赛 (赛前48h~赛后2h)'}

    delay = config.get('download_delay', 2)

    for i, (name, ko, phase, hours_to_ko) in enumerate(active_matches):
        freshness = get_data_freshness(name)
        stale = is_data_stale(name, phase, freshness)

        if force:
            stale['xls'] = True
            stale['betfair'] = True

        need_xls = stale['xls']
        need_bf = stale['betfair']

        if not need_xls and not need_bf:
            age_xls = freshness['xls']
            age_bf = freshness['betfair']
            skipped.append(f'{name} [{phase}] XLS:{age_xls}h前 BF:{age_bf}h前')
            continue

        # 需要拉取
        ko_label = f'{ko.strftime("%m/%d %H:%M")}'
        reasons = []
        if need_xls:
            age = freshness['xls']
            reasons.append(f'XLS过期({age}h前)' if age else 'XLS无数据')
        if need_bf:
            age = freshness['betfair']
            reasons.append(f'BF过期({age}h前)' if age else 'BF无数据')

        print(f'\n🔄 [{phase}] {name} ({ko_label} | 距开球{hours_to_ko:.1f}h)')
        print(f'   原因: {", ".join(reasons)}')

        xls_id = find_match_id(name)
        ko_str = ko.strftime('%Y-%m-%dT%H:%M')

        # XLS
        if need_xls and xls_id:
            try:
                results = download_all_xls(name, match_id=xls_id, config=config)
                ok = sum(1 for r in results.values() if r.success)
                if ok > 0:
                    fetched_xls.append(f'{name} ({ok}/4)')
            except Exception as e:
                errors.append(f'XLS:{name}:{e}')

        # Betfair
        if need_bf:
            try:
                bf_result = fetch_betfair_data(
                    match_name=name,
                    match_id=xls_id,
                    kickoff=ko_str,
                    config=config,
                )
                if bf_result:
                    fetched_bf.append(f'{name} ({bf_result.get("snapshot_count", "?")}快照)')
                else:
                    errors.append(f'BF:{name}:获取失败')
            except Exception as e:
                errors.append(f'BF:{name}:{e}')

        if i < len(active_matches) - 1:
            time.sleep(delay)

    summary = {
        'time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'checked': len(active_matches),
        'fetched_xls': fetched_xls,
        'fetched_bf': fetched_bf,
        'skipped': skipped,
        'errors': errors,
    }

    # 输出摘要
    print(f'\n{"="*55}')
    print(f'📊 智能调度摘要 [{summary["time"]}]')
    print(f'   检查: {len(active_matches)}场活跃比赛 (已排除{completed_filtered}场完赛)')
    if fetched_xls:
        print(f'   XLS刷新: {len(fetched_xls)}场 — {", ".join(fetched_xls)}')
    if fetched_bf:
        print(f'   必发刷新: {len(fetched_bf)}场 — {", ".join(fetched_bf)}')
    if skipped:
        print(f'   跳过(数据新鲜): {len(skipped)}场')
    if errors:
        print(f'   ⚠️ 错误: {len(errors)} — {"; ".join(errors[:3])}')
    if not fetched_xls and not fetched_bf:
        print(f'   ✅ 所有数据均为最新, 无需拉取')
    print(f'{"="*55}')

    # 🆕 V4.2: 每次数据刷新后自动重载积分榜+小组排名
    try:
        from knockout_motivation import refresh_standings
        refresh_standings()
        print('📊 积分榜已刷新')
        from update_group_predictions import predict_all, save_json, generate_html
        groups = predict_all()
        save_json(groups)
        generate_html(groups)
        print('📊 小组排名已更新')
    except Exception as e:
        print(f'⚠️ 积分/排名更新异常: {e}')

    return summary


def auto_fetch_cron_wrapper():
    """
    供 cron 直接调用的轻量入口 (最小输出)。

    用法 (cron / 任务计划程序):
      PYTHONIOENCODING=utf-8 python -c "from auto_fetch import auto_fetch_cron_wrapper; auto_fetch_cron_wrapper()"

    建议频率: 每30分钟 (cron: 7,37 * * * *)
    """
    config = load_config()
    summary = auto_fetch_scheduled(config=config)

    # 单行日志 (便于cron日志记录)
    parts = [f'[{summary["time"]}]', f'查{summary["checked"]}场']
    if summary['fetched_xls']:
        parts.append(f'XLS:{len(summary["fetched_xls"])}')
    if summary['fetched_bf']:
        parts.append(f'BF:{len(summary["fetched_bf"])}')
    if summary['skipped']:
        parts.append(f'跳过:{len(summary["skipped"])}')
    if summary['errors']:
        parts.append(f'错:{len(summary["errors"])}')
    if not summary['fetched_xls'] and not summary['fetched_bf']:
        parts.append('无需拉取')

    print(' | '.join(parts))


# ═══════════════════════════════════════════════════════════


# ── 状态检查 ──

def check_status(match_name: str = None) -> str:
    """检查数据就绪状态"""
    lines = []
    config = load_config()

    if match_name:
        matches = [match_name]
    else:
        matches = get_all_configured_matches()
        upcoming = get_upcoming_matches(48)
        for m in upcoming:
            if m not in matches:
                matches.append(m)

    if not matches:
        return '没有配置的比赛。使用 --add 添加'

    lines.append(f'{"="*70}')
    lines.append(f'  📊 数据就绪状态 ({datetime.now().strftime("%m-%d %H:%M")})')
    lines.append(f'{"="*70}')
    lines.append(f'{"比赛":24s} | {"XLS":6s} | {"必发":6s} | {"赔率":6s} | {"500.com ID":12s} | {"配置":6s}')
    lines.append('-' * 70)

    for name in matches:
        # XLS状态
        missing = check_missing_files(name)
        xls_status = f'✅ {4-len(missing)}/4' if len(missing) < 4 else '❌ 0/4'

        # 必发状态
        bf_data_dir = PROJECT_DIR / 'betfair_data'
        safe_name = name.replace('/', '_').replace('\\', '_').replace(' ', '_')
        bf_file = bf_data_dir / f'{safe_name}.json'
        if bf_file.exists():
            with open(bf_file, 'r', encoding='utf-8') as f:
                bf_data = json.load(f)
            count = bf_data.get('snapshot_count', 0)
            bf_status = f'✅ {count}快照'
        else:
            bf_status = '❌ 无'

        # 赔率趋势
        trend_file = PROJECT_DIR / 'odds_trend_analysis_text.csv'
        odds_status = '?'
        if trend_file.exists():
            import csv
            with open(trend_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                found = any(
                    (_extract_home(row['主队']) in name or _extract_home(row['客队']) in name)
                    for row in reader
                )
            odds_status = '✅' if found else '❌'
        else:
            odds_status = '❌ 无CSV'

        # 500.com ID
        mid = ''
        is_configured = '✅' if name in config.get('matches', {}) else '⚠️ 未配置'
        if name in config.get('matches', {}):
            mid = config['matches'][name].get('match_id', '?')

        lines.append(f'{name:24s} | {xls_status:6s} | {bf_status:6s} | {odds_status:6s} | {mid:12s} | {is_configured:6s}')

    lines.append('-' * 70)
    return '\n'.join(lines)


def _extract_home(match_name: str) -> str:
    """从中文比赛名提取主队英文名"""
    mapping = {
        '法国': 'France', '塞内加尔': 'Senegal', '伊拉克': 'Iraq', '挪威': 'Norway',
        '阿根廷': 'Argentina', '阿尔及利亚': 'Algeria', '奥地利': 'Austria', '约旦': 'Jordan',
        '西班牙': 'Spain', '佛得角': 'Cape Verde', '比利时': 'Belgium', '埃及': 'Egypt',
        '沙特': 'Saudi Arabia', '乌拉圭': 'Uruguay', '伊朗': 'Iran', '新西兰': 'New Zealand',
        '巴西': 'Brazil', '摩洛哥': 'Morocco', '海地': 'Haiti', '苏格兰': 'Scotland',
        '澳大利亚': 'Australia', '土耳其': 'Turkey', '卡塔尔': 'Qatar', '瑞士': 'Switzerland',
        '加拿大': 'Canada', '波黑': 'Bosnia & Herzegovina', '美国': 'USA', '巴拉圭': 'Paraguay',
        '荷兰': 'Netherlands', '日本': 'Japan', '德国': 'Germany', '库拉索': 'Curaçao',
        '科特迪瓦': 'Ivory Coast', '厄瓜多尔': 'Ecuador', '瑞典': 'Sweden', '突尼斯': 'Tunisia',
        '墨西哥': 'Mexico', '韩国': 'South Korea', '捷克': 'Czech Republic', '南非': 'South Africa',
        '葡萄牙': 'Portugal', '民主刚果': 'DR Congo', '英格兰': 'England', '克罗地亚': 'Croatia',
        '加纳': 'Ghana', '巴拿马': 'Panama', '乌兹别克斯坦': 'Uzbekistan', '哥伦比亚': 'Colombia',
    }
    for cn, en in mapping.items():
        if cn in match_name:
            return en
    return match_name.split('VS')[0].strip() if 'VS' in match_name else match_name


# ── CLI ──

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('\n快速开始:')
        print('  1. 首次使用: python auto_fetch.py --discover')
        print('  2. 配置比赛: python auto_fetch.py --add "法国VS塞内加尔" --xls-id xxxxx')
        print('  3. 查看状态: python auto_fetch.py --status')
        print('  4. 一键获取: python auto_fetch.py "法国VS塞内加尔"')
        return

    arg1 = sys.argv[1] if len(sys.argv) > 1 else ''

    # --discover: 从500.com发现比赛ID
    if arg1 == '--discover' or '--discover' in sys.argv:
        print('🔍 从500.com发现世界杯比赛ID...')
        discovered = discover_match_ids()
        if discovered:
            config = load_config()
            if 'matches' not in config:
                config['matches'] = {}
            new_count = 0
            for name, mid in discovered.items():
                if name not in config['matches']:
                    config['matches'][name] = {
                        'match_id': mid,
                        'discovered_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    }
                    new_count += 1
            save_config(config)
            print(f'\n发现 {len(discovered)} 场比赛, 新增 {new_count} 场配置')
            for name, mid in discovered.items():
                print(f'  {name:30s} → ID: {mid}')
        else:
            print('⚠️ 未能从500.com发现比赛。')
            print('   可能原因: 网络问题 / 500.com改版 / 需要cookie')
            print('   替代方案: 手动配置 python auto_fetch.py --add "队名" --xls-id <id>')
        return

    # --status: 查看数据状态
    if arg1 == '--status':
        match_name = None
        if '--match' in sys.argv:
            idx = sys.argv.index('--match') + 1
            if idx < len(sys.argv):
                match_name = sys.argv[idx]
        print(check_status(match_name))
        return

    # --add: 手动配置比赛
    if arg1 == '--add':
        match_name = sys.argv[2] if len(sys.argv) > 2 else ''
        if not match_name:
            print('请指定比赛名: python auto_fetch.py --add "法国VS塞内加尔" --xls-id <id>')
            return

        xls_id = ''
        bf_url = ''

        if '--xls-id' in sys.argv:
            idx = sys.argv.index('--xls-id') + 1
            if idx < len(sys.argv):
                xls_id = sys.argv[idx]
        if '--bf-url' in sys.argv:
            idx = sys.argv.index('--bf-url') + 1
            if idx < len(sys.argv):
                bf_url = sys.argv[idx]

        config = load_config()
        if 'matches' not in config:
            config['matches'] = {}

        entry = config['matches'].get(match_name, {})
        if xls_id:
            entry['match_id'] = xls_id
        entry['added'] = datetime.now().strftime('%Y-%m-%d %H:%M')

        config['matches'][match_name] = entry

        if bf_url:
            if 'betfair_matches' not in config:
                config['betfair_matches'] = {}
            config['betfair_matches'][match_name] = {
                'url': bf_url,
                'added': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }

        save_config(config)
        print(f'✅ 已配置: {match_name}')
        if xls_id:
            print(f'   500.com ID: {xls_id}')
        if bf_url:
            print(f'   必发URL: {bf_url}')
        return

    # --all: 批量获取所有比赛
    if arg1 == '--all':
        include_xls = '--bf-only' not in sys.argv
        include_bf = '--xls-only' not in sys.argv
        results = fetch_all_matches(include_xls=include_xls, include_betfair=include_bf)
        return

    # --cron: 智能调度模式 (供 cron/任务计划程序调用)
    if arg1 == '--cron':
        force = '--force' in sys.argv
        auto_fetch_scheduled(force=force)
        return

    # --full-pipeline: 完整管道
    if arg1 == '--full-pipeline' or '--full-pipeline' in sys.argv:
        match_name = None
        if '--match' in sys.argv:
            idx = sys.argv.index('--match') + 1
            if idx < len(sys.argv):
                match_name = sys.argv[idx]
        log = run_full_pipeline(match_name)
        print(f'\n📋 管道日志:\n{log}')
        return

    # 默认: 单场获取 (第一个非 -- 参数作为比赛名)
    if not arg1.startswith('--'):
        match_name = arg1
        include_xls = '--bf-only' not in sys.argv
        include_bf = '--xls-only' not in sys.argv

        if '--full-pipeline' in sys.argv:
            log = run_full_pipeline(match_name)
            print(f'\n📋 管道日志:\n{log}')
        else:
            result = fetch_all_for_match(
                match_name,
                include_xls=include_xls,
                include_betfair=include_bf,
            )

        return

    # 处理 --xls-only 或 --bf-only 但没有比赛名的情况
    if '--match' in sys.argv:
        idx = sys.argv.index('--match') + 1
        if idx < len(sys.argv):
            match_name = sys.argv[idx]
            include_xls = '--bf-only' not in sys.argv
            include_bf = '--xls-only' not in sys.argv
            fetch_all_for_match(match_name, include_xls=include_xls, include_betfair=include_bf)
            return

    print('未知参数。使用 --help 查看用法')


if __name__ == '__main__':
    main()

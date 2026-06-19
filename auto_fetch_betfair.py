# -*- coding: utf-8 -*-
"""
必发数据自动抓取器 — 替代人工复制粘贴

功能:
  1. 从必发指数镜像站自动抓取冷热/盈亏/大单数据
  2. 解析HTML表格 → 结构化数据 (BetfairMatch格式)
  3. 自动保存到 betfair_data/ (JSON格式·兼容betfair_store.py)
  4. 多源支持: bfindex.com / 500.com指数页 / 自定义源

用法:
  # 单场抓取
  python auto_fetch_betfair.py --match "法国VS塞内加尔"

  # 批量抓取
  python auto_fetch_betfair.py --all

  # 指定数据源
  python auto_fetch_betfair.py --match "法国VS塞内加尔" --source bfindex

  # 配置比赛URL
  python auto_fetch_betfair.py --add "法国VS塞内加尔" --url "https://..."

架构:
  HTML页面 → BeautifulSoup解析 → 结构化dict → BetfairMatch → betfair_store.save_betfair()
  支持3种数据源格式:
    Source A: bfindex.com 标准格式
    Source B: 500.com 必发指数页
    Source C: 通用格式 (自动检测)
"""

import re
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

# 复用现有模块
from betfair_parser import BetfairMatch, parse_betfair_text, summary as bf_summary
from betfair_store import save_betfair, load_betfair, compare_snapshots

# ── 配置 ──

CONFIG_FILE = Path(__file__).parent / "auto_fetch_config.json"

# 必发数据源配置
BETFAIR_SOURCES = {
    'bfindex': {
        'name': '必发指数网',
        # bfindex.com 的URL模式 (需确认实际格式)
        'match_url_patterns': [
            'https://www.bfindex.com/match/{match_id}',
            'https://www.bfindex.com/index/{match_id}.html',
        ],
        'schedule_url': 'https://www.bfindex.com/',
        'encoding': 'utf-8',
    },
    '500com': {
        'name': '500.com必发指数',
        'match_url_patterns': [
            'https://odds.500.com/fenxi/touzhu-{match_id}.shtml',
            'https://odds.500.com/fenxi/bfindex-{match_id}.shtml',
            'https://odds.500.com/fenxi/zhishu-{match_id}.shtml',
        ],
        'schedule_url': 'https://odds.500.com/fenxi/nlz/',
        'encoding': 'gb2312',
    },
    'custom': {
        'name': '自定义源',
        'match_url_patterns': [],
        'schedule_url': '',
        'encoding': 'utf-8',
    },
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

CST = timezone(timedelta(hours=8))


# ── 配置管理 (与 auto_fetch_xls.py 共享) ──

def load_config() -> dict:
    """加载配置 (与auto_fetch_xls.py共享同一配置文件)"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'matches': {},
        'betfair_matches': {},  # 必发专用配置
        'preferred_source': 'bfindex',
        'cookie_string': '',
        'download_delay': 2.0,
        'timeout': 30,
        'max_retries': 3,
    }


def save_config(config: dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ── HTML解析引擎 ──

def parse_betfair_html(html: str, source: str = 'auto') -> Optional[BetfairMatch]:
    """
    解析必发指数HTML页面 → BetfairMatch结构化数据。

    自动检测页面格式并提取:
      - 百家欧赔 / 交易比例 / 必发成交价
      - 成交量 / 庄家盈亏 / 冷热指数
      - 大额交易明细
    """
    soup = BeautifulSoup(html, 'lxml')

    result = BetfairMatch()
    result.parsed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 策略0: 500.com touzhu 页面专用解析 (最优先) ──
    if _parse_500com_touzhu(soup, result):
        return result

    # ── 策略1: 解析标准热度分析表 ──
    table_data = _extract_heat_table(soup)
    if table_data:
        _fill_from_match(result, table_data)

    # ── 策略2: 从JSON-LD或内嵌脚本提取 ──
    if not result.home_odds:
        _extract_from_scripts(soup, result)

    # ── 策略3: 从页面文本提取 (通用fallback) ──
    if not result.home_odds:
        text = soup.get_text(separator='\n')
        cleaned = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        parsed = parse_betfair_text(cleaned)
        if parsed.home_odds:
            return parsed

    # ── 提取大额交易 ──
    big_trades = _extract_big_trades(soup)
    if big_trades:
        result.big_trades = big_trades

    # ── 运行分析 ──
    if result.home_odds:
        from betfair_parser import _detect_pollution, _classify_hot, _check_big_sell
        _detect_pollution(result)
        _classify_hot(result)
        _check_big_sell(result)

    return result if result.home_odds else None


def _parse_500com_touzhu(soup: BeautifulSoup, result: BetfairMatch) -> bool:
    """
    解析 500.com touzhu 页面格式 (专用)。

    页面结构: 4个独立表格
      Table 6: 赔率+概率+交易比例+成交价+成交量+庄家盈亏+冷热+盈亏指数
      Table 7: 大额交易明细
      Table 8: 必发交易量汇总
      Table 9: 庄家盈亏+盈亏指数

    返回: True=解析成功, False=格式不匹配
    """
    tables = soup.find_all('table')
    if len(tables) < 5:
        return False

    # 搜索包含 '百家欧赔' + '指数分析' 的赔率表 (不固定索引)
    odds_table = None
    for t in tables:
        t_text = t.get_text()
        if '百家欧赔' in t_text and '指数分析' in t_text:
            odds_table = t
            break

    if not odds_table:
        return False

    # 搜索包含 '综合' + '属性' 的大额交易表
    trades_table = None
    for t in tables:
        t_text = t.get_text()
        if '综合' in t_text and '属性' in t_text:
            trades_table = t
            break

    # === 赔率表: 核心数据 (主/平/客 三行) ===
    data_rows = []
    for row in odds_table.find_all('tr')[2:]:  # 跳过2行表头
        cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
        if len(cells) >= 8 and cells[0] not in ('数据提点', '', None, '&nbsp'):
            data_rows.append(cells)

    if len(data_rows) < 3:
        return False

    # 500.com touzhu 固定顺序: 主→平→客
    # 列: [标签, 赔率, 概率, 北单, 交易比例, 成交价, 成交量, 庄家盈亏, 必发指数, 冷热, 盈亏指数]
    for i, side in enumerate(['home', 'draw', 'away']):
        if i >= len(data_rows):
            break
        r = data_rows[i]

        try:
            odds       = float(r[1]) if r[1] != '-' else 0.0
            prob       = float(r[2].replace('%', '')) / 100.0
            trade      = float(r[4].replace('%', '')) / 100.0 if len(r) > 4 and r[4] != '-' else 0.0
            bf_price   = float(r[5]) if len(r) > 5 and r[5] != '-' else 0.0
            volume     = float(r[6].replace(',', '')) if len(r) > 6 and r[6] != '-' else 0.0
            pnl        = float(r[7].replace(',', '')) if len(r) > 7 and r[7] != '-' else 0.0
            cold       = float(r[9]) if len(r) > 9 and r[9] != '-' else 0.0
            profit_idx = float(r[10]) if len(r) > 10 and r[10] != '-' else 0.0
        except (ValueError, IndexError):
            continue

        if side == 'home':
            result.home_odds, result.home_prob = odds, prob
            result.home_trade_ratio = trade
            result.home_bf_price = bf_price
            result.home_volume, result.home_pnl = volume, pnl
            result.home_cold, result.home_profit_idx = cold, profit_idx
        elif side == 'draw':
            result.draw_odds, result.draw_prob = odds, prob
            result.draw_trade_ratio = trade
            result.draw_bf_price = bf_price
            result.draw_volume, result.draw_pnl = volume, pnl
            result.draw_cold, result.draw_profit_idx = cold, profit_idx
        else:
            result.away_odds, result.away_prob = odds, prob
            result.away_trade_ratio = trade
            result.away_bf_price = bf_price
            result.away_volume, result.away_pnl = volume, pnl
            result.away_cold, result.away_profit_idx = cold, profit_idx

    # === 大额交易表 ===
    if trades_table:
        for row in trades_table.find_all('tr')[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            if len(cells) >= 4 and cells[0] in ('主', '平', '客'):
                try:
                    result.big_trades.append({
                        'direction': cells[0],
                        'action': cells[1],
                        'volume': float(cells[2].replace(',', '')),
                        'time': cells[3] if len(cells) > 3 else '',
                        'ratio': cells[4] if len(cells) > 4 else '',
                    })
                except ValueError:
                    continue

    # === 数据提点 ===
    for el in soup.find_all(string=re.compile('本场比赛必发')):
        txt = el.strip()
        if len(txt) > 20:
            result.data_tip = txt
            break
    # 也尝试从赔率表最后一行提取
    if not result.data_tip:
        last_rows = odds_table.find_all('tr')[-3:]
        for row in last_rows:
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            for c in cells:
                if '本场比赛必发' in c:
                    result.data_tip = c
                    break

    return result.home_odds > 0


def _extract_heat_table(soup: BeautifulSoup) -> Optional[Dict[str, List[float]]]:
    """
    从HTML表格提取热度分析数据。

    目标格式 (典型必发指数表格):
    ┌────────┬──────┬──────┬──────┬──────┬──────┬──────┐
    │        │百家欧赔│交易比例│必发价 │成交量 │庄盈亏 │冷热  │
    ├────────┼──────┼──────┼──────┼──────┼──────┼──────┤
    │ 主胜   │ 2.04 │ 58%  │ 2.14 │ 4.18M│-2.55 │ +40  │
    │ 平局   │ 3.43 │ 22%  │ 3.60 │ 0.99M│+2.83 │ -44  │
    │ 客胜   │ 3.63 │ 20%  │ 3.95 │ 1.22M│+1.56 │ -27  │
    └────────┴──────┴──────┴──────┴──────┴──────┴──────┘

    返回: {'home': [col1, col2, ...], 'draw': [...], 'away': [...]}
    或 None (未找到表格)
    """
    # 查找所有表格
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 3:
            continue

        extracted = {}
        side_map = {}

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 4:
                continue

            # 提取行首标识 (主/平/客)
            # 注意: 必须精确匹配, 避免 '胜' 同时匹配主胜和客胜
            first_text = cells[0].get_text(strip=True)

            # 如果第一个cell不匹配, 尝试从行中找到标识文字
            row_text = ' '.join(c.get_text(strip=True) for c in cells[:3])

            side = None
            # 优先匹配复合词 (避免 '胜' 歧义)
            if any(kw in row_text for kw in ['主胜', '主队', '主赢', 'Home', 'home']):
                side = 'home'
            elif any(kw in row_text for kw in ['客胜', '客队', '客赢', 'Away', 'away']):
                side = 'away'
            elif any(kw in row_text for kw in ['平局', '和局', '平手', 'Draw', 'draw']):
                side = 'draw'
            # 回退: 单字匹配 (仅当上面都未匹配时)
            if not side:
                if any(kw in first_text for kw in ['主']):
                    side = 'home'
                elif any(kw in first_text for kw in ['客', '负']):
                    side = 'away'
                elif any(kw in first_text for kw in ['平', '和']):
                    side = 'draw'

            if not side:
                # 尝试从后续列中识别
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if '主' in text or '胜' in text:
                        side = 'home'; break
                    elif '平' in text or '和' in text:
                        side = 'draw'; break
                    elif '客' in text or '负' in text:
                        side = 'away'; break

            if not side:
                continue

            # 提取所有数值列
            values = []
            for cell in cells[1:]:
                text = cell.get_text(strip=True)
                # 提取数值 (支持: 2.04, 58%, 4.18M, -2.55, +40, 4,179,426)
                nums = re.findall(r'[-+]?[\d,]+\.?\d*', text)
                for n in nums:
                    try:
                        values.append(float(n.replace(',', '')))
                    except ValueError:
                        continue

            if len(values) >= 3:
                extracted[side] = values

        # 验证: 需要3个方向的数据
        if len(extracted) >= 3:
            return extracted

    return None


def _fill_from_match(result: BetfairMatch, data: Dict[str, List[float]]):
    """从表格数据填充BetfairMatch — 自动检测列格式"""
    # 取第一个side的数据来检测列格式
    sample = next(iter(data.values()))
    n = len(sample)

    # 列格式检测 (基于典型必发表格):
    # 6列: [赔率, 交易比例%, 必发价, 成交量, 庄盈亏, 冷热]  ← 最常见
    # 7列: [赔率, 概率%, 交易比例%, 必发价, 成交量, 庄盈亏, 冷热]
    # 8列: [赔率, 概率%, 交易比例%, 必发价, 成交量, 庄盈亏, 冷热, 盈亏指数]
    #
    # 检测方法: 第2列如果与隐含概率(1/赔率*100)接近(<5%偏差) → 是概率列 → 7/8列格式
    #           否则 → 是交易比例列 → 6列格式

    has_prob_column = False
    if n >= 7:
        implied_prob = (1.0 / sample[0] * 100) if sample[0] > 0 else 0
        second_col = sample[1] if sample[1] < 10 else sample[1]  # 统一为百分比
        if abs(second_col - implied_prob) < 10:  # 偏差<10%
            has_prob_column = True

    for side, values in data.items():
        n = len(values)

        if has_prob_column and n >= 7:
            # 7/8列格式: [赔率, 概率, 交易比例, 必发价, 成交量, 庄盈亏, 冷热, (盈亏指数)]
            odds       = values[0] if n > 0 else 0
            prob       = (values[1] / 100 if values[1] > 1 else values[1]) if n > 1 else 0
            trade      = (values[2] / 100 if values[2] > 1 else values[2]) if n > 2 else 0
            bf_price   = values[3] if n > 3 else 0
            volume     = values[4] if n > 4 else 0
            pnl        = values[5] if n > 5 else 0
            cold       = values[6] if n > 6 else 0
            profit_idx = values[7] if n > 7 else 0
        else:
            # 6列格式 (最常见): [赔率, 交易比例%, 必发价, 成交量, 庄盈亏, 冷热]
            odds       = values[0] if n > 0 else 0
            prob       = (1.0 / values[0] * 0.92) if n > 0 and values[0] > 0 else 0  # 从赔率估算
            trade      = (values[1] / 100 if values[1] > 1 else values[1]) if n > 1 else 0
            bf_price   = values[2] if n > 2 else 0
            volume     = values[3] if n > 3 else 0
            pnl        = values[4] if n > 4 else 0
            cold       = values[5] if n > 5 else 0
            profit_idx = 0  # 6列格式无盈亏指数

        # 单位转换: 如果volume > 10000 (原始值), 转换为K显示
        # 如果 pnl 绝对值很大 (像成交量), 说明可能错位了
        if abs(pnl) > 1000:
            # PNL和volume可能互换 — 比较哪个更像PNL (< 50M)
            if abs(volume) < 50:
                volume, pnl = pnl, volume  # 交换

        if side == 'home':
            result.home_odds = odds
            result.home_prob = prob
            result.home_trade_ratio = trade
            result.home_bf_price = bf_price
            result.home_volume = volume
            result.home_pnl = pnl
            result.home_cold = cold
            result.home_profit_idx = profit_idx
        elif side == 'draw':
            result.draw_odds = odds
            result.draw_prob = prob
            result.draw_trade_ratio = trade
            result.draw_bf_price = bf_price
            result.draw_volume = volume
            result.draw_pnl = pnl
            result.draw_cold = cold
            result.draw_profit_idx = profit_idx
        elif side == 'away':
            result.away_odds = odds
            result.away_prob = prob
            result.away_trade_ratio = trade
            result.away_bf_price = bf_price
            result.away_volume = volume
            result.away_pnl = pnl
            result.away_cold = cold
            result.away_profit_idx = profit_idx


def _extract_from_scripts(soup: BeautifulSoup, result: BetfairMatch):
    """从页面内嵌JSON/JS变量提取数据 (用于React渲染的页面)"""
    # 查找 <script> 中的 JSON 数据
    for script in soup.find_all('script'):
        text = script.string or ''
        if not text:
            continue

        # 模式1: var data = {...} 或 window.__INITIAL_STATE__ = {...}
        for pattern in [r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                        r'var\s+data\s*=\s*({.*?});',
                        r'"home_odds"\s*:',
                        r'"matchData"\s*:']:
            if re.search(pattern, text, re.DOTALL):
                # 尝试提取数值
                nums = re.findall(r'"home_odds"\s*:\s*([\d.]+)', text)
                if nums:
                    result.home_odds = float(nums[0])
                nums = re.findall(r'"draw_odds"\s*:\s*([\d.]+)', text)
                if nums:
                    result.draw_odds = float(nums[0])
                nums = re.findall(r'"away_odds"\s*:\s*([\d.]+)', text)
                if nums:
                    result.away_odds = float(nums[0])
                break


def _extract_big_trades(soup: BeautifulSoup) -> List[Dict]:
    """提取大额交易明细"""
    trades = []

    # 查找包含"大额交易"或"综合"的表格
    for table in soup.find_all('table'):
        # 检查表头
        header_text = table.get_text()[:200]
        if not any(kw in header_text for kw in ['大额', '综合', '成交', '买卖']):
            continue

        rows = table.find_all('tr')[1:]  # 跳过表头
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 4:
                continue

            texts = [c.get_text(strip=True) for c in cells]

            # 解析: 主/平/客 | 买/卖 | 成交量 | 时间 | 比例
            direction = ''
            for t in texts:
                if t in ('主', '平', '客', '主胜', '平局', '客胜'):
                    direction = t; break
            action = ''
            for t in texts:
                if t in ('买', '卖', 'Buy', 'Sell', 'Lay'):
                    action = t; break

            if direction and action:
                # 找成交量 (最大数值)
                nums = []
                for t in texts:
                    n = re.findall(r'[\d,]+', t)
                    nums.extend(int(x.replace(',', '')) for x in n)
                volume = max(nums) if nums else 0

                trades.append({
                    'direction': direction,
                    'action': '买' if action in ('买', 'Buy') else '卖',
                    'volume': volume,
                    'time': texts[-1] if len(texts) > 3 else '',
                })

    return trades


# ── HTTP获取 ──

def fetch_betfair_page(
    match_name: str,
    match_id: str = None,
    source: str = None,
    config: dict = None,
) -> Optional[str]:
    """
    获取必发数据页面的HTML内容。

    Args:
        match_name: 比赛名称
        match_id: 比赛ID (可选, 用于构造URL)
        source: 数据源 ('bfindex' / '500com' / 'custom')
        config: 配置字典

    返回: HTML字符串 或 None
    """
    if config is None:
        config = load_config()

    if source is None:
        source = config.get('preferred_source', 'bfindex')

    src_cfg = BETFAIR_SOURCES.get(source, BETFAIR_SOURCES['bfindex'])
    encoding = src_cfg.get('encoding', 'utf-8')

    session = requests.Session()
    session.headers.update(HEADERS)

    cookie_str = config.get('cookie_string', '')
    if cookie_str:
        for pair in cookie_str.split(';'):
            pair = pair.strip()
            if '=' in pair:
                k, v = pair.split('=', 1)
                session.cookies.set(k.strip(), v.strip())

    timeout = config.get('timeout', 30)

    # 1. 如果有match_id, 尝试URL模式
    if match_id:
        for pattern in src_cfg['match_url_patterns']:
            url = pattern.format(match_id=match_id)
            try:
                resp = session.get(url, headers=HEADERS, timeout=timeout)
                resp.encoding = encoding
                if resp.status_code == 200 and len(resp.text) > 1000:
                    return resp.text
            except requests.RequestException:
                continue

    # 2. 从配置文件中的自定义URL
    bf_matches = config.get('betfair_matches', {})
    if match_name in bf_matches:
        custom_url = bf_matches[match_name].get('url', '')
        if custom_url:
            try:
                resp = session.get(custom_url, headers=HEADERS, timeout=timeout)
                resp.encoding = encoding
                if resp.status_code == 200:
                    return resp.text
            except requests.RequestException:
                pass

    # 3. 尝试搜索
    return _search_match_page(match_name, source, session, config)


def _search_match_page(
    match_name: str,
    source: str,
    session: requests.Session,
    config: dict,
) -> Optional[str]:
    """在数据源首页搜索比赛链接"""
    src_cfg = BETFAIR_SOURCES.get(source, BETFAIR_SOURCES['bfindex'])
    schedule_url = src_cfg.get('schedule_url', '')
    encoding = src_cfg.get('encoding', 'utf-8')

    if not schedule_url:
        return None

    try:
        resp = session.get(schedule_url, headers=HEADERS, timeout=config.get('timeout', 30))
        resp.encoding = encoding
        soup = BeautifulSoup(resp.text, 'lxml')

        # 提取队名关键词
        teams = match_name.replace('VS', ' ').split()
        keywords = [t for t in teams if len(t) >= 1]

        # 查找包含队名的链接
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link['href']

            if all(kw in text for kw in keywords):
                # 构造完整URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    base = re.match(r'(https?://[^/]+)', schedule_url)
                    base_url = base.group(1) if base else ''
                    full_url = base_url + href
                else:
                    continue

                # 抓取比赛页
                detail_resp = session.get(full_url, headers=HEADERS, timeout=config.get('timeout', 30))
                if detail_resp.status_code == 200:
                    return detail_resp.text

        return None

    except requests.RequestException:
        return None


# ── 核心API ──

def fetch_betfair_data(
    match_name: str,
    match_id: str = None,
    source: str = None,
    kickoff: str = '',
    config: dict = None,
) -> Optional[Dict[str, Any]]:
    """
    抓取并保存必发数据 (完整流程)。

    1. 获取HTML页面
    2. 解析为 BetfairMatch
    3. 自动保存到 betfair_data/
    4. 返回结构化数据

    Args:
        match_name: 比赛名称
        match_id: 比赛ID (可选)
        source: 数据源
        kickoff: 开球时间 '2026-06-17T03:00'
        config: 配置字典

    返回: 保存后的完整数据 (含快照历史)
    """
    if config is None:
        config = load_config()

    print(f'📊 抓取必发数据: {match_name} ...')

    # 1. 获取HTML
    html = fetch_betfair_page(match_name, match_id, source, config)
    if not html:
        print(f'  ❌ 无法获取页面 (源: {source})')
        return None

    # 2. 解析
    bf = parse_betfair_html(html, source)
    if not bf or not bf.home_odds:
        print(f'  ❌ 解析失败: 未提取到有效数据')
        return None

    print(f'  ✅ 解析成功: 主{bf.home_odds}/{bf.draw_odds}/{bf.away_odds} | '
          f'冷热: 主{bf.home_cold:+.0f} 平{bf.draw_cold:+.0f} 客{bf.away_cold:+.0f}')

    # 3. 转换为 betfair_store 格式并保存
    odds = {'home': bf.home_odds, 'draw': bf.draw_odds, 'away': bf.away_odds}
    betfair_dict = {
        'home_price': bf.home_bf_price,
        'draw_price': bf.draw_bf_price,
        'away_price': bf.away_bf_price,
        'home_volume': bf.home_volume,
        'draw_volume': bf.draw_volume,
        'away_volume': bf.away_volume,
        'home_pnl': bf.home_pnl,
        'draw_pnl': bf.draw_pnl,
        'away_pnl': bf.away_pnl,
        'home_heat': bf.home_cold,
        'draw_heat': bf.draw_cold,
        'away_heat': bf.away_cold,
        # V2.6.1 新增字段
        'home_prob': bf.home_prob,
        'draw_prob': bf.draw_prob,
        'away_prob': bf.away_prob,
        'home_trade': bf.home_trade_ratio,
        'draw_trade': bf.draw_trade_ratio,
        'away_trade': bf.away_trade_ratio,
        'home_profit_idx': bf.home_profit_idx,
        'draw_profit_idx': bf.draw_profit_idx,
        'away_profit_idx': bf.away_profit_idx,
    }
    big_trades = [{
        'side': t['direction'],
        'direction': t['action'],
        'volume': t['volume'],
        'time': t.get('time', ''),
    } for t in bf.big_trades]

    notes = bf.data_tip or f'自动抓取 [{source}] {datetime.now(CST).strftime("%H:%M")}'

    saved = save_betfair(
        match_name=match_name,
        odds=odds,
        betfair=betfair_dict,
        big_trades=big_trades,
        notes=notes,
        kickoff=kickoff,
        source=f'auto_fetch:{source}',
    )

    print(f'  💾 已保存: {saved["snapshot_count"]}个快照')
    return saved


def fetch_batch(
    match_names: List[str],
    match_ids: Dict[str, str] = None,
    source: str = None,
    kickoffs: Dict[str, str] = None,
    config: dict = None,
) -> Dict[str, Optional[Dict]]:
    """
    批量抓取多场比赛的必发数据。

    Args:
        match_names: 比赛名列表
        match_ids: {name: id} 映射
        source: 数据源
        kickoffs: {name: kickoff_time} 映射
        config: 配置

    返回: {match_name: saved_data or None}
    """
    if config is None:
        config = load_config()

    if match_ids is None:
        match_ids = {}
    if kickoffs is None:
        kickoffs = {}

    results = {}
    total = len(match_names)
    delay = config.get('download_delay', 2)

    for i, name in enumerate(match_names, 1):
        print(f'\n[{i}/{total}] {name}')
        mid = match_ids.get(name)
        ko = kickoffs.get(name, '')

        results[name] = fetch_betfair_data(
            match_name=name,
            match_id=mid,
            source=source,
            kickoff=ko,
            config=config,
        )

        if i < total:
            time.sleep(delay)

    # 汇总
    success = sum(1 for v in results.values() if v is not None)
    print(f'\n{"="*50}')
    print(f'📊 必发数据汇总: {success}/{total} 成功')
    print(f'{"="*50}')

    return results


# ── 数据导出 (兼容 betfair_parser 文本格式) ──

def to_text_format(bf: BetfairMatch) -> str:
    """
    将 BetfairMatch 转换为文本格式 (兼容 betfair_parser.parse_betfair_text)。

    方便: 在不改变下游代码的情况下使用自动抓取的数据。
    """
    lines = [
        f"{bf.match_name}",
        "",
        "赔率公司 百家欧赔 交易比例 必发成交价 成交量 庄家盈亏 冷热指数",
        f"主 {bf.home_odds:.2f} {bf.home_trade_ratio*100:.1f}% {bf.home_bf_price:.2f} "
        f"{bf.home_volume:,.0f} {bf.home_pnl:+.2f} {bf.home_cold:+.0f}",
        f"平 {bf.draw_odds:.2f} {bf.draw_trade_ratio*100:.1f}% {bf.draw_bf_price:.2f} "
        f"{bf.draw_volume:,.0f} {bf.draw_pnl:+.2f} {bf.draw_cold:+.0f}",
        f"客 {bf.away_odds:.2f} {bf.away_trade_ratio*100:.1f}% {bf.away_bf_price:.2f} "
        f"{bf.away_volume:,.0f} {bf.away_pnl:+.2f} {bf.away_cold:+.0f}",
    ]

    if bf.data_tip:
        lines.append(f"\n数据提点: {bf.data_tip}")

    if bf.big_trades:
        lines.append(f"\n综合 属性")
        for t in bf.big_trades:
            lines.append(f"{t['direction']} {t['action']} {t['volume']:,}")

    return '\n'.join(lines)


# ── CLI ──

def main():
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print('\n用法:')
        print('  python auto_fetch_betfair.py --match "法国VS塞内加尔"')
        print('  python auto_fetch_betfair.py --match "法国VS塞内加尔" --source bfindex')
        print('  python auto_fetch_betfair.py --all')
        print('  python auto_fetch_betfair.py --compare "法国VS塞内加尔"')
        print('  python auto_fetch_betfair.py --list')
        print('  python auto_fetch_betfair.py --add "法国VS塞内加尔" --url "https://..."')
        return

    config = load_config()

    if '--list' in sys.argv:
        data_dir = Path(r"C:\Users\A\PyCharmMiscProject\betfair_data")
        if data_dir.exists():
            files = list(data_dir.glob('*.json'))
            if files:
                print(f'已保存 {len(files)} 场比赛的必发数据:')
                for f in files:
                    try:
                        d = json.loads(f.read_text(encoding='utf-8'))
                        name = d.get('match_name', f.stem)
                        count = d.get('snapshot_count', 0)
                        print(f'  📁 {name} ({count}个快照)')
                    except:
                        print(f'  📁 {f.stem}')
            else:
                print('暂无必发数据')
        return

    if '--compare' in sys.argv:
        idx = sys.argv.index('--compare') + 1
        if idx < len(sys.argv):
            match_name = sys.argv[idx]
            print(compare_snapshots(match_name))
        return

    if '--add' in sys.argv and '--url' in sys.argv:
        match_idx = sys.argv.index('--add') + 1
        url_idx = sys.argv.index('--url') + 1
        if match_idx < len(sys.argv) and url_idx < len(sys.argv):
            match_name = sys.argv[match_idx]
            url = sys.argv[url_idx]
            if 'betfair_matches' not in config:
                config['betfair_matches'] = {}
            config['betfair_matches'][match_name] = {
                'url': url,
                'added': datetime.now().strftime('%Y-%m-%d %H:%M'),
            }
            save_config(config)
            print(f'✅ 已添加: {match_name} → {url}')
        return

    source = None
    if '--source' in sys.argv:
        idx = sys.argv.index('--source') + 1
        if idx < len(sys.argv):
            source = sys.argv[idx]

    if '--match' in sys.argv:
        idx = sys.argv.index('--match') + 1
        if idx < len(sys.argv):
            match_name = sys.argv[idx]
            mid = None
            if match_name in config.get('matches', {}):
                mid = config['matches'][match_name].get('match_id')
            fetch_betfair_data(match_name, match_id=mid, source=source)
            return

    if '--all' in sys.argv:
        match_names = list(config.get('matches', {}).keys())
        if not match_names:
            print('没有配置的比赛。使用 --add 添加')
            return
        match_ids = {n: config['matches'][n].get('match_id') for n in match_names}
        fetch_batch(match_names, match_ids=match_ids, source=source)
        return

    print('请指定操作: --match / --all / --compare / --list / --add')


if __name__ == '__main__':
    main()

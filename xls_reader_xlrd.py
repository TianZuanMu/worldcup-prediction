# -*- coding: utf-8 -*-
"""
P0-3: XLS读取管道 —— 统一使用 Python xlrd

替换原因:
  - PowerShell COM: 编码问题(中文乱码)、速度慢、弹窗风险
  - xlrd: 纯Python、速度快、编码稳定、已验证可用

支持四种文件类型:
  - (世界杯)欧洲数据.xls  → 百家欧赔 (初盘/即时/概率/凯利)
  - (亚盘).xls           → 亚盘 (盘口/水位/升降)
  - (大小).xls           → 大小球 (盘口/水位)
  - (让球指数).xls       → 让球指数 (特定让球的胜平负概率)

用法:
  from xls_reader_xlrd import read_all_xls
  data = read_all_xls('厄瓜多尔VS塞内加尔')
  # data = {'european': {...}, 'asian': {...}, 'totals': {...}, 'handicap_index': {...}}
"""

import os
import xlrd
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


# ── 🆕 V4.5 P2: XLS结构异常类 ──
class XlsStructureError(Exception):
    """500.com XLS模板变更导致解析失败"""
    pass


# ── 文件路径构建 ──
XLS_DIR = r"D:"


def _find_latest_xls(match_name: str, suffix: str) -> str | None:
    """
    查找最新版本的XLS文件。

    500.com 下载逻辑: 同一文件重复下载时, 浏览器自动加 (1) (2) ...
    基础名 (无编号) = 最早版本, (N) = 第N+1次下载

    返回: 最新文件的完整路径, 若不存在返回 None
    """
    import glob
    import re

    base_name = f'{match_name}{suffix}'
    base_path = os.path.join(XLS_DIR, base_name)

    # 收集所有版本: 基础文件 + 编号文件
    # 编号文件格式: "西班牙VS佛得角(亚盘) (1).xls"
    stem, ext = os.path.splitext(base_name)
    pattern = os.path.join(XLS_DIR, f'{stem}*.xls')

    candidates = []
    for fpath in glob.glob(pattern):
        fname = os.path.basename(fpath)
        # 匹配: 基础名.xls 或 基础名 (N).xls
        if fname == base_name:
            # 基础文件 (版本0)
            candidates.append((fpath, 0))
        else:
            m = re.match(r'^' + re.escape(stem) + r' \((\d+)\)\.xls$', fname)
            if m:
                candidates.append((fpath, int(m.group(1))))

    if not candidates:
        return None

    # 按修改时间排序, 返回最新
    candidates.sort(key=lambda x: os.path.getmtime(x[0]), reverse=True)
    return candidates[0][0]


def _find_all_xls_versions(match_name: str, suffix: str) -> list[tuple[str, int, float]]:
    """
    查找所有版本的XLS文件, 按修改时间排序 (旧→新)。

    返回: [(路径, 版本号, 修改时间戳), ...]
    """
    import glob
    import re

    stem, ext = os.path.splitext(f'{match_name}{suffix}')
    pattern = os.path.join(XLS_DIR, f'{stem}*.xls')
    base_name = f'{match_name}{suffix}'

    candidates = []
    for fpath in glob.glob(pattern):
        fname = os.path.basename(fpath)
        if fname == base_name:
            candidates.append((fpath, 0, os.path.getmtime(fpath)))
        else:
            m = re.match(r'^' + re.escape(stem) + r' \((\d+)\)\.xls$', fname)
            if m:
                candidates.append((fpath, int(m.group(1)), os.path.getmtime(fpath)))

    candidates.sort(key=lambda x: x[2])  # 按时间排序
    return candidates


def _find_version_xls(match_name: str, suffix: str, version: int) -> str | None:
    """查找指定版本号的XLS文件"""
    import glob, re
    stem, ext = os.path.splitext(f'{match_name}{suffix}')
    pattern = os.path.join(XLS_DIR, f'{stem}*.xls')
    base_name = f'{match_name}{suffix}'

    for fpath in glob.glob(pattern):
        fname = os.path.basename(fpath)
        if version == 0 and fname == base_name:
            return fpath
        m = re.match(r'^' + re.escape(stem) + r' \((\d+)\)\.xls$', fname)
        if m and int(m.group(1)) == version:
            return fpath
    return None


def _build_paths(match_name: str, use_latest: bool = True, use_version: int = None) -> Dict[str, str]:
    """
    构建四个XLS文件路径。

    Args:
        match_name: 比赛名称, 如 '西班牙VS佛得角'
        use_latest: True=使用最新版本, False=使用基础版本(兼容旧行为)

    文件后缀映射:
      - european:      (世界杯)欧洲数据.xls
      - asian:         (亚盘).xls
      - totals:        (大小).xls
      - handicap_index: (让球指数).xls
    """
    suffixes = {
        'european': '(世界杯)欧洲数据.xls',
        'asian': '(亚盘).xls',
        'totals': '(大小).xls',
        'handicap_index': '(让球指数).xls',
    }

    paths = {}
    for key, suffix in suffixes.items():
        if use_version is not None:
            # V3.0: 指定版本号
            found = _find_version_xls(match_name, suffix, use_version)
            if found:
                paths[key] = found
            else:
                paths[key] = os.path.join(XLS_DIR, f'{match_name}{suffix}')
        elif use_latest:
            latest = _find_latest_xls(match_name, suffix)
            if latest:
                paths[key] = latest
            else:
                paths[key] = os.path.join(XLS_DIR, f'{match_name}{suffix}')
        else:
            paths[key] = os.path.join(XLS_DIR, f'{match_name}{suffix}')

    return paths


# ── 解析函数 ──

def parse_european_odds(sheet) -> Dict[str, Any]:
    """
    解析百家欧赔数据。

    500.com XLS 结构:
      Row 0: 表头 (欧赔公司 | 欧赔 | ...)
      Row 1: 子表头 (胜/平/负 | 胜率/和率/负率/返还率)
      Row 2: 最高值 (label="最高值")
      Row 3: (空label, 某种变体)
      Row 4: 最低值 (label="最低值")
      Row 5: (空label, 离散值)
      Row 6: 初盘均值 (label="平均值")
      Row 7: 即时均值 (空label) ← 最关键!
      Row 8+: 公司配对数据 (奇数行=公司+初盘, 偶数行=即时)
          最后几行: 即时均值/初盘均值 汇总行 (空label, 出现在所有公司之后)
    """
    result = {
        'bookmakers': [],
        'summary': {},
        'row_count': sheet.nrows,
    }

    # ── V4.5 P2: 动态关键词扫描(前20行)·避免硬编码行号 ──
    summary_labels = {}
    for r in range(min(20, sheet.nrows)):
        label = str(sheet.cell_value(r, 0)).strip()
        if label:
            summary_labels[label] = r
    # 必要标签缺失→抛异常而非静默返回残缺数据
    _required_labels = ['最高值', '最低值', '平均值']
    _missing_labels = [l for l in _required_labels if l not in summary_labels]
    if _missing_labels:
        raise XlsStructureError(
            f'欧赔XLS缺少必要标签: {_missing_labels}·'
            f'已找到{list(summary_labels.keys())[:8]}·'
            f'可能500.com模板变更·需更新解析器'
        )

    # 最高值
    if '最高值' in summary_labels:
        r = summary_labels['最高值']
        result['summary']['max'] = {
            'win': str(sheet.cell_value(r, 1)),
            'draw': str(sheet.cell_value(r, 2)),
            'lose': str(sheet.cell_value(r, 3)),
        }

    # 最低值
    if '最低值' in summary_labels:
        r = summary_labels['最低值']
        result['summary']['min'] = {
            'win': str(sheet.cell_value(r, 1)),
            'draw': str(sheet.cell_value(r, 2)),
            'lose': str(sheet.cell_value(r, 3)),
        }

    # 初盘均值 (label="平均值")
    if '平均值' in summary_labels:
        r = summary_labels['平均值']
        result['summary']['initial_avg'] = {
            'win': str(sheet.cell_value(r, 1)),
            'draw': str(sheet.cell_value(r, 2)),
            'lose': str(sheet.cell_value(r, 3)),
            'win_prob': str(sheet.cell_value(r, 4)),
            'draw_prob': str(sheet.cell_value(r, 5)),
            'lose_prob': str(sheet.cell_value(r, 6)),
            'return_rate': str(sheet.cell_value(r, 7)),
        }

    # 即时均值: 紧跟"平均值"的无label行 (row index = 平均值_row + 1)
    if '平均值' in summary_labels:
        instant_row = summary_labels['平均值'] + 1
        if instant_row < sheet.nrows:
            instant_label = str(sheet.cell_value(instant_row, 0)).strip()
            if not instant_label:  # 确认是无label行
                result['summary']['instant'] = {
                    'win': str(sheet.cell_value(instant_row, 1)),
                    'draw': str(sheet.cell_value(instant_row, 2)),
                    'lose': str(sheet.cell_value(instant_row, 3)),
                    'win_prob': str(sheet.cell_value(instant_row, 4)),
                    'draw_prob': str(sheet.cell_value(instant_row, 5)),
                    'lose_prob': str(sheet.cell_value(instant_row, 6)),
                    'return_rate': str(sheet.cell_value(instant_row, 7)),
                }

    # 如果上面没找到即时均值（异常情况），回退到扫描末尾的无label行
    if 'instant' not in result['summary']:
        for r in range(sheet.nrows - 1, max(sheet.nrows - 20, 0), -1):
            label = str(sheet.cell_value(r, 0)).strip()
            if not label:
                # 检查是否有合理的数值
                try:
                    w = float(sheet.cell_value(r, 1))
                    if 1.0 < w < 20.0:  # 合理的赔率范围
                        result['summary']['instant'] = {
                            'win': str(w),
                            'draw': str(sheet.cell_value(r, 2)),
                            'lose': str(sheet.cell_value(r, 3)),
                            'win_prob': str(sheet.cell_value(r, 4)),
                            'draw_prob': str(sheet.cell_value(r, 5)),
                            'lose_prob': str(sheet.cell_value(r, 6)),
                            'return_rate': str(sheet.cell_value(r, 7)),
                        }
                        break
                except (ValueError, IndexError):
                    continue

    # ── 公司配对数据 ──
    # 公司数据从第8行或"平均值"+2行开始
    start_row = summary_labels.get('平均值', 6) + 2
    if start_row < 8:
        start_row = 8

    i = start_row
    while i < sheet.nrows - 1:
        cells_a = [str(sheet.cell_value(i, c)) for c in range(min(11, sheet.ncols))]
        name = cells_a[0].strip()

        # 跳过空行和汇总行
        if not name or name in ['最大值', '最小值', '即时', '初盘', '离散值', '平均值', '']:
            i += 1
            continue

        # 奇数行: 初盘
        init_win = cells_a[1] if len(cells_a) > 1 else ''
        init_draw = cells_a[2] if len(cells_a) > 2 else ''
        init_lose = cells_a[3] if len(cells_a) > 3 else ''

        # 偶数行: 即时 (紧跟奇数行)
        cells_b = [str(sheet.cell_value(i + 1, c)) for c in range(min(11, sheet.ncols))]
        now_win = cells_b[1] if len(cells_b) > 1 else ''
        now_draw = cells_b[2] if len(cells_b) > 2 else ''
        now_lose = cells_b[3] if len(cells_b) > 3 else ''

        # 计算变动
        try:
            iw, nw = float(init_win), float(now_win)
            w_change = round((nw - iw) / iw * 100, 2) if iw > 0 else 0
        except (ValueError, ZeroDivisionError):
            w_change = 0

        try:
            idr, ndr = float(init_draw), float(now_draw)
            d_change = round((ndr - idr) / idr * 100, 2) if idr > 0 else 0
        except (ValueError, ZeroDivisionError):
            d_change = 0

        try:
            il, nl = float(init_lose), float(now_lose)
            l_change = round((nl - il) / il * 100, 2) if il > 0 else 0
        except (ValueError, ZeroDivisionError):
            l_change = 0

        result['bookmakers'].append({
            'name': name,
            'init_win': init_win, 'init_draw': init_draw, 'init_lose': init_lose,
            'now_win': now_win, 'now_draw': now_draw, 'now_lose': now_lose,
            'win_change': w_change, 'draw_change': d_change, 'lose_change': l_change,
        })
        i += 2

    # 计算变动统计
    if result['bookmakers']:
        w_changes = [b['win_change'] for b in result['bookmakers']]
        d_changes = [b['draw_change'] for b in result['bookmakers']]
        l_changes = [b['lose_change'] for b in result['bookmakers']]

        result['stats'] = {
            'win_avg_change': round(sum(w_changes) / len(w_changes), 2),
            'draw_avg_change': round(sum(d_changes) / len(d_changes), 2),
            'lose_avg_change': round(sum(l_changes) / len(l_changes), 2),
            'win_down_count': sum(1 for c in w_changes if c < -1),   # 赔率下降>1%
            'win_up_count': sum(1 for c in w_changes if c > 1),      # 赔率上升>1%
            'draw_down_count': sum(1 for c in d_changes if c < -1),
            'draw_up_count': sum(1 for c in d_changes if c > 1),
        }

    return result


def parse_asian_handicap(sheet) -> Dict[str, Any]:
    """
    解析亚盘数据。

    结构:
      0: 表头
      1: 子表头 (赔率公司 | 即时水/盘/水 | 变化时间 | 初始水/盘/水 | 变化时间)
      2: 平均值
      3: 最高值
      4: 最低值
      5+: 各公司数据
    """
    result = {
        'companies': [],
        'summary': {},
        'row_count': sheet.nrows,
    }

    # 平均值 (第3行, 0-indexed=2)
    if sheet.nrows > 2:
        result['summary']['avg'] = {
            'instant_water_home': str(sheet.cell_value(2, 1)),
            'instant_line': str(sheet.cell_value(2, 2)),
            'instant_water_away': str(sheet.cell_value(2, 3)),
            'init_water_home': str(sheet.cell_value(2, 5)),
            'init_line': str(sheet.cell_value(2, 6)),
            'init_water_away': str(sheet.cell_value(2, 7)),
        }

    # 各公司
    for i in range(5, sheet.nrows):
        cells = [str(sheet.cell_value(i, c)) for c in range(min(9, sheet.ncols))]
        name = cells[0].strip()
        if not name or name in ['平均值', '最高值', '最低值']:
            continue

        result['companies'].append({
            'name': name,
            'instant_water_home': cells[1] if len(cells) > 1 else '',
            'instant_line': cells[2] if len(cells) > 2 else '',
            'instant_water_away': cells[3] if len(cells) > 3 else '',
            'change_time': cells[4] if len(cells) > 4 else '',
            'init_water_home': cells[5] if len(cells) > 5 else '',
            'init_line': cells[6] if len(cells) > 6 else '',
            'init_water_away': cells[7] if len(cells) > 7 else '',
            'init_time': cells[8] if len(cells) > 8 else '',
        })

    # 判断盘口变动方向
    # 注意: avg行(第3行)的"盘"列是数值(如-0.214=平均值)，不是文字
    # 需要从公司数据中提取实际的文字盘口描述
    avg = result['summary'].get('avg', {})

    def parse_line(s):
        """解析盘口文字，支持 '平手/半球 升' 格式"""
        s = str(s).strip()
        # 检测升降后缀
        direction_suffix = ''
        if '升' in s:
            direction_suffix = '升'
            s = s.replace('升', '').strip()
        elif '降' in s:
            direction_suffix = '降'
            s = s.replace('降', '').strip()

        # 先尝试作为数值解析（avg行是数值）
        try:
            return float(s)
        except (ValueError, TypeError):
            pass

        # 文字映射 (完整版·含深盘)
        line_map = {
            '平手': 0.0,
            '平手/半球': 0.25, '平手／半球': 0.25,
            '半球': 0.5,
            '半球/一球': 0.75, '半球／一球': 0.75,
            '一球': 1.0,
            '一球/球半': 1.25, '一球／球半': 1.25,
            '球半': 1.5,
            '球半/两球': 1.75, '球半／两球': 1.75,
            '两球': 2.0,
            '两球/两球半': 2.25, '两球／两球半': 2.25,
            '两球半': 2.5,
            '两球半/三球': 2.75, '两球半／三球': 2.75,
            '三球': 3.0,
            '三球/三球半': 3.25, '三球／三球半': 3.25,
            '三球半': 3.5,
            '三球半/四球': 3.75, '三球半／四球': 3.75,
            '四球': 4.0,
            '四球/四球半': 4.25, '四球／四球半': 4.25,
            '四球半': 4.5,
            # 受让方(下盘)对应负数
            '受平手/半球': -0.25, '受平手／半球': -0.25,
            '受半球': -0.5,
            '受半球/一球': -0.75, '受半球／一球': -0.75,
            '受一球': -1.0,
            '受一球/球半': -1.25, '受一球／球半': -1.25,
            '受球半': -1.5,
            '受球半/两球': -1.75, '受球半／两球': -1.75,
            '受两球': -2.0,
            '受两球/两球半': -2.25, '受两球／两球半': -2.25,
            '受两球半': -2.5,
            '受两球半/三球': -2.75, '受两球半／三球': -2.75,
            '受三球': -3.0,
            '受三球/三球半': -3.25, '受三球／三球半': -3.25,
            '受三球半': -3.5,
        }
        return line_map.get(s, 0)

    # 从公司数据统计最常见的盘口
    company_lines_init = []
    company_lines_inst = []
    direction_tags = []

    for comp in result['companies']:
        il = parse_line(comp.get('init_line', ''))
        cl = parse_line(comp.get('instant_line', ''))
        company_lines_init.append(il)
        company_lines_inst.append(cl)
        # 检测升降标记
        il_str = str(comp.get('init_line', ''))
        cl_str = str(comp.get('instant_line', ''))
        # 升/降基于绝对值: |盘口|变大=升盘(热方让更多球), |盘口|变小=降盘
        # 优先用数值比较·文字"升/降"仅兜底(parse_line返回0时)
        if cl != 0 and il != 0:
            if abs(cl) > abs(il): direction_tags.append('up')
            elif abs(cl) < abs(il): direction_tags.append('down')
        elif '升' in cl_str: direction_tags.append('up')
        elif '降' in cl_str: direction_tags.append('down')

    # 取众数作为盘口
    from collections import Counter
    init_counter = Counter(company_lines_init)
    inst_counter = Counter(company_lines_inst)

    init_line_val = init_counter.most_common(1)[0][0] if init_counter else 0
    inst_line_val = inst_counter.most_common(1)[0][0] if inst_counter else 0

    # 🆕 V3.4: 方向判定 — 需足够公司支持(≥30%或≥5家)
    total_companies = len(result['companies'])
    min_dir_count = max(3, total_companies * 0.25)  # 至少3家或25%
    dir_counter = Counter(direction_tags)
    most_dir = 'stable'
    if dir_counter:
        top_dir, top_count = dir_counter.most_common(1)[0]
        if top_count >= min_dir_count:
            most_dir = top_dir

    result['line_analysis'] = {
        'init_line': init_line_val,
        'instant_line': inst_line_val,
        'change': round(abs(inst_line_val) - abs(init_line_val), 3),  # 绝对值差=盘口深度变化
        'direction': most_dir,
    }

    return result


def parse_totals(sheet) -> Dict[str, Any]:
    """
    解析大小球数据。

    结构: 与亚盘相同
    """
    result = {
        'companies': [],
        'summary': {},
        'row_count': sheet.nrows,
    }

    if sheet.nrows > 2:
        result['summary']['avg'] = {
            'instant_over_water': str(sheet.cell_value(2, 1)),
            'instant_line': str(sheet.cell_value(2, 2)),
            'instant_under_water': str(sheet.cell_value(2, 3)),
            'init_over_water': str(sheet.cell_value(2, 5)),
            'init_line': str(sheet.cell_value(2, 6)),
            'init_under_water': str(sheet.cell_value(2, 7)),
        }

    for i in range(5, sheet.nrows):
        cells = [str(sheet.cell_value(i, c)) for c in range(min(9, sheet.ncols))]
        name = cells[0].strip()
        if not name or name in ['平均值', '最高值', '最低值']:
            continue

        result['companies'].append({
            'name': name,
            'instant_over': cells[1] if len(cells) > 1 else '',
            'instant_line': cells[2] if len(cells) > 2 else '',
            'instant_under': cells[3] if len(cells) > 3 else '',
            'init_over': cells[5] if len(cells) > 5 else '',
            'init_line': cells[6] if len(cells) > 6 else '',
            'init_under': cells[7] if len(cells) > 7 else '',
        })

    # 盘口变动
    avg = result['summary'].get('avg', {})
    init_line_str = avg.get('init_line', '2.5')
    inst_line_str = avg.get('instant_line', '2.5')

    try:
        init_val = float(init_line_str.replace(' ', '').replace('球', '').split('/')[0]) if init_line_str else 2.5
    except (ValueError, AttributeError):
        init_val = 2.5
    try:
        inst_val = float(inst_line_str.replace(' ', '').replace('球', '').split('/')[0]) if inst_line_str else 2.5
    except (ValueError, AttributeError):
        inst_val = 2.5

    result['line_analysis'] = {
        'init_line': init_val,
        'instant_line': inst_val,
        'change': round(inst_val - init_val, 3),
        'direction': 'up' if inst_val > init_val else ('down' if inst_val < init_val else 'stable'),
    }

    return result


def parse_handicap_index(sheet) -> Dict[str, Any]:
    """
    解析让球指数数据。

    支持两种格式:
      Format 1 (旧·30行): 每公司2行 —— 初盘+即时, 统一让球
          例: Row2=竞*官*初盘(-2.0), Row3=竞*官*即时(-2.0)
      Format 2 (新·72行): 每公司4行 —— 两个让球档位各初盘+即时
          例: Row2=竞*官*初盘(-3.0), Row3=竞*官*即时(-3.0),
              Row4=竞*官*初盘(-2.0), Row5=竞*官*即时(-2.0)

    配对逻辑: 同公司名+同让球档位 → 初盘行+即时行配对
    """
    result = {
        'companies': [],
        'row_count': sheet.nrows,
        'lines_available': [],  # 可用的让球档位列表
    }

    i = 2
    while i < sheet.nrows:
        # Read paired rows: init row + instant row
        cells_init = [str(sheet.cell_value(i, c)) for c in range(min(12, sheet.ncols))]
        name = cells_init[0].strip()
        line_init = cells_init[1].strip() if len(cells_init) > 1 else ''
        if not name:
            i += 1
            continue

        # Second row (instant) - must have same name AND same handicap line
        has_instant = False
        cells_inst = []
        if (i + 1) < sheet.nrows:
            cells_inst = [str(sheet.cell_value(i+1, c)) for c in range(min(12, sheet.ncols))]
            inst_name = cells_inst[0].strip()
            inst_line = cells_inst[1].strip() if len(cells_inst) > 1 else ''
            # Paired only if same company name AND same handicap line
            if inst_name == name and (not inst_line or inst_line == line_init):
                has_instant = True

        entry = {
            'name': name,
            'line': line_init,
            # 初盘
            'init_win_odds': cells_init[2] if len(cells_init) > 2 else '',
            'init_draw_odds': cells_init[3] if len(cells_init) > 3 else '',
            'init_lose_odds': cells_init[4] if len(cells_init) > 4 else '',
            'init_win_prob': cells_init[5] if len(cells_init) > 5 else '',
            'init_draw_prob': cells_init[6] if len(cells_init) > 6 else '',
            'init_lose_prob': cells_init[7] if len(cells_init) > 7 else '',
            'init_return_rate': cells_init[8] if len(cells_init) > 8 else '',
            # 即时盘口 (优先使用)
            'win_odds': cells_inst[2] if has_instant and len(cells_inst) > 2 else cells_init[2],
            'draw_odds': cells_inst[3] if has_instant and len(cells_inst) > 3 else cells_init[3],
            'lose_odds': cells_inst[4] if has_instant and len(cells_inst) > 4 else cells_init[4],
            'win_prob': cells_inst[5] if has_instant and len(cells_inst) > 5 else cells_init[5],
            'draw_prob': cells_inst[6] if has_instant and len(cells_inst) > 6 else cells_init[6],
            'lose_prob': cells_inst[7] if has_instant and len(cells_inst) > 7 else cells_init[7],
            'return_rate': cells_inst[8] if has_instant and len(cells_inst) > 8 else cells_init[8],
        }
        result['companies'].append(entry)

        # Track available handicap lines
        if line_init and line_init not in result['lines_available']:
            result['lines_available'].append(line_init)

        i += 2  # Skip both rows (init + instant)

    # ── 按让球档位分组统计 ──
    from collections import defaultdict
    by_line = defaultdict(list)
    for comp in result['companies']:
        by_line[comp['line']].append(comp)

    result['by_line'] = {}
    for line, comps in by_line.items():
        win_probs = []
        for c in comps:
            try:
                wp = float(c['win_prob'].replace('%', ''))
                win_probs.append(wp)
            except (ValueError, AttributeError):
                pass
        result['by_line'][line] = {
            'count': len(comps),
            'avg_win_prob': round(sum(win_probs) / len(win_probs), 2) if win_probs else None,
            'companies': comps,
        }

    # ── 确定主让球档位 (最接近市场实际盘口的) ──
    # 优先选 -2.0 (最常见), 其次绝对值最小的
    if result['lines_available']:
        lines_float = []
        for l in result['lines_available']:
            try:
                lines_float.append((abs(float(l)), float(l)))
            except ValueError:
                pass
        if lines_float:
            # 先找恰好是 -2.0 的
            exact = [lf for lf in lines_float if lf[1] == -2.0]
            if exact:
                result['primary_line'] = '-2.0'
            else:
                # 取绝对值最小的 (最接近平手盘)
                lines_float.sort()
                result['primary_line'] = str(lines_float[0][1])

    return result


# ── 统一入口 ──

def read_all_xls(match_name: str, use_latest: bool = True, use_version: int = None) -> Dict[str, Any]:
    """
    读取一场比赛的全部四个XLS文件。

    Args:
        match_name: 比赛名称, 如 '西班牙VS佛得角'
        use_latest: True=自动选择最新版本 (与use_version互斥)
        use_version: 指定版本号 (0=基础版, 1=第1次重下载, ...)

    返回:
      {...}
    """
    paths = _build_paths(match_name, use_latest=use_latest, use_version=use_version)
    result = {
        'match_name': match_name,
        'files_found': [],
        'files_missing': [],
        'file_paths': {},
        'file_versions': {},
    }

    parsers = {
        'european': parse_european_odds,
        'asian': parse_asian_handicap,
        'totals': parse_totals,
        'handicap_index': parse_handicap_index,
    }

    for key, path in paths.items():
        if os.path.exists(path):
            try:
                wb = xlrd.open_workbook(path)
                sheet = wb.sheet_by_index(0)
                result[key] = parsers[key](sheet)
                result['files_found'].append(key)
                result['file_paths'][key] = path
                result['file_versions'][key] = (
                    os.path.getmtime(path),
                    os.path.basename(path),
                )
            except Exception as e:
                result[key] = {'error': str(e)}
                result['files_missing'].append(key)
        else:
            result[key] = None
            result['files_missing'].append(key)

    return result


def read_all_versions(match_name: str) -> Dict[str, Any]:
    """
    读取一场比赛所有版本的XLS文件, 用于趋势分析。

    返回:
      {
        'match_name': str,
        'european': [(path, version, mtime, parsed_data), ...],
        'asian': [...],
        'totals': [...],
        'handicap_index': [...],
      }
    """
    suffixes = {
        'european': '(世界杯)欧洲数据.xls',
        'asian': '(亚盘).xls',
        'totals': '(大小).xls',
        'handicap_index': '(让球指数).xls',
    }

    parsers = {
        'european': parse_european_odds,
        'asian': parse_asian_handicap,
        'totals': parse_totals,
        'handicap_index': parse_handicap_index,
    }

    result = {'match_name': match_name}
    for key, suffix in suffixes.items():
        versions = _find_all_xls_versions(match_name, suffix)
        parsed_versions = []
        for path, ver, mtime in versions:
            try:
                wb = xlrd.open_workbook(path)
                sheet = wb.sheet_by_index(0)
                data = parsers[key](sheet)
                parsed_versions.append({
                    'path': path,
                    'version': ver,
                    'mtime': mtime,
                    'filename': os.path.basename(path),
                    'data': data,
                })
            except Exception as e:
                parsed_versions.append({
                    'path': path,
                    'version': ver,
                    'mtime': mtime,
                    'filename': os.path.basename(path),
                    'error': str(e),
                })
        result[key] = parsed_versions

    return result


def quick_summary(data: Dict[str, Any]) -> str:
    """生成XLS数据的一句话摘要"""
    lines = []
    # 文件版本信息
    file_versions = data.get('file_versions', {})
    if file_versions:
        # 检查各文件类型有多少个版本
        from collections import Counter
        fnames = [os.path.basename(data['file_paths'].get(k, '')) for k in ['european', 'asian', 'totals', 'handicap_index']]
        lines.append(f"📋 {data['match_name']} XLS数据 (最新版本):")
    else:
        lines.append(f"📋 {data['match_name']} XLS数据:")

    # 欧洲数据
    eu = data.get('european')
    if eu and 'summary' in eu and 'instant' in eu['summary']:
        inst = eu['summary']['instant']
        lines.append(f"  百家欧赔: W{inst['win']}/D{inst['draw']}/L{inst['lose']} "
                    f"(主{inst['win_prob']}/平{inst['draw_prob']}/客{inst['lose_prob']}) "
                    f"({len(eu.get('bookmakers', []))}家公司)")
        if 'stats' in eu:
            s = eu['stats']
            lines.append(f"  变动: 主{ s['win_avg_change']:+.1f}% "
                        f"平{s['draw_avg_change']:+.1f}% "
                        f"客{s['lose_avg_change']:+.1f}% | "
                        f"主降{s['win_down_count']}家/主升{s['win_up_count']}家")
    elif eu and 'error' in eu:
        lines.append(f"  欧洲数据: ⚠️ {eu['error']}")
    else:
        lines.append("  欧洲数据: ❌ 缺失")

    # 亚盘
    ah = data.get('asian')
    if ah and 'line_analysis' in ah:
        la = ah['line_analysis']
        direction_cn = {'up': '升盘', 'down': '降盘', 'stable': '稳定'}[la['direction']]
        lines.append(f"  亚盘: {la['init_line']}→{la['instant_line']} ({direction_cn}) "
                    f"({len(ah.get('companies', []))}家公司)")
    elif ah and 'error' in ah:
        lines.append(f"  亚盘: ⚠️ {ah['error']}")
    else:
        lines.append("  亚盘: ❌ 缺失")

    # 大小球
    tot = data.get('totals')
    if tot and 'line_analysis' in tot:
        la = tot['line_analysis']
        direction_cn = {'up': '升盘', 'down': '退盘⚠️', 'stable': '稳定'}[la['direction']]
        lines.append(f"  大小球: {la['init_line']}→{la['instant_line']} ({direction_cn})")
    elif tot and 'error' in tot:
        lines.append(f"  大小球: ⚠️ {tot['error']}")
    else:
        lines.append("  大小球: ❌ 缺失")

    # 让球指数
    hi = data.get('handicap_index')
    if hi and hi.get('companies'):
        # 优先使用主让球档位 (primary_line), 否则取第一个
        primary_line = hi.get('primary_line', None)
        by_line = hi.get('by_line', {})

        if primary_line and primary_line in by_line:
            # 使用主让球档位的平均数据
            bl = by_line[primary_line]
            # 取该档位的第一家公司作为展示
            c = bl['companies'][0] if bl['companies'] else hi['companies'][0]
            avg_wp = bl['avg_win_prob']
            lines.append(f"  让球指数: 让{primary_line}球 "
                        f"穿盘率{avg_wp}% "
                        f"({bl['count']}家公司, "
                        f"共{len(hi['lines_available'])}档: {', '.join(hi['lines_available'])})")
        else:
            c = hi['companies'][0]
            lines.append(f"  让球指数: 让{c['line']}球 "
                        f"胜{c['win_prob']}/平{c['draw_prob']}/负{c['lose_prob']} "
                        f"→ 穿盘率{c['win_prob']}")
    elif hi and 'error' in hi:
        lines.append(f"  让球指数: ⚠️ {hi['error']}")
    else:
        lines.append("  让球指数: ❌ 缺失")

    lines.append(f"  找到: {len(data['files_found'])}/4 | 缺失: {', '.join(data['files_missing']) if data['files_missing'] else '无'}")

    return '\n'.join(lines)


# ── 快速测试 ──
if __name__ == "__main__":
    print("=" * 60)
    print("XLS xlrd 管道 测试")
    print("=" * 60)

    matches_to_test = [
        '厄瓜多尔VS塞内加尔',
        '荷兰VS厄瓜多尔',
        '荷兰VS日本',
        '科特迪瓦VS厄瓜多尔',
    ]

    for match in matches_to_test:
        print(f"\n{'─' * 50}")
        data = read_all_xls(match)
        print(quick_summary(data))

        # 验证
        assert len(data['files_found']) >= 4, f"{match}: 应有4个文件，实际{len(data['files_found'])}"
        assert data['european'] is not None, f"{match}: 欧洲数据缺失"
        assert data['asian'] is not None, f"{match}: 亚盘数据缺失"

    print("\n" + "=" * 60)
    print("🎉 所有XLS文件读取成功!")
    print("=" * 60)

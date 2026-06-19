# -*- coding: utf-8 -*-
"""
V3.0 伤病追踪模块
位置级伤病影响评估 · 赛前首发确认

数据来源优先级:
  1. confirmed  — 官方确认 (FIFA/球队官宣)
  2. reported   — 媒体广泛报道
  3. doubtful   — 出战成疑
  4. expected   — 预期健康

用法:
  from injury_tracker import check_injuries, INJURY_DB
  impact = check_injuries('葡萄牙')
  # → {total_impact, position_loss, notes, confidence_adj}
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── 伤病状态枚举 ──

STATUS = {
    'out': '❌ 确认缺阵',
    'doubtful': '⚠️ 出战成疑',
    'minor': '🟡 轻伤·可能出战',
    'fit': '✅ 健康',
}


# ── 位置权重 (缺阵对球队的影响) ──

POSITION_WEIGHT = {
    'GK':  2.5,   # 主力门将缺阵影响大
    'CB':  2.0,   # 中后卫·防线核心
    'FB':  1.2,   # 边后卫
    'DM':  1.8,   # 防守中场
    'CM':  1.5,   # 中场组织
    'AM':  2.0,   # 进攻中场·创造力
    'WG':  1.8,   # 边锋·突破
    'FW':  2.5,   # 前锋·进球核心
}


# ══════════════════════════════════════════════════════════
# 伤病数据库
# ══════════════════════════════════════════════════════════

INJURY_DB: Dict[str, dict] = {
    # ── 今晚四场 (6/18 K+L组 MD1) ──
    '葡萄牙': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '主力阵容齐整·C罗最后一届世界杯',
        'last_updated': '2026-06-17',
    },
    '民主刚果': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '世界杯首秀·无伤病报告',
        'last_updated': '2026-06-17',
    },
    '刚果(金)': {  # 别名
        'confirmed_out': [],
        'doubtful': [],
        'notes': '世界杯首秀·无伤病报告',
        'last_updated': '2026-06-17',
    },
    # ── MD2 伤病 (6/19) ──
    '加拿大': {
        'confirmed_out': [],
        'doubtful': [
            {'name': 'Alphonso Davies', 'position': 'LB', 'status': 'doubtful',
             'note': '腿筋受伤·缺战MD1·MD2主帅确认可出战(替补)·体能受限'},
            {'name': 'Moise Bombito', 'position': 'CB', 'status': 'doubtful',
             'note': '骨折恢复中·MD2可能出战'},
        ],
        'notes': '戴维斯恢复训练·预计替补20-30分钟·队长核心',
        'last_updated': '2026-06-18',
    },
    '英格兰': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '阵容齐整·凯恩+贝林厄姆双核健康',
        'last_updated': '2026-06-17',
    },
    '克罗地亚': {
        'confirmed_out': [
            {'name': 'Perisic', 'position': 'WG', 'status': 'out',
             'note': '已从国家队退役·边路突破能力下降'}
        ],
        'doubtful': [
            {'name': 'Modric', 'position': 'CM', 'status': 'doubtful',
             'note': '39岁·体能存疑·可能无法打满全场'}
        ],
        'notes': '黄金一代老化·魔笛+佩剑时代终结',
        'last_updated': '2026-06-17',
    },
    '加纳': {
        'confirmed_out': [],
        'doubtful': [
            {'name': 'Partey', 'position': 'DM', 'status': 'doubtful',
             'note': '赛季末带伤·状态未确认'}
        ],
        'notes': 'Partey出战成疑可能影响中场硬度',
        'last_updated': '2026-06-17',
    },
    '巴拿马': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '无伤病报告·全员可用',
        'last_updated': '2026-06-17',
    },
    '乌兹别克斯坦': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '世界杯首秀·无伤病报告',
        'last_updated': '2026-06-17',
    },
    '哥伦比亚': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': 'J罗+Diaz双核健康·阵容齐整',
        'last_updated': '2026-06-17',
    },

    # ── 已完赛强队 ──
    '阿根廷': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '梅西健康·全队无伤病',
        'last_updated': '2026-06-17',
    },
    '法国': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '姆巴佩健康·阵容深度顶级',
        'last_updated': '2026-06-17',
    },
    '巴西': {
        'confirmed_out': [],
        'doubtful': [
            {'name': 'Neymar', 'position': 'FW', 'status': 'doubtful',
             'note': '伤病恢复中·出场时间受限'}
        ],
        'notes': '内马尔恢复中·维尼修斯+罗德里戈主力',
        'last_updated': '2026-06-17',
    },
    '德国': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '年轻阵容·全员健康·深度顶级',
        'last_updated': '2026-06-17',
    },
    '西班牙': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '罗德里+佩德里健康·阵容齐整',
        'last_updated': '2026-06-17',
    },
    '荷兰': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '范戴克+加克波·防线齐整',
        'last_updated': '2026-06-17',
    },
    '比利时': {
        'confirmed_out': [],
        'doubtful': [
            {'name': 'De Bruyne', 'position': 'AM', 'status': 'doubtful',
             'note': '赛季末轻微伤·首轮可能替补'}
        ],
        'notes': '黄金一代老化·德布劳内轻伤',
        'last_updated': '2026-06-17',
    },
    '挪威': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '哈兰德+厄德高双核健康',
        'last_updated': '2026-06-17',
    },
    '摩洛哥': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '2022四强班底·主力齐整',
        'last_updated': '2026-06-17',
    },
    '日本': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '三笘薫+镰田大地健康·阵容完整',
        'last_updated': '2026-06-17',
    },
    '韩国': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '孙兴慜+金玟哉健康·士气正盛',
        'last_updated': '2026-06-17',
    },
    '美国': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '普利西奇+麦肯尼健康·东道主全主力',
        'last_updated': '2026-06-17',
    },
}

# Default for untracked teams
DEFAULT_INJURY = {
    'confirmed_out': [],
    'doubtful': [],
    'notes': '无伤病数据·默认全员健康',
    'last_updated': '',
}


# ══════════════════════════════════════════════════════════
# 核心API
# ══════════════════════════════════════════════════════════

@dataclass
class InjuryImpact:
    team: str
    confirmed_out: List[dict] = field(default_factory=list)
    doubtful: List[dict] = field(default_factory=list)
    total_weight_loss: float = 0.0       # 累计位置权重损失
    max_confidence_adj: float = 0.0       # -20 to 0
    notes: List[str] = field(default_factory=list)
    overall: str = ''                     # 一句话摘要


def check_injuries(team: str) -> InjuryImpact:
    """
    检查一支球队的伤病情况。

    Returns:
        InjuryImpact with position-weighted severity assessment.
    """
    # Lookup with aliases
    data = INJURY_DB.get(team)
    if not data:
        from match_context import normalize_team_name
        canonical = normalize_team_name(team)
        data = INJURY_DB.get(canonical, DEFAULT_INJURY)

    impact = InjuryImpact(team=team)
    impact.confirmed_out = data.get('confirmed_out', [])
    impact.doubtful = data.get('doubtful', [])

    # Calculate position-weighted loss
    total_loss = 0.0
    for p in impact.confirmed_out:
        pos = p.get('position', 'CM')
        w = POSITION_WEIGHT.get(pos, 1.5)
        total_loss += w
        impact.notes.append(f"❌ {p['name']}({pos}): {p.get('note','缺阵')}")

    for p in impact.doubtful:
        pos = p.get('position', 'CM')
        w = POSITION_WEIGHT.get(pos, 1.5) * 0.5  # doubtful = half weight
        total_loss += w
        impact.notes.append(f"⚠️ {p['name']}({pos}): {p.get('note','出战成疑')}")

    impact.total_weight_loss = total_loss

    # Map to confidence adjustment (max -20%)
    if total_loss == 0:
        impact.confidence_adj = 0
        impact.overall = '全员健康·阵容齐整'
    elif total_loss <= 1.5:
        impact.confidence_adj = -3
        impact.overall = '轻微影响·替补可弥补'
    elif total_loss <= 3.0:
        impact.confidence_adj = -8
        impact.overall = '中度影响·战术需调整'
    elif total_loss <= 5.0:
        impact.confidence_adj = -12
        impact.overall = f'重要缺阵·{len(impact.confirmed_out)}人确认缺阵'
    else:
        impact.confidence_adj = -20
        impact.overall = f'核心缺阵·{len(impact.confirmed_out)}人确认缺阵·实力大减'

    # Add DB notes
    if data.get('notes'):
        impact.notes.append(f'📋 {data["notes"]}')

    return impact


def get_match_injury_impact(home: str, away: str) -> dict:
    """
    双方伤病对比。

    Returns:
        {home_impact, away_impact, differential, confidence_adj}
    """
    hi = check_injuries(home)
    ai = check_injuries(away)

    diff = ai.total_weight_loss - hi.total_weight_loss  # positive = away worse
    adj = ai.confidence_adj - hi.confidence_adj
    # Cap at -15 to 0 for the combined adjustment
    adj = max(-15, min(0, adj))

    return {
        'home': {'loss': hi.total_weight_loss, 'adj': hi.confidence_adj, 'overall': hi.overall},
        'away': {'loss': ai.total_weight_loss, 'adj': ai.confidence_adj, 'overall': ai.overall},
        'differential': diff,
        'confidence_adj': adj,
        'notes': hi.notes + ai.notes,
    }


# ── CLI ──
if __name__ == '__main__':
    for team in ['葡萄牙', '民主刚果', '英格兰', '克罗地亚', '加纳', '巴拿马', '乌兹别克斯坦', '哥伦比亚']:
        impact = check_injuries(team)
        print(f'{team}: {impact.overall} (loss={impact.total_weight_loss:.1f}, adj={impact.confidence_adj})')

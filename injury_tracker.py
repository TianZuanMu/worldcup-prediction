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
    # ── 6月22日 四场 (H+G组 MD3) ──
    '西班牙': {
        'confirmed_out': [
            {'name': 'Víctor Muñoz', 'position': 'CM', 'status': 'out',
             'note': '确认缺阵'},
        ],
        'doubtful': [
            {'name': 'Lamine Yamal', 'position': 'WG', 'status': 'doubtful',
             'note': '从伤病恢复·自认无法踢满全场·可能替补'},
        ],
        'notes': '尼科·威廉姆斯已痊愈有望首发·亚马尔未完全康复·穆尼奥斯缺阵',
        'last_updated': '2026-06-21',
    },
    '沙特阿拉伯': {
        'confirmed_out': [
            {'name': 'Nawaf Al Abed', 'position': 'WG', 'status': 'out',
             'note': '落选大名单'},
        ],
        'doubtful': [
            {'name': 'Nawaf Al-Aqidi', 'position': 'GK', 'status': 'doubtful',
             'note': '主力门将肌肉有伤·出战成疑·奥韦斯大概率首发'},
        ],
        'notes': '主力门将伤疑·防线不确定性增加',
        'last_updated': '2026-06-21',
    },
    '沙特': {  # alias
        'confirmed_out': [
            {'name': 'Nawaf Al Abed', 'position': 'WG', 'status': 'out',
             'note': '落选大名单'},
        ],
        'doubtful': [
            {'name': 'Nawaf Al-Aqidi', 'position': 'GK', 'status': 'doubtful',
             'note': '主力门将肌肉有伤·出战成疑·奥韦斯大概率首发'},
        ],
        'notes': '主力门将伤疑·防线不确定性增加',
        'last_updated': '2026-06-21',
    },
    '比利时': {
        'confirmed_out': [
            {'name': 'Jérémy Doku', 'position': 'WG', 'status': 'out',
             'note': '呼吸道感染·确认缺席'},
            {'name': 'Zeno Debast', 'position': 'CB', 'status': 'out',
             'note': '因伤缺阵'},
        ],
        'doubtful': [],
        'notes': '多库+德巴斯特缺阵·卢卡库+特罗萨德+CDK已于6/19恢复全面合练·具备出场条件',
        'last_updated': '2026-06-21',
    },
    '伊朗': {
        'confirmed_out': [
            {'name': 'Sardar Azmoun', 'position': 'FW', 'status': 'out',
             'note': '已告别本届赛事·锋线支柱缺阵'},
        ],
        'doubtful': [
            {'name': 'Alireza Jahanbakhsh', 'position': 'WG', 'status': 'doubtful',
             'note': '队长·出战成疑'},
        ],
        'notes': '阿兹蒙告别赛事·贾汉巴赫什存疑·进攻端双重打击',
        'last_updated': '2026-06-21',
    },
    '乌拉圭': {
        'confirmed_out': [
            {'name': 'Ronald Araújo', 'position': 'CB', 'status': 'out',
             'note': '肌肉/小腿伤势·确认缺席'},
            {'name': 'Giorgian de Arrascaeta', 'position': 'AM', 'status': 'out',
             'note': '因伤确认缺席'},
        ],
        'doubtful': [
            {'name': 'José Giménez', 'position': 'CB', 'status': 'doubtful',
             'note': '因伤出战成疑'},
        ],
        'notes': '🔴 后防伤病潮: 阿劳霍+德阿拉斯卡埃塔确认缺阵·希门尼斯存疑·双中卫可能同时缺席',
        'last_updated': '2026-06-21',
    },
    '佛得角': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '阵容齐整·无伤病困扰',
        'last_updated': '2026-06-21',
    },
    '新西兰': {
        'confirmed_out': [
            {'name': 'Matt Garbett', 'position': 'CM', 'status': 'out',
             'note': '腿筋伤势·确认无缘本届世界杯剩余比赛'},
        ],
        'doubtful': [],
        'notes': '加贝特缺阵·中场组织受损',
        'last_updated': '2026-06-21',
    },
    '埃及': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '阵容齐整·萨拉赫腿筋已康复·全员可用',
        'last_updated': '2026-06-21',
    },

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
    # ── R16 停赛+伤病 (6/28) ──
    '南非': {
        'confirmed_out': [
            {'name': 'Themba Zwane', 'position': 'AM', 'status': 'out',
             'note': '🔴 红牌·3场禁赛(最后一场)·进攻核心缺阵'},
            {'name': 'Sphephelo Sithole', 'position': 'CM', 'status': 'out',
             'note': '🔴 红牌·禁赛·中场屏障缺失'},
        ],
        'doubtful': [],
        'notes': '🆕 兹瓦内+西索尔红牌停赛·莫科纳黄牌解禁复出·中场一出一进·进攻端削弱·防反体系',
        'last_updated': '2026-06-28',
    },
    # ── MD2 伤病 (6/19) ──
    '加拿大': {
        'confirmed_out': [
            {'name': 'Ismael Kone', 'position': 'CM', 'status': 'out',
             'note': '🆕 腿部骨折·赛季报销·缺席剩余全部比赛'},
        ],
        'doubtful': [
            {'name': 'Moise Bombito', 'position': 'CB', 'status': 'doubtful',
             'note': '骨折恢复中·状态不明'},
            {'name': 'Stephen Eustaquio', 'position': 'DM', 'status': 'doubtful',
             'note': '🆕 肌肉伤势·minor doubt·出战成疑'},
            {'name': 'Alfie Jones', 'position': 'FB', 'status': 'doubtful',
             'note': '🆕 健康问题·出战成疑'},
        ],
        'notes': '🆕 戴维斯复出(X因素·左路升级)·科内骨折报销·欧斯塔基奥+邦比托+琼斯伤疑·中场+防线双重受损',
        'last_updated': '2026-06-28',
    },
    # ── R16 伤病 (6/29) ──
    '巴西': {
        'confirmed_out': [
            {'name': 'Raphinha', 'position': 'WG', 'status': 'out', 'note': '膝伤·缺席本场'},
        ],
        'doubtful': [],
        'notes': '拉菲尼亚伤缺·内马尔伤愈替补待命·边路火力略减',
        'last_updated': '2026-06-29',
    },
    '日本': {
        'confirmed_out': [],
        'doubtful': [
            {'name': 'Takefusa Kubo', 'position': 'AM', 'status': 'doubtful', 'note': '出战成疑'},
        ],
        'notes': '久保建英伤疑·板仓滉可登场·南野+三笘薰已无缘大名单',
        'last_updated': '2026-06-29',
    },
    '德国': {
        'confirmed_out': [
            {'name': 'Nico Schlotterbeck', 'position': 'CB', 'status': 'out', 'note': '伤缺·缺席剩余比赛'},
        ],
        'doubtful': [],
        'notes': '施洛特贝克伤缺·防线核心-1·布朗已复出',
        'last_updated': '2026-06-29',
    },
    '巴拉圭': {
        'confirmed_out': [
            {'name': 'Diego Gomez', 'position': 'MF', 'status': 'out', 'note': '累积黄牌停赛'},
        ],
        'doubtful': [
            {'name': 'Omar Alderete', 'position': 'CB', 'status': 'doubtful', 'note': '上场受伤·出战成疑'},
            {'name': 'Ramon Sosa', 'position': 'FW', 'status': 'doubtful', 'note': '出战成疑'},
        ],
        'notes': '戈麦斯停赛·阿尔米隆解禁复出·阿尔德雷特+索萨伤疑',
        'last_updated': '2026-06-29',
    },
    '荷兰': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '廷贝尔有望复出·阵容接近完整',
        'last_updated': '2026-06-29',
    },
    '摩洛哥': {
        'confirmed_out': [],
        'doubtful': [],
        'notes': '无伤停影响·全员健康·阿布德+阿格德已无缘大名单',
        'last_updated': '2026-06-29',
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
    # 🆕 V3.29fix: 取双方伤病调整的最小值 (伤病总是降低置信度)
    adj = min(hi.confidence_adj, ai.confidence_adj)
    # Cap at -15 to 0
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

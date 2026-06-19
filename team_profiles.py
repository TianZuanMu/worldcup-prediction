"""
V2.9 球队战术画像 & 教练分析
提供: 32队战术风格·阵型·教练大赛经验·风格对抗矩阵
依赖: match_context.py (球队名映射)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


# ── 球队战术画像 ──

@dataclass
class TeamProfile:
    """单队战术画像"""
    team: str                           # 中文名
    playing_style: str                  # 'possession'|'counter'|'high_press'|'direct'|'balanced'|'long_ball'
    formation: str                      # '4-3-3'|'4-2-3-1'|'3-5-2'|'4-4-2' etc.
    coach_name: str
    coach_experience_years: int         # 执教年数
    coach_big_match_score: float        # 0-10 大赛评分
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    tempo: str = 'medium'               # 'fast'|'medium'|'slow'
    defensive_style: str = 'medium_block'  # 'high_line'|'medium_block'|'low_block'|'mixed'


TEAM_PROFILES: Dict[str, TeamProfile] = {
    # ═══ A组 ═══
    '墨西哥': TeamProfile(
        team='墨西哥', playing_style='possession', formation='4-3-3',
        coach_name='Javier Aguirre', coach_experience_years=22,
        coach_big_match_score=7.5,
        strengths=['主场气势', '快速边路', '大赛经验丰富'],
        weaknesses=['防守定位球', '门将不稳定'],
        tempo='fast', defensive_style='medium_block',
    ),
    '南非': TeamProfile(
        team='南非', playing_style='counter', formation='4-2-3-1',
        coach_name='Hugo Broos', coach_experience_years=18,
        coach_big_match_score=6.0,
        strengths=['身体对抗', '快速反击', '非洲杯经验'],
        weaknesses=['技术粗糙', '控球能力弱', '缺乏深度'],
        tempo='fast', defensive_style='low_block',
    ),
    '韩国': TeamProfile(
        team='韩国', playing_style='high_press', formation='4-4-2',
        coach_name='Hong Myung-bo', coach_experience_years=12,
        coach_big_match_score=7.0,
        strengths=['跑动能力', '高压逼抢', '孙兴慜'],
        weaknesses=['防空能力', '伤病深度', '中场创造力'],
        tempo='fast', defensive_style='high_line',
    ),
    '捷克': TeamProfile(
        team='捷克', playing_style='direct', formation='3-5-2',
        coach_name='Ivan Hasek', coach_experience_years=15,
        coach_big_match_score=6.5,
        strengths=['身体对抗', '定位球', '空中优势'],
        weaknesses=['速度慢', '技术粗糙', '控球率低'],
        tempo='medium', defensive_style='medium_block',
    ),

    # ═══ B组 ═══
    '加拿大': TeamProfile(
        team='加拿大', playing_style='counter', formation='4-4-2',
        coach_name='Jesse Marsch', coach_experience_years=10,
        coach_big_match_score=5.5,
        strengths=['速度', '反击效率', '东道主气势'],
        weaknesses=['防守组织', '大赛经验', '中场控制'],
        tempo='fast', defensive_style='medium_block',
    ),
    '波黑': TeamProfile(
        team='波黑', playing_style='balanced', formation='4-2-3-1',
        coach_name='Sergej Barbarez', coach_experience_years=3,
        coach_big_match_score=3.0,
        strengths=['哲科经验', '中场拼抢', '整体纪律'],
        weaknesses=['缺乏速度', '教练经验不足', '进攻创造力'],
        tempo='medium', defensive_style='medium_block',
    ),
    '卡塔尔': TeamProfile(
        team='卡塔尔', playing_style='possession', formation='4-3-3',
        coach_name='Tintin Marquez', coach_experience_years=12,
        coach_big_match_score=5.0,
        strengths=['技术控球', '亚洲杯冠军', '长期集训'],
        weaknesses=['身体对抗', '大赛压力', '防守集中力'],
        tempo='slow', defensive_style='medium_block',
    ),
    '瑞士': TeamProfile(
        team='瑞士', playing_style='balanced', formation='4-2-3-1',
        coach_name='Murat Yakin', coach_experience_years=10,
        coach_big_match_score=7.0,
        strengths=['防守组织', '战术纪律', '大赛稳定'],
        weaknesses=['进攻创造力', '速度不足', '缺乏巨星'],
        tempo='medium', defensive_style='medium_block',
    ),

    # ═══ C组 ═══
    '巴西': TeamProfile(
        team='巴西', playing_style='possession', formation='4-3-3',
        coach_name='Dorival Junior', coach_experience_years=20,
        coach_big_match_score=7.5,
        strengths=['技术优势', '攻击线深度', '个人能力'],
        weaknesses=['防守纪律', '情绪管理', '内马尔依赖'],
        tempo='fast', defensive_style='high_line',
    ),
    '摩洛哥': TeamProfile(
        team='摩洛哥', playing_style='counter', formation='4-3-3',
        coach_name='Walid Regragui', coach_experience_years=8,
        coach_big_match_score=9.0,
        strengths=['防守铁壁', '快速反击', '29场不败(2022)'],
        weaknesses=['控球率低', '进攻单一', '依赖反击'],
        tempo='fast', defensive_style='low_block',
    ),
    '巴拿马': TeamProfile(
        team='巴拿马', playing_style='direct', formation='4-4-2',
        coach_name='Thomas Christiansen', coach_experience_years=9,
        coach_big_match_score=4.5,
        strengths=['身体对抗', '斗志', '定位球'],
        weaknesses=['技术粗糙', '缺乏速度', '整体实力弱'],
        tempo='medium', defensive_style='low_block',
    ),
    '加纳': TeamProfile(
        team='加纳', playing_style='counter', formation='4-2-3-1',
        coach_name='Otto Addo', coach_experience_years=5,
        coach_big_match_score=6.5,
        strengths=['速度', '身体素质', '非洲大赛经验'],
        weaknesses=['防守漏洞', '战术纪律', '中场控制'],
        tempo='fast', defensive_style='medium_block',
    ),

    # ═══ D组 ═══
    '德国': TeamProfile(
        team='德国', playing_style='possession', formation='4-2-3-1',
        coach_name='Julian Nagelsmann', coach_experience_years=10,
        coach_big_match_score=8.0,
        strengths=['整体战术', '中场控制', '大赛底蕴'],
        weaknesses=['中锋问题', '高压防守漏洞', '年轻防线'],
        tempo='fast', defensive_style='high_line',
    ),
    '荷兰': TeamProfile(
        team='荷兰', playing_style='possession', formation='4-3-3',
        coach_name='Ronald Koeman', coach_experience_years=18,
        coach_big_match_score=7.5,
        strengths=['战术体系', '技术能力', '范戴克防守'],
        weaknesses=['前锋不稳定', '大赛心理', '伤病问题'],
        tempo='fast', defensive_style='high_line',
    ),
    '日本': TeamProfile(
        team='日本', playing_style='possession', formation='4-2-3-1',
        coach_name='Hajime Moriyasu', coach_experience_years=10,
        coach_big_match_score=7.0,
        strengths=['技术细腻', '战术执行', '跑动量'],
        weaknesses=['身体对抗', '空中劣势', '终结能力'],
        tempo='fast', defensive_style='high_line',
    ),
    '科特迪瓦': TeamProfile(
        team='科特迪瓦', playing_style='counter', formation='4-3-3',
        coach_name='Emerse Fae', coach_experience_years=2,
        coach_big_match_score=6.0,
        strengths=['速度', '身体素质', '非洲杯冠军'],
        weaknesses=['教练经验', '防守组织', '战术单一'],
        tempo='fast', defensive_style='medium_block',
    ),

    # ═══ E组 ═══
    '英格兰': TeamProfile(
        team='英格兰', playing_style='possession', formation='4-2-3-1',
        coach_name='Thomas Tuchel', coach_experience_years=16,
        coach_big_match_score=9.5,
        strengths=['攻击线豪华', '阵容深度', '教练大赛经验'],
        weaknesses=['后防速度', '点球大战', '媒体压力'],
        tempo='fast', defensive_style='high_line',
    ),
    '克罗地亚': TeamProfile(
        team='克罗地亚', playing_style='possession', formation='4-3-3',
        coach_name='Zlatko Dalic', coach_experience_years=10,
        coach_big_match_score=9.0,
        strengths=['中场控制', '莫德里奇', '大赛韧性'],
        weaknesses=['老龄化', '速度下降', '前锋效率'],
        tempo='slow', defensive_style='medium_block',
    ),
    '美国': TeamProfile(
        team='美国', playing_style='high_press', formation='4-3-3',
        coach_name='Mauricio Pochettino', coach_experience_years=15,
        coach_big_match_score=8.5,
        strengths=['运动能力', '高压逼抢', '东道主+名帅'],
        weaknesses=['大赛经验', '防守纪律', '关键时刻'],
        tempo='fast', defensive_style='high_line',
    ),
    '海地': TeamProfile(
        team='海地', playing_style='counter', formation='4-4-2',
        coach_name='Sebastien Migne', coach_experience_years=8,
        coach_big_match_score=3.5,
        strengths=['斗志', '速度反击'],
        weaknesses=['整体实力', '缺乏深度', '防守组织'],
        tempo='fast', defensive_style='low_block',
    ),

    # ═══ F组 ═══
    '葡萄牙': TeamProfile(
        team='葡萄牙', playing_style='possession', formation='4-3-3',
        coach_name='Roberto Martinez', coach_experience_years=16,
        coach_big_match_score=7.5,
        strengths=['攻击线', 'C罗经验', '阵容深度'],
        weaknesses=['防守转换', 'C罗依赖', '战术僵化'],
        tempo='fast', defensive_style='high_line',
    ),
    '刚果民主共和国': TeamProfile(
        team='刚果民主共和国', playing_style='counter', formation='4-2-3-1',
        coach_name='Sebastien Desabre', coach_experience_years=10,
        coach_big_match_score=5.0,
        strengths=['身体素质', '速度', '非洲杯崛起'],
        weaknesses=['大赛经验', '整体配合', '控球能力'],
        tempo='fast', defensive_style='low_block',
    ),
    '苏格兰': TeamProfile(
        team='苏格兰', playing_style='direct', formation='3-4-3',
        coach_name='Steve Clarke', coach_experience_years=15,
        coach_big_match_score=6.5,
        strengths=['身体对抗', '团队精神', '定位球'],
        weaknesses=['技术能力', '速度不足', '缺乏巨星'],
        tempo='medium', defensive_style='low_block',
    ),
    '匈牙利': TeamProfile(
        team='匈牙利', playing_style='counter', formation='3-4-2-1',
        coach_name='Marco Rossi', coach_experience_years=12,
        coach_big_match_score=6.5,
        strengths=['防守组织', '索博斯洛伊', '反击效率'],
        weaknesses=['深度不足', '控球率', '对阵强队'],
        tempo='medium', defensive_style='medium_block',
    ),

    # ═══ G组 ═══
    '西班牙': TeamProfile(
        team='西班牙', playing_style='possession', formation='4-3-3',
        coach_name='Luis de la Fuente', coach_experience_years=10,
        coach_big_match_score=7.5,
        strengths=['技术控球', '年轻天才', '战术体系'],
        weaknesses=['缺乏中锋', '防守高度', '大赛经验'],
        tempo='medium', defensive_style='high_line',
    ),
    '佛得角': TeamProfile(
        team='佛得角', playing_style='counter', formation='4-4-2',
        coach_name='Bubista', coach_experience_years=8,
        coach_big_match_score=4.0,
        strengths=['防守纪律', '团队精神'],
        weaknesses=['整体实力', '攻击力弱', '大赛首秀'],
        tempo='medium', defensive_style='low_block',
    ),
    '土耳其': TeamProfile(
        team='土耳其', playing_style='balanced', formation='4-2-3-1',
        coach_name='Vincenzo Montella', coach_experience_years=12,
        coach_big_match_score=7.0,
        strengths=['攻击天赋', '年轻球员', '主场气氛'],
        weaknesses=['防守不稳定', '纪律问题', '大起大落'],
        tempo='fast', defensive_style='medium_block',
    ),
    '塞尔维亚': TeamProfile(
        team='塞尔维亚', playing_style='direct', formation='3-5-2',
        coach_name='Dragan Stojkovic', coach_experience_years=15,
        coach_big_match_score=6.5,
        strengths=['身体对抗', '空中优势', '米特罗维奇'],
        weaknesses=['速度慢', '防守转身', '大赛不稳定'],
        tempo='medium', defensive_style='medium_block',
    ),

    # ═══ H组 ═══
    '意大利': TeamProfile(
        team='意大利', playing_style='possession', formation='4-3-3',
        coach_name='Luciano Spalletti', coach_experience_years=25,
        coach_big_match_score=8.5,
        strengths=['防守传统', '战术智慧', '教练经验'],
        weaknesses=['前锋效率', '年轻化', '预选赛困难'],
        tempo='medium', defensive_style='medium_block',
    ),
    '乌拉圭': TeamProfile(
        team='乌拉圭', playing_style='counter', formation='4-2-3-1',
        coach_name='Marcelo Bielsa', coach_experience_years=30,
        coach_big_match_score=9.0,
        strengths=['战术大师', '高压逼抢', '战斗精神'],
        weaknesses=['老龄化过渡', '体能消耗大', '深度'],
        tempo='fast', defensive_style='high_line',
    ),
    '伊朗': TeamProfile(
        team='伊朗', playing_style='counter', formation='4-4-2',
        coach_name='Amir Ghalenoei', coach_experience_years=18,
        coach_big_match_score=6.0,
        strengths=['防守铁壁', '身体对抗', '亚洲经验'],
        weaknesses=['技术粗糙', '攻击力有限', '速度'],
        tempo='medium', defensive_style='low_block',
    ),
    '乌兹别克斯坦': TeamProfile(
        team='乌兹别克斯坦', playing_style='counter', formation='4-4-2',
        coach_name='Timur Kapadze', coach_experience_years=3,
        coach_big_match_score=3.0,
        strengths=['年轻有活力', '亚洲杯经验'],
        weaknesses=['大赛首秀', '教练经验', '整体实力'],
        tempo='medium', defensive_style='low_block',
    ),

    # ═══ I组 (当前比赛日) ═══
    '法国': TeamProfile(
        team='法国', playing_style='possession', formation='4-2-3-1',
        coach_name='Zinedine Zidane', coach_experience_years=8,
        coach_big_match_score=9.5,
        strengths=['姆巴佩', '阵容深度', '大赛基因', '边路突击'],
        weaknesses=['中场平衡', '防守专注度', '队内关系'],
        tempo='fast', defensive_style='high_line',
    ),
    '塞内加尔': TeamProfile(
        team='塞内加尔', playing_style='counter', formation='4-3-3',
        coach_name='Pape Thiaw', coach_experience_years=4,
        coach_big_match_score=6.5,
        strengths=['速度', '身体对抗', '非洲冠军', '马内'],
        weaknesses=['防守组织', '中场控制', '教练大赛经验'],
        tempo='fast', defensive_style='medium_block',
    ),
    '伊拉克': TeamProfile(
        team='伊拉克', playing_style='counter', formation='4-4-2',
        coach_name='Jesus Casas', coach_experience_years=8,
        coach_big_match_score=5.5,
        strengths=['团队精神', '防守纪律', '亚洲杯冠军(2007)'],
        weaknesses=['整体实力', '个人能力', '攻击力弱'],
        tempo='medium', defensive_style='low_block',
    ),
    '挪威': TeamProfile(
        team='挪威', playing_style='direct', formation='4-3-3',
        coach_name='Stale Solbakken', coach_experience_years=16,
        coach_big_match_score=6.0,
        strengths=['哈兰德', '身体对抗', '定位球', '厄德高组织'],
        weaknesses=['大赛经验', '防守速度', '缺乏世界杯履历'],
        tempo='fast', defensive_style='medium_block',
    ),

    # ═══ J组 (当前比赛日) ═══
    '阿根廷': TeamProfile(
        team='阿根廷', playing_style='possession', formation='4-3-3',
        coach_name='Lionel Scaloni', coach_experience_years=6,
        coach_big_match_score=9.5,
        strengths=['梅西', '中场控制', '世界杯冠军', '团队凝聚力'],
        weaknesses=['防线高度', '速度', '梅西依赖'],
        tempo='medium', defensive_style='medium_block',
    ),
    '阿尔及利亚': TeamProfile(
        team='阿尔及利亚', playing_style='possession', formation='4-2-3-1',
        coach_name='Vladimir Petkovic', coach_experience_years=16,
        coach_big_match_score=7.0,
        strengths=['马赫雷斯', '技术控球', '2014逼平德国基因'],
        weaknesses=['防守不稳', '老龄化', '阵容深度'],
        tempo='medium', defensive_style='medium_block',
    ),
    '奥地利': TeamProfile(
        team='奥地利', playing_style='high_press', formation='4-2-3-1',
        coach_name='Ralf Rangnick', coach_experience_years=25,
        coach_big_match_score=8.0,
        strengths=['高压战术', '跑动量', '教练战术大师', '整体性'],
        weaknesses=['缺乏巨星', '终结效率', '深度不足'],
        tempo='fast', defensive_style='high_line',
    ),
    '约旦': TeamProfile(
        team='约旦', playing_style='counter', formation='4-4-2',
        coach_name='Hussein Ammouta', coach_experience_years=15,
        coach_big_match_score=4.5,
        strengths=['防守纪律', '团队精神', '亚洲杯亚军(2023)'],
        weaknesses=['整体实力', '个人能力', '世界杯首秀'],
        tempo='medium', defensive_style='low_block',
    ),

    # ═══ 补全: 6/15回测新队 ═══
    '库拉索': TeamProfile(
        team='库拉索', playing_style='counter', formation='4-4-2',
        coach_name='Dean Gorre', coach_experience_years=6, coach_big_match_score=3.0,
        strengths=['斗志', '防守密集'],
        weaknesses=['整体实力', '个人能力', '世界杯首秀'],
        tempo='slow', defensive_style='low_block',
    ),
    '厄瓜多尔': TeamProfile(
        team='厄瓜多尔', playing_style='counter', formation='4-2-3-1',
        coach_name='Felix Sanchez', coach_experience_years=12, coach_big_match_score=6.5,
        strengths=['Caicedo', '高原主场经验', '年轻活力'],
        weaknesses=['客场表现', '大赛稳定性'],
        tempo='fast', defensive_style='medium_block',
    ),
    '瑞典': TeamProfile(
        team='瑞典', playing_style='direct', formation='4-4-2',
        coach_name='Janne Andersson', coach_experience_years=15, coach_big_match_score=7.0,
        strengths=['Isak', 'Gyokeres', '身体对抗', '定位球'],
        weaknesses=['速度慢', '创造力不足'],
        tempo='medium', defensive_style='medium_block',
    ),
    '突尼斯': TeamProfile(
        team='突尼斯', playing_style='counter', formation='4-3-3',
        coach_name='Jalel Kadri', coach_experience_years=8, coach_big_match_score=5.5,
        strengths=['防守组织', '快速反击', '非洲经验'],
        weaknesses=['攻击力弱', '缺乏巨星'],
        tempo='medium', defensive_style='low_block',
    ),

    # ═══ K组 ═══
    '比利时': TeamProfile(
        team='比利时', playing_style='possession', formation='4-2-3-1',
        coach_name='Domenico Tedesco', coach_experience_years=8,
        coach_big_match_score=7.0,
        strengths=['德布劳内', '攻击线', '大赛经验'],
        weaknesses=['黄金一代老化', '防守速度', '队内不和传闻'],
        tempo='medium', defensive_style='high_line',
    ),
    '哥伦比亚': TeamProfile(
        team='哥伦比亚', playing_style='balanced', formation='4-3-3',
        coach_name='Nestor Lorenzo', coach_experience_years=10,
        coach_big_match_score=7.0,
        strengths=['技术能力', '迪亚斯', '不败纪录'],
        weaknesses=['J罗老化', '防守组织', '关键时刻'],
        tempo='fast', defensive_style='medium_block',
    ),
    '澳大利亚': TeamProfile(
        team='澳大利亚', playing_style='direct', formation='4-4-2',
        coach_name='Tony Popovic', coach_experience_years=12,
        coach_big_match_score=6.0,
        strengths=['身体对抗', '定位球', '团队精神'],
        weaknesses=['技术能力', '速度不足', '亚洲顶级但'],
        tempo='medium', defensive_style='medium_block',
    ),
    '新西兰': TeamProfile(
        team='新西兰', playing_style='direct', formation='4-4-2',
        coach_name='Darren Bazeley', coach_experience_years=6,
        coach_big_match_score=3.5,
        strengths=['身体对抗', '高空球'],
        weaknesses=['整体实力', '技术粗糙', '大赛经验'],
        tempo='medium', defensive_style='low_block',
    ),

    # ═══ L组 ═══
    '智利': TeamProfile(
        team='智利', playing_style='high_press', formation='4-3-3',
        coach_name='Ricardo Gareca', coach_experience_years=25,
        coach_big_match_score=7.5,
        strengths=['高压逼抢', '美洲杯基因', '战斗精神'],
        weaknesses=['黄金一代离开', '新老交替', '锋无力'],
        tempo='fast', defensive_style='high_line',
    ),
    '埃及': TeamProfile(
        team='埃及', playing_style='counter', formation='4-3-3',
        coach_name='Hossam Hassan', coach_experience_years=10,
        coach_big_match_score=6.0,
        strengths=['萨拉赫', '非洲杯经验', '防守组织'],
        weaknesses=['萨拉赫依赖', '中场创造力', '整体性'],
        tempo='fast', defensive_style='medium_block',
    ),
    '阿联酋': TeamProfile(
        team='阿联酋', playing_style='counter', formation='4-4-2',
        coach_name='Paulo Bento', coach_experience_years=18,
        coach_big_match_score=6.5,
        strengths=['技术控球', '亚洲经验', '教练经验'],
        weaknesses=['身体对抗', '速度不足', '大赛压力'],
        tempo='medium', defensive_style='medium_block',
    ),
    '哥斯达黎加': TeamProfile(
        team='哥斯达黎加', playing_style='counter', formation='4-4-2',
        coach_name='Claudio Vivas', coach_experience_years=12,
        coach_big_match_score=6.0,
        strengths=['防守纪律', '大赛经验', '纳瓦斯'],
        weaknesses=['攻击力弱', '老化', '新老交替'],
        tempo='slow', defensive_style='low_block',
    ),
}


# ── 风格对抗矩阵 ──
# 矩阵: (style_home, style_away) → edge (正数=主队优势, 负数=客队优势)

STYLE_MATCHUP_MATRIX: Dict[tuple, dict] = {
    ('possession', 'possession'): {'edge': 0, 'note': '同风格比拼, 看个人能力'},
    ('possession', 'counter'):    {'edge': -2, 'note': '反击克制控球: 控球方防线易被打穿'},
    ('possession', 'high_press'): {'edge': -1, 'note': '高压干扰传控出球'},
    ('possession', 'direct'):     {'edge': 2, 'note': '控球消耗直接打法方的体能'},
    ('possession', 'balanced'):   {'edge': 1, 'note': '控球方有技术优势'},
    ('possession', 'long_ball'):  {'edge': 1, 'note': '控球减少长传方的球权'},
    ('counter', 'possession'):    {'edge': 2, 'note': '反击克制控球: 空间大'},
    ('counter', 'counter'):       {'edge': 0, 'note': '双方保守, 场面可能沉闷'},
    ('counter', 'high_press'):    {'edge': 1, 'note': '反击绕过高压线'},
    ('counter', 'direct'):        {'edge': 0, 'note': '相似, 看转换效率'},
    ('counter', 'balanced'):      {'edge': -1, 'note': '平衡风格能限制反击'},
    ('counter', 'long_ball'):     {'edge': 1, 'note': '反击更快'},
    ('high_press', 'possession'): {'edge': 1, 'note': '高压克制传控: 不让舒服出球'},
    ('high_press', 'counter'):    {'edge': -1, 'note': '高压线留给反击空间'},
    ('high_press', 'high_press'): {'edge': 0, 'note': '对轰, 看体能和纪律'},
    ('high_press', 'direct'):     {'edge': 2, 'note': '高压逼直接打法失误'},
    ('high_press', 'balanced'):   {'edge': 1, 'note': '高压打乱平衡节奏'},
    ('high_press', 'long_ball'):  {'edge': 3, 'note': '高压最克长传: 不给起脚时间'},
    ('direct', 'possession'):     {'edge': -2, 'note': '缺少控球难以对抗传控'},
    ('direct', 'counter'):        {'edge': 0, 'note': '身体对抗决定胜负'},
    ('direct', 'high_press'):     {'edge': -2, 'note': '高压对直接打法很有效'},
    ('direct', 'direct'):         {'edge': 0, 'note': '肉搏战'},
    ('direct', 'balanced'):       {'edge': -1, 'note': '平衡打法更灵活'},
    ('direct', 'long_ball'):      {'edge': 1, 'note': '身体对抗压制长传'},
    ('balanced', 'possession'):   {'edge': -1, 'note': '平衡弱于极致传控'},
    ('balanced', 'counter'):      {'edge': 1, 'note': '平衡能适应反击'},
    ('balanced', 'high_press'):   {'edge': -1, 'note': '以柔克刚的高压'},
    ('balanced', 'direct'):       {'edge': 1, 'note': '平衡更全面'},
    ('balanced', 'balanced'):     {'edge': 0, 'note': '五五开'},
    ('balanced', 'long_ball'):    {'edge': 1, 'note': '平衡更灵活'},
    ('long_ball', 'possession'):  {'edge': -1, 'note': '长传很少控球'},
    ('long_ball', 'counter'):     {'edge': -1, 'note': '长传防线怕反击'},
    ('long_ball', 'high_press'):  {'edge': -3, 'note': '高压最克长传'},
    ('long_ball', 'direct'):      {'edge': -1, 'note': '直接打法更有效'},
    ('long_ball', 'balanced'):    {'edge': -1, 'note': '平衡能限制长传'},
    ('long_ball', 'long_ball'):   {'edge': 0, 'note': '对轰'},
}


# ── 场馆-战术交互数据库 ──

# 北欧/中北欧球队 (炎热气候劣势)
NORTHERN_EUROPEAN_TEAMS = {
    '挪威', '瑞典', '苏格兰', '英格兰', '德国', '荷兰', '捷克',
    '丹麦', '冰岛', '芬兰', '爱尔兰', '比利时', '波兰', '瑞士',
    '奥地利', '克罗地亚', '塞尔维亚', '匈牙利',
}

# 技术盘带型球队 (天然草皮增益)
TECHNICAL_DRIBBLER_TEAMS = {
    '巴西', '阿根廷', '葡萄牙', '西班牙', '法国', '摩洛哥',
    '墨西哥', '日本', '哥伦比亚', '阿尔及利亚', '韩国',
}

# 场馆属性映射 (场馆名 → 关键属性) — 用于字符串输入时的查找
_VENUE_PROPERTIES: Dict[str, dict] = {
    # ═══ 墨西哥 ═══
    'Estadio Azteca':            {'indoor': False, 'altitude_m': 2250, 'natural_grass': True,  'capacity': 87523, 'hot_climate': False},
    'Estadio BBVA':              {'indoor': False, 'altitude_m': 540,  'natural_grass': True,  'capacity': 53500, 'hot_climate': True},
    'Estadio Akron':             {'indoor': False, 'altitude_m': 1566, 'natural_grass': True,  'capacity': 48100, 'hot_climate': False},
    # ═══ 加拿大 ═══
    'BMO Field':                {'indoor': False, 'altitude_m': 76,   'natural_grass': False, 'capacity': 45500, 'hot_climate': False},
    'BC Place':                 {'indoor': True,  'altitude_m': 4,    'natural_grass': False, 'capacity': 54500, 'hot_climate': False},
    # ═══ 美国 ═══
    'MetLife Stadium':          {'indoor': False, 'altitude_m': 3,    'natural_grass': True,  'capacity': 82500, 'hot_climate': False},
    'AT&T Stadium':             {'indoor': True,  'altitude_m': 180,  'natural_grass': False, 'capacity': 80000, 'hot_climate': False},
    'Arrowhead Stadium':        {'indoor': False, 'altitude_m': 277,  'natural_grass': True,  'capacity': 76416, 'hot_climate': False},
    'NRG Stadium':              {'indoor': True,  'altitude_m': 15,   'natural_grass': True,  'capacity': 72220, 'hot_climate': False},
    'Mercedes-Benz Stadium':    {'indoor': True,  'altitude_m': 320,  'natural_grass': False, 'capacity': 71000, 'hot_climate': False},
    'SoFi Stadium':             {'indoor': True,  'altitude_m': 30,   'natural_grass': False, 'capacity': 70240, 'hot_climate': False},
    "Levi's Stadium":           {'indoor': False, 'altitude_m': 4,    'natural_grass': True,  'capacity': 68500, 'hot_climate': False},
    'Lincoln Financial Field':  {'indoor': False, 'altitude_m': 12,   'natural_grass': True,  'capacity': 67594, 'hot_climate': False},
    'Lumen Field':              {'indoor': False, 'altitude_m': 50,   'natural_grass': False, 'capacity': 68740, 'hot_climate': False},
    'Gillette Stadium':         {'indoor': False, 'altitude_m': 70,   'natural_grass': True,  'capacity': 65878, 'hot_climate': False},
    'Hard Rock Stadium':        {'indoor': False, 'altitude_m': 2,    'natural_grass': True,  'capacity': 65326, 'hot_climate': True},
}


def _resolve_venue(venue) -> dict:
    """解析场馆输入: 支持字符串名称或字典格式 (来自 match_context.VENUE_DB)"""
    if not venue:
        return {}
    if isinstance(venue, dict):
        # 字典格式: 提取关键字段
        return {
            'indoor': venue.get('indoor', False),
            'altitude_m': venue.get('altitude_m', 0),
            'natural_grass': venue.get('grass_type', '') in ('natural', 'hybrid'),
            'capacity': venue.get('capacity', 50000),
            'hot_climate': venue.get('hot_climate', False),
        }
    if isinstance(venue, str):
        if venue in _VENUE_PROPERTIES:
            return dict(_VENUE_PROPERTIES[venue])
        for key in _VENUE_PROPERTIES:
            if venue in key or key in venue:
                return dict(_VENUE_PROPERTIES[key])
    return {}


def analyze_venue_tactic_interaction(venue, home_profile=None, away_profile=None) -> dict:
    """
    分析场馆对战术对抗的交互影响

    五大规则:
      1. 室内/人工草皮 + 传控型球队 → -2% (传球精度下降)
      2. 高海拔(>1500m) + 高压逼抢 → -3% (加速疲劳)
      3. 天然草皮 + 技术盘带型球队 → +2% (控球更佳)
      4. 小场地(容量<50000) + 防反 → +2% (空间压缩利于防守)
      5. 炎热气候(>28°C) + 北欧球队 → -2% (热适应劣势)

    Args:
        venue: 场馆名(str) 或 场馆信息(dict, 来自 match_context.VENUE_DB)
        home_profile: 主队 TeamProfile 对象 (可选; 为None时跳过该队)
        away_profile: 客队 TeamProfile 对象 (可选; 为None时跳过该队)

    Returns:
        {'score': float (-5~+5), 'factors': [str], 'confidence_adj': float (-3~+3)}
    """
    props = _resolve_venue(venue)
    if not props:
        return {'score': 0.0, 'factors': [], 'confidence_adj': 0.0}

    score = 0.0
    confidence_adj = 0.0
    factors: List[str] = []

    profiles = [p for p in (home_profile, away_profile) if p is not None]

    indoor = props.get('indoor', False)
    altitude = props.get('altitude_m', 0)
    natural_grass = props.get('natural_grass', True)
    capacity = props.get('capacity', 50000)
    hot_climate = props.get('hot_climate', False)

    for profile in profiles:
        team = profile.team
        style = profile.playing_style

        # 规则1: 室内场馆 + 传控型 → 节奏变化 (FIFA要求全天然草)
        if indoor and style == 'possession':
            score -= 1.0
            confidence_adj -= 2.0
            factors.append(f'{team}传控打法在室内场馆·节奏受影响')

        # 规则2: 高海拔(>1500m) + 高压逼抢 → 疲劳加速
        if altitude > 1500 and style == 'high_press':
            score -= 1.5
            confidence_adj -= 3.0
            factors.append(f'{team}高压战术在{altitude}m高原加速疲劳')

        # 规则3: 天然草皮 + 技术盘带 → 控球增益
        if natural_grass and team in TECHNICAL_DRIBBLER_TEAMS:
            score += 1.0
            confidence_adj += 2.0
            factors.append(f'{team}技术盘带在天然草皮控球更佳')

        # 规则4: 小场地(容量<50000) + 防反 → 空间压缩优势
        if capacity < 50000 and style == 'counter':
            score += 1.0
            confidence_adj += 2.0
            factors.append(f'{team}防反战术适配小场地')

        # 规则5: 炎热气候 + 北欧球队 → 热适应劣势
        if hot_climate and team in NORTHERN_EUROPEAN_TEAMS:
            score -= 1.0
            confidence_adj -= 2.0
            factors.append(f'{team}北欧球队不适应炎热气候')

    # 限制范围
    score = max(-5.0, min(5.0, score))
    confidence_adj = max(-3.0, min(3.0, confidence_adj))

    return {
        'score': round(score, 1),
        'factors': factors,
        'confidence_adj': round(confidence_adj, 1),
    }


def get_venue_tactic_adj(venue_name: str, home_team: str = None, away_team: str = None) -> float:
    """
    便捷函数: 获取场馆-战术置信度调整值

    Args:
        venue_name: 场馆名
        home_team: 主队中文名 (可选)
        away_team: 客队中文名 (可选)

    Returns:
        float: 置信度调整值 (-3 ~ +3)
    """
    hp = get_team_profile(home_team) if home_team else None
    ap = get_team_profile(away_team) if away_team else None
    result = analyze_venue_tactic_interaction(venue_name, hp, ap)
    return result.get('confidence_adj', 0.0)


# ── 核心分析函数 ──

def get_team_profile(team_name: str) -> Optional[TeamProfile]:
    """获取球队战术画像"""
    # 精确匹配
    if team_name in TEAM_PROFILES:
        return TEAM_PROFILES[team_name]
    # 模糊匹配
    for key in TEAM_PROFILES:
        if team_name in key or key in team_name:
            return TEAM_PROFILES[key]
    return None


def analyze_tactical_matchup(home: str, away: str) -> dict:
    """
    分析战术风格对抗
    Returns:
        {'home_style', 'away_style', 'edge', 'note', 'home_advantages', 'away_advantages', 'key_battles'}
    """
    hp = get_team_profile(home)
    ap = get_team_profile(away)

    if not hp or not ap:
        return {'home_style': 'unknown', 'away_style': 'unknown', 'edge': 0,
                'note': '缺少战术数据', 'home_advantages': [], 'away_advantages': [],
                'key_battles': []}

    # 查询风格对抗矩阵
    style_key = (hp.playing_style, ap.playing_style)
    matchup = STYLE_MATCHUP_MATRIX.get(style_key, {'edge': 0, 'note': '风格对抗无数据'})

    home_adv = []
    away_adv = []

    # 速度对比
    if hp.tempo == 'fast' and ap.tempo in ('medium', 'slow'):
        home_adv.append(f'{home}快节奏克制{away}慢节奏')
    if ap.tempo == 'fast' and hp.tempo in ('medium', 'slow'):
        away_adv.append(f'{away}快节奏克制{home}慢节奏')

    # 防线对比
    if hp.defensive_style == 'high_line' and ap.playing_style == 'counter':
        away_adv.append(f'{away}反击针对{home}高位防线')
    if ap.defensive_style == 'high_line' and hp.playing_style == 'counter':
        home_adv.append(f'{home}反击针对{away}高位防线')

    # 定位球优势
    if '定位球' in hp.strengths or '空中优势' in hp.strengths:
        if '防空' in ap.weaknesses or '防守高度' in ap.weaknesses:
            home_adv.append(f'{home}定位球/空中优势 vs {away}防空弱点')

    if '定位球' in ap.strengths or '空中优势' in ap.strengths:
        if '防空' in hp.weaknesses or '防守高度' in hp.weaknesses:
            away_adv.append(f'{away}定位球/空中优势 vs {home}防空弱点')

    return {
        'home_style': hp.playing_style,
        'away_style': ap.playing_style,
        'home_formation': hp.formation,
        'away_formation': ap.formation,
        'edge': matchup['edge'],
        'note': matchup['note'],
        'home_advantages': home_adv,
        'away_advantages': away_adv,
        'key_battles': [],
    }


def analyze_coach(home: str, away: str) -> dict:
    """
    教练对比分析
    Returns:
        {'home_coach', 'away_coach', 'home_score', 'away_score', 'gap', 'impact'}
    """
    hp = get_team_profile(home)
    ap = get_team_profile(away)

    if not hp or not ap:
        return {'home_coach': '?', 'away_coach': '?', 'home_score': 5, 'away_score': 5,
                'gap': 0, 'impact': 0}

    gap = hp.coach_big_match_score - ap.coach_big_match_score

    # 教练经验差距→置信度调整
    if gap >= 3:
        impact = 3
    elif gap >= 1.5:
        impact = 1
    elif gap <= -3:
        impact = -3
    elif gap <= -1.5:
        impact = -1
    else:
        impact = 0

    return {
        'home_coach': hp.coach_name,
        'away_coach': ap.coach_name,
        'home_score': hp.coach_big_match_score,
        'away_score': ap.coach_big_match_score,
        'gap': gap,
        'impact': impact,
    }


def get_tactical_edge(home: str, away: str, venue=None) -> float:
    """
    综合战术优势得分 (-10 ~ +10)
    正数=主队战术优势, 负数=客队战术优势

    Args:
        home: 主队中文名
        away: 客队中文名
        venue: 场馆名(str) 或 场馆信息(dict), 可选 — 启用场馆-战术交互分析
    """
    matchup = analyze_tactical_matchup(home, away)
    coach = analyze_coach(home, away)

    # 风格对抗分 (×2放大, -6~+6)
    style_edge = matchup.get('edge', 0) * 2

    # 教练分 (×1, -3~+3)
    coach_edge = coach.get('impact', 0)

    # 优势计数
    home_adv_count = len(matchup.get('home_advantages', []))
    away_adv_count = len(matchup.get('away_advantages', []))
    adv_edge = (home_adv_count - away_adv_count) * 1.5

    total = style_edge + coach_edge + adv_edge

    # 场馆-战术交互 (V3.0)
    if venue:
        hp = get_team_profile(home)
        ap = get_team_profile(away)
        vti = analyze_venue_tactic_interaction(venue, hp, ap)
        total += vti.get('score', 0)

    return max(-10, min(10, total))


# ── 独立测试 ──
if __name__ == '__main__':
    test_matches = ['法国VS塞内加尔', '伊拉克VS挪威', '阿根廷VS阿尔及利亚', '奥地利VS约旦']

    for mn in test_matches:
        parts = mn.split('VS')
        home, away = parts[0], parts[1]

        print(f"\n{'='*60}")
        print(f"  ⚽ {mn}")

        hp = get_team_profile(home)
        ap = get_team_profile(away)

        if hp:
            print(f"  {home}: {hp.playing_style} {hp.formation} | 教练: {hp.coach_name} (大赛{hv.coach_big_match_score:.0f}/10)" if False else "")
            print(f"  {home}: {hp.playing_style} {hp.formation} | 教练: {hp.coach_name} (大赛{hp.coach_big_match_score:.0f}/10)")
            print(f"    优势: {', '.join(hp.strengths)}")
            print(f"    弱点: {', '.join(hp.weaknesses)}")

        if ap:
            print(f"  {away}: {ap.playing_style} {ap.formation} | 教练: {ap.coach_name} (大赛{ap.coach_big_match_score:.0f}/10)")
            print(f"    优势: {', '.join(ap.strengths)}")
            print(f"    弱点: {', '.join(ap.weaknesses)}")

        matchup = analyze_tactical_matchup(home, away)
        print(f"\n  风格对抗: {matchup['home_style']} vs {matchup['away_style']}")
        print(f"  对抗分: {matchup['edge']:+d} | {matchup['note']}")
        if matchup['home_advantages']:
            for a in matchup['home_advantages']:
                print(f"    → {home}优势: {a}")
        if matchup['away_advantages']:
            for a in matchup['away_advantages']:
                print(f"    → {away}优势: {a}")

        coach = analyze_coach(home, away)
        print(f"\n  教练: {coach['home_coach']}({coach['home_score']:.0f}) vs {coach['away_coach']}({coach['away_score']:.0f}) → 差距{coach['gap']:+.1f} 影响{coach['impact']:+d}")

        edge = get_tactical_edge(home, away)
        print(f"\n  综合战术优势: {edge:+.1f}/10")

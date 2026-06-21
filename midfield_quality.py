"""
V3.2 中场实力对比 (基于2026年6月真实球员数据)
CLOSE级别比赛: 实力接近时, 中场控制力决定胜负。
评分标准: 1-10, 综合考量: 五大联赛主力·欧冠经验·创造力·防守硬度·年龄结构
"""

MIDFIELD_RATING: dict = {
    # ═══ 世界级中场 (9-10) ═══
    '法国':      9.5,   # Olise(1.5亿拜仁)+Doue(1.2亿PSG)+Tchouameni+Camavinga
    '英格兰':    9.5,   # Bellingham(1.3亿皇马)+Rice(1.2亿阿森纳)+Foden
    '西班牙':    9.0,   # Pedri(1.5亿巴萨)+Rodri(金球)+Gavi+Yamal
    '葡萄牙':    9.0,   # Vitinha(1.4亿)+Neves(1.4亿)+B费+B席 → 最豪华中场群
    '德国':      8.5,   # Musiala(1亿)+Wirtz(1亿)+Kimmich+Havertz → 年轻化

    # ═══ 顶级中场 (7.5-8.5) ═══
    '阿根廷':    8.0,   # Enzo(Chelsea)+Mac Allister+De Paul → 世界杯冠军中场
    '巴西':      8.0,   # Guimaraes(7000万纽卡)+Casemiro+内马尔(AM)
    '荷兰':      7.0,   # Gravenberch(9000万)+De Jong(巴萨)+Reijnders(6000万) → Simons伤缺·Timber脑震荡缺阵
    '比利时':    7.5,   # De Bruyne(曼城)+Tielemans+Onana → KDB世界级但老化
    '土耳其':    8.0,   # Guler(9000万皇马)+Calhanoglu(国米) → 惊喜升级
    '克罗地亚':  7.5,   # Modric(40/AC米兰)+Kovacic(曼城)+P.Sucic(3000万国米)+Baturina(2400万) → 新老结合

    # ═══ 强力中场 (6.5-7.5) ═══
    '乌拉圭':    7.5,   # Valverde(9000万皇马)+Ugarte(3000万曼联)+Bentancur
    '挪威':      7.0,   # Odegaard(阿森纳核心)+Berge → 创造力强
    '厄瓜多尔':  7.5,   # Caicedo(1亿切尔西) → 亿元先生单核
    '韩国':      7.0,   # Lee Kang-in(PSG)+黄仁范+李在城(美因茨) → 亚洲最强
    '日本':      7.0,   # 远藤航(利物浦)+镰田大地(水晶宫)+久保建英
    '摩洛哥':    6.5,   # Amrabat+Ounahi → 世界杯四强班底
    '瑞士':      7.0,   # Xhaka+Zakaria+Freuler → 硬朗实用
    '奥地利':    7.5,   # Sabitzer(多特)+Laimer(3200万拜仁)+Baumgartner → 德甲帮
    '墨西哥':    6.5,   # Alvarez+Chavez+Pineda → 经验丰富(无五大联赛)
    '哥伦比亚':  6.5,   # James(老化)+Lerma+Uribe → 经验+硬度

    # ═══ 中等级中场 (5-6.5) ═══
    '美国':      6.5,   # McKennie(尤文)+Reyna(伯恩茅斯)+Adams(伯恩茅斯)
    '苏格兰':    6.0,   # McTominay(4000万那不勒斯)+McGinn(维拉)
    '捷克':      6.0,   # Soucek(西汉姆)+Coufal → 英超双核偏防守
    '塞内加尔':  6.0,   # Koulibaly(退)+Gueye → 防守型
    '瑞典':      5.5,   # Ayari(3500万布莱顿)+Bergvall(3500万热刺) → Kulusevski伤缺
    '阿尔及利亚':6.0,   # Bennacer(老化)+Bentaleb → 经验型
    '加拿大':    6.0,   # Kone(萨索洛2500万)+Eustaquio(Porto) → 升级
    '巴拉圭':    5.5,   # Diego Gomez(布莱顿2500万) → 单核
    '伊朗':      5.0,   # 无五大联赛中场·Taremi前锋
    '埃及':      5.5,   # Elneny+Zidane → Salah前锋非中场
    '澳大利亚':  5.5,   # 升级: Irvine+McGree+Circati → 平平
    '加纳':      5.5,   # Partey+Kudus(边锋) → 有硬度
    '乌克兰':    6.5,   # Zinchenko+Sudakov → 技术型
    '波兰':      6.0,   # Zielinski+Linetty → 中规中矩
    '塞尔维亚':  6.5,   # Milinkovic-Savic+Tadic → 技术好

    # ═══ 弱中场 (3-5) ═══
    '波黑':      5.0,   # Tahirovic(500万)+Gigovic(400万)+Memic(350万) → 年轻但缺乏球星·Pjanic已退役
    '卡塔尔':    5.0,   # 亚洲冠军·技术流但低对抗
    '沙特阿拉伯':5.0,   # 技术型·缺乏高强度经验
    '沙特':      5.0,   # alias
    '南非':      4.0,   # 缺乏五大联赛中场
    '海地':      3.5,   # 伊西多尔是前锋
    '库拉索':    2.0,   # 业余半职业
    '佛得角':    3.5,   # 缺乏组织核心
    '新西兰':    4.0,   # 身体流·无技术中场
    '约旦':      3.5,   # 亚洲二流
    '民主刚果':  4.0,   # 身体好·组织差
    '刚果(金)':  4.0,   # 同上(别名)
    '乌兹别克斯坦':4.5, # Khusanov(曼城/CB)不是中场·中场无亮点
    '巴拿马':    4.5,   # Murillo(马赛700万) → 唯一五大联赛
    '伊拉克':    4.0,   # 亚洲级别·无五大联赛
    '突尼斯':    4.5,   # Mejbri(伯恩利1500万) → 独苗
    '哥斯达黎加':5.0,
    '洪都拉斯':  4.0,
    '萨尔瓦多':  3.0,
    '阿联酋':    4.5,
    '中国':      4.0,
    '俄罗斯':    5.5,   # Golovin+Miranda
    '委内瑞拉':  4.5,
    '玻利维亚':  4.0,
    '冰岛':      5.0,
    '匈牙利':    5.5,
    '罗马尼亚':  5.0,
    '希腊':      5.0,
    '丹麦':      7.0,   # Hojbjerg+Eriksen → 均衡
    '威尔士':    6.0,   # Ramsey(老)+Ampadu
    '喀麦隆':    5.5,   # Anguissa+Onana
    '尼日利亚':  6.0,   # Ndidi+Iwobi
    '秘鲁':      5.0,
    '智利':      5.5,
}


def get_midfield_rating(team_name: str) -> float:
    """V3.11: 中场评分·静态表为主·自动计算为fallback"""
    if team_name in MIDFIELD_RATING:
        return MIDFIELD_RATING[team_name]
    from match_context import normalize_team_name
    cn = normalize_team_name(team_name)
    if cn in MIDFIELD_RATING:
        return MIDFIELD_RATING[cn]
    # 🆕 V3.11: 自动推算 — 从球员DB的MF威胁值映射到1-10评分
    try:
        from opponent_db import _count_attacking_threat
        _, mf_val, _, _, _ = _count_attacking_threat(team_name, 'moderate')
        # MF威胁值(0-15) → 评分(2-9.5): 评分 = mf_val * 0.7
        auto_rating = min(9.5, max(2.0, mf_val * 0.7))
        return round(auto_rating, 1)
    except Exception:
        pass
    from fifa_rank_db import get_team_info
    info = get_team_info(team_name)
    if info.get('conf', 'Unknown') != 'Unknown':
        for cn_name in MIDFIELD_RATING:
            if normalize_team_name(cn_name) == cn:
                return MIDFIELD_RATING[cn_name]
    return 5.0


def compare_midfield(home_cn: str, away_cn: str) -> dict:
    """比较两队中场实力"""
    home_r = get_midfield_rating(home_cn)
    away_r = get_midfield_rating(away_cn)
    gap = home_r - away_r

    if abs(gap) < 0.5:
        edge = 'neutral'; adj = 0
        note = '中场势均力敌'
    elif gap >= 2.0:
        edge = 'home'; adj = 5
        note = f'主队中场碾压(差{gap:.1f}分)·控制力优势'
    elif gap >= 1.0:
        edge = 'home'; adj = 3
        note = f'主队中场占优(差{gap:.1f}分)'
    elif gap >= 0.5:
        edge = 'home'; adj = 2
        note = f'主队中场略优(差{gap:.1f}分)'
    elif gap <= -2.0:
        edge = 'away'; adj = -5
        note = f'客队中场碾压(差{abs(gap):.1f}分)·控制力优势'
    elif gap <= -1.0:
        edge = 'away'; adj = -3
        note = f'客队中场占优(差{abs(gap):.1f}分)'
    else:
        edge = 'away'; adj = -2
        note = f'客队中场略优(差{abs(gap):.1f}分)'

    return {
        'home_rating': home_r, 'away_rating': away_r,
        'edge': edge, 'gap': abs(gap),
        'confidence_adj': adj, 'note': note,
    }


if __name__ == '__main__':
    tests = [('韩国', '捷克'), ('加拿大', '波黑'), ('澳大利亚', '土耳其'), ('科特迪瓦', '厄瓜多尔')]
    for h, a in tests:
        r = compare_midfield(h, a)
        print(f'{h}({r["home_rating"]}) vs {a}({r["away_rating"]}): {r["note"]} | adj={r["confidence_adj"]:+d}%')

# -*- coding: utf-8 -*-
"""V2.2 完整复盘: 6月12-14日 全部8场 (含必发)"""
from betfair_store import save_betfair
from dimension12_books import analyze_books_structure

matches = [
    {'name':'墨西哥VS南非','kickoff':'2026-06-12T03:00','actual':'2-0','result':'home',
     'odds':{'home':1.43,'draw':4.29,'away':8.16},
     'bf':{'hp':1.45,'dp':4.70,'ap':9.40,'hv':34156472,'dv':2557238,'av':2366360,
           'hpnl':-10.447,'dpnl':27.061,'apnl':16.836,'hh':32,'dh':-71,'ah':-48},
     'notes':'谨防主胜过热','gap':'big'},
    {'name':'韩国VS捷克','kickoff':'2026-06-12T10:00','actual':'2-1','result':'home',
     'odds':{'home':2.55,'draw':3.07,'away':2.96},
     'bf':{'hp':2.66,'dp':3.20,'ap':3.20,'hv':5797684,'dv':3601840,'av':3604535,
           'hpnl':-2.418,'dpnl':1.478,'apnl':1.470,'hh':20,'dh':-11,'ah':-14},
     'notes':'成交量与概率相差不大','gap':'close'},
    {'name':'加拿大VS波黑','kickoff':'2026-06-13T03:00','actual':'1-1','result':'draw',
     'odds':{'home':1.84,'draw':3.46,'away':4.55},
     'bf':{'hp':1.92,'dp':3.70,'ap':4.90,'hv':38629268,'dv':3290420,'av':3928787,
           'hpnl':-28.320,'dpnl':33.674,'apnl':26.597,'hh':63,'dh':-74,'ah':-60},
     'notes':'谨防主胜过热','gap':'moderate'},
    {'name':'美国VS巴拉圭','kickoff':'2026-06-13T09:00','actual':'4-1','result':'home',
     'odds':{'home':2.04,'draw':3.25,'away':3.83},
     'bf':{'hp':2.16,'dp':3.30,'ap':4.30,'hv':25920674,'dv':4187218,'av':3216944,
           'hpnl':-22.664,'dpnl':19.507,'apnl':19.492,'hh':68,'dh':-57,'ah':-61},
     'notes':'谨防主胜过热','gap':'moderate'},
    {'name':'卡塔尔VS瑞士','kickoff':'2026-06-14T03:00','actual':'1-1','result':'draw',
     'odds':{'home':15.16,'draw':6.81,'away':1.20},
     'bf':{'hp':19.0,'dp':8.40,'ap':1.21,'hv':1521666,'dv':1848774,'av':38410243,
           'hpnl':12.869,'dpnl':26.251,'apnl':-4.696,'hh':-46,'dh':-69,'ah':15},
     'notes':'成交量与概率相差不大','gap':'big'},
    {'name':'巴西VS摩洛哥','kickoff':'2026-06-14T06:00','actual':'1-1','result':'draw',
     'odds':{'home':1.66,'draw':3.72,'away':5.44},
     'bf':{'hp':1.74,'dp':3.90,'ap':6.20,'hv':27400620,'dv':2564968,'av':1974564,
           'hpnl':-15.737,'dpnl':21.937,'apnl':19.698,'hh':50,'dh':-69,'ah':-65},
     'notes':'谨防主胜过热','gap':'moderate'},
    {'name':'海地VS苏格兰','kickoff':'2026-06-14T09:00','actual':'0-1','result':'away',
     'odds':{'home':5.56,'draw':4.33,'away':1.56},
     'bf':{'hp':5.80,'dp':4.40,'ap':1.67,'hv':2517856,'dv':2358358,'av':22190809,
           'hpnl':12.463,'dpnl':16.690,'apnl':-9.992,'hh':-46,'dh':-61,'ah':34},
     'notes':'谨防客胜过热','gap':'big'},
    {'name':'澳大利亚VS土耳其','kickoff':'2026-06-14T12:00','actual':'2-0','result':'home',
     'odds':{'home':5.20,'draw':3.67,'away':1.70},
     'bf':{'hp':5.70,'dp':3.80,'ap':1.78,'hv':1705519,'dv':1728985,'av':16197504,
           'hpnl':9.911,'dpnl':13.062,'apnl':-9.200,'hh':-53,'dh':-66,'ah':47},
     'notes':'谨防客胜过热','gap':'moderate'},
]

print('=' * 75)
print('V2.2 完整复盘: 6月12-14日 全部8场 (含必发)')
print('=' * 75)

results = []
for m in matches:
    bf = m['bf']
    save_betfair(m['name'],
        odds=m['odds'],
        betfair={'home_price':bf['hp'],'draw_price':bf['dp'],'away_price':bf['ap'],
                 'home_volume':bf['hv'],'draw_volume':bf['dv'],'away_volume':bf['av'],
                 'home_pnl':bf['hpnl'],'draw_pnl':bf['dpnl'],'away_pnl':bf['apnl'],
                 'home_heat':bf['hh'],'draw_heat':bf['dh'],'away_heat':bf['ah']},
        notes=m['notes'],kickoff=m['kickoff'],source='用户手动输入(完赛复盘)')

    h12 = analyze_books_structure(
        home_odds=m['odds']['home'],draw_odds=m['odds']['draw'],away_odds=m['odds']['away'],
        home_volume=bf['hv'],draw_volume=bf['dv'],away_volume=bf['av'],
        home_pnl=bf['hpnl'],draw_pnl=bf['dpnl'],away_pnl=bf['apnl'],
        strength_gap=m['gap'])

    # V2.2 预测逻辑
    if h12.is_real_hot:
        if h12.draw_signal:
            pred = '平局(真过热)'
        elif h12.hot_side == 'home':
            pred = '客队不败(主真过热)'
        else:
            pred = '主队不败(客真过热)'
    elif h12.is_false_hot:
        pred = '主胜(假过热)' if h12.hot_side == 'home' else '客胜(假过热)'
    elif h12.cold_upset_risk:
        pred = '热门方有风险'
    else:
        # 隐含概率
        o = m['odds']
        total = 1/o['home']+1/o['draw']+1/o['away']
        ih, ia = (1/o['home'])/total, (1/o['away'])/total
        if ih > 0.55: pred = '主胜(健康)'
        elif ia > 0.55: pred = '客胜(健康)'
        else: pred = '平局/均衡(健康)'

    # 正确性
    res = m['result']
    correct = False
    if res == 'home' and ('主胜' in pred or '主队' in pred): correct = True
    if res == 'away' and ('客胜' in pred or '客队' in pred): correct = True
    if res == 'draw' and '平局' in pred: correct = True

    results.append({**m, 'pred':pred, 'correct':correct, 'h12':h12})

# 输出
correct_count = sum(1 for r in results if r['correct'])
print(f'\n📊 准确率: {correct_count}/{len(results)} ({correct_count/len(results)*100:.0f}%)')
print()
print(f'{"比赛":<14} {"实际":<6} {"V2.2预测":<24} {"冷热":<10} {"庄亏热门":<10} {"信号":<12} {"结果"}')
print('─' * 90)
for r in results:
    icon = '✅' if r['correct'] else '❌'
    bf = r['bf']
    # 确定热门方
    o = r['odds']
    if o['home'] < o['away']:
        hot_heat, hot_pnl = bf['hh'], bf['hpnl']
        heat_str = f'主{hot_heat:+d}'
        pnl_str = f'{hot_pnl:+.1f}M'
    else:
        hot_heat, hot_pnl = bf['ah'], bf['apnl']
        heat_str = f'客{hot_heat:+d}'
        pnl_str = f'{hot_pnl:+.1f}M'
    h12 = r['h12']
    signal = '🔴真过热' if h12.is_real_hot else ('🟢假过热' if h12.is_false_hot else '🟢健康')
    if h12.draw_signal: signal += '+平'
    print(f'{r["name"]:<14} {r["actual"]:<6} {r["pred"]:<24} {heat_str:<10} {pnl_str:<10} {signal:<12} {icon}')

# 分类统计
print()
print('─' * 50)
print('分类统计:')
real_hot = [r for r in results if r['h12'].is_real_hot]
false_hot = [r for r in results if r['h12'].is_false_hot]
healthy = [r for r in results if not r['h12'].is_real_hot and not r['h12'].is_false_hot]

print(f'  真过热: {len(real_hot)}场 → 应全部反向 → 正确{sum(1 for r in real_hot if r["correct"])}/{len(real_hot)}')
for r in real_hot:
    print(f'    {r["name"]}: {r["pred"]} vs {r["actual"]} {("✅" if r["correct"] else "❌")}')

print(f'  假过热: {len(false_hot)}场 → 应全部正路 → 正确{sum(1 for r in false_hot if r["correct"])}/{len(false_hot)}')
for r in false_hot:
    print(f'    {r["name"]}: {r["pred"]} vs {r["actual"]} {("✅" if r["correct"] else "❌")}')

print(f'  结构健康: {len(healthy)}场 → 按基本面 → 正确{sum(1 for r in healthy if r["correct"])}/{len(healthy)}')
for r in healthy:
    print(f'    {r["name"]}: {r["pred"]} vs {r["actual"]} {("✅" if r["correct"] else "❌")}')

# 对比: 有必发 vs 无必发
print()
print('─' * 50)
print('必发数据价值验证:')
print(f'  无必发回测 (之前): 2-3/6 (33-50%)')
print(f'  有必发回测 (现在): {correct_count}/{len(results)} ({correct_count/len(results)*100:.0f}%)')
print(f'  提升: +{correct_count/len(results)*100 - 33:.0f}~{correct_count/len(results)*100 - 50:.0f}pp')

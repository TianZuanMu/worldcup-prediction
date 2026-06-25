# -*- coding: utf-8 -*-
"""
V4.0 因子链校准 — 预缓存+快速搜索

Phase 1: 预计算所有比赛的因子输入 (50×5s≈4min)
Phase 2: 243组合×50场纯因子链计算 (243×50×0.001s≈12s)
"""
import json, time, pickle
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Dict
from config import CONF
from pre_match_report import generate_report

BT_FILE = Path(r'C:\Users\A\PyCharmMiscProject\backtest\matches.json')
CACHE_FILE = Path(r'C:\Users\A\PyCharmMiscProject\calib_cache.pkl')

JUNE25 = {
    '南非VS韩国': 'home', '捷克VS墨西哥': 'away', '瑞士VS加拿大': 'home',
    '波黑VS卡塔尔': 'home', '苏格兰VS巴西': 'away', '摩洛哥VS海地': 'home',
}


@dataclass
class MatchInput:
    name: str
    actual: str
    prior_win: float; prior_draw: float; prior_lose: float
    cold: float; gap_level: str; hot_side: str
    form_diff: float
    home_pnl: float; away_pnl: float; draw_pnl: float
    consensus_pct: float; consensus_dir: str; unanimity: float
    books_is_real_hot: bool; d12_hot_idx: float; d12_pnl_conf: float
    has_d12: bool
    mot_diff: float; rotation_risk: float; draw_advance: bool; matchday: int
    has_elite_fw: bool; threat_count: int
    trap_score: float; trap_level: str
    is_extreme: bool; crush_index: float
    big_sell_vol: float


def build_cache():
    """Phase 1: 预计算所有比赛的因子输入"""
    print('Phase 1: 预计算因子输入...')
    with open(BT_FILE, 'r', encoding='utf-8') as f:
        matches = json.load(f)

    all_inputs = []
    pending = [m for m in matches if m.get('actual', {}).get('result', 'pending') != 'pending']

    for i, m in enumerate(pending):
        name = m['match_name']
        actual = m['actual']['result']
        print(f'  [{i+1}/{len(pending)}] {name}...', end=' ', flush=True)
        t0 = time.time()

        try:
            r = generate_report(name)
            bf = getattr(r, '_bf_raw_odds', {}) or {}
            bf_pnl = getattr(r, '_bf_raw_pnls', {}) or {}
            sp = (r.structured.get('score_probabilities') or {}) if hasattr(r, 'structured') else {}
            wp = sp.get('win_probs', {}) if sp else {}

            # Poisson prior
            pw = float(wp.get('home', 0) or 0); pd = float(wp.get('draw', 0) or 0); pl = float(wp.get('away', 0) or 0)
            if pw == 0 and pl == 0:
                bh = bf.get('home', 0) or 0; ba = bf.get('away', 0) or 0; bd = bf.get('draw', 0) or 0
                if bh > 1 and ba > 1:
                    ih = 1/bh; ia = 1/ba; id_ = 1/bd if bd > 1 else 0.05
                    tot = ih+ia+id_; pw=ih/tot*100; pl=ia/tot*100; pd=id_/tot*100
                else:
                    pw=50; pd=25; pl=25

            # Form diff
            fd = 0.0
            try:
                hf = getattr(r.home_recent_form, 'form_score', 5) or 5
                af = getattr(r.away_recent_form, 'form_score', 5) or 5
                fd = hf - af
            except: pass

            # Threat
            mt = getattr(r, 'moderate_threat', None)
            has_elite = mt.get('has_elite_fw', False) if mt else False
            threat_n = len(mt.get('top_players', [])) if mt else 0

            # Motivation
            mot = r.match_motivation
            md = 0; rr = 0; da = False; mday = 3
            if mot:
                md = mot.differential
                rr = max(mot.home_motivation.rotation_risk, mot.away_motivation.rotation_risk)
                da = (mot.home_motivation.scenario == 'draw_enough' and mot.away_motivation.scenario == 'draw_enough')
                mday = getattr(mot, 'matchday', 3) or 3

            # d12
            bs = getattr(r, 'books_structure', None)
            has_d12 = bool(bs)
            d12_is_real = bs.get('is_real_hot', False) if bs else False
            d12_hot = bs.get('hot_index', 15) if bs else 15
            d12_pconf = bs.get('pnl_confidence', 0.5) if bs else 0.5

            # Crush
            ci = 0.0
            try:
                rg = abs(getattr(r, 'fifa_rank_gap', 10))
                vr = getattr(r, 'squad_value_ratio', 5)
                ci = (rg/60*0.6) + (vr/25*0.4)
            except: pass

            inp = MatchInput(
                name=name, actual=actual,
                prior_win=pw, prior_draw=pd, prior_lose=pl,
                cold=getattr(r, 'betfair_cold', 0) or 0,
                gap_level=getattr(r, 'gap_level', 'moderate') or 'moderate',
                hot_side=getattr(r, 'betfair_hot_side', 'home') or 'home',
                form_diff=fd,
                home_pnl=bf_pnl.get('home', 0) or 0,
                away_pnl=bf_pnl.get('away', 0) or 0,
                draw_pnl=bf_pnl.get('draw', 0) or 0,
                consensus_pct=getattr(r, 'xls_consensus_pct', 0) or 0,
                consensus_dir=getattr(r, 'xls_consensus_direction', 'neutral') or 'neutral',
                unanimity=(getattr(r, 'xls_bookmakers', 0) or 0) / 52,
                books_is_real_hot=d12_is_real,
                d12_hot_idx=d12_hot, d12_pnl_conf=d12_pconf, has_d12=has_d12,
                mot_diff=md, rotation_risk=rr, draw_advance=da, matchday=mday,
                has_elite_fw=has_elite, threat_count=threat_n,
                trap_score=r.trap_odds.trap_score if r.trap_odds else 0,
                trap_level=r.trap_odds.trap_level if r.trap_odds else 'none',
                is_extreme=(getattr(r, 'gap_level', '') == 'extreme'),
                crush_index=ci,
                big_sell_vol=getattr(r, 'betfair_big_sell_volume', 0) or 0,
            )
            all_inputs.append(inp)
            print(f'{time.time()-t0:.1f}s')
        except Exception as e:
            print(f'SKIP: {e}')

    # Add June 25
    for name, actual in JUNE25.items():
        print(f'  [J25] {name}...', end=' ', flush=True)
        t0 = time.time()
        try:
            r = generate_report(name)
            bf = getattr(r, '_bf_raw_odds', {}) or {}
            bf_pnl = getattr(r, '_bf_raw_pnls', {}) or {}
            sp = (r.structured.get('score_probabilities') or {}) if hasattr(r, 'structured') else {}
            wp = sp.get('win_probs', {}) if sp else {}
            pw = float(wp.get('home', 0) or 0); pd = float(wp.get('draw', 0) or 0); pl = float(wp.get('away', 0) or 0)
            if pw == 0 and pl == 0:
                bh = bf.get('home', 0) or 0; ba = bf.get('away', 0) or 0; bd = bf.get('draw', 0) or 0
                if bh > 1 and ba > 1:
                    ih=1/bh; ia=1/ba; id_=1/bd if bd>1 else 0.05
                    tot=ih+ia+id_; pw=ih/tot*100; pl=ia/tot*100; pd=id_/tot*100
                else: pw=50; pd=25; pl=25
            fd = 0.0
            try:
                hf=getattr(r.home_recent_form,'form_score',5) or 5
                af=getattr(r.away_recent_form,'form_score',5) or 5
                fd=hf-af
            except: pass
            mt=getattr(r,'moderate_threat',None)
            has_elite=mt.get('has_elite_fw',False) if mt else False
            threat_n=len(mt.get('top_players',[])) if mt else 0
            mot=r.match_motivation; md=0; rr=0; da=False; mday=3
            if mot:
                md=mot.differential
                rr=max(mot.home_motivation.rotation_risk,mot.away_motivation.rotation_risk)
                da=(mot.home_motivation.scenario=='draw_enough' and mot.away_motivation.scenario=='draw_enough')
                mday=getattr(mot,'matchday',3) or 3
            bs=getattr(r,'books_structure',None)
            has_d12=bool(bs)
            d12_is_real=bs.get('is_real_hot',False) if bs else False
            d12_hot=bs.get('hot_index',15) if bs else 15
            d12_pconf=bs.get('pnl_confidence',0.5) if bs else 0.5
            ci=0.0
            try:
                rg=abs(getattr(r,'fifa_rank_gap',10))
                vr=getattr(r,'squad_value_ratio',5)
                ci=(rg/60*0.6)+(vr/25*0.4)
            except: pass
            inp = MatchInput(
                name=name, actual=actual,
                prior_win=pw, prior_draw=pd, prior_lose=pl,
                cold=getattr(r,'betfair_cold',0)or 0,
                gap_level=getattr(r,'gap_level','moderate')or'moderate',
                hot_side=getattr(r,'betfair_hot_side','home')or'home',
                form_diff=fd,
                home_pnl=bf_pnl.get('home',0)or 0,
                away_pnl=bf_pnl.get('away',0)or 0,
                draw_pnl=bf_pnl.get('draw',0)or 0,
                consensus_pct=getattr(r,'xls_consensus_pct',0)or 0,
                consensus_dir=getattr(r,'xls_consensus_direction','neutral')or'neutral',
                unanimity=(getattr(r,'xls_bookmakers',0)or 0)/52,
                books_is_real_hot=d12_is_real,
                d12_hot_idx=d12_hot, d12_pnl_conf=d12_pconf, has_d12=has_d12,
                mot_diff=md, rotation_risk=rr, draw_advance=da, matchday=mday,
                has_elite_fw=has_elite, threat_count=threat_n,
                trap_score=r.trap_odds.trap_score if r.trap_odds else 0,
                trap_level=r.trap_odds.trap_level if r.trap_odds else 'none',
                is_extreme=(getattr(r,'gap_level','')=='extreme'),
                crush_index=ci,
                big_sell_vol=getattr(r,'betfair_big_sell_volume',0)or 0,
            )
            all_inputs.append(inp)
            print(f'{time.time()-t0:.1f}s')
        except Exception as e:
            print(f'SKIP: {e}')

    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(all_inputs, f)
    print(f'\n缓存 {len(all_inputs)} 场比赛 → {CACHE_FILE}')
    return all_inputs


@dataclass
class CalibResult:
    flow_w: float; context_w: float; anomaly_w: float
    md3_draw: float; d12_mild: float
    train_acc: float; fold1_acc: float; fold2_acc: float
    avg_val_acc: float; coverage: float; abstain_rate: float
    total_correct: int; total_wrong: int; total_abstain: int


# Pre-import for speed
from bayes_factors import (
    FactorResult, apply_factor_chain,
    calc_hot_factor, calc_pnl_factor, calc_consensus_factor,
    calc_d12_factor, calc_context_factor, calc_form_factor,
    calc_threat_factor, calc_trap_factor,
)

def run_factor_chain_only(inp: MatchInput, flow_w: float, context_w: float,
                          anomaly_w: float, md3_draw: float, d12_mild: float):
    """Phase 2: 纯因子链计算·无磁盘IO"""

    # Temp override CONF
    save = {}
    for attr in ['factor_weight_hot','factor_weight_pnl','factor_weight_consensus',
                 'factor_weight_context','factor_weight_trap','_calib_md3_draw_boost',
                 '_calib_d12_mild_draw']:
        save[attr] = getattr(CONF, attr, None)
    CONF.factor_weight_hot = flow_w
    CONF.factor_weight_pnl = flow_w
    CONF.factor_weight_consensus = flow_w * 0.8
    CONF.factor_weight_context = context_w
    CONF.factor_weight_trap = anomaly_w
    CONF._calib_md3_draw_boost = md3_draw
    CONF._calib_d12_mild_draw = d12_mild

    raw_factors = [
        calc_hot_factor(cold=inp.cold, gap_level=inp.gap_level,
                       form_diff=inp.form_diff, hot_side=inp.hot_side),
        calc_pnl_factor(home_pnl=inp.home_pnl, away_pnl=inp.away_pnl,
                       draw_pnl=inp.draw_pnl, hot_side=inp.hot_side, cold=inp.cold),
        calc_consensus_factor(consensus_pct=inp.consensus_pct,
                             consensus_direction=inp.consensus_dir,
                             hot_side=inp.hot_side, unanimity=inp.unanimity),
        calc_d12_factor(books_structure={'is_real_hot': inp.books_is_real_hot,
                         'hot_index': inp.d12_hot_idx, 'pnl_confidence': inp.d12_pnl_conf}
                        if inp.has_d12 else {},
                        is_real_hot=(abs(inp.cold) >= 20)),
        calc_context_factor(motivation_diff=inp.mot_diff, home_mot=7, away_mot=7,
                           rotation_risk=inp.rotation_risk,
                           draw_advance_both=inp.draw_advance, matchday=inp.matchday),
        calc_form_factor(form_diff=inp.form_diff),
        calc_threat_factor(has_elite_fw=inp.has_elite_fw, threat_count=inp.threat_count),
        calc_trap_factor(trap_score=inp.trap_score, trap_level=inp.trap_level),
    ]

    result = apply_factor_chain(
        prior=(inp.prior_win, inp.prior_draw, inp.prior_lose),
        raw_factors=raw_factors,
        is_extreme=inp.is_extreme, crush_index=inp.crush_index,
        big_sell_volume=inp.big_sell_vol,
    )

    # Restore
    for attr, val in save.items():
        if val is not None:
            setattr(CONF, attr, val)
        elif hasattr(CONF, attr):
            delattr(CONF, attr)

    return result.prediction


def is_correct(pred: str, actual: str):
    if pred == 'ABSTAIN': return None
    if pred == '主胜': return actual == 'home'
    if pred == '客胜': return actual == 'away'
    if pred == '平局倾向': return actual == 'draw'
    return None


def main():
    print('=' * 60)
    print('V4.0 因子链校准 — 预缓存 + 快速搜索')
    print('=' * 60)

    # Phase 1
    if CACHE_FILE.exists():
        print(f'加载缓存: {CACHE_FILE}')
        with open(CACHE_FILE, 'rb') as f:
            all_inputs = pickle.load(f)
        print(f'  {len(all_inputs)} 场比赛')
    else:
        all_inputs = build_cache()

    # Phase 2
    flow_weights = [0.8, 1.0, 1.2]
    context_weights = [1.0, 1.2, 1.4]
    anomaly_weights = [0.5, 0.8, 1.0]
    md3_draws = [1.00, 1.03, 1.06]
    d12_milds = [1.00, 1.02, 1.05]

    total = len(flow_weights)*len(context_weights)*len(anomaly_weights)*len(md3_draws)*len(d12_milds)
    print(f'\nPhase 2: {total} 组合 × {len(all_inputs)} 场')
    t0 = time.time()

    results: List[CalibResult] = []
    n = len(all_inputs)
    fold1_start = min(30, n); fold1_end = min(40, n)
    fold2_start = min(40, n); fold2_end = n

    count = 0
    for fw in flow_weights:
        for cw in context_weights:
            for aw in anomaly_weights:
                for md3 in md3_draws:
                    for d12m in d12_milds:
                        count += 1
                        train_c = 0; train_w = 0; train_a = 0
                        f1_c = 0; f1_w = 0; f1_a = 0
                        f2_c = 0; f2_w = 0; f2_a = 0

                        for i, inp in enumerate(all_inputs):
                            pred = run_factor_chain_only(inp, fw, cw, aw, md3, d12m)
                            flag = is_correct(pred, inp.actual)

                            if i < fold1_start:
                                if flag is True: train_c += 1
                                elif flag is False: train_w += 1
                                else: train_a += 1
                            if fold1_start <= i < fold1_end:
                                if flag is True: f1_c += 1
                                elif flag is False: f1_w += 1
                                else: f1_a += 1
                            if i >= fold2_start:
                                if flag is True: f2_c += 1
                                elif flag is False: f2_w += 1
                                else: f2_a += 1

                        def acc(c, w): return c/(c+w)*100 if(c+w)>0 else 0
                        def cov(c,w,a): return (c+w)/(c+w+a) if(c+w+a)>0 else 1

                        t_acc = acc(train_c, train_w)
                        f1_acc = acc(f1_c, f1_w)
                        f2_acc = acc(f2_c, f2_w)
                        avg_val = (f1_acc+f2_acc)/2 if f1_acc>0 and f2_acc>0 else max(f1_acc,f2_acc)
                        coverage = cov(f1_c+f2_c, f1_c+f2_w, f1_a+f2_a)
                        abstain_r = (f1_a+f2_a)/(f1_c+f1_w+f1_a+f2_c+f2_w+f2_a)*100 if(f1_c+f1_w+f1_a+f2_c+f2_w+f2_a)>0 else 0

                        # Filters (looser for small validation sets: 10 matches each)
                        if abs(f1_acc - f2_acc) > 8.0:
                            continue
                        if coverage < 0.75:
                            continue

                        results.append(CalibResult(
                            flow_w=fw, context_w=cw, anomaly_w=aw,
                            md3_draw=md3, d12_mild=d12m,
                            train_acc=t_acc, fold1_acc=f1_acc, fold2_acc=f2_acc,
                            avg_val_acc=avg_val, coverage=coverage, abstain_rate=abstain_r,
                            total_correct=f1_c+f2_c, total_wrong=f1_w+f2_w,
                            total_abstain=f1_a+f2_a,
                        ))

                        if count % 50 == 0:
                            elapsed = time.time() - t0
                            best = max(results, key=lambda x: x.avg_val_acc).avg_val_acc if results else 0
                            print(f'  [{count}/{total}] {elapsed:.0f}s | top={best:.1f}% | pass={len(results)}')

    elapsed = time.time() - t0
    print(f'\n搜索完成: {elapsed:.1f}s | {len(results)}/{total} 通过筛选')

    results.sort(key=lambda x: (x.avg_val_acc, -x.abstain_rate), reverse=True)

    header = (f'\n{"Rank":<5} {"Flow":<6} {"Ctx":<6} {"Anom":<6} {"MD3":<6} {"d12m":<6} '
              f'{"训练":<7} {"F1":<7} {"F2":<7} {"均值":<7} {"覆盖":<7} {"弃权":<6}')
    print(header)
    print('-' * 95)

    for i, r in enumerate(results[:15]):
        print(f'{i+1:<5} {r.flow_w:<6.1f} {r.context_w:<6.1f} {r.anomaly_w:<6.1f} '
              f'{r.md3_draw:<6.2f} {r.d12_mild:<6.2f} '
              f'{r.train_acc:<6.1f}% {r.fold1_acc:<6.1f}% {r.fold2_acc:<6.1f}% '
              f'{r.avg_val_acc:<6.1f}% {r.coverage:<6.1%} {r.abstain_rate:<5.1f}%')

    if results:
        best = results[0]
        print(f'\n{"="*60}')
        print(f'🏆 最优: Flow={best.flow_w:.1f} Context={best.context_w:.1f} '
              f'Anomaly={best.anomaly_w:.1f} MD3={best.md3_draw:.2f} d12m={best.d12_mild:.2f}')
        print(f'   验证: {best.avg_val_acc:.1f}% | 覆盖: {best.coverage:.1%} | 弃权: {best.abstain_rate:.1f}%')
        print(f'   F1={best.fold1_acc:.1f}% F2={best.fold2_acc:.1f}% '
              f'(偏差{abs(best.fold1_acc-best.fold2_acc):.1f}pp)')

        # Full backtest
        all_c=0; all_w=0; all_a=0
        for inp in all_inputs:
            pred = run_factor_chain_only(inp, best.flow_w, best.context_w,
                                         best.anomaly_w, best.md3_draw, best.d12_mild)
            flag = is_correct(pred, inp.actual)
            if flag is True: all_c+=1
            elif flag is False: all_w+=1
            else: all_a+=1
        print(f'\n完整回测: {all_c}正确 {all_w}错误 {all_a}弃权')
        print(f'准确率: {all_c}/{all_c+all_w} = {all_c/(all_c+all_w)*100:.1f}%')
        print(f'覆盖率: {(all_c+all_w)/(all_c+all_w+all_a)*100:.1f}%')

        # Gold ratio check
        if abs(best.flow_w-1.0)<0.05 and abs(best.context_w-1.2)<0.05 and abs(best.anomaly_w-0.8)<0.05:
            print(f'\n✨ 黄金权重确认: Flow=1.0, Context=1.2, Anomaly=0.8')


if __name__ == '__main__':
    main()

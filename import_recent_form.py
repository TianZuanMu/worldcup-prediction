# -*- coding: utf-8 -*-
"""
从 近期状态.txt 导入真实赛果数据到 RECENT_RESULTS
用法: python import_recent_form.py
"""
import re, json
from pathlib import Path
from datetime import datetime
from match_context import normalize_team_name

# Team name mapping (txt name -> canonical name)
NAME_MAP = {
    '刚果（金）': '民主刚果',
    '刚果(金)': '民主刚果',
    '沙特阿拉伯': '沙特阿拉伯',
    '沙特': '沙特阿拉伯',
    '加纳队': '加纳',
    '葡萄牙队': '葡萄牙',
    '葡萄牙国家队': '葡萄牙',
}

RESULT_MAP = {'胜': 'W', '平': 'D', '负': 'L', '击败': 'W', '战胜': 'W',
              '不敌': 'L', '惜败': 'L', '惨败': 'L', '告负': 'L',
              '逼平': 'D', '战平': 'D', '握手言和': 'D', '闷平': 'D'}

MONTH_MAP = {'1月': '01', '2月': '02', '3月': '03', '4月': '04', '5月': '05',
             '6月': '06', '7月': '07', '8月': '08', '9月': '09', '10月': '10',
             '11月': '11', '12月': '12'}

def parse_date(text):
    """Parse various Chinese date formats to YYYY-MM-DD"""
    # 2026年6月17日
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    return None

def parse_score(text):
    """Extract score like '1 - 3' or '3-1'"""
    m = re.search(r'(\d+)\s*[-–—]\s*(\d+)', text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None

def determine_result(line, team_name):
    """Determine W/D/L from match description"""
    if '击败' in line or '战胜' in line or '大胜' in line or '完胜' in line or '逆转' in line:
        return 'W'
    if '不敌' in line or '负于' in line or '告负' in line or '惜败' in line or '惨败' in line:
        return 'L'
    if '逼平' in line or '战平' in line or '握手言和' in line or '闷平' in line or '互交白卷' in line:
        return 'D'
    # Check who scored more
    hg, ag = parse_score(line)
    if hg is not None and ag is not None:
        # Need to know if this team is home or away - default: assume they're listed first
        if hg > ag: return 'W'
        if hg < ag: return 'L'
        return 'D'
    return None

def import_all():
    txt_path = Path(__file__).parent / '近期状态.txt'
    if not txt_path.exists():
        print(f'文件不存在: {txt_path}')
        return 0

    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find team sections and their matches
    from recent_form import RECENT_RESULTS

    imported = 0
    current_team = None
    current_matches = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Detect team header: "XXX国家队近5场" or "XXX队近5场"
        team_match = re.match(r'^(.+?)(?:国家队|队)近5场', line)
        if team_match:
            # Save previous team's data
            if current_team and current_matches:
                save_team_data(current_team, current_matches)
                imported += len(current_matches)

            current_team = team_match.group(1).strip()
            current_team = NAME_MAP.get(current_team, current_team)
            current_team = normalize_team_name(current_team)
            current_matches = []
            i += 1
            continue

        # Detect match line with date
        date_match = parse_date(line)
        if date_match and current_team:
            # Look for opponent and score
            opponent = None
            hg, ag = parse_score(line)

            # Try patterns like "XXX vs YYY" or "YYY vs XXX"
            vs_match = re.search(r'(.+?)\s*(?:vs|VS|vs\.)\s*(.+?)(?:\s+\d|\s*$)', line)
            if vs_match:
                left = vs_match.group(1).strip()
                right = vs_match.group(2).strip()
                # Determine which is the opponent
                if current_team in left or left in current_team:
                    opponent = right
                else:
                    opponent = left

            # If opponent found, look at next 1-2 lines for score and result description
            if opponent:
                result = None
                desc_lines = []
                for j in range(i, min(i+3, len(lines))):
                    desc_lines.append(lines[j].strip())

                full_desc = ' '.join(desc_lines)

                if hg is None:
                    hg, ag = parse_score(full_desc)

                # Determine result
                result = determine_result(full_desc, current_team)
                if result is None and hg is not None and ag is not None:
                    result = 'W' if hg > ag else ('D' if hg == ag else 'L')

                if opponent and result and hg is not None:
                    # Normalize opponent
                    opponent = NAME_MAP.get(opponent, opponent)
                    opponent = normalize_team_name(opponent)
                    if opponent == current_team:
                        opponent = NAME_MAP.get(right, right) if right != current_team else left

                    # Get opponent rank
                    from fifa_rank_db import get_team_info
                    info = get_team_info(opponent)
                    opp_rank = info.get('rank', 50) if info else 50

                    match_entry = {
                        'opponent': opponent, 'result': result,
                        'score': f'{hg}-{ag}',
                        'opponent_rank': opp_rank,
                        'home_away': 'neutral',  # Most matches are neutral/WC
                        'is_official': True,
                        'key_players': 10,
                        'date': date_match,
                        '_source': 'manual_import',
                    }
                    current_matches.append(match_entry)

        i += 1

    # Save last team
    if current_team and current_matches:
        save_team_data(current_team, current_matches)
        imported += len(current_matches)

    print(f'导入完成: {imported} 条赛果')
    return imported


def save_team_data(team, matches):
    """Save parsed matches to RECENT_RESULTS"""
    from recent_form import RECENT_RESULTS
    # Keep only 5 most recent
    matches.sort(key=lambda x: x.get('date', ''), reverse=True)
    recent5 = matches[:5]
    if team not in RECENT_RESULTS:
        RECENT_RESULTS[team] = []
    # Replace existing data with imported data for this team
    old = [m for m in RECENT_RESULTS[team] if m.get('_source') != 'manual_import']
    RECENT_RESULTS[team] = recent5 + old
    print(f'  {team}: {len(recent5)}场')


if __name__ == '__main__':
    import_all()
    # Quick coverage check
    from recent_form import RECENT_RESULTS
    print(f'\n总覆盖: {len(RECENT_RESULTS)} 队')
    for t in sorted(RECENT_RESULTS.keys())[:10]:
        m = RECENT_RESULTS[t]
        results = ''.join([x['result'] for x in m[:5]])
        print(f'  {t:10s} {results}')

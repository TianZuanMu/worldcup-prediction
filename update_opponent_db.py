# -*- coding: utf-8 -*-
"""解析 球员身价.txt 并更新 opponent_db.py"""
import re
import math

# ============================================================
# 1. Parse 球员身价.txt
# ============================================================

def parse_value(raw: str) -> float:
    """Parse value string to millions of euros.
    300万 -> 3.0, 1.2亿 -> 120.0, 1.1亿 -> 110.0, 2亿 -> 200.0
    """
    raw = raw.strip().replace('**', '').replace('*', '')
    if raw in ('—', '-', '', '0'):
        return 0.0
    # Remove commas, spaces
    raw = raw.replace(',', '').replace('，', '').replace(' ', '')
    # Handle "or" format like "4000万 (或2500万)"
    raw = re.sub(r'\([^)]*\)', '', raw).strip()

    if '亿' in raw:
        num = float(raw.replace('亿', ''))
        return num * 100.0  # 1亿 = 100M
    elif '万' in raw:
        num = float(raw.replace('万', ''))
        return num / 100.0  # 300万 = 3M
    else:
        try:
            return float(raw)
        except:
            return 0.0

def parse_age(raw: str):
    """Parse age string. 35岁 -> 35, **25岁** -> 25, — -> None"""
    raw = raw.strip().replace('**', '').replace('*', '')
    if raw in ('—', '-', '', '?'):
        return None
    m = re.search(r'(\d+)', raw)
    if m:
        return int(m.group(1))
    return None

def parse_club(raw: str) -> str:
    """Clean club name. Remove parenthetical English if present."""
    raw = raw.strip()
    # Remove trailing parenthetical like "特尔斯达 (SC Telstar)"
    # But keep if it's the main name
    raw = re.sub(r'\s*\([^)]*\)\s*$', '', raw)
    # Remove leading/trailing whitespace
    raw = raw.strip()
    # Remove "（切尔西租借）" etc
    raw = re.sub(r'（[^）]*）', '', raw)
    return raw

# Top 5 leagues: club name patterns
TOP5_CLUBS = [
    # England (Premier League + Championship clubs that were in PL)
    '阿森纳', '曼城', '曼联', '利物浦', '切尔西', '热刺', '托特纳姆热刺',
    '纽卡斯尔联', '纽卡斯尔', '阿斯顿维拉', '布莱顿', '西汉姆联', '水晶宫',
    '狼队', '富勒姆', '伯恩茅斯', '诺丁汉森林', '布伦特福德', '埃弗顿',
    '利兹联', '莱斯特城', '南安普顿', '伯恩利', '诺维奇', '沃特福德',
    '谢菲尔德联', '米德尔斯堡', '桑德兰', '考文垂', '伊普斯维奇',
    '斯托克城', '赫尔城', '斯旺西', '卡迪夫', '查尔顿', '德比郡',
    # Spain
    '巴塞罗那', '皇家马德里', '马德里竞技', '塞维利亚', '皇家社会',
    '比利亚雷亚尔', '瓦伦西亚', '毕尔巴鄂竞技', '皇家贝蒂斯', '赫罗纳',
    '马略卡', '奥萨苏纳', '塞尔塔', '西班牙人', '巴列卡诺',
    # Italy
    '尤文图斯', '国际米兰', 'AC米兰', '那不勒斯', '罗马', '拉齐奥',
    '亚特兰大', '博洛尼亚', '佛罗伦萨', '都灵', '热那亚', '萨索洛',
    '科莫', '帕尔马', '维罗纳', '卡利亚里', '克雷莫内塞', '威尼斯',
    '乌迪内斯', '恩波利', '蒙扎',
    # Germany
    '拜仁慕尼黑', '多特蒙德', 'RB莱比锡', '勒沃库森', '法兰克福',
    '斯图加特', '门兴格拉德巴赫', '霍芬海姆', '弗赖堡', '沃尔夫斯堡',
    '云达不莱梅', '奥格斯堡', '美因茨', '柏林联合', '圣保利',
    '汉诺威96', '汉堡', '沙尔克04', '杜塞尔多夫', '柏林赫塔',
    # France
    '巴黎圣日耳曼', '摩纳哥', '里昂', '马赛', '里尔', '雷恩',
    '朗斯', '尼斯', '斯特拉斯堡', '洛里昂', '欧塞尔', '图卢兹',
    '蒙彼利埃', '兰斯', '南特', '昂热', '勒阿弗尔',
    '布雷斯特', '克莱蒙',
    # Additional: Benfica/Porto/Sporting are not top5 but Ajax/PSV/Feyenoord also not
]

def is_top5_league(club: str) -> bool:
    """Check if club is in a top-5 league"""
    if not club:
        return False
    for tc in TOP5_CLUBS:
        if tc in club:
            return True
    return False

POS_MAP = {
    '门将': 'GK',
    '后卫': 'CB',  # generic defender -> CB
    '中场': 'MF',
    '前锋': 'FW',
    '中后卫': 'CB',
    '左后卫': 'LB',
    '右后卫': 'RB',
    '左翼卫': 'LB',
    '右翼卫': 'RB',
    '防守型中场': 'MF',
    '攻击型中场': 'MF',
    '中场/前锋': 'MF',
    '中场/后卫': 'MF',
    '中前卫': 'MF',
    '左边锋': 'FW',
    '右边锋': 'FW',
    '前锋/中场': 'FW',
    '中场/边锋': 'MF',
    '左中场': 'MF',
    '右中场': 'MF',
    '左后卫/左翼卫': 'LB',
    '中后卫/左后卫': 'CB',
    '中场/右后卫': 'MF',
}

def map_position(raw: str) -> str:
    """Map Chinese position to short code"""
    raw = raw.strip()
    if raw in POS_MAP:
        return POS_MAP[raw]
    if '门将' in raw or 'GK' in raw.upper():
        return 'GK'
    if '中后' in raw or 'CB' in raw.upper():
        return 'CB'
    if '左后' in raw or 'LB' in raw.upper() or '左翼' in raw:
        return 'LB'
    if '右后' in raw or 'RB' in raw.upper() or '右翼' in raw:
        return 'RB'
    if '后卫' in raw or 'DF' in raw.upper():
        return 'CB'  # generic defender -> CB (consistent with existing DB)
    if '中场' in raw or 'MF' in raw.upper() or '前卫' in raw:
        return 'MF'
    if '前锋' in raw or 'FW' in raw.upper() or '边锋' in raw or '中锋' in raw:
        return 'FW'
    return 'MF'  # default

# Team name mapping from text file to OPPONENT_DB
TEAM_MAP = {
    '民主刚果': '刚果(金)',
}

def parse_players_file(filepath: str) -> dict:
    """Parse the player file, return {team_cn: [player_dicts]}"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    teams = {}
    errors = []

    for i, line in enumerate(lines[1:], start=2):  # skip header
        line = line.strip()
        if not line:
            continue

        # Determine separator
        if '\t' in line:
            parts = line.split('\t')
        else:
            # Space-separated: use regex
            # Pattern: name (optional english)  nationality  age   value  club  position
            parts = re.split(r'\s{2,}', line)

        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) < 5:
            errors.append(f"Line {i}: only {len(parts)} fields: {line[:80]}")
            continue

        # Extract fields
        name_raw = parts[0]
        # Remove English name in parentheses from player name
        name_cn = re.sub(r'\s*\([^)]*\)\s*', '', name_raw).strip()
        if not name_cn:
            name_cn = name_raw.strip()

        nationality = parts[1].strip()
        age_str = parts[2].strip()
        value_str = parts[3].strip()

        if len(parts) == 6:
            club = parts[4].strip()
            position = parts[5].strip()
        elif len(parts) == 5:
            # Could be missing club or position
            if '岁' in parts[3] or parts[3] in ('—', '-'):
                club = '—'
                position = parts[4].strip()
            else:
                club = parts[4].strip()
                position = 'MF'
        else:
            club = '—'
            position = 'MF'

        # Parse values
        age = parse_age(age_str)
        value_m = parse_value(value_str)
        club_clean = parse_club(club)
        pos = map_position(position)
        top5 = is_top5_league(club_clean)

        # Map team name
        team = TEAM_MAP.get(nationality, nationality)

        if team not in teams:
            teams[team] = []

        teams[team].append({
            'name': name_cn,
            'name_raw': name_raw,
            'age': age,
            'value_m': value_m,
            'club': club_clean,
            'pos': pos,
            'top5': top5,
        })

    if errors:
        print(f"Parse errors ({len(errors)}):")
        for e in errors[:20]:
            print(f"  {e}")

    return teams


# ============================================================
# 2. Parse and print summary
# ============================================================
print("=== Parsing 球员身价.txt ===")
teams_data = parse_players_file('球员身价.txt')
print(f"Parsed {sum(len(v) for v in teams_data.values())} players across {len(teams_data)} teams")

for team in sorted(teams_data.keys()):
    players = teams_data[team]
    total_val = sum(p['value_m'] for p in players)
    top5_count = sum(1 for p in players if p['top5'])
    top5_attackers = sum(1 for p in players if p['top5'] and p['pos'] == 'FW')
    no_age = sum(1 for p in players if p['age'] is None)
    print(f"  {team}: {len(players)}人  €{total_val:.0f}M  top5:{top5_count}/{top5_attackers}  no_age:{no_age}")

# ============================================================
# 3. Build updated OPPONENT_DB
# ============================================================
print("\n=== Building updated OPPONENT_DB ===")

# Import existing DB
from opponent_db import OPPONENT_DB as OLD_DB, EN_MAP

# Fuzzy name matching helpers
def normalize_name(name: str) -> str:
    """Remove middle dot, brackets, spaces for comparison"""
    name = name.replace('·', '').replace('•', '').replace(' ', '')
    name = re.sub(r'\([^)]*\)', '', name)
    return name.lower()

def name_match(old_name: str, new_name: str) -> bool:
    """Check if two Chinese player names refer to the same person"""
    n1 = normalize_name(old_name)
    n2 = normalize_name(new_name)
    if n1 == n2:
        return True
    # One is substring of the other
    if len(n1) >= 2 and len(n2) >= 2:
        if n1 in n2 or n2 in n1:
            return True
        # Compare first and last characters
        if n1[:2] == n2[:2] and n1[-1] == n2[-1]:
            return True
    return False

def find_player(old_players: list, new_player: dict) -> int:
    """Find matching player index in old list. -1 if not found."""
    name = new_player['name']
    name_raw = new_player.get('name_raw', name)

    for i, p in enumerate(old_players):
        if not isinstance(p, dict):
            continue
        old_name = p.get('name', '')
        # Direct Chinese name match
        if name_match(old_name, name):
            return i
        if name_match(old_name, name_raw):
            return i
        # Try matching old name in the raw name (English part)
        if name_raw != name:
            en_part = name_raw.replace(name, '').strip(' ()')
            if en_part and (old_name.lower() in en_part.lower() or en_part.lower() in old_name.lower()):
                return i
    return -1

# Build new DB
NEW_DB = {}
update_stats = {'updated': 0, 'added': 0, 'total_new': 0, 'total_old': 0}

for team_cn, new_players in sorted(teams_data.items()):
    old_data = OLD_DB.get(team_cn, {})
    old_players = old_data.get('players', []) if old_data else []

    # Keep old giant_killings and pre_goals_per_game
    old_gk = old_data.get('giant_killings', []) if old_data else []
    old_rank = old_data.get('rank', 50) if old_data else 50
    old_pre_goals = old_data.get('pre_goals_per_game', 1.0) if old_data else 1.0

    # Build new player list - update existing, add new
    updated_players = []
    matched_indices = set()

    for new_p in new_players:
        idx = find_player(old_players, new_p)
        if idx >= 0:
            # Update existing player
            old_p = old_players[idx]
            matched_indices.add(idx)
            player = {
                'name': new_p['name'],
                'value_m': new_p['value_m'],
                'age': new_p['age'] if new_p['age'] is not None else old_p.get('age'),
                'club': new_p['club'],
                'top5': new_p['top5'],
                'pos': new_p['pos'],
            }
            # Preserve extended stats if they existed
            for key in ('intl_goals', 'intl_caps', 'season_goals', 'season_assists'):
                if key in old_p and old_p[key] is not None:
                    player[key] = old_p[key]
            update_stats['updated'] += 1
        else:
            # New player
            player = {
                'name': new_p['name'],
                'value_m': new_p['value_m'],
                'age': new_p['age'],
                'club': new_p['club'],
                'top5': new_p['top5'],
                'pos': new_p['pos'],
            }
            update_stats['added'] += 1
        updated_players.append(player)

    # Keep old players that had extended stats but weren't matched
    # (These might be using different Chinese names)
    for i, old_p in enumerate(old_players):
        if i not in matched_indices and isinstance(old_p, dict):
            has_ext = any(k in old_p for k in ('intl_goals', 'season_goals'))
            if has_ext:
                # Try to match by position+value proximity
                old_name = old_p.get('name', '')
                old_pos = old_p.get('pos', '')
                # Find unmatched new player with closest name or same pos
                found = False
                for j, np in enumerate(updated_players):
                    if np['pos'] == old_pos and abs(np['value_m'] - old_p.get('value_m', 0)) < 10:
                        if 'intl_goals' not in np:
                            for key in ('intl_goals', 'intl_caps', 'season_goals', 'season_assists'):
                                if key in old_p and old_p[key] is not None:
                                    np[key] = old_p[key]
                            found = True
                            break
                if not found:
                    print(f"  ⚠ Orphan extended stats: {old_name} ({team_cn})")

    update_stats['total_new'] += len(updated_players)
    update_stats['total_old'] += len(old_players)

    # Calculate team stats
    total_val = sum(p['value_m'] for p in updated_players)
    top5_count = sum(1 for p in updated_players if p.get('top5', False))
    top5_fw = sum(1 for p in updated_players if p.get('top5', False) and p.get('pos') == 'FW')

    NEW_DB[team_cn] = {
        'rank': old_rank,
        'pre_goals_per_game': old_pre_goals,
        'total_value_m': round(total_val),
        'top5_count': top5_count,
        'top5_attackers': top5_fw,
        'giant_killings': old_gk,
        'players': updated_players,
    }

print(f"Updated: {update_stats['updated']}, Added: {update_stats['added']}")
print(f"Total new players: {update_stats['total_new']}, Total old: {update_stats['total_old']}")

# ============================================================
# 4. Generate new opponent_db.py content
# ============================================================
print("\n=== Generating new opponent_db.py ===")

# Count how many extended-stat players we preserved
ext_count = 0
for team, data in NEW_DB.items():
    for p in data['players']:
        if 'intl_goals' in p:
            ext_count += 1
print(f"Extended stats preserved: {ext_count}")

# Fix orphaned extended stats with manual name mapping
ORPHAN_FIXES = {
    ('瑞典', '维克托·约克雷斯'): '维克托·哲凯赖什',
    ('荷兰', '弗兰基·德容'): '弗伦基·德容',
}

for (team, old_name), new_name in ORPHAN_FIXES.items():
    if team in NEW_DB:
        for p in NEW_DB[team]['players']:
            if p['name'] == new_name or new_name in p['name']:
                # Find old extended stats
                old_data = OLD_DB.get(team, {})
                for old_p in old_data.get('players', []):
                    if isinstance(old_p, dict) and old_p.get('name') == old_name:
                        for key in ('intl_goals', 'intl_caps', 'season_goals', 'season_assists'):
                            if key in old_p and old_p[key] is not None:
                                p[key] = old_p[key]
                        print(f"  ✓ Fixed orphan: {old_name} → {p['name']} ({team})")
                        ext_count += 1
                        break

print(f"Extended stats after fixes: {ext_count}")

# Show teams with most changes
for team in sorted(NEW_DB.keys()):
    old_count = len(OLD_DB.get(team, {}).get('players', [])) if team in OLD_DB else 0
    new_count = len(NEW_DB[team]['players'])
    diff = new_count - old_count
    if diff != 0:
        marker = f"+{diff}" if diff > 0 else str(diff)
        print(f"  {team}: {old_count} → {new_count} ({marker})")

# ============================================================
# 5. Write new opponent_db.py
# ============================================================
print("\n=== Writing opponent_db.py ===")

def format_player(p: dict) -> str:
    """Format a single player dict as Python code"""
    parts = []
    parts.append(f"            {{'name': '{p['name']}'")

    # Format value - use int if whole number
    v = p['value_m']
    if v == int(v):
        parts.append(f", 'value_m': {int(v)}")
    else:
        parts.append(f", 'value_m': {v}")

    if p.get('age') is not None:
        parts.append(f", 'age': {p['age']}")

    club = p.get('club', '')
    if club and club != '—':
        parts.append(f", 'club': '{club}'")

    parts.append(f", 'top5': {p.get('top5', False)}")
    parts.append(f", 'pos': '{p['pos']}'")

    # Extended stats
    for key in ('intl_goals', 'intl_caps', 'season_goals', 'season_assists'):
        if key in p and p[key] is not None:
            parts.append(f", '{key}': {p[key]}")

    parts.append('}')
    return ''.join(parts)

# Generate file content
lines_out = []
lines_out.append('# -*- coding: utf-8 -*-')
lines_out.append('import re')
lines_out.append('')
lines_out.append('"""V3.4 - Auto-updated from 球员身价.txt (2026-06-20)"""')
lines_out.append('')
lines_out.append('OPPONENT_DB = {')

for team_cn in sorted(NEW_DB.keys()):
    data = NEW_DB[team_cn]
    lines_out.append(f"    '{team_cn}': {{")
    lines_out.append(f"        'rank': {data['rank']},")
    lines_out.append(f"        'pre_goals_per_game': {data['pre_goals_per_game']},")
    lines_out.append(f"        'total_value_m': {data['total_value_m']},")
    lines_out.append(f"        'top5_count': {data['top5_count']},")
    lines_out.append(f"        'top5_attackers': {data['top5_attackers']},")
    gk = data['giant_killings']
    lines_out.append(f"        'giant_killings': {gk},")
    lines_out.append(f"        'players': [")
    for p in data['players']:
        lines_out.append(format_player(p) + ',')
    lines_out.append(f"        ],")
    lines_out.append(f"    }},")

lines_out.append('}')
lines_out.append('')

# EN_MAP (preserve from old)
lines_out.append('EN_MAP = {')
# Copy old EN_MAP but add any missing
en_lines = []
for en, cn in sorted(EN_MAP.items()):
    if cn in NEW_DB or en in NEW_DB:
        en_lines.append(f"    '{en}': '{cn}',")
# Check for teams that need new mappings
for team in NEW_DB:
    if team not in EN_MAP.values() and team not in EN_MAP:
        # Find if it's a variation
        pass
lines_out.extend(en_lines)
lines_out.append('}')
lines_out.append('')
lines_out.append('')

# Functions (preserve from old)
# Read the old file to extract functions
with open('opponent_db.py', 'r', encoding='utf-8') as f:
    old_content = f.read()

# Find the function section (after EN_MAP)
func_start = old_content.find('\ndef opponent_quality')
if func_start >= 0:
    func_code = old_content[func_start:].strip()
    lines_out.append(func_code)
    lines_out.append('')

# Write
with open('opponent_db.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines_out))

print("Done! Written to opponent_db.py")
print(f"Total teams: {len(NEW_DB)}")
total_players = sum(len(d['players']) for d in NEW_DB.values())
print(f"Total players: {total_players}")


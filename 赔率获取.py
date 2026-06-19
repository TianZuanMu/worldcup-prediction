import requests
import csv
from datetime import datetime

API_KEY = "bf7dcf5a37a419d8ba6aef80717d20fe"
SPORT_KEY = "soccer_fifa_world_cup"  # 世界杯
REGION = "uk"              # 可选 uk, us, eu, au
ODDS_FORMAT = "decimal"   # 欧洲赔率
MARKETS = "h2h,spreads,totals"  # 同时请求三个市场

url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
params = {
    "apiKey": API_KEY,
    "regions": REGION,
    "markets": MARKETS,
    "oddsFormat": ODDS_FORMAT,
    # "dateFormat": "iso",
}

response = requests.get(url, params=params)

if response.status_code != 200:
    print(f"请求失败，状态码: {response.status_code}")
    print(response.text)
    exit()

data = response.json()
if not data:
    print("当前没有可用的世界杯比赛赔率。")
    exit()

# 准备写入的 CSV 文件
filename = f"worldcup_odds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
# 定义 CSV 表头
fieldnames = [
    "比赛ID", "主队", "客队", "开始时间",
    "博彩公司", "市场类型", "选项", "赔率", "点数/让球数"
]

with open(filename, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for match in data:
        match_id = match.get("id")
        home = match.get("home_team")
        away = match.get("away_team")
        commence = match.get("commence_time")

        for bookmaker in match.get("bookmakers", []):
            bookie = bookmaker.get("title")
            for market in bookmaker.get("markets", []):
                market_type = market.get("key")  # 例如 "h2h", "spreads", "totals"

                for outcome in market.get("outcomes", []):
                    # 基础数据
                    row = {
                        "比赛ID": match_id,
                        "主队": home,
                        "客队": away,
                        "开始时间": commence,
                        "博彩公司": bookie,
                        "市场类型": market_type,
                        "选项": outcome.get("name", outcome.get("description")),  # totals里可能用description
                        "赔率": outcome.get("price"),
                        "点数/让球数": None
                    }
                    # 对于 spreads 和 totals，获取让球点数或大小球界线
                    if market_type == "spreads":
                        row["点数/让球数"] = outcome.get("point")
                    elif market_type == "totals":
                        row["点数/让球数"] = outcome.get("point")

                    writer.writerow(row)

print(f"Data saved to file: {filename}")
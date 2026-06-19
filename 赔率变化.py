import pandas as pd
from pathlib import Path
import re
from datetime import datetime
import os

# ==================== 配置区域（请按实际情况修改） ====================
# 存放所有 worldcup_odds_*.csv 的目录
DATA_DIR = r"C:\Users\A\PyCharmMiscProject"
# 输出文字分析结果的 CSV 文件路径（默认与 DATA_DIR 相同）
OUTPUT_CSV = os.path.join(DATA_DIR, "odds_trend_analysis_text.csv")
# 需要分析的博彩公司（留空分析所有）   示例: ["Bet365", "Pinnacle"]
TARGET_BOOKMAKERS = []
# 需要分析的比赛ID（留空分析所有）     示例: ["c12986f..."]
TARGET_MATCH_IDS = []
# 市场类型筛选：h2h, h2h_lay, spreads, totals  留空则分析所有
TARGET_MARKETS = []  # 如果想只看胜平负，改为 ["h2h"]
# 变化幅度阈值（百分比），变化绝对值小于此值视为“平稳”
TREND_THRESHOLD_PCT = 2.0


# =============================================================

def extract_timestamp_from_filename(filename):
    """从文件名中提取抓取时间戳，格式: worldcup_odds_YYYYMMDD_HHMMSS.csv"""
    match = re.search(r'worldcup_odds_(\d{8})_(\d{6})', filename)
    if match:
        date_str = match.group(1) + match.group(2)
        return datetime.strptime(date_str, '%Y%m%d%H%M%S')
    return None


def load_all_data(data_dir):
    """加载目录下所有 worldcup_odds_*.csv 并合并"""
    csv_files = sorted(Path(data_dir).glob('worldcup_odds_*.csv'))
    if not csv_files:
        print(f"❌ 在 {data_dir} 下未找到 worldcup_odds_*.csv 文件")
        return None

    all_data = []
    for file in csv_files:
        timestamp = extract_timestamp_from_filename(file.name)
        if timestamp is None:
            print(f"⚠️ 无法从文件名 {file.name} 提取时间戳，跳过")
            continue
        try:
            df = pd.read_csv(file, encoding='utf-8-sig')
            df['抓取时间'] = timestamp
            all_data.append(df)
            print(f"✅ 已加载: {file.name}  ({timestamp})，共 {len(df)} 行")
        except Exception as e:
            print(f"❌ 读取 {file.name} 失败: {e}")

    if not all_data:
        return None

    full_df = pd.concat(all_data, ignore_index=True)
    # 确保赔率为数值
    full_df['赔率'] = pd.to_numeric(full_df['赔率'], errors='coerce')
    full_df['点数/让球数'] = pd.to_numeric(full_df['点数/让球数'], errors='coerce')
    full_df.sort_values('抓取时间', inplace=True)
    return full_df


def analyze_trend(group_df):
    """
    对一组赔率序列进行分析，返回一个字典，包含各项趋势指标。
    要求 group_df 至少有两个不同抓取时间点的数据。
    """
    trend = group_df.groupby('抓取时间')['赔率'].mean().reset_index()
    trend = trend.sort_values('抓取时间')

    if len(trend) < 2:
        return None  # 无法分析趋势

    start_odds = trend.iloc[0]['赔率']
    end_odds = trend.iloc[-1]['赔率']
    change = end_odds - start_odds
    change_pct = (change / start_odds) * 100 if start_odds != 0 else 0
    max_odds = trend['赔率'].max()
    min_odds = trend['赔率'].min()
    max_time = trend.loc[trend['赔率'].idxmax(), '抓取时间']
    min_time = trend.loc[trend['赔率'].idxmin(), '抓取时间']
    data_points = len(trend)
    start_time = trend.iloc[0]['抓取时间']
    end_time = trend.iloc[-1]['抓取时间']

    # 趋势判断
    if abs(change_pct) < TREND_THRESHOLD_PCT:
        trend_desc = "平稳"
    elif change > 0:
        trend_desc = "上升"
    else:
        trend_desc = "下降"

    return {
        "起始赔率": round(start_odds, 3),
        "最新赔率": round(end_odds, 3),
        "变化量": round(change, 3),
        "变化百分比": round(change_pct, 2),
        "最高赔率": round(max_odds, 3),
        "最高时间": max_time,
        "最低赔率": round(min_odds, 3),
        "最低时间": min_time,
        "数据点数": data_points,
        "起始时间": start_time,
        "最新时间": end_time,
        "趋势判断": trend_desc
    }


def main():
    df = load_all_data(DATA_DIR)
    if df is None or df.empty:
        return

    print(f"\n📊 总共加载 {len(df)} 条赔率记录")
    print(f"⏰ 时间范围: {df['抓取时间'].min()} ~ {df['抓取时间'].max()}")
    print(f"⚽ 比赛数量: {df['比赛ID'].nunique()}")

    # 筛选
    if TARGET_BOOKMAKERS:
        df = df[df['博彩公司'].isin(TARGET_BOOKMAKERS)]
    if TARGET_MATCH_IDS:
        df = df[df['比赛ID'].isin(TARGET_MATCH_IDS)]
    if TARGET_MARKETS:
        df = df[df['市场类型'].isin(TARGET_MARKETS)]

    # 分组分析 —— 必须使用 dropna=False 保留“点数/让球数”为空的行（如h2h）
    group_cols = ['比赛ID', '主队', '客队', '开始时间', '博彩公司', '市场类型', '选项', '点数/让球数']
    groups = df.groupby(group_cols, dropna=False)

    results = []
    for group_key, group_df in groups:
        match_id, home, away, commence_time, bookmaker, market, outcome, point = group_key

        analysis = analyze_trend(group_df)
        if analysis is None:
            continue

        # 处理让球/大小球界线显示
        point_display = point if pd.notna(point) else ""

        record = {
            "比赛ID": match_id,
            "主队": home,
            "客队": away,
            "比赛开始时间": commence_time,
            "博彩公司": bookmaker,
            "市场类型": market,
            "选项": outcome,
            "让球/大小球界线": point_display,
            **analysis
        }
        results.append(record)

    if not results:
        print("❌ 没有足够的数据生成趋势分析（每组至少需要2个不同抓取时间点的记录）")
        print("   请确认已收集多个 worldcup_odds_*.csv 文件（不同时间抓取）")
        return

    # 转为 DataFrame 并保存
    result_df = pd.DataFrame(results)
    result_df.sort_values(['主队', '客队', '博彩公司', '市场类型', '选项'], inplace=True)
    result_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n✅ 文字分析结果已保存到: {OUTPUT_CSV}")

    # 控制台输出简要报告（前20条）
    print("\n📋 赔率变化趋势简要报告（前20条）：")
    print("-" * 100)
    cols_to_show = ["主队", "客队", "博彩公司", "市场类型", "选项", "起始赔率", "最新赔率", "变化百分比", "趋势判断"]
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 150)
    print(result_df[cols_to_show].head(20).to_string(index=False))
    print(f"\n(完整报告共 {len(result_df)} 条，请查看 CSV 文件)")


if __name__ == "__main__":
    main()
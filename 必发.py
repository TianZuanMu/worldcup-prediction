import betfairlightweight
import logging
import time

# 设置日志（可选，有助于调试）
logging.basicConfig(level=logging.INFO)

# --- 1. 配置您的凭证 ---
# 建议使用环境变量或单独的配置文件，不要直接写死在代码里。
APP_KEY = 'YOUR_APP_KEY'      # 替换为你的 App Key
USERNAME = 'YOUR_USERNAME'    # 替换为你的 Betfair 用户名

# --- 2. 初始化API客户端 (使用交互式登录) ---
# 注意：这里不需要提供密码和证书路径！
trading = betfairlightweight.APIClient(username=USERNAME, app_key=APP_KEY)

# 执行交互式登录，会自动打开浏览器进行网页认证
print("正在执行交互式登录，您的浏览器将自动打开...")
trading.login_interactive()
print("登录成功！")

# --- 3. 获取2026年世界杯的市场目录 ---
# 设置市场过滤器：筛选2026年世界杯（eventTypeId=1是足球）
market_filter = betfairlightweight.filters.market_filter(
    event_type_ids=[1],          # 1 = 足球
    text_query="World Cup 2026"  # 使用文本搜索来定位
)

print("\n正在搜索2026年世界杯的市场...")
# 使用list_market_catalogue获取市场列表
market_catalogue = trading.betting.list_market_catalogue(
    filter=market_filter,
    max_results=20,               # 返回最多20个市场
    market_projection=['RUNNER_METADATA', 'MARKET_START_TIME']  # 包含更多信息
)

if not market_catalogue:
    print("未找到相关市场。请检查文本查询 'World Cup 2026' 或市场是否已开放。")
    trading.logout()
    exit()

# 打印找到的市场信息
print(f"找到 {len(market_catalogue)} 个市场:")
for i, market in enumerate(market_catalogue):
    print(f"{i+1}. 市场名称: {market.market_name}")
    print(f"   市场ID: {market.market_id}")
    print(f"   赛事名称: {market.event.name}  (ID: {market.event.id})")
    if hasattr(market, 'market_start_time'):
        print(f"   开赛时间: {market.market_start_time}")
    print("-" * 30)

# 选择第一个市场作为示例
selected_market_id = market_catalogue[0].market_id
print(f"\n已选择市场: {market_catalogue[0].market_name}")
print(f"即将获取其市场价格... (市场ID: {selected_market_id})")

# --- 4. 获取市场的实时动态数据 (使用list_market_book) ---
# 定义价格投影，仅获取最佳出价/要价，以减少数据量
price_projection = betfairlightweight.filters.price_projection(
    price_data=['EX_BEST_OFFERS']  # 获取最佳卖出/买入价
)

print("\n正在获取实时价格数据...")
# 循环获取3次，展示数据变化
for i in range(3):
    market_book = trading.betting.list_market_book(
        market_ids=[selected_market_id],
        price_projection=price_projection
    )

    if market_book and market_book[0]:
        market_book_obj = market_book[0]
        print(f"\n--- 获取次数: {i+1} ---")
        print(f"市场状态: {market_book_obj.status} (ACTIVE=活跃, SUSPENDED=暂停, CLOSED=关闭)")

        # 遍历每个参赛者（runner）的价格
        for runner in market_book_obj.runners:
            if runner.status == 'ACTIVE':
                # 获取最佳要价（别人想卖出的价格）
                best_offer = runner.ex.available_to_back[0].price if runner.ex.available_to_back else None
                # 获取最佳买价（别人想买入的价格）
                best_bid = runner.ex.available_to_lay[0].price if runner.ex.available_to_lay else None
                # 获取累积交易量
                traded_volume = runner.ex.traded_volume

                print(f"参赛者: {runner.selection_id}")
                print(f"  最佳卖价: {best_offer} | 最佳买价: {best_bid}")
                print(f"  累计交易量: {traded_volume}")
    else:
        print("未获取到市场数据，请检查市场ID是否正确或市场是否处于非活跃状态。")

    # 等待2秒再进行下一次请求，避免频率过高
    time.sleep(2)

print("\n数据获取完成。")

# --- 5. 登出 ---
trading.logout()
print("已安全登出。")
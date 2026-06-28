# -*- coding: utf-8 -*-
"""
赛前高频赔率拉取 —— 智能包装器 (V3.4: 频率10分钟·窗口2h)

每10分钟触发一次，自动判断是否有比赛在2h内即将开始或正在进行。
仅在"临近比赛"窗口内实际拉取赔率，避免非赛时浪费API额度。

用法:
  定时任务(cron/任务计划程序)每10分钟执行:
  PYTHONIOENCODING=utf-8 python "赛前高频赔率.py"
"""

import subprocess
import sys
from datetime import datetime, timedelta, timezone

# 🆕 V3.4: 比赛时间均为北京时间(UTC+8), 明确时区避免本地时区误判
BJT = timezone(timedelta(hours=8))


# ── 比赛时间表 (北京时间·可动态维护) ──
# 格式: (日期, 时间, 主队, 客队)
MATCH_SCHEDULE = [
    # 06月24日
    (6, 24,  1, 0, "葡萄牙", "乌兹别克斯坦"),
    (6, 24,  4, 0, "英格兰", "加纳"),
    (6, 24,  7, 0, "巴拿马", "克罗地亚"),
    (6, 24, 10, 0, "哥伦比亚", "民主刚果"),
    # 06月25日
    (6, 25,  3, 0, "波黑", "卡塔尔"),
    (6, 25,  3, 0, "瑞士", "加拿大"),
    (6, 25,  6, 0, "摩洛哥", "海地"),
    (6, 25,  6, 0, "苏格兰", "巴西"),
    (6, 25,  9, 0, "捷克", "墨西哥"),
    (6, 25,  9, 0, "南非", "韩国"),
    # 06月26日
    (6, 26,  4, 0, "库拉索", "科特迪瓦"),
    (6, 26,  4, 0, "厄瓜多尔", "德国"),
    (6, 26,  7, 0, "日本", "瑞典"),
    (6, 26,  7, 0, "突尼斯", "荷兰"),
    (6, 26, 10, 0, "巴拉圭", "澳大利亚"),
    (6, 26, 10, 0, "土耳其", "美国"),
    # 06月27日
    (6, 27,  3, 0, "挪威", "法国"),
    (6, 27,  3, 0, "塞内加尔", "伊拉克"),
    (6, 27,  8, 0, "佛得角", "沙特"),
    (6, 27,  8, 0, "乌拉圭", "西班牙"),
    (6, 27, 11, 0, "埃及", "伊朗"),
    (6, 27, 11, 0, "新西兰", "比利时"),
    # 06月28日
    (6, 28,  5, 0, "克罗地亚", "加纳"),
    (6, 28,  5, 0, "巴拿马", "英格兰"),
    (6, 28,  7, 30, "哥伦比亚", "葡萄牙"),
    (6, 28,  7, 30, "民主刚果", "乌兹别克斯坦"),
    (6, 28, 10, 0, "阿尔及利亚", "奥地利"),
    (6, 28, 10, 0, "约旦", "阿根廷"),
    # ═══ 1/16决赛 (R32) ═══
    # 06月29日
    (6, 29,  3, 0, "南非", "加拿大"),
    # 06月30日
    (6, 30,  1, 0, "巴西", "日本"),
    (6, 30,  4, 30, "德国", "巴拉圭"),
    (6, 30,  9, 0, "荷兰", "摩洛哥"),
    # 07月01日
    (7,  1,  1, 0, "科特迪瓦", "挪威"),
    (7,  1,  5, 0, "法国", "瑞典"),
    (7,  1,  9, 0, "墨西哥", "厄瓜多尔"),
    # 07月02日
    (7,  2,  0, 0, "英格兰", "民主刚果"),
    (7,  2,  4, 0, "比利时", "塞内加尔"),
    (7,  2,  8, 0, "美国", "波黑"),
    # 07月03日
    (7,  3,  3, 0, "西班牙", "奥地利"),
    (7,  3,  7, 0, "葡萄牙", "克罗地亚"),
    (7,  3, 11, 0, "瑞士", "阿尔及利亚"),
    # 07月04日
    (7,  4,  2, 0, "澳大利亚", "埃及"),
    (7,  4,  6, 0, "阿根廷", "佛得角"),
    (7,  4,  9, 30, "哥伦比亚", "加纳"),
]

# 窗口设置 (小时)
PRE_MATCH_WINDOW = 2.0    # 赛前拉取窗口 (赛前2h开始)
IN_MATCH_WINDOW = 0       # 赛中不拉取 (比赛开始即停止)
FETCH_COOLDOWN = 9.5      # 两次拉取最小间隔(分钟) - 略小于10分钟cron
AUTO_FETCH_COOLDOWN = 20  # auto_fetch 最小间隔(分钟) - XLS/必发变化慢


def get_active_matches() -> list:
    """返回当前在窗口内的比赛列表 (时区: 北京时间 UTC+8)"""
    now = datetime.now(tz=BJT)
    active = []

    for m in MATCH_SCHEDULE:
        month, day, hour, minute, home, away = m
        # 跳过未填的比赛
        if "待更新" in home:
            continue

        try:
            kickoff = datetime(2026, month, day, hour, minute, tzinfo=BJT)
        except ValueError:
            continue

        # 赛前窗口 到 比赛结束
        window_start = kickoff - timedelta(hours=PRE_MATCH_WINDOW)
        window_end = kickoff + timedelta(hours=IN_MATCH_WINDOW)

        if window_start <= now <= window_end:
            minutes_to_kickoff = (kickoff - now).total_seconds() / 60
            if minutes_to_kickoff > 0:
                status = f"赛前{minutes_to_kickoff:.0f}分钟"
            else:
                status = f"比赛中({-minutes_to_kickoff:.0f}分钟)"
            active.append((home, away, kickoff, status))

    return active


def should_fetch() -> bool:
    """检查是否应该拉取 (避免过于频繁)"""
    # 简单策略: 只要有活跃比赛就拉取
    # cron每5分钟触发, 不需要额外冷却检查
    return len(get_active_matches()) > 0


def main():
    active = get_active_matches()

    if not active:
        # 无活跃比赛, 静默跳过
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏟️ 活跃比赛窗口:")
    for home, away, ko, status in active:
        print(f"  {home} vs {away} ({ko.strftime('%m-%d %H:%M')}) — {status}")

    print("  → 拉取赔率...")
    try:
        result = subprocess.run(
            [sys.executable, "赔率获取.py"],
            capture_output=True, text=True, timeout=60,
            cwd=r"C:\Users\A\PyCharmMiscProject",
            encoding='utf-8',
        )
        if result.returncode == 0:
            # 提取保存的文件名
            for line in result.stdout.split('\n'):
                if 'Data saved' in line or 'saved to file' in line:
                    print(f"  ✅ {line.strip()}")
                    break
            else:
                print(f"  ✅ 完成")
        else:
            print(f"  ⚠️ 错误: {result.stderr[:100] if result.stderr else 'unknown'}")
    except Exception as e:
        print(f"  ❌ 异常: {e}")

    # 🆕 联动: 每隔15分钟检查XLS/必发是否需要刷新
    _maybe_trigger_auto_fetch()


# ── auto_fetch 联动 ──
_last_auto_fetch_time = None


def _maybe_trigger_auto_fetch():
    """每隔 AUTO_FETCH_COOLDOWN 分钟触发一次 auto_fetch 阶段检查"""
    global _last_auto_fetch_time
    now = datetime.now()

    if _last_auto_fetch_time:
        elapsed = (now - _last_auto_fetch_time).total_seconds() / 60
        if elapsed < AUTO_FETCH_COOLDOWN:
            return  # 冷却中

    _last_auto_fetch_time = now

    try:
        # 调用 auto_fetch 的 cron 模式 (内置新鲜度保护)
        import subprocess
        result = subprocess.run(
            [sys.executable, '-c',
             'from auto_fetch import auto_fetch_cron_wrapper; auto_fetch_cron_wrapper()'],
            capture_output=True, text=True, timeout=120,
            cwd=r"C:\Users\A\PyCharmMiscProject",
            encoding='utf-8',
        )
        if result.returncode == 0 and result.stdout.strip():
            # 简洁输出
            print(f"  🔄 {result.stdout.strip()}")
    except Exception:
        pass  # auto_fetch 失败不影响赔率管道


if __name__ == "__main__":
    main()

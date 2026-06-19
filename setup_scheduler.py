"""设置Windows定时任务"""
import subprocess, sys, os

def create_task(name, command, minutes):
    tr = f'cmd /c cd /d C:\\Users\\A\\PyCharmMiscProject && set PYTHONIOENCODING=utf-8 && {command}'
    cmd = ['schtasks', '/create', '/tn', name, '/tr', tr, '/sc', 'minute', '/mo', str(minutes), '/f']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if r.returncode == 0:
        print(f'  ✅ {name}: 每{minutes}分钟')
        return True
    else:
        err = (r.stderr or r.stdout or '').strip()
        if 'ERROR: Access is denied' in err:
            print(f'  ❌ {name}: 权限不足，请以管理员身份运行')
        elif 'already exists' in err.lower():
            print(f'  ⚠️ {name}: 已存在')
            return True
        else:
            print(f'  ❌ {name}: {err[:200]}')
        return False

print('创建 Windows 定时任务...')
print()

ok1 = create_task(
    'AutoFetch',
    'python auto_fetch.py --cron',
    30
)
ok2 = create_task(
    'OddsFetch',
    'python 赛前高频赔率.py',
    10
)

if ok1 and ok2:
    print()
    print('验证任务:')
    os.system('schtasks /query /tn AutoFetch /fo table 2>nul')
    print()
    os.system('schtasks /query /tn OddsFetch /fo table 2>nul')
    print()
    print('=' * 50)
    print('  定时任务已就绪!')
    print('  AutoFetch:  每30分钟  (XLS + 必发 + 比赛ID刷新)')
    print('  OddsFetch:  每5分钟   (赔率API拉取)')
    print('=' * 50)
else:
    print()
    print('⚠️ 部分任务创建失败。请以管理员身份运行:')
    print('   python setup_scheduler.py')
    print('   或执行: setup_tasks.bat')

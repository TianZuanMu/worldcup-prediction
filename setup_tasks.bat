@echo off
chcp 65001 >nul
echo ============================================
echo  世界杯预测模型 - 设置定时任务
echo ============================================

echo.
echo [1/2] 创建 AutoFetch 任务 (每30分钟)...
schtasks /create /tn "AutoFetch" /tr "cmd /c \"cd /d C:\Users\A\PyCharmMiscProject && set PYTHONIOENCODING=utf-8 && python auto_fetch.py --cron\"" /sc minute /mo 30 /f

echo.
echo [2/2] 创建 OddsFetch 任务 (每5分钟)...
schtasks /create /tn "OddsFetch" /tr "cmd /c \"cd /d C:\Users\A\PyCharmMiscProject && set PYTHONIOENCODING=utf-8 && python 赛前高频赔率.py\"" /sc minute /mo 5 /f

echo.
echo ============================================
echo  验证任务...
echo ============================================
schtasks /query /tn "AutoFetch" /fo list | findstr /C:"TaskName" /C:"Schedule" /C:"Status"
echo.
schtasks /query /tn "OddsFetch" /fo list | findstr /C:"TaskName" /C:"Schedule" /C:"Status"

echo.
echo 完成!
pause

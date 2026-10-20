@echo off
chcp 65001 >nul
echo ========================================================
echo  国土 AI 竞赛｜推送代码至 GitHub (AI_urban_plan)
echo ========================================================
echo.
git push origin main
if %errorlevel% equ 0 (
    echo.
    echo [OK] 代码已成功推送到 GitHub 远端仓库！
) else (
    echo.
    echo [提示] 如果弹出 GitHub 登录窗口，请点击「Sign in with your browser」完成授权。
    echo 如需使用 Token 推送，可执行:
    echo   git push https://wojiushilyj:你的GitHubToken@github.com/wojiushilyj/AI_urban_plan.git main
)
pause

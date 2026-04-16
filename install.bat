@echo off
chcp 65001 >nul
echo ========================================
echo   필요한 도구를 설치합니다...
echo ========================================
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo ========================================
echo   설치가 완료되었습니다!
echo   이제 run.bat을 더블클릭하여 실행하세요.
echo ========================================
pause

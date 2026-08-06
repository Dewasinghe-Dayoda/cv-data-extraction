@echo off
echo ============================================
echo   Your Local IP Address
echo ============================================
echo.
echo Look for "IPv4 Address" below:
echo.
ipconfig | findstr /i "IPv4"
echo.
echo Share this IP with HR users.
echo They should open: http://YOUR_IP:8501
echo   in their web browser.
echo.
pause

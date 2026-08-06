@echo off
title CV Data Extraction Tool
echo ============================================
echo   CV Data Extraction Tool
echo ============================================
echo.
echo Finding your IP address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do set IP=%%a
set IP=%IP: =%
echo.
echo Your IP address is: %IP%
echo.
echo Share this URL with HR users:
echo   http://%IP%:8501
echo.
echo Press Ctrl+C to stop the server.
echo ============================================
echo.
streamlit run app.py
pause

@echo off
setlocal EnableDelayedExpansion
title Anizium Altyazi Indirici

:: ============================================================
:: Python kontrolu
:: ============================================================
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [UYARI] Python bulunamadi. Otomatik indiriliyor...
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe' -OutFile 'python_installer.exe' -UseBasicParsing"
    if not exist python_installer.exe (
        echo [HATA] Indirilemedi. https://python.org adresinden manuel yukleyin.
        pause
        exit /b 1
    )
    echo [INFO] Python kuruluyor...
    start /wait python_installer.exe /quiet InstallAllUsers=0 PrependPath=1
    del python_installer.exe
    echo [INFO] Kurulum tamamlandi. Script yeniden baslatiliyor...
    start cmd /k "cd /d %~dp0 && altyazi_indirici.bat"
    exit /b
)

:: ============================================================
:: Bagimliliklar
:: ============================================================
echo [INFO] Kutuphaneler yukleniyor...
python -m pip install -r requirements.txt --quiet

echo [INFO] Playwright/Chromium kontrol ediliyor...
python -m playwright install chromium

:: ============================================================
:: Calistir
:: ============================================================
echo.
echo [INFO] Anizium Altyazi Indirici baslatiliyor...
echo.
python subtitle_downloader.py

echo.
pause

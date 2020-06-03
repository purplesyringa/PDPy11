@echo off
python -m pdpy11 --sublime "%~1" --lst
if errorlevel 1 (
    exit /b 1
)

:: cd C:\path\to\bk2010
:: taskkill /f /im java.exe
:: set "a=%~1"
:: if "%a:~-4,-4%" <> "." (
::     echo File extension must be exactly three characters long
::     exit /b 1
:: )
:: java -jar bk2010.jar -bk0010 -multicolor on -bin "%a:~0,-4%.bin"
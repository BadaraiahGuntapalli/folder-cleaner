@echo off
:: %~dp0 = this script's folder (scripts\), go one level up to project root
set "ROOT=%~dp0.."
python "%ROOT%\main.py" --folder "%USERPROFILE%\Downloads" %*

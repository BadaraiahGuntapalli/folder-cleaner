@echo off
:: %~dp0 = the folder this .bat file lives in (dynamic, works for any user)
:: %USERPROFILE% = current user's home directory (e.g. C:\Users\YourName)
python "%~dp0cleaner.py" --folder "%USERPROFILE%\Downloads" %*

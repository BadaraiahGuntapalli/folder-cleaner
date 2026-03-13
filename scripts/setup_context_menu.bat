@echo off
:: %~dp0 = this script's folder (scripts\), go one level up to project root
set "ROOT=%~dp0.."
set "LAUNCHER=%ROOT%\cleaner\launcher.py"

echo Setting up right-click context menu...
echo Launcher path: %LAUNCHER%
echo.

:: Right-click ON a folder
reg add "HKCR\Directory\shell\CleanerTool"          /ve /d "Clean with Cleaner"                               /f
reg add "HKCR\Directory\shell\CleanerTool"          /v "Icon" /d "shell32.dll,31"                             /f
reg add "HKCR\Directory\shell\CleanerTool\command"  /ve /d "cmd /k python \"%LAUNCHER%\" \"%%1\""             /f

:: Right-click INSIDE a folder (background)
reg add "HKCR\Directory\Background\shell\CleanerTool"          /ve /d "Clean with Cleaner"                    /f
reg add "HKCR\Directory\Background\shell\CleanerTool"          /v "Icon" /d "shell32.dll,31"                   /f
reg add "HKCR\Directory\Background\shell\CleanerTool\command"  /ve /d "cmd /k python \"%LAUNCHER%\" \"%%V\""  /f

echo.
echo Done! Right-click any folder and you will see "Clean with Cleaner".
echo.
pause

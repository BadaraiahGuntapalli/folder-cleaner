@echo off
echo Removing right-click context menu...

reg delete "HKCR\Directory\shell\CleanerTool" /f
reg delete "HKCR\Directory\Background\shell\CleanerTool" /f

echo.
echo Done! Context menu removed.
echo.
pause

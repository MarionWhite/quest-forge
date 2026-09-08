@echo off
rem Re-copy Quest Forge perf overlays if a running session overwrote them on quit.
set "INST=C:\Users\a2dsu\AppData\Roaming\.crazycraft4"
set "SRC=%~dp0overlay"
copy /Y "%SRC%\optionsof.txt" "%INST%\optionsof.txt"
copy /Y "%SRC%\journeymap.core.config" "%INST%\journeymap\config\5.1\journeymap.core.config"
copy /Y "%SRC%\lycanitesmobs-spawning.cfg" "%INST%\config\lycanitesmobs\lycanitesmobs-spawning.cfg"
copy /Y "%SRC%\TEST-LAUNCH.bat" "%INST%\TEST-LAUNCH.bat"
echo Reapplied. Fully quit Minecraft, then use the Quest Forge shortcut (TEST-LAUNCH.bat).
pause

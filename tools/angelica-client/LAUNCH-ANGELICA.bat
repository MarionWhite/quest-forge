@echo off
setlocal enabledelayedexpansion
title Quest Forge - Angelica

rem Quest Forge launcher for the Angelica client (Forge 10.13.4.1614, Java 8).
rem build_angelica_client.py puts this file in the game folder it builds,
rem next to bin\, mods\ and options.txt. Double-click it.
rem
rem OFFLINE ONLY, like TEST-LAUNCH.bat: singleplayer and LAN work, the friends'
rem server (online mode) does not. To play there, use Prism Launcher with
rem Forge 1614 and the same mods (docs/setup/angelica-client.md).
rem
rem Heap from installed RAM: 8 GB -> 3 GB, 12 GB -> 4 GB, 16 GB -> 5 GB,
rem 32 GB or more -> 7 GB. set QF_XMX=6144M before launching to override.
rem QF_USER sets the player name (default Dev). QF_JVM_ARGS / QF_GAME_ARGS add arguments,
rem e.g. QF_GAME_ARGS=--server 1.2.3.4 --port 25565 to connect straight away.

cd /d "%~dp0" || (echo Could not change to "%~dp0" & pause & exit /b 1)
set "INST=%CD%"

set "JAVA="
if exist "C:\Program Files\Java\jre1.8.0_241\bin\java.exe" set "JAVA=C:\Program Files\Java\jre1.8.0_241\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Java\jre1.8*") do if exist "%%~D\bin\java.exe" set "JAVA=%%~D\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Java\jdk1.8*") do if exist "%%~D\jre\bin\java.exe" set "JAVA=%%~D\jre\bin\java.exe"
if not defined JAVA for /d %%D in ("C:\Program Files\Eclipse Adoptium\jre-8*" "C:\Program Files\Eclipse Adoptium\jdk-8*") do if exist "%%~D\bin\java.exe" set "JAVA=%%~D\bin\java.exe"
if not defined JAVA (
  echo Java 8 64-bit not found. Install Java 8 ^(e.g. Temurin 8 x64^) and try again.
  pause & exit /b 1
)
for %%F in (bin\minecraft.jar bin\natives bin\lib\forge-1.7.10-10.13.4.1614-1.7.10-universal.jar mods\angelica-2.2.33.jar) do (
  if not exist "%%F" (echo Missing "%INST%\%%F" -- is this the Quest Forge Angelica folder? & pause & exit /b 1)
)
if exist "bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar" (
  echo bin\lib holds the 1558 Forge jar as well as 1614. Angelica needs 1614 only:
  echo move forge-1.7.10-10.13.4.1558-1.7.10-universal.jar out of bin\lib.
  pause & exit /b 1
)
if exist "mods\OptiFine_1.7.10_HD_U_E7.jar" (
  echo OptiFine is in mods\. It cannot run with Angelica; rebuild with build_angelica_client.py.
  pause & exit /b 1
)

set "RAMGB=16"
for /f %%m in ('powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)"') do set "RAMGB=%%m"
set "XMX=3072M" & set "XMS=1024M"
if !RAMGB! GEQ 11 set "XMX=4096M"
if !RAMGB! GEQ 15 (set "XMX=5120M" & set "XMS=2048M")
if !RAMGB! GEQ 30 set "XMX=7168M"
if defined QF_XMX set "XMX=%QF_XMX%"
if not defined QF_USER set "QF_USER=Dev"

set "CP=bin\minecraft.jar"
for %%f in (bin\lib\*.jar) do set "CP=!CP!;bin\lib\%%~nxf"
set "LOG4J="
if exist "log4j2_17-111.xml" set "LOG4J=-Dlog4j.configurationFile=log4j2_17-111.xml"

echo Instance: %INST%
echo Java:     %JAVA%
echo Heap:     %XMX%  (RAM %RAMGB% GB; set QF_XMX to override)
echo Starting Quest Forge (Angelica)...
echo.

"%JAVA%" ^
 -Djava.net.preferIPv4Stack=true ^
 -Dfml.ignoreInvalidMinecraftCertificates=true ^
 -Dfml.ignorePatchDiscrepancies=true ^
 -Dlog4j2.formatMsgNoLookups=true %LOG4J% ^
 -Djava.library.path="%INST%\bin\natives" ^
 -Xms%XMS% -Xmx%XMX% -XX:MaxPermSize=256M ^
 -XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M ^
 -XX:+ParallelRefProcEnabled -XX:+DisableExplicitGC -XX:+UseCompressedOops ^
 -XX:+UseSplitVerifier -XX:+FailOverToOldVerifier -XX:-HeapDumpOnOutOfMemoryError %QF_JVM_ARGS% ^
 -cp "!CP!" ^
 net.minecraft.launchwrapper.Launch ^
 --username %QF_USER% --accessToken 0 ^
 --uuid 00000000-0000-0000-0000-000000000000 ^
 --version 1.7.10 --assetIndex 1.7.10 ^
 --tweakClass cpw.mods.fml.common.launcher.FMLTweaker ^
 --gameDir "%INST%" --assetsDir "%INST%\assets" ^
 --userProperties {} %QF_GAME_ARGS%

echo.
echo ---- Minecraft exited with code %ERRORLEVEL% ----
pause

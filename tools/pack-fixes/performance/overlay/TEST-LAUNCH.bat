@echo off
setlocal enabledelayedexpansion
title Quest Forge - CrazyCraft 4

rem Direct launch: no VoidLauncher (it would re-sync and overwrite mods/config).
rem Offline credentials: singleplayer works; online servers do not.
rem cd to this script's folder so Desktop shortcuts and Explorer always work.

cd /d "%~dp0" || (
  echo ERROR: Could not change directory to the script folder.
  echo Path: "%~dp0"
  pause
  exit /b 1
)
set "INST=%CD%"

set "JAVA="
if exist "C:\Program Files\Java\jre1.8.0_241\bin\java.exe" set "JAVA=C:\Program Files\Java\jre1.8.0_241\bin\java.exe"
if not defined JAVA (
  for /d %%D in ("C:\Program Files\Java\jre1.8*") do if exist "%%~D\bin\java.exe" set "JAVA=%%~D\bin\java.exe"
)
if not defined JAVA (
  for /d %%D in ("C:\Program Files\Java\jdk1.8*") do if exist "%%~D\jre\bin\java.exe" set "JAVA=%%~D\jre\bin\java.exe"
)
if not defined JAVA (
  echo Java 8 not found. Looked for:
  echo   C:\Program Files\Java\jre1.8.0_241\bin\java.exe
  pause
  exit /b 1
)

if not exist "bin\minecraft.jar" (
  echo ERROR: Missing "%INST%\bin\minecraft.jar"
  pause
  exit /b 1
)
if not exist "bin\natives" (
  echo ERROR: Missing "%INST%\bin\natives"
  pause
  exit /b 1
)
if not exist "bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar" (
  echo ERROR: Missing Forge jar in bin\lib
  pause
  exit /b 1
)

echo.
echo Instance: %INST%
echo Java:     %JAVA%
echo Starting Quest Forge...
echo.

set "CP=bin\minecraft.jar"
for %%f in (bin\lib\*.jar) do set "CP=!CP!;bin\lib\%%~nxf"

rem JVM: G1 + modest Xms for shorter pauses than ParallelGC with 12 threads.
rem Heap stays 7G (31G RAM; 1.7.10 suffers if Xmx is pushed much past 8G).

"%JAVA%" ^
 -Djava.net.preferIPv4Stack=true ^
 -Dfml.ignoreInvalidMinecraftCertificates=true ^
 -Dfml.ignorePatchDiscrepancies=true ^
 -Dlog4j2.formatMsgNoLookups=true ^
 -Dlog4j.configurationFile=log4j2_17-111.xml ^
 -Djava.library.path="%INST%\bin\natives" ^
 -Xms2048M -Xmx7168M -XX:MaxPermSize=256M ^
 -XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=16M ^
 -XX:ParallelGCThreads=6 -XX:ConcGCThreads=2 ^
 -XX:+UseSplitVerifier -XX:+FailOverToOldVerifier ^
 -XX:-HeapDumpOnOutOfMemoryError -XX:+UseCompressedOops ^
 -XX:+DisableExplicitGC ^
 -cp "!CP!" ^
 net.minecraft.launchwrapper.Launch ^
 --username Dev --accessToken 0 ^
 --uuid 00000000-0000-0000-0000-000000000000 ^
 --version 1.7.10 --assetIndex 1.7.10 ^
 --tweakClass cpw.mods.fml.common.launcher.FMLTweaker ^
 --gameDir "%INST%" --assetsDir "%INST%\assets" ^
 --userProperties {}

echo.
echo ---- Minecraft exited with code %ERRORLEVEL% ----
pause
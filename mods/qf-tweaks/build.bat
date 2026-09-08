@echo off
setlocal enabledelayedexpansion
title Build QuestForgeTweaks coremod

rem ---------------------------------------------------------------------------
rem Builds QuestForgeTweaks-1.0.jar and installs it into the CrazyCraft 4
rem instance's mods folder.
rem
rem REQUIRES A JDK. The instance's C:\Program Files\Java\jre1.8.0_241 is a
rem runtime only and has no javac. Install a JDK 8 (Adoptium Temurin 8 is the
rem usual choice) and either set JAVA_HOME or edit JDK below.
rem ---------------------------------------------------------------------------

set "INST=%APPDATA%\.crazycraft4"
set "HERE=%~dp0"

rem --- locate a JDK -----------------------------------------------------------
set "JDK="
if defined JAVA_HOME if exist "%JAVA_HOME%\bin\javac.exe" set "JDK=%JAVA_HOME%"
if not defined JDK for %%d in (
  "C:\Program Files\Eclipse Adoptium\jdk-8*"
  "C:\Program Files\Java\jdk1.8*"
  "C:\Program Files\Amazon Corretto\jdk1.8*"
) do if exist "%%~d\bin\javac.exe" set "JDK=%%~d"

if not defined JDK (
  echo.
  echo   ERROR: no JDK found. Install a JDK 8 or set JAVA_HOME, then re-run.
  echo   javac is required; a JRE is not enough.
  echo.
  pause
  exit /b 1
)
echo Using JDK: %JDK%

rem --- classpath: everything we compile against is already in the instance ----
set "CP=%INST%\bin\lib\forge-1.7.10-10.13.4.1558-1.7.10-universal.jar"
set "CP=%CP%;%INST%\bin\lib\launchwrapper-1.11.jar"
set "CP=%CP%;%INST%\bin\lib\asm-all-5.0.3.jar"
set "CP=%CP%;%INST%\bin\lib\log4j-api-2.0-beta9.jar"
set "CP=%CP%;%INST%\bin\minecraft.jar"

if exist "%HERE%build" rd /s /q "%HERE%build"
mkdir "%HERE%build"

rem --- compile ----------------------------------------------------------------
rem Target 1.7 bytecode. TEST-LAUNCH.bat passes -XX:+UseSplitVerifier and
rem -XX:+FailOverToOldVerifier, so older-version bytecode is fine here.
"%JDK%\bin\javac.exe" -source 1.7 -target 1.7 -nowarn ^
  -bootclasspath "%JDK%\jre\lib\rt.jar" ^
  -cp "%CP%" ^
  -d "%HERE%build" ^
  "%HERE%src\com\questforge\QuestForgeCore.java" ^
  "%HERE%src\com\questforge\PanelButtonQuestTransformer.java" ^
  "%HERE%src\com\questforge\MusicTickerTransformer.java"

if errorlevel 1 (
  echo.
  echo   COMPILE FAILED.
  pause
  exit /b 1
)

rem --- package ----------------------------------------------------------------
"%JDK%\bin\jar.exe" cfm "%HERE%QuestForgeTweaks-1.0.jar" "%HERE%manifest.txt" -C "%HERE%build" .
if errorlevel 1 (
  echo   JAR FAILED.
  pause
  exit /b 1
)

echo.
echo   Built "%HERE%QuestForgeTweaks-1.0.jar"
echo.

rem --- verify the manifest actually points at a class that exists -------------
rem (ColorfulMobsMC.jar in this pack shipped a stale FMLCorePlugin line for a
rem  class it did not contain, which produced a ClassNotFoundException at
rem  startup. Check rather than assume.)
"%JDK%\bin\jar.exe" tf "%HERE%QuestForgeTweaks-1.0.jar" | findstr /c:"com/questforge/QuestForgeCore.class" >nul
if errorlevel 1 (
  echo   ERROR: QuestForgeCore.class missing from jar - manifest would dangle.
  pause
  exit /b 1
)
echo   Verified: com/questforge/QuestForgeCore.class present.

rem --- install ----------------------------------------------------------------
copy /Y "%HERE%QuestForgeTweaks-1.0.jar" "%INST%\mods\QuestForgeTweaks-1.0.jar" >nul
if errorlevel 1 (
  echo   INSTALL FAILED.
  pause
  exit /b 1
)
echo   Installed to "%INST%\mods\QuestForgeTweaks-1.0.jar"
echo.
echo   Done. Launch with TEST-LAUNCH.bat and grep logs\latest.log for:
echo     [QuestForgeTweaks] Transform applied
echo.
pause

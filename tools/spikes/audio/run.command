#!/bin/zsh
# Spike A: positional audio from raw PCM, using the exact sound stack MC 1.7.10 ships.
# Runs on arm64 Zulu 8 with the arm64 LWJGL natives RFG already extracted into run/.
set -e
cd "$(dirname "$0")"

JAVA_HOME=/Library/Java/JavaVirtualMachines/zulu-8.jdk/Contents/Home
GC="$HOME/.gradle/caches/modules-2/files-2.1"
INST="$HOME/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/bin/lib"
NATIVES="$HOME/Desktop/QuestForge-Mods/run/natives/lwjgl2"

SS=$(find "$GC/com.paulscode/soundsystem"     -name "*.jar" | head -1)
OAL=$(find "$INST" -iname "librarylwjglopenal*.jar" | head -1)
LWJGL=$(find "$GC/org.lwjgl.lwjgl/lwjgl" -name "lwjgl-2.9.4*.jar" ! -name "*sources*" | head -1)

CP="$SS:$OAL:$LWJGL:."
echo "classpath:"
for j in "$SS" "$OAL" "$LWJGL"; do echo "  $(basename "$j")"; done
echo

MAIN="${1:-AudioDiag}"
"$JAVA_HOME/bin/javac" -classpath "$CP" -nowarn "$MAIN.java"
"$JAVA_HOME/bin/java" -classpath "$CP" -Dorg.lwjgl.librarypath="$NATIVES" "$MAIN"

#!/bin/bash
# ---------------------------------------------------------------------------
# Builds QuestForge Content and installs it into the Prism "Quest Forge"
# instance. The Mac replacement for the pack's Windows-only build.bat.
#
# Double-click in Finder, or run from a terminal.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

INSTANCE="$HOME/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft"
MODS="$INSTANCE/mods"

if [ ! -d "$MODS" ]; then
  echo "ERROR: Prism instance not found at:"
  echo "  $MODS"
  echo "Is the instance still named 'Quest Forge'?"
  exit 1
fi

echo "==> Building..."
./gradlew build

# The reobfuscated jar is the one that runs in a real instance.
# -dev / -sources / -javadoc jars are for development only.
JAR=$(ls -t build/libs/*.jar 2>/dev/null \
      | grep -v -- '-dev\.jar$' \
      | grep -v -- '-sources\.jar$' \
      | grep -v -- '-javadoc\.jar$' \
      | head -1 || true)

if [ -z "$JAR" ]; then
  echo "ERROR: no output jar found in build/libs/"
  exit 1
fi

BASE=$(basename "$JAR")
echo "==> Built $BASE"

# Keep one backup of whatever was there before.
if [ -f "$MODS/$BASE" ]; then
  mkdir -p "$MODS/../_qf-backups"
  cp "$MODS/$BASE" "$MODS/../_qf-backups/$BASE.bak-$(date +%Y%m%d-%H%M%S)"
  echo "==> Backed up the previous copy"
fi

cp "$JAR" "$MODS/$BASE"
echo "==> Installed to: $MODS/$BASE"
echo
echo "Launch Quest Forge in Prism to test it."

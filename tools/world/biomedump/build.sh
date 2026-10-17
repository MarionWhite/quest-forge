#!/bin/sh
# Build the trial-only biome-dump probe and stage it for trial.py (catalog key "biomedump").
#   sh tools/world/biomedump/build.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
JDK="/c/Program Files/Eclipse Adoptium/jdk-8.0.504.1-hotspot/bin"
FORGE=/c/qfs/forge1614-install/forge-1.7.10-10.13.4.1614-1.7.10-universal.jar
OUT=$(mktemp -d)
"$JDK/javac" -source 1.8 -target 1.8 -cp "$FORGE" -d "$OUT" "$HERE/src/qfbiomedump/BiomeDump.java"
"$JDK/jar" cf "$OUT/qf-biomedump.jar" -C "$OUT" qfbiomedump
py -3.10 "$HERE/../../trial/trial.py" stage "$OUT/qf-biomedump.jar"
rm -rf "$OUT"

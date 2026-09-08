#!/bin/bash
# Drives the dev dedicated server through a census run, headlessly.
#
# The dev server has no pack mods in it, which is the point: it is a control.
# Vanilla entity values are known, so a census run here either reproduces them or
# proves the harness is broken -- and it is much cheaper to find that out here
# than after loading 115 mods.
set -u
cd "$(dirname "$0")/../.." || exit 1

OUT="${1:-/tmp/qf-census-dev.log}"

{
  sleep 100          # FML startup + world generation
  echo "qfcensus calibrate"
  sleep 8
  echo "qfcensus gear"
  sleep 45
  echo "qfcensus mobs"
  sleep 180
  echo "qfcensus status"
  sleep 5
  echo "stop"
  sleep 20
} | ./gradlew runServer --console=plain > "$OUT" 2>&1

echo "exit=$? log=$OUT"

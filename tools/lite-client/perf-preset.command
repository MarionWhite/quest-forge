#!/bin/zsh
# Quest Forge performance preset switcher.
# Usage:  double-click and pick, or:  ./perf-preset.command [low|balanced|quality|show]
#
#   quality  = Sildur Vibrant High, full detail. Best looking, heaviest. (the pack's original look)
#   balanced = Sildur Enhanced Default + half-res shadows, RD7, fewer particles. Shaded but ~2x faster on this Mac. (default)
#   low      = shaders OFF + OptiFine Fast Render, Fast graphics, RD6, minimal everything. For weak PCs / if the Mac still lags.
#
# Only performance/visual keys are edited in place; keybinds, resource pack, quests etc. are untouched.
# A backup of the three settings files is written next to this script the first time you switch.
set -u
MC="$(cd "$(dirname "$0")" && pwd)/minecraft"
[[ -f "$MC/options.txt" ]] || { echo "Cannot find $MC/options.txt"; exit 1; }

PRESET="${1:-}"
if [[ -z "$PRESET" ]]; then
  echo "Quest Forge performance preset"
  echo "  1) low       (weak PCs / max FPS, no shaders)"
  echo "  2) balanced  (recommended for this Mac — shaded, ~2x faster)"
  echo "  3) quality   (original Vibrant High look, heaviest)"
  echo "  s) show current"
  echo -n "Choose [1/2/3/s]: "
  read -k 1 ans; echo
  case "$ans" in
    1) PRESET=low;; 2) PRESET=balanced;; 3) PRESET=quality;; s|S) PRESET=show;;
    *) echo "No change."; exit 0;;
  esac
fi

setkey() { # file key sep value
  local f="$1" k="$2" s="$3" v="$4"
  if grep -qE "^${k}${s}" "$f"; then
    /usr/bin/sed -i '' -E "s|^(${k}${s}).*|\1${v}|" "$f"
  else
    printf '%s%s%s\n' "$k" "$s" "$v" >> "$f"
  fi
}

O="$MC/options.txt"; OF="$MC/optionsof.txt"; SH="$MC/optionsshaders.txt"

if [[ "$PRESET" == show ]]; then
  echo "options.txt :"; grep -E "^(renderDistance|particles|fancyGraphics|maxFps|clouds|mipmapLevels|ao):" "$O"
  echo "optionsof.txt :"; grep -E "^(ofRenderDistanceChunks|ofFastRender|ofClouds|ofTrees|ofDroppedItems|ofRain|ofDynamicLights|ofAnimatedWater|ofAnimatedLava|ofBetterGrass|ofConnectedTextures|ofAoLevel):" "$OF"
  echo "optionsshaders.txt :"; grep -E "shaderPack|shadowResMul|renderResMul" "$SH"
  exit 0
fi

BK="$(dirname "$0")/_perf-preset-firstrun-backup"
if [[ ! -d "$BK" ]]; then mkdir -p "$BK"; cp "$O" "$OF" "$SH" "$BK/"; echo "First-run backup saved to $BK"; fi

case "$PRESET" in
  quality)
    setkey "$O" renderDistance ":" 8;  setkey "$O" particles ":" 0; setkey "$O" fancyGraphics ":" true
    setkey "$O" maxFps ":" 120; setkey "$O" clouds ":" true; setkey "$O" mipmapLevels ":" 4; setkey "$O" ao ":" 2
    setkey "$OF" ofRenderDistanceChunks ":" 8; setkey "$OF" ofFastRender ":" false; setkey "$OF" ofClouds ":" 0
    setkey "$OF" ofTrees ":" 2; setkey "$OF" ofDroppedItems ":" 0; setkey "$OF" ofRain ":" 0; setkey "$OF" ofDynamicLights ":" 1
    setkey "$OF" ofAnimatedWater ":" 1; setkey "$OF" ofAnimatedLava ":" 1; setkey "$OF" ofBetterGrass ":" 3
    setkey "$OF" ofConnectedTextures ":" 1; setkey "$OF" ofAoLevel ":" 1.0
    setkey "$SH" shaderPack "=" "Sildur's Vibrant Shaders v2.01 High.zip"; setkey "$SH" shadowResMul "=" 1.0; setkey "$SH" renderResMul "=" 1.0
    ;;
  balanced)
    setkey "$O" renderDistance ":" 7;  setkey "$O" particles ":" 1; setkey "$O" fancyGraphics ":" true
    setkey "$O" maxFps ":" 90; setkey "$O" clouds ":" true; setkey "$O" mipmapLevels ":" 2; setkey "$O" ao ":" 2
    setkey "$OF" ofRenderDistanceChunks ":" 7; setkey "$OF" ofFastRender ":" false; setkey "$OF" ofClouds ":" 1
    setkey "$OF" ofTrees ":" 2; setkey "$OF" ofDroppedItems ":" 1; setkey "$OF" ofRain ":" 1; setkey "$OF" ofDynamicLights ":" 1
    setkey "$OF" ofAnimatedWater ":" 1; setkey "$OF" ofAnimatedLava ":" 1; setkey "$OF" ofBetterGrass ":" 2
    setkey "$OF" ofConnectedTextures ":" 1; setkey "$OF" ofAoLevel ":" 1.0
    setkey "$SH" shaderPack "=" "Sildur's Enhanced Default v1.19 Fancy.zip"; setkey "$SH" shadowResMul "=" 0.5; setkey "$SH" renderResMul "=" 1.0
    ;;
  low)
    setkey "$O" renderDistance ":" 6;  setkey "$O" particles ":" 2; setkey "$O" fancyGraphics ":" false
    setkey "$O" maxFps ":" 60; setkey "$O" clouds ":" false; setkey "$O" mipmapLevels ":" 0; setkey "$O" ao ":" 1
    setkey "$OF" ofRenderDistanceChunks ":" 6; setkey "$OF" ofFastRender ":" true; setkey "$OF" ofClouds ":" 3
    setkey "$OF" ofTrees ":" 1; setkey "$OF" ofDroppedItems ":" 1; setkey "$OF" ofRain ":" 1; setkey "$OF" ofDynamicLights ":" 3
    setkey "$OF" ofAnimatedWater ":" 2; setkey "$OF" ofAnimatedLava ":" 2; setkey "$OF" ofBetterGrass ":" 1
    setkey "$OF" ofConnectedTextures ":" 0; setkey "$OF" ofAoLevel ":" 0.0
    setkey "$SH" shaderPack "=" "(internal)"; setkey "$SH" shadowResMul "=" 1.0; setkey "$SH" renderResMul "=" 1.0
    ;;
  *) echo "Unknown preset: $PRESET"; exit 1;;
esac

echo "Applied '$PRESET'. Restart Quest Forge (or from the title screen: Options > Video reload) for it to take effect."
echo "Note: 'low' turns shaders OFF and Fast Render ON; 'balanced'/'quality' turn shaders ON and Fast Render OFF."

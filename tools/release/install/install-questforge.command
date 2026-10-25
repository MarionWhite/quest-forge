#!/bin/bash
# Quest Forge installer for macOS (Prism Launcher). Double-click it, or run it in Terminal:
#   ./install-questforge.command            install or update the OptiFine edition
#   ./install-questforge.command --dry-run  show what would happen, change nothing
#   ./install-questforge.command --help     every option
#
# It finds Prism's folder and an Intel (x86_64) Java 8, picks the memory for this Mac, downloads
# the newest "client instance" release from GitHub (or uses a zip you pass with --zip), checks every
# file against the release's SHA1SUMS.txt, and installs it as "Quest Forge" in Prism's instances folder.
# An update keeps your saves, screenshots, options, servers.dat, JourneyMap data and your own
# resource and shader packs. Mods and config are replaced; the old copies go to _qf-backups/<time>.
#
# Bash 3.2 compatible (the Mac default). Needs only what macOS ships: curl, unzip, shasum, awk,
# osascript, ps, sysctl.
#
# Hooks for tests (tools/release/tests): --prism-dir, --instances-dir, --java, --ram-gb,
# --releases-json, --no-prompt, --skip-process-check. Ordinary use needs none of them.

REPO="MarionWhite/quest-forge"
EDITION="optifine"
INSTANCE_NAME=""
ZIP=""
PRISM_DIR=""
INSTANCES_DIR=""
JAVA=""
RAM_GB=""
PROFILE=""
DRY=0
NOPROMPT=0
SKIP_PROC=0
RELEASES_JSON=""

# Keys the release decides in instance.cfg; the rest (UI layout, play time, uuid) stays.
RELEASE_CFG_KEYS="ConfigVersion InstanceType JvmArgs OverrideJavaArgs OverrideMemory PermGen iconKey notes"
REPLACE_DIRS="mods config scripts resources assets fonts"
REPLACE_FILES="log4j2_17-111.xml questforge.ico pack.png tf-tutorials.txt"
ROOT_ITEMS="mmc-pack.json patches libraries questforge-tools perf-preset.command questforge-release.json SHA1SUMS.txt icon.png"

usage() {
  cat <<'EOF'
Quest Forge installer (macOS)

  ./install-questforge.command [options]

  --edition optifine|angelica   which edition (default optifine)
  --instance-name NAME          folder and display name in Prism (default: Quest Forge, or Quest Forge Angelica)
  --zip FILE                    install this zip instead of downloading (its .sha1 must be next to it)
  --profile keep|none|lite|potato
                                lite or potato: apply the Mac preset (perf-preset.command low).
                                keep (updates): keep the instance's own profile. Default: ask, or keep / none.
  --dry-run, -n                 show the plan and change nothing
  --prism-dir DIR               Prism's data folder (default ~/Library/Application Support/PrismLauncher)
  --instances-dir DIR           Prism's instances folder (default: from prismlauncher.cfg, else <data>/instances)
  --java PATH                   a Java 8 (x86_64) to use instead of the one found
  --ram-gb N                    the RAM to plan for (default: read from this Mac)
  --help, -h                    this text
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --edition) EDITION="$2"; shift 2 ;;
    --instance-name) INSTANCE_NAME="$2"; shift 2 ;;
    --zip) ZIP="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --dry-run|-n) DRY=1; shift ;;
    --prism-dir) PRISM_DIR="$2"; shift 2 ;;
    --instances-dir) INSTANCES_DIR="$2"; shift 2 ;;
    --java) JAVA="$2"; shift 2 ;;
    --ram-gb) RAM_GB="$2"; shift 2 ;;
    --releases-json) RELEASES_JSON="$2"; shift 2 ;;
    --no-prompt) NOPROMPT=1; shift ;;
    --skip-process-check) SKIP_PROC=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
done

case "$EDITION" in optifine|angelica) ;; *) echo "--edition must be optifine or angelica"; exit 2 ;; esac
case "$PROFILE" in ""|keep|none|lite|potato) ;; *) echo "--profile must be keep, none, lite or potato"; exit 2 ;; esac
if [ -z "$INSTANCE_NAME" ]; then
  if [ "$EDITION" = angelica ]; then INSTANCE_NAME="Quest Forge Angelica"; else INSTANCE_NAME="Quest Forge"; fi
fi
INTERACTIVE=0
if [ "$NOPROMPT" -eq 0 ] && [ -t 0 ]; then INTERACTIVE=1; fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/qf-install.XXXXXX")" || exit 1
trap 'rm -rf "$WORK"' EXIT

say() { printf '%s\n' "$*"; }
section() { printf '\n%s\n' "$*"; }
stop() {
  printf '\nSTOPPED: %s\n' "$*"
  printf 'Fix the problem above and run the installer again. A re-run does not touch your saves.\n'
  if [ "$INTERACTIVE" -eq 1 ]; then printf '\nPress Return to close. '; read -r _; fi
  exit 1
}
end_pause() {
  if [ "$INTERACTIVE" -eq 1 ]; then printf '\nPress Return to close. '; read -r _; fi
}

# ---- Prism's folders -------------------------------------------------------
[ -n "$PRISM_DIR" ] || PRISM_DIR="$HOME/Library/Application Support/PrismLauncher"
[ -d "$PRISM_DIR" ] || stop "Prism Launcher's folder was not found ($PRISM_DIR). Open Prism Launcher once, then run this again."
if [ -z "$INSTANCES_DIR" ]; then
  INSTANCES_DIR="$PRISM_DIR/instances"
  if [ -f "$PRISM_DIR/prismlauncher.cfg" ]; then
    v="$(grep -m1 '^InstanceDir=' "$PRISM_DIR/prismlauncher.cfg" | cut -d= -f2- | tr -d '"')"
    if [ -n "$v" ]; then
      case "$v" in /*) INSTANCES_DIR="$v" ;; *) INSTANCES_DIR="$PRISM_DIR/$v" ;; esac
    fi
  fi
fi
say "Prism folder:      $PRISM_DIR"
say "Instances folder:  $INSTANCES_DIR"

# ---- Java 8, Intel build ----------------------------------------------------
# Prints the version and os.arch of a java, or nothing if it is not one.
java_facts() {
  "$1" -XshowSettings:properties -version 2>&1 | awk -F' = ' '
    /^ *java.version = / { gsub(/ /, "", $2); v = $2 }
    /^ *os.arch = /      { gsub(/ /, "", $2); a = $2 }
    END { if (v != "") print v " " a }'
}
find_java() {
  local c facts v a
  if [ -n "$JAVA" ]; then candidates="$JAVA"; else
    candidates="$(/usr/libexec/java_home -v 1.8 2>/dev/null)"
    candidates="$candidates
$(ls -d /Library/Java/JavaVirtualMachines/*/Contents/Home 2>/dev/null)
$(ls -d "$HOME"/Library/Java/JavaVirtualMachines/*/Contents/Home 2>/dev/null)"
  fi
  printf '%s\n' "$candidates" | while IFS= read -r c; do
    [ -n "$c" ] || continue
    case "$c" in *.jdk|*/Home) [ -x "$c/bin/java" ] && c="$c/bin/java" ;; esac
    [ -x "$c" ] || continue
    facts="$(java_facts "$c")"
    v="${facts%% *}"; a="${facts#* }"
    case "$v" in 1.8.*) ;; *) continue ;; esac
    case "$a" in x86_64|amd64) echo "$c"; return 0 ;; esac
  done
  return 1
}
JAVA_FOUND="$(find_java)"
if [ -z "$JAVA_FOUND" ]; then
  stop "Java 8, Intel (x86_64) was not found. Install Temurin 8 for macOS x64 (the .pkg whose name contains x64, from adoptium.net), and run Rosetta with: softwareupdate --install-rosetta --agree-to-license . Then run this again."
fi
JAVA="$JAVA_FOUND"
JAVA_FACTS="$(java_facts "$JAVA")"
JAVA_VER="${JAVA_FACTS%% *}"
say "Java 8 (x86_64):   $JAVA  ($JAVA_VER)"
case "$JAVA_VER" in
  1.8.0_*)
    upd="${JAVA_VER#1.8.0_}"
    if [ "$upd" -ge 242 ] 2>/dev/null; then
      say "  Note: Java 8u$upd can crash LWJGL 2 on modern macOS. Temurin 8u$upd or 8u162 is safer."
    fi ;;
esac

# ---- Memory ------------------------------------------------------------------
if [ -z "$RAM_GB" ]; then
  bytes="$(sysctl -n hw.memsize 2>/dev/null)"
  if [ -n "$bytes" ]; then RAM_GB=$(( (bytes + 536870912) / 1073741824 )); else RAM_GB=8; fi
fi
if [ "$RAM_GB" -lt 12 ] 2>/dev/null; then MIN_MB=1024; MAX_MB=4096; MROW="8 GB"; else MIN_MB=2048; MAX_MB=6144; MROW="12 GB or more"; fi
say "Installed RAM:     ${RAM_GB} GB  (heap ${MIN_MB} to ${MAX_MB} MiB, the $MROW row)"

# ---- The release -------------------------------------------------------------
# Picks the newest release named "client instance" with a zip for this edition.
# Prints "OK<TAB>release<TAB>zipname<TAB>zipurl<TAB>shaurl", or NONE, or ERROR<TAB>message.
cat > "$WORK/select.js" <<'JXA'
function run(argv) {
  ObjC.import('Foundation');
  var text = $.NSString.stringWithContentsOfFileEncodingError(argv[0], 4, null).js;
  var releases = JSON.parse(text);
  var re = new RegExp(argv[1], 'i');
  for (var i = 0; i < releases.length; i++) {
    var r = releases[i];
    if (r.draft || !r.name || !/client instance/i.test(r.name)) continue;
    var assets = r.assets || [];
    var zip = null;
    for (var j = 0; j < assets.length; j++) {
      if (re.test(assets[j].name) && /\.zip$/.test(assets[j].name)) { zip = assets[j]; break; }
    }
    if (!zip) continue;
    var sha = null;
    for (var k = 0; k < assets.length; k++) {
      if (assets[k].name === zip.name + '.sha1') { sha = assets[k]; break; }
    }
    if (!sha) return 'ERROR\tRelease ' + r.name + ' has ' + zip.name + ' but no ' + zip.name + '.sha1';
    return ['OK', r.name, zip.name, zip.browser_download_url, sha.browser_download_url].join('\t');
  }
  return 'NONE';
}
JXA

if [ -z "$ZIP" ]; then
  section "Looking for the newest release on GitHub..."
  if [ -n "$RELEASES_JSON" ]; then
    cp "$RELEASES_JSON" "$WORK/releases.json" || stop "Could not read $RELEASES_JSON."
  else
    curl -fsSL -H 'Accept: application/vnd.github+json' -H 'User-Agent: QuestForge-installer' \
      -o "$WORK/releases.json" "https://api.github.com/repos/$REPO/releases?per_page=30" \
      || stop "Could not reach GitHub to find the release. Check the internet connection, or download the zip and its .sha1 and run with --zip FILE."
  fi
  sel="$(osascript -l JavaScript "$WORK/select.js" "$WORK/releases.json" "$EDITION" 2>/dev/null)" \
    || stop "Could not read the release list."
  case "$sel" in
    NONE) stop "No release named 'client instance' has a $EDITION download yet. Ask the host." ;;
    ERROR*) stop "$(printf '%s' "$sel" | cut -f2). Ask the host to upload it." ;;
  esac
  REL_NAME="$(printf '%s' "$sel" | cut -f2)"
  ZIP_NAME="$(printf '%s' "$sel" | cut -f3)"
  ZIP_URL="$(printf '%s' "$sel" | cut -f4)"
  SHA_URL="$(printf '%s' "$sel" | cut -f5)"
  say "Release:           $REL_NAME"
  say "Downloading        $ZIP_NAME"
  ZIP="$WORK/$ZIP_NAME"
  curl -fL --retry 3 -o "$ZIP" "$ZIP_URL" || stop "The download of $ZIP_NAME failed. Try again."
  curl -fL --retry 3 -o "$ZIP.sha1" "$SHA_URL" || stop "The download of the checksum failed. Try again."
else
  [ -f "$ZIP" ] || stop "The zip '$ZIP' does not exist."
  [ -f "$ZIP.sha1" ] || stop "No $(basename "$ZIP").sha1 next to the zip. Download it along with the zip."
fi
WANT="$(awk '{print tolower($1); exit}' "$ZIP.sha1")"
GOT="$(shasum -a 1 "$ZIP" | awk '{print tolower($1)}')"
[ "$GOT" = "$WANT" ] || stop "The download is damaged (its checksum does not match). Run the installer again."
say "Download checksum: ok"

UNPACK="$WORK/unpacked"
mkdir -p "$UNPACK"
unzip -q "$ZIP" -d "$UNPACK" || stop "The zip could not be unpacked."
CFGS="$(find "$UNPACK" -name instance.cfg -maxdepth 3)"
[ "$(printf '%s\n' "$CFGS" | grep -c .)" -eq 1 ] || stop "The zip does not hold exactly one Prism instance."
ROOT="$(dirname "$CFGS")"
REL_JSON="$ROOT/questforge-release.json"
[ -f "$REL_JSON" ] || stop "The zip has no questforge-release.json."
NEW_EDITION="$(sed -n 's/.*"edition": *"\([^"]*\)".*/\1/p' "$REL_JSON" | head -1)"
NEW_RELEASE="$(sed -n 's/.*"release": *"\([^"]*\)".*/\1/p' "$REL_JSON" | head -1)"
NEW_PACK="$(sed -n 's/.*"fingerprint": *"\([^"]*\)".*/\1/p' "$REL_JSON" | head -1)"
[ "$NEW_EDITION" = "$EDITION" ] || stop "That zip is the '$NEW_EDITION' edition, not '$EDITION'. Run again with --edition $NEW_EDITION."

# Every file against the release's own SHA1SUMS.txt.
BAD=""; NSUM=0
while IFS= read -r line; do
  case "$line" in
    [0-9a-f]*"  "*) ;;
    *) continue ;;
  esac
  digest="${line%%  *}"
  rel="${line#*  }"
  NSUM=$((NSUM + 1))
  got="$(shasum -a 1 "$ROOT/$rel" 2>/dev/null | awk '{print $1}')"
  [ "$got" = "$digest" ] || BAD="$BAD
  $rel"
done < "$ROOT/SHA1SUMS.txt"
[ -z "$BAD" ] || stop "These files do not match the release, so the download is damaged:$BAD"
say "Release files:     $NSUM checked, all match"
say "This release:      $NEW_RELEASE   pack $NEW_PACK"
REL_CFG="$WORK/release-instance.cfg"
cp "$ROOT/instance.cfg" "$REL_CFG"

# ---- Existing install? --------------------------------------------------------
TARGET="$INSTANCES_DIR/$INSTANCE_NAME"
MC="$TARGET/minecraft"
IS_UPDATE=0
if [ -f "$TARGET/instance.cfg" ]; then IS_UPDATE=1; fi
if [ -e "$TARGET" ] && [ "$IS_UPDATE" -eq 0 ]; then
  stop "A folder named '$INSTANCE_NAME' is in Prism and it is not a Quest Forge install. Run again with --instance-name \"$INSTANCE_NAME (new)\" to install beside it."
fi
if [ "$IS_UPDATE" -eq 1 ]; then
  OLD_REL="$TARGET/questforge-release.json"
  if [ -f "$OLD_REL" ]; then
    old_name="$(sed -n 's/.*"release": *"\([^"]*\)".*/\1/p' "$OLD_REL" | head -1)"
    old_pack="$(sed -n 's/.*"fingerprint": *"\([^"]*\)".*/\1/p' "$OLD_REL" | head -1)"
    say "Installed now:     $old_name   pack $old_pack"
  else
    say "Installed now:     an older Quest Forge install with no release record"
  fi
fi

# ---- Prism or the game open? ---------------------------------------------------
if [ "$SKIP_PROC" -eq 0 ]; then
  if [ "$IS_UPDATE" -eq 1 ] && ps -axww -o command= 2>/dev/null | grep -F "$MC" | grep -i 'java' | grep -q .; then
    stop "Minecraft is running from this instance. Quit the game first."
  fi
  if ps -axww -o command= 2>/dev/null | grep -iE 'prismlauncher|Prism Launcher\.app' | grep -vi 'install-questforge' | grep -q .; then
    stop "Prism Launcher is open. Quit it first; it rewrites the instance settings when it closes."
  fi
fi

# ---- Profile -------------------------------------------------------------------
LITE_TIER=""
if [ -n "$(ls -A "$MC/mods-lite-removed" 2>/dev/null)" ]; then
  if ls "$MC/mods-lite-removed" 2>/dev/null | grep -qi '^journeymap'; then LITE_TIER=potato; else LITE_TIER=lite; fi
fi
if [ -z "$PROFILE" ]; then
  if [ "$IS_UPDATE" -eq 1 ]; then PROFILE=keep
  elif [ "$INTERACTIVE" -eq 1 ]; then
    section "Which Mac is this?"
    say "  n  a Mac that runs the game well with shaders on (normal)"
    say "  l  an 8 to 16 GB Mac that struggles: shaders off, smaller view (lite)"
    say "  p  the weakest Mac you have (potato; the same preset as lite on a Mac)"
    printf 'Choose n, l or p [n]: '
    read -r ans
    case "$ans" in l|L) PROFILE=lite ;; p|P) PROFILE=potato ;; *) PROFILE=none ;; esac
  else PROFILE=none; fi
fi
case "$PROFILE" in
  keep) TIER="$LITE_TIER" ;;
  lite|potato) TIER="$PROFILE" ;;
  *) TIER="" ;;
esac

# ---- The plan --------------------------------------------------------------------
if [ "$IS_UPDATE" -eq 1 ]; then section "Update plan"; else section "New install plan"; fi
if [ "$IS_UPDATE" -eq 1 ]; then
  say "  KEEP     saves, screenshots, options*.txt, servers.dat, journeymap, your resource and shader packs"
  say "  REPLACE  $REPLACE_DIRS and the release files (old copies go to _qf-backups)"
  say "  SET      instance.cfg: Java, memory and JVM arguments; your other settings stay"
else
  say "  CREATE   $TARGET"
fi
say "  JAVA     $JAVA"
say "  MEMORY   min $MIN_MB MiB, max $MAX_MB MiB"
say "  PROFILE  ${TIER:-normal}"
if [ "$PROFILE" = none ] && [ -n "$LITE_TIER" ]; then
  say "  NOTE     this instance is on the $LITE_TIER profile. To go back to normal, run perf-preset.command with show, or ask for help."
fi
if [ "$DRY" -eq 1 ]; then
  section "Dry run: nothing was changed. Run again without --dry-run to install."
  end_pause
  exit 0
fi

# ---- Install -----------------------------------------------------------------------
mkdir -p "$INSTANCES_DIR" || stop "Could not create $INSTANCES_DIR."
BACKUP=""
if [ "$IS_UPDATE" -eq 0 ]; then
  mv "$ROOT" "$TARGET" || stop "Could not move the instance into Prism's folder."
else
  BACKUP="$TARGET/_qf-backups/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP/minecraft" || stop "Could not create the backup folder."
  section "Backing up what is replaced to: $BACKUP"
  for d in $REPLACE_DIRS; do
    [ -e "$MC/$d" ] && mv "$MC/$d" "$BACKUP/minecraft/$d"
  done
  for f in $REPLACE_FILES; do
    [ -e "$MC/$f" ] && cp "$MC/$f" "$BACKUP/minecraft/$f"
  done
  [ -e "$MC/mods-lite-removed" ] && mv "$MC/mods-lite-removed" "$BACKUP/minecraft/mods-lite-removed"
  for item in instance.cfg $ROOT_ITEMS; do
    [ -e "$TARGET/$item" ] && cp -R "$TARGET/$item" "$BACKUP/$item"
  done
  # Replace the release's folders and files.
  mkdir -p "$MC"
  for d in $REPLACE_DIRS; do
    [ -e "$ROOT/minecraft/$d" ] && mv "$ROOT/minecraft/$d" "$MC/$d"
  done
  for f in $REPLACE_FILES; do
    [ -f "$ROOT/minecraft/$f" ] && cp -f "$ROOT/minecraft/$f" "$MC/$f"
  done
  for item in $ROOT_ITEMS; do
    [ -e "$TARGET/$item" ] && rm -rf "$TARGET/$item"
    [ -e "$ROOT/$item" ] && mv "$ROOT/$item" "$TARGET/$item"
  done
  # Everything else the release ships: only what the player does not have yet (cp -n never overwrites).
  if [ -d "$ROOT/minecraft" ]; then cp -Rn "$ROOT/minecraft/." "$MC/"; fi
  rm -rf "$ROOT"
fi

# instance.cfg: this Mac's Java and memory, the release's JVM arguments, everything else as it was.
cfg_set() {
  local f="$1" k="$2" v="$3" tmp="$WORK/cfg.tmp"
  if grep -q "^$k=" "$f" 2>/dev/null; then
    awk -v k="$k" -v v="$v" 'index($0, k "=") == 1 { print k "=" v; next } { print }' "$f" > "$tmp"
  else
    awk -v k="$k" -v v="$v" '{ print } /^\[General\]/ && !done { print k "=" v; done = 1 } END { if (!done) print k "=" v }' "$f" > "$tmp"
  fi
  mv "$tmp" "$f"
}
CFG="$TARGET/instance.cfg"
if [ "$IS_UPDATE" -eq 0 ]; then
  cp "$REL_CFG" "$CFG"
  cfg_set "$CFG" name "$INSTANCE_NAME"
else
  for k in $RELEASE_CFG_KEYS; do
    v="$(grep -m1 "^$k=" "$REL_CFG" | cut -d= -f2-)"
    [ -n "$v" ] && cfg_set "$CFG" "$k" "$v"
  done
fi
cfg_set "$CFG" JavaPath "$JAVA"
cfg_set "$CFG" OverrideJavaLocation true
cfg_set "$CFG" JavaArchitecture 64
cfg_set "$CFG" OverrideMemory true
cfg_set "$CFG" MinMemAlloc "$MIN_MB"
cfg_set "$CFG" MaxMemAlloc "$MAX_MB"
cfg_set "$CFG" OverrideJavaArgs true
if ! grep -q '^uuid=' "$CFG"; then cfg_set "$CFG" uuid "$(uuidgen 2>/dev/null | tr -d '-' | tr 'A-Z' 'a-z')"; fi

# The icon: Prism reads icons from its own folder.
if [ -f "$TARGET/icon.png" ]; then
  mkdir -p "$PRISM_DIR/icons"
  [ -f "$PRISM_DIR/icons/questforge.png" ] || cp "$TARGET/icon.png" "$PRISM_DIR/icons/questforge.png"
fi

# ---- Profile, by the Mac preset the release ships ---------------------------------
PROFILE_NOTE=""
if [ -n "$TIER" ]; then
  if /bin/zsh "$TARGET/perf-preset.command" low > "$WORK/preset.log" 2>&1; then
    PROFILE_NOTE="The $TIER profile is applied (the Mac preset, low). perf-preset.command keeps a backup of your settings."
  else
    PROFILE_NOTE="The $TIER profile did NOT apply. Run perf-preset.command low by hand (see its output in Terminal)."
  fi
fi

section "Done."
say "Installed to: $TARGET"
if [ -n "$BACKUP" ]; then say "Your saves, options and screenshots are untouched. What was replaced is in: $BACKUP"; fi
if [ -n "$PROFILE_NOTE" ]; then say "$PROFILE_NOTE"; fi
section "Next steps"
say "  1. Open Prism Launcher. Sign in with your Microsoft account (Accounts, top right) if you have not."
say "  2. Click '$INSTANCE_NAME', then Launch. Wait three to four minutes on a Mac for the title screen."
say "  3. Multiplayer, Add Server: ask the host for the address. They whitelist your exact name."
end_pause
exit 0

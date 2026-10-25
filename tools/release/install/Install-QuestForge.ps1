<#
.SYNOPSIS
  Installs or updates Quest Forge in Prism Launcher (Windows).

.DESCRIPTION
  Finds Prism's folder and a 64-bit Java 8, picks the memory for this PC, gets the newest
  "client instance" release from GitHub (or a zip you already have), checks every file against the
  release's SHA1SUMS.txt, and puts it in Prism's instances folder as "Quest Forge".

  An update keeps what you made: saves, screenshots, options, servers.dat, JourneyMap data, and
  any resource or shader packs you added. The mods, the config and the pack's other folders are
  replaced; the old copies go to _qf-backups\<date-time>\ inside the instance. Prism and the game
  must be closed, and the installer checks that.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Install-QuestForge.ps1
      Install or update the OptiFine edition from the newest release.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Install-QuestForge.ps1 -WhatIf
      Show what would happen. Changes nothing.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Install-QuestForge.ps1 -Edition angelica -Profile lite
      The Angelica edition, with the lite settings applied.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File Install-QuestForge.ps1 -Zip D:\Downloads\QuestForge-client-instance-optifine.zip
      Use a zip you downloaded yourself. Its .sha1 file must be next to it.

.NOTES
  Hooks for tests (tools/release/tests): -PrismDir, -InstancesDir, -JavaPath, -RamGB,
  -SkipProcessCheck, -ReleasesJson, -NoPrompt. Ordinary use needs none of them.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('optifine', 'angelica')][string]$Edition = 'optifine',
    [string]$InstanceName,
    [string]$Zip,
    [string]$PrismDir,
    [string]$InstancesDir,
    [string]$JavaPath,
    [double]$RamGB,
    [ValidateSet('keep', 'none', 'lite', 'potato')][string]$Profile,
    [switch]$NoPrompt,
    [switch]$SkipProcessCheck,
    [string]$ReleasesJson
)

$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 may still negotiate TLS 1.0/1.1, which GitHub refuses.
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }
$Repo = 'MarionWhite/quest-forge'
$DefaultNames = @{ optifine = 'Quest Forge'; angelica = 'Quest Forge Angelica' }
if (-not $InstanceName) { $InstanceName = $DefaultNames[$Edition] }
$OnWindows = ($env:OS -eq 'Windows_NT')
# -WhatIf is handled here, not by the cmdlets: the temp download and unpack still happen in a dry run.
$DryRun = [bool]$WhatIfPreference
$WhatIfPreference = $false
$Interactive = (-not $NoPrompt) -and [Environment]::UserInteractive
$ProfileGiven = $PSBoundParameters.ContainsKey('Profile')
$RamGiven = $PSBoundParameters.ContainsKey('RamGB')

# The release folders an update replaces (the pack's own mods, config and data).
$ReplaceDirs = @('mods', 'config', 'scripts', 'resources', 'assets', 'fonts')
# Release files in minecraft\ that an update replaces.
$ReplaceFiles = @('log4j2_17-111.xml', 'questforge.ico', 'pack.png', 'tf-tutorials.txt')
# Folders where an update adds what is missing and never overwrites a file the player has.
$AddMissingDirs = @('resourcepacks', 'shaderpacks', 'structures', 'legends', 'hats', 'CustomDISkins', 'customnpcs')
# Player settings: kept, and copied from the release only when missing.
$KeepFiles = @('options.txt', 'optionsof.txt', 'optionsshaders.txt', 'betterfps.txt', 'servers.dat')
# Instance-root items the release replaces as a whole.
$ReplaceRootItems = @('mmc-pack.json', 'patches', 'libraries', 'questforge-tools', 'perf-preset.command',
                      'questforge-release.json', 'SHA1SUMS.txt', 'icon.png')
# instance.cfg keys the release decides. The rest (UI layout, play time, uuid) stays as it is.
$ReleaseCfgKeys = @('ConfigVersion', 'InstanceType', 'JvmArgs', 'OverrideJavaArgs', 'OverrideMemory', 'PermGen', 'iconKey', 'notes')

function Say([string]$Text = '') { Write-Host $Text }
function Head([string]$Text) { Write-Host ''; Write-Host $Text -ForegroundColor Cyan }

function Get-PrismDataDir {
    if ($PrismDir) {
        if (-not (Test-Path -LiteralPath $PrismDir)) { throw "The folder -PrismDir '$PrismDir' does not exist." }
        return (Resolve-Path -LiteralPath $PrismDir).Path
    }
    $appdata = Join-Path $env:APPDATA 'PrismLauncher'
    if (Test-Path -LiteralPath $appdata) { return $appdata }
    throw ("Prism Launcher's folder was not found ($appdata).`n" +
           "  Open Prism Launcher once and try again. If Prism is a portable copy, run this with`n" +
           "  -PrismDir set to the folder that holds prismlauncher.exe.")
}

function Get-InstancesDir([string]$Data) {
    if ($InstancesDir) { return $InstancesDir }
    $cfg = Join-Path $Data 'prismlauncher.cfg'
    if (Test-Path -LiteralPath $cfg) {
        foreach ($line in Get-Content -LiteralPath $cfg) {
            if ($line -match '^\s*InstanceDir\s*=\s*"?([^"]*?)"?\s*$' -and $Matches[1]) {
                $v = $Matches[1]
                if (-not [IO.Path]::IsPathRooted($v)) { $v = Join-Path $Data $v }
                return $v
            }
        }
    }
    return (Join-Path $Data 'instances')
}

function Test-Java8x64([string]$Exe) {
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return $false }
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $out = (& $Exe -version 2>&1 | Out-String) } catch { return $false } finally { $ErrorActionPreference = $old }
    return ($out -match 'version "1\.8\.' -and $out -match '64-Bit')
}

function Find-Java {
    if ($JavaPath) { if (Test-Java8x64 $JavaPath) { return $JavaPath } else { return $null } }
    # The places the release's launch .bat files look (build_client_release.py), in the same order.
    $candidates = @()
    if ($env:JAVA_HOME) { $candidates += (Join-Path $env:JAVA_HOME 'bin\java.exe') }
    foreach ($p in @('C:\Program Files\Java\jre1.8*\bin\java.exe',
                     'C:\Program Files\Java\jdk1.8*\jre\bin\java.exe',
                     'C:\Program Files\Eclipse Adoptium\jre-8*\bin\java.exe',
                     'C:\Program Files\Eclipse Adoptium\jdk-8*\bin\java.exe')) {
        $candidates += @(Get-ChildItem -Path $p -ErrorAction SilentlyContinue |
                         Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
    }
    foreach ($c in $candidates) { if (Test-Java8x64 $c) { return $c } }
    return $null
}

function Get-RamGB {
    if ($RamGiven) { return $RamGB }
    if ($OnWindows) {
        try { return [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB) } catch { }
    }
    return 8   # unknown: the smallest row, which is safe on any PC
}

# The RAM table (docs/setup/jvm-args.md, the play page): installed RAM -> heap min and max in MiB.
function Get-Memory([double]$Gb) {
    if ($Gb -lt 11) { return @{ Min = 1024; Max = 3072; Row = '8 GB' } }
    if ($Gb -lt 15) { return @{ Min = 1024; Max = 4096; Row = '12 GB' } }
    if ($Gb -lt 28) { return @{ Min = 2048; Max = 5120; Row = '16 GB' } }
    return @{ Min = 2048; Max = 6144; Row = '32 GB or more' }
}

function Get-RunningCommands {
    if ($OnWindows) {
        $lines = @(Get-CimInstance Win32_Process |
                   Where-Object { $_.Name -match '^(java|javaw|prismlauncher)\.exe$' } |
                   ForEach-Object { "$($_.Name) $($_.CommandLine)" })
    } else {
        $lines = @(& ps -axww -o command= 2>$null)
    }
    # This script's own command line can name the Prism folder; that is not Prism running.
    return @($lines | Where-Object { $_ -and $_ -notmatch '(?i)install-questforge' })
}

function Get-ReleasesListing {
    if ($ReleasesJson) { return @(Get-Content -Raw -LiteralPath $ReleasesJson | ConvertFrom-Json) }
    $headers = @{ 'User-Agent' = 'QuestForge-installer'; Accept = 'application/vnd.github+json' }
    try {
        return @(Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases?per_page=30" -Headers $headers)
    } catch {
        throw ("Could not reach GitHub to find the release ($($_.Exception.Message)).`n" +
               "  Check the internet connection, or download the zip and its .sha1 and run with -Zip <file>.")
    }
}

# The newest release named "client instance" that has a zip for this edition.
function Select-Release {
    foreach ($r in (Get-ReleasesListing)) {
        if ($r.draft -or -not $r.name -or $r.name -notmatch '(?i)client instance') { continue }
        $zip = @($r.assets | Where-Object { $_.name -match "(?i)$Edition" -and $_.name -match '\.zip$' }) | Select-Object -First 1
        if (-not $zip) { continue }
        $sha = @($r.assets | Where-Object { $_.name -eq ($zip.name + '.sha1') }) | Select-Object -First 1
        if (-not $sha) { throw "Release '$($r.name)' has $($zip.name) but no $($zip.name).sha1. Ask the host to upload it." }
        return [pscustomobject]@{ Release = $r.name; ZipName = $zip.name; ZipUrl = $zip.browser_download_url; ShaUrl = $sha.browser_download_url }
    }
    throw "No release named 'client instance' has a $Edition download yet. Ask the host."
}

function Get-Release([string]$Url, [string]$Dest) {
    if ($Url -match '^https?://') {
        Invoke-WebRequest -Uri $Url -OutFile $Dest -Headers @{ 'User-Agent' = 'QuestForge-installer' } -UseBasicParsing
    } else {
        $local = if ($Url -match '^file://') { ([Uri]$Url).LocalPath } else { $Url }
        Copy-Item -LiteralPath $local -Destination $Dest   # a local file (tests only)
    }
}

function Set-CfgKey([string]$File, [string]$Key, [string]$Value) {
    $lines = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $File) { foreach ($l in Get-Content -LiteralPath $File) { $lines.Add($l) } }
    $done = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].StartsWith("$Key=")) { $lines[$i] = "$Key=$Value"; $done = $true }
    }
    if (-not $done) {
        # New keys belong in [General]; Prism ignores keys that end up under [UI].
        $at = $lines.IndexOf('[General]')
        if ($at -ge 0) { $lines.Insert($at + 1, "$Key=$Value") } else { $lines.Insert(0, "$Key=$Value") }
    }
    [IO.File]::WriteAllLines($File, [string[]]$lines, (New-Object Text.UTF8Encoding($false)))
}

function Get-CfgValue([string]$Text, [string]$Key) {
    foreach ($l in ($Text -split "`r?`n")) { if ($l.StartsWith("$Key=")) { return $l.Substring($Key.Length + 1) } }
    return $null
}

# Copies files under $From that $To does not have yet. Never overwrites.
function Copy-Missing([string]$From, [string]$To) {
    if (-not (Test-Path -LiteralPath $From)) { return }
    foreach ($f in @(Get-ChildItem -LiteralPath $From -Recurse -File)) {
        $rel = $f.FullName.Substring($From.Length).TrimStart('\', '/')
        $dst = Join-Path $To $rel
        if (-not (Test-Path -LiteralPath $dst)) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
            Copy-Item -LiteralPath $f.FullName -Destination $dst
        }
    }
}

function Test-Release([string]$Root) {
    $bad = @()
    $n = 0
    foreach ($l in Get-Content -LiteralPath (Join-Path $Root 'SHA1SUMS.txt')) {
        if ($l -notmatch '^([0-9a-f]{40})  (.+)$') { continue }
        $n++
        $rel = $Matches[2]
        $digest = $Matches[1]
        $p = Join-Path $Root ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $p) -or (Get-FileHash -Algorithm SHA1 -LiteralPath $p).Hash.ToLower() -ne $digest) {
            $bad += $rel
        }
    }
    return [pscustomobject]@{ Count = $n; Bad = $bad }
}

function Install-QuestForge {
    Head 'Quest Forge installer'
    Say "Edition: $Edition    Instance name: $InstanceName"

    # 1. Prism's folders.
    $data = Get-PrismDataDir
    $instances = Get-InstancesDir $data
    Say "Prism folder:      $data"
    Say "Instances folder:  $instances"

    # 2. Java 8, 64-bit. Checked before anything is touched.
    $java = Find-Java
    if (-not $java) {
        throw ("Java 8 (64-bit) was not found.`n" +
               "  Install Temurin 8 (x64, the .msi) from adoptium.net with the defaults, then run this again.`n" +
               "  Keep any newer Java you have: Prism picks Java 8 for this instance.")
    }
    Say "Java 8 (64-bit):   $java"

    # 3. Memory for this PC.
    $gb = Get-RamGB
    $mem = Get-Memory $gb
    Say "Installed RAM:     $gb GB  (heap $($mem.Min) to $($mem.Max) MiB, the $($mem.Row) row)"

    # 4. The release: a zip you gave, or the newest one on GitHub.
    $stage = Join-Path ([IO.Path]::GetTempPath()) ('qf-install-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    if ($Zip) {
        if (-not (Test-Path -LiteralPath $Zip)) { throw "The zip '$Zip' does not exist." }
        $zipPath = (Resolve-Path -LiteralPath $Zip).Path
        $shaPath = "$zipPath.sha1"
        if (-not (Test-Path -LiteralPath $shaPath)) { throw "No $(Split-Path -Leaf $shaPath) next to the zip. Download it along with the zip." }
    } else {
        Head 'Looking for the newest release on GitHub...'
        $sel = Select-Release
        Say "Release:           $($sel.Release)"
        Say "Downloading        $($sel.ZipName)"
        $zipPath = Join-Path $stage $sel.ZipName
        $shaPath = "$zipPath.sha1"
        Get-Release $sel.ZipUrl $zipPath
        Get-Release $sel.ShaUrl $shaPath
    }
    $want = ((Get-Content -Raw -LiteralPath $shaPath).Trim() -split '\s+')[0].ToLower()
    $got = (Get-FileHash -Algorithm SHA1 -LiteralPath $zipPath).Hash.ToLower()
    if ($got -ne $want) { throw 'The download is damaged (its checksum does not match). Run the installer again.' }
    Say 'Download checksum: ok'

    # 5. Unpack, find the instance, check every file against the release's SHA1SUMS.txt.
    $unpack = Join-Path $stage 'unpacked'
    Expand-Archive -LiteralPath $zipPath -DestinationPath $unpack -Force
    $found = @(Get-ChildItem -LiteralPath $unpack -Recurse -Filter instance.cfg)
    if ($found.Count -ne 1) { throw "The zip does not hold exactly one Prism instance (found $($found.Count))." }
    $root = $found[0].DirectoryName
    $newRel = Get-Content -Raw -LiteralPath (Join-Path $root 'questforge-release.json') | ConvertFrom-Json
    if ($newRel.edition -ne $Edition) {
        throw "That zip is the '$($newRel.edition)' edition, not '$Edition'. Run again with -Edition $($newRel.edition)."
    }
    $check = Test-Release $root
    if ($check.Bad.Count -gt 0) {
        throw ("These files do not match the release, so the download is damaged:`n  " + ($check.Bad -join "`n  "))
    }
    Say "Release files:     $($check.Count) checked, all match"
    Say "This release:      $($newRel.release)   pack $($newRel.pack.date) $($newRel.pack.fingerprint)"
    $releaseCfgText = Get-Content -Raw -LiteralPath (Join-Path $root 'instance.cfg')
    $releaseCfgFile = Join-Path $stage 'release-instance.cfg'
    [IO.File]::WriteAllText($releaseCfgFile, $releaseCfgText, (New-Object Text.UTF8Encoding($false)))

    # 6. Existing install?
    $target = Join-Path $instances $InstanceName
    $mc = Join-Path $target 'minecraft'
    $isUpdate = Test-Path -LiteralPath (Join-Path $target 'instance.cfg')
    if ((Test-Path -LiteralPath $target) -and -not $isUpdate) {
        throw "A folder named '$InstanceName' is in Prism and it is not a Quest Forge install. Run again with -InstanceName '$InstanceName (new)' to install beside it."
    }
    if ($isUpdate) {
        $oldRelPath = Join-Path $target 'questforge-release.json'
        if (Test-Path -LiteralPath $oldRelPath) {
            $old = Get-Content -Raw -LiteralPath $oldRelPath | ConvertFrom-Json
            Say "Installed now:     $($old.release)   pack $($old.pack.date) $($old.pack.fingerprint)"
        } else {
            Say 'Installed now:     an older Quest Forge install with no release record'
        }
    }

    # 7. Prism or the game holding the instance open?
    if (-not $SkipProcessCheck) {
        $running = Get-RunningCommands
        if ($isUpdate -and ($running | Where-Object { $_ -match '(?i)java' -and $_.IndexOf($mc, [StringComparison]::OrdinalIgnoreCase) -ge 0 })) {
            throw 'Minecraft is running from this instance. Quit the game first.'
        }
        if ($running | Where-Object { $_ -match '(?i)prismlauncher' }) {
            throw 'Prism Launcher is open. Close it first; it rewrites the instance settings when it closes.'
        }
    }

    # 8. Profile. An update keeps the lite or potato state the instance already has.
    $liteDir = Join-Path $mc 'mods-lite-removed'
    $liteTier = $null
    if (Test-Path -LiteralPath $liteDir) {
        $moved = @(Get-ChildItem -LiteralPath $liteDir -File -ErrorAction SilentlyContinue)
        if ($moved.Count -gt 0) {
            $liteTier = $(if ($moved | Where-Object { $_.Name -match '^journeymap' }) { 'potato' } else { 'lite' })
        }
    }
    if (-not $ProfileGiven) {
        if ($isUpdate) { $Profile = 'keep' }
        elseif ($Interactive) {
            Head 'Which PC is this?'
            Say '  n  a gaming PC, or a graphics card from the last five years (normal)'
            Say '  l  a mid-range PC: GTX 1060 / RX 580 class, 8 to 16 GB (lite)'
            Say '  p  a laptop or integrated graphics, 8 GB (potato)'
            $ans = (Read-Host 'Choose n, l or p [n]').Trim().ToLower()
            $Profile = switch ($ans) { 'l' { 'lite' } 'p' { 'potato' } default { 'none' } }
        } else { $Profile = 'none' }
    }
    $tier = switch ($Profile) {
        'lite' { 'lite' }
        'potato' { 'potato' }
        'keep' { $liteTier }
        default { $null }
    }

    # 9. The plan.
    Head $(if ($isUpdate) { 'Update plan' } else { 'New install plan' })
    if ($isUpdate) {
        Say '  KEEP     saves, screenshots, options*.txt, servers.dat, journeymap, your resource and shader packs'
        Say "  REPLACE  $($ReplaceDirs -join ', ') and the release files (old copies go to _qf-backups)"
        Say '  SET      instance.cfg: Java, memory and JVM arguments; your other settings stay'
    } else {
        Say "  CREATE   $target"
    }
    Say "  JAVA     $java"
    Say "  MEMORY   min $($mem.Min) MiB, max $($mem.Max) MiB"
    Say "  PROFILE  $(if ($tier) { $tier } else { 'normal' })"
    if ($Profile -eq 'none' -and $liteTier) {
        Say "  NOTE     this instance is on the $liteTier profile. To go back to normal later, run apply-lite.ps1 -Undo."
    }

    if ($DryRun) {
        Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
        Head 'Dry run: nothing was changed. Run again without -WhatIf to install.'
        return
    }

    # 10. Install.
    New-Item -ItemType Directory -Path $instances -Force | Out-Null
    $stageMc = Join-Path $root 'minecraft'
    $backup = $null
    if (-not $isUpdate) {
        Move-Item -LiteralPath $root -Destination $target
    } else {
        $backup = Join-Path $target ('_qf-backups\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
        New-Item -ItemType Directory -Path (Join-Path $backup 'minecraft') -Force | Out-Null
        Say "Backing up what is replaced to: $backup"
        # Old copies of the replaced things, moved (not copied) so the disk is not used twice.
        foreach ($d in $ReplaceDirs) {
            $old = Join-Path $mc $d
            if (Test-Path -LiteralPath $old) { Move-Item -LiteralPath $old -Destination (Join-Path $backup "minecraft\$d") }
        }
        foreach ($f in $ReplaceFiles) {
            $old = Join-Path $mc $f
            if (Test-Path -LiteralPath $old) { Copy-Item -LiteralPath $old -Destination (Join-Path $backup "minecraft\$f") }
        }
        if (Test-Path -LiteralPath $liteDir) { Move-Item -LiteralPath $liteDir -Destination (Join-Path $backup 'minecraft\mods-lite-removed') }
        foreach ($item in @('instance.cfg', 'mmc-pack.json', 'patches', 'libraries', 'questforge-tools',
                            'perf-preset.command', 'questforge-release.json', 'SHA1SUMS.txt', 'icon.png')) {
            $old = Join-Path $target $item
            if (Test-Path -LiteralPath $old) { Copy-Item -LiteralPath $old -Destination (Join-Path $backup $item) -Recurse }
        }
        # Replace.
        foreach ($d in $ReplaceDirs) {
            $new = Join-Path $stageMc $d
            if (Test-Path -LiteralPath $new) { Move-Item -LiteralPath $new -Destination (Join-Path $mc $d) }
        }
        foreach ($f in $ReplaceFiles) {
            $new = Join-Path $stageMc $f
            if (Test-Path -LiteralPath $new) { Copy-Item -LiteralPath $new -Destination (Join-Path $mc $f) -Force }
        }
        foreach ($item in $ReplaceRootItems) {
            $old = Join-Path $target $item
            if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Recurse -Force }
            $new = Join-Path $root $item
            if (Test-Path -LiteralPath $new) { Move-Item -LiteralPath $new -Destination $old }
        }
        # Add what the player does not have, never overwrite.
        foreach ($d in $AddMissingDirs) { Copy-Missing (Join-Path $stageMc $d) (Join-Path $mc $d) }
        foreach ($f in $KeepFiles) {
            $new = Join-Path $stageMc $f
            if ((Test-Path -LiteralPath $new) -and -not (Test-Path -LiteralPath (Join-Path $mc $f))) { Copy-Item -LiteralPath $new -Destination (Join-Path $mc $f) }
        }
        # Anything else the release ships: add what is missing.
        foreach ($d in @(Get-ChildItem -LiteralPath $stageMc -Directory -ErrorAction SilentlyContinue)) {
            if (($ReplaceDirs + $AddMissingDirs) -notcontains $d.Name) { Copy-Missing $d.FullName (Join-Path $mc $d.Name) }
        }
        foreach ($f in @(Get-ChildItem -LiteralPath $stageMc -File -ErrorAction SilentlyContinue)) {
            if (($ReplaceFiles + $KeepFiles) -notcontains $f.Name -and -not (Test-Path -LiteralPath (Join-Path $mc $f.Name))) {
                Copy-Item -LiteralPath $f.FullName -Destination $mc
            }
        }
        Remove-Item -LiteralPath $root -Recurse -Force
    }

    # The icon: Prism reads icons from its own folder.
    $icon = Join-Path $target 'icon.png'
    if (Test-Path -LiteralPath $icon) {
        $iconDir = Join-Path $data 'icons'
        New-Item -ItemType Directory -Path $iconDir -Force | Out-Null
        $iconDst = Join-Path $iconDir 'questforge.png'
        if (-not (Test-Path -LiteralPath $iconDst)) { Copy-Item -LiteralPath $icon -Destination $iconDst }
    }

    # instance.cfg: the release's values for the keys it decides, then this PC's Java and memory.
    $cfg = Join-Path $target 'instance.cfg'
    if (-not $isUpdate) { Copy-Item -LiteralPath $releaseCfgFile -Destination $cfg }
    if (-not $isUpdate) { Set-CfgKey $cfg 'name' $InstanceName }
    foreach ($k in $ReleaseCfgKeys) {
        $v = Get-CfgValue $releaseCfgText $k
        if ($null -ne $v) { Set-CfgKey $cfg $k $v }
    }
    Set-CfgKey $cfg 'JavaPath' $java
    Set-CfgKey $cfg 'OverrideJavaLocation' 'true'
    Set-CfgKey $cfg 'JavaArchitecture' '64'
    Set-CfgKey $cfg 'OverrideMemory' 'true'
    Set-CfgKey $cfg 'MinMemAlloc' ([string]$mem.Min)
    Set-CfgKey $cfg 'MaxMemAlloc' ([string]$mem.Max)
    Set-CfgKey $cfg 'OverrideJavaArgs' 'true'
    if (-not (Get-CfgValue ([IO.File]::ReadAllText($cfg)) 'uuid')) {
        Set-CfgKey $cfg 'uuid' ([guid]::NewGuid().ToString('N'))
    }
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue

    # 11. Lite or potato, by the tooling the release ships.
    $liteNote = $null
    if ($tier) {
        $apply = Join-Path $target 'questforge-tools\lite-client\apply-lite.ps1'
        try {
            & $apply -Instance $mc -Tier $tier | Out-Null
            $liteNote = "The $tier profile is applied. apply-lite.ps1 -Undo puts everything back."
        } catch {
            $liteNote = "The $tier profile did NOT apply ($($_.Exception.Message)). Run questforge-tools\lite-client\apply-lite.ps1 by hand; its README says how."
        }
    }

    Head 'Done.'
    Say "Installed to: $target"
    if ($backup) { Say "Your saves, options and screenshots are untouched. What was replaced is in: $backup" }
    if ($liteNote) { Say $liteNote }
    Head 'Next steps'
    Say '  1. Open Prism Launcher. Sign in with your Microsoft account (Accounts, top right) if you have not.'
    Say "  2. Click '$InstanceName', then Launch. Wait two to four minutes for the title screen."
    Say '  3. Multiplayer, Add Server: ask the host for the address. They whitelist your exact name.'
}

try {
    Install-QuestForge
} catch {
    Write-Host ''
    Write-Host "STOPPED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Fix the problem above and run the installer again. Your saves are not touched by a re-run.'
    if ($Interactive) { Write-Host ''; Read-Host 'Press Enter to close' | Out-Null }
    exit 1
}
if ($Interactive) { Write-Host ''; Read-Host 'Press Enter to close' | Out-Null }

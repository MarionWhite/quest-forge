<#
.SYNOPSIS
  Put a Quest Forge client on the full, lite or potato profile, or back on its own settings.

.DESCRIPTION
  Reads profiles\<name>.json (the same files the Mac tooling reads) and applies it to one
  game folder: the folder that holds mods\ and options.txt (in Prism: right-click the
  instance -> Folder -> .minecraft). It changes only client-side files the server never
  sees:
    options.txt                      the profile's video keys; keybinds, sound, chat untouched
    config\angelica-options.json     Celeritas quality and FPS-reducer settings (merged)
    config\angelica-modules.cfg      Angelica module switches (dynamic lights, item limit)
    config\shaders.properties        shader pack on/off and which pack
    shaderpacks\<pack>.txt           the pack's preset (QF_PRESET) and options
    mods\ -> mods-aside\             the profile's client-only jars, moved, never deleted
  On the OptiFine E7 fallback client (no Angelica jar) it writes optionsof.txt and
  optionsshaders.txt instead of the Angelica files. Content is identical by construction:
  every jar it moves is on the server's CLIENT_ONLY list, so the server never had it.

  Idempotent: applying the same profile twice changes nothing. Every file it is about to
  change is copied first: the player's own settings go to _qf-profile\original\ (written
  once per file, never overwritten; -Revert restores them) and the pre-change state of
  each run to _qf-profile\backup-<time>\. Files are unlinked before they are rewritten,
  so a test folder whose files are hard links never writes through to another install.

.PARAMETER Instance  The game folder (holds mods\ and options.txt).
.PARAMETER Profile   full, lite (default) or potato: profiles\<name>.json.
.PARAMETER Shaders   auto (default: what the profile says) or off: shaders off whatever the
                     profile says, for GPUs below the Potato class or the E7 client.
.PARAMETER Revert    Put the player's own settings back and move every jar home.
.PARAMETER Status    Show the applied profile and the live values; change nothing.
.PARAMETER WhatIf    Print what would change and write nothing.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "C:\Users\me\AppData\Roaming\PrismLauncher\instances\Quest Forge\.minecraft" -Profile lite
  powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "..." -Profile potato -Shaders off
  powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "..." -Revert
  powershell -ExecutionPolicy Bypass -File apply-profile.ps1 -Instance "..." -Status
  Add -WhatIf to any of them to see the changes without making them.
#>
param(
    [Parameter(Mandatory = $true)][string]$Instance,
    [ValidateSet('full', 'lite', 'potato')][string]$Profile = 'lite',
    [ValidateSet('auto', 'off')][string]$Shaders = 'auto',
    [switch]$Revert,
    [switch]$Status,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Instance = (Resolve-Path -LiteralPath $Instance).Path.TrimEnd('\')
$mods = Join-Path $Instance 'mods'
$aside = Join-Path $Instance 'mods-aside'
$state = Join-Path $Instance '_qf-profile'
$orig = Join-Path $state 'original'
$marker = Join-Path $state 'applied.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$dry = [bool]$WhatIf
$verb = if ($dry) { 'would ' } else { '' }

if (-not (Test-Path -LiteralPath $mods -PathType Container)) {
    throw "$Instance has no mods\ folder. Point -Instance at the game folder that holds mods\ and options.txt (Prism: right-click the instance -> Folder -> .minecraft)."
}
$renderer = 'none'
if (Get-ChildItem -LiteralPath $mods -Filter 'angelica-*.jar' -File -ErrorAction SilentlyContinue) { $renderer = 'angelica' }
elseif (Get-ChildItem -LiteralPath $mods -Filter 'OptiFine*.jar' -File -ErrorAction SilentlyContinue) { $renderer = 'e7' }

# The game rewrites options.txt and Angelica rewrites its JSON when they quit: a change made
# while the game runs is lost, and a jar moved under a running game is a crash.
$running = Get-CimInstance Win32_Process -Filter "Name='java.exe' or Name='javaw.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($Instance, [StringComparison]::OrdinalIgnoreCase) -ge 0 }
if ($running -and -not $Status) { throw "Minecraft is running from this folder (pid $($running.ProcessId -join ', ')). Quit it first." }

# ------------------------------------------------------------------ helpers
function Rel([string]$path) { return $path.Substring($Instance.Length).TrimStart('\') }
function Read-Lines([string]$path) {
    if (Test-Path -LiteralPath $path) { return [string[]](Get-Content -LiteralPath $path -Encoding UTF8) } else { return [string[]]@() }
}
function Pairs($obj) {
    # The profile's JSON objects and our own [ordered] tables, as one ordered key -> value map.
    $o = [ordered]@{}
    if ($null -eq $obj) { return $o }
    if ($obj -is [System.Collections.IDictionary]) { foreach ($k in $obj.Keys) { $o[[string]$k] = $obj[$k] } }
    else { foreach ($p in $obj.PSObject.Properties) { if (-not $p.Name.StartsWith('_')) { $o[$p.Name] = $p.Value } } }
    return $o
}
function Unlink([string]$path) {
    # Deleting first turns a hard link into a plain name; the write then creates a new file.
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    $dir = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
}
function Write-Fresh([string]$path, $item) {
    Unlink $path
    if ($null -ne $item.text) { [IO.File]::WriteAllText($path, $item.text, $utf8) }
    else { [IO.File]::WriteAllLines($path, [string[]]$item.lines, $utf8) }
}
function Copy-Fresh([string]$from, [string]$to) {
    Unlink $to
    Copy-Item -LiteralPath $from -Destination $to
}

# key<sep>value files: options.txt (:), optionsof.txt (:), *.properties and shaderpacks\*.txt (=).
function Set-KeyLines([string[]]$lines, $keys, [string]$sep) {
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($l in $lines) { $out.Add($l) }
    $changes = @()
    $pairs = Pairs $keys
    foreach ($k in $pairs.Keys) {
        $want = "$k$sep$($pairs[$k])"
        $idx = -1
        for ($i = 0; $i -lt $out.Count; $i++) { if ($out[$i].StartsWith("$k$sep")) { $idx = $i; break } }
        if ($idx -ge 0) {
            if ($out[$idx] -ne $want) { $changes += "$($out[$idx])  ->  $want"; $out[$idx] = $want }
        } else { $changes += "+ $want"; $out.Add($want) }
    }
    return @{ lines = $out.ToArray(); changes = $changes }
}

# Angelica's settings are JSON (config\angelica-options.json): merge the profile's keys in,
# keep everything else, report what changed.
function Merge-Json($base, $over, [string]$prefix, [ref]$changes) {
    foreach ($p in $over.PSObject.Properties) {
        if ($p.Name.StartsWith('_')) { continue }
        $path = if ($prefix) { "$prefix.$($p.Name)" } else { $p.Name }
        $cur = $base.PSObject.Properties[$p.Name]
        if ($p.Value -is [System.Management.Automation.PSCustomObject]) {
            if (-not $cur) {
                $base | Add-Member -NotePropertyName $p.Name -NotePropertyValue (New-Object PSObject)
                $cur = $base.PSObject.Properties[$p.Name]
            } elseif ($cur.Value -isnot [System.Management.Automation.PSCustomObject]) { $cur.Value = New-Object PSObject }
            Merge-Json $cur.Value $p.Value $path $changes
        } elseif ($cur) {
            if ("$($cur.Value)" -ne "$($p.Value)") { $changes.Value += "$path : $($cur.Value)  ->  $($p.Value)"; $cur.Value = $p.Value }
        } else {
            $changes.Value += "+ $path : $($p.Value)"
            $base | Add-Member -NotePropertyName $p.Name -NotePropertyValue $p.Value
        }
    }
}

# Forge-style config (config\angelica-modules.cfg): B:/I:/S:/D: keys inside general { }.
# A file Angelica has not written yet gets just our keys; Forge fills in the rest on boot.
function Set-CfgLines([string[]]$lines, $keys) {
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($l in $lines) { $out.Add($l) }
    $changes = @()
    if ($out.Count -eq 0) { foreach ($l in '# Configuration file', '', 'general {', '}') { $out.Add($l) } }
    $pairs = Pairs $keys
    $added = 0
    foreach ($k in $pairs.Keys) {
        $v = "$($pairs[$k])"
        $idx = -1; $indent = '    '
        for ($i = 0; $i -lt $out.Count; $i++) {
            if ($out[$i] -match '^(\s*)([BISD]:(?:"[^"]*"|[\w.]+))=(.*)$' -and $Matches[2] -eq $k) { $idx = $i; $indent = $Matches[1]; break }
        }
        $new = "$indent$k=$v"
        if ($idx -ge 0) {
            if ($out[$idx] -ne $new) { $changes += "$($out[$idx].Trim())  ->  $($new.Trim())"; $out[$idx] = $new }
        } else {
            $g = -1
            for ($i = 0; $i -lt $out.Count; $i++) { if ($out[$i] -match '^\s*general\s*\{') { $g = $i; break } }
            if ($g -lt 0) { $out.Add('general {'); $out.Add('}'); $g = $out.Count - 2; $added = 0 }
            $out.Insert($g + 1 + $added, $new)
            $added++
            $changes += "+ $($new.Trim())"
        }
    }
    return @{ lines = $out.ToArray(); changes = $changes }
}

# ------------------------------------------------------------------ status
function Read-Marker {
    if (Test-Path -LiteralPath $marker) { return Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json } else { return $null }
}
if ($Status) {
    $m = Read-Marker
    if ($m) { Write-Host "profile: $($m.profile) (shaders $($m.shaders)), applied $($m.applied) on the $($m.renderer) client" }
    else { Write-Host "profile: none applied by this script (the player's own settings)" }
    $opt = @{}
    foreach ($l in Read-Lines (Join-Path $Instance 'options.txt')) { $i = $l.IndexOf(':'); if ($i -gt 0) { $opt[$l.Substring(0, $i)] = $l.Substring($i + 1) } }
    Write-Host ("options.txt: renderDistance {0}, fancyGraphics {1}, ao {2}, particles {3}, mipmapLevels {4}, maxFps {5}" -f $opt['renderDistance'], $opt['fancyGraphics'], $opt['ao'], $opt['particles'], $opt['mipmapLevels'], $opt['maxFps'])
    if ($renderer -eq 'angelica') {
        $sp = @{}
        foreach ($l in Read-Lines (Join-Path $Instance 'config\shaders.properties')) { $i = $l.IndexOf('='); if ($i -gt 0 -and -not $l.StartsWith('#')) { $sp[$l.Substring(0, $i)] = $l.Substring($i + 1) } }
        $preset = ''
        if ($sp['shaderPack']) {
            foreach ($l in Read-Lines (Join-Path $Instance "shaderpacks\$($sp['shaderPack']).txt")) { if ($l.StartsWith('QF_PRESET=')) { $preset = " QF_PRESET=$($l.Substring(10))" } }
        }
        Write-Host "shaders: enableShaders=$($sp['enableShaders']) shaderPack=$($sp['shaderPack'])$preset"
        $ao = Join-Path $Instance 'config\angelica-options.json'
        if (Test-Path -LiteralPath $ao) {
            $j = Get-Content -LiteralPath $ao -Raw | ConvertFrom-Json
            Write-Host "angelica: biome_blend_radius $($j.quality.biome_blend_radius), grass $($j.quality.grass_quality), smooth lighting $($j.quality.use_celeritas_smooth_lighting), filter $($j.quality.texture_filter_mode), vsync $($j.advanced.vsync_mode), reducer $($j.reducer.enabled)"
        } else { Write-Host "angelica: config\angelica-options.json not written yet (Angelica has not started here)" }
    } elseif ($renderer -eq 'e7') {
        $of = @{}
        foreach ($l in Read-Lines (Join-Path $Instance 'optionsof.txt')) { $i = $l.IndexOf(':'); if ($i -gt 0) { $of[$l.Substring(0, $i)] = $l.Substring($i + 1) } }
        $sh = @{}
        foreach ($l in Read-Lines (Join-Path $Instance 'optionsshaders.txt')) { $i = $l.IndexOf('='); if ($i -gt 0) { $sh[$l.Substring(0, $i)] = $l.Substring($i + 1) } }
        Write-Host "optifine: shaderPack=$($sh['shaderPack']) ofFastRender=$($of['ofFastRender']) ofSmoothFps=$($of['ofSmoothFps']) ofDynamicLights=$($of['ofDynamicLights'])"
    } else { Write-Host "renderer: neither Angelica nor OptiFine found in mods\" }
    if (Test-Path -LiteralPath $aside) {
        $j = @(Get-ChildItem -LiteralPath $aside -File | ForEach-Object Name)
        if ($j.Count) { Write-Host "mods-aside: $($j -join ', ')" } else { Write-Host "mods-aside: empty" }
    } else { Write-Host "mods-aside: none" }
    if ($running) { Write-Host "note: Minecraft is running from this folder (pid $($running.ProcessId -join ', '))" }
    return
}

# ------------------------------------------------------------------ revert
if ($Revert) {
    $n = 0
    if (Test-Path -LiteralPath $orig) {
        foreach ($f in Get-ChildItem -LiteralPath $orig -File -Recurse) {
            $rel = $f.FullName.Substring($orig.Length).TrimStart('\')
            if ($rel.EndsWith('.absent')) {
                $target = Join-Path $Instance $rel.Substring(0, $rel.Length - 7)
                if (Test-Path -LiteralPath $target) { Write-Host "${verb}remove $(Rel $target) (did not exist before the first profile)"; if (-not $dry) { Remove-Item -LiteralPath $target -Force }; $n++ }
            } else {
                Write-Host "${verb}restore $rel"
                if (-not $dry) { Copy-Fresh $f.FullName (Join-Path $Instance $rel) }
                $n++
            }
        }
    }
    if (Test-Path -LiteralPath $aside) {
        foreach ($j in Get-ChildItem -LiteralPath $aside -File) {
            $dest = Join-Path $mods $j.Name
            if (Test-Path -LiteralPath $dest) { Write-Host "skip mods-aside\$($j.Name): mods\ already has one"; continue }
            Write-Host "${verb}move mods\$($j.Name)  <-  mods-aside\"
            if (-not $dry) { Move-Item -LiteralPath $j.FullName -Destination $dest }
            $n++
        }
    }
    if (-not $dry -and (Test-Path -LiteralPath $marker)) { Remove-Item -LiteralPath $marker -Force }
    if ($n -eq 0) { Write-Host "nothing to revert: no profile was applied here." }
    elseif ($dry) { Write-Host "(dry run: nothing written)" }
    else { Write-Host "Back on your own settings. _qf-profile\ keeps the backups; delete it if you like." }
    return
}

# ------------------------------------------------------------------ apply: plan
$profPath = Join-Path $here "profiles\$Profile.json"
$prof = Get-Content -LiteralPath $profPath -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "$($prof.title)  [$($prof.hardware)]"
Write-Host "client: $renderer   folder: $Instance"
if ($renderer -eq 'none') { Write-Host "warning: neither Angelica nor OptiFine in mods\; only options.txt and the jar list are applied." }

$plan = New-Object System.Collections.Generic.List[object]
$notes = @()
function Add-Plan([string]$rel, $result) {
    if ($result.changes.Count -eq 0) { return }
    $plan.Add([pscustomobject]@{ rel = $rel; lines = $result.lines; text = $result.text; changes = $result.changes })
}

# 1. options.txt
Add-Plan 'options.txt' (Set-KeyLines (Read-Lines (Join-Path $Instance 'options.txt')) $prof.options_txt ':')

$shaderState = 'off'
if ($renderer -eq 'angelica') {
    # 2. Celeritas settings
    $aoPath = Join-Path $Instance 'config\angelica-options.json'
    $json = if (Test-Path -LiteralPath $aoPath) { Get-Content -LiteralPath $aoPath -Raw | ConvertFrom-Json } else { $notes += "config\angelica-options.json did not exist (Angelica has not started here yet); it is created with the profile's keys and Angelica fills in the rest."; New-Object PSObject }
    $ch = @()
    Merge-Json $json $prof.angelica_options '' ([ref]$ch)
    Add-Plan 'config\angelica-options.json' @{ text = ($json | ConvertTo-Json -Depth 10); changes = $ch }

    # 3. Angelica module switches
    Add-Plan 'config\angelica-modules.cfg' (Set-CfgLines (Read-Lines (Join-Path $Instance 'config\angelica-modules.cfg')) $prof.angelica_modules)

    # 4. Shaders: config\shaders.properties (Iris reads this, never optionsshaders.txt) and the
    #    pack's own option file shaderpacks\<pack>.txt, where QF_PRESET lives.
    $pack = $prof.shaders.pack
    $packName = $null
    if (Test-Path -LiteralPath (Join-Path $Instance "shaderpacks\$pack") -PathType Container) { $packName = $pack }
    elseif (Test-Path -LiteralPath (Join-Path $Instance "shaderpacks\$pack.zip")) { $packName = "$pack.zip" }
    $sp = [ordered]@{}
    if ($Shaders -eq 'off') {
        $sp['enableShaders'] = 'false'; $notes += "shaders off (-Shaders off)."
    } elseif (-not $prof.shaders.enabled) {
        $sp['enableShaders'] = 'false'
    } elseif ($packName) {
        $sp['shaderPack'] = $packName; $sp['enableShaders'] = 'true'
        $shaderState = "$packName QF_PRESET=$($prof.shaders.options.QF_PRESET)"
        Add-Plan "shaderpacks\$packName.txt" (Set-KeyLines (Read-Lines (Join-Path $Instance "shaderpacks\$packName.txt")) $prof.shaders.options '=')
    } elseif ($prof.shaders.if_missing -eq 'off') {
        $sp['enableShaders'] = 'false'; $notes += "shader pack '$pack' is not in shaderpacks\: shaders turned off (the profile's if_missing rule)."
    } else {
        $notes += "shader pack '$pack' is not in shaderpacks\: the current shader choice is left alone (the profile's if_missing rule)."
        $shaderState = 'left as is'
    }
    if ($sp.Count) { Add-Plan 'config\shaders.properties' (Set-KeyLines (Read-Lines (Join-Path $Instance 'config\shaders.properties')) $sp '=') }
} elseif ($renderer -eq 'e7') {
    # OptiFine E7 fallback (GPUs without OpenGL 3.3): optionsof.txt and optionsshaders.txt.
    $of = Pairs $prof.optifine.optionsof_txt
    $sh = Pairs $prof.optifine.optionsshaders_txt
    if ($Shaders -eq 'off') { $sh['shaderPack'] = 'OFF' }
    $cur = @{}
    foreach ($l in Read-Lines (Join-Path $Instance 'optionsshaders.txt')) { $i = $l.IndexOf('='); if ($i -gt 0) { $cur[$l.Substring(0, $i)] = $l.Substring($i + 1) } }
    $packAfter = if ($sh.Contains('shaderPack')) { $sh['shaderPack'] } else { $cur['shaderPack'] }
    if ($packAfter -and $packAfter -ne 'OFF' -and "$($of['ofFastRender'])" -eq 'true') {
        # Fast Render breaks every shader pack on E7. Never leave both on.
        $of['ofFastRender'] = 'false'; $notes += "a shader pack ($packAfter) stays selected, so Fast Render is kept off."
    }
    if ($packAfter -and $packAfter -ne 'OFF') { $shaderState = $packAfter }
    if ($of.Count) { Add-Plan 'optionsof.txt' (Set-KeyLines (Read-Lines (Join-Path $Instance 'optionsof.txt')) $of ':') }
    if ($sh.Count) { Add-Plan 'optionsshaders.txt' (Set-KeyLines (Read-Lines (Join-Path $Instance 'optionsshaders.txt')) $sh '=') }
}

# 5. Client-only jars: the profile's prefixes go to mods-aside\, everything else comes home.
$prefixes = @($prof.mods_aside)
function Is-Aside([string]$name) {
    foreach ($p in $prefixes) { if ($name.StartsWith($p, [StringComparison]::OrdinalIgnoreCase)) { return $true } }
    return $false
}
$moves = @()
foreach ($j in Get-ChildItem -LiteralPath $mods -File | Where-Object { $_.Extension -match '^\.(jar|zip|litemod)$' }) {
    if (Is-Aside $j.Name) {
        $to = Join-Path $aside $j.Name
        if (Test-Path -LiteralPath $to) { $notes += "mods-aside\$($j.Name) already exists; mods\$($j.Name) left where it is." ; continue }
        $moves += @{ from = $j.FullName; to = $to; what = "mods\$($j.Name)  ->  mods-aside\" }
    }
}
if (Test-Path -LiteralPath $aside) {
    foreach ($j in Get-ChildItem -LiteralPath $aside -File) {
        if (-not (Is-Aside $j.Name)) {
            $to = Join-Path $mods $j.Name
            if (Test-Path -LiteralPath $to) { $notes += "mods\$($j.Name) already exists; mods-aside\$($j.Name) left where it is."; continue }
            $moves += @{ from = $j.FullName; to = $to; what = "mods\$($j.Name)  <-  mods-aside\" }
        }
    }
}

# ------------------------------------------------------------------ apply: show and commit
foreach ($item in $plan) {
    Write-Host "$($item.rel):"
    foreach ($c in $item.changes) { Write-Host "  $c" }
}
foreach ($m in $moves) { Write-Host "$($m.what)" }
foreach ($n in $notes) { Write-Host "note: $n" }

$prev = Read-Marker
$changed = ($plan.Count -gt 0) -or ($moves.Count -gt 0)
if (-not $changed) {
    Write-Host "already on the $Profile profile: nothing to change."
} elseif ($dry) {
    Write-Host "(dry run: nothing written)"
} else {
    $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = Join-Path $state "backup-$ts"
    foreach ($item in $plan) {
        $full = Join-Path $Instance $item.rel
        $o = Join-Path $orig $item.rel
        if (Test-Path -LiteralPath $full) {
            if (-not (Test-Path -LiteralPath $o) -and -not (Test-Path -LiteralPath "$o.absent")) { Copy-Fresh $full $o }
            Copy-Fresh $full (Join-Path $backup $item.rel)
        } elseif (-not (Test-Path -LiteralPath $o) -and -not (Test-Path -LiteralPath "$o.absent")) {
            Unlink "$o.absent"; [IO.File]::WriteAllText("$o.absent", "did not exist before the first profile was applied`n", $utf8)
        }
        Write-Fresh $full $item
    }
    foreach ($m in $moves) {
        if (-not (Test-Path -LiteralPath (Split-Path -Parent $m.to))) { New-Item -ItemType Directory -Path (Split-Path -Parent $m.to) -Force | Out-Null }
        Move-Item -LiteralPath $m.from -Destination $m.to
    }
    if ($plan.Count) { Write-Host "backups: $backup (this run) and $orig (your own settings, for -Revert)" }
}
if (-not $dry) {
    New-Item -ItemType Directory -Path $state -Force | Out-Null
    $info = [ordered]@{ profile = $Profile; shaders = $shaderState; renderer = $renderer; applied = (Get-Date -Format 's'); script = 'apply-profile.ps1 schema 1' }
    Unlink $marker; [IO.File]::WriteAllText($marker, ($info | ConvertTo-Json), $utf8)
}

# ------------------------------------------------------------------ Java memory for Prism
$ramGb = 0
try { $ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB) } catch { }
$rows = Pairs $prof.jvm.xmx_mb_by_ram_gb
$pick = $null
foreach ($k in ($rows.Keys | Sort-Object { [int]$_ })) { if ([int]$k -le [math]::Max($ramGb, 8)) { $pick = $k } }
if (-not $pick) { $pick = ($rows.Keys | Sort-Object { [int]$_ })[0] }
$xmx = $rows[$pick]; $xms = (Pairs $prof.jvm.xms_mb_by_ram_gb)[$pick]
Write-Host ""
if ($dry) { Write-Host "Dry run of the $Profile profile (shaders: $shaderState); nothing was written." }
else { Write-Host "Done: $Profile profile (shaders: $shaderState)." }
Write-Host "Java (Prism: Edit instance -> Settings -> Java), this PC has $ramGb GB RAM:"
if ($ramGb -gt 0 -and $ramGb -lt 8) { Write-Host "  warning: under 8 GB. The pack needs 8; close everything else and expect swapping." }
Write-Host "  Maximum memory: $xmx MiB    Minimum memory: $xms MiB    ($($prof.jvm.java))"
Write-Host "  Java arguments: $($prof.jvm.args)"
Write-Host "To go back: apply-profile.ps1 -Instance `"$Instance`" -Revert"

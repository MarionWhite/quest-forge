<#
.SYNOPSIS
  Switch a Quest Forge client instance to the LITE (or POTATO) profile, or back.

.DESCRIPTION
  Changes only two kinds of thing, both of which the server never sees:
    1. Video keys in options.txt, optionsof.txt and optionsshaders.txt.
       Keybinds, sound, chat, language and resource packs are left alone.
       On the Angelica client (mods\angelica-*.jar present) OptiFine's two
       files do not exist; its equivalents go into three client-only Angelica
       files under config\: angelica-options.json, angelica-modules.cfg and
       shaders.properties.
    2. Client-only mod jars listed in client-only-drop.txt are moved out of
       mods\ into mods-lite-removed\ (never deleted).
  The rest of config\ is never touched: the server and every client must
  share it. (The server has no Angelica, so its files are not shared.)

  The first run saves the options files to _lite-backup\ next to mods\.
  -Undo puts them back and moves the jars back.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File apply-lite.ps1 -Instance "C:\Users\me\AppData\Roaming\PrismLauncher\instances\Quest Forge\.minecraft"
  powershell -ExecutionPolicy Bypass -File apply-lite.ps1 -Instance "..." -Tier potato
  powershell -ExecutionPolicy Bypass -File apply-lite.ps1 -Instance "..." -Undo
  Add -WhatIf to see what would change without changing anything.
#>
param(
    [Parameter(Mandatory = $true)][string]$Instance,
    [ValidateSet('lite', 'potato')][string]$Tier = 'lite',
    [switch]$Undo,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Instance = (Resolve-Path $Instance).Path
$mods = Join-Path $Instance 'mods'
$removed = Join-Path $Instance 'mods-lite-removed'
$backup = Join-Path $Instance '_lite-backup'
$angelica = [bool](Get-ChildItem -LiteralPath $mods -Filter 'angelica-*.jar' -ErrorAction SilentlyContinue)
if ($angelica) {
    # OptiFine's optionsof.txt / optionsshaders.txt mean nothing to Angelica.
    $files = @(@{ n = 'options.txt'; sep = ':' })
    $angFiles = @('config\angelica-options.json', 'config\angelica-modules.cfg', 'config\shaders.properties')
} else {
    $files = @(@{ n = 'options.txt'; sep = ':' }, @{ n = 'optionsof.txt'; sep = ':' }, @{ n = 'optionsshaders.txt'; sep = '=' })
    $angFiles = @()
}

if (-not (Test-Path (Join-Path $mods 'OptiFine_1.7.10_HD_U_E7.jar')) -and -not $angelica -and -not (Test-Path (Join-Path $Instance 'options.txt'))) {
    throw "$Instance does not look like a Quest Forge game folder (no mods\OptiFine jar, no options.txt). Point -Instance at the folder that holds mods\ and options.txt."
}
# The game rewrites options.txt when it quits, so a change made while it runs is lost.
$running = Get-CimInstance Win32_Process -Filter "Name='java.exe' or Name='javaw.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*$Instance*" }
if ($running) { throw "Minecraft is running from this folder (pid $($running.ProcessId -join ', ')). Quit it first." }

function Read-Overrides([string]$path, [string]$sep) {
    $o = [ordered]@{}
    if (-not (Test-Path $path)) { return $o }
    foreach ($line in Get-Content -LiteralPath $path) {
        $t = $line.Trim()
        if ($t -eq '' -or $t.StartsWith('#')) { continue }
        $i = $t.IndexOf($sep)
        if ($i -lt 1) { continue }
        $o[$t.Substring(0, $i)] = $t.Substring($i + 1)
    }
    return $o
}

function Set-Keys([string]$target, [System.Collections.IDictionary]$keys, [string]$sep) {
    $lines = New-Object System.Collections.Generic.List[string]
    if (Test-Path $target) { foreach ($l in Get-Content -LiteralPath $target) { $lines.Add($l) } }
    foreach ($k in $keys.Keys) {
        $want = "$k$sep$($keys[$k])"
        $idx = -1
        for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].StartsWith("$k$sep")) { $idx = $i; break } }
        if ($idx -ge 0) {
            if ($lines[$idx] -ne $want) { Write-Host "  $($lines[$idx])  ->  $want"; $lines[$idx] = $want }
        } else { Write-Host "  + $want"; $lines.Add($want) }
    }
    if (-not $WhatIf) {
        # Minecraft reads these as plain ASCII/UTF-8 without a BOM.
        [System.IO.File]::WriteAllLines($target, $lines, (New-Object System.Text.UTF8Encoding($false)))
    }
}

# Angelica's own settings file is JSON: merge the profile's keys into it.
function Merge-Json($base, $over) {
    foreach ($p in $over.PSObject.Properties) {
        if ($p.Name -like '_*') { continue }
        $cur = $base.PSObject.Properties[$p.Name]
        if ($p.Value -is [System.Management.Automation.PSCustomObject] -and $cur -and $cur.Value -is [System.Management.Automation.PSCustomObject]) {
            Merge-Json $cur.Value $p.Value
        } elseif ($cur) {
            if ("$($cur.Value)" -ne "$($p.Value)") { Write-Host "  $($p.Name): $($cur.Value)  ->  $($p.Value)" }
            $cur.Value = $p.Value
        } else {
            Write-Host "  + $($p.Name): $($p.Value)"
            $base | Add-Member -NotePropertyName $p.Name -NotePropertyValue $p.Value
        }
    }
}

# Forge-style config (angelica-modules.cfg): replace B:/I:/S:/D: lines by key.
function Set-CfgKeys([string]$target, [string]$overlay) {
    $want = [ordered]@{}
    foreach ($l in Get-Content -LiteralPath $overlay) { if ($l -match '^\s*([BISD]:[\w"]+)=(.*)$') { $want[$Matches[1]] = $Matches[2] } }
    if (-not (Test-Path $target)) {
        Write-Host "  + new file with $($want.Keys -join ', ')"
        if (-not $WhatIf) { Copy-Item -LiteralPath $overlay -Destination $target }
        return
    }
    $lines = @(Get-Content -LiteralPath $target)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^(\s*)([BISD]:[\w"]+)=(.*)$' -and $want.Contains($Matches[2])) {
            $new = "$($Matches[1])$($Matches[2])=$($want[$Matches[2]])"
            if ($lines[$i] -ne $new) { Write-Host "  $($lines[$i].Trim())  ->  $($new.Trim())"; $lines[$i] = $new }
        }
    }
    if (-not $WhatIf) { [System.IO.File]::WriteAllLines($target, $lines, (New-Object System.Text.UTF8Encoding($false))) }
}

function Drop-List {
    $out = @()
    foreach ($line in Get-Content -LiteralPath (Join-Path $here 'client-only-drop.txt')) {
        $t = $line.Trim()
        if ($t -eq '' -or $t.StartsWith('#')) { continue }
        $p = $t -split "`t+|\s{2,}"
        $out += [pscustomobject]@{ tier = $p[0]; prefix = $p[1] }
    }
    return $out
}

if ($Undo) {
    foreach ($a in $angFiles) {
        $b = Join-Path $backup (Split-Path $a -Leaf)
        if (Test-Path $b) {
            Write-Host "restore $a"
            if (-not $WhatIf) { Copy-Item -LiteralPath $b -Destination (Join-Path $Instance $a) -Force }
        }
    }
    foreach ($f in $files) {
        $b = Join-Path $backup $f.n
        if (Test-Path $b) {
            Write-Host "restore $($f.n)"
            if (-not $WhatIf) { Copy-Item -LiteralPath $b -Destination (Join-Path $Instance $f.n) -Force }
        }
    }
    if (Test-Path $removed) {
        foreach ($j in Get-ChildItem -LiteralPath $removed -File) {
            Write-Host "mods\$($j.Name)  <-  mods-lite-removed\"
            if (-not $WhatIf) { Move-Item -LiteralPath $j.FullName -Destination $mods }
        }
    }
    Write-Host "Back to the full profile. (The _lite-backup folder is kept; delete it if you like.)"
    return
}

# 1. Back up once: the first backup is the player's own settings, never a lite state.
if (-not (Test-Path $backup)) {
    if (-not $WhatIf) { New-Item -ItemType Directory -Path $backup | Out-Null }
    foreach ($f in $files) {
        $s = Join-Path $Instance $f.n
        if ((Test-Path $s) -and -not $WhatIf) { Copy-Item -LiteralPath $s -Destination $backup }
    }
    foreach ($a in $angFiles) {
        $s = Join-Path $Instance $a
        if ((Test-Path $s) -and -not $WhatIf) { Copy-Item -LiteralPath $s -Destination $backup }
    }
    Write-Host "saved your current settings to $backup"
}

# 2. Options: lite first, then potato on top.
$tiers = @('lite'); if ($Tier -eq 'potato') { $tiers += 'potato' }
foreach ($f in $files) {
    $keys = [ordered]@{}
    foreach ($t in $tiers) {
        $o = Read-Overrides (Join-Path $here "profiles\$t\$($f.n)") $f.sep
        foreach ($k in $o.Keys) { $keys[$k] = $o[$k] }
    }
    if ($keys.Count -eq 0) { continue }
    Write-Host "$($f.n):"
    Set-Keys (Join-Path $Instance $f.n) $keys $f.sep
}

# Angelica: its settings JSON, its module switches, and no shader pack.
if ($angelica) {
    $cfg = Join-Path $Instance 'config'
    $ao = Join-Path $cfg 'angelica-options.json'
    $json = if (Test-Path $ao) { Get-Content -LiteralPath $ao -Raw | ConvertFrom-Json } else { New-Object PSObject }
    Write-Host "config\angelica-options.json:"
    foreach ($t in $tiers) {
        $p = Join-Path $here "profiles\$t\angelica-options.json"
        if (Test-Path $p) { Merge-Json $json (Get-Content -LiteralPath $p -Raw | ConvertFrom-Json) }
    }
    if (-not $WhatIf) {
        [System.IO.File]::WriteAllText($ao, ($json | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding($false)))
    }
    foreach ($t in $tiers) {
        $p = Join-Path $here "profiles\$t\angelica-modules.cfg"
        if (Test-Path $p) { Write-Host "config\angelica-modules.cfg:"; Set-CfgKeys (Join-Path $cfg 'angelica-modules.cfg') $p }
    }
    Write-Host "config\shaders.properties:"
    Set-Keys (Join-Path $cfg 'shaders.properties') ([ordered]@{ enableShaders = 'false' }) '='
}

# Fast Render breaks every shader pack on OptiFine E7. Never leave both on.
$sh = Read-Overrides (Join-Path $Instance 'optionsshaders.txt') '='
if (-not $angelica -and $sh['shaderPack'] -and $sh['shaderPack'] -ne 'OFF' -and -not $WhatIf) {
    Write-Host "a shader pack is still selected; turning Fast Render back off"
    Set-Keys (Join-Path $Instance 'optionsof.txt') ([ordered]@{ ofFastRender = 'false' }) ':'
}

# 3. Client-only jars out of mods\.
$drop = Drop-List | Where-Object { $tiers -contains $_.tier }
foreach ($d in $drop) {
    foreach ($j in Get-ChildItem -LiteralPath $mods -File | Where-Object { $_.Name.StartsWith($d.prefix, [StringComparison]::OrdinalIgnoreCase) -and $_.Name -match '\.(jar|zip)$' }) {
        Write-Host "mods\$($j.Name)  ->  mods-lite-removed\"
        if (-not $WhatIf) {
            if (-not (Test-Path $removed)) { New-Item -ItemType Directory -Path $removed | Out-Null }
            Move-Item -LiteralPath $j.FullName -Destination $removed
        }
    }
}
Write-Host ""
Write-Host "Done: $Tier profile. Set the Java memory as README.md says, then start the game."
Write-Host "To go back: apply-lite.ps1 -Instance `"$Instance`" -Undo"

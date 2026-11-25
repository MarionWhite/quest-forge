<#
  apply-lite.ps1 is superseded by apply-profile.ps1 (2026-10-25), which reads the profile
  definitions in profiles\*.json and also knows the Angelica client's own settings and the
  QuestForge shader presets. This stub keeps the old command line working:
    -Tier lite|potato  ->  -Profile lite|potato
    -Undo              ->  -Revert
#>
param(
    [Parameter(Mandatory = $true)][string]$Instance,
    [ValidateSet('lite', 'potato')][string]$Tier = 'lite',
    [switch]$Undo,
    [switch]$WhatIf
)
$fwd = @('-Instance', $Instance, '-Profile', $Tier)
if ($Undo) { $fwd += '-Revert' }
if ($WhatIf) { $fwd += '-WhatIf' }
Write-Host "apply-lite.ps1 is now apply-profile.ps1; running it with: $($fwd -join ' ')"
& (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'apply-profile.ps1') @fwd

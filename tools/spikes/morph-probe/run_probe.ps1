param([Parameter(Mandatory)] [string]$Tag, [int]$TimeoutMin = 15)
# Throwaway Morph repro client in C:\qfm\client. Reads bin\ and assets\ from the
# live instance, never writes to it.
$ErrorActionPreference = 'Stop'
$live = "$env:APPDATA\.crazycraft4"
$c = "C:\qfm\client"

# One client at a time: a second full-pack client resets the GPU driver.
$clients = Get-CimInstance Win32_Process -Filter "Name like '%java%'" |
    Where-Object { $_.CommandLine -like '*launchwrapper*' }
if ($clients) { throw "A Minecraft client is already running (pid $($clients.ProcessId -join ',')); not launching." }

Remove-Item "$c\morphprobe.log" -ErrorAction SilentlyContinue
$java = "C:\Program Files\Java\jre1.8.0_241\bin\java.exe"
$cp = @("$live\bin\minecraft.jar") + (Get-ChildItem "$live\bin\lib\*.jar" | ForEach-Object FullName)
$jargs = @(
    '-Djava.net.preferIPv4Stack=true', '-Dfml.ignoreInvalidMinecraftCertificates=true',
    '-Dfml.ignorePatchDiscrepancies=true', '-Dlog4j2.formatMsgNoLookups=true',
    "-Dlog4j.configurationFile=$c\log4j2_17-111.xml",
    "-Djava.library.path=$live\bin\natives",
    '-Xms2048M', '-Xmx7168M', '-XX:MaxPermSize=256M',
    '-XX:+UseG1GC', '-XX:MaxGCPauseMillis=50', '-XX:G1HeapRegionSize=16M',
    '-XX:ParallelGCThreads=6', '-XX:ConcGCThreads=2',
    '-XX:+UseSplitVerifier', '-XX:+FailOverToOldVerifier',
    '-XX:-HeapDumpOnOutOfMemoryError', '-XX:+UseCompressedOops', '-XX:+DisableExplicitGC',
    '-XX:-OmitStackTraceInFastThrow',
    '-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=127.0.0.1:5005',
    '-cp', ($cp -join ';'),
    'net.minecraft.launchwrapper.Launch',
    '--username', 'Dev', '--accessToken', '0', '--uuid', '00000000-0000-0000-0000-000000000000',
    '--version', '1.7.10', '--assetIndex', '1.7.10',
    '--tweakClass', 'cpw.mods.fml.common.launcher.FMLTweaker',
    '--gameDir', $c, '--assetsDir', "$live\assets",
    '--width', '1920', '--height', '1080', '--userProperties', '{}')

Add-Type -Namespace W -Name U -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
'@

$p = Start-Process -FilePath $java -ArgumentList $jargs -WorkingDirectory $c -PassThru `
    -RedirectStandardOutput "$c\logs\stdout-$Tag.txt" -RedirectStandardError "$c\logs\stderr-$Tag.txt"
Write-Output "pid $($p.Id)"
$end = (Get-Date).AddMinutes($TimeoutMin)
while (-not $p.HasExited -and (Get-Date) -lt $end) {
    $p.Refresh()
    if ($p.MainWindowHandle -ne [IntPtr]::Zero -and [W.U]::IsIconic($p.MainWindowHandle)) {
        [W.U]::ShowWindow($p.MainWindowHandle, 4) | Out-Null   # SW_SHOWNOACTIVATE
    }
    Start-Sleep -Seconds 2
}
if (-not $p.HasExited) { Write-Output "TIMEOUT - killing client"; Stop-Process -Id $p.Id -Force }
Write-Output "exit: $($p.ExitCode)"

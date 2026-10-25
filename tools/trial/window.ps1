<#
Window helper for tools/trial/trial.py (background client launches).

  window.ps1 -Mode hide -ProcessId N [-FastSeconds 40]
      Keeps every top-level window of process N off every monitor until N exits:
      not minimized (a minimized LWJGL client stalls), moved left of the virtual
      screen, WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE added and WS_EX_APPWINDOW removed
      (no taskbar button, no Alt-Tab entry, never takes focus), and its taskbar tab
      deleted. Never calls SetForegroundWindow and never shows with an activating
      flag (all calls async: the splash leaves the window unpumped). Until the move
      lands it is veiled (layered, alpha 0, click-through). Polls every 10 ms for the first FastSeconds (the splash, then the main
      window), then every second for the life of the process, because LWJGL may
      recreate or reposition the window (F11, a display-mode change); every poll re-asserts
      the styles and keeps the window at the bottom of the z-order.
      FOCUS GUARD (2026-10-25): every 50 ms for the whole life of the process it checks the
      foreground window. If it is ours, focus goes straight back to the window the owner had
      (AttachThreadInput + SetForegroundWindow), and the event is appended to focus.log next
      to -Log, which trial.py, bench_round.py and renderq read as a failure. LWJGL 2.9.1 calls
      SetForegroundWindow itself (WindowsDisplay.createWindow, and appActivate on every
      activation), and Windows grants it once the owner has not typed for the foreground lock
      timeout: on 2026-10-25 r007's qp, off8p, qpb0 and offpb clients were the foreground window
      in 1 to 4 of their userbusy samples, twice taking it from the owner's Cursor window.
  window.ps1 -Mode inspect -ProcessId N     JSON: that process's windows (read only)
  window.ps1 -Mode foreground               JSON: the foreground window (read only)
  window.ps1 -Mode userbusy [-OurPids 1,2]  JSON: is the owner gaming? (read only)
#>
param(
    [ValidateSet("hide", "inspect", "foreground", "userbusy")] [string]$Mode = "inspect",
    [int]$ProcessId = 0,
    [int]$FastSeconds = 40,
    [int[]]$OurPids = @(),
    [string]$Log = ""
)
$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

namespace QF {
  [ComImport, Guid("56FDF342-FD6D-11d0-958A-006097C9A090"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface ITaskbarList {
    void HrInit();
    void AddTab(IntPtr hwnd);
    void DeleteTab(IntPtr hwnd);
    void ActivateTab(IntPtr hwnd);
    void SetActiveAlt(IntPtr hwnd);
  }
  [ComImport, Guid("56FDF344-FD6D-11d0-958A-006097C9A090")] class TaskbarList { }

  public static class Win {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [StructLayout(LayoutKind.Sequential)] public struct MONITORINFO { public int cbSize; public RECT rcMonitor, rcWork; public int dwFlags; }

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongPtrW")] public static extern IntPtr GetLong(IntPtr h, int i);
    [DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW")] public static extern IntPtr SetLong(IntPtr h, int i, IntPtr v);
    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h, uint cmd);
    [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr h, uint f);
    [DllImport("user32.dll")] public static extern bool GetMonitorInfo(IntPtr m, ref MONITORINFO mi);
    [DllImport("user32.dll")] public static extern IntPtr GetShellWindow();
    [DllImport("user32.dll")] public static extern IntPtr GetDesktopWindow();
    [DllImport("shell32.dll")] public static extern int SHQueryUserNotificationState(out int state);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool attach);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern IntPtr FindWindow(string cls, string title);
    public static readonly IntPtr HWND_BOTTOM = new IntPtr(1);

    // Our window is the foreground window: hand the foreground back to `prev` (the owner's last
    // window), or to the taskbar if that is gone. A background process may not call
    // SetForegroundWindow, but one attached to the foreground thread's input may.
    public static string GiveBack(IntPtr ours, IntPtr prev) {
      IntPtr target = (prev != IntPtr.Zero && IsWindow(prev) && IsWindowVisible(prev)) ? prev : FindWindow("Shell_TrayWnd", null);
      uint pid; uint fgThread = GetWindowThreadProcessId(ours, out pid);
      uint me = GetCurrentThreadId();
      bool att = AttachThreadInput(me, fgThread, true);
      bool ok = SetForegroundWindow(target);
      if (att) AttachThreadInput(me, fgThread, false);
      // Push ours to the bottom so Windows never picks it as the next window to activate.
      SetWindowPos(ours, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOSIZE | 0x2 /*NOMOVE*/ | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS);
      bool back = GetForegroundWindow() != ours;
      return "returned focus to hwnd " + target.ToInt64() + " '" + Title(target) + "' (" + Class(target) + "): "
             + (back ? "ok" : "STILL OURS") + (ok ? "" : " (SetForegroundWindow refused)");
    }

    public const int GWL_EXSTYLE = -20;
    public const long WS_EX_TOOLWINDOW = 0x80, WS_EX_APPWINDOW = 0x40000, WS_EX_NOACTIVATE = 0x8000000;
    public const uint SWP_NOSIZE = 0x1, SWP_NOZORDER = 0x4, SWP_NOACTIVATE = 0x10, SWP_FRAMECHANGED = 0x20,
                      SWP_NOOWNERZORDER = 0x200;
    public const int SW_SHOWNOACTIVATE = 4;
    public const long WS_EX_LAYERED = 0x80000, WS_EX_TRANSPARENT = 0x20;
    public const uint SWP_ASYNCWINDOWPOS = 0x4000, SWP_SHOWWINDOW = 0x40, LWA_ALPHA = 0x2;
    [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool SetLayeredWindowAttributes(IntPtr h, uint key, byte alpha, uint flags);
    static HashSet<long> veiled = new HashSet<long>();
    static Dictionary<long, DateTime> asked = new Dictionary<long, DateTime>();

    public static List<IntPtr> WindowsOf(uint pid) {
      var list = new List<IntPtr>();
      EnumWindows((h, l) => {
        uint p; GetWindowThreadProcessId(h, out p);
        if (p == pid) list.Add(h);
        return true;
      }, IntPtr.Zero);
      return list;
    }
    public static string Class(IntPtr h) { var s = new StringBuilder(256); GetClassName(h, s, 256); return s.ToString(); }
    public static string Title(IntPtr h) { var s = new StringBuilder(256); GetWindowText(h, s, 256); return s.ToString(); }
    public static uint Pid(IntPtr h) { uint p; GetWindowThreadProcessId(h, out p); return p; }

    static ITaskbarList taskbar;
    static void DeleteTab(IntPtr h) {
      try {
        if (taskbar == null) { taskbar = (ITaskbarList)new TaskbarList(); taskbar.HrInit(); }
        taskbar.DeleteTab(h);
      } catch (Exception) { }
    }

    // Keep one window off-screen, unfocusable and out of the taskbar. Returns what it changed.
    public static string Banish(IntPtr h) {
      // The game window is class LWJGL. trial.py starts the JVM hidden (STARTUPINFO SW_HIDE),
      // so LWJGL's first ShowWindow leaves it hidden; it is shown here, off-screen, with no
      // activation. Other hidden windows (wgl dummies, D3DFocusWindow, AWT, IME) and the
      // zero-size ConPTY PseudoConsoleWindow: leave alone.
      bool game = Class(h) == "LWJGL";
      bool hidden = !IsWindowVisible(h) && !IsIconic(h);
      if (hidden && !game) return null;
      if (Class(h) == "PseudoConsoleWindow") return null;
      RECT r0; GetWindowRect(h, out r0);
      if (!IsIconic(h) && (r0.R - r0.L <= 0 || r0.B - r0.T <= 0)) return null;
      var did = new List<string>();
      // Async: the client's main thread pumps no messages while Forge loads mods behind
      // the splash, so a synchronous ShowWindow/SetWindowPos blocks until it does -- 9.6 s
      // on screen in the 2026-10-23 test. Window styles and layered alpha apply at once.
      if (IsIconic(h)) { ShowWindowAsync(h, SW_SHOWNOACTIVATE); did.Add("restored"); }
      RECT r; GetWindowRect(h, out r);
      int w = r.R - r.L, vx = GetSystemMetrics(76), vy = GetSystemMetrics(77);
      int x = vx - w - 100;
      bool off = r.R <= vx;
      long ex = GetLong(h, GWL_EXSTYLE).ToInt64();
      long want = (ex | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE) & ~WS_EX_APPWINDOW;
      // Until the move lands, the window is veiled: layered at alpha 0 and click-through,
      // so it is invisible where it is. Unveiled once it is off-screen, so the game renders
      // through the normal (non-layered) path.
      bool veil = !off && !veiled.Contains(h.ToInt64());
      if (veil) want |= WS_EX_LAYERED | WS_EX_TRANSPARENT;
      bool unveil = off && veiled.Contains(h.ToInt64());
      if (unveil) want &= ~(WS_EX_LAYERED | WS_EX_TRANSPARENT);
      uint frame = 0;
      if (want != ex) {
        SetLong(h, GWL_EXSTYLE, new IntPtr(want)); frame = SWP_FRAMECHANGED; did.Add("exstyle");
        if ((ex & WS_EX_APPWINDOW) != 0 || (ex & WS_EX_TOOLWINDOW) == 0) DeleteTab(h);
      }
      if (veil) { SetLayeredWindowAttributes(h, 0, 0, LWA_ALPHA); veiled.Add(h.ToInt64()); did.Add("veiled"); }
      if (unveil) { veiled.Remove(h.ToInt64()); did.Add("unveiled"); }
      DateTime last;
      bool due = veil || frame != 0 || !asked.TryGetValue(h.ToInt64(), out last) || (DateTime.Now - last).TotalSeconds > 1;
      if (((!off || hidden) && due) || frame != 0) {
        asked[h.ToInt64()] = DateTime.Now;
        // For a hidden window, SWP_SHOWWINDOW makes the move and the show one queued
        // message, so it can only become visible already off-screen.
        // Bottom of the z-order (not NOZORDER): the window Windows activates when the owner's
        // window closes or minimizes is the next one down, never ours.
        SetWindowPos(h, HWND_BOTTOM, off ? r.L : x, off ? r.T : vy, 0, 0,
                     SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_ASYNCWINDOWPOS | frame
                     | (hidden ? SWP_SHOWWINDOW : 0));
        if (!off) did.Add("move requested from " + r.L + "," + r.T);
        if (hidden) { ShowWindowAsync(h, SW_SHOWNOACTIVATE); did.Add("show (no activate) requested"); }
      }
      return did.Count == 0 ? null : string.Join(" ", did.ToArray());
    }

    // Does this window cover the whole monitor it is on (borderless or exclusive fullscreen)?
    public static bool CoversMonitor(IntPtr h, out string mon) {
      mon = "";
      RECT r; if (!GetWindowRect(h, out r)) return false;
      IntPtr m = MonitorFromWindow(h, 2 /* NEAREST */);
      var mi = new MONITORINFO(); mi.cbSize = Marshal.SizeOf(typeof(MONITORINFO));
      if (!GetMonitorInfo(m, ref mi)) return false;
      mon = (mi.rcMonitor.R - mi.rcMonitor.L) + "x" + (mi.rcMonitor.B - mi.rcMonitor.T);
      return r.L <= mi.rcMonitor.L && r.T <= mi.rcMonitor.T && r.R >= mi.rcMonitor.R && r.B >= mi.rcMonitor.B;
    }
  }
}
'@

function Describe([IntPtr]$h) {
    $r = New-Object QF.Win+RECT
    [void][QF.Win]::GetWindowRect($h, [ref]$r)
    [ordered]@{
        hwnd = $h.ToInt64(); pid = [QF.Win]::Pid($h); class = [QF.Win]::Class($h); title = [QF.Win]::Title($h)
        visible = [QF.Win]::IsWindowVisible($h); iconic = [QF.Win]::IsIconic($h)
        rect = @($r.L, $r.T, $r.R, $r.B)
        exstyle = ('0x{0:X}' -f [QF.Win]::GetLong($h, -20).ToInt64())
    }
}

function Write-Log($msg) {
    if ($Log) { Add-Content -LiteralPath $Log -Value ("{0:HH:mm:ss.fff} {1}" -f (Get-Date), $msg) }
}

# Install folders of the game stores: an exe under one of these is a game.
$GamePaths = '\\steamapps\\common\\|\\Epic Games\\|\\Riot Games\\|\\GOG Galaxy\\Games\\|\\XboxGames\\|\\Battle\.net\\|\\Ubisoft Game Launcher\\games\\|\\EA Games\\'

switch ($Mode) {
    "hide" {
        $t0 = Get-Date
        $focusLog = if ($Log) { Join-Path (Split-Path -Parent $Log) "focus.log" } else { "" }
        Write-Log "hide: watching pid $ProcessId"
        $prev = [QF.Win]::GetForegroundWindow()
        if ([QF.Win]::Pid($prev) -eq [uint32]$ProcessId) { $prev = [IntPtr]::Zero }
        $checks = 0; $stolen = 0; $lastBanish = [DateTime]::MinValue; $lastAlive = [DateTime]::MinValue
        while ($true) {
            $now = Get-Date
            if (($now - $lastAlive).TotalMilliseconds -ge 1000) {
                $lastAlive = $now
                if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { break }
            }
            $fast = ($now - $t0).TotalSeconds -lt $FastSeconds
            if ($fast -or ($now - $lastBanish).TotalMilliseconds -ge 1000) {
                $lastBanish = $now
                foreach ($h in [QF.Win]::WindowsOf([uint32]$ProcessId)) {
                    $did = [QF.Win]::Banish($h)
                    if ($did) { Write-Log ("hwnd {0} {1} '{2}': {3}" -f $h, [QF.Win]::Class($h), [QF.Win]::Title($h), $did) }
                }
            }
            # Focus guard, every pass (10 ms early, 50 ms after).
            $checks++
            $fg = [QF.Win]::GetForegroundWindow()
            if ($fg -ne [IntPtr]::Zero) {
                if ([QF.Win]::Pid($fg) -eq [uint32]$ProcessId) {
                    $stolen++
                    $what = [QF.Win]::GiveBack($fg, $prev)
                    $line = "FOCUS: our window hwnd $fg '$([QF.Win]::Title($fg))' was the foreground window; $what"
                    Write-Log $line
                    if ($focusLog) { Add-Content -LiteralPath $focusLog -Value ("{0:yyyy-MM-dd HH:mm:ss.fff} pid {1} {2}" -f (Get-Date), $ProcessId, $line) }
                } else {
                    $prev = $fg
                }
            }
            if ($fast) { Start-Sleep -Milliseconds 10 } else { Start-Sleep -Milliseconds 50 }
        }
        Write-Log "hide: pid $ProcessId exited; $checks foreground checks, ours $stolen times"
    }
    "inspect" {
        $rows = @([QF.Win]::WindowsOf([uint32]$ProcessId) | ForEach-Object { Describe $_ })
        ConvertTo-Json -InputObject $rows -Compress
    }
    "foreground" {
        $h = [QF.Win]::GetForegroundWindow()
        if ($h -eq [IntPtr]::Zero) { '{"hwnd":0}' } else { ConvertTo-Json -InputObject (Describe $h) -Compress }
    }
    "userbusy" {
        $reasons = New-Object System.Collections.ArrayList
        $fg = [QF.Win]::GetForegroundWindow()
        $fgInfo = $null
        if ($fg -ne [IntPtr]::Zero) {
            $fgPid = [QF.Win]::Pid($fg)
            $cls = [QF.Win]::Class($fg)
            $proc = Get-Process -Id $fgPid -ErrorAction SilentlyContinue
            $exe = if ($proc) { $proc.ProcessName } else { "" }
            $path = ""; try { $path = $proc.Path } catch { }
            $mon = ""
            $full = [QF.Win]::CoversMonitor($fg, [ref]$mon)
            $fgInfo = [ordered]@{ pid = $fgPid; exe = $exe; title = [QF.Win]::Title($fg); class = $cls; fullscreen = $full; monitor = $mon }
            # The lock and sign-in screens are fullscreen but mean the owner is away (2026-10-25:
            # LockApp after the 7:00 wake held a shader round for 3 h).
            $shell = $fg -eq [QF.Win]::GetShellWindow() -or $cls -in @("Progman", "WorkerW", "Shell_TrayWnd") -or
                     $exe -in @("LockApp", "LogonUI")
            $ours = $OurPids -contains [int]$fgPid
            if ($full -and -not $shell -and -not $ours) { [void]$reasons.Add("foreground '$exe' covers its $mon monitor") }
            if (-not $ours -and $path -match $GamePaths) {
                [void]$reasons.Add("foreground '$exe' is a game ($path)")
            }
        }
        $state = 0
        [void][QF.Win]::SHQueryUserNotificationState([ref]$state)
        # 2 QUNS_BUSY (fullscreen app), 3 QUNS_RUNNING_D3D_FULL_SCREEN, 4 QUNS_PRESENTATION_MODE
        if ($state -in 2, 3, 4) { [void]$reasons.Add("Windows notification state $state (fullscreen app / D3D exclusive / presentation)") }
        # GPU 3D engine load per process (Windows GPU performance counters), others than ours and dwm.
        $gpu = @()
        try {
            $samples = (Get-Counter '\GPU Engine(*engtype_3D)\Utilization Percentage' -ErrorAction Stop).CounterSamples
            $byPid = @{}
            foreach ($s in $samples) {
                if ($s.InstanceName -match 'pid_(\d+)_') { $k = [int]$Matches[1]; $byPid[$k] = [double]$byPid[$k] + $s.CookedValue }
            }
            foreach ($k in $byPid.Keys) {
                if ($byPid[$k] -lt 5) { continue }
                $gp = Get-Process -Id $k -ErrorAction SilentlyContinue
                $pn = if ($gp) { $gp.ProcessName } else { "" }
                $pp = ""; try { $pp = $gp.Path } catch { }
                $gpu += [ordered]@{ pid = $k; exe = $pn; pct = [math]::Round($byPid[$k], 1) }
                if (($OurPids -contains $k) -or $pn -eq "dwm") { continue }
                if ($byPid[$k] -ge 40) {
                    [void]$reasons.Add("'$pn' (pid $k) uses $([math]::Round($byPid[$k]))% of the GPU 3D engine")
                } elseif ($pp -match $GamePaths) {
                    # A game left running behind other windows still renders and shares the GPU.
                    [void]$reasons.Add("game '$pn' (pid $k) is running, $([math]::Round($byPid[$k]))% of the GPU 3D engine")
                }
            }
        } catch { }
        $out = [ordered]@{ busy = ($reasons.Count -gt 0); reasons = @($reasons); foreground = $fgInfo; notification_state = $state; gpu3d = @($gpu | Sort-Object { -$_.pct }) }
        ConvertTo-Json -InputObject $out -Compress -Depth 4
    }
}

# Lists top-level windows of the Unreal Editor process (title, class, state, rect, z-order index).
# Usage: powershell -File win.ps1 [-Restore]   (-Restore: un-minimise the main window behind everything, no focus)
param([switch]$Restore, [switch]$OffScreen, [switch]$Minimize)
Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class UEWin {
 public delegate bool EnumProc(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 public static List<string> List(uint pid) {
  var o = new List<string>(); int z = 0;
  EnumWindows((h, l) => { z++; uint p; GetWindowThreadProcessId(h, out p);
   if (p == pid && IsWindowVisible(h)) { var sb = new StringBuilder(256); GetWindowText(h, sb, 256); var cn = new StringBuilder(256); GetClassName(h, cn, 256);
    RECT r; GetWindowRect(h, out r);
    o.Add("z=" + z + " '" + sb + "' class=" + cn + " iconic=" + IsIconic(h) + " enabled=" + IsWindowEnabled(h) + " rect=" + r.L + "," + r.T + " " + (r.R - r.L) + "x" + (r.B - r.T)); }
   return true; }, IntPtr.Zero);
  return o; }
}
"@
$p = Get-Process UnrealEditor -ErrorAction SilentlyContinue
if (-not $p) { "UnrealEditor is not running"; exit }
if ($Restore) {
  $h = $p.MainWindowHandle; $bottom = [IntPtr]1; $flags = 0x0013
  if ([UEWin]::IsIconic($h)) {
    [void][UEWin]::SetWindowPos($h, $bottom, 0, 0, 0, 0, $flags)
    [void][UEWin]::ShowWindowAsync($h, 4)
    Start-Sleep -Milliseconds 800
    [void][UEWin]::SetWindowPos($h, $bottom, 0, 0, 0, 0, $flags)
    "restored behind other windows"
  } else { "main window is not minimised" }
}
if ($OffScreen) {
  # un-minimise without focus and park the window beyond the right edge of the screen: Slate draws it, the user does not see it
  $h = $p.MainWindowHandle
  [void][UEWin]::SetWindowPos($h, [IntPtr]1, 0, 0, 0, 0, 0x0013)
  [void][UEWin]::ShowWindowAsync($h, 4)
  Start-Sleep -Milliseconds 600
  [void][UEWin]::SetWindowPos($h, [IntPtr]1, 2400, 0, 1280, 800, 0x0010)
  Start-Sleep -Milliseconds 300
  "parked off-screen"
}
if ($Minimize) { [void][UEWin]::ShowWindowAsync($p.MainWindowHandle, 7); "minimised (no focus change)" }
[UEWin]::List([uint32]$p.Id)

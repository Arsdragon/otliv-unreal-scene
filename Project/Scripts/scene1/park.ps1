# Waits for the Unreal Editor main window and parks it beyond the right edge of the screen without taking focus
# (the editor must not be minimised: a minimised editor does not render, so screenshots never arrive).
param([int]$TimeoutMin = 40)
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class UEPark {
 public delegate bool EnumProc(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
 public static IntPtr Find(uint pid) { IntPtr r = IntPtr.Zero;
  EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p);
   if (p == pid && IsWindowVisible(h)) { var sb = new StringBuilder(256); GetWindowText(h, sb, 256); if (sb.ToString().Contains("Unreal Editor")) { r = h; return false; } }
   return true; }, IntPtr.Zero); return r; }
}
"@
$deadline = (Get-Date).AddMinutes($TimeoutMin)
while ((Get-Date) -lt $deadline) {
  $p = Get-Process UnrealEditor -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $p) { Start-Sleep -Seconds 2; continue }
  $h = [UEPark]::Find([uint32]$p.Id)
  if ($h -ne [IntPtr]::Zero) {
    if ([UEPark]::IsIconic($h) -or [UEPark]::IsZoomed($h)) { [void][UEPark]::ShowWindowAsync($h, 4); Start-Sleep -Milliseconds 500 }
    [void][UEPark]::SetWindowPos($h, [IntPtr]1, 2400, 0, 1280, 800, 0x0010)
    Start-Sleep -Milliseconds 700
    [void][UEPark]::SetWindowPos($h, [IntPtr]1, 2400, 0, 1280, 800, 0x0010)
    "parked at $(Get-Date -Format HH:mm:ss)"; exit 0
  }
  Start-Sleep -Milliseconds 700
}
"timeout: editor window not found"

# Starts the packed scene in a small window, waits, shoots the window, closes it. Result: Review\scene1\rt_check\game_*.png
param([int]$Wait = 75, [string]$Out = 'C:\UnrealScenes\Review\scene1\rt_check')
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; } }
'@
$env:HTTP_PROXY = ''; $env:HTTPS_PROXY = ''
$p = Start-Process 'C:\UnrealScenes\Build\Windows\Scenes.exe' -ArgumentList '-windowed', '-ResX=960', '-ResY=540' -PassThru
$shots = @()
foreach ($k in 1..2) {
    Start-Sleep -Seconds ($Wait / 2)
    $g = Get-Process -Name 'Scenes*', 'UnrealGame*' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if (-not $g) { Write-Output "no game window after $($k * $Wait / 2) s"; continue }
    $r = New-Object W+RECT; [void][W]::GetWindowRect($g.MainWindowHandle, [ref]$r)
    $bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
    $gr = [System.Drawing.Graphics]::FromImage($bmp); $gr.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
    $f = Join-Path $Out ("game_{0}s.png" -f ($k * $Wait / 2)); $bmp.Save($f); $shots += $f
    Write-Output ("{0}: '{1}' {2}x{3}, memory {4} MB, responding {5}" -f $f, $g.MainWindowTitle, $bmp.Width, $bmp.Height, [int]($g.WorkingSet64 / 1MB), $g.Responding)
}
Get-Process -Name 'Scenes*', 'UnrealGame*' -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Output "closed; exit of launcher: $($p.HasExited)"

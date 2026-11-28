# Full run of the packed scene: window 960x540, shots at given seconds, a mouse move test, checks that the game keeps
# responding all the way to the end, then closes it. Result: Review\scene1\rt_check\full_<s>.png and lines on stdout.
param([int[]]$At = @(40, 46, 120, 240, 380, 420, 470, 520, 556), [int]$MouseAt = 42, [string]$Out = 'C:\UnrealScenes\Review\scene1\rt_check')
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W {
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint d, UIntPtr e);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; } }
'@
$env:HTTP_PROXY = ''; $env:HTTPS_PROXY = ''
$p = Start-Process 'C:\UnrealScenes\Build\Windows\Scenes.exe' -ArgumentList '-windowed', '-ResX=960', '-ResY=540' -PassThru
$t0 = Get-Date; $moved = $false; $bad = 0
function Get-Game { Get-Process -Name 'Scenes*' -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1 }
foreach ($s in $At) {
    while (((Get-Date) - $t0).TotalSeconds -lt $s) {
        Start-Sleep -Milliseconds 500
        $g = Get-Game
        if (-not $g) { Write-Output ("{0:N0} s: no game window" -f ((Get-Date) - $t0).TotalSeconds); $bad++; Start-Sleep 5; continue }
        if (-not $moved -and ((Get-Date) - $t0).TotalSeconds -ge $MouseAt) {
            [void][W]::SetForegroundWindow($g.MainWindowHandle); Start-Sleep -Milliseconds 300
            foreach ($k in 1..20) { [W]::mouse_event(1, 30, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 15 }      # 600 counts to the right
            $moved = $true; Write-Output ("{0:N0} s: mouse moved 600 counts right" -f ((Get-Date) - $t0).TotalSeconds)
        }
    }
    $g = Get-Game
    if (-not $g) { Write-Output "$s s: game is gone"; $bad++; continue }
    [void][W]::SetForegroundWindow($g.MainWindowHandle); Start-Sleep -Milliseconds 200
    $r = New-Object W+RECT; [void][W]::GetWindowRect($g.MainWindowHandle, [ref]$r)
    $bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
    $gr = [System.Drawing.Graphics]::FromImage($bmp); $gr.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
    $f = Join-Path $Out ("full_{0:D3}.png" -f $s); $bmp.Save($f)
    Write-Output ("{0} s: responding {1}, memory {2} MB -> {3}" -f $s, $g.Responding, [int]($g.WorkingSet64 / 1MB), $f)
}
Get-Process -Name 'Scenes*' -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Output "closed after $([int]((Get-Date) - $t0).TotalSeconds) s; problems: $bad"

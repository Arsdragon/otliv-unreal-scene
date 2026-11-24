# Contact sheet of the five key frames: sheet.ps1 <dir with KF*.png> <out.jpg> [cell width]
param([string]$Dir, [string]$Out, [int]$W = 760)
Add-Type -AssemblyName System.Drawing
$files = Get-ChildItem $Dir -Filter 'KF*.png' | Sort-Object Name
$H = [int]($W * 9 / 16); $cols = 2; $rows = [int][math]::Ceiling($files.Count / $cols)
$bmp = New-Object System.Drawing.Bitmap(($W * $cols), ($H * $rows))
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$i = 0
foreach ($f in $files) { $img = [System.Drawing.Image]::FromFile($f.FullName); $g.DrawImage($img, ($i % $cols) * $W, [int][math]::Floor($i / $cols) * $H, $W, $H); $img.Dispose(); $i++ }
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]86)
$bmp.Save($Out, $enc, $ep); $g.Dispose(); $bmp.Dispose()
"sheet: $Out ($($files.Count) frames)"

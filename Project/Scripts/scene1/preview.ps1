# Downscale a PNG for a quick look: preview.ps1 <src.png> <dst.jpg> [width]
param([string]$Src, [string]$Dst, [int]$Width = 960)
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($Src)
$h = [int]($img.Height * $Width / $img.Width)
$bmp = New-Object System.Drawing.Bitmap($Width, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.DrawImage($img, 0, 0, $Width, $h)
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]88)
$bmp.Save($Dst, $enc, $ep)
$g.Dispose(); $bmp.Dispose(); $img.Dispose()
"$($img.Width) -> $Width : $Dst"

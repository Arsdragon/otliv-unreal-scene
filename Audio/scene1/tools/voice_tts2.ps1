# Voice of the ship through the modern Windows speech engine (OneCore voices: Microsoft Pavel / Irina, Russian).
# Takes a folder with bort_NN.ssml files (made by voice_text.py) and writes bort_NN.wav next to them.
#   powershell -NoProfile -ExecutionPolicy Bypass -File voice_tts2.ps1 -Dir <folder> [-Voice Pavel]
param([string]$Dir, [string]$Voice = 'Pavel')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Wait-WinRt($op, [Type]$type) {
    $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result
}
$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$v = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.Language -eq 'ru-RU' -and $_.DisplayName -like "*$Voice*" } | Select-Object -First 1
if ($null -eq $v) { Write-Output "no Russian voice like '$Voice'"; exit 1 }
$synth.Voice = $v
$n = 0
foreach ($f in Get-ChildItem -Path $Dir -Filter 'bort_*.ssml' | Sort-Object Name) {
    $ssml = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
    $stream = Wait-WinRt ($synth.SynthesizeSsmlToStreamAsync($ssml)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
    $reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
    Wait-WinRt ($reader.LoadAsync([uint32]$stream.Size)) ([uint32]) | Out-Null
    $bytes = New-Object byte[] ([int]$stream.Size)
    $reader.ReadBytes($bytes)
    [System.IO.File]::WriteAllBytes([System.IO.Path]::ChangeExtension($f.FullName, '.wav'), $bytes)
    $reader.Dispose(); $stream.Dispose(); $n++
}
$synth.Dispose()
Write-Output ("voice: {0}, files: {1}" -f $v.DisplayName, $n)

# Temporary voice of the ship: Windows speech synthesis (Russian voice) -> voice_tts\bort_01.wav ... bort_16.wav
# The texts are read from voice_lines.md (the table), so the file stays the single source.
#   powershell -NoProfile -ExecutionPolicy Bypass -File voice_tts.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'voice_tts'
New-Item -ItemType Directory -Force $out | Out-Null
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$ru = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'ru-RU' } | Select-Object -First 1
if ($null -eq $ru) { Write-Output 'no Russian voice installed'; exit 1 }
$s.SelectVoice($ru.VoiceInfo.Name)
$s.Rate = -2          # calm, unhurried
$s.Volume = 100
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$n = 0
foreach ($line in [System.IO.File]::ReadAllLines((Join-Path $root 'voice_lines.md'), [System.Text.Encoding]::UTF8)) {
    if ($line -match '^\|\s*(\d\d)\s*\|[^|]*\|\s*(.+?)\s*\|\s*$') {
        $id = $Matches[1]; $text = $Matches[2]
        $text = $text -replace '«', '' -replace '»', '' -replace ' — ', ', '
        $path = Join-Path $out ("bort_{0}.wav" -f $id)
        $s.SetOutputToWaveFile($path, $fmt)
        $s.Speak($text)
        $s.SetOutputToNull()
        $n++
    }
}
$s.Dispose()
Write-Output ("voice: {0}, files: {1}" -f $ru.VoiceInfo.Name, $n)

#!/bin/bash
# Puts the soundtrack under the animatic: the full copy (video untouched) and a small one for sending (640x360, <= 30 MB).
#   bash mux.sh [mix version, default v1]
VER=${1:-v1}
A=/c/UnrealScenes/Audio/scene1/mix_$VER.wav
D=/c/UnrealScenes/Review/scene1/animatic
# AAC overshoots the peaks of the WAV by 2-3 dB: the compressed copies get their own limiter with a -3 dBFS ceiling
LIM="alimiter=level_in=1:level_out=1:limit=0.708:attack=5:release=100:asc=1:level=0"
ffmpeg -y -v error -i "$D/otliv_v3.mp4" -i "$A" -map 0:v -map 1:a -c:v copy -af "$LIM" -c:a aac -b:a 256k -movflags +faststart "$D/otliv_v3_sound.mp4" || exit 1
cd /c/UnrealScenes/Audio/scene1/work || exit 1
ffmpeg -y -v error -i "$D/otliv_v3.mp4" -vf scale=640:360 -c:v libx264 -preset medium -b:v 312k -pass 1 -passlogfile small2p -an -f null - || exit 1
ffmpeg -y -v error -i "$D/otliv_v3.mp4" -i "$A" -map 0:v -map 1:a -vf scale=640:360 -c:v libx264 -preset medium -b:v 312k -pass 2 -passlogfile small2p \
  -pix_fmt yuv420p -af "$LIM" -c:a aac -b:a 96k -movflags +faststart "$D/otliv_v3_sound_small.mp4" || exit 1
rm -f small2p*
ls -la "$D/otliv_v3_sound.mp4" "$D/otliv_v3_sound_small.mp4"
for f in otliv_v3_sound.mp4 otliv_v3_sound_small.mp4; do
  ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,sample_rate,channels -of default=nw=1 "$D/$f" | tr '\n' ' '; echo
done

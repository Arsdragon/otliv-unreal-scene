#!/bin/bash
# Final assembly of scene 1 "Otliv": 1080p frames of the one-pass render + the soundtrack -> H.264 mp4 with the title,
# and a small copy for sending (640x360, <= 30 MB).
#   bash encode_final.sh [mix version, default v3]
VER=${1:-v3}
SRC=/c/UnrealScenes/Renders/scene1/final_1080
DST=/c/UnrealScenes/Review/scene1/final
A=/c/UnrealScenes/Audio/scene1/mix_$VER.wav
# AAC overshoots the peaks of the WAV by 2-3 dB: the encoded copies get their own limiter with a -3 dBFS ceiling
LIM="alimiter=level_in=1:level_out=1:limit=0.708:attack=5:release=100:asc=1:level=0"
mkdir -p "$DST"
cd "$SRC" || exit 1
[ -s "$A" ] || { echo "no soundtrack $A"; exit 1; }
n=$(ls f_*.png | wc -l); [ "$n" -eq 13201 ] || { echo "frames: $n of 13201 - render is not complete"; exit 1; }
printf 'О Т Л И В' > title.txt
# the title and the fades are the same as in the animatic, sizes doubled for 1080p
VF="drawtext=fontfile='C\:/Windows/Fonts/segoeuil.ttf':textfile=title.txt:fontsize=116:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-48:alpha='if(lt(t\,541)\,0\,if(lt(t\,544.5)\,(t-541)/3.5\,0.92))',fade=t=out:st=547:d=3,fade=t=in:st=0:d=2"
ffmpeg -y -loglevel error -stats -framerate 24 -i f_%05d.png -i "$A" -map 0:v -map 1:a -vf "$VF" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -af "$LIM" -c:a aac -b:a 256k -movflags +faststart "$DST/otliv_scene1_1080p.mp4" || exit 1
cd /c/UnrealScenes/Audio/scene1/work || exit 1
ffmpeg -y -v error -i "$DST/otliv_scene1_1080p.mp4" -vf scale=640:360 -c:v libx264 -preset medium -b:v 312k -pass 1 -passlogfile fin2p -an -f null - || exit 1
ffmpeg -y -v error -i "$DST/otliv_scene1_1080p.mp4" -vf scale=640:360 -c:v libx264 -preset medium -b:v 312k -pass 2 -passlogfile fin2p \
  -pix_fmt yuv420p -af "$LIM" -c:a aac -b:a 96k -movflags +faststart "$DST/otliv_scene1_small.mp4" || exit 1
rm -f fin2p*
for f in otliv_scene1_1080p.mp4 otliv_scene1_small.mp4; do
  ls -la "$DST/$f" | awk '{print $5, $9}'
  ffprobe -v error -show_entries format=duration -show_entries stream=codec_name,width,height,nb_frames -of default=nw=1 "$DST/$f" | tr '\n' ' '; echo
  ffmpeg -hide_banner -nostats -i "$DST/$f" -map 0:a -af ebur128=peak=true -f null - 2>&1 | grep -A16 "Summary" | grep "I:\|Peak:" | tr -s ' ' | tr '\n' ' '; echo
done

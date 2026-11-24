#!/bin/bash
# Assembles the S3 animatic: PNG frames -> H.264 mp4 with the title, plus stills.
# Usage: bash encode_v1.sh
SRC=/c/UnrealScenes/Renders/scene1/animatic_v1
DST=/c/UnrealScenes/Review/scene1/animatic
mkdir -p "$DST"
cd "$SRC" || exit 1
printf 'О Т Л И В' > title.txt
ffmpeg -y -loglevel error -stats -framerate 24 -i f_%05d.png \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/segoeuil.ttf':textfile=title.txt:fontsize=58:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-24:alpha='if(lt(t\,541)\,0\,if(lt(t\,544.5)\,(t-541)/3.5\,0.92))',fade=t=out:st=547:d=3,fade=t=in:st=0:d=2" \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -movflags +faststart "$DST/otliv_v1.mp4"
# stills: frame = seconds * 24
i=1
for spec in 480:orbit 1080:giant 1392:entry 2016:low_flight 2832:ramp 3384:mirror 4392:ridge 6336:wreck 7680:rangefinder 9108:shadow 9480:airlock 10704:wall 10992:slope 11160:underwater 12144:surfaced; do
  f=${spec%%:*}; n=${spec##*:}
  cp "$(printf 'f_%05d.png' "$f")" "$DST/$(printf 'still_%02d_%s.png' "$i" "$n")"; i=$((i+1))
done
ffmpeg -y -loglevel error -ss 545.5 -i "$DST/otliv_v1.mp4" -frames:v 1 "$DST/$(printf 'still_%02d_title.png' "$i")"
ls -la "$DST" | tail -20

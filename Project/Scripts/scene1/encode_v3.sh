#!/bin/bash
# Assembles the S3 animatic v3 (v2 montage + mood and weather): PNG frames -> H.264 mp4 with the title,
# the mood strip from six moments of the finished film and stills of the storm.
SRC=/c/UnrealScenes/Renders/scene1/animatic_v3
DST=/c/UnrealScenes/Review/scene1/animatic
TOOLS=/c/UnrealScenes/Project/Scripts/scene1
mkdir -p "$DST"
cd "$SRC" || exit 1
printf 'О Т Л И В' > title.txt
ffmpeg -y -loglevel error -stats -framerate 24 -i f_%05d.png \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/segoeuil.ttf':textfile=title.txt:fontsize=58:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-24:alpha='if(lt(t\,541)\,0\,if(lt(t\,544.5)\,(t-541)/3.5\,0.92))',fade=t=out:st=547:d=3,fade=t=in:st=0:d=2" \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -movflags +faststart "$DST/otliv_v3.mp4" || exit 1
# stills of the storm: frame = seconds * 24
i=1
for spec in 7680:roll_forms 8160:roll_over_crest 8928:gusts_of_rain 9865:flash_1 9600:cockpit_rain 10032:drops_on_glass \
            10405:flash_2 10560:wall_of_water 10968:under_the_wall 12192:rainbow; do
  f=${spec%%:*}; n=${spec##*:}
  cp "$(printf 'f_%05d.png' "$f")" "$DST/$(printf 'v3_still_%02d_%s.png' "$i" "$n")"; i=$((i+1))
done
# mood strip v3: the same six moments, taken from the film itself
S=/c/UnrealScenes/Renders/scene1/mood_strip_v3
mkdir -p "$S"
for spec in 3600:1500 6480:2700 8160:3400 9600:4000 10560:4400 12480:5200; do
  cp "$(printf 'f_%05d.png' "${spec%%:*}")" "$S/s_${spec##*:}.png"
done
python -I "$TOOLS/mood_sheet.py" "C:/UnrealScenes/Renders/scene1/mood_strip_v3" "C:/UnrealScenes/Review/scene1/animatic/mood_strip_v3.jpg"
ls "$DST" | grep -c v3_still

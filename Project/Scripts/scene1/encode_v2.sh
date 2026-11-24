#!/bin/bash
# Assembles the S3 animatic v2: PNG frames (v1 frames + re-rendered intervals) -> H.264 mp4 with the title, plus stills.
SRC=/c/UnrealScenes/Renders/scene1/animatic_v2
DST=/c/UnrealScenes/Review/scene1/animatic
mkdir -p "$DST"
cd "$SRC" || exit 1
printf 'О Т Л И В' > title.txt
ffmpeg -y -loglevel error -stats -framerate 24 -i f_%05d.png \
  -vf "drawtext=fontfile='C\:/Windows/Fonts/segoeuil.ttf':textfile=title.txt:fontsize=58:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2-24:alpha='if(lt(t\,541)\,0\,if(lt(t\,544.5)\,(t-541)/3.5\,0.92))',fade=t=out:st=547:d=3,fade=t=in:st=0:d=2" \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -movflags +faststart "$DST/otliv_v2.mp4"
# stills of the changed places: frame = seconds * 24
i=1
for spec in 1392:plasma 1872:clouds 2420:spray 3408:ship_and_giant 3792:water_at_feet 4128:drone_close 4464:mountains 5760:wreck_walk \
            5856:beacon 6288:cutting 6560:cover_falls 6864:storage 8388:glance_back 8544:giant_on_return 11030:water_on_glass 12288:giant_after; do
  f=${spec%%:*}; n=${spec##*:}
  cp "$(printf 'f_%05d.png' "$f")" "$DST/$(printf 'v2_still_%02d_%s.png' "$i" "$n")"; i=$((i+1))
done
ls "$DST" | grep -c v2_still

#!/usr/bin/env bash
# остальные кадры обломков, затем дрон: пересборка (скруглённый нос) -> запекание -> текстуры -> экспорт -> кадры
cd /c/UnrealScenes/Models
export PYTHONIOENCODING=utf-8
L=shots/_tmp/chain1.log
echo "== wreck shots" > $L
BG_TAIL=4 bash tools/bg.sh "load('probe_wreck_final.blend'); run('live_shots_d.py', D_ID='probe_wreck', LIVE_VIEWS=['wide10','wide25','main','crust'], LIVE_SAMPLES=32)" >> $L 2>&1
echo "== drone build + bake" >> $L
BG_TAIL=30 bash tools/bg.sh "fresh(); run('svetlyak.py'); run('d_bake.py', BAKE_ID='svetlyak', BAKE_SEPARATE=['sv_head'])" 2>&1 | grep -v "Baking map" >> $L
echo "== drone textures" >> $L
python tools/d_tex.py svetlyak A 2>&1 | tail -2 >> $L
echo "== drone final + shots" >> $L
BG_TAIL=8 bash tools/bg.sh "load('svetlyak.blend'); os.environ['D_ID']='svetlyak'; run('d_final.py'); run('live_shots_d.py', D_ID='svetlyak', LIVE_VIEWS=['lens','around1','below'], LIVE_SAMPLES=32)" >> $L 2>&1
echo "== CHAIN DONE" >> $L

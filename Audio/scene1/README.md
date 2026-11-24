# Сцена 1 «Отлив» — звуковая дорожка

Собирается вне Unreal: Python 3.13 (numpy, scipy) и ffmpeg. Все команды — из папки `tools\`.

## Что лежит

- `mix_v3.wav` — текущая сведённая дорожка (голос Piper dmitri, выбран пользователем на слух): 48 кГц, стерео, 24 бита,
  9:10, −16 LUFS, потолок лимитера −2 дБFS.
  Для сравнения оставлены `mix_v3_denis.wav` (Piper denis), `mix_v2.wav` (Microsoft Pavel) и `mix_v1.wav` (Microsoft Irina).
- `stem_voice_v3.wav`, `stem_ambience_v3.wav`, `stem_fx_v3.wav`, `stem_music_v3.wav` — дорожки так, как они стоят в миксе
  (баланс, приглушение под голосом, обрыв в конце), до лимитера. Общая поправка уровня записана в `mix_v3.json`
  (`stems_trim_db`): сумма четырёх дорожек, поднятая на эту величину, равна миксу до лимитера.
- `check\` — приборы: `levels_*.txt` (уровни по актам, тишина, клиппинг), `spectrum_*.png` (спектрограмма всего ролика
  с кривой уровня), `acts_*.png` (спектрограмма каждого акта).
- `voice_tts_piper_dmitri\` — голос борта для v3 (тексты, звук и `phonemes.txt` — как произносится каждая реплика).
  `voice_tts_piper\` — Piper denis, `voice_tts_pavel\` — голос v2, `voice_tts\` — голос v1. `voice_raw\` — сюда живые записи.
- `work\` — промежуточные дорожки в сыром виде (float32), пересоздаются скриптами; можно удалить.
- `CREDITS.md` — источники и лицензии. Скачанных звуков нет; скачан только синтезатор Piper с двумя голосами.

## Как пересобрать

```
python -I extract_timeline.py     # времена шагов, путь дрона, маркеры реплик из скриптов сцены -> timeline.json
python -I voice_piper.py dmitri ..\voice_tts_piper_dmitri         # голос Piper -> bort_NN.wav и phonemes.txt
python -I voice_clicks.py ..\voice_tts_piper_dmitri               # номера реплик с короткими ВЧ-всплесками (их можно пересинтезировать: --only=NN)
python -I voice_process.py ..\voice_tts_piper_dmitri              # «радио»-обработка и расстановка реплик -> work\voice.f32
python -I build_ambience.py       # окружение  (около 2 мин)
python -I build_fx.py             # эффекты    (около 4 мин)
python -I build_music.py          # музыка     (около 2 мин)
python -I mix.py v3               # сведение -> ..\mix_v3.wav и stem_*_v3.wav (около 4 мин)
python -I check.py ..\mix_v3.wav  # приборы -> ..\check
bash mux.sh v3                    # ролик со звуком и сжатая копия в Review\scene1\animatic
python -I voice_probe.py --lines=03,10,11                      # сравнение проб голоса приборами (папки в work\probe)
python -I voice_compare.py <out.mp3> <папка1> <папка2> ...     # одни и те же реплики подряд разными голосами — на слух
```

Piper лежит в `C:\UnrealScenes\Downloads\audio\piper\` (своё окружение Python и два голоса); как он был скачан — `piper_get.sh`.
Вариант с голосом denis: `python -I voice_piper.py denis ..\voice_tts_piper --pitch=-1.5`.
Перед синтезом стоит открыть `voice_tts_piper_dmitri\phonemes.txt`: знак `ˈ` стоит перед ударным гласным, так что ударение
каждого слова видно глазами. Неверное исправляется знаком ударения в словаре `STRESS` в `voice_piper.py`.

Голос Windows (v2), если понадобится снова:

```
python -I voice_text.py ..\voice_tts_pavel --rate=-8 --pitch=-6
powershell -NoProfile -ExecutionPolicy Bypass -File voice_tts2.ps1 -Dir ..\voice_tts_pavel -Voice Pavel
python -I voice_process.py ..\voice_tts_pavel
```

## Заменить синтез голоса на записи пользователя

Записи `bort_01 … bort_16` (m4a, mp3, wav — что угодно) положить в `voice_raw\`, затем:

```
python -I voice_process.py ..\voice_raw
python -I mix.py v4
bash mux.sh v4
```

Скрипт сам обрежет тишину, выровняет громкость реплик, при нехватке места сократит паузы и чуть ускорит реплику
(таблица в консоли покажет, что сделано с каждой). Если в файле два дубля подряд — берётся последний
(`--takes=auto` по умолчанию; `--takes=1` — брать файл целиком, `--takes=2` — всегда последний блок).
Для синтеза паузы внутри реплики обрезаются до 0,6 с (`--pause-cap`), для живых записей — нет.

## Тайминг

Все события берутся из скриптов сцены (`Project\Scripts\scene1\s3_timeline.py`, `s3_v2.py`, `s3_mood.py`): реплики — по
маркерам `LINES`, шаги — по тому же правилу, что круги на воде, дрон — по своей траектории относительно камеры.
Если монтаж изменится, достаточно заново выполнить `extract_timeline.py` и сборку; времена, записанные числами
в `build_*.py` (шлюз, резак, удар, вспышки), придётся поправить руками.

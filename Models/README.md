# Models — модели для UnrealScenes (чат «Модели», Blender)

Правила проекта — в `C:\UnrealScenes\CLAUDE.md`, ТЗ сцены 1 — в `C:\UnrealScenes\SCENE1.md`.
Blender на машине — **5.0.1** (`%LOCALAPPDATA%\Programs\Blender 3D\blender.exe`).

## Как работаем с Blender

- Пользователь хочет видеть работу в **открытом окне Blender**. Сервер MCP «blender» в чате «Модели» не подключился,
  поэтому код в живой Blender отправляется напрямую в аддон BlenderMCP (порт 9876): `python tools/bmcp.py @файл.py`.
- `tools/live_run.py` выполняет любой сборочный скрипт в открытом окне так, как если бы он был запущен отдельно:

      python tools/bmcp.py "LIVE_SCRIPT='chaika_cockpit.py'; exec(open(r'C:\UnrealScenes\Models\tools\live_run.py', encoding='utf-8').read())" 900

- **Не держать два Blender сразу**: памяти мало, рендер в фоновом Blender при открытом окне занял 37 минут вместо одной.
  Фоновый режим (`bash tools/bl.sh …`) — только если окно закрыто или аддон не отвечает.
- Рендеры идут очередью обычных F12 (`live_shots.py`, `live_shots_ck.py`): окно не блокируется, кадр — 1–2 минуты,
  готовность — файл `shots/_tmp/live_done.txt`, журнал — `shots/_tmp/live_shots.log`.
- Узлы материалов искать по типу (`n.type == 'BSDF_PRINCIPLED'`), а не по имени: интерфейс Blender русский.
- После добавления коллекций из других .blend убирать `bpy.data.libraries` перед сохранением поверх исходного файла.

## Папки

- `tools\` — скрипты (всё собирается кодом, .blend можно пересоздать). `src\` — .blend
  (`chaika_ext_final.blend`, `chaika_cockpit_final.blend`, `chaika_all_live.blend` — обе модели вместе).
- `export\<id>\` — готовое для Unreal. `shots\` — рендеры на приёмку, `shots\_tmp\` — черновые кадры и журналы.

## Конвейер (одинаковый для chaika_ext и chaika_cockpit)

1. Сборка геометрии и развёрток в Blender: `chaika_ext.py` или `chaika_cockpit.py` (через `live_run.py`)
   → `src/<id>.blend`, `export/<id>/layout.json`, `faces_<атлас>.npz`.
2. Текстуры — обычным Python, без Blender: `python tools/chaika_tex.py chaika_ext` / `chaika_cockpit`
   (для кабины ещё `python tools/chaika_screens.py` — заглушки экранов).
3. Материалы на экспортных картах, экспорт glb / fbx и манифест: `chaika_final.py` / `chaika_cockpit_final.py`
   (через `live_run.py`) → `src/<id>_final.blend`, `export/<id>/*`.
4. Рендеры: `python tools/bmcp.py @tools/live_shots.py 300` (снаружи) или `@tools/live_shots_ck.py` (кабина);
   список видов — переменная `LIVE_VIEWS`.

Текстуры рисуются не запеканием, а кодом прямо в развёртке: плитка, швы, крепёж, надписи, пояса, нагар, потёки.
Поменял надписи или цвет — достаточно шага 2 и повторного рендера (текстуры перечитываются с диска), потом шаг 3 ради glb.

## Конвейер этапа D (дрон «Светляк», обломки зонда) — атлас 2048, всё в открытом Blender

    bash tools/live.sh @reset                                   # пустой файл в живом Blender (освобождает память)
    bash tools/live.sh svetlyak.py                              # или probe_wreck.py: геометрия, развёртка, tris.npz, layout.json
    bash tools/live.sh @code "BAKE_ID='svetlyak'; exec(open(r'C:\UnrealScenes\Models\tools\d_bake.py', encoding='utf-8').read())"
                                                                # запекание затенения (AO) -> export/<id>/_ao.png, ~40 с
    python tools/d_tex.py svetlyak                              # текстуры: T_Svetlyak_* / T_ProbeWreck_*
    bash tools/live.sh @code "import os; os.environ['D_ID']='svetlyak'; LIVE_SCRIPT='d_final.py'; exec(open(r'C:\UnrealScenes\Models\tools\live_run.py', encoding='utf-8').read())"
    bash tools/live.sh @code "D_ID='svetlyak'; LIVE_SAMPLES=32; exec(open(r'C:\UnrealScenes\Models\tools\live_shots_d.py', encoding='utf-8').read())"

`d_tex.py` знает про каждый тексель 3D-положение (в осях детали и в мире), нормаль, класс поверхности и деталь, поэтому
износ, соль, «ватерлинии», швы и надписи рисуются в 3D и не рвутся на стыках островов развёртки. Правила раскраски —
`d_tex_rules.py` (дрон) и `d_tex_wreck.py` (обломки); надписи и сетку солнечных элементов обломков задаёт `probe_wreck.py`
через layout.json. `live_quick.py` — быстрые виды в Workbench для проверки формы.

Осторожно: у `cyl()` торцы закрыты — для трубок (тубус объектива, бленда, кольца) строить кольцевой профиль через
`revolve(..., closed=True, cap=False)`; для гладких тел (корпус дрона) развёртку делать с малым углом (`smart_uv(angle=32)`),
иначе на скользящих гранях текстура растягивается в «ступеньки».

## Скрипты

- `kit.py` — геометрия (bmesh). `uvkit.py` — развёртки в метрах, раскладка по атласам, выгрузка граней художнику.
- `partkit.py` — заготовки агрегатов, тумблеры, ручки, кнопки и лицевые панели с подписями (`Plates`).
- `chaika_shape.py` — **единственный источник формы «Чайки»**: сечения корпуса `KEYS`, фонарь (`canopy_cuts`,
  `canopy_class`, `frame_solid`), крыло, корма, опоры, главные размеры, метка глаз `EYE`. Общий для ext и cockpit,
  поэтому переплёты снаружи и изнутри совпадают по построению.
- `chaika_ext.py` + `chaika_ext_parts.py` — внешняя модель; `chaika_final.py` — её материалы, экспорт, манифест.
- `chaika_cockpit.py` + `chaika_cockpit_station.py` + `chaika_cockpit_rear.py` — кабина и шлюз;
  `chaika_cockpit_final.py` — материалы, экспорт, манифест; `chaika_screens.py` — заглушки экранов.
- `chaika_tex.py` — художник текстур (numpy + Pillow) для обеих моделей.
- `live_run.py`, `live_load.py`, `show_in_blender.py`, `live_shots.py`, `live_shots_ck.py`, `live_export.py`, `bmcp.py` —
  работа с открытым окном Blender. `contact.py` — склейка кадров в один лист для быстрой проверки.
- `chaika_block.py`, `shots_a.py`, `sheet_a.py`, `shots_b.py`, `stage_a.sh`, `stage_b.sh` — этапы A и B в фоновом режиме (история).

## Оси и договорённости

- Метры, Z вверх, нос по −Y. Начало координат — центр под опорами на уровне грунта, общее для ext и cockpit.
- **Борта: +X — левый борт (слева от пилота), −X — правый.** Суффиксы `_L` / `_R` в именах объектов — настоящие борта.
  Ручка управления стоит на −X, РУД — на +X. (В блок-модели этапа A ручка стояла не с той стороны.)
- В сцене Unreal нос смотрит на +X: после импорта корабль поворачивается вокруг вертикали.
- Подвижные части — отдельные объекты с опорной точкой на оси вращения; анимация не запекается.
  Поза экспорта ext: мотогондолы в полётном положении (0°), трап и люк закрыты; посадочные значения — в manifest.json.
- Атласы ext: A `T_ChaikaHull_*` — корпус (развёрнут по обводу, 304 пикс/м), обтекатели кормовых двигателей, кили;
  B `T_ChaikaParts_*` — крыло, мотогондолы, мелкие детали (347 пикс/м); C `T_ChaikaGear_*` — опоры, трап, люк,
  ниша трапа (295 пикс/м). Левые части делят участок атласа с правыми.
- Атласы cockpit: A `T_CockpitFront_*` — место пилота (307 пикс/м, лицевые панели с подписями 1227 пикс/м);
  B `T_CockpitRear_*` — задняя часть кабины и шлюз (264 пикс/м). Экраны — слоты `screen_1…6`, развёртка 0…1, 16:10.

## Конструкция «Чайки»

- Корпус 14,0 м: сечение — скруглённый шестиугольник (киль — скула — плечо — конёк), килеватое «лодочное» днище.
  Днище 1,35 м над грунтом, вода 0,45 м. Ряды плитки идут вдоль конька, плеча и киля.
- Фонарь: 7 окон. Центральное панорамное стекло ±52° по азимуту от глаз пилота, от козырька панели до +79°, без переплётов.
  Две стойки — вертикальные плоскости через вертикаль глаз пилота; переплёты вытянуты внутрь по линии взгляда.
- Крыло «чайка» с поворотными мотогондолами на законцовках, два ракетных двигателя в корме, V-образные кили,
  четыре опоры-треноги с широкими лыжами (2,4 × 0,96 м), трап под хвостом, люк шлюза в стенке y = +2,0 м.
- Кабина: y от −6,8 до −2,3 м; шлюз: от −2,3 до +2,0 м; пол z = 1,66 м. Приборная панель — дуга из пяти экранов,
  боковые консоли с автоматами защиты, верхний пульт под хребтовой балкой за головой пилота.

## Этап E и фоновый Blender (2026-11-21)

**Фоновый Blender** (`tools/bg.sh "код"`, помощники `fresh()`, `load('файл.blend')`, `run('скрипт.py', ИМЯ=значение)`): отдельный
процесс без окна, заводские настройки. Нужен, когда открытый Blender занят или не принимает запись (21.11 после рендера он
стал отвечать «Writing to ID classes in this context is not allowed» на любую запись — лечится перезапуском Blender).
`d_bake.py`, `live_shots_d.py`, `giant_scene.py` сами понимают фоновый режим и считают подряд, без таймеров.

Порядок для моделей этапа D в фоне (на примере дрона):
1. `bash tools/bg.sh "fresh(); run('svetlyak.py'); run('d_bake.py', BAKE_ID='svetlyak', BAKE_SEPARATE=['sv_head'])"`
2. `python tools/d_tex.py svetlyak A` (для обломков ещё `python tools/d_tex.py probe_wreck M`)
3. `bash tools/bg.sh "load('svetlyak.blend'); os.environ['D_ID']='svetlyak'; run('d_final.py'); run('live_shots_d.py', D_ID='svetlyak', LIVE_VIEWS=['lens'])"`
Не запускать шаг 3, пока не дорисованы текстуры шага 2: экспорт упадёт или возьмёт старые PNG.

**Несколько атласов на модель**: атлас задаётся в `smart_uv(ob, 'M', ...)`; `finish_model` раскладывает каждый атлас отдельно и
пишет `tris_<атлас>.npz`; имена наборов текстур — в `extra=dict(tex={'A': ..., 'M': ...})`; в `d_final.py` — `sets` и `join`
(детали, разделённые только ради плотности текстуры, вливаются обратно при экспорте). Обломки: атлас M — грань с нишей,
крышка и накопитель (835–960 пикс/м), атлас A — всё остальное (главный блок 378 пикс/м, дальние куски 113).

**Газовый гигант** (`export/gas_giant`): `python tools/giant_tex.py` (проба: `python tools/giant_tex.py 1024`) — текстуры и лист
`shots/E_giant_unwrap.png`; `bash tools/bg.sh "fresh(); run('giant_scene.py', LIVE_VIEWS=['view1','view2','view3'])"` — сетка,
экспорт, манифест, кадры; `python tools/giant_comp.py` — накладывает третий ракурс на дневное небо. Узор полос получается
переносом «краски» течением (струи, вихри, волны на границах) с трассировкой назад; всё считается на сфере — шва и стягивания
у полюсов нет.

**Перчатки пилота** (`export/pilot_gloves`): `tools/pilot_gloves.py` строит правую кисть в осях хвата (ось Z — вдоль рукояти)
и ставит её матрицей на ручку; левая — зеркальной матрицей на РУД. Позы задаются в `CFG_R`/`CFG_L` (полуоси рукояти, угол
костяшек, высоты пальцев, опорные точки большого пальца) и направлением предплечья. Раскраска — `tools/d_tex_gloves.py`.
Кадры в кабине: `bash tools/bg.sh "load('chaika_cockpit_final.blend'); run('gloves_shots.py', LIVE_VIEWS=['eye_down'])"`.

Осторожно с правками через heredoc в Bash: обратная косая черта перед `n` и в конце строки может потеряться — правки с
такими строками писать файлом-скриптом в `tools/_probe/`.

## Экраны кабины по состояниям сюжета (2026-11-22)

`python tools/cockpit_screens.py` -> `export/cockpit_screens/<состояние>/T_Screen_1…5.png`, `manifest.json` и контрольный лист
`shots/F_screens_sheet.png`. Девять папок: orbit, entry, approach, landed, alert, contact_25/15/05, failure (у экрана 5 второй
кадр `T_Screen_5_b.png` для мигания). Тексты и числа каждого состояния — в функциях `orbit()`, `entry()` … в конце скрипта.
Шрифт Bahnschrift не содержит знака «минус» (U+2212) — писать короткое тире «–», иначе выйдет пустой квадрат.

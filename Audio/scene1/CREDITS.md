# Сцена 1 «Отлив» — источники звука

## Скачанные файлы

Звуков из интернета в миксах нет. Скачан только синтезатор речи Piper и два голоса для него — с прямого согласия
пользователя («Да, скачать», 2026-11-22). Всё лежит в `C:\UnrealScenes\Downloads\audio\piper\` (292 МБ), копия этой таблицы —
там же в `LICENSES.md`.

| Файл | Автор / проект | Лицензия | Ссылка |
|---|---|---|---|
| `venv\` — пакет `piper-tts` 1.8.0 | Open Home Foundation, OHF-Voice/piper1-gpl | GPL-3.0-or-later | https://pypi.org/project/piper-tts/1.8.0/ |
| `venv\` — пакет `onnxruntime` 1.32.0 | Microsoft | MIT | https://pypi.org/project/onnxruntime/1.32.0/ |
| `venv\` — зависимости: `numpy` 2.5.5, `protobuf` 7.36.2, `flatbuffers` 25.12.19, `packaging` 26.3, `pathvalidate` 3.3.1 | их авторы | свободные; тексты лицензий лежат внутри пакетов, отдельно я их не сверял | pypi.org |
| `voices\ru_RU-dmitri-medium.onnx` и `.onnx.json` — **голос борта в `mix_v3`**, выбран пользователем на слух | rhasspy/piper-voices; данные OHF-Voice/voice-datasets | данные CC0 | https://huggingface.co/rhasspy/piper-voices/tree/main/ru/ru_RU/dmitri/medium |
| `voices\ru_RU-denis-medium.onnx` и `.onnx.json` — для сравнения (`mix_v3_denis.wav`) | rhasspy/piper-voices; данные OHF-Voice/voice-datasets | данные CC0 | https://huggingface.co/rhasspy/piper-voices/tree/main/ru/ru_RU/denis/medium |

Piper — программа под GPL-3.0. Она здесь только инструмент: в ролик входит звук, который она выдала, а не она сама.
По карточке модели `dmitri` дообучена от базовой модели `hifi_tts_92` (голос чтицы Cori Samuel из набора Hi-Fi TTS);
лицензию этой базовой модели я не проверял. Карточки моделей сохранены рядом (`voices\MODEL_CARD_*.txt`).

## Синтез (скрипты в `tools\`)

Всё, кроме голоса, получено расчётом: фильтрованный шум, синусоидальные тоны, импульсы через звенящие фильтры.
Образцов, записей и чужих мелодий нет.

- `build_ambience.py` — гул корабля, рёв входа, воздух на планировании, ветер, гул и рёв волны, шум дождя, течение, подводный фон, зыбь.
- `build_fx.py` — дыхание, электроника кабины, двигатели, посадка, шлюз и трап, шаги по воде, дрон, маяк, резак, крышка ниши,
  капли дождя, гром, тревога, скрип корпуса, удар, пузыри, сердцебиение, всплытие.
- `build_music.py` — оригинальный эмбиент из синусоидальных тонов (тональный центр ре).

## Голос борта

- **`mix_v3` (текущий):** нейросинтез Piper, голос `ru_RU-dmitri-medium`, выбран пользователем на слух (2026-11-22).
  Темп ×1,08 (чуть медленнее), тон не менялся. Файлы: `voice_tts_piper_dmitri\`.
  Ударения проверены глазами по фонемам (`voice_tts_piper_dmitri\phonemes.txt`); три слова исправлены знаком ударения:
  «со́рок», «воды́», «заме́р».
- `mix_v3_denis`: Piper, голос `ru_RU-denis-medium`, тон понижен на 1,5 полутона после синтеза. Файлы: `voice_tts_piper\`.
- `mix_v2`: синтез речи Windows, голос **Microsoft Pavel** (ru-RU, мужской, движок OneCore). Файлы: `voice_tts_pavel\`.
- `mix_v1`: голос **Microsoft Irina Desktop** (ru-RU, женский, движок SAPI 5). Файлы: `voice_tts\`.
- Голоса Windows входят в систему; условия использования их речи в публикуемом ролике я не проверял. Для `mix_v3`
  этот вопрос не стоит: данные голоса `dmitri` — CC0 (см. оговорку про базовую модель выше).

## Другие русские голоса Piper (не скачаны)

| Голос | Данные для обучения | Лицензия | Годится |
|---|---|---|---|
| `ru_RU-irina-medium` | RHVoice | неизвестна | нет |
| `ru_RU-ruslan-medium` | RUSLAN corpus | CC BY-NC-SA 4.0 (некоммерческая) | нет |

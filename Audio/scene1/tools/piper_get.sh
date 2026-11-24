#!/bin/bash
# Downloads the neural speech synthesizer Piper and two Russian voices into C:\UnrealScenes\Downloads\audio\piper.
# NOT TO BE RUN until the user himself says yes in the chat of "Scene 1" (downloading and running programs needs his word).
# Nothing goes into the system Python: a separate environment is made inside that folder.
#   piper-tts 1.8.0      pypi.org, project OHF-Voice/piper1-gpl, GPL-3.0-or-later   (wheel 34.1 MB)
#   onnxruntime 1.32.0   pypi.org, MIT                                             (wheel 16.7 MB) + its dependencies (numpy, sympy, protobuf...)
#   ru_RU-denis-medium, ru_RU-dmitri-medium   huggingface.co/rhasspy/piper-voices, training data CC0   (63.2 MB each)
D=/c/UnrealScenes/Downloads/audio/piper
mkdir -p "$D/voices" || exit 1
[ -d "$D/venv" ] || python -I -m venv "$(cygpath -w "$D/venv")" || exit 1
"$D/venv/Scripts/python.exe" -I -m pip install --no-cache-dir --only-binary=:all: "piper-tts==1.8.0" "onnxruntime==1.32.0" || exit 1
for v in denis dmitri; do
  for ext in onnx onnx.json; do
    f="$D/voices/ru_RU-$v-medium.$ext"
    [ -s "$f" ] || curl -L --fail --max-time 1200 -H "User-Agent: curl" -o "$f" \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/$v/medium/ru_RU-$v-medium.$ext" || exit 1
  done
  curl -sL --fail -H "User-Agent: curl" -o "$D/voices/MODEL_CARD_$v.txt" "https://huggingface.co/rhasspy/piper-voices/raw/main/ru/ru_RU/$v/medium/MODEL_CARD"
done
cat > "$D/LICENSES.md" <<'EOF'
# Piper — что скачано и на каких условиях

| Файл | Автор / проект | Лицензия | Ссылка |
|---|---|---|---|
| venv: пакет piper-tts 1.8.0 | Open Home Foundation (OHF-Voice/piper1-gpl) | GPL-3.0-or-later | https://pypi.org/project/piper-tts/1.8.0/ |
| venv: пакет onnxruntime 1.32.0 и его зависимости | Microsoft и др. | MIT (зависимости — свои свободные лицензии) | https://pypi.org/project/onnxruntime/1.32.0/ |
| voices/ru_RU-denis-medium.onnx (+ .json) | rhasspy/piper-voices; данные OHF-Voice/voice-datasets | данные CC0 | https://huggingface.co/rhasspy/piper-voices/tree/main/ru/ru_RU/denis/medium |
| voices/ru_RU-dmitri-medium.onnx (+ .json) | rhasspy/piper-voices; данные OHF-Voice/voice-datasets | данные CC0 | https://huggingface.co/rhasspy/piper-voices/tree/main/ru/ru_RU/dmitri/medium |

Карточки моделей лежат рядом: voices/MODEL_CARD_*.txt.
EOF
du -sh "$D" | cut -f1; ls -la "$D/voices" | awk '{print $5, $9}'
"$D/venv/Scripts/python.exe" -I -m piper --help 2>&1 | head -40

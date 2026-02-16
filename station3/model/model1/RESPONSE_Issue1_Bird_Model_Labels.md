# Response to Issue #1 — Bird Model Label Confusion

**Issue:** [mklemmingen/LogChirpy#1](https://github.com/mklemmingen/LogChirpy/issues/1)
**Author:** Herbert Betz (@herbbetz)
**Subject:** Cannot match model output to labels; "Class 128" for a sparrow image

---

## English

### What Happened

You tried to classify an image of a House Sparrow (*Passer domesticus*) using:
- **Model:** `assets/models/birds_mobilenetv2/bird_classifier_metadata.tflite`
- **Labels:** `assets/model_labels_whoBird/labels_de.txt`

Your script returned **"Class 128"**, but in `labels_de.txt` *Passer domesticus* sits at **line 4246**. Nothing made sense — and for good reason: **those labels do not belong to that model.**

### Why It Didn't Work — Two Completely Separate Models

LogChirpy ships **two independent ML models** for different sensory modalities. They have different architectures, different class counts, and completely different label sets:

| | Image Model (MobileNetV2) | Audio Model (BirdNET v2.4) |
|---|---|---|
| **Purpose** | Classify bird **photos** (JPG/PNG) | Classify bird **songs/calls** (audio) |
| **File** | `assets/models/birds_mobilenetv2/bird_classifier_metadata.tflite` | `assets/models/whoBIRD-TFlite-master/BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite` |
| **Size** | 17 MB | 50 MB |
| **Input** | 224 x 224 x 3 RGB image, Float32, normalized to [-1, 1] | 144,000 raw Float32 audio samples (3 s @ 48 kHz) |
| **Output classes** | **400** bird species | **6,522** bird species |
| **Label format** | English common names (e.g. "House Sparrow") | Scientific_CommonName (e.g. "Passer domesticus_Haussperling") |
| **Label file** | `assets/models/birds_mobilenetv2/labels.txt` **(NEW — added with this fix)** | `assets/model_labels_whoBird/labels_de.txt` (and 37 other languages) |
| **Architecture** | MobileNetV2 (image CNN) | BirdNET/EfficientNet (audio) |
| **Framework in app** | Google ML Kit Image Labeling | react-native-fast-tflite |

**The core mistake:** `labels_de.txt` (6,522 entries) belongs to the **audio** model. The **image** model only has 400 classes. Using 6,522 labels against 400 output neurons can never produce a meaningful result.

### What "Class 128" Actually Was

In the image model's 400-class output, index 128 = **"Cream Colored Woodpecker"**. Your sparrow was misclassified — likely because the preprocessing (image resize, normalization) wasn't set up correctly for MobileNetV2, or because the model confidence for "House Sparrow" (index 225) was lower than for other classes on that particular photo.

### The Embedded Labels Bug

We also discovered that the labels inside `bird_classifier_metadata.tflite` had an additional bug: each label included a **numeric prefix** (e.g. `"225 House Sparrow"` instead of `"House Sparrow"`). This means the app's ML Kit integration was displaying bird names with numbers in front. We've re-embedded the model with corrected labels.

### What We Fixed

1. **Corrected embedded labels** — Removed numeric prefixes from the 400 labels inside `bird_classifier_metadata.tflite`
2. **Added `labels.txt`** — The image model's 400 labels are now available as a standalone file at `assets/models/birds_mobilenetv2/labels.txt`
3. **Added `classify_bird_image.py`** — A comprehensive Python script you can use right now (see below)

### How to Use the Script

```bash
# Requirements: Python 3.9, 3.10, or 3.11 (NOT 3.12/3.13 — tflite-runtime doesn't support them yet)
pip install tflite-runtime Pillow numpy

# Run from this Issue/ folder:
python3 classify_bird_image.py your_sparrow.jpg

# Or specify model/labels explicitly:
python3 classify_bird_image.py your_sparrow.jpg \
    --model ../assets/models/birds_mobilenetv2/bird_classifier_metadata.tflite \
    --labels ../assets/models/birds_mobilenetv2/labels.txt
```

The script will output:
- Full technical details (model architecture, input shape, normalization)
- Top-10 predictions with confidence percentages
- Whether "House Sparrow" appears in the results at all
- Preprocessing diagnostics

### Python Version Compatibility

You mentioned `tflite_support.metadata` not working on Python 3.13. This is correct — the TFLite ecosystem currently supports **Python 3.9 to 3.11** only. We recommend:

- **Python 3.11** (best compatibility)
- On Windows: use WSL2 with Debian 12 / Ubuntu 22.04
- `pip install tflite-runtime Pillow numpy` — that's all you need

### Comparing with birdiary

For a fair comparison with the birdiary platform's model, keep in mind:
- The LogChirpy image model covers **400 species** with English common names only
- It's optimized for **mobile speed**, not maximum accuracy
- The BirdNET audio model (6,522 species) is far more comprehensive but works with **audio only**
- Preprocessing must be exact: 224x224 pixels, RGB, normalized to [-1, 1] via `(pixel - 127.5) / 127.5`

---

## Deutsch

### Was passiert ist

Sie haben versucht, ein Bild eines Haussperlings (*Passer domesticus*) zu klassifizieren mit:
- **Modell:** `assets/models/birds_mobilenetv2/bird_classifier_metadata.tflite`
- **Labels:** `assets/model_labels_whoBird/labels_de.txt`

Ihr Script gab **"Class 128"** aus, aber in `labels_de.txt` steht *Passer domesticus* auf **Zeile 4246**. Nichts ergab Sinn — und das aus gutem Grund: **Diese Labels gehören nicht zu diesem Modell.**

### Warum es nicht funktionierte — Zwei völlig getrennte Modelle

LogChirpy enthält **zwei unabhängige ML-Modelle** für verschiedene Sinnesmodalitäten. Sie haben verschiedene Architekturen, verschiedene Klassenanzahlen und völlig verschiedene Label-Sets:

| | Bild-Modell (MobileNetV2) | Audio-Modell (BirdNET v2.4) |
|---|---|---|
| **Zweck** | Klassifizierung von Vogel-**Fotos** (JPG/PNG) | Klassifizierung von Vogel-**Gesang/Rufen** (Audio) |
| **Datei** | `assets/models/birds_mobilenetv2/bird_classifier_metadata.tflite` | `assets/models/whoBIRD-TFlite-master/BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite` |
| **Größe** | 17 MB | 50 MB |
| **Eingabe** | 224 x 224 x 3 RGB-Bild, Float32, normalisiert auf [-1, 1] | 144.000 rohe Float32 Audio-Samples (3 s bei 48 kHz) |
| **Ausgabe-Klassen** | **400** Vogelarten | **6.522** Vogelarten |
| **Label-Format** | Englische Trivialnamen (z.B. "House Sparrow") | Wissenschaftlich_Trivialname (z.B. "Passer domesticus_Haussperling") |
| **Label-Datei** | `assets/models/birds_mobilenetv2/labels.txt` **(NEU — mit diesem Fix hinzugefügt)** | `assets/model_labels_whoBird/labels_de.txt` (und 37 weitere Sprachen) |
| **Architektur** | MobileNetV2 (Bild-CNN) | BirdNET/EfficientNet (Audio) |
| **Framework in App** | Google ML Kit Image Labeling | react-native-fast-tflite |

**Der Kernfehler:** `labels_de.txt` (6.522 Einträge) gehört zum **Audio-Modell**. Das **Bild-Modell** hat nur 400 Klassen. 6.522 Labels gegen 400 Ausgabe-Neuronen zu verwenden, kann nie ein sinnvolles Ergebnis liefern.

### Was "Class 128" tatsächlich war

In der 400-Klassen-Ausgabe des Bild-Modells steht Index 128 = **"Cream Colored Woodpecker"** (Cremefarbener Specht). Ihr Spatz wurde falsch klassifiziert — wahrscheinlich weil die Vorverarbeitung (Bildskalierung, Normalisierung) nicht korrekt für MobileNetV2 eingestellt war, oder weil die Konfidenz des Modells für "House Sparrow" (Index 225) bei diesem bestimmten Foto niedriger war als für andere Klassen.

### Der Bug in den eingebetteten Labels

Wir haben außerdem entdeckt, dass die Labels innerhalb der `bird_classifier_metadata.tflite` einen zusätzlichen Bug hatten: Jedes Label enthielt ein **numerisches Präfix** (z.B. `"225 House Sparrow"` statt `"House Sparrow"`). Das bedeutet, die ML-Kit-Integration der App hat Vogelnamen mit Zahlen davor angezeigt. Wir haben das Modell mit korrigierten Labels neu eingebettet.

### Was wir behoben haben

1. **Eingebettete Labels korrigiert** — Numerische Präfixe aus den 400 Labels in `bird_classifier_metadata.tflite` entfernt
2. **`labels.txt` hinzugefügt** — Die 400 Labels des Bild-Modells sind jetzt als eigenständige Datei unter `assets/models/birds_mobilenetv2/labels.txt` verfügbar
3. **`classify_bird_image.py` hinzugefügt** — Ein umfassendes Python-Script, das Sie sofort verwenden können (siehe unten)

### So verwenden Sie das Script

```bash
# Voraussetzungen: Python 3.9, 3.10 oder 3.11 (NICHT 3.12/3.13 — tflite-runtime unterstützt diese noch nicht)
pip install tflite-runtime Pillow numpy

# Ausführen aus diesem Issue/-Ordner:
python3 classify_bird_image.py ihr_spatz.jpg

# Oder Modell/Labels explizit angeben:
python3 classify_bird_image.py ihr_spatz.jpg \
    --model ../assets/models/birds_mobilenetv2/bird_classifier_metadata.tflite \
    --labels ../assets/models/birds_mobilenetv2/labels.txt
```

Das Script gibt aus:
- Vollständige technische Details (Modell-Architektur, Eingabeform, Normalisierung)
- Top-10 Vorhersagen mit Konfidenz-Prozenten
- Ob "House Sparrow" überhaupt in den Ergebnissen auftaucht
- Vorverarbeitungs-Diagnostik

### Python-Versionskompatibilität

Sie erwähnten, dass `tflite_support.metadata` unter Python 3.13 nicht funktioniert. Das stimmt — das TFLite-Ökosystem unterstützt derzeit nur **Python 3.9 bis 3.11**. Wir empfehlen:

- **Python 3.11** (beste Kompatibilität)
- Unter Windows: WSL2 mit Debian 12 / Ubuntu 22.04 verwenden
- `pip install tflite-runtime Pillow numpy` — mehr brauchen Sie nicht

### Vergleich mit birdiary

Für einen fairen Vergleich mit dem Modell der birdiary-Plattform beachten Sie:
- Das LogChirpy-Bild-Modell deckt **400 Arten** ab, nur mit englischen Trivialnamen
- Es ist auf **mobile Geschwindigkeit** optimiert, nicht auf maximale Genauigkeit
- Das BirdNET-Audio-Modell (6.522 Arten) ist weitaus umfassender, arbeitet aber nur mit **Audio**
- Die Vorverarbeitung muss exakt sein: 224x224 Pixel, RGB, normalisiert auf [-1, 1] über `(Pixel - 127.5) / 127.5`

---

## File Index

| File | Description |
|---|---|
| `Issue/RESPONSE_Issue1_Bird_Model_Labels.md` | This document |
| `Issue/classify_bird_image.py` | Full-featured Python classification script |
| `assets/models/birds_mobilenetv2/labels.txt` | 400 image model labels (standalone) |
| `assets/models/birds_mobilenetv2/bird_classifier_metadata.tflite` | Fixed image model (labels without numeric prefixes) |
| `assets/model_labels_whoBird/labels_de.txt` | 6,522 audio model labels (German) — **NOT for the image model** |
| `dev/scripts/classify_bird_image.py` | Simpler version of the classification script |

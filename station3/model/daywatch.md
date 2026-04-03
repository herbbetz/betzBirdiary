<!--keywords[daywatch,KI-Model,ramdisk,Tensorflow_Lite_C_API]-->

**Doku zu daywatch**

- 30 aus jedem Vogelvideo ausgekoppelte JPG Images werden nach KI-ermittelter Erkennungsrate auf die zwei eindeutigsten vogelhaltigen Bilder reduziert. 

- mehrere KI-Modelle im Vergleich (in der Reihenfolge ihrer zeitlichen Verfügbarkeit):

  - *model0*: ursprüngliche KI-Analyse der birdiary Plattform (Uni Münster)
  - *model1*: LogChirpy der Uni Reutlingen
  - *model2*: Anni's KI-Modell aus ihrer Masterarbeit vom Nov.25 (Uni Münster)

- Modelle, die `None/Background` mit hoher Wahrscheinlichkeit erkennen, dürfen nicht zum Löschen der vogelhaltigen Bilder führen. Deshalb werden auch hochprozentige `None/Background` Bilder und Einstufungen nicht behalten. Modellen ohne `None/Background` wird unterhalb einer Erkennungsschwelle (empirisch, z.B. 50%) ein `None` nachträglich zugeteilt.

- Kodierung: Die 30 Bilder sind benannt als `yyyy-mm-dd_hhMMss.msecs.X.jpg (X = 0–29)`. *modelY* hat ein spezelles *birdclassifyY.py*, welches jeweils das Prefix `yyyy-mm-dd_hhMMss.msecs` als Kommandozeilenargument erhält und sein Resultat ins `prefix.csv` schreibt. Haben alle Modelle dorthin geschrieben, löscht `crop_imgpool.py` die überflüssigen JPGs. Das ganze wird orchestriert durch `run_classify.sh`.

- Die JPG Images und ihre Diagnosen im `prefix.csv` sind  auf `ramdisk` und werden mit jedem Reboot gelöscht.

- Die Geschwindigkeit der `tflite runtime` wäre auf dem Raspberry durch verschiedene Maßnahmen sogar noch steigerbar, z.B. Python threads (`interpreter = Interpreter(model_path=MODEL_PATH, num_threads=4)`= XNNPACK delegate, PIL decoder buffer, input tensor preallocation.

- *Tensorflow Lite C API* ermöglicht die Anwendung trainierter Modelle in C ohne Umweg über Python. Auch diese API wäre noch beschleunigbar durch *NEON acceleration /XNNPACK threads /zero-copy tensors*.

- Tensorflow Lite C API Install on Trixie: `sudo apt install libtensorflow-lite-dev`, checke mit `ldconfig -p | grep tensorflow`. Damit wird `gcc -ltensorflow-lite`verfügbar. Das hat ein paar wenige *Core TFLite operators* eingebaut, die aber für unsere Bild-Modelle genügen.

  - jedoch brauchen die BirdNET .tflite Modelle zur Audio-WAV-Klassifizierung zusätzlich ein `gcc -ltensorflowlite_flex` für ihren eingebauten *TF Op* `FlexRFFT`. Dieses Tensorflow Model hat nämlich `fast fourier transformation` und `MEL spectrogram processing` intern. Man kann dann entweder Python mit [full tensorflow](https://github.com/tensorflow/tensorflow) nehmen (`pip install tensorflow-cpu`) oder `ltensorflowlite_flex`bauen, wozu man statt `cmake` aber `bazel` braucht. Nur *TFLite* geht mit *CMake*, größere *TensorFlow* Projekte immer mit *Bazel*.

````
cd ~
sudo apt install bazel -> geht nicht
=> curl -L -o bazelisk https://github.com/bazelbuild/bazelisk/releases/latest/download/bazelisk-linux-arm64
	chmod +x bazelisk
	sudo mv bazelisk /usr/local/bin/bazel
	bazel version
git clone --depth 1 https://github.com/tensorflow/tensorflow.git
cd tensorflow
bazel build //tensorflow/lite/delegates/flex:tensorflowlite_flex
(or with ending ssh:
nohup bazel build //tensorflow/lite/delegates/flex:tensorflowlite_flex > build.log 2>&1 &
tail -f build.log)

oder zeitsparender (30 min, 3 GB):
yes "" | ./configure (skips interactive shortcut)
bazel build --config=opt --copt=-O3 --define=tflite_with_select_tf_ops=true //tensorflow/lite/delegates/flex:tensorflowlite_flex

-> output: bazel-bin/tensorflow/lite/delegates/flex/libtensorflowlite_flex.so
(or search by: find $(bazel info output_base) -name "*tensorflowlite_flex*.so" 2>/dev/null)
sudo cp bazel-bin/tensorflow/lite/delegates/flex/libtensorflowlite_flex.so /usr/local/lib/
sudo ldconfig
ldconfig -p | grep flex
````
- `run_classify.sh` ist ein Softlink, der auf `run_classify_C.sh` = *Tensorflow_Lite_C_API* oder auf `run_classify_orig.sh` = *Python_tflite_runtime* (pyenv python 3.11) ausgerichtet werden kann.

  Näheres siehe im [Blog](https://herbbetz.github.io/betzBirdiary/posts/2026-02-10-tflite/).
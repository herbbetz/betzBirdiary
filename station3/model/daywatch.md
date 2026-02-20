<!--keywords[daywatch,KI-Model,ramdisk]-->

**Doku zu daywatch**

- 30 aus jedem Vogelvideo ausgekoppelte JPG Images werden nach KI-ermittelter Erkennungsrate auf die zwei eindeutigsten vogelhaltigen Bilder reduziert. 

- mehrere KI-Modelle im Vergleich (in der Reihenfolge ihrer zeitlichen Verfügbarkeit):

  - *model0*: ursprüngliche KI-Analyse der birdiary Plattform (Uni Münster)
  - *model1*: LogChirpy der Uni Reutlingen
  - *model2*: Anni's KI-Modell aus ihrer Masterarbeit vom Nov.25 (Uni Münster)

- Modelle, die `None/Background` mit hoher Wahrscheinlichkeit erkennen, dürfen nicht zum Löschen der vogelhaltigen Bilder führen. Deshalb werden auch hochprozentige `None/Background` Bilder und Einstufungen nicht behalten. Modellen ohne `None/Background` wird unterhalb einer Erkennungsschwelle (empirisch, z.B. 50%) ein `None` nachträglich zugeteilt.

- Kodierung: Die 30 Bilder sind benannt als `yyyy-mm-dd_hhMMss.msecs.X.jpg (X = 0–29)`. *modelY* hat ein spezelles *birdclassifyY.py*, welches das Prefix `yyyy-mm-dd_hhMMss.msecs` erhält und sein Resultat ins `prefix.csv` schreibt. Haben alle Modelle dorthin geschrieben, löscht `crop_imgpool.py` die überflüssigen JPGs. Das ganze wird orchestriert durch `run_classify.sh`.

- Die JPG Images und ihre Diagnosen sind  auf `ramdisk` und werden mit jedem Reboot gelöscht.

  Näheres siehe im [Blog](https://herbbetz.github.io/betzBirdiary/posts/2026-02-10-tflite/).
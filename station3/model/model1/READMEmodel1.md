**model1**

- tflite model von [Bird-Classifier](https://github.com/rprkh/Bird-Classifier), auch verwendet von [LogChirpy](https://github.com/mklemmingen/LogChirpy) (Uni Reutlingen)

| | Bird Image Model |
|---|---|
| **Purpose** | Classify bird **photos** (JPG/PNG) |
| **Input** | 224 x 224 x 3 RGB image, Float32, normalized to [-1, 1] |
| **Output classes** | **400** bird species |
| **Label format** | English common names, external text format |
| **Architecture** | MobileNetV2 (image CNN) |
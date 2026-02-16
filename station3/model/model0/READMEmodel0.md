**Model0**

- dies ist das .tflite Vogelbild-Modell, das birdiary auf seinem Server verwendet (Herkunft unbekannt).

- dazu extrahiert es jeden zehnten Frame aus dem hochgeladenen Vogelvideo:

  ``` Line 699 in api/api.py
  for fno in range(0, total_frames, 10):
          cap.set(cv2.CAP_PROP_POS_FRAMES, fno)
          _, image = cap.read()
          result.append(classify(image))
  ```



|                    | Bird Image Model                             |
| ------------------ | -------------------------------------------- |
| **Purpose**        | Classify bird **photos** (JPG/PNG)           |
| **Input**          | 224 x 224 x 3 RGB image, raw_uint8           |
| **Output classes** | **964** bird species                         |
| **Label format**   | Scientific Latin Names, external text format |
| **Architecture**   | MobileNetV2 CNN                                         |
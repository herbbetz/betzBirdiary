settings/settings.html könnte durch einen Button in config3.html aufgerufen werden. Es gibt:

- statische Settings: können wie bei calibratehx711.py in configbird3.py (auch in config.sh) eingetragen werden. Werden erst durch ein Reboot neu gelesen. Beispiel: maxVideos
- dynamische Settings: werden mit laufenden Programmen wie mainFoBird ausgetauscht, also zu deren Laufzeit via Flask gelesen und verändert. Beispiel: Bildhelligkeit
-  Aber wie stellt man deren Werte ökonomisch auf der Webpage dar? Nur Lese- oder auch Schreibmodus?
- Kann python oder bash seine statischen Werte aus einem config.json lesen, das eine Webpage auch darstellen (und verändern) kann? Ja, weil import das config.py nicht nur liest, sondern ausführt. Nur bei einem write/change müsste dieses ein lock haben, da von mehreren Quellen möglich. Problem der JSON Validierung!!
- schau in formeln/sliders auf das `<input type="range" class="slider" value="5" min="1" max="10" id="amprange">Amplitude <span id="ampshow">5</span><br>`. 
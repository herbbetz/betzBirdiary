<!--keywords[ADC,Falstad,Fritzing,Dehnmesstreifen,Hx711,load_cell,Wheatstone]-->

Mit [Falstad](https://www.falstad.com/circuit/) kann man folgende Schaltung für den [Dehnmesstreifen](https://circuitjournal.com/four-wire-load-cell-with-HX711) (strain gauge, load cell) imitieren und den hx711 mit einem Potentiometer testen. Die Simulation zeigt, dass bei 5V DC, selbst wenn die Widerstände der wheatstone Widerstandsanordnung nur 100 Ohm betrügen, nur eine Spannung von 2.5 V für den Raspi Messeingang resultiert.

A+ mit A- kurzschließen (E+, E- frei) ist ein Standardtest für Null Input zur Hx711-Platine, die dann als digitalen Output nur ein bischen *noise* um die Null herum anzeigen sollte und andernfalls Probleme hätte mit Verdrahtung, Minus-Erdung usw.

| 711out                                                       | RPin | Reihe/Spalte | GPIO | Fun  |
| :--- | :--: | :--: | :--: | :--: |
| (VDD)                                                        | 1    | r2s1 |      | 3.5V |
| VCC                                                          | 2    | r1s1 |      | 5 V  |
| DAT                                                          | 11 | r2s6 | 17 |      |
| CLK                                                          | 16 | r1s8 | 23 |      |
| GND                                                          | 6    | r1s3 |||

<img src="image19.png" alt="RPi4B" style="zoom:75%;" />
<img src="wheatstone.jpg" alt="skizze" style="zoom:50%;" /> <img src="circuit-20250620-0550.svg" alt="wstone_falstad" style="zoom:100%;" /> <img src="wheatstone_bb.svg" alt="wstone_fritzing" style="zoom:75%;" />
<!--keywords[booterror,debug,HDMI,SDkartenschonung,UART]-->

**Boot Debugging des Raspberry 4B SBC**

- vor dem Netzwerk gibt es Meldungen über Mikro-HDMI / USB-Keyboard

- das UART-Interface (Baud rate 115200-8N1) kann den Bootprozess noch vor dem Laden des Linuxkernel loggen.
  - Terminal Programm: Putty, screen, minicom, kermit

  - `enable_uart=1` in `/boot/firmware/config.txt` (Grundeinstellung in dietPi)

  - USB-TTL-Adapter: Adapter TX → Pi GPIO 15 (RXD); Adapter RX → Pi GPIO 14 (TXD); Adapter GND → Pi GPIO any GND



  - https://itsfoss.com/use-uart-raspberry-pi/ , typische Adapterchips: CH340G, CP2102, FT232,

    https://www.amazon.de/AZDelivery-AZDELFTDI-CH340-USB-Konverter/dp/B07N7MC999/ref=asc_df_B07N7MC999

  - Adapter Outputs: TX, RX, GND, 5V, 3V

  - old adapter for ESP-01 programming, Windows and Ubuntu usually have driver support for CH340G.

    <img src="ch340G.jpg" alt="ch340G" style="zoom:25%;" />

````
[ GND ] [ GPIO2 ]
[ GPIO0 ] [ RX ]
[ CH_PD ] [ TX ]
[ RST ] [ VCC (3.3V) ]
````

**SD Card Schonung**

- Das 7-fache Blinken beim Booten bedeutet ein Problem beim Hochfahren, meist durch Schädigung der SD card, die unter Windows noch lesbar sein kann, aber nicht mehr das `boot/kernel8.img` lädt.
- Maßnahmen zur Schonung der SD-Karte:
	- `camdata.json` über `ramdisk` schreiben (mainFoBird) und lesen (flaskBird)
	- Logdateien während Produktivbetrieb nach `/dev/null` (startup.sh, ,mdroid.sh)
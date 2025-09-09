<!--keywords[Container,Docker]-->
**Vorteile**
- Zum Verteilen von Updates nur Update des Containers unabhängig vom Hostsystem. Kein Neueinstellen des WLAN im Hostsystem.

**Nachteile**
- Ein Container (z.B. Docker) müsste dasselbe Betriebssystem (z.B. bookworm) beinhalten und letztlich auf die Hardware (Kamera, GPIO) zugreifen über das Hostsystem. Neben dem Hostsystem wäre also auch das Containersystem zu pflegen.
- Das doppelte System wäre auch schwieriger zu entwickeln.
- Es könnte aus mehreren Containern bestehen, einen für die Kamera, einen für die Waage usw.

**Technik**
- Über 'Multistage Builds' können aus einem Container, der die Buildtools beinhaltet, die resultierenden Executables dann in einen Container ohne die Buildtools kopiert werden. Aufwändig, aber dadurch wird der Container schlanker.
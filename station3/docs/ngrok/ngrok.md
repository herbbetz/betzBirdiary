<!--keywords[Fernsupport,ngrok,ssh]-->

NGROK ist ein 'reverse tunneling provider'. Ich verwende ihn zum Aufbau einer Verbindung zwecks Fernwartung und Support eines Systemes auf dem Raspberry. Das ermöglicht eine ssh-Verbindung, die der Kunde im Raspberry Terminal beim Support anfordert. Dazu muss er nicht einmal einen Port in seinem Heimrouter freigeben. Er verbindet seinen Raspberry mit NGROK durch das Kommando `ngrok tcp 22`. Dies zeigt ihm Daten an wie `Forwarding tcp://0.tcp.ngrok.io:12345 -> localhost:22`, die er dem Support mitteilt. Der Support kann sich dann in seinen Raspberry einloggen mit `ssh pi@0.tcp.ngrok.io -p 12345` und eine Fehlersuche durchführen. Und das im Freemium Modell, also gratis.



**Installation:** 

Auf dem Raspberry installiert wurde der NGROK Client durch folgende Kommandos als user 'pi':

- `curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
    && echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" \
    | sudo tee /etc/apt/sources.list.d/ngrok.list \
    && sudo apt update`
- `sudo apt install ngrok`
- `ngrok authtoken <my-ngrok-authtoken>` (erhalten vom [Ngrok Provider](https://dashboard.ngrok.com/authtokens) )



**Konfiguration:** 

- das Authtoken ist gespeichert in `~/.config/ngrok/ngrok.yml`, was auch durch `ngrok config check` angezeigt wird.

- `ngrok config edit` ermöglicht gleichzeitig mehrere Tunnel, z.B. ssh und http:8080 
```
  version: 2
  authtoken: <YOUR_AUTH_TOKEN> 
  tunnels:

    ssh:
      addr: 22
      proto: tcp

    web:
      addr: 8080
      proto: http
```
- `ngrok start ssh web` oder `ngrok start --all` aktiviert dann die Tunnel.


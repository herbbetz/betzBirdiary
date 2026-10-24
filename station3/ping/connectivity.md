<!--keywords[connectivity,mtr,online,ping,upload]-->

## Connection Test zu wiediversistmeingarten.org

- `mtr-tiny` (my traceroute) erweitert `ping`
- siehe Endpoints `/ping` und `/curl` in `flaskBird3.py` und `curltest.html`

```bash
ping -c 200 -i 0.2 fritz.box (200 packets with interval 0.2 secs)
ping -c 200 -i 0.2 wiediversistmeingarten.org

mtr -r -w -c 100 wiediversistmeingarten.org

sudo apt install mtr-tiny
sudo mtr -rwbzc 100 -i 0.5 wiediversistmeingarten.org          # ICMP: loss and latency per hop
sudo mtr -rwbzc 100 -i 0.5 -T -P 443 wiediversistmeingarten.org # TCP/443, closer to real traffic
curl -o /dev/null -s -w 'dns %{time_namelookup} tcp %{time_connect} tls %{time_appconnect} ttfb %{time_starttransfer} total %{time_total}\n' https://wiediversistmeingarten.org

sudo mtr -rwbzc 100 -i 0.5 wiediversistmeingarten.org; iw dev wlan0 link; iw dev wlan0 get power_save

iw dev wlan0 link; iw dev wlan0 station dump | grep -E 'signal|retries|failed|bitrate'
sudo iw dev wlan0 set power_save off   # temporary, until reboot
GW=$(ip route | awk '/default/{print $3; exit}'); sudo mtr -rwc 200 -i 0.2 $GW; sudo mtr -rwbzc 100 -i 0.5 wiediversistmeingarten.org
```
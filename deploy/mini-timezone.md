# Mini PC clock (Berlin)

System timezone (logs, `timedatectl`, all services) — run once on the mini with sudo:

```bash
sudo timedatectl set-timezone Europe/Berlin
timedatectl status
```

NTP stays on (Chrony/systemd-timesyncd). No router change.

User session TZ for `systemctl --user` services is optional via `~/.config/environment.d/tz.conf` containing `TZ=Europe/Berlin`, then `systemctl --user daemon-reload`.

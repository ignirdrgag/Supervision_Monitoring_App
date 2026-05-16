# Supervision des machines physiques 192.168.1.133 et 192.168.1.124

Le poste superviseur est `192.168.1.116`. Lance le backend et le frontend dessus, puis installe l'agent sur chaque machine Linux a superviser.

## 1. Configurer l'email sur le superviseur

Copie `.env.example` vers `.env` et remplace les valeurs SMTP:

```bash
cp .env.example .env
```

Pour Gmail, utilise un mot de passe d'application, pas le mot de passe normal du compte.

## 2. Demarrer l'application sur 192.168.1.116 sans Docker

Terminal 1, backend Django:

```bash
cd /home/kruger/Supervision_Monitoring_App
./scripts/start-backend.sh
```

Terminal 2, frontend React:

```bash
cd /home/kruger/Supervision_Monitoring_App
./scripts/start-frontend.sh
```

Interface: `http://192.168.1.116:5173`
API: `http://192.168.1.116:8000/api`

Si tu preferes lancer les commandes manuellement:

```bash
cd /home/kruger/Supervision_Monitoring_App/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata demo
python manage.py runserver 0.0.0.0:8000
```

Puis dans un autre terminal:

```bash
cd /home/kruger/Supervision_Monitoring_App/frontend
npm install
VITE_API_BASE=http://192.168.1.116:8000/api npm run dev -- --host 0.0.0.0
```

## 3. Installer l'agent sur 192.168.1.133

Copie `agents/linux_agent.py` sur la machine `192.168.1.133`, par exemple dans `/opt/supervision-ia/linux_agent.py`, puis lance:

```bash
export SUPERVISION_API_URL=http://192.168.1.116:8000/api
export AGENT_INGEST_TOKEN=token-long-et-secret
export AGENT_HOSTNAME=machine-192-168-1-133
export AGENT_IP_ADDRESS=192.168.1.133
export MONITOR_SERVICES=ssh:22:tcp:high,apache2:80:tcp:critical
export MONITOR_ALLOWED_LISTEN_PORTS=22,80,443
python3 /opt/supervision-ia/linux_agent.py --interval 5
```

Adapte `MONITOR_SERVICES` aux vrais services de la machine: `nginx:80:tcp:critical`, `mysql:3306:tcp:critical`, `postgresql:5432:tcp:critical`, etc.

## 4. Installer l'agent sur 192.168.1.124

```bash
export SUPERVISION_API_URL=http://192.168.1.116:8000/api
export AGENT_INGEST_TOKEN=token-long-et-secret
export AGENT_HOSTNAME=machine-192-168-1-124
export AGENT_IP_ADDRESS=192.168.1.124
export MONITOR_SERVICES=ssh:22:tcp:high,apache2:80:tcp:critical
export MONITOR_ALLOWED_LISTEN_PORTS=22,80,443
python3 /opt/supervision-ia/linux_agent.py --interval 5
```

## 5. Activer l'agent au demarrage avec systemd

Exemple de service `/etc/systemd/system/supervision-agent.service`:

```ini
[Unit]
Description=Agent Supervision IA
After=network-online.target

[Service]
Environment=SUPERVISION_API_URL=http://192.168.1.116:8000/api
Environment=AGENT_INGEST_TOKEN=token-long-et-secret
Environment=MONITOR_SERVICES=ssh:22:tcp:high,apache2:80:tcp:critical
Environment=MONITOR_ALLOWED_LISTEN_PORTS=22,80,443
Environment=ALLOW_REMOTE_REBOOT=true
ExecStart=/usr/bin/python3 /opt/supervision-ia/linux_agent.py --interval 5
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activation:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now supervision-agent
sudo systemctl status supervision-agent
```

`ALLOW_REMOTE_REBOOT=true` est obligatoire pour autoriser le bouton `Redemarrer` depuis le superviseur. Sans cette variable, l'agent refuse la commande et marque l'action en echec.

## 6. Alerte quand une machine ne repond plus

Sur le superviseur, execute cette commande toutes les 5 secondes avec un timer systemd:

```bash
cd /home/kruger/Supervision_Monitoring_App/backend
. .venv/bin/activate
python manage.py check_agents_stale --max-age-seconds 5
```

Si aucun agent n'a envoye de donnees depuis plus de 5 secondes, le serveur passe hors ligne et une alerte email critique est creee.

Exemple systemd sur le superviseur pour verifier toutes les 5 secondes.

Fichier `/etc/systemd/system/supervision-stale-check.service`:

```ini
[Unit]
Description=Verification des agents Supervision IA silencieux

[Service]
Type=oneshot
WorkingDirectory=/home/kruger/Supervision_Monitoring_App/backend
ExecStart=/home/kruger/Supervision_Monitoring_App/backend/.venv/bin/python manage.py check_agents_stale --max-age-seconds 5
```

Fichier `/etc/systemd/system/supervision-stale-check.timer`:

```ini
[Unit]
Description=Lance la verification des agents toutes les 5 secondes

[Timer]
OnBootSec=5
OnUnitActiveSec=5
AccuracySec=1
Unit=supervision-stale-check.service

[Install]
WantedBy=timers.target
```

Activation:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now supervision-stale-check.timer
systemctl list-timers supervision-stale-check.timer
```

## 7. Detection de trafic suspect

L'agent detecte:

- debit entrant superieur a `MONITOR_MAX_RX_MBPS`, par defaut `80`;
- debit sortant superieur a `MONITOR_MAX_TX_MBPS`, par defaut `80`;
- connexions TCP etablies superieures a `MONITOR_MAX_CONNECTIONS`, par defaut `200`;
- ports en ecoute absents de `MONITOR_ALLOWED_LISTEN_PORTS` et de `MONITOR_SERVICES`.

Exemple plus strict:

```bash
export MONITOR_MAX_RX_MBPS=20
export MONITOR_MAX_TX_MBPS=10
export MONITOR_MAX_CONNECTIONS=80
export MONITOR_ALLOWED_LISTEN_PORTS=22,80,443
```

Cette detection est faite depuis chaque machine. Pour analyser tout le reseau, il faut ajouter une sonde IDS comme Suricata sur un port miroir du switch ou sur la passerelle.

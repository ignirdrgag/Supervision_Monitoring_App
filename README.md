# Supervision IA - Monitoring et Administration

Application de supervision des serveurs et services d'un reseau d'entreprise, construite avec Django et React.

## Fonctionnalites

- Tableau de bord des serveurs, services, alertes et incidents.
- API REST Django pour l'inventaire, les metriques, les alertes et les actions d'administration.
- Frontend React moderne avec vues dashboard, infrastructure, alertes, agents IA et administration.
- Agents IA integres pour analyser les incidents, evaluer les risques et proposer des remediations.
- Agents de collecte avec endpoint d'ingestion securisable par token.
- Simulation d'un cycle de monitoring depuis l'interface pour generer metriques, alertes et actions.
- Journal des notifications email envoyees, ignorees ou echouees.
- Donnees de demonstration prechargees via fixtures pour demarrer rapidement.

## Structure

```text
backend/
  manage.py
  requirements.txt
  monitoring_platform/
  supervision/
frontend/
  package.json
  src/
```

## Demarrage backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata demo
python manage.py runserver 0.0.0.0:8000
```

API disponible sur `http://192.168.1.116:8000/api/` depuis le reseau local.

Si `python -m venv` echoue sur Ubuntu/Debian, installe d'abord `python3.12-venv`.

## Demarrage frontend

```bash
cd frontend
npm install
VITE_API_BASE=http://192.168.1.116:8000/api npm run dev -- --host 0.0.0.0
```

Interface disponible sur `http://192.168.1.116:5173`.

Pour eviter de retaper ces commandes, tu peux utiliser:

```bash
./scripts/start-backend.sh
./scripts/start-frontend.sh
```

## Agents IA

Le backend expose `/api/ai/analysis/`. L'implementation actuelle produit une analyse deterministe a partir des alertes et metriques locales, ce qui permet de travailler sans cle API. Pour connecter un modele externe, remplacer la logique dans `backend/supervision/services/ai_agents.py`.

## Agents de collecte

Un collecteur peut envoyer ses donnees vers :

```text
POST /api/agents/ingest/
X-Agent-Token: valeur-de-AGENT_INGEST_TOKEN
```

Exemple de payload :

```json
{
  "hostname": "srv-app-01",
  "ip_address": "10.0.10.21",
  "os_family": "Ubuntu 24.04",
  "environment": "production",
  "agent_name": "agent-srv-app-01",
  "metrics": {
    "cpu_usage": 67,
    "memory_usage": 72,
    "disk_usage": 81,
    "network_latency": 24
  },
  "services": [
    {"name": "nginx", "port": 80, "status": "running", "criticality": "high"},
    {"name": "postgresql", "port": 5432, "status": "running", "criticality": "critical"}
  ]
}
```

Depuis l'interface, le bouton `Simuler cycle` appelle `/api/monitoring/simulate/` pour generer un cycle de supervision sans agent externe.

### Superviser une vraie machine Linux avec Apache

Le projet contient un agent sans dependance externe :

```bash
agents/linux_agent.py
```

Sur la machine a superviser, copie le dossier `agents/` ou le fichier `linux_agent.py`, puis lance :

```bash
export SUPERVISION_API_URL=http://IP_DU_BACKEND:8000/api
export AGENT_INGEST_TOKEN=token-long-et-secret
export AGENT_ENVIRONMENT=production
export AGENT_OWNER=equipe-noc
export AGENT_LOCATION=salle-serveur-1
export MONITOR_SERVICES=apache2:80:tcp:critical
python3 linux_agent.py --once
```

Pour superviser Apache en continu toutes les 5 secondes :

```bash
python3 linux_agent.py --interval 5
```

Format de `MONITOR_SERVICES` :

```text
nom:port:protocole:criticite
```

Exemples :

```bash
MONITOR_SERVICES=apache2:80:tcp:critical,mysql:3306:tcp:critical,ssh:22:tcp:high
```

L'agent remonte CPU, RAM, disque, latence reseau, IP, OS, statut des services et heartbeat. Si Apache est arrete ou si le port 80 ne repond pas, le backend cree une alerte, propose une action de redemarrage et envoie un email personnalise pour cette panne.

Exemple systemd minimal sur le serveur supervise :

```ini
[Unit]
Description=Supervision IA Linux Agent
After=network-online.target

[Service]
Environment=SUPERVISION_API_URL=http://IP_DU_BACKEND:8000/api
Environment=AGENT_INGEST_TOKEN=token-long-et-secret
Environment=MONITOR_SERVICES=apache2:80:tcp:critical
ExecStart=/usr/bin/python3 /opt/supervision-ia/linux_agent.py --interval 5
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Notifications email

Lorsqu'une alerte ouverte est creee via l'API `/api/alerts/`, Django envoie une notification email.

Le contenu de l'email est personnalise selon la panne : CPU, memoire, disque, reseau ou service applicatif comme Apache. Le sujet inclut la severite, la categorie et le serveur concerne.

Par defaut, en mode developpement, les emails sont affiches dans la console du backend grace a :

```text
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Pour envoyer de vrais emails, configure ces variables d'environnement :

```bash
ALERT_EMAIL_ENABLED=true
ALERT_ADMIN_EMAIL=admin@entreprise.com
ALERT_EMAIL_RECIPIENTS=noc@entreprise.com,admin@entreprise.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.entreprise.com
EMAIL_PORT=587
EMAIL_HOST_USER=supervision@entreprise.com
EMAIL_HOST_PASSWORD=mot-de-passe-ou-token
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=supervision@entreprise.com
AGENT_INGEST_TOKEN=token-long-et-secret
```

## Tester l'application

1. Demarre les conteneurs :

```bash
docker compose up --build
```

2. Ouvre le frontend :

```text
http://localhost:5173
```

3. Clique sur `Register`, cree un compte, puis tu arrives sur le dashboard.

4. Teste `Logout`, puis reconnecte-toi avec `Login`.

5. Verifie l'API backend :

```text
http://localhost:8000/api/
```

6. Configure l'email Gmail dans un fichier `.env` a la racine du projet :

```bash
ALERT_EMAIL_ENABLED=true
ALERT_EMAIL_RECIPIENTS=monitoringentreprise@gmail.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=monitoringentreprise@gmail.com
EMAIL_HOST_PASSWORD=mot-de-passe-application-gmail
EMAIL_USE_TLS=true
EMAIL_SSL_VERIFY=true
DEFAULT_FROM_EMAIL=monitoringentreprise@gmail.com
```

7. Pour tester l'email d'alerte :

```bash
docker compose exec backend python manage.py simulate_alert
```

Tu dois recevoir un email avec un sujet comme `[Supervision IA] CRITICAL - Simulation alerte critique`.

Pour Gmail, `EMAIL_HOST_PASSWORD` doit etre un mot de passe d'application Gmail, pas le mot de passe normal du compte.

Si ton reseau renvoie une erreur `CERTIFICATE_VERIFY_FAILED` avec certificat auto-signe, tu peux tester en developpement avec :

```bash
EMAIL_BACKEND=supervision.email_backends.ConfigurableTLSBackend
EMAIL_SSL_VERIFY=false
```

En production, garde `EMAIL_SSL_VERIFY=true` et installe le certificat racine de ton entreprise dans l'image Docker.

from dataclasses import dataclass

from supervision.models import Alert, MetricSnapshot, MonitoringAgent, Server


@dataclass
class AgentFinding:
    agent: str
    priority: str
    title: str
    recommendation: str


class IncidentTriageAgent:
    name = "Agent IA - Triage incidents"

    def run(self):
        critical_alerts = Alert.objects.filter(status=Alert.Status.OPEN, severity=Alert.Severity.CRITICAL)
        if critical_alerts.exists():
            first = critical_alerts.select_related("server", "service").first()
            service = f" / {first.service.name}" if first.service else ""
            return AgentFinding(
                self.name,
                "critique",
                f"{critical_alerts.count()} alerte(s) critique(s) ouverte(s)",
                f"Prioriser {first.server.hostname}{service}, verifier les journaux applicatifs et valider un plan de retour arriere.",
            )
        return AgentFinding(
            self.name,
            "normal",
            "Aucune alerte critique ouverte",
            "Maintenir la surveillance et traiter les avertissements selon leur criticite metier.",
        )


class CapacityPlanningAgent:
    name = "Agent IA - Capacite"

    def run(self):
        latest_metrics = MetricSnapshot.objects.select_related("server").order_by("server_id", "-created_at")
        risky = []
        seen = set()
        for metric in latest_metrics:
            if metric.server_id in seen:
                continue
            seen.add(metric.server_id)
            if metric.cpu_usage >= 85 or metric.memory_usage >= 85 or metric.disk_usage >= 85:
                risky.append(metric)

        if risky:
            metric = risky[0]
            return AgentFinding(
                self.name,
                "elevee",
                f"{len(risky)} serveur(s) proche(s) de la saturation",
                f"Augmenter la capacite ou reduire la charge sur {metric.server.hostname}; CPU {metric.cpu_usage}%, RAM {metric.memory_usage}%, disque {metric.disk_usage}%.",
            )
        return AgentFinding(
            self.name,
            "normal",
            "Capacite stable",
            "Aucune saturation immediate detectee sur les dernieres metriques connues.",
        )


class SecurityPostureAgent:
    name = "Agent IA - Securite"

    def run(self):
        offline_or_degraded = Server.objects.filter(status__in=[Server.Status.OFFLINE, Server.Status.DEGRADED])
        if offline_or_degraded.exists():
            hostnames = ", ".join(offline_or_degraded.values_list("hostname", flat=True)[:3])
            return AgentFinding(
                self.name,
                "moyenne",
                "Surface de risque operationnel",
                f"Controler les acces, sauvegardes et journaux sur {hostnames}; isoler uniquement si des indicateurs de compromission sont confirmes.",
            )
        return AgentFinding(
            self.name,
            "normal",
            "Posture nominale",
            "Aucun serveur hors ligne ou degrade dans l'inventaire actuel.",
        )


class AgentFleetAgent:
    name = "Agent IA - Collecte"

    def run(self):
        inactive_agents = MonitoringAgent.objects.exclude(status=MonitoringAgent.Status.ACTIVE)
        if inactive_agents.exists():
            agent = inactive_agents.select_related("server").first()
            return AgentFinding(
                self.name,
                "moyenne",
                f"{inactive_agents.count()} agent(s) de supervision inactif(s)",
                f"Verifier le service agent sur {agent.server.hostname}, la connectivite API et le token d'ingestion.",
            )
        if MonitoringAgent.objects.exists():
            return AgentFinding(
                self.name,
                "normal",
                "Agents de collecte operationnels",
                "Les agents enregistrent correctement leurs heartbeats et metriques.",
            )
        return AgentFinding(
            self.name,
            "moyenne",
            "Aucun agent de collecte enregistre",
            "Installer un agent sur chaque serveur critique ou utiliser l'endpoint d'ingestion pour les collecteurs existants.",
        )


def run_ai_analysis():
    agents = [IncidentTriageAgent(), CapacityPlanningAgent(), SecurityPostureAgent(), AgentFleetAgent()]
    findings = [agent.run().__dict__ for agent in agents]
    score = 100
    for finding in findings:
        score -= {"critique": 30, "elevee": 20, "moyenne": 10}.get(finding["priority"], 0)

    return {
        "health_score": max(score, 0),
        "summary": "Analyse generee par les agents IA a partir des donnees de supervision locales.",
        "findings": findings,
    }

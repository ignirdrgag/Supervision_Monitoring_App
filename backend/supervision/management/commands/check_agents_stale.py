from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from supervision.models import Alert, MonitoringAgent, Server
from supervision.views import _create_open_alert


class Command(BaseCommand):
    help = "Cree une alerte si un agent ne remonte plus de donnees."

    def add_arguments(self, parser):
        parser.add_argument("--max-age-seconds", type=int, default=5, help="Age maximum du heartbeat en secondes.")

    def handle(self, *args, **options):
        max_age_seconds = options["max_age_seconds"]
        limit = timezone.now() - timedelta(seconds=max_age_seconds)
        stale_agents = MonitoringAgent.objects.select_related("server").filter(
            Q(last_heartbeat__lt=limit) | Q(last_heartbeat__isnull=True)
        )
        created_count = 0

        for agent in stale_agents:
            server = agent.server
            agent.status = MonitoringAgent.Status.STALE
            agent.save(update_fields=["status", "updated_at"])

            server.status = Server.Status.OFFLINE
            server.save(update_fields=["status", "updated_at"])

            _, created = _create_open_alert(
                server,
                "Serveur ou agent indisponible",
                (
                    f"Aucune donnee recue de l'agent {agent.name} depuis plus de {max_age_seconds} secondes. "
                    f"La machine {server.hostname} ({server.ip_address}) est consideree hors ligne."
                ),
                Alert.Severity.CRITICAL,
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"{created_count} alerte(s) creee(s)."))

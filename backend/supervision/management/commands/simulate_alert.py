from django.core.management.base import BaseCommand

from supervision.models import Alert, Server, Service
from supervision.services.email_notifications import send_alert_email


class Command(BaseCommand):
    help = "Cree une alerte de test et envoie une notification email."

    def add_arguments(self, parser):
        parser.add_argument("--severity", default=Alert.Severity.CRITICAL, choices=[item[0] for item in Alert.Severity.choices])
        parser.add_argument("--title", default="Simulation alerte critique")

    def handle(self, *args, **options):
        server = Server.objects.first()
        if not server:
            self.stderr.write(self.style.ERROR("Aucun serveur trouve. Lance d'abord: python manage.py loaddata demo"))
            return

        service = Service.objects.filter(server=server).first()
        alert = Alert.objects.create(
            server=server,
            service=service,
            title=options["title"],
            description="Alerte generee pour tester l'envoi email depuis la plateforme de supervision.",
            severity=options["severity"],
            status=Alert.Status.OPEN,
        )
        sent = send_alert_email(alert)

        if sent:
            self.stdout.write(self.style.SUCCESS(f"Alerte #{alert.pk} creee et email envoye."))
        else:
            self.stdout.write(self.style.WARNING(f"Alerte #{alert.pk} creee, mais email non envoye."))

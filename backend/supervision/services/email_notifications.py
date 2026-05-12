import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from supervision.models import AdminNotificationRouting, Alert, AlertNotification


logger = logging.getLogger(__name__)


def _dedupe_emails(emails):
    unique = []
    seen = set()
    for email in emails:
        clean = (email or "").strip()
        if clean and clean.lower() not in seen:
            unique.append(clean)
            seen.add(clean.lower())
    return unique


def get_alert_recipients():
    routed_email = AdminNotificationRouting.objects.filter(pk=1).values_list("active_admin_email", flat=True).first()
    if routed_email:
        return [routed_email]

    configured = list(getattr(settings, "ALERT_EMAIL_RECIPIENTS", []))
    admin_email = getattr(settings, "ALERT_ADMIN_EMAIL", "")

    User = get_user_model()
    staff_emails = User.objects.filter(is_active=True, email__gt="").filter(
        is_staff=True
    ).values_list("email", flat=True)
    superuser_emails = User.objects.filter(is_active=True, email__gt="", is_superuser=True).values_list("email", flat=True)

    return _dedupe_emails([admin_email, *configured, *staff_emails, *superuser_emails])


def _alert_context(alert: Alert):
    title = alert.title.lower()
    service_name = alert.service.name if alert.service else "Serveur"

    if alert.service:
        return {
            "category": "service",
            "impact": f"Le service {service_name} ne repond plus correctement sur {alert.server.hostname}.",
            "actions": [
                f"Verifier l'etat du service: systemctl status {service_name}",
                f"Consulter les journaux: journalctl -u {service_name} -n 80",
                "Tester le port applicatif depuis le reseau de supervision.",
                "Relancer le service uniquement apres validation de la cause probable.",
            ],
        }
    if "cpu" in title:
        return {
            "category": "cpu",
            "impact": "Risque de ralentissement general, timeouts applicatifs et files d'attente longues.",
            "actions": [
                "Identifier les processus consommateurs: top ou ps aux --sort=-%cpu",
                "Verifier les jobs planifies et les traitements batch recents.",
                "Reduire la charge ou basculer le trafic si le serveur est critique.",
            ],
        }
    if "memoire" in title or "ram" in title:
        return {
            "category": "memoire",
            "impact": "Risque d'OOM killer, swap eleve et indisponibilite progressive des services.",
            "actions": [
                "Identifier les processus consommateurs: ps aux --sort=-%mem",
                "Verifier les logs systeme pour OOM killer.",
                "Redemarrer le service fautif si une fuite memoire est confirmee.",
            ],
        }
    if "disque" in title:
        return {
            "category": "disque",
            "impact": "Risque d'echec d'ecriture, arret de base de donnees ou corruption de journaux.",
            "actions": [
                "Verifier l'espace: df -h",
                "Identifier les gros repertoires: du -xh / | sort -h",
                "Purger uniquement les fichiers de logs ou temporaires valides par l'equipe.",
            ],
        }
    if "latence" in title or "reseau" in title:
        return {
            "category": "reseau",
            "impact": "Risque de lenteur applicative, pertes de paquets ou rupture entre services.",
            "actions": [
                "Tester la connectivite: ping, traceroute, curl depuis le serveur.",
                "Verifier interface, erreurs et saturation: ip addr, ip route, ss -tunap.",
                "Controler pare-feu, proxy et equipements reseau intermediaires.",
            ],
        }
    return {
        "category": "general",
        "impact": "Incident operationnel detecte sur l'infrastructure supervisee.",
        "actions": [
            "Ouvrir le dashboard Supervision IA.",
            "Qualifier l'incident et verifier les metriques recentes.",
            "Executer une action d'administration seulement apres validation humaine.",
        ],
    }


def send_alert_email(alert: Alert) -> bool:
    recipients = get_alert_recipients()
    if not settings.ALERT_EMAIL_ENABLED or not recipients:
        AlertNotification.objects.create(
            alert=alert,
            channel=AlertNotification.Channel.EMAIL,
            recipient=",".join(recipients) or "administrateur-non-configure",
            status=AlertNotification.Status.SKIPPED,
            detail="Notifications email desactivees ou aucun administrateur destinataire configure.",
        )
        return False

    alert = Alert.objects.select_related("server", "service").get(pk=alert.pk)
    service_name = alert.service.name if alert.service else "Serveur"
    context = _alert_context(alert)
    subject = f"[Supervision IA][{alert.severity.upper()}][{context['category'].upper()}] {alert.server.hostname} - {alert.title}"
    message = "\n".join(
        [
            "Une nouvelle alerte personnalisee a ete detectee.",
            "",
            f"Titre: {alert.title}",
            f"Severite: {alert.severity}",
            f"Statut: {alert.status}",
            f"Serveur: {alert.server.hostname} ({alert.server.ip_address})",
            f"Service: {service_name}",
            f"Environnement: {alert.server.environment}",
            f"Localisation: {alert.server.location or 'non renseignee'}",
            "",
            "Description:",
            alert.description,
            "",
            "Impact probable:",
            context["impact"],
            "",
            "Actions recommandees:",
            *[f"- {action}" for action in context["actions"]],
            "",
            "Lien operationnel: ouvrir le tableau de bord Supervision IA pour acquitter, resoudre ou lancer une action controlee.",
        ]
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        for recipient in recipients:
            AlertNotification.objects.create(
                alert=alert,
                channel=AlertNotification.Channel.EMAIL,
                recipient=recipient,
                status=AlertNotification.Status.SENT,
            )
        return True
    except Exception as exc:
        logger.exception("Impossible d'envoyer l'email pour l'alerte %s", alert.pk)
        for recipient in recipients:
            AlertNotification.objects.create(
                alert=alert,
                channel=AlertNotification.Channel.EMAIL,
                recipient=recipient,
                status=AlertNotification.Status.FAILED,
                detail=str(exc),
            )
        return False

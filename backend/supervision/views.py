import random
import unicodedata
from datetime import datetime

from django.contrib.auth import authenticate
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import AdministrationAction, AdminNotificationRouting, Alert, AlertNotification, MetricSnapshot, MonitoringAgent, Server, Service
from .serializers import (
    AdministrationActionSerializer,
    AlertSerializer,
    AlertNotificationSerializer,
    MetricSnapshotSerializer,
    MonitoringAgentSerializer,
    RegisterSerializer,
    ServerSerializer,
    ServiceSerializer,
)
from .services.ai_agents import run_ai_analysis
from .services.email_notifications import send_alert_email


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)
    if not user:
        return Response({"detail": "Identifiants invalides."}, status=status.HTTP_400_BAD_REQUEST)

    token, _ = Token.objects.get_or_create(user=user)
    if user.is_staff or user.is_superuser:
        if user.email:
            AdminNotificationRouting.objects.update_or_create(
                pk=1,
                defaults={"active_admin_email": user.email, "active_admin_username": user.username},
            )
    return Response(
        {
            "token": token.key,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }
    )


@api_view(["POST"])
def logout(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser) and request.user.email:
        AdminNotificationRouting.objects.filter(pk=1, active_admin_email=request.user.email).delete()
    if request.auth:
        request.auth.delete()
    return Response({"detail": "Deconnexion effectuee."})


@api_view(["GET"])
def me(request):
    if not request.user.is_authenticated:
        return Response({"detail": "Non authentifie."}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({"id": request.user.id, "username": request.user.username, "email": request.user.email})


class ServerViewSet(viewsets.ModelViewSet):
    queryset = Server.objects.prefetch_related("services", "metrics", "alerts").all()
    serializer_class = ServerSerializer

    @action(detail=True, methods=["post"])
    def reboot(self, request, pk=None):
        server = self.get_object()
        action_obj = AdministrationAction.objects.create(
            action_type=AdministrationAction.ActionType.REBOOT_SERVER,
            target_server=server,
            requested_by=request.user.username,
            status=AdministrationAction.Status.APPROVED,
            notes=(
                "Redemarrage serveur demande depuis la console de supervision. "
                "L'agent executera la commande au prochain heartbeat si ALLOW_REMOTE_REBOOT=true."
            ),
        )
        return Response(AdministrationActionSerializer(action_obj).data, status=status.HTTP_201_CREATED)


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related("server").all()
    serializer_class = ServiceSerializer


class MonitoringAgentViewSet(viewsets.ModelViewSet):
    queryset = MonitoringAgent.objects.select_related("server").all()
    serializer_class = MonitoringAgentSerializer


class MetricSnapshotViewSet(viewsets.ModelViewSet):
    queryset = MetricSnapshot.objects.select_related("server").all()
    serializer_class = MetricSnapshotSerializer


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related("server", "service").all()
    serializer_class = AlertSerializer

    def perform_create(self, serializer):
        alert = serializer.save()
        if alert.status == Alert.Status.OPEN:
            send_alert_email(alert)


class AlertNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlertNotification.objects.select_related("alert", "alert__server").all()
    serializer_class = AlertNotificationSerializer


class AdministrationActionViewSet(viewsets.ModelViewSet):
    queryset = AdministrationAction.objects.select_related("target_server", "target_service").all()
    serializer_class = AdministrationActionSerializer

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        action_obj = self.get_object()
        if action_obj.status in [AdministrationAction.Status.SUCCESS, AdministrationAction.Status.RUNNING]:
            return Response(self.get_serializer(action_obj).data)

        action_obj.status = AdministrationAction.Status.RUNNING
        action_obj.notes = f"{action_obj.notes}\nExecution lancee par {request.user.username}.".strip()
        action_obj.save(update_fields=["status", "notes", "updated_at"])

        if action_obj.action_type == AdministrationAction.ActionType.RESTART_SERVICE and action_obj.target_service:
            action_obj.target_service.status = Service.Status.RUNNING
            action_obj.target_service.last_check = timezone.now()
            action_obj.target_service.save(update_fields=["status", "last_check"])
        elif action_obj.action_type == AdministrationAction.ActionType.REBOOT_SERVER:
            action_obj.status = AdministrationAction.Status.APPROVED
            action_obj.notes = f"{action_obj.notes}\nRedemarrage transmis a l'agent.".strip()
            action_obj.save(update_fields=["status", "notes", "updated_at"])
            return Response(self.get_serializer(action_obj).data)
        elif action_obj.action_type == AdministrationAction.ActionType.RUN_DIAGNOSTIC:
            MetricSnapshot.objects.create(
                server=action_obj.target_server,
                cpu_usage=random.randint(20, 70),
                memory_usage=random.randint(25, 75),
                disk_usage=random.randint(30, 82),
                network_latency=random.randint(5, 90),
            )
        elif action_obj.action_type == AdministrationAction.ActionType.ISOLATE_SERVER:
            action_obj.target_server.status = Server.Status.MAINTENANCE
            action_obj.target_server.save(update_fields=["status", "updated_at"])

        action_obj.status = AdministrationAction.Status.SUCCESS
        action_obj.notes = f"{action_obj.notes}\nOperation terminee par le moteur d'administration.".strip()
        action_obj.save(update_fields=["status", "notes", "updated_at"])
        return Response(self.get_serializer(action_obj).data)


def _create_open_alert(server, title, description, severity, service=None):
    alert, created = Alert.objects.get_or_create(
        server=server,
        service=service,
        title=title,
        status=Alert.Status.OPEN,
        defaults={"description": description, "severity": severity},
    )
    if created:
        send_alert_email(alert)
    return alert, created


def _metric_value(metrics, key):
    try:
        return float(metrics.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _evaluate_server_health(server, metric):
    server.status = Server.Status.ONLINE
    recommendations = []

    if metric.cpu_usage >= 90:
        server.status = Server.Status.DEGRADED
        _create_open_alert(
            server,
            "CPU critique",
            f"Utilisation CPU a {metric.cpu_usage}% sur {server.hostname}.",
            Alert.Severity.CRITICAL,
        )
        recommendations.append(AdministrationAction.ActionType.RUN_DIAGNOSTIC)
    if metric.memory_usage >= 88:
        server.status = Server.Status.DEGRADED
        _create_open_alert(
            server,
            "Memoire critique",
            f"Utilisation memoire a {metric.memory_usage}% sur {server.hostname}.",
            Alert.Severity.CRITICAL,
        )
        recommendations.append(AdministrationAction.ActionType.RUN_DIAGNOSTIC)
    if metric.disk_usage >= 90:
        server.status = Server.Status.DEGRADED
        _create_open_alert(
            server,
            "Disque presque plein",
            f"Espace disque utilise a {metric.disk_usage}% sur {server.hostname}.",
            Alert.Severity.WARNING,
        )
    if metric.network_latency >= 180:
        server.status = Server.Status.DEGRADED
        _create_open_alert(
            server,
            "Latence reseau elevee",
            f"Latence mesuree a {metric.network_latency} ms sur {server.hostname}.",
            Alert.Severity.WARNING,
        )

    server.last_seen = timezone.now()
    server.save(update_fields=["status", "last_seen", "updated_at"])

    for action_type in set(recommendations):
        AdministrationAction.objects.get_or_create(
            action_type=action_type,
            target_server=server,
            status=AdministrationAction.Status.PENDING,
            defaults={"notes": "Action recommandee automatiquement par l'agent IA."},
        )


def _evaluate_service_health(server, service):
    if service.status not in [Service.Status.STOPPED, Service.Status.DEGRADED]:
        return None

    severity = Alert.Severity.CRITICAL if service.criticality == Service.Criticality.CRITICAL else Alert.Severity.WARNING
    title = f"Service {service.name} indisponible"
    port_text = f" sur le port {service.port}" if service.port else ""
    description = (
        f"Le service {service.name}{port_text} est dans l'etat {service.status} sur {server.hostname}. "
        "Cette alerte provient d'un agent de collecte installe sur une machine reelle."
    )
    alert, created = _create_open_alert(server, title, description, severity, service=service)
    if created:
        AdministrationAction.objects.get_or_create(
            action_type=AdministrationAction.ActionType.RESTART_SERVICE,
            target_server=server,
            target_service=service,
            status=AdministrationAction.Status.PENDING,
            defaults={"notes": f"Redemarrage recommande suite a l'alerte {alert.id}."},
        )
    return alert


def _evaluate_network_security(server, network_security):
    if not network_security or network_security.get("status") != "suspicious":
        return None

    events = network_security.get("events") or ["Anomalie reseau detectee par l'agent."]
    description = "\n".join(
        [
            "Trafic reseau suspect detecte sur la machine supervisee.",
            f"Debit entrant: {network_security.get('rx_mbps', 0)} Mbps",
            f"Debit sortant: {network_security.get('tx_mbps', 0)} Mbps",
            f"Connexions TCP etablies: {network_security.get('established_connections', 0)}",
            "Evenements:",
            *[f"- {event}" for event in events],
        ]
    )
    return _create_open_alert(
        server,
        "Trafic reseau suspect",
        description,
        Alert.Severity.WARNING,
    )


def _pending_agent_commands(server):
    actions = AdministrationAction.objects.filter(
        target_server=server,
        target_service__isnull=True,
        action_type=AdministrationAction.ActionType.REBOOT_SERVER,
        status=AdministrationAction.Status.APPROVED,
    )[:1]
    commands = []
    for action_obj in actions:
        action_obj.status = AdministrationAction.Status.RUNNING
        action_obj.notes = f"{action_obj.notes}\nCommande remise a l'agent a {timezone.now().isoformat()}.".strip()
        action_obj.save(update_fields=["status", "notes", "updated_at"])
        commands.append({"id": action_obj.id, "action_type": action_obj.action_type})
    return commands


@api_view(["GET"])
def dashboard(request):
    server_counts = Server.objects.values("status").annotate(count=Count("id"))
    service_counts = Service.objects.values("status").annotate(count=Count("id"))
    alert_counts = Alert.objects.values("severity").filter(status=Alert.Status.OPEN).annotate(count=Count("id"))
    latest_alerts = Alert.objects.select_related("server", "service").all()[:5]
    latest_notifications = AlertNotification.objects.select_related("alert").all()[:5]
    latest_metrics = MetricSnapshot.objects.select_related("server").order_by("server_id", "-created_at")

    metrics_by_server = {}
    for metric in latest_metrics:
        metrics_by_server.setdefault(metric.server_id, metric)

    return Response(
        {
            "servers_total": Server.objects.count(),
            "services_total": Service.objects.count(),
            "open_alerts": Alert.objects.filter(status=Alert.Status.OPEN).count(),
            "critical_alerts": Alert.objects.filter(status=Alert.Status.OPEN, severity=Alert.Severity.CRITICAL).count(),
            "active_agents": MonitoringAgent.objects.filter(status=MonitoringAgent.Status.ACTIVE).count(),
            "agents_total": MonitoringAgent.objects.count(),
            "servers_by_status": {item["status"]: item["count"] for item in server_counts},
            "services_by_status": {item["status"]: item["count"] for item in service_counts},
            "alerts_by_severity": {item["severity"]: item["count"] for item in alert_counts},
            "latest_alerts": AlertSerializer(latest_alerts, many=True).data,
            "latest_notifications": AlertNotificationSerializer(latest_notifications, many=True).data,
            "latest_metrics": MetricSnapshotSerializer(metrics_by_server.values(), many=True).data,
        }
    )


@api_view(["GET"])
def ai_analysis(request):
    return Response(run_ai_analysis())


@api_view(["GET"])
def topology(request):
    servers = Server.objects.prefetch_related("services").all()
    return Response(
        {
            "nodes": [
                {
                    "id": f"server-{server.id}",
                    "label": server.hostname,
                    "type": "server",
                    "status": server.status,
                }
                for server in servers
            ]
            + [
                {
                    "id": f"service-{service.id}",
                    "label": service.name,
                    "type": "service",
                    "status": service.status,
                    "server": service.server_id,
                }
                for server in servers
                for service in server.services.all()
            ],
            "links": [
                {"source": f"server-{service.server_id}", "target": f"service-{service.id}"}
                for server in servers
                for service in server.services.all()
            ],
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def agent_ingest(request):
    expected_token = getattr(settings, "AGENT_INGEST_TOKEN", "")
    provided_token = request.headers.get("X-Agent-Token", "")
    if expected_token and provided_token != expected_token:
        return Response({"detail": "Token agent invalide."}, status=status.HTTP_403_FORBIDDEN)

    hostname = request.data.get("hostname")
    ip_address = request.data.get("ip_address")
    if not hostname or not ip_address:
        return Response({"detail": "hostname et ip_address sont obligatoires."}, status=status.HTTP_400_BAD_REQUEST)

    server, _ = Server.objects.update_or_create(
        hostname=hostname,
        defaults={
            "ip_address": ip_address,
            "os_family": request.data.get("os_family", "Linux"),
            "environment": request.data.get("environment", "production"),
            "owner": request.data.get("owner", ""),
            "location": request.data.get("location", ""),
            "last_seen": timezone.now(),
        },
    )
    agent, _ = MonitoringAgent.objects.update_or_create(
        server=server,
        defaults={
            "name": request.data.get("agent_name", f"agent-{hostname}"),
            "version": request.data.get("agent_version", "1.0.0"),
            "status": MonitoringAgent.Status.ACTIVE,
            "last_heartbeat": timezone.now(),
            "last_payload": request.data,
        },
    )

    metrics = request.data.get("metrics") or {}
    metric = MetricSnapshot.objects.create(
        server=server,
        cpu_usage=_metric_value(metrics, "cpu_usage"),
        memory_usage=_metric_value(metrics, "memory_usage"),
        disk_usage=_metric_value(metrics, "disk_usage"),
        network_latency=_metric_value(metrics, "network_latency"),
    )
    _evaluate_server_health(server, metric)

    for item in request.data.get("services", []):
        if not item.get("name"):
            continue
        service, _ = Service.objects.update_or_create(
            server=server,
            name=item.get("name"),
            defaults={
                "port": item.get("port"),
                "protocol": item.get("protocol", "tcp"),
                "status": item.get("status", Service.Status.RUNNING),
                "criticality": item.get("criticality", Service.Criticality.MEDIUM),
                "last_check": timezone.now(),
            },
        )
        _evaluate_service_health(server, service)

    _evaluate_network_security(server, request.data.get("network_security") or {})

    return Response(
        {
            "server": ServerSerializer(server).data,
            "agent": MonitoringAgentSerializer(agent).data,
            "commands": _pending_agent_commands(server),
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def agent_command_complete(request, action_id):
    expected_token = getattr(settings, "AGENT_INGEST_TOKEN", "")
    provided_token = request.headers.get("X-Agent-Token", "")
    if expected_token and provided_token != expected_token:
        return Response({"detail": "Token agent invalide."}, status=status.HTTP_403_FORBIDDEN)

    try:
        action_obj = AdministrationAction.objects.get(pk=action_id)
    except AdministrationAction.DoesNotExist:
        return Response({"detail": "Commande introuvable."}, status=status.HTTP_404_NOT_FOUND)

    result_status = request.data.get("status")
    detail = request.data.get("detail", "")
    action_obj.status = (
        AdministrationAction.Status.SUCCESS
        if result_status == "success"
        else AdministrationAction.Status.FAILED
    )
    action_obj.notes = f"{action_obj.notes}\nRetour agent: {detail or result_status}.".strip()
    action_obj.save(update_fields=["status", "notes", "updated_at"])
    return Response(AdministrationActionSerializer(action_obj).data)


def _ascii_text(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return normalized.encode("ascii", "ignore").decode("ascii")


def _pdf_escape(value):
    return _ascii_text(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_text(x, y, text, size=10, color="0.10 0.16 0.25"):
    return f"BT /F1 {size} Tf {color} rg {x} {y} Td ({_pdf_escape(text)}) Tj ET\n"


def _pdf_rect(x, y, width, height, color):
    return f"{color} rg {x} {y} {width} {height} re f\n"


def _build_monitoring_pdf():
    servers = list(Server.objects.prefetch_related("services", "alerts", "metrics").all())
    alerts = list(Alert.objects.select_related("server", "service").all()[:8])
    notifications = list(AlertNotification.objects.select_related("alert").all()[:6])
    width, height = 595, 842
    content = []

    content.append(_pdf_rect(0, 0, width, height, "0.95 0.97 1"))
    content.append(_pdf_rect(0, 760, width, 82, "0.06 0.13 0.25"))
    content.append(_pdf_text(40, 802, "Rapport de supervision", 22, "1 1 1"))
    content.append(_pdf_text(40, 780, f"Genere le {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 10, "0.82 0.88 0.96"))

    open_alerts = Alert.objects.filter(status=Alert.Status.OPEN).count()
    critical_alerts = Alert.objects.filter(status=Alert.Status.OPEN, severity=Alert.Severity.CRITICAL).count()
    active_agents = MonitoringAgent.objects.filter(status=MonitoringAgent.Status.ACTIVE).count()
    stats = [
        ("Serveurs", Server.objects.count(), "0.86 0.92 1"),
        ("Services", Service.objects.count(), "0.84 0.97 0.89"),
        ("Alertes ouvertes", open_alerts, "1 0.93 0.84"),
        ("Critiques", critical_alerts, "1 0.88 0.88"),
        ("Agents actifs", active_agents, "0.91 0.89 1"),
    ]
    x = 40
    for label, value, color in stats:
        content.append(_pdf_rect(x, 700, 96, 44, color))
        content.append(_pdf_text(x + 10, 724, label, 8))
        content.append(_pdf_text(x + 10, 706, value, 16, "0.06 0.13 0.25"))
        x += 104

    y = 660
    content.append(_pdf_text(40, y, "Inventaire et dernieres metriques", 14))
    y -= 24
    content.append(_pdf_rect(40, y - 6, 515, 20, "0.88 0.92 0.97"))
    content.append(_pdf_text(50, y, "Serveur", 9))
    content.append(_pdf_text(205, y, "IP", 9))
    content.append(_pdf_text(300, y, "Statut", 9))
    content.append(_pdf_text(380, y, "CPU/RAM/Disque", 9))
    y -= 24

    for server in servers[:10]:
        metric = server.metrics.first()
        metric_text = "N/A"
        if metric:
            metric_text = f"{metric.cpu_usage}% / {metric.memory_usage}% / {metric.disk_usage}%"
        content.append(_pdf_text(50, y, server.hostname, 9))
        content.append(_pdf_text(205, y, server.ip_address, 9))
        content.append(_pdf_text(300, y, server.status, 9))
        content.append(_pdf_text(380, y, metric_text, 9))
        y -= 18

    y -= 16
    content.append(_pdf_text(40, y, "Alertes recentes", 14))
    y -= 22
    for alert in alerts:
        service = alert.service.name if alert.service else "serveur"
        content.append(_pdf_text(50, y, f"[{alert.severity}] {alert.server.hostname} - {service}", 9, "0.55 0.12 0.12"))
        y -= 13
        content.append(_pdf_text(62, y, alert.title, 9))
        y -= 17

    y -= 8
    content.append(_pdf_text(40, y, "Dernieres notifications email", 14))
    y -= 22
    for notification in notifications:
        content.append(_pdf_text(50, y, f"{notification.recipient} - {notification.status}", 9))
        y -= 15

    stream = "".join(content).encode("latin-1", errors="ignore")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


@api_view(["GET"])
def report_pdf(request):
    response = HttpResponse(_build_monitoring_pdf(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="rapport-supervision.pdf"'
    return response


@api_view(["POST"])
def simulate_monitoring(request):
    servers = list(Server.objects.prefetch_related("services").all())
    if not servers:
        return Response({"detail": "Aucun serveur disponible pour la simulation."}, status=status.HTTP_400_BAD_REQUEST)

    generated = {"metrics": 0, "alerts": 0, "actions": 0}
    for server in servers:
        agent, _ = MonitoringAgent.objects.get_or_create(
            server=server,
            defaults={"name": f"agent-{server.hostname}", "last_heartbeat": timezone.now()},
        )
        agent.status = MonitoringAgent.Status.ACTIVE
        agent.last_heartbeat = timezone.now()
        agent.save(update_fields=["status", "last_heartbeat", "updated_at"])

        metric = MetricSnapshot.objects.create(
            server=server,
            cpu_usage=random.randint(15, 96),
            memory_usage=random.randint(20, 94),
            disk_usage=random.randint(25, 96),
            network_latency=random.randint(5, 240),
        )
        generated["metrics"] += 1
        before_alerts = Alert.objects.filter(status=Alert.Status.OPEN).count()
        before_actions = AdministrationAction.objects.filter(status=AdministrationAction.Status.PENDING).count()
        _evaluate_server_health(server, metric)

        for service in server.services.all():
            if random.random() < 0.16:
                service.status = random.choice([Service.Status.DEGRADED, Service.Status.STOPPED])
            else:
                service.status = Service.Status.RUNNING
            service.last_check = timezone.now()
            service.save(update_fields=["status", "last_check"])
            if service.status != Service.Status.RUNNING:
                before = Alert.objects.filter(status=Alert.Status.OPEN).count()
                alert = _evaluate_service_health(server, service)
                if alert and Alert.objects.filter(status=Alert.Status.OPEN).count() > before:
                    generated["alerts"] += 1

        generated["alerts"] += max(Alert.objects.filter(status=Alert.Status.OPEN).count() - before_alerts, 0)
        generated["actions"] += max(
            AdministrationAction.objects.filter(status=AdministrationAction.Status.PENDING).count() - before_actions,
            0,
        )

    return Response({"detail": "Cycle de monitoring simule.", **generated})

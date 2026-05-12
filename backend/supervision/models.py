from django.db import models


class Server(models.Model):
    class Status(models.TextChoices):
        ONLINE = "online", "En ligne"
        DEGRADED = "degraded", "Degrade"
        OFFLINE = "offline", "Hors ligne"
        MAINTENANCE = "maintenance", "Maintenance"

    hostname = models.CharField(max_length=120, unique=True)
    ip_address = models.GenericIPAddressField(unique=True)
    os_family = models.CharField(max_length=80)
    environment = models.CharField(max_length=60, default="production")
    owner = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONLINE)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hostname


class MonitoringAgent(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Actif"
        STALE = "stale", "Silencieux"
        DISABLED = "disabled", "Desactive"

    server = models.OneToOneField(Server, related_name="agent", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40, default="1.0.0")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    last_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} @ {self.server.hostname}"


class Service(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Actif"
        DEGRADED = "degraded", "Degrade"
        STOPPED = "stopped", "Arrete"
        UNKNOWN = "unknown", "Inconnu"

    class Criticality(models.TextChoices):
        LOW = "low", "Faible"
        MEDIUM = "medium", "Moyenne"
        HIGH = "high", "Haute"
        CRITICAL = "critical", "Critique"

    server = models.ForeignKey(Server, related_name="services", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    port = models.PositiveIntegerField(null=True, blank=True)
    protocol = models.CharField(max_length=20, default="tcp")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    criticality = models.CharField(max_length=20, choices=Criticality.choices, default=Criticality.MEDIUM)
    last_check = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("server", "name")

    def __str__(self):
        return f"{self.name} @ {self.server.hostname}"


class MetricSnapshot(models.Model):
    server = models.ForeignKey(Server, related_name="metrics", on_delete=models.CASCADE)
    cpu_usage = models.DecimalField(max_digits=5, decimal_places=2)
    memory_usage = models.DecimalField(max_digits=5, decimal_places=2)
    disk_usage = models.DecimalField(max_digits=5, decimal_places=2)
    network_latency = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Alert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Avertissement"
        CRITICAL = "critical", "Critique"

    class Status(models.TextChoices):
        OPEN = "open", "Ouverte"
        ACKNOWLEDGED = "acknowledged", "Acquittee"
        RESOLVED = "resolved", "Resolue"

    server = models.ForeignKey(Server, related_name="alerts", on_delete=models.CASCADE)
    service = models.ForeignKey(Service, related_name="alerts", on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=180)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class AlertNotification(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        WEBHOOK = "webhook", "Webhook"

    class Status(models.TextChoices):
        SENT = "sent", "Envoyee"
        FAILED = "failed", "Echec"
        SKIPPED = "skipped", "Ignoree"

    alert = models.ForeignKey(Alert, related_name="notifications", on_delete=models.CASCADE)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.EMAIL)
    recipient = models.CharField(max_length=180)
    status = models.CharField(max_length=20, choices=Status.choices)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AdminNotificationRouting(models.Model):
    active_admin_email = models.EmailField(unique=True)
    active_admin_username = models.CharField(max_length=150, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.active_admin_email


class AdministrationAction(models.Model):
    class ActionType(models.TextChoices):
        RESTART_SERVICE = "restart_service", "Redemarrer service"
        PATCH_SERVER = "patch_server", "Appliquer correctifs"
        ISOLATE_SERVER = "isolate_server", "Isoler serveur"
        RUN_DIAGNOSTIC = "run_diagnostic", "Diagnostic"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        APPROVED = "approved", "Approuvee"
        RUNNING = "running", "En cours"
        SUCCESS = "success", "Terminee"
        FAILED = "failed", "Echec"

    action_type = models.CharField(max_length=40, choices=ActionType.choices)
    target_server = models.ForeignKey(Server, related_name="actions", on_delete=models.CASCADE)
    target_service = models.ForeignKey(Service, related_name="actions", on_delete=models.SET_NULL, null=True, blank=True)
    requested_by = models.CharField(max_length=120, default="agent-ia")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

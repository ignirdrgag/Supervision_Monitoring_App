# Generated for the supervision monitoring starter application.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Server",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hostname", models.CharField(max_length=120, unique=True)),
                ("ip_address", models.GenericIPAddressField(unique=True)),
                ("os_family", models.CharField(max_length=80)),
                ("environment", models.CharField(default="production", max_length=60)),
                ("owner", models.CharField(blank=True, max_length=120)),
                ("location", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("online", "En ligne"),
                            ("degraded", "Degrade"),
                            ("offline", "Hors ligne"),
                            ("maintenance", "Maintenance"),
                        ],
                        default="online",
                        max_length=20,
                    ),
                ),
                ("last_seen", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Service",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("port", models.PositiveIntegerField(blank=True, null=True)),
                ("protocol", models.CharField(default="tcp", max_length=20)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("running", "Actif"),
                            ("degraded", "Degrade"),
                            ("stopped", "Arrete"),
                            ("unknown", "Inconnu"),
                        ],
                        default="running",
                        max_length=20,
                    ),
                ),
                (
                    "criticality",
                    models.CharField(
                        choices=[
                            ("low", "Faible"),
                            ("medium", "Moyenne"),
                            ("high", "Haute"),
                            ("critical", "Critique"),
                        ],
                        default="medium",
                        max_length=20,
                    ),
                ),
                ("last_check", models.DateTimeField(blank=True, null=True)),
                (
                    "server",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="services", to="supervision.server"),
                ),
            ],
            options={"unique_together": {("server", "name")}},
        ),
        migrations.CreateModel(
            name="MetricSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cpu_usage", models.DecimalField(decimal_places=2, max_digits=5)),
                ("memory_usage", models.DecimalField(decimal_places=2, max_digits=5)),
                ("disk_usage", models.DecimalField(decimal_places=2, max_digits=5)),
                ("network_latency", models.DecimalField(decimal_places=2, max_digits=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "server",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metrics", to="supervision.server"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField()),
                (
                    "severity",
                    models.CharField(
                        choices=[("info", "Info"), ("warning", "Avertissement"), ("critical", "Critique")],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Ouverte"), ("acknowledged", "Acquittee"), ("resolved", "Resolue")],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "server",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to="supervision.server"),
                ),
                (
                    "service",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="alerts",
                        to="supervision.service",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AdministrationAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("restart_service", "Redemarrer service"),
                            ("patch_server", "Appliquer correctifs"),
                            ("isolate_server", "Isoler serveur"),
                            ("run_diagnostic", "Diagnostic"),
                        ],
                        max_length=40,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "En attente"),
                            ("approved", "Approuvee"),
                            ("running", "En cours"),
                            ("success", "Terminee"),
                            ("failed", "Echec"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("requested_by", models.CharField(default="agent-ia", max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "target_server",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="supervision.server"),
                ),
                (
                    "target_service",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="actions",
                        to="supervision.service",
                    ),
                ),
            ],
        ),
    ]

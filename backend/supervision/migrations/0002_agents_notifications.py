# Generated for dynamic monitoring agents and alert notification audit.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("supervision", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonitoringAgent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("version", models.CharField(default="1.0.0", max_length=40)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Actif"),
                            ("stale", "Silencieux"),
                            ("disabled", "Desactive"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("last_heartbeat", models.DateTimeField(blank=True, null=True)),
                ("last_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "server",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="agent", to="supervision.server"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AlertNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "channel",
                    models.CharField(choices=[("email", "Email"), ("webhook", "Webhook")], default="email", max_length=20),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("sent", "Envoyee"), ("failed", "Echec"), ("skipped", "Ignoree")],
                        max_length=20,
                    ),
                ),
                ("recipient", models.CharField(max_length=180)),
                ("detail", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "alert",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="supervision.alert"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]

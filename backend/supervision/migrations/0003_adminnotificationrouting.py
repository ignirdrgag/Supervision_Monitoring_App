# Generated for administrator email routing.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("supervision", "0002_agents_notifications"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminNotificationRouting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("active_admin_email", models.EmailField(max_length=254, unique=True)),
                ("active_admin_username", models.CharField(blank=True, max_length=150)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

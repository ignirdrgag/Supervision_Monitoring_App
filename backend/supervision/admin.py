from django.contrib import admin

from .models import (
    AdministrationAction,
    AdminNotificationRouting,
    Alert,
    AlertNotification,
    MetricSnapshot,
    MonitoringAgent,
    Server,
    Service,
)


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("hostname", "ip_address", "environment", "status", "owner", "last_seen")
    list_filter = ("status", "environment", "os_family")
    search_fields = ("hostname", "ip_address", "owner")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "server", "port", "status", "criticality")
    list_filter = ("status", "criticality")
    search_fields = ("name", "server__hostname")


@admin.register(MonitoringAgent)
class MonitoringAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "server", "version", "status", "last_heartbeat")
    list_filter = ("status", "version")
    search_fields = ("name", "server__hostname")


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ("server", "cpu_usage", "memory_usage", "disk_usage", "network_latency", "created_at")
    list_filter = ("created_at",)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "server", "service", "severity", "status", "created_at")
    list_filter = ("severity", "status")
    search_fields = ("title", "description")


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = ("alert", "channel", "recipient", "status", "created_at")
    list_filter = ("channel", "status")
    search_fields = ("alert__title", "recipient", "detail")


@admin.register(AdminNotificationRouting)
class AdminNotificationRoutingAdmin(admin.ModelAdmin):
    list_display = ("active_admin_email", "active_admin_username", "updated_at")
    search_fields = ("active_admin_email", "active_admin_username")


@admin.register(AdministrationAction)
class AdministrationActionAdmin(admin.ModelAdmin):
    list_display = ("action_type", "target_server", "target_service", "requested_by", "status", "created_at")
    list_filter = ("action_type", "status")

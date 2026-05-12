from django.contrib.auth.models import User
from rest_framework import serializers

from .models import AdministrationAction, Alert, AlertNotification, MetricSnapshot, MonitoringAgent, Server, Service


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MetricSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricSnapshot
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class MonitoringAgentSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source="server.hostname", read_only=True)

    class Meta:
        model = MonitoringAgent
        fields = "__all__"


class AlertSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source="server.hostname", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Alert
        fields = "__all__"


class AlertNotificationSerializer(serializers.ModelSerializer):
    alert_title = serializers.CharField(source="alert.title", read_only=True)

    class Meta:
        model = AlertNotification
        fields = "__all__"


class ServerSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)
    agent = MonitoringAgentSerializer(read_only=True)
    latest_metric = serializers.SerializerMethodField()
    open_alerts = serializers.SerializerMethodField()

    class Meta:
        model = Server
        fields = "__all__"

    def get_latest_metric(self, obj):
        metric = obj.metrics.first()
        return MetricSnapshotSerializer(metric).data if metric else None

    def get_open_alerts(self, obj):
        return obj.alerts.filter(status=Alert.Status.OPEN).count()


class AdministrationActionSerializer(serializers.ModelSerializer):
    target_server_name = serializers.CharField(source="target_server.hostname", read_only=True)
    target_service_name = serializers.CharField(source="target_service.name", read_only=True)

    class Meta:
        model = AdministrationAction
        fields = "__all__"

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdministrationActionViewSet,
    AlertNotificationViewSet,
    AlertViewSet,
    MetricSnapshotViewSet,
    MonitoringAgentViewSet,
    ServerViewSet,
    ServiceViewSet,
    ai_analysis,
    agent_ingest,
    dashboard,
    login,
    logout,
    me,
    register,
    simulate_monitoring,
    topology,
)


router = DefaultRouter()
router.register("servers", ServerViewSet)
router.register("services", ServiceViewSet)
router.register("agents", MonitoringAgentViewSet)
router.register("metrics", MetricSnapshotViewSet)
router.register("alerts", AlertViewSet)
router.register("notifications", AlertNotificationViewSet)
router.register("actions", AdministrationActionViewSet)

urlpatterns = [
    path("auth/register/", register, name="register"),
    path("auth/login/", login, name="login"),
    path("auth/logout/", logout, name="logout"),
    path("auth/me/", me, name="me"),
    path("dashboard/", dashboard, name="dashboard"),
    path("ai/analysis/", ai_analysis, name="ai-analysis"),
    path("agents/ingest/", agent_ingest, name="agent-ingest"),
    path("monitoring/simulate/", simulate_monitoring, name="simulate-monitoring"),
    path("topology/", topology, name="topology"),
    path("", include(router.urls)),
]

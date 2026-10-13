from django.urls import path
from . import views

urlpatterns = [
    # IoT Ingestion
    path("sensorreading/", views.CurrentSensorView.as_view(), name="ingest-telemetry"),
    #frondend
    
    # Dashboards & Lists
    path("devices/<str:device_id>/live/", views.SensorDataView.as_view(), name="device-live-dashboard"),
    path("home/", views.HomeView.as_view(), name="user-home-summary"),
    path("devices/", views.DeviceListView.as_view(), name="user-device-list"),
    path("devicelist/", views.DeviceListView.as_view(), name="user-device-list-alias"),
    
    # Analytics & History
    path("history/<str:device_id>/", views.SensorHistoryView.as_view(), name="sensor-time-series"),
    path("summary/<str:device_id>/", views.DailySummaryView.as_view(), name="daily-summary-legacy"),
    path("daily-summary/<str:device_id>/", views.DailySummaryView.as_view(), name="photoperiod-analytics"),
    
    # Alarms
    path("alarms/warning/", views.WarningAlarmListView.as_view(), name="active-warnings-all"), # For listing all unread
    path("alarms/<str:device_id>/", views.WarningAlarmListView.as_view(), name="active-warnings-device"),
]

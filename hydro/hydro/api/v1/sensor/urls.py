from django.urls import path
from hydro.api.v1.sensor import views 

urlpatterns = [
    path("sensorreading/", views.CurrentSensorView.as_view(), name="current-sensor-reading"),
    path("sensorreading/<str:device_id>/", views.CurrentSensorView.as_view(), name="current-sensor-reading-with-device-id"),
    path("devicelist/", views.DeviceListView.as_view(), name="device-list"),
    
    # Harmonized endpoints for mobile app
    path("devices/", views.DeviceListView.as_view(), name="mobile-device-list"),
    path("devices/<str:device_id>/live/", views.SensorDataView.as_view(), name="mobile-device-live"),
    path("home/", views.HomeView.as_view(), name="mobile-home"),
    path("alarms/warning/", views.WarningAlarmView.as_view(), name="warning-alarms"),
]

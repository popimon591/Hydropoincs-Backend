from django.contrib import admin

from sensor.models import (
    CurrentSensorData,
    DailySensorSummary,
    Device,
    PlantCategory,
    SensorDataHistory,
    WarningAlarm,
)

# Register your models here.
admin.site.register(Device)
admin.site.register(CurrentSensorData)
admin.site.register(SensorDataHistory)
admin.site.register(DailySensorSummary)
admin.site.register(WarningAlarm)
admin.site.register(PlantCategory)
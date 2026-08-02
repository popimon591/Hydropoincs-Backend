from django.contrib import admin

from sensor.models import Device,CurrentSensorData,SensorDataHistory

# Register your models here.
admin.site.register(Device)
admin.site.register(CurrentSensorData)
admin.site.register(SensorDataHistory)
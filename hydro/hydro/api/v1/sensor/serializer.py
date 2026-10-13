from rest_framework import serializers
from sensor.models import Device, CurrentSensorData, SensorDataHistory, WarningAlarm, DailySensorSummary

class DeviceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'device_id', 'device_name', 'location', 'type', 'created_at']

class SensorViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrentSensorData
        fields = [
            "temperature", "humidity", "tds", "light_intensity",
            "daily_light_hours", "daily_dli", "updated_at",
            "water_temperature", "water_level", "ph", "soil_ph", "soil_moisture", "ec"
        ]

class SensorDataHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorDataHistory
        fields = "__all__"

class DailySensorSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySensorSummary
        fields = ["date", "total_light_hours", "total_dli"]

class WarningAlarmSerializer(serializers.ModelSerializer):
    at = serializers.DateTimeField(source="created_at", format="%Y-%m-%dT%H:%M:%SZ")
    device_name = serializers.CharField(source="device.device_name", read_only=True)

    class Meta:
        model = WarningAlarm
        fields = ["id", "parameter", "value", "level", "message", "is_resolved", "at", "device_name"]

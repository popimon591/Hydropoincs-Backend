from django.db import models
from user.models import CustomUser
from django.utils import timezone

irrigation_type = [
    ('Hydroponics_water', 'Hydroponics'),
    ('Soil_farming', 'Soil'),
    ('Aquaponics', 'Aquaponics'),
    ('DWC', 'Deep Water Culture'),
    ('NFT', 'Nutrient Film Technique'),
    ('Microgreens', 'Microgreens'),
    ('Tower', 'Hyroponics_Tower')
]


class Device(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="devices"
    )
    device_id = models.CharField(max_length=100, unique=True)
    device_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True, null=True)
    type = models.CharField(max_length=50, choices=irrigation_type, default='Hydroponics_water')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_name} ({self.device_id})"


class CurrentSensorData(models.Model):
    device = models.OneToOneField(
        Device,
        on_delete=models.CASCADE,
        related_name="current_sensor"
    )

    # Mandatory
    temperature = models.FloatField(default=0.0)
    humidity = models.FloatField(default=0.0)
    tds = models.FloatField(default=0.0)
    light_intensity = models.FloatField(default=0.0)

    # Accumulated Light Data (Today)
    daily_light_hours = models.FloatField(
        default=0.0, help_text="Total active daylight hours today"
    )
    daily_dli = models.FloatField(
        default=0.0, help_text="Daily Light Integral in mol/m²/day"
    )
    last_light_date = models.DateField(
        default=timezone.now,
        help_text="Date tracker for midnight rollover",
    )

    # Hydroponics
    water_temperature = models.FloatField(blank=True, null=True)
    water_level = models.FloatField(blank=True, null=True)
    ph = models.FloatField(blank=True, null=True)

    # Soil farming optional
    soil_ph = models.FloatField(blank=True, null=True)
    soil_moisture = models.FloatField(blank=True, null=True)
    ec = models.FloatField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.device.device_id} - Current Data"


class SensorDataHistory(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="history"
    )

    # Mandatory
    temperature = models.FloatField(default=0.0)
    humidity = models.FloatField(default=0.0)
    tds = models.FloatField(default=0.0)
    light_intensity = models.FloatField(default=0.0)

    # Optional fields
    water_temperature = models.FloatField(blank=True, null=True)
    water_level = models.FloatField(blank=True, null=True)
    ph = models.FloatField(blank=True, null=True)
    soil_ph = models.FloatField(blank=True, null=True)
    soil_moisture = models.FloatField(blank=True, null=True)
    ec = models.FloatField(blank=True, null=True)
    
    # NPK Readings
    nitrogen_read = models.FloatField(blank=True, null=True)
    potassium_read = models.FloatField(blank=True, null=True)
    phosphorus_read = models.FloatField(blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp'])
        ]

    def __str__(self):
        return f"{self.device.device_id} - {self.timestamp}"


class DailySensorSummary(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="daily_summaries"
    )
    date = models.DateField()
    total_light_hours = models.FloatField(default=0.0)
    total_dli = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("device", "date")
        ordering = ['-date']


class WarningAlarm(models.Model):
    class Level(models.TextChoices):
        MIN = "MIN", "Minimum Breach"
        WARNING = "WARNING", "Warning Threshold"
        MAX = "MAX", "Maximum Breach"

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="warning_alarms"
    )
    parameter = models.CharField(max_length=100)
    value = models.FloatField()
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.WARNING
    )
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.device.device_name} - {self.parameter} ({self.level})"


class PlantCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    min_air_temp = models.FloatField()
    max_air_temp = models.FloatField()
    min_water_temp = models.FloatField()
    max_water_temp = models.FloatField()
    min_humidity = models.FloatField()
    max_humidity = models.FloatField()
    min_ph = models.FloatField()
    max_ph = models.FloatField()
    min_tds = models.FloatField()
    max_tds = models.FloatField()
    min_soil_moisture = models.FloatField(blank=True, null=True)
    max_soil_moisture = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.name

from django.db import models
from user.models import CustomUser


class Device(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="devices"
    )
    device_id = models.CharField(max_length=100, unique=True)
    device_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True, null=True)
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
    temperature = models.FloatField()
    humidity = models.FloatField()
    tds = models.FloatField()
    light_intensity = models.FloatField(
        blank=True, 
        null=True
    )

    # Hydroponics
    water_temperature = models.FloatField(
        blank=True,
        null=True
    )

    water_level = models.FloatField(
        blank=True,
        null=True
    )

    ph = models.FloatField(
        blank=True,
        null=True
    )

    # Soil farming optional
    soil_ph = models.FloatField(
        blank=True,
        null=True
    )

    soil_moisture = models.FloatField(
        blank=True,
        null=True
    )

    ec = models.FloatField(
        blank=True,
        null=True
    )   

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.device.device_id} - Current Data"



class SensorDataHistory(models.Model):

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="history"
    )

    # Mandatory
    temperature = models.FloatField()
    humidity = models.FloatField()
    tds = models.FloatField()

    # Hydroponics
    water_temperature = models.FloatField(
        blank=True,
        null=True
    )

    water_level = models.FloatField(
        blank=True,
        null=True
    )

    ph = models.FloatField(
        blank=True,
        null=True
    )

    # Soil
    soil_ph = models.FloatField(
        blank=True,
        null=True
    )

    soil_moisture = models.FloatField(
        blank=True,
        null=True
    )

    ec = models.FloatField(
        blank=True,
        null=True
    )
    timestamp = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        ordering = ['-timestamp']

        indexes = [
            models.Index(
                fields=['device', '-timestamp']
            )
        ]


    def __str__(self):
        return f"{self.device.device_id} - {self.timestamp}"


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

    min_soil_moisture = models.FloatField(
        blank=True,
    max_length=100,
        null=True
    )
    max_soil_moisture = models.FloatField(
        blank=True, 
        null=True
    )

    def __str__(self):
        return self.name


class Alarm(models.Model):
    class Severity(models.TextChoices):
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="alarms"
    )
    trigger = models.CharField(max_length=100)
    critical_value = models.CharField(max_length=50)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.WARNING
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_dismissed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.device.device_name} - {self.trigger} ({self.severity})"

from django.db.models.signals import post_save
from django.dispatch import receiver

from sensor.models import CurrentSensorData, Device


@receiver(post_save, sender=Device)
def create_current_sensor_data(sender, instance, created, **kwargs):
    """Automatically insert a CurrentSensorData row the moment a new Device is added.

    Later sensor readings for this device must update this same row
    (see CurrentSensorView.put) rather than creating a new one, since
    CurrentSensorData.device is a OneToOneField.
    """
    if created:
        CurrentSensorData.objects.get_or_create(device=instance)

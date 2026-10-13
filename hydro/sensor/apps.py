from django.apps import AppConfig


class SensorConfig(AppConfig):
    name = "sensor"

    def ready(self):
        import sensor.signals  # noqa: F401

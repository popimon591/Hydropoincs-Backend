from django.test import TestCase

from sensor.models import CurrentSensorData, Device, WarningAlarm
from user.models import CustomUser


class WarningAlarmLogicTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone="+1234567890",
            full_name="Test User",
            password="testpass123",
        )
        self.device = Device.objects.create(
            user=self.user,
            device_id="device-001",
            device_name="Greenhouse A",
            location="Room 1",
        )

    def test_alarm_is_created_updated_and_resolved(self):
        data, _ = CurrentSensorData.objects.update_or_create(
            device=self.device,
            defaults={
                "temperature": 35,
                "humidity": 60,
                "tds": 700,
                "light_intensity": 900,
            },
        )

        from hydro.api.v1.sensor.views import CurrentSensorView

        CurrentSensorView()._check_alarms(self.device, data)

        self.assertEqual(WarningAlarm.objects.filter(device=self.device, parameter="Temperature").count(), 1)
        alarm = WarningAlarm.objects.get(device=self.device, parameter="Temperature")
        self.assertFalse(alarm.is_resolved)
        self.assertEqual(alarm.level, WarningAlarm.Level.MAX)

        data.temperature = 29
        CurrentSensorView()._check_alarms(self.device, data)

        self.assertEqual(
            WarningAlarm.objects.filter(device=self.device, parameter="Temperature").count(),
            1,
        )
        alarm.refresh_from_db()
        self.assertTrue(alarm.is_resolved)

    def test_low_alarm_is_created_updated_and_resolved(self):
        # Fixed THRESHOLDS: temperature = [min=10, warn=30, max=35]
        data, _ = CurrentSensorData.objects.update_or_create(
            device=self.device,
            defaults={
                "temperature": 5,  # <= min(10) -> LOW
                "humidity": 60,
                "tds": 700,
                "light_intensity": 900,
            },
        )

        from hydro.api.v1.sensor.views import CurrentSensorView

        # INSERT: LOW alarm created -> is_resolved must be False
        CurrentSensorView()._check_alarms(self.device, data)

        alarm = WarningAlarm.objects.get(device=self.device, parameter="Temperature")
        self.assertFalse(alarm.is_resolved)
        self.assertEqual(alarm.level, WarningAlarm.Level.MIN)

        # UPDATE: still LOW (<= min) -> same alarm updated, is_resolved must stay False
        data.temperature = 8
        CurrentSensorView()._check_alarms(self.device, data)

        self.assertEqual(
            WarningAlarm.objects.filter(device=self.device, parameter="Temperature").count(),
            1,
        )
        alarm.refresh_from_db()
        self.assertFalse(alarm.is_resolved)
        self.assertEqual(alarm.value, 8)

        # NORMAL: value back in optimal range -> existing alarm resolved (is_resolved=True), not deleted
        data.temperature = 20
        CurrentSensorView()._check_alarms(self.device, data)

        alarm.refresh_from_db()
        self.assertTrue(alarm.is_resolved)
        self.assertEqual(WarningAlarm.objects.filter(device=self.device, parameter="Temperature").count(), 1)

    def test_history_keeps_every_reading(self):
        from sensor.models import SensorDataHistory

        readings = [
            {"temperature": 30.0, "humidity": 60.0, "tds": 500.0, "light_intensity": 800.0},
            {"temperature": 31.0, "humidity": 61.0, "tds": 530.0, "light_intensity": 820.0},
            {"temperature": 32.0, "humidity": 62.0, "tds": 540.0, "light_intensity": 850.0},
        ]

        for payload in readings:
            CurrentSensorData.objects.update_or_create(
                device=self.device,
                defaults={**payload},
            )
            SensorDataHistory.objects.create(device=self.device, **payload)

        self.assertEqual(SensorDataHistory.objects.filter(device=self.device).count(), 3)


class CurrentSensorDataDeviceSignalTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone="+1234567891",
            full_name="Signal Test User",
            password="testpass123",
        )

    def test_current_sensor_data_created_when_device_added(self):
        device = Device.objects.create(
            user=self.user,
            device_id="device-signal-001",
            device_name="Greenhouse Signal",
            location="Room 2",
        )

        self.assertEqual(CurrentSensorData.objects.filter(device=device).count(), 1)
        current = CurrentSensorData.objects.get(device=device)
        self.assertEqual(current.temperature, 0.0)

    def test_existing_device_reading_updates_same_row_not_duplicate(self):
        device = Device.objects.create(
            user=self.user,
            device_id="device-signal-002",
            device_name="Greenhouse Signal 2",
            location="Room 3",
        )

        CurrentSensorData.objects.update_or_create(
            device=device,
            defaults={"temperature": 22.5, "humidity": 55.0, "tds": 400.0, "light_intensity": 600.0},
        )
        CurrentSensorData.objects.update_or_create(
            device=device,
            defaults={"temperature": 23.5},
        )

        self.assertEqual(CurrentSensorData.objects.filter(device=device).count(), 1)
        current = CurrentSensorData.objects.get(device=device)
        self.assertEqual(current.temperature, 23.5)

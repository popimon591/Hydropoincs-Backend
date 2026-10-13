from sensor.models import WarningAlarm


def check_warnings(device, update_data):
    """Check and update warning alarms for a device from incoming sensor values."""
    thresholds = {
        "temperature": [10, 30, 35, "°C"],
        "humidity": [30, 70, 75, "%"],
        "tds": [0, 400, 500, "ppm"],
        "light_intensity": [0, 800, 1000, "lux"],
    }

    for param, limits in thresholds.items():
        if param not in update_data:
            continue

        value = update_data.get(param)
        if value is None:
            continue

        min_v, warn_v, max_v, unit = limits
        level = None

        if value <= min_v:
            level = "MIN"
        elif value >= max_v:
            level = "MAX"
        elif value >= warn_v:
            level = "WARNING"

        parameter_name = param.replace("_", " ").title()

        if level is None:
            WarningAlarm.objects.filter(
                device=device,
                parameter=parameter_name,
                is_resolved=False,
            ).update(is_resolved=True)
            continue

        WarningAlarm.objects.update_or_create(
            device=device,
            parameter=parameter_name,
            is_resolved=False,
            defaults={
                "value": value,
                "level": level,
                "message": f"{parameter_name} breach: {value}{unit} (Limits: {min_v}-{max_v})",
            },
        )


def update_warning(device, warning_type, description, severity, critical_value, trigger):
    """Backward-compatible helper for updating a warning by type."""
    parameter_name = warning_type.replace("_", " ").title()
    warning, _ = WarningAlarm.objects.get_or_create(
        device=device,
        parameter=parameter_name,
        defaults={
            "value": critical_value,
            "level": "WARNING",
            "message": description,
            "is_resolved": False,
        },
    )
    warning.value = critical_value
    warning.level = severity if severity in [choice[0] for choice in WarningAlarm.Level.choices] else WarningAlarm.Level.WARNING
    warning.message = description
    warning.is_resolved = False
    warning.save()
    return warning
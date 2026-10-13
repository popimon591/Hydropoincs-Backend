from sensor.models import WarningAlarm

THRESHOLDS = {
    "temperature": [10, 30, 35, "°C"],
    "humidity": [30, 70, 75, "%"],
    "tds": [0, 400, 500, "ppm"],
    "light_intensity": [0, 800, 1000, "lux"],
}


def _get_val(data_source, field_name):
    """Extract numeric value safely from either a dict or a model instance."""
    if isinstance(data_source, dict):
        val = data_source.get(field_name)
    else:
        val = getattr(data_source, field_name, None)

    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def evaluate_alarms_for_device(device, data_source):
    """Evaluates sensor readings against multi-tier thresholds.

    Guarantees strictly ONE WarningAlarm row per (device, parameter):
    - Normal/optimal range: the single row for that parameter is marked is_resolved=True.
    - Breach (MIN/WARNING/MAX): the single row for that parameter is created
      or updated in place, so a severity change (e.g. WARNING -> MAX) updates
      the existing row instead of creating a duplicate.

    Self-heals any pre-existing duplicate rows (device, parameter) by keeping
    only the most recent one and deleting the rest, so this never relies on a
    plain .get() that could raise MultipleObjectsReturned.
    """
    for param, limits in THRESHOLDS.items():
        value = _get_val(data_source, param)
        if value is None:
            continue

        min_v, warn_v, max_v, unit = limits
        level = None
        severity_label = ""

        # Determine threshold breach level
        if value <= min_v:
            level = getattr(WarningAlarm.Level, "MIN", "MIN")
            severity_label = f"CRITICAL: Below Minimum"
        elif value >= max_v:
            level = getattr(WarningAlarm.Level, "MAX", "MAX")
            severity_label = f"CRITICAL: Above Maximum"
        elif value >= warn_v:
            level = getattr(WarningAlarm.Level, "WARNING", "WARNING")
            severity_label = f"WARNING: Above Optimal"

        parameter_name = param.replace("_", " ").title()

        # Self-heal: collapse any pre-existing duplicate rows for this
        # (device, parameter) down to a single, most-recent row before
        # deciding whether to update or create.
        existing_qs = WarningAlarm.objects.filter(
            device=device,
            parameter=parameter_name,
        ).order_by("-created_at")
        existing = existing_qs.first()
        if existing is not None:
            existing_qs.exclude(pk=existing.pk).delete()

        # Reading is within optimal bounds -> resolve the single record for this parameter
        if level is None:
            if existing is not None and not existing.is_resolved:
                existing.is_resolved = True
                existing.save(update_fields=["is_resolved"])
            continue

        message = (
            f"{parameter_name} {severity_label}: {value}{unit} "
            f"(Optimal: {min_v}-{warn_v}{unit}, Max Limit: {max_v}{unit})"
        )

        # Strict single-record guarantee: update the existing row in place, or
        # create a new one if none exists yet for this (device, parameter).
        if existing is not None:
            existing.value = value
            existing.level = level
            existing.message = message
            existing.is_resolved = False
            existing.save(update_fields=["value", "level", "message", "is_resolved"])
        else:
            WarningAlarm.objects.create(
                device=device,
                parameter=parameter_name,
                value=value,
                level=level,
                message=message,
                is_resolved=False,
            )


# Backward-compatible alias
check_warnings = evaluate_alarms_for_device



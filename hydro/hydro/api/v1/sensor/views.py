from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from sensor.models import Device, CurrentSensorData, SensorDataHistory, DailySensorSummary,WarningAlarm
from .alarm_service import evaluate_alarms_for_device
from .serializer import (
    DeviceListSerializer, 
    SensorViewSerializer, 
    SensorDataHistorySerializer, 
    DailySensorSummarySerializer, 
    WarningAlarmSerializer
)

class CurrentSensorView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def put(self, request):
        device_id = request.data.get("device_id")
        user_id = request.data.get("user_id") or request.data.get("user")
        if not device_id or not user_id:
            return Response({"error": "device_id and user_id required"}, status=status.HTTP_400_BAD_REQUEST)

        # 0. Reject unwanted/unregistered devices: check the Device table itself first,
        # independent of the requesting user, so unknown device_ids get a clear error.
        if not Device.objects.filter(device_id=device_id).exists():
            return Response({"error": "Device not existing"}, status=status.HTTP_404_NOT_FOUND)

        device = Device.objects.filter(device_id=device_id, user_id=user_id).first()
        if not device:
            return Response({"error": "Device not registered to this user"}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        today = now.date()
        current_data, created = CurrentSensorData.objects.select_for_update().get_or_create(device=device)

        # 1. Midnight Rollover Logic
        if today > current_data.last_light_date:
            DailySensorSummary.objects.update_or_create(
                device=device, 
                date=current_data.last_light_date,
                defaults={
                    "total_light_hours": current_data.daily_light_hours,
                    "total_dli": current_data.daily_dli
                }
            )
            current_data.daily_light_hours = 0.0
            current_data.daily_dli = 0.0
            current_data.last_light_date = today

        # 2. Scientific Calculations (DLI & Photoperiod)
        elapsed_seconds = (now - current_data.updated_at).total_seconds() if not created else 0
        # Cap elapsed time for safety (max 1 hour per interval)
        elapsed_seconds = min(max(elapsed_seconds, 0), 3600)

        lux = float(request.data.get("light_intensity", current_data.light_intensity))
        ppfd = lux / 75.0
        interval_dli = (ppfd * elapsed_seconds) / 1000000.0
        
        current_data.daily_dli += interval_dli
        if lux >= 200.0:
            current_data.daily_light_hours += elapsed_seconds / 3600.0

        # 3. Update Current Metrics
        fields = [
            "temperature", "humidity", "tds", "light_intensity",
            "water_temperature", "water_level", "ph", "soil_ph", "soil_moisture", "ec",
        ]
        for field in fields:
            if field in request.data:
                setattr(current_data, field, request.data[field])
        
        current_data.save()

        # 4. History Logging - preserve every incoming reading as a new history record
        hist_data = {**request.data, "device": device.pk}
        hist_serializer = SensorDataHistorySerializer(data=hist_data)
        if hist_serializer.is_valid():
            hist_serializer.save()
        else:
            return Response({"error": hist_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # 5. Alarm Threshold Checks
        self._check_alarms(device, current_data)

        return Response({
            "success": True,
            "data": {
                "daily_dli": round(current_data.daily_dli, 4),
                "daily_light_hours": round(current_data.daily_light_hours, 2),
                "updated_at": current_data.updated_at
            }
        })

    def _check_alarms(self, device, data):
        evaluate_alarms_for_device(device, data)

class SensorDataView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, device_id):
        data = CurrentSensorData.objects.filter(
            device__device_id=device_id,
            device__user=request.user
        ).first()
        if not data:
            return Response({"error": "No data found for this device"}, status=404)
        return Response({"success": True, "data": SensorViewSerializer(data).data})

class DeviceListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        devices = Device.objects.filter(user=request.user)
        serializer = DeviceListSerializer(devices, many=True)
        return Response({"success": True, "data": serializer.data})

class HomeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        devices = Device.objects.filter(user=request.user)
        res = []
        for d in devices:
            live = getattr(d, 'current_sensor', None)
            item = DeviceListSerializer(d).data
            item['live'] = SensorViewSerializer(live).data if live else None
            res.append(item)
        return Response({"success": True, "data": {"devices": res}})

class SensorHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, device_id):
        hours = int(request.query_params.get("hours", 24))
        cutoff = timezone.now() - timedelta(hours=hours)
        history = SensorDataHistory.objects.filter(
            device__device_id=device_id,
            device__user=request.user,
            timestamp__gte=cutoff
        ).order_by('timestamp')
        return Response({"success": True, "data": SensorDataHistorySerializer(history, many=True).data})

class DailySummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, device_id):
        summaries = DailySensorSummary.objects.filter(
            device__device_id=device_id,
            device__user=request.user
        ).order_by('-date')[:30]
        return Response({"success": True, "data": DailySensorSummarySerializer(summaries, many=True).data})

class WarningAlarmListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, device_id=None):
        filters = {"device__user": request.user, "is_resolved": False}
        if device_id:
            filters["device__device_id"] = device_id
            
        alarms = WarningAlarm.objects.filter(**filters)
        return Response({"success": True, "data": WarningAlarmSerializer(alarms, many=True).data})

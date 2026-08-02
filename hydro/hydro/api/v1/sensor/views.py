from django.conf import settings
DEBUG = settings.DEBUG

from hydro.api.v1.sensor.serializer import SensorDataHistorySerializer,SensorViewSerializer,DeviceListSerializer, AlarmListSerializer
from sensor.models import Device, CurrentSensorData, Alarm
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny


class CurrentSensorView(APIView):

    permission_classes = ([AllowAny] if DEBUG else [IsAuthenticated])


    def put(self, request):

        device_id = request.data.get("device_id")
        temperature = request.data.get("temperature")
        humidity = request.data.get("humidity")
        tds = request.data.get("tds")
        light_intensity = request.data.get("light_intensity")

        if not device_id:
            return Response(
                {"error": "Device ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if temperature is None and humidity is None and tds is None and light_intensity is None:
            return Response(
                {"error": "Sensor values required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        device = Device.objects.filter(device_id=device_id).first()
        if not device:
            return Response(
                {"error": "Device not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        history_data = request.data.copy()
        history_data["device"] = device.pk

        serializer = SensorDataHistorySerializer(data=history_data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        update_data = {}

        if temperature is not None:
            update_data["temperature"] = temperature

        if humidity is not None:
            update_data["humidity"] = humidity

        if tds is not None:
            update_data["tds"] = tds

        if light_intensity is not None:
            update_data["light_intensity"] = light_intensity

        print('start the data')
        print("Update Data:", update_data)  # Debugging line to check the update_data dictionary
        print("Device:", device)  # Debugging line to check the device object
        print("Request Data:", request.data)  # Debugging line to check the incoming request data

        updated = CurrentSensorData.objects.filter(
            device=device
        ).update(**update_data)

        if updated == 0:
            return Response(
                {"error": "Current sensor data not found for device"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer.save()

        return Response(
            {
                "message": "Sensor data updated and history saved"
            },
            status=status.HTTP_200_OK
        )
class SensorDataView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, device_id):
        current_user = request.user
        device = Device.objects.filter(device_id=device_id, user=current_user).first()
        if not device:
            return Response(
                {"error": "Device not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        current_data = CurrentSensorData.objects.filter(device=device).first()
        if not current_data:
            return Response(
                {"error": "Current sensor data not found for device"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SensorViewSerializer(current_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
class DeviceListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_user = request.user
        devices = Device.objects.filter(user=current_user)
        serializer = DeviceListSerializer(devices, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )


class HomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_user = request.user
        devices = Device.objects.filter(user=current_user)

        device_data = []
        for device in devices:
            d_serializer = DeviceListSerializer(device)
            current_reading = CurrentSensorData.objects.filter(device=device).first()
            r_serializer = SensorViewSerializer(current_reading) if current_reading else None

            d_dict = d_serializer.data
            d_dict['live'] = r_serializer.data if r_serializer else None
            device_data.append(d_dict)

        return Response(
            {
                "success": True,
                "data": {
                    "devices": device_data
                }
            },
            status=status.HTTP_200_OK
        )


class WarningAlarmView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_user = request.user
        alarms = Alarm.objects.filter(device__user=current_user, is_dismissed=False)
        serializer = AlarmListSerializer(alarms, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

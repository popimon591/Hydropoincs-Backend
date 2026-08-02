from sensor.models import CurrentSensorData, Device, SensorDataHistory, Alarm
from rest_framework import serializers


class SensorDataHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = SensorDataHistory
        fields = "__all__"


    def validate_temperature(self, value):

        if value is None:
            raise serializers.ValidationError(
                "Temperature is required."
            )

        if not isinstance(value, (int, float)):
            raise serializers.ValidationError(
                "Temperature must be a number."
            )

        if value < -10 or value > 50:
            raise serializers.ValidationError(
                "Temperature value is invalid."
            )

        return value


    def validate_humidity(self, value):

        if value is None:
            raise serializers.ValidationError(
                "Humidity is required."
            )

        if not isinstance(value, (int, float)):
            raise serializers.ValidationError(
                "Humidity must be a number."
            )

        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Humidity must be between 0 and 100."
            )

        return value


    def validate_tds(self, value):

        if value is None:
            raise serializers.ValidationError(
                "TDS is required."
            )

        if value < 0:
            raise serializers.ValidationError(
                "TDS cannot be negative."
            )

        return value


    def validate_ph(self, value):

        if value is None:
            raise serializers.ValidationError(
                "pH is required."
            )

        if value < 0 or value > 14:
            raise serializers.ValidationError(
                "pH must be between 0 and 14."
            )

        return value


    def validate_ec(self, value):

        if value is None:
            raise serializers.ValidationError(
                "EC is required."
            )

        if value < 0:
            raise serializers.ValidationError(
                "EC cannot be negative."
            )

        return value


    def validate_water_temperature(self, value):

        if value is None:
            raise serializers.ValidationError(
                "Water temperature is required."
            )
        if value < 0 or value > 50:
            raise serializers.ValidationError(
                "Water temperature error."
            )
        return value
    
    def validate_water_level(self, value):

        if value is None:
            raise serializers.ValidationError(
                "Water level is required."
            )
        if value < 0:
            raise serializers.ValidationError(
                "Water level cannot be negative."
            )
        return value
    
    def validate_soil_ph(self, value):

        if value is None:
            raise serializers.ValidationError(
                "Soil pH is required."
            )
        if value < 0 or value > 14:
            raise serializers.ValidationError(
                "Soil pH must be between 0 and 14."
            )
        return value
    def validate_soil_moisture(self, value):

        if value is None:
            raise serializers.ValidationError(
                "Soil moisture is required."
            )
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Soil moisture must be between 0 and 100."
            )
        return value
    
    def validate_light_intensity(self, value):
        if value is None:
            raise serializers.ValidationError(
                "Light intensity is required."
            )
        if value < 0:
            raise serializers.ValidationError(
                "Light intensity cannot be negative."
            )
        return value
    
    def validate(self, data):
        # Ensure that at least one of the optional fields is provided
        optional_fields = ['water_temperature', 'water_level', 'ph', 'soil_ph', 'soil_moisture', 'ec']
        if not any(data.get(field) is not None for field in optional_fields):
            raise serializers.ValidationError(
                "At least one of the optional fields (water_temperature, water_level, ph, soil_ph, soil_moisture, ec) must be provided."
            )
        return data
    
    def create(self, validated_data):
        # Create a new SensorDataHistory instance with the validated data
        sensor_data_history = SensorDataHistory.objects.create(**validated_data)
        return sensor_data_history  
    
class SensorViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = CurrentSensorData
        fields = "__all__"


    def validate(self, data):
        # Ensure that at least one of the optional fields is provided
        optional_fields = ['water_temperature', 'water_level', 'ph', 'soil_ph', 'soil_moisture', 'ec']
        if not any(data.get(field) is not None for field in optional_fields):
            raise serializers.ValidationError(
                "At least one of the optional fields (water_temperature, water_level, ph, soil_ph, soil_moisture, ec) must be provided."
            )
        return data

class DeviceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['device_id', 'device_name', 'location', 'created_at']
    def validate(self, data):
        # Ensure that at least one of the optional fields is provided
        optional_fields = ['device_name']
        if not any(data.get(field) is not None for field in optional_fields):
            raise serializers.ValidationError(
                "At least one of the optional fields ( device_name) must be provided."
            )
        return data


class AlarmListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alarm
        fields = "__all__"

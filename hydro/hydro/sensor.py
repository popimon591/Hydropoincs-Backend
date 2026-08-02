class SinglePlant:

    def __init__(self, sensor_temperature):
        print(type(sensor_temperature))
        self.temperature = sensor_temperature

    def print_temperature(self):
        print(f"Temperature Reading: {self.temperature}°C")




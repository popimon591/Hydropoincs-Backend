import serial
from sensor import SinglePlant

ser = serial.Serial("COM3", 115200)
print(ser)
while True:
    temp = ser.readline().decode().strip()   # e.g. "28.5"
    print('start',temp)
    print(repr(temp))
    #temp = float(temp)  # Convert to float
    #emp = 25.0  # For testing purposes, replace with actual sensor reading
    plant = SinglePlant(temp)
    plant.print_temperature()
   

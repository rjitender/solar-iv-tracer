import serial
import time
import csv

PORT = 'COM5'       
BAUD = 9600
DURATION_SECONDS = 3600   
OUTPUT_FILE = 'sensor_log.csv'

ser = serial.Serial(PORT, BAUD)
time.sleep(2)   

start_time = time.time()

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'thermistor_v', 'photoresistor_v'])

    while time.time() - start_time < DURATION_SECONDS:
        line = ser.readline().decode().strip()
        if line:
            try:
                therm, photo = line.split(',')
                elapsed = round(time.time() - start_time, 1)
                writer.writerow([elapsed, therm, photo])
                print(elapsed, therm, photo)
            except ValueError:
                pass   

ser.close()
print("Logging complete.")
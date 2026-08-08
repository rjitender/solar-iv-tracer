import serial
import csv
import time

PORT = 'COM5'
BAUD = 9600
OUTPUT_FILE = 'iv_sweep_v2.csv'

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(0.5)

rows = []
print("Reading sweep...")

start = time.time()
while time.time() - start < 100:
    line = ser.readline().decode().strip()
    if line:
        try:
            duty, voltage, current = line.split(',')
            rows.append([int(duty), float(voltage), float(current)])
            print(f"duty={duty}  V={voltage}  I={current}")
        except ValueError:
            pass

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['duty_cycle', 'voltage_v', 'current_mA'])
    writer.writerows(rows)

print(f"\nSaved {len(rows)} points to {OUTPUT_FILE}")
ser.close()
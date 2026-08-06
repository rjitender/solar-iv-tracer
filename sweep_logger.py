import serial
import csv
import time

PORT = 'COM5'
BAUD = 9600
OUTPUT_FILE = 'iv_sweep.csv'

ser = serial.Serial(PORT, BAUD)
time.sleep(2)  # let the Arduino reset

rows = []

print("Turn the potentiometer to your first setting, then press Enter to log a reading.")
print("Type 'q' then Enter when you're done sweeping.\n")

while True:
    user_input = input("Press Enter to log (or 'q' to quit): ")
    if user_input.strip().lower() == 'q':
        break

    ser.reset_input_buffer()   # clear out stale buffered lines
    time.sleep(0.3)            # let a fresh line arrive
    line = ser.readline().decode().strip()

    try:
        voltage, current = line.split(',')
        voltage = float(voltage)
        current = float(current)
        label = input("  Label this point (e.g. pot position, or just press Enter to skip): ")
        rows.append([label, voltage, current])
        print(f"  Logged: {voltage} V, {current} mA\n")
    except ValueError:
        print("  Bad reading, try again.\n")

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['label', 'voltage_v', 'current_mA'])
    writer.writerows(rows)

print(f"\nSaved {len(rows)} points to {OUTPUT_FILE}")
ser.close()
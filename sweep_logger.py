"""
Serial logger for the v2 MOSFET-load sweep.

Must match the Arduino sketch's DUTY_START / DUTY_END / DUTY_STEP, and allow
enough wall-clock time for the new settle timings (500 ms per point).
"""

import serial
import csv
import time

PORT = 'COM5'
BAUD = 9600

# Must match the sketch 
DUTY_START = 0
DUTY_END = 255
DUTY_STEP = 1          # 1 for characterisation run, 5 for normal sweeps

EXPECTED_ROWS = len(range(DUTY_START, DUTY_END + 1, DUTY_STEP))

# Each point costs GATE_SETTLE_MS + ADC_SETTLE_MS = 500 ms in the sketch.
# Add headroom so a slow start never truncates the sweep as the row
# counter below is what actually ends the run.
TIMEOUT_S = EXPECTED_ROWS * 0.5 * 1.5 + 30

OUTPUT_FILE = f'iv_sweep_v2_step{DUTY_STEP}.csv'

ser = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(0.5)

rows = []
print(f"Reading sweep: expecting {EXPECTED_ROWS} points, "
      f"about {EXPECTED_ROWS * 0.5:.0f} s.")

start = time.time()
while time.time() - start < TIMEOUT_S and len(rows) < EXPECTED_ROWS:
    line = ser.readline().decode(errors='ignore').strip()
    if not line:
        continue
    try:
        duty, voltage, current = line.split(',')
        rows.append([int(duty), float(voltage), float(current)])
        print(f"[{len(rows):>3}/{EXPECTED_ROWS}] duty={duty:>3}  "
              f"V={voltage}  I={current}")
    except ValueError:
        pass

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['duty_cycle', 'voltage_v', 'current_mA'])
    writer.writerows(rows)

if len(rows) < EXPECTED_ROWS:
    print(f"\nWARNING: only {len(rows)} of {EXPECTED_ROWS} points arrived. "
          f"Sweep was truncated - check that the Arduino IDE Serial Monitor "
          f"is closed.")

print(f"\nSaved {len(rows)} points to {OUTPUT_FILE}")
ser.close()
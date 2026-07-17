import matplotlib.pyplot as plt
from datacleaner import dedupe_readings

df = dedupe_readings('sensor_log.csv', 'sensor_log_clean.csv')

plt.figure(figsize=(10, 5))
plt.plot(df['timestamp'], df['thermistor_v'], label='Thermistor (V)')
plt.plot(df['timestamp'], df['photoresistor_v'], label='Photoresistor (V)')

plt.xlabel('Time (s)')
plt.ylabel('Voltage (V)')
plt.title('Sensor Readings Over Time')
plt.legend()
plt.grid(True)

plt.savefig('sensor_plot.png')
plt.show()
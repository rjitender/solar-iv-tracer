import matplotlib.pyplot as plt
from datacleaner import dedupe_readings

df = dedupe_readings('sensor_log.csv', 'sensor_log_clean.csv')

df['minutes'] = df['timestamp'] / 60

plt.figure(figsize=(12, 6))
plt.plot(df['minutes'], df['thermistor_v'], label='Thermistor (V)', linewidth=1.2)
plt.plot(df['minutes'], df['photoresistor_v'], label='Photoresistor (V)', linewidth=1.2)

plt.xlabel('Time (minutes)')
plt.ylabel('Voltage (V)')
plt.title('Thermistor and Photoresistor Voltage Over 1 Hour')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('sensor_plot_clean.png', dpi=150)
plt.show()
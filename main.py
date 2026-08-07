import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

df = pd.read_csv('iv_sweep.csv')
df = df[~((df['voltage_v'] == 2.29) & (df['current_mA'] == 5.6))]
df = df[~((df['voltage_v'] == 2.51) & (df['current_mA'] == 10.4))]

df = df.sort_values('voltage_v').reset_index(drop=True)

plt.figure(figsize=(8, 6))
plt.plot(df['voltage_v'], df['current_mA'], 'o-', markersize=4)

plt.xlabel('Voltage (V)')
plt.ylabel('Current (mA)')
plt.title('Solar Panel I-V Curve')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('iv_curve.png', dpi=150)
plt.show()

isc = df.loc[df['voltage_v'].idxmin(), 'current_mA']

voc = df.loc[df['current_mA'].idxmin(), 'voltage_v']

df['power_mW'] = df['voltage_v'] * df['current_mA']

mpp_row = df.loc[df['power_mW'].idxmax()]
mpp_voltage = mpp_row['voltage_v']
mpp_current = mpp_row['current_mA']
mpp_power = mpp_row['power_mW']

fill_factor = mpp_power / (voc * isc)

print(f"Isc: {isc} mA")
print(f"Voc: {voc} V")
print(f"MPP: {mpp_voltage} V, {mpp_current} mA, {mpp_power:.2f} mW")
print(f"Fill Factor: {fill_factor:.3f}")

V_T = 0.0259

def diode_model(V, I_L, logI_0, n):
    I_0 = 10**logI_0
    return I_L - I_0 * (np.exp(V / (n * V_T)) - 1)

V_data = df['voltage_v'].values
I_data = df['current_mA'].values / 1000

initial_guess = [0.0153, -7.6, 15.0]

params, covariance = curve_fit(
    diode_model, V_data, I_data,
    p0=initial_guess,
    bounds=([0.010, -12, 5.0], [0.020, -4, 30.0]),
    maxfev=20000
)
I_L_fit, logI_0_fit, n_fit = params
I_0_fit = 10**logI_0_fit

n_cell = n_fit / 10

print(f"I_L (light current):        {I_L_fit*1000:.2f} mA")
print(f"I_0 (saturation current):   {I_0_fit:.3e} A")
print(f"n_eff (module):             {n_fit:.2f}")
print(f"n per cell (if 10 cells):   {n_cell:.2f}")

V_fit = np.linspace(V_data.min(), V_data.max(), 300)
I_fit = diode_model(V_fit, I_L_fit, logI_0_fit, n_fit) * 1000 

plt.figure(figsize=(8, 6))
plt.plot(df['voltage_v'], df['current_mA'], 'o', markersize=5, label='Measured')
plt.plot(V_fit, I_fit, '-', linewidth=1.5, label='Single-diode fit')
plt.plot(mpp_voltage, mpp_current, 's', markersize=9, fillstyle='none', label='MPP')

plt.xlabel('Voltage (V)')
plt.ylabel('Current (mA)')
plt.title('Solar Panel I-V Curve with Single-Diode Fit')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('iv_curve_fit.png', dpi=150)
plt.show()
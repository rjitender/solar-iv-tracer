"""
Solar Cell I-V Curve Tracer Analysis
Loads a manual sweep, computes figures of merit, fits the single-diode
equation, and plots both the raw curve and the fitted overlay.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# ---- Constants ----
V_T = 0.0259        # thermal voltage at room temperature, volts
N_CELLS = 10         # counted from the panel: two 10-cell strings in parallel

# ---- Known bad points: identified as illumination artifacts, see README ----
EXCLUDE_POINTS = [
    (2.29, 5.6),
    (2.51, 10.4),
]


def load_sweep(filename):
    """Load a sweep CSV and drop known illumination-artifact points."""
    df = pd.read_csv(filename)
    for v, i in EXCLUDE_POINTS:
        df = df[~((df['voltage_v'] == v) & (df['current_mA'] == i))]
    return df.sort_values('voltage_v').reset_index(drop=True)


def compute_characteristics(df):
    """Extract Voc, Isc, MPP, and fill factor from a cleaned sweep."""
    isc = df.loc[df['voltage_v'].idxmin(), 'current_mA']
    voc = df.loc[df['current_mA'].idxmin(), 'voltage_v']

    df = df.copy()
    df['power_mW'] = df['voltage_v'] * df['current_mA']
    mpp = df.loc[df['power_mW'].idxmax()]

    fill_factor = mpp['power_mW'] / (voc * isc)

    return {
        'isc_mA': isc,
        'voc_V': voc,
        'mpp_V': mpp['voltage_v'],
        'mpp_mA': mpp['current_mA'],
        'mpp_mW': mpp['power_mW'],
        'fill_factor': fill_factor,
    }


def diode_model(V, I_L, logI_0, n):
    """Single-diode equation. n here is the module-level ideality factor
    (n_cell x N_CELLS), since Voc divides across N_CELLS in series."""
    I_0 = 10 ** logI_0
    return I_L - I_0 * (np.exp(V / (n * V_T)) - 1)


def fit_diode_model(df):
    """Fit I_L, I_0, and n to the measured sweep."""
    V_data = df['voltage_v'].values
    I_data = df['current_mA'].values / 1000  # mA -> A

    initial_guess = [0.0153, -7.6, 15.0]
    bounds = ([0.010, -12, 5.0], [0.020, -4, 30.0])

    params, _ = curve_fit(
        diode_model, V_data, I_data,
        p0=initial_guess, bounds=bounds, maxfev=20000
    )
    I_L_fit, logI_0_fit, n_fit = params

    return {
        'I_L_mA': I_L_fit * 1000,
        'I_0_A': 10 ** logI_0_fit,
        'n_module': n_fit,
        'n_cell': n_fit / N_CELLS,
    }


def plot_curve(df, filename='iv_curve.png'):
    """Raw measured I-V curve."""
    plt.figure(figsize=(8, 6))
    plt.plot(df['voltage_v'], df['current_mA'], 'o-', markersize=4)
    plt.xlabel('Voltage (V)')
    plt.ylabel('Current (mA)')
    plt.title('Solar Panel I-V Curve')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.show()


def plot_fit(df, values, fit, filename='iv_curve_fit.png'):
    """Measured curve with the fitted single-diode model overlaid."""
    V_fit = np.linspace(df['voltage_v'].min(), df['voltage_v'].max(), 300)
    I_fit = diode_model(
        V_fit, fit['I_L_mA'] / 1000,
        np.log10(fit['I_0_A']), fit['n_module']
    ) * 1000

    plt.figure(figsize=(8, 6))
    plt.plot(df['voltage_v'], df['current_mA'], 'o', markersize=5, label='Measured')
    plt.plot(V_fit, I_fit, '-', linewidth=1.5, label='Single-diode fit')
    plt.plot(values['mpp_V'], values['mpp_mA'], 's', markersize=9,
              fillstyle='none', label='MPP')
    plt.xlabel('Voltage (V)')
    plt.ylabel('Current (mA)')
    plt.title('Solar Panel I-V Curve with Single-Diode Fit')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.show()


# --- v2 sweep (PWM/MOSFET, automated) ---
# KNOWN ISSUE: this fit does not converge to a physically meaningful result.
# n_module pins at the fit's upper bound (30.0), and I_L undershoots the
# measured Isc by ~40% (10.0 mA fit vs 16.66 mA measured) -- contrast with
# v1, where these two agreed within 0.5%.
#
# Root cause: PWM gate drive is not a clean DC signal, so consecutive duty
# cycle steps can produce out-of-order voltage readings. Sorting by voltage
# before fitting then connects points that were not measured adjacently in
# time, turning point-to-point sensor/PWM noise into visible zigzag rather
# than smooth curvature -- see iv_curve_v2.png. The optimizer fits that
# noise rather than the underlying diode behavior.
#
# Fix in progress: 0.1-1uF ceramic capacitor across Gate-Source to filter
# the PWM signal into genuine DC before it reaches the MOSFET, addressing
# the noise at its source rather than averaging it out downstream.
def main():
    df_v2 = load_sweep('iv_sweep_v2.csv')
    values_v2 = compute_characteristics(df_v2)
    fit_v2 = fit_diode_model(df_v2)

    print(f"Isc:  {values_v2['isc_mA']:.2f} mA")
    print(f"Voc:  {values_v2['voc_V']:.2f} V")
    print(f"MPP:  {values_v2['mpp_V']:.2f} V, {values_v2['mpp_mA']:.2f} mA, {values_v2['mpp_mW']:.2f} mW")
    print(f"Fill Factor: {values_v2['fill_factor']:.3f}")
    print()
    print(f"I_L:        {fit_v2['I_L_mA']:.2f} mA")
    print(f"I_0:        {fit_v2['I_0_A']:.3e} A")
    print(f"n (module): {fit_v2['n_module']:.2f}")
    print(f"n (cell):   {fit_v2['n_cell']:.2f}")
    plot_curve(df_v2, filename='iv_curve_v2.png')
    plot_fit(df_v2, values_v2, fit_v2, filename='iv_curve_fit_v2.png')


if __name__ == '__main__':
    main()
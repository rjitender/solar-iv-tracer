"""
Solar Cell I-V Curve Tracer

Loads a sweep, checks whether it is physically valid before fitting, trims the
MOSFET dead zones, computes figures of merit, fits the single-diode equation,
and plots the curve, the fit, and the fit residuals.

The residual plot is the decision tool for whether to add Rs and Rsh: fit the
3-parameter model first, look at where the residuals slope, and only then add
parameters. Adding them speculatively fits noise.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Constants
V_T = 0.0259      # thermal voltage at room temperature, volts
N_CELLS = 10      # counted from the panel: two 10-cell strings in parallel


def load_sweep(filename, exclude=None):
    """Load a sweep CSV in acquisition order (by duty cycle, not voltage).
    Dead-zone trimming operates on duty-cycle order, since
    the dead zones are adjacent in duty and scattered in voltage. Sorting by
    voltage happens later, immediately before fitting and plotting.
    """
    df = pd.read_csv(filename)
    if exclude:
        for v, i in exclude:
            df = df[~((df['voltage_v'] == v) & (df['current_mA'] == i))]
    if 'duty_cycle' in df.columns:
        df = df.sort_values('duty_cycle')
    return df.reset_index(drop=True)


def sweep_is_valid(V, I, tol_V=1e-3):
    """Is this data physically a solar cell sweep at all?
    A real sweep should be monotonic: as the load pulls more current, terminal
    voltage must fall. So sort by current, take consecutive voltage differences,
    and require every one to be non-positive within ADC noise.
    If this fails, the data is not physically valid and the problem is in the hardware.
    """
    order = np.argsort(np.asarray(I))
    dV = np.diff(np.asarray(V)[order])
    return bool(np.all(dV <= tol_V))


def monotonicity_report(df, tol_V=1e-3):
    """How badly does the sweep violate monotonicity, and where?
    Pass/fail isn't much use while debugging hardware. This returns the
    count of violating steps and the worst one, so you can tell a single bad point
    apart from a whole bad sweep.
    """
    ordered = df.sort_values('current_mA')
    dV = np.diff(ordered['voltage_v'].values)
    violations = dV > tol_V
    return {
        'n_violations': int(violations.sum()),
        'n_steps': int(len(dV)),
        'worst_rise_V': float(dV.max()) if len(dV) else 0.0,
    }


def trim_dead_zones(df, i_floor_mA=0.5, v_floor_V=0.05):
    """Drop the duty ranges where the MOSFET load isn't actually doing anything.
    Below the gate threshold the load never turns on, so every row reports the
    same (Voc, ~0 mA) point. Above saturation every row reports (~0 V, Isc).
    Those rows are duplicates: they carry no information about the knee, but
    they contribute residual terms that the optimiser has to minimise,
    which is a possible way fitting ends up pinned at a parameter bound.
    One row is kept on each side of the responsive band as a genuine Voc and
    Isc anchor, since those two points do constrain the fit.
    """
    responsive = (df['current_mA'] > i_floor_mA) & (df['voltage_v'] > v_floor_V)
    if not responsive.any():
        print("  trim_dead_zones: no responsive rows found - returning data "
              "untouched. The load never left dead zone.")
        return df.copy()

    idx = np.flatnonzero(responsive.values)
    lo = max(0, idx.min() - 1)
    hi = min(len(df) - 1, idx.max() + 1)

    trimmed = df.iloc[lo:hi + 1].reset_index(drop=True)
    print(f"  trim_dead_zones: kept rows {lo}-{hi} "
          f"({len(trimmed)} of {len(df)}); "
          f"duty {trimmed['duty_cycle'].min()}-{trimmed['duty_cycle'].max()}"
          if 'duty_cycle' in df.columns else
          f"  trim_dead_zones: kept {len(trimmed)} of {len(df)} rows")
    return trimmed


def compute_characteristics(df):
    """Extract Voc, Isc, MPP, and fill factor from a sweep."""
    isc = df.loc[df['voltage_v'].idxmin(), 'current_mA']
    voc = df.loc[df['current_mA'].idxmin(), 'voltage_v']

    df = df.copy()
    df['power_mW'] = df['voltage_v'] * df['current_mA']
    mpp = df.loc[df['power_mW'].idxmax()]

    return {
        'isc_mA': isc,
        'voc_V': voc,
        'mpp_V': mpp['voltage_v'],
        'mpp_mA': mpp['current_mA'],
        'mpp_mW': mpp['power_mW'],
        'fill_factor': mpp['power_mW'] / (voc * isc),
    }


def diode_model(V, I_L, logI_0, n):
    """Single-diode equation. n is the module-level ideality factor
    (n_cell * N_CELLS), since the terminal voltage divides across N_CELLS in
    series. Fitting log10(I_0) rather than I_0 keeps the two fitted parameters
    on comparable scales. Without it, the optimiser is trying to fit something
    near 1e-2 alongside something near 1e-8."""
    I_0 = 10 ** logI_0
    return I_L - I_0 * (np.exp(V / (n * V_T)) - 1)


def fit_diode_model(df):
    """Fit I_L, I_0, and n to the measured sweep.
    Returns the fit plus a `pinned` flag. A parameter sitting exactly on a bound
    means the optimiser wanted to keep going and hit a wall. The numbers are
    not a converged result and should not be reported as one.
    """
    V_data = df['voltage_v'].values
    I_data = df['current_mA'].values / 1000.0   # mA -> A

    initial_guess = [0.0153, -7.6, 15.0]
    lower = [0.010, -12, 5.0]
    upper = [0.020, -4, 30.0]

    params, _ = curve_fit(
        diode_model, V_data, I_data,
        p0=initial_guess, bounds=(lower, upper), maxfev=20000
    )
    I_L_fit, logI_0_fit, n_fit = params

    pinned = [
        name for name, val, lo, hi in
        zip(['I_L', 'log10(I_0)', 'n'], params, lower, upper)
        if np.isclose(val, lo, rtol=1e-4) or np.isclose(val, hi, rtol=1e-4)
    ]

    return {
        'I_L_mA': I_L_fit * 1000,
        'I_0_A': 10 ** logI_0_fit,
        'n_module': n_fit,
        'n_cell': n_fit / N_CELLS,
        'pinned': pinned,
    }


def plot_curve(df, filename='iv_curve.png'):
    """Raw measured I-V curve, points connected in voltage order."""
    d = df.sort_values('voltage_v')
    plt.figure(figsize=(8, 6))
    plt.plot(d['voltage_v'], d['current_mA'], 'o-', markersize=4)
    plt.xlabel('Voltage (V)')
    plt.ylabel('Current (mA)')
    plt.title('Solar Panel I-V Curve')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.show()


def plot_fit(df, values, fit, filename='iv_curve_fit.png'):
    """Measured curve with the fitted single-diode model overlaid."""
    d = df.sort_values('voltage_v')
    V_fit = np.linspace(d['voltage_v'].min(), d['voltage_v'].max(), 300)
    I_fit = diode_model(
        V_fit, fit['I_L_mA'] / 1000,
        np.log10(fit['I_0_A']), fit['n_module']
    ) * 1000

    plt.figure(figsize=(8, 6))
    plt.plot(d['voltage_v'], d['current_mA'], 'o', markersize=5, label='Measured')
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


def plot_residuals(df, fit, filename='iv_residuals.png'):
    """Measured minus fitted current, against voltage.
    This is the tool for deciding whether Rs and Rsh are needed, and it only
    means anything once the data itself is clean:
      - residuals sloping near Voc  -> add Rs  (4-parameter)
      - residuals sloping near Isc  -> add Rsh (5-parameter)
      - flat, scattered about zero  -> the 3-parameter model is sufficient

    Scatter with no structure is noise. Any structure in it is due to a mismatched model. 
    Adding parameters to absorb noise makes the fit look better and the extracted
    values meaningless.
    """
    d = df.sort_values('voltage_v')
    I_pred = diode_model(
        d['voltage_v'].values, fit['I_L_mA'] / 1000,
        np.log10(fit['I_0_A']), fit['n_module']
    ) * 1000
    resid = d['current_mA'].values - I_pred

    plt.figure(figsize=(8, 4))
    plt.axhline(0, linewidth=1, alpha=0.5)
    plt.plot(d['voltage_v'], resid, 'o', markersize=5)
    plt.xlabel('Voltage (V)')
    plt.ylabel('Measured - fitted (mA)')
    plt.title('Single-Diode Fit Residuals')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.show()


def main():
    SWEEP_FILE = 'iv_sweep_v2_step1.csv'

    V2_EXCLUDE_POINTS = [
    
    ]

    df = load_sweep(SWEEP_FILE, exclude=V2_EXCLUDE_POINTS)
    print(f"Loaded {len(df)} points from {SWEEP_FILE}")

    df = trim_dead_zones(df)

    report = monotonicity_report(df)
    valid = sweep_is_valid(df['voltage_v'], df['current_mA'])
    print(f"  monotonicity: {report['n_violations']} violating steps of "
          f"{report['n_steps']}, worst rise {report['worst_rise_V']*1000:.1f} mV")

    if not valid:
        print("\n  Sweep is not monotonic. This data does not describe a solar")
        print("  cell, and no choice of fit parameters will make it do so.")
        print("  Figures of merit below are not meaningful and the fit is not valid.")
        print("  Go back and fix the load circuit.\n")

    values = compute_characteristics(df)
    print(f"\nIsc:  {values['isc_mA']:.2f} mA")
    print(f"Voc:  {values['voc_V']:.2f} V")
    print(f"MPP:  {values['mpp_V']:.2f} V, {values['mpp_mA']:.2f} mA, "
          f"{values['mpp_mW']:.2f} mW")
    print(f"Fill Factor: {values['fill_factor']:.3f}")

    fit = fit_diode_model(df)
    print()
    print(f"I_L:        {fit['I_L_mA']:.2f} mA   "
          f"(measured Isc {values['isc_mA']:.2f} mA)")
    print(f"I_0:        {fit['I_0_A']:.3e} A")
    print(f"n (module): {fit['n_module']:.2f}")
    print(f"n (cell):   {fit['n_cell']:.2f}")

    if fit['pinned']:
        print(f"\n  FIT DID NOT CONVERGE: {', '.join(fit['pinned'])} sitting on "
              f"a bound.")
        print("  Do not report these values. Fix the data first.")

    plot_curve(df, filename='iv_curve_v2.png')
    plot_fit(df, values, fit, filename='iv_curve_fit_v2.png')
    plot_residuals(df, fit, filename='iv_residuals_v2.png')


if __name__ == '__main__':
    main()
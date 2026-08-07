# Solar Cell I-V Curve Tracer

An instrument for electrically characterizing a photovoltaic device: sweeping a solar panel across its full load range, measuring voltage and current simultaneously at each point, and extracting the physical parameters of the underlying pn junction from the resulting curve.

Built with an Arduino Uno, an INA219 current/voltage sensor, and a Python analysis pipeline.

## Results

Measured on a 6 V, 1 W polycrystalline silicon module (10 cells in series, 2 strings in parallel) under window illumination.

| Parameter | Value |
|---|---|
| Open-circuit voltage (Voc) | 5.27 V |
| Short-circuit current (Isc) | 15.1 mA |
| Maximum power point | 60.34 mW at 4.31 V, 14.0 mA |
| Fill factor | 0.758 |

Fitting the ideal single-diode equation to the measured curve gives:

| Parameter | Value |
|---|---|
| Light-generated current (I_L) | 15.03 mA |
| Saturation current (I_0) | 2.22 × 10⁻⁸ A |
| Ideality factor, module (n_eff) | 15.20 |
| Ideality factor, per cell | 1.52 |

The fitted I_L agrees with the independently measured Isc to within 0.5%, and the fitted ideality factor agrees within 1% of a two-point hand calculation taken from the knee region — two independent checks that the model describes the device rather than merely interpolating the data.

A per-cell ideality factor of 1.52 sits between the diffusion-limited ideal (n → 1) and depletion-region recombination (n → 2), consistent with polycrystalline silicon where grain boundaries contribute mid-gap defect states without dominating.

## How it works

A solar cell is a large-area pn junction. Its output is not a fixed voltage or current but a curve: connect no load and you get maximum voltage at zero current (Voc); short it and you get maximum current at zero voltage (Isc). Sweeping the load resistance between those extremes traces the I-V curve, whose shape is the device's fingerprint.

The measurement chain:

- **Load** — a 10 kΩ potentiometer in series with the panel, varied by hand across its full range
- **Sensing** — an INA219 breakout inline with the current path (VIN+/VIN−), measuring current differentially across an internal shunt and bus voltage against a shared ground reference, reporting both over I²C
- **Acquisition** — the Arduino polls the sensor and streams comma-separated readings over serial
- **Logging** — a Python script triggered by keypress captures one reading per load setting, so each point corresponds to a deliberate dial position

The extracted parameters come from the single-diode equation:

```
I = I_L − I_0 · (exp(V / (n · V_T)) − 1)
```

The light-generated current is roughly constant, set by illumination. The diode term grows exponentially with voltage — a consequence of Boltzmann statistics governing how many carriers can clear the junction's barrier as forward bias lowers it. The measured current is the difference. Voc is the voltage at which the diode term has grown to exactly cancel I_L.

## Files

```
├── arduino/
│   └── solar_tracer/
│       └── solar_tracer.ino     INA219 polling, CSV output over serial
├── sweep_logger.py              Keypress-triggered acquisition
├── main.py                      Analysis: cleaning, figures of merit, diode fit, plots
├── datacleaner.py               Duplicate-timestamp removal
├── iv_sweep.csv                 Raw sweep data
├── iv_curve.png                 Measured I-V curve
├── iv_curve_fit.png             Measured data with fitted model overlay
└── sensor_logging/              Earlier thermistor/photoresistor pipeline
```

## Running it

```bash
python -m pip install pyserial pandas matplotlib scipy
```

Upload `solar_tracer.ino`, close the Arduino IDE's Serial Monitor (only one program can hold the serial port), then:

```bash
python sweep_logger.py    # sweep the potentiometer, log points
python main.py            # analyze and plot
```

## Known limitations

**No series or shunt resistance in the model.** Real cells have both: series resistance from contacts and interconnects, shunt resistance from parasitic leakage paths around the junction. The full model is implicit in I and requires a numerical root-find or the Lambert W function to fit.

Series resistance shows no visible effect in this data — at 15 mA, the I·R_s drop is only tens of millivolts, too small to distinguish. Shunt resistance is under-constrained: extracting it needs slope information near Isc, and only three points were captured below 0.25 V. The fitted n should therefore be read as an effective value that may absorb some resistive loss.

**Illumination drift during the sweep.** A hand-turned sweep takes several minutes, during which passing clouds change the light level. Two points showing non-monotonic behavior were excluded as clear artifacts; one further point at 3.17 V sits ~3% below the fitted curve and is likely a milder instance of the same effect. It was retained, since the fit handles it without distortion.

## Next version

Replacing the potentiometer with an IRLZ44N logic-level MOSFET under PWM control addresses both limitations at once. Programmatic load control allows non-uniform sampling — dense near Isc where series resistance is determined, dense near Voc for shunt resistance, sparse through the uninformative flat region — enabling a five-parameter fit. It also runs the full sweep in seconds rather than minutes, so every point shares the same illumination.

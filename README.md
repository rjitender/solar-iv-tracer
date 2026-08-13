# Solar Cell I-V Curve Tracer

An instrument for electrically characterizing a photovoltaic device: sweeping a solar panel across its full load range, measuring voltage and current simultaneously at each point, and extracting the physical parameters of the underlying pn junction from the resulting curve.

Built with an Arduino Uno, an INA219 current/voltage sensor, and Python analysis. Two versions: v1 sweeps the load by hand with a potentiometer; v2 automates it with a MOSFET under PWM control.

## Results

Measured on a 6 V, 1 W polycrystalline silicon module (10 cells in series, 2 strings in parallel), same physical panel across both versions.

| Parameter | v1 (manual, potentiometer) | v2 (automated, MOSFET) |
|---|---|---|
| Open-circuit voltage (Voc) | 5.27 V | 5.30 V |
| Short-circuit current (Isc) | 15.1 mA | 15.50 mA |
| Maximum power point | 60.34 mW at 4.31 V, 14.0 mA | 59.22 mW at 4.08 V, 14.50 mA |
| Fill factor | 0.758 | 0.721 |

Fitting the ideal single-diode equation to each:

| Parameter | v1 | v2 |
|---|---|---|
| Light-generated current (I_L) | 15.03 mA | 15.46 mA |
| Saturation current (I_0) | 2.22 × 10⁻⁸ A | 3.12 × 10⁻⁸ A |
| Ideality factor, per cell | 1.52 | 1.56 |

Both fits cross-check against their own independent measurement: fitted I_L agrees with measured Isc to within 0.5% (v1) and 0.3% (v2). Per-cell ideality factor has now landed at 1.52, 1.59, and 1.56 across three separate converged sweeps with two different load mechanisms, different days, different light. 

A per-cell ideality factor in this range sits between the diffusion-limited ideal (n → 1) and depletion-region recombination (n → 2), consistent with polycrystalline silicon where grain boundaries contribute mid-gap defect states without dominating.

v2's fill factor is consistently a bit lower than v1's across every converged run. This may be due to the MOSFET's on-resistance and the added breadboard wiring in the load path introduce resistive loss v1's potentiometer sweep didn't have. Quantifying that loss is the motivation for the five-parameter (Rs/Rsh) extension below.

## How it works

A solar cell is a large-area pn junction. Its output is not a fixed voltage or current but a curve: connect no load and you get maximum voltage at zero current (Voc); short it and you get maximum current at zero voltage (Isc). Sweeping the load resistance between those extremes traces the I-V curve, whose shape is the device's fingerprint.

The measurement chain, common to both versions:

- **Sensing** — an INA219 breakout inline with the current path (VIN+/VIN−), measuring current differentially across an internal shunt and bus voltage against a shared ground reference, reporting both over I²C
- **Acquisition** — the Arduino polls the sensor and streams comma-separated readings over serial
- **Logging** — a Python script reads the serial stream and writes it to CSV

The two versions differ only in how the load is varied:

- **v1** — a 10 kΩ potentiometer in series with the panel, varied by hand; Python logs one reading per keypress, so each point corresponds to a deliberate dial position
- **v2** — an IRLZ44N logic-level MOSFET in series with the panel, acting as a voltage-controlled variable resistor; the Arduino steps through PWM duty cycle automatically and logs every point without hands on a dial

The extracted parameters come from the single-diode equation:

```
I = I_L − I_0 · (exp(V / (n · V_T)) − 1)
```

The light-generated current is roughly constant, set by illumination. The diode term grows exponentially with voltage due to Boltzmann statistics governing how many carriers can clear the junction's barrier as forward bias lowers it. The measured current is the difference. Voc is the voltage at which the diode term has grown to exactly cancel I_L.

## v2: building the automated load

Replacing the potentiometer with a MOSFET sounds like a drop-in swap, the same current loop with one component replaced. It wasn't. Getting from "PWM drives a MOSFET" to a sweep that actually produces a fittable curve took two independent hardware bugs that took a lot of testing to work through.

**PWM ripple was too fast for the gate filter, but not in the direction that sounds intuitive.** The Arduino's default PWM frequency on the gate pin is 490 Hz. A gate capacitor smooths PWM into a stable DC level only when the switching period is much shorter than the RC time constant it's charging against. Otherwise the capacitor has time to meaningfully charge and discharge every single cycle, and the "load" is actually flickering between two extreme operating points rather than sitting at one. At 490 Hz, with the gate resistance in this circuit, the ripple period and the RC time constant were close to equal, the worst case. No amount of averaging fixes this, because averaging two points on an exponential curve doesn't produce a point on that curve. This is why increasing capacitor value alone (tried at 1, 2.25, 4.75, and 10 µF) never fully resolved it, and why switching from mean to median sample averaging didn't help either.

The fix was reprogramming the Timer1 prescaler directly (`TCCR1B`) to raise the gate PWM frequency to ~31 kHz. It was now fast enough that each cycle is a small fraction of the RC time constant, so the capacitor barely reacts to individual switches and settles on their average instead.

**A second, unrelated fault reproduced at the same operating point across multiple sessions.** Independent of the frequency fix, a sharp current spike kept appearing at the same PWM duty cycle: right at the edge of the load's transition into saturation. Parking the sketch at that fixed duty cycle and probing directly with a multimeter isolated it: gate voltage was steady, but drain-source voltage wouldn't settle, consistent with parasitic oscillation from gate-drain capacitance interacting with breadboard lead inductance. A small ceramic capacitor added directly across drain-source, plus moving the gate resistor closer to the gate pin, resolved it. This was confirmed by the spike's disappearance across two subsequent sweeps.

Also changed for v2: the INA219 configured for 128-sample hardware averaging with calibration matched to this panel's actual current range (16 V / 400 mA, versus the library default of 32 V / 2 A, which was using under a tenth of the sensor's resolution on a 15 mA signal). Hardware averaging integrates continuously across each conversion window; the software-side sample averaging it replaced was taking discrete point-samples at arbitrary PWM phase, which is a worse way to average a switching signal.

## Files

```
├── Arduino/
│   ├── solar_tracer_v1.ino      v1: INA219 polling, CSV output over serial
│   ├── solar_tracer_v2.ino      v2: 31kHz gate PWM, hardware-averaged INA219, automated sweep
│   └── sensor_logger.ino        earlier thermistor/photoresistor test sketch
├── sweep_logger.py              v2 acquisition — automated, matches solar_tracer_v2.ino's duty-cycle sweep
├── main.py                      Analysis: cleaning, validity checks, figures of merit, diode fit, plots, residuals
├── iv_sweep.csv                 v1 raw sweep data
├── iv_sweep_v2_step1.csv        v2 raw sweep data (full duty-cycle characterization)
├── iv_curve.png / iv_curve_fit.png            v1 plots
├── iv_curve_v2.png / iv_curve_fit_v2.png       v2 plots
├── iv_residuals_v2.png          v2 fit residuals — the diagnostic for whether Rs/Rsh are needed
└── sensor_stuff/                 Earlier thermistor/photoresistor test project
    ├── sensor_tools.py
    ├── data_cleaner.py
    ├── serial_logger.py
    ├── sensor_analysis.py
    ├── sensor_log.csv / sensor_log_clean.csv
    ├── sensor_plot_clean.png
    └── readings.txt
```

## Running it

```bash
python -m pip install pyserial pandas matplotlib scipy
```

Close the Arduino IDE's Serial Monitor before running any Python script. Only one program can hold the serial port at a time.

Note: `sweep_logger.py` evolved from a v1 keypress-driven logger into v2's automated version over the course of this project, and the earlier keypress version wasn't kept separately. `iv_sweep.csv` is preserved as v1's dataset, but re-running a v1-style manual sweep from this repo as-is isn't currently possible. `solar_tracer_v1.ino` still exists and would need a matching keypress logger written to pair with it. The legacy sweep_logger is accessible in prior commits. 

**v2 sweep:**
```bash
python sweep_logger.py    
```

**Analysis:**
```bash
python main.py
```

`main.py` currently points at `iv_sweep_v2_step1.csv` (set at the top of `main()`) — edit `SWEEP_FILE` there to point at `iv_sweep.csv` to re-run the same analysis against v1's data instead.

`main.py` checks the loaded sweep for monotonicity before fitting anything. The current should only ever increase as voltage decreases. A non-monotonic sweep gets flagged explicitly rather than fit anyway; no choice of fit parameters makes bad data describe a solar cell. It also reports if any fitted parameter lands exactly on its search bound, which means the optimizer didn't converge, not that it found an answer.

## Known limitations

**No series or shunt resistance in the model.** Real cells have both: series resistance from contacts, interconnects, and the MOSFET's own on-resistance; shunt resistance from leakage paths around the junction. The full model is implicit in I and requires a numerical root-find or the Lambert W function to fit, rather than the direct fit used here.

v1's data showed no visible Rs effect (the I·Rs drop at 15 mA is only tens of millivolts) and couldn't constrain Rsh (only three points were captured below 0.25 V in a hand-turned sweep). v2's automated, faster sweep is what actually makes a five-parameter fit viable as it can sample densely at both endpoints on demand, which v1's manual dial control couldn't do repeatably. Not yet done; the current v2 sweep prioritized validating the three-parameter model on clean data first.

**Illumination drift during acquisition.** Both versions are vulnerable to this, at different timescales. v1's hand-turned sweep takes minutes, during which passing clouds change the light level and two points were excluded as clear non-monotonic artifacts, a third retained as a milder instance the fit handled without distortion. v2's automated sweep is much faster per point, but a full 256-step characterization run still takes about two minutes; one early v2 sweep failed to converge because the sun visibly weakened over that window, leaving the Isc plateau still declining rather than flat. The fix is either a shorter, coarser sweep once the responsive duty-cycle range is already known, or acquiring in more stable light and both were sufficient once tried.

## Next steps

- **Five-parameter fit (Rs, Rsh)** — now viable with v2's clean, fast, repeatable sweeps. Requires dense sampling specifically near both Isc and Voc, and an implicit-equation solver in place of direct `curve_fit`.
- **Multi-condition characterization** — sweep across light intensity, angle, and temperature, and track how Voc, Isc, and n shift with each.
- **Adaptive sampling** — a Gaussian process model over the multi-condition data, with an acquisition function choosing the next most informative load point rather than a fixed grid; validated live against the physical tracer.

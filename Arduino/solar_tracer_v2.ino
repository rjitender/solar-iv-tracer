/*
 * Solar Cell I-V Curve Tracer - v2.1
 * MOSFET electronic load with PWM gate drive.
 */

#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219;

const int GATE_PIN = 9;   // Timer1. Do NOT move this to pin 5 or 6 (Timer0).

// Sweep range 
// DUTY_STEP = 1  -> 256 points, ~2 min. Use this to map the threshold window.
// DUTY_STEP = 5  -> 52 points, ~26 s. Use once the window is known.
#define DUTY_START   0
#define DUTY_END     255
#define DUTY_STEP    1

// Timing
// GATE_SETTLE: must exceed 5 time constants of the gate RC network.
//   Current network (220R || 10k = 215R, 10uF): time constant = 2.15 ms, 5 time constants = 11 ms.
//   After 1b (2763R, 10uF): time constant = 27.6 ms, 5 time constants = 138 ms.
//   200 ms covers both, so this value does not need changing when rewiring.
//
// ADC_SETTLE: the INA219 converts bus and shunt sequentially, 68.1 ms each at
//   128-sample averaging, so one complete V+I pair takes 136 ms. This allows
//   sequential sampling to work.
const unsigned int GATE_SETTLE_MS = 200;
const unsigned int ADC_SETTLE_MS  = 300;

void configureINA219() {
  // setCalibration_*() writes both the calibration register and
  // the config register, so it has to run before the manual config write below
  // or it won't work.
  //
  // Default calibration is 32V/2A: at 15 mA that is 0.75% of full scale.
  // 16V/400mA puts the same current at ~4% of full scale.
  ina219.setCalibration_16V_400mA();

  // Now overwrite only the config register (0x00) with 0x27FF.
  // Decoding the value bit by bit:
  //   bit 13      BRNG = 1    -> 32 V bus range (bus LSB is 4 mV either way)
  //   bits 12-11  PGA  = 00   -> /1, +/-40 mV shunt full scale
  //   bits 10-7   BADC = 1111 -> 12-bit, 128 samples averaged (68.10 ms)
  //   bits 6-3    SADC = 1111 -> 12-bit, 128 samples averaged (68.10 ms)
  //   bits 2-0    MODE = 111  -> shunt + bus, continuous
  // Hardware averaging integrates continuously across the whole 68 ms window 
  // instead of taking 20 instantaneous point-samples at arbitrary PWM phase.
  Wire.beginTransmission(0x40);
  Wire.write(0x00);   // register pointer: config
  Wire.write(0x27);   // high byte
  Wire.write(0xFF);   // low byte
  Wire.endTransmission();
}

void readAndPrint(int duty) {
  analogWrite(GATE_PIN, duty);

  delay(GATE_SETTLE_MS);   // gate voltage reaches its new level
  delay(ADC_SETTLE_MS);    // both INA219 conversions restart and complete

  // Single read each since software averaging was replaced with hardware averaging.
  float v = ina219.getBusVoltage_V();
  float i = ina219.getCurrent_mA();

  Serial.print(duty);
  Serial.print(",");
  Serial.print(v, 4);
  Serial.print(",");
  Serial.println(i, 3);
}

void setup() {
  Serial.begin(9600);

  pinMode(GATE_PIN, OUTPUT);
  analogWrite(GATE_PIN, 0);

  // 1a: Timer1 prescaler 64 -> 1.
  // Pins 9 and 10 run off Timer1 in 8-bit phase-correct PWM. The low 3 bits of
  // TCCR1B select the prescaler; Arduino's default is 0b011 (/64), giving
  // 16e6 / (2 * 64 * 255) = 490 Hz. 0b001 (/1) gives 16e6 / (2 * 1 * 255) =
  // 31372 Hz. The & 0b11111000 mask clears only those 3 bits and preserves the
  // waveform-mode and input-capture bits elsewhere in the register.

  // Period drops 2040 us -> 31.9 us. Against the existing gate
  // RC (time constant = 2.15 ms) that moves T/tau from 0.95 to 0.015, so gate ripple
  // falls from roughly 1.2 V p-p to about 18 mV. Below 490 Hz the MOSFET was
  // switching between hard-off and hard-on, not sitting in its linear region.
  TCCR1B = (TCCR1B & 0b11111000) | 0b001;

  if (!ina219.begin()) {
    Serial.println("INA219 not found. Check wiring!");
    while (1) { delay(10); }
  }

  configureINA219();
}

void loop() {
  for (int duty = DUTY_START; duty <= DUTY_END; duty += DUTY_STEP) {
    readAndPrint(duty);
  }

  analogWrite(GATE_PIN, 0);
  while (true) { delay(1000); }   
}

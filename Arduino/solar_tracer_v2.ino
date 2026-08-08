#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219;
const int GATE_PIN = 9;

void setup() {
  Serial.begin(9600);
  pinMode(GATE_PIN, OUTPUT);
  analogWrite(GATE_PIN, 0);  // start fully off

  if (!ina219.begin()) {
    Serial.println("INA219 not found. Check wiring!");
    while (1) { delay(10); }
  }
}

void loop() {
  for (int duty = 0; duty <= 255; duty += 5) {
    analogWrite(GATE_PIN, duty);
    delay(400);  

    float vSum = 0, iSum = 0;
    const int numSamples = 10;  

    for (int j = 0; j < numSamples; j++) {
      vSum += ina219.getBusVoltage_V();
      iSum += ina219.getCurrent_mA();
      delay(15);
    }

    float voltage = vSum / numSamples;
    float current = iSum / numSamples;

    Serial.print(duty);
    Serial.print(",");
    Serial.print(voltage);
    Serial.print(",");
    Serial.println(current);
  }

  analogWrite(GATE_PIN, 0); 
  while (true) { delay(1000); }  
}
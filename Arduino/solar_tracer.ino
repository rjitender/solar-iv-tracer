#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219;

void setup() {
  Serial.begin(9600);
  if (!ina219.begin()) {
    Serial.println("INA219 not found. Check wiring!");
    while (1) { delay(10); }
  }
}

void loop() {
  Serial.print(ina219.getBusVoltage_V());
  Serial.print(",");
  Serial.println(ina219.getCurrent_mA());
  delay(200);
}
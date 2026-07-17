void setup() {
  Serial.begin(9600);
}

void loop() {
  int rawTherm = analogRead(A0);
  float voltageTherm = rawTherm * (4.5 / 1023.0);

  int rawPhoto = analogRead(A1);
  float voltagePhoto = rawPhoto * (4.5 / 1023.0);

  Serial.print(voltageTherm);
  Serial.print(",");
  Serial.println(voltagePhoto);

  delay(500);
}

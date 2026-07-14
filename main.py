from sensortools import summarize

data = [21.4, 22.1, 20.9, 23.0, 22.6]
lo, hi, avg = summarize(data)
print(f"min={lo}  max={hi}  avg={avg:.2f}")
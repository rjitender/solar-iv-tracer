import statistics


def summarize(readings):
    return min(readings), max(readings), statistics.mean(readings)

def load_readings(filename):
    readings = []
    with open(filename, "r") as f:
        for line in f:
            value = float(line.strip())
            readings.append(value)
    return readings
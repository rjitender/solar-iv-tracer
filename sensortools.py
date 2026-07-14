import statistics

def summarize(readings):
    return min(readings), max(readings), statistics.mean(readings)
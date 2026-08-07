import pandas as pd

def dedupe_readings(filename, output_filename=None):
    df = pd.read_csv(filename)
    before = len(df)
    df = df.drop_duplicates(subset='timestamp', keep='first')
    after = len(df)
    print(f"Removed {before - after} duplicate timestamp rows ({before} → {after})")

    if output_filename:
        df.to_csv(output_filename, index=False)

    return df
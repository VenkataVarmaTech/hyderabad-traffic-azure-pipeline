import numpy as np
import pandas as pd

np.random.seed(42)

junctions = {
    "Hitech City":      (17.4435, 78.3772),
    "Gachibowli":       (17.4401, 78.3489),
    "Madhapur":         (17.4483, 78.3915),
    "Kukatpally":       (17.4849, 78.4138),
    "Ameerpet":         (17.4375, 78.4482),
    "Banjara Hills":    (17.4126, 78.4482),
    "Jubilee Hills":    (17.4326, 78.4071),
    "Begumpet":         (17.4440, 78.4676),
    "Secunderabad":     (17.4399, 78.4983),
    "Uppal":            (17.4058, 78.5591),
    "LB Nagar":         (17.3457, 78.5522),
    "Charminar":        (17.3616, 78.4747),
}

# base traffic load per junction (IT corridor junctions are busier)
base_load = {
    "Hitech City": 1.3, "Gachibowli": 1.3, "Madhapur": 1.25, "Kukatpally": 1.1,
    "Ameerpet": 1.2, "Banjara Hills": 1.0, "Jubilee Hills": 1.0, "Begumpet": 1.05,
    "Secunderabad": 1.1, "Uppal": 0.95, "LB Nagar": 0.95, "Charminar": 1.0,
}

timestamps = pd.date_range("2026-10-01", "2026-10-30 23:45", freq="15min")

def peak_factor(hour, is_weekend):
    if is_weekend:
        return 0.6 + 0.3 * np.exp(-((hour - 18) ** 2) / 8)
    morning = np.exp(-((hour - 9.5) ** 2) / 3)
    evening = np.exp(-((hour - 18.5) ** 2) / 4)
    return 0.3 + 0.9 * max(morning, evening)

rows = []
for ts in timestamps:
    hour = ts.hour + ts.minute / 60
    is_weekend = ts.dayofweek >= 5
    # rain is decided per day-ish, so it stays consistent through a day
    rainy = np.random.rand() < 0.08 if ts.hour == 0 and ts.minute == 0 else None
    for name, (lat, lon) in junctions.items():
        rows.append((ts, name, lat, lon, is_weekend))

df = pd.DataFrame(rows, columns=["timestamp", "junction", "latitude", "longitude", "is_weekend"])

# daily rain flag
days = df["timestamp"].dt.date.unique()
rain_days = {d: np.random.rand() < 0.25 for d in days}
df["weather"] = df["timestamp"].dt.date.map(lambda d: "Rain" if rain_days[d] else "Clear")

df["hour_f"] = df["timestamp"].dt.hour + df["timestamp"].dt.minute / 60
df["load"] = [
    peak_factor(h, w) * base_load[j] * (1.25 if wx == "Rain" else 1.0)
    for h, w, j, wx in zip(df["hour_f"], df["is_weekend"], df["junction"], df["weather"])
]

df["vehicle_count"] = (df["load"] * 400 + np.random.normal(0, 25, len(df))).clip(20).astype(int)
df["avg_speed_kmph"] = (55 - df["load"] * 38 + np.random.normal(0, 3, len(df))).clip(5, 60).round(1)

def level(speed):
    if speed < 15: return "High"
    if speed < 30: return "Medium"
    return "Low"

df["congestion_level"] = df["avg_speed_kmph"].apply(level)

df = df.drop(columns=["hour_f", "load"])
df["is_weekend"] = df["is_weekend"].astype(int)

# introduce a few missing values so cleaning in Databricks is meaningful
idx = df.sample(frac=0.01, random_state=1).index
df.loc[idx, "avg_speed_kmph"] = np.nan

df.to_csv("hyderabad_traffic_raw.csv", index=False)
print(df.shape)
print(df.head())
print(df["congestion_level"].value_counts())

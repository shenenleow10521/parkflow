"""Simple simulation of a busy Saturday evening at a 1,300-bay mall car park.

Compares three cases, 4 pm to 10 pm in 5-minute steps:
  none   - no alerts
  all    - warn every reachable driver at once when the forecast says "full"
  batch  - ParkAhead: shift only as many arrivals as needed, in small batches

Every number below is an assumption, stated here so anyone can change it.
Usage: python simulate_saturday.py   (writes simulate_saturday.csv, prints a summary)
"""
import numpy as np
import pandas as pd

CAP = 1300            # car bays
START_OCC = 0.70      # occupancy at 4 pm
STEP = 5              # minutes per step
MEAN_STAY = 150       # average stay in minutes (cinema + dinner)
REACH = 0.25          # share of arriving drivers who see an alert (opted in, or checked the app)
RESPONSE = 0.25       # share of those who come later when asked
SHIFT_MIN = 90        # how much later they come
GIVE_UP = 0.06        # share of the entrance queue that gives up each 5 minutes
CANCEL_IF_WARNED = 0.4  # in "warn everyone", share of shifted drivers who don't come at all
TARGET = 0.95         # batch mode aims to keep occupancy at or below this

t = np.arange(16 * 60, 22 * 60 + STEP, STEP)  # minutes since midnight
n = len(t)
# Arrivals per 5 min: a steady base plus an evening peak centred on 7 pm (shows and dinner).
# PEAK_EXTRA = 30 is a busy Saturday where, with no alerts, the car park is full for about an hour.
# At 35 (a heavier day) ParkAhead still helps, but less: reach limits how many drivers can shift.
PEAK_EXTRA = 30
demand = 30 + PEAK_EXTRA * np.exp(-0.5 * ((t - 19 * 60) / 50) ** 2)


def run(mode):
    occ, queue = CAP * START_OCC, 0.0
    late = np.zeros(n + SHIFT_MIN // STEP + 1)
    out = []
    lost = 0.0
    for i in range(n):
        arrive = demand[i] + late[i]
        leave = occ * STEP / MEAN_STAY
        if mode != "none":
            # The forecast looks one hour ahead using the same flow equation.
            ahead = occ
            for j in range(i, min(i + 12, n)):
                ahead += demand[j] - ahead * STEP / MEAN_STAY
            if ahead > CAP * TARGET:
                movable = demand[i] * REACH * RESPONSE if mode == "batch" else demand[i] * REACH
                if mode == "batch":
                    need = (ahead - CAP * TARGET) / 12  # spread the excess over the hour
                    shift = min(movable, need)
                else:
                    shift = movable
                    lost += shift * CANCEL_IF_WARNED
                    late[i + SHIFT_MIN // STEP] += shift * (1 - CANCEL_IF_WARNED)
                    arrive -= shift
                    shift = 0
                if mode == "batch":
                    late[i + SHIFT_MIN // STEP] += shift
                    arrive -= shift
        occ -= leave
        free = CAP - occ
        enter = min(free, queue + arrive)
        queue = queue + arrive - enter
        gave_up = queue * GIVE_UP
        queue -= gave_up
        lost += gave_up
        occ += enter
        out.append((t[i], occ / CAP, queue))
    return pd.DataFrame(out, columns=["minute", f"occ_{mode}", f"queue_{mode}"]), lost


frames, summary = [], {}
for mode in ("none", "all", "batch"):
    df, lost = run(mode)
    frames.append(df.set_index("minute"))
    summary[mode] = (df[f"occ_{mode}"].max(), df[f"queue_{mode}"].max(), lost,
                     (df[f"occ_{mode}"] >= 0.999).sum() * STEP)
res = pd.concat(frames, axis=1).reset_index()
res["time"] = res.minute.map(lambda m: f"{m // 60:02d}:{m % 60:02d}")
res.drop(columns="minute").round(3).to_csv("simulate_saturday.csv", index=False)

print(f"{'Case':<16}{'Peak full':>10}{'Max queue':>11}{'Visits lost':>13}{'Minutes full':>14}")
for mode, label in (("none", "No alerts"), ("all", "Warn everyone"), ("batch", "ParkAhead")):
    peak, q, lost, full = summary[mode]
    print(f"{label:<16}{peak:>9.0%}{q:>11.0f}{lost:>13.0f}{full:>14d}")

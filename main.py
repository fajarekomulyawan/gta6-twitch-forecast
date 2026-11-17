"""Forecast a launch day's Twitch viewers, hour by hour, from comparable launches.

Idea: a big game's release-day shape is not flat. Viewers surge and fade at
similar hours across past launches when each launch is measured against its
own first hour. So for every hour h we collect, from every comparable launch
in the case, the ratio

    r_h = (viewers in hour h of that launch's release day) / (its hour 1)

and forecast this case's quantiles as hour 1's print times the empirical
quantiles of those ratios. The spread therefore comes from how much real
launches actually disagreed with each other at that hour, not from a fixed
formula. Everything is deterministic: ratios are sorted, quantiles use
linear interpolation, and no clock, randomness or network is involved.

Runs as the grader runs it: python3 main.py with MAKEFUN_INPUT_DIR /
MAKEFUN_OUTPUT_DIR set locally, or /input and /output in the sandbox.
Standard library only.
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]
# A comparable counts only when its first hour was a real launch hour.
MIN_FIRST_HOUR = 1000
# Keep one wild comparable from dragging a quantile to an absurd place.
RATIO_MIN = 0.02
RATIO_MAX = 20.0


def round2(x):
    """Round to 2 decimals, half up, returning an int when whole."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if float(value).is_integer() else value


def quantile(sorted_values, tau):
    """The tau quantile of a sorted list, by linear interpolation."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    pos = (n - 1) * tau
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def launch_day_ratios(comparable):
    """Map hour index 0..23 of a comparable's release day to viewer ratios.

    Hour 0 of the release date is that launch's hour 1, so the ratio for
    forecast hour h (2..24) is day[h - 1] / day[0]. Returns None when the
    comparable has no usable release day.
    """
    day_date = str(comparable.get("day_start", ""))[:10]
    if not day_date:
        return None
    day = {}
    for point in comparable.get("hourly", []):
        stamp = str(point.get("from", ""))
        if stamp[:10] == day_date:
            try:
                day[int(stamp[11:13])] = float(point.get("viewers") or 0)
            except ValueError:
                continue
    first = day.get(0, 0.0)
    if first < MIN_FIRST_HOUR or len(day) < 18:
        return None
    return {h: day[h - 1] / first for h in range(2, 25) if (h - 1) in day}


def fallback_quantiles(p1, hour):
    """The persistence shape, used only if a case carries no comparables."""
    spread = 0.15 * math.sqrt(hour - 1)
    return [round2(p1 * math.exp(z * spread)) for z in Z]


def forecast_case(case):
    if case["levels"] != LEVELS:
        raise ValueError("unexpected levels")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError("no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))

    ratios_by_hour = {h: [] for h in range(2, 25)}
    for comparable in case.get("comparables") or []:
        ratios = launch_day_ratios(comparable)
        if ratios is None:
            continue
        for hour, ratio in ratios.items():
            if RATIO_MIN <= ratio <= RATIO_MAX:
                ratios_by_hour[hour].append(ratio)
    for hour in ratios_by_hour:
        ratios_by_hour[hour].sort()

    rows = []
    for wanted in case["forecast"]:
        hour = int(wanted["hour"])
        ratios = ratios_by_hour.get(hour, [])
        if len(ratios) >= 5:
            qs = [round2(p1 * quantile(ratios, tau)) for tau in LEVELS]
        else:
            qs = fallback_quantiles(p1, hour)
        # The output contract: every quantile above 0 and at most 1e9.
        qs = [max(1, min(1_000_000_000, q)) for q in qs]
        # Quantiles must never decrease along the row.
        for i in range(1, len(qs)):
            if qs[i] < qs[i - 1]:
                qs[i] = qs[i - 1]
        rows.append({"hour": hour, "q": qs})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        result = forecast_case(case)
        text = json.dumps(result, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()

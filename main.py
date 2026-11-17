"""Forecast a launch day's Twitch viewers, hour by hour, from comparable launches.

Method (v2, tuned by leave-one-out cross-validation over the comparables):

A big game's release-day shape is not flat: viewers surge and fade at similar
hours across past launches when each launch is measured against its own first
hour. For every hour h we collect, from every comparable launch, the ratio

    r_h = (viewers in hour h of that launch's release day) / (its hour 1)

and forecast this case's quantiles as hour 1's print times weighted quantiles
of those ratios. Three refinements over plain empirical quantiles, each kept
because it lowered the cross-validated pinball loss on the log scale (the
contest's own metric) for launches with a large first hour like this one:

1. Quality gate. A comparable counts only when its first hour was a real
   launch hour: at least 10,000 viewers and at least a quarter of its own
   day's peak. Launches that unlocked late in the UTC day (a global unlock at
   16:00Z, say) have a near-empty hour 1, so their ratios explode and say
   nothing about a midnight-rolling console launch like this one.
2. Size weighting. A comparable's weight falls off with the distance between
   its first hour and this case's, exp(-|ln p1 - ln h0| / 0.9): a launch that
   opened at 850k shapes the forecast of another huge launch more than one
   that opened at 30k, because the two audiences behave differently by hour.
3. Tier weighting. The case notes tag each comparable's tier; early-access
   contaminated launches count 0.7 and weak ones 0.6, since their release-day
   curves are distorted, and the target category's own pre-release history
   counts 0 (it is no launch at all).

Everything is deterministic: ratios are sorted, weighted quantiles use
linear interpolation on cumulative weights, and no clock, randomness or
network is involved. Standard library only.
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
MIN_FIRST_HOUR = 10000
MIN_FIRST_HOUR_PEAK_SHARE = 0.25
# Keep one wild comparable from dragging a quantile to an absurd place.
RATIO_MIN = 0.02
RATIO_MAX = 20.0
# How fast a comparable's weight decays with first-hour size distance (log units).
SIZE_SCALE = 0.9
# Trust the weighted pool only once it carries at least this much weight.
MIN_POOL_WEIGHT = 2.5
MIN_POOL_COUNT = 5
# Tier weights from the case notes; an untagged comparable counts in full.
TIER_WEIGHTS = {
    "comparable": 1.0,
    "early-access-contaminated": 0.7,
    "weak": 0.6,
    "target-history": 0.0,
}


def round2(x):
    """Round to 2 decimals, half up, returning an int when whole."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if float(value).is_integer() else value


def weighted_quantile(sorted_pairs, tau):
    """The tau quantile of (value, weight) pairs sorted by value.

    Linear interpolation across the cumulative-weight axis, so a pair with
    twice the weight spans twice the axis of an ordinary one.
    """
    total = sum(w for _, w in sorted_pairs)
    if total <= 0:
        return sorted_pairs[len(sorted_pairs) // 2][0]
    target = tau * total
    acc = 0.0
    prev_value, prev_acc = sorted_pairs[0][0], 0.0
    for value, weight in sorted_pairs:
        acc += weight
        if acc >= target:
            if acc == prev_acc:
                return value
            frac = (target - prev_acc) / (acc - prev_acc)
            return prev_value + (value - prev_value) * frac
        prev_value, prev_acc = value, acc
    return sorted_pairs[-1][0]


def tier_weight(comparable):
    """The weight the case notes' tier earns this comparable (1.0 untagged)."""
    unlock = str(comparable.get("unlock") or "")
    if "Tier:" not in unlock:
        return 1.0
    tier = unlock.split("Tier:", 1)[1].split(".", 1)[0].strip().lower()
    return TIER_WEIGHTS.get(tier, 1.0)


def launch_day_ratios(comparable):
    """Map hour index 0..23 of a comparable's release day to viewer ratios.

    Hour 0 of the release date is that launch's hour 1, so the ratio for
    forecast hour h (2..24) is day[h - 1] / day[0]. Returns None when the
    comparable has no usable release day: too few hours, or a first hour
    that was not a real launch hour (too small outright, or next to its
    own day's peak — the mark of a launch that unlocked late in the day).
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
    if len(day) < 18 or first < MIN_FIRST_HOUR:
        return None
    if first < MIN_FIRST_HOUR_PEAK_SHARE * max(day.values()):
        return None
    ratios = {h: day[h - 1] / first for h in range(2, 25) if (h - 1) in day}
    return ratios, first


def fallback_quantiles(p1, hour):
    """The persistence shape, used only if a case carries no usable comparables."""
    spread = 0.15 * math.sqrt(hour - 1)
    return [round2(p1 * math.exp(z * spread)) for z in Z]


def forecast_case(case):
    if case["levels"] != LEVELS:
        raise ValueError("unexpected levels")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError("no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))
    own_name = str((case.get("game") or {}).get("name") or "")

    # Weighted ratio pools, one per forecast hour. A comparable's weight is
    # set once — by its size distance to this case and by its tier — and the
    # same weight rides on every hour it speaks for.
    pools = {h: [] for h in range(2, 25)}
    for comparable in case.get("comparables") or []:
        if own_name and str(comparable.get("name") or "") == own_name:
            continue  # the target is never its own comparable
        found = launch_day_ratios(comparable)
        if found is None:
            continue
        ratios, first_hour = found
        size_weight = math.exp(-abs(math.log(p1) - math.log(first_hour)) / SIZE_SCALE)
        weight = size_weight * tier_weight(comparable)
        if weight <= 0:
            continue
        for hour, ratio in ratios.items():
            if RATIO_MIN <= ratio <= RATIO_MAX:
                pools[hour].append((ratio, weight))
    for hour in pools:
        pools[hour].sort(key=lambda pair: pair[0])

    rows = []
    for wanted in case["forecast"]:
        hour = int(wanted["hour"])
        pairs = pools.get(hour, [])
        total_weight = sum(w for _, w in pairs)
        if len(pairs) >= MIN_POOL_COUNT and total_weight >= MIN_POOL_WEIGHT:
            qs = [round2(p1 * weighted_quantile(pairs, tau)) for tau in LEVELS]
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

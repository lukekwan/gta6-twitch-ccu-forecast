#!/usr/bin/env python3
"""Forecast GTA VI's Twitch viewers hour by hour on release day.

Model: the launch-day shape is the median, across past big launches, of
each launch's hourly viewers divided by its own hour-1 viewers. The
median forecast for hour h is hour-1's print times that median ratio.
The spread is the interquartile range of the log ratios across
non-degenerate launches (ones whose hour 1 was a real launch hour, not
a pre-launch trickle), converted to a log standard deviation and clamped
to [0.10, 0.80]. Quantiles are lognormal around the median.

Reads every *.in file in $MAKEFUN_INPUT_DIR (else /input) and writes one
*.out file per case to $MAKEFUN_OUTPUT_DIR (else /output). Standard
library only, deterministic, no network.
"""

import json
import math
import os
import statistics
import sys

# Standard normal quantiles for the five levels [0.05, 0.25, 0.5, 0.75, 0.95].
Z = [-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817,
     1.6448536269514722]

SIGMA_FLOOR = 0.10
SIGMA_CAP = 0.80
# A launch whose hour 1 is under 5% of its own release-day peak had not
# really launched at hour 1 (fixed global unlock later in the day), so its
# ratios are degenerate and it is left out of the spread.
NONDEGENERATE_FRACTION = 0.05
MIN_CURVE_HOURS = 20


def release_day_curve(comp):
    """Hour (1..24) -> viewers for the comparable's release day (UTC)."""
    day = comp.get("day_start", "")[:10]
    curve = {}
    for row in comp.get("hourly") or []:
        start = row.get("from", "")
        if not start.startswith(day):
            continue
        try:
            hour = int(start[11:13]) + 1
            viewers = row.get("viewers")
        except (ValueError, TypeError):
            continue
        if 1 <= hour <= 24 and isinstance(viewers, (int, float)) and viewers > 0:
            curve[hour] = float(viewers)
    return curve


def is_nondegenerate(curve):
    """True when hour 1 was a real launch hour, not a pre-launch trickle."""
    return curve[1] >= NONDEGENERATE_FRACTION * max(curve.values())


def iqr_sigma(logs):
    """Robust log spread: interquartile range of log ratios / 1.349.

    Needs at least four observations; with fewer the quartile positions
    are too noisy to trust, so the caller falls back to a widening
    persistence spread instead.
    """
    ordered = sorted(logs)
    n = len(ordered)
    if n < 4:
        return None
    q1 = ordered[n // 4]
    q3 = ordered[(3 * n) // 4]
    return (q3 - q1) / 1.349


def forecast_case(case):
    known = case.get("known") or []
    p1 = 1.0
    if known:
        v = known[0].get("viewers")
        if isinstance(v, (int, float)) and v > 0 and math.isfinite(v):
            p1 = float(v)

    hours = [row.get("hour") for row in case.get("forecast") or []]
    hours = [h for h in hours if isinstance(h, int) and 2 <= h <= 24]
    if not hours:
        hours = list(range(2, 25))

    # Collect usable comparable curves.
    curves = []
    for comp in case.get("comparables") or []:
        curve = release_day_curve(comp)
        if curve.get(1) and len(curve) >= MIN_CURVE_HOURS:
            curves.append(curve)

    out_hours = []
    for h in hours:
        ratios = []
        spread_logs = []
        for curve in curves:
            if h not in curve:
                continue
            ratio = curve[h] / curve[1]
            if ratio > 0 and math.isfinite(ratio):
                ratios.append(ratio)
                if is_nondegenerate(curve):
                    spread_logs.append(math.log(ratio))
        if ratios:
            median_ratio = statistics.median(ratios)
            sigma = iqr_sigma(spread_logs)
            if sigma is None:
                sigma = 0.15 * math.sqrt(h - 1)
        else:
            # No comparable has this hour: fall back to persistence.
            median_ratio = 1.0
            sigma = 0.15 * math.sqrt(h - 1)
        sigma = max(SIGMA_FLOOR, min(SIGMA_CAP, sigma))
        median = p1 * median_ratio
        quantiles = []
        prev = 0.0
        for z in Z:
            q = median * math.exp(z * sigma)
            if not math.isfinite(q) or q <= 0:
                q = median if median > 0 else 1.0
            q = min(q, 1e9)
            q = max(q, prev)  # keep the five quantiles non-decreasing
            quantiles.append(round(q, 2))
            prev = q
        out_hours.append({"hour": h, "q": quantiles})
    return {"hours": out_hours}


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    names = sorted(n for n in os.listdir(in_dir) if n.endswith(".in"))
    for name in names:
        with open(os.path.join(in_dir, name), "r", encoding="utf-8") as f:
            case = json.load(f)
        result = forecast_case(case)
        stem = name[:-3]
        with open(os.path.join(out_dir, stem + ".out"), "w",
                  encoding="utf-8") as f:
            json.dump(result, f, separators=(",", ":"))
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

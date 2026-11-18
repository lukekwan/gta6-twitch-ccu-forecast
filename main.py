"""GTA VI Twitch launch-day forecast (make.fun gta6-twitch-ccu-forecast-01).

Scheme B: empirical quantile ratios.

For each hour h in 2..24, collect the ratios curve[h] / curve[1] across
all kept comparables (past big launches), where curve is a comparable's
release-day hourly viewers. For each target quantile level tau, take the
empirical quantile (type 7, linear interpolation) of those ratios and
multiply by the launch's own hour-1 viewers. No parametric shape is
assumed: the spread and the skew come straight from how past launches
actually grew or fell after their first hour.

A comparable is kept only if its release-day curve has hour 1 and at
least 20 hours, all viewers > 0, and hour-1 viewers >= 500 (a dead
launch carries no shape information). If an hour has no ratios at all,
fall back to a mild linear growth around hour 1.

Standard library only, deterministic, no network.
"""

import json
import os
import sys

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]


def release_day_curve(comp):
    """Return {hour: viewers} for the comparable's release day, or None."""
    day = comp["day_start"][:10]
    curve = {}
    for row in comp.get("hourly", []):
        ts = row.get("from", "")
        if not ts.startswith(day):
            continue
        hour = int(ts[11:13]) + 1
        viewers = row.get("viewers")
        if viewers is None or viewers <= 0:
            return None
        curve[hour] = viewers
    if 1 not in curve or len(curve) < 20:
        return None
    return curve


def quantile_type7(sorted_vals, tau):
    """Empirical quantile with linear interpolation (type 7)."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = tau * (n - 1)
    idx = int(pos)
    frac = pos - idx
    if idx >= n - 1:
        return sorted_vals[-1]
    return sorted_vals[idx] + frac * (sorted_vals[idx + 1] - sorted_vals[idx])


def forecast_case(case):
    hour1 = case["known"][0]["viewers"]
    levels = case.get("levels", LEVELS)

    curves = []
    for comp in case.get("comparables", []):
        curve = release_day_curve(comp)
        if curve is None:
            continue
        if curve[1] < 500:
            continue
        curves.append(curve)

    hours_out = []
    for h in range(2, 25):
        ratios = sorted(c[h] / c[1] for c in curves if h in c)
        qs = []
        for tau in levels:
            if ratios:
                ratio = quantile_type7(ratios, tau)
                q = hour1 * ratio
            else:
                q = hour1 * (1.0 + (h - 1) * 0.02 * (tau - 0.5))
            q = max(1.0, min(1e9, q))
            q = round(q, 4)
            qs.append(q)
        for i in range(1, len(qs)):
            if qs[i] < qs[i - 1]:
                qs[i] = qs[i - 1]
        hours_out.append({"hour": h, "q": qs})
    return {"hours": hours_out}


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    for name in sorted(os.listdir(in_dir)):
        if not name.endswith(".in"):
            continue
        with open(os.path.join(in_dir, name), "r", encoding="utf-8") as f:
            case = json.load(f)
        result = forecast_case(case)
        out_name = name[:-3] + ".out"
        with open(os.path.join(out_dir, out_name), "w", encoding="utf-8") as f:
            json.dump(result, f, separators=(",", ":"))
            f.write("\n")


if __name__ == "__main__":
    main()

# GTA VI Twitch Viewers Forecaster

[![make.fun](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/lukekwan/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/lukekwan/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)

Forecasts how many people watch Grand Theft Auto VI live on Twitch in
each hour of its release day (2026-11-19 UTC), given only the first
hour's viewer count. Entry for the
[make.fun bounty](https://make.fun/bounty/gta6-twitch-ccu-forecast-01).

## Model

The launch-day shape comes from the case's own comparables, computed at
runtime — nothing is hardcoded.

1. For each past big launch, take its release-day hourly curve and divide
   each hour's viewers by its own hour-1 viewers. That is the launch's
   shape ratio `r_h` for hour `h`.
2. The median ratio across all usable comparables is the shape. The
   median forecast for hour `h` is hour 1's print times that median
   ratio. Viewership dips in the early UTC hours, then builds as regions
   unlock and wake up (UK at 00:00 UTC, US East at 05:00 UTC, US West at
   08:00 UTC), peaking around hour 19-20 at about 2.4x hour 1.
3. The spread is the interquartile range of the log ratios across
   non-degenerate launches — launches whose hour 1 was a real launch
   hour, not a pre-launch trickle (hour 1 at least 5% of the launch's own
   release-day peak). Games that unlocked later in the day have hour-1
   counts near zero and ratios in the hundreds or thousands; they are
   left out of the spread so they do not inflate it. The IQR is
   converted to a log standard deviation (IQR / 1.349) and clamped to
   [0.10, 0.80]. The five quantiles are lognormal around the median:
   `q = median * exp(z * sigma)`.
4. Fallbacks: a comparable with no hour 1, or with fewer than 20 hours
   on its release day, is skipped. An hour no comparable covers falls
   back to persistence. If hour 1 is missing or zero, the level is 1.

## Validation

Leave-one-out cross-validation on the comparables in the practice cases
(each comparable forecast from all the others, scored by mean pinball
loss on the log scale, the competition's metric):

| set | this model | starter (flat at hour 1) |
| --- | --- | --- |
| all 37 usable comparables | 0.829 | 0.930 |
| console-only comparables (n=8, most like GTA VI) | 0.211 | 0.323 |

On the console-only launches — the ones that, like GTA VI, are
console-only rolling-midnight releases — the model cuts the loss by
about 35% (typical miss 38% vs 68% for persistence). The all-launch
number is worse for every model because it includes launches whose
hour 1 was near zero (a fixed unlock later in the day), which no
hour-1-anchored shape can predict.

## Files

- `main.py` — the forecaster (Python 3.13, standard library only).
- `README.md` — this file.
- `LICENSE` — MIT.

One detail worth stating: the GTA VI category's own pre-release history
is among the comparables (its hourly runs from the 2026-08-27
extended-look premiere to 2026-11-17), but it has no hour 1 on its
nominal release day, so the hour-1 requirement excludes it from the
shape automatically. No launch is excluded by name; the filters are
hour-1 presence, a minimum of 20 release-day hours, and the 5%-of-peak
rule for the spread.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `*.in` file in the input directory and writes one `*.out`
per case. Standard library only, no network, deterministic — two runs
write byte-identical output.

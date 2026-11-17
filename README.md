# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/fajarekomulyawan/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/fajarekomulyawan/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An entry for make.fun's **Forecast GTA VI's launch-day Twitch viewers hour by hour** bounty. The program forecasts, for each of hours 2 to 24 of GTA VI's release day, five quantiles (5%, 25%, 50%, 75%, 95%) of the Twitch concurrent viewers in the Grand Theft Auto VI category.

How it works: a big game's release-day shape is not flat — viewers surge and fade at similar hours across past launches when each launch is measured against its own first hour. For every hour h the program collects, from every comparable launch in the case file, the ratio r_h = (viewers in hour h of that launch's release day) / (its hour 1), and forecasts this case's quantiles as hour 1's print times weighted quantiles of those ratios. Version 2 adds three refinements, each kept because it lowered the leave-one-out cross-validated pinball loss (the contest's own metric) over the comparables themselves: a quality gate (a comparable counts only when its first hour was a real launch hour — at least 10,000 viewers and a quarter of its day's peak — so late-in-the-day global unlocks with a near-empty hour 1 cannot poison the pool), size weighting (weight falls off with the log distance between the comparable's first hour and this case's, so huge launches shape a huge launch's forecast most), and tier weighting (early-access-contaminated comparables count 0.7, weak ones 0.6, the target category's own pre-release history 0). If a case carried too few comparables it falls back to a persistence forecast with a widening log spread. Deterministic, standard library only, no network.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

where `input/` holds one `<id>.in` case file per run; the program writes one `<id>.out` forecast per case to the output directory.

## License

MIT — see `LICENSE`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=cxst033q&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>

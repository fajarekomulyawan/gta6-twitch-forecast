# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An entry for make.fun's **Forecast GTA VI's launch-day Twitch viewers hour by hour** bounty.

The program forecasts, for each of hours 2 to 24 of GTA VI's release day, five
quantiles (5%, 25%, 50%, 75%, 95%) of the Twitch concurrent viewers in the
Grand Theft Auto VI category.

## How it works

A big game's release-day shape is not flat: viewers surge and fade at similar
hours across past launches when each launch is measured against its own first
hour. For every hour h the program collects, from every comparable launch in
the case file, the ratio

    r_h = (viewers in hour h of that launch's release day) / (its hour 1)

and forecasts this case's quantiles as hour 1's print times the empirical
quantiles of those ratios. The spread comes from how much real launches
actually disagreed with each other at that hour. If a case carried too few
comparables it falls back to a persistence forecast with a widening log
spread. Deterministic, standard library only, no network.

## Run it

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

where `input/` holds one `<id>.in` case file per run; the program writes one
`<id>.out` forecast per case to the output directory.

## License

MIT — see `LICENSE`.

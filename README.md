# Pedibus — Châtel-St-Denis

Analysis of the parent interest survey for walking school buses. Groups
households by real walking distance and renders an interactive map on swisstopo
tiles, so you can see which Pedibus routes are actually viable.

Code, identifiers and documentation are in English. Everything the user sees —
CLI output, map labels, exported column headers — is in French, and all French
strings live in section 9 of `config.py`.

## Setup

```bash
conda env create -f environment.yml
conda activate pedibus
```

To update the environment later:

```bash
conda env update -f environment.yml --prune
```

## Usage

Drop the survey export into `data/` as `pedibus_survey.xlsx` (or point
`SURVEY_FILE` in `config.py` elsewhere), then:

```bash
python cli.py all
```

The four steps can also run one at a time, in order. Each reads the previous
step's file, so you can re-run a single step after changing a setting:

```bash
python cli.py prepare      # spreadsheet -> normalised table
python cli.py geocode      # addresses -> lat/lon (cached)
python cli.py cluster      # group by distance
python cli.py map          # HTML map
```

Useful options:

```bash
python cli.py cluster --radius 400     # wider groups (neighbourhoods)
python cli.py cluster --threshold 3    # a route works with 3 volunteers
python cli.py all --no-map             # everything except the HTML
python cli.py settings                 # show current configuration
python cli.py --help
```

Geocoding is the slow step — about a minute the first time — but results are
cached, so later runs are instant. In practice, after one `all`, you only re-run
`cluster` and `map` to compare settings.

## Output

Written to `output/`, numbered by step:

| File | Contents |
|---|---|
| `1_survey_normalised.csv` | cleaned survey: duplicates removed, addresses completed, street variants merged, commitment reduced to four values |
| `2_households_geocoded.csv` | in-scope households with `lat` and `lon` |
| `2_schools.json` | school coordinates |
| `3_clusters.csv` | the same households with their `cluster` |
| `4_map.html` | the map — open in a browser |
| `.geocode_cache.json` | geocoding cache — keep it |

The map has four toggleable layers: households coloured by commitment, proximity
groups, walking-time rings around each school, and the schools themselves. A
control switches between the swisstopo map and aerial imagery. The side panel
ranks groups by volunteer count, the only column that decides whether a route
can run.

## Configuration

Everything lives in `config.py`, split into nine sections.

| Section | What it holds |
|---|---|
| 1. Input | survey file path, column names |
| 2. Outputs | the five output paths and the cache |
| 3. Clustering | `CLUSTER_RADIUS_M`, `MIN_HOUSEHOLDS`, `ROUTE_THRESHOLD` |
| 4. Schools | addresses or coordinates, walking rings, pace |
| 5. Scope | areas already served by a bus, excluded from analysis |
| 6. Street names | the `STREETS` table merging spelling variants |
| 7. Geocoding | API URLs, timeout, politeness delay |
| 8. Map | tiles, colours, marker sizes |
| 9. French strings | every visible label |

The four worth knowing:

- `CLUSTER_RADIUS_M` — 250 m gives "same stretch of street" groups, 400 m gives
  neighbourhoods. Comparing both is informative.
- `ROUTE_THRESHOLD` — volunteers needed before a route can run a full year.
  Defaults to 4; adjust once Pedibus Fribourg confirms what holds in practice.
  It drives both the terminal count and the green highlight on the map.
- `SCHOOLS` — the addresses are guesses. Fix them, or better, replace each with a
  `(46.52xx, 6.90xx)` tuple read off [map.geo.admin.ch](https://map.geo.admin.ch).
- `STREETS` — extend it when a later survey turns up a street the table doesn't
  know. Unknown streets still geocode; only their group label is raw.

## Architecture

```
cli.py           command-line interface (Typer)
config.py        settings and French strings — the only file to edit day to day
survey.py        spreadsheet -> normalised table
geocoding.py     address -> lat/lon (geo.admin.ch, Nominatim fallback, disk cache)
clustering.py    haversine DBSCAN, summary, map envelopes
mapping.py       HTML template (Leaflet + swisstopo tiles)
```

The four domain modules don't depend on `cli.py` — import them straight into a
notebook if that's easier.

## Reading the results

In the summary, `cluster = -1` is not a group: it collects households with no
neighbour inside the radius.

The column that matters is `volunteers`. Four or more covers a school week; two
or three means merging with an adjacent group; one or zero leads nowhere even
when demand is high. A group with many households and few volunteers is a place
to recruit, not a place to open a route.

## Notes

Both geocoders are free and need no API key. The cache spares them unnecessary
traffic — keep it.

This repository handles names and home addresses of families with children.
`.gitignore` excludes `data/` and `output/` wholesale; keep the repository
private regardless.

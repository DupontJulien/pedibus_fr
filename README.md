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
python cli.py cluster --diameter 600   # wider groups (neighbourhoods)
python cli.py cluster --threshold 3    # a route works with 3 volunteers
python cli.py all --no-map             # everything except the HTML
python cli.py check                    # geocoding sanity check
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

Base tiles come from swisstopo, which allows this use and shows Swiss footpaths
and crossings in far more detail than any general-purpose map. OpenStreetMap is
deliberately **not** used as a fallback: its tile usage policy forbids this kind
of access to volunteer-run servers, and the tiles come back blocked.

WMTS REST orders the axes `{z}/{y}/{x}`, the reverse of Leaflet's default, and
published examples disagree on what swisstopo actually serves. The page tries one
order and swaps to the other after four tile errors, so it sorts itself out.

If the map still stays blank, a banner at the bottom left says what failed:
Leaflet not loading from the CDN, no tiles arriving, or no households to draw.
Markers, groups and the summary table work regardless of the tiles.

The layer selector sits at the **top left**, below the zoom buttons — the legend
panel occupies the top right.

The map has four toggleable layers: households coloured by commitment, proximity
groups, walking-time rings around each school, and the schools themselves.

Each group carries its number at its centre, matching the `N°` column in the
side panel and in the terminal summary, so a row can be found on the map at a
glance. Set `CLUSTER_SHOW_NUMBER = False` to drop the on-map labels.

Groups are an orange wash with a solid orange outline — continuous, never
dashed, so it is never mistaken for a walking-time ring, which are black and
dashed. Overlapping groups show as a deeper orange.

### Styling

Section 8 holds one dict per circle type, and each is passed straight to Leaflet,
so any Leaflet path option works: `color` (the stroke), `weight`, `opacity`,
`dashArray` (`None` draws a continuous line), `fillColor`, `fillOpacity`,
`stroke`, `fill`.

| Dict | What it styles |
|---|---|
| `HOUSEHOLD_STYLE` | household dots — outline and transparency; the fill colour comes from `COLORS` |
| `HOUSEHOLD_STYLE_NOT_INTERESTED` | the same dots for households that answered "non" |
| `CLUSTER_STYLE` | the orange group washes |
| `WALK_RING_STYLE` | the black walking-time rings |
| `SCHOOL_STYLE` | the square school markers (drawn in HTML, so `size`, `borderWidth`, `cornerRadius`) |

Ring widths and dashes are interpolated between `WALK_RING_WIDTH_MAX` /
`_MIN` and `WALK_RING_DASH_MAX` / `_MIN` across however many rings
`WALK_CIRCLES_MIN` defines, so the innermost is always the thickest.

Household markers: **colour** is commitment — green for a fixed volunteer, amber
for an occasional one, grey for neither. Households that answered "non" to the
interest question are drawn in one flat dark grey (`COLOR_NOT_INTERESTED`) at
`NOT_INTERESTED_SCALE` (60%) of normal size. They are shown because they reveal
where a street actually runs, but they are not demand. Set
`SHOW_NOT_INTERESTED = False` to leave them out entirely.

The **walking-time rings** are the black dashed circles around each school, one
per entry in `WALK_CIRCLES_MIN` — 5, 10 and 15 minutes by default. Each carries
its duration as a label, and the lines thin outwards: thick for 5 minutes, thin
for 15, so you can tell them apart at a glance without reading every label.

Radii come from `WALK_SPEED_KMH` (4 km/h, a 6-to-10-year-old's pace) and are
straight-line distances, so a real walk following streets runs roughly a third
longer: a household on the 10-minute ring is about 13 minutes away on foot. They
answer one question — is this group close enough to its school for a walking
route to make sense at all. A
control switches between the swisstopo map and aerial imagery. The side panel
ranks groups by volunteer count, the only column that decides whether a route
can run.

## Configuration

Everything lives in `config.py`, split into nine sections.

| Section | What it holds |
|---|---|
| 1. Input | survey file path, column names |
| 2. Outputs | the five output paths and the cache |
| 3. Clustering | `CLUSTER_METHOD`, `CLUSTER_DIAMETER_M`, `MIN_HOUSEHOLDS`, `CLUSTER_INTERESTED_ONLY`, `ROUTE_THRESHOLD` |
| 4. Schools | addresses or coordinates, walking rings, pace |
| 5. Scope | areas already served by a bus, excluded from analysis |
| 6. Street names | the `STREETS` table merging spelling variants |
| 7. Geocoding | API URLs, timeout, politeness delay |
| 8. Map | tiles, and one style dict per circle type |
| 9. French strings | every visible label |

The four worth knowing:

- `CLUSTER_DIAMETER_M` — the widest a group may span, end to end. 200 m keeps a
  group to a handful of neighbouring houses; 400 to 600 m gives
  neighbourhood-sized groups. The `spread_m` column reports what each group
  actually spans, so you can see how close to the limit it sits.
- `CLUSTER_INTERESTED_ONLY` — on by default. Households that answered "non" take
  no part in the clustering: they are not demand, and including them would
  inflate group sizes and drag group centres towards homes that will never use a
  route. They still appear on the map, marked as isolated.
- `ROUTE_THRESHOLD` — volunteers needed before a route can run a full year.
  Defaults to 4; adjust once Pedibus Fribourg confirms what holds in practice.
  It drives both the terminal count and the green highlight on the map.
- `SCHOOLS` — addresses taken from the school's own access plan. If the geocoder
  still places one wrongly, replace it with a `(46.52xx, 6.90xx)` tuple read off
  [map.geo.admin.ch](https://map.geo.admin.ch); `check` will no longer be able to
  mislead you.
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

## Checking the geocoding

```bash
python cli.py check
```

Reports four things that silently distort the grouping:

- **different addresses sharing one coordinate** — the geocoder fell back to the
  middle of a street or of the commune, so homes land on the same point and get
  grouped as if they were neighbours;
- **one address, several answers** — a couple who both replied, or two families in
  the same building. Only you can tell which, so they are counted as one
  household: that understates demand rather than inflating it, and the
  volunteers are still counted individually;
- **distance between street centres** — a quick sanity check on the geography;
- **streets that span more than `CLUSTER_DIAMETER_M`** — these legitimately split
  across several groups, which is why the same street name can appear twice in
  the summary.

That last point matters when reading results: a long street like Lac Lussy spans
more than one group. Groups are therefore labelled by **address**, not by street
name — `Lac Lussy 4, 5` and `Lac Lussy 92, 106` are two different places a
kilometre apart, and the label says so. A group covering four or more numbers on
one street is shortened to a range: `Montmoirin 5-14 (4 nos)`.

## Clustering method

`CLUSTER_METHOD = "complete"` uses complete-linkage agglomerative clustering,
which bounds each group's *diameter*: every household is within
`CLUSTER_DIAMETER_M` of every other one in its group.

DBSCAN (`--method dbscan`) is kept for comparison but should not be used here.
It grows groups by chaining: in a village where houses sit 70–80 m apart along
every street, one household links to the next all the way across town, and the
whole place collapses into a single group whatever radius you pick. On this
survey it produces one group of 72 households spanning 1.8 km — useless for
planning a walking route.

## Reading the results

Groups are numbered from 1, largest first, so the table reads in size order and
the numbers ascend together. **Group 0 is not a group**: it collects everything
left over — homes with no neighbour close enough to join one, and every
household that answered "non" while `CLUSTER_INTERESTED_ONLY` is on. It is shown
greyed at the bottom of the table and draws no orange wash on the map.

`households` counts **distinct addresses**, not answers: two parents of the same
home are one household, and `answers` records how many replies that covers.
Clustering runs on addresses too, so a pair of replies from one address can never
form a group on its own. `volunteers` stays a count of people — two adults at one
address really are two possible accompanists.

With `CLUSTER_INTERESTED_ONLY` on — the default — only interested households take
part, so the figure is demand rather than a count of replies.

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

# -*- coding: utf-8 -*-
"""Project settings.

Everything tunable lives here; nothing is hard-coded elsewhere.
Code and identifiers are in English, user-facing strings are in French
and grouped in the last section.
"""

from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

# ==========================================================================
# 1. INPUT
# ==========================================================================

SURVEY_FILE = DATA_DIR / "pedibus_survey.xlsx"

# Survey columns, in the order they appear in the spreadsheet.
SURVEY_COLUMNS = ["name", "interested", "commitment", "would_use",
                  "time_slots", "comment", "address"]

# ==========================================================================
# 2. OUTPUTS
# ==========================================================================
# Each step reads the previous step's file, so steps can be re-run alone.

NORMALISED_FILE = OUTPUT_DIR / "1_survey_normalised.csv"
GEOCODED_FILE = OUTPUT_DIR / "2_households_geocoded.csv"
SCHOOLS_FILE = OUTPUT_DIR / "2_schools.json"
CLUSTERED_FILE = OUTPUT_DIR / "3_clusters.csv"
MAP_FILE = OUTPUT_DIR / "4_map.html"
GEOCODE_CACHE = OUTPUT_DIR / ".geocode_cache.json"

# ==========================================================================
# 3. CLUSTERING
# ==========================================================================

# "complete" bounds the group's diameter: every household is within
# CLUSTER_DIAMETER_M of every other one in its group. That is what a walking
# route needs, and it is immune to the chaining that makes DBSCAN swallow a
# whole village. "dbscan" is kept for comparison only.
CLUSTER_METHOD = "complete"

CLUSTER_DIAMETER_M = 200   # widest spread allowed inside one group
MIN_HOUSEHOLDS = 2         # below this a group is reported as isolated

# Households that answered "non" to the interest question take no part in the
# clustering: they are not demand, and letting them join would inflate group
# sizes and pull group centres towards homes that will never use a route.
# They still appear on the map, marked as isolated.
CLUSTER_INTERESTED_ONLY = True

# Volunteers needed before a route can realistically run for a whole year.
# Adjust once Pedibus Fribourg confirms what works in practice.
ROUTE_THRESHOLD = 4

# ==========================================================================
# 4. SCHOOLS
# ==========================================================================
# Either an address (geocoded automatically) or a (lat, lon) tuple read off
# https://map.geo.admin.ch -- more reliable.

# Addresses taken from the school's own access plan (epchatelstdenis.ch).
SCHOOLS = {
    "Ecole des Pleiades": "Route des Pleiades 30, 1618 Chatel-St-Denis",
    "Ecole du Lussy": "Chemin de Crey-Derrey 1, 1618 Chatel-St-Denis",
    "Ecole du Bourg": "Le Bourg 117, 1618 Chatel-St-Denis",
}

WALK_CIRCLES_MIN = [5, 10, 15]   # walking-time rings drawn around each school
WALK_SPEED_KMH = 4.0             # pace of a 6-10 year old

# ==========================================================================
# 5. SCOPE
# ==========================================================================
# Areas already served by a school bus or the 492 line: excluded from the
# analysis. Matched against the flattened address (lowercase, no accents).

OUT_OF_SCOPE = {"cierne", "rosalys", "dailles", "verollys",
                "moille critsou", "paccot", "frasse"}

# ==========================================================================
# 6. STREET NAMES
# ==========================================================================
# Maps spelling variants onto one label. The key is searched in the flattened
# address once the number, postcode and "route de" prefix have been stripped.
# Add any street a later survey turns up.

STREETS = {
    "montmoirin": "Montmoirin",
    "lac lussy": "Lac Lussy", "lussy n": "Lac Lussy",
    "montreux": "Montreux",
    "fruence": "Fruence",
    "crets": "Crets",
    "rocasse": "Rocasse",
    "champ bochet": "Champ Bochet",
    "peralla": "Peralla",
    "coula": "Coula",
    "misets": "Misets",
    "sires": "Sires",
    "champ thomas": "Champ Thomas",
    "montimbert": "Montimbert",
    "bourg": "Le Bourg",
    "pontille": "Pontille",
    "prayoud": "Prayoud",
    "ebastements": "Ebastements",
    "veveyse": "Veveyse",
    "bosquets": "Bosquets",
    "lechere": "Lechere",
    "rochettes": "Rochettes",
    "gare": "Place de la Gare",
    "gottau": "Gottau",
    "chaussin": "Chaussin",
    "crey-derrey": "Crey-Derrey",
    "derriere chateau": "Derriere le Chateau",
    "planiere": "Planiere",
    "chardonnerets": "Chardonnerets",
    "pleiades": "Rte des Pleiades",
    "grand rue": "Grand-Rue",
}

# Appended to incomplete addresses so geocoding resolves.
# Some answers hold two addresses ("X 22 et Y 30"). Only the first is kept.
ADDRESS_SEPARATORS = [" et ", " / ", " ou ", " + ", " & ", ";"]

POSTCODE_DEFAULT = ", 1618 Chatel-St-Denis"
POSTCODE_PACCOTS = ", 1619 Les Paccots"
COUNTRY = ", Suisse"

# ==========================================================================
# 7. GEOCODING
# ==========================================================================

SWISSTOPO_API = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
NOMINATIM_API = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "pedibus-chatel/1.0 (conseil des parents)"
API_TIMEOUT = 12          # seconds
API_PAUSE = 0.25          # politeness delay between calls

# ==========================================================================
# 8. MAP
# ==========================================================================
# Tiles ---------------------------------------------------------------------
LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css"
LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"

# No OpenStreetMap fallback: their tile usage policy forbids this kind of
# access to volunteer-run servers, and the tiles come back blocked.

# WMTS REST puts the axes in the order {TileMatrix}/{TileRow}/{TileCol}, i.e.
# {z}/{y}/{x}, which is the reverse of Leaflet's default. Published examples
# disagree on what swisstopo actually serves, so the page tries this order and
# silently swaps to the other one if tiles come back as errors.
TILES_SWISS_TEMPLATE = ("https://wmts.geo.admin.ch/1.0.0/{layer}"
                        "/default/current/3857/{axes}.jpeg")
SWISS_LAYER_MAP = "ch.swisstopo.pixelkarte-farbe"
SWISS_LAYER_AERIAL = "ch.swisstopo.swissimage"
AXES_PRIMARY = "{z}/{y}/{x}"
AXES_FALLBACK = "{z}/{x}/{y}"


def _swiss_tiles(layer, axes):
    return (TILES_SWISS_TEMPLATE
            .replace("{layer}", layer)
            .replace("{axes}", axes))


TILES_MAP = _swiss_tiles(SWISS_LAYER_MAP, AXES_PRIMARY)
TILES_MAP_ALT = _swiss_tiles(SWISS_LAYER_MAP, AXES_FALLBACK)
TILES_AERIAL = _swiss_tiles(SWISS_LAYER_AERIAL, AXES_PRIMARY)
TILES_AERIAL_ALT = _swiss_tiles(SWISS_LAYER_AERIAL, AXES_FALLBACK)
ATTRIBUTION = '&copy; <a href="https://www.swisstopo.admin.ch">swisstopo</a>'

MAX_ZOOM = 19
# swisstopo serves no tile above this zoom in EPSG:3857; past it Leaflet must
# upscale rather than request tiles that do not exist (which renders grey).
MAX_NATIVE_ZOOM = 17

# Where Leaflet puts the layer selector. Keep it clear of the legend panel,
# which sits top right.
LAYER_CONTROL_POSITION = "topleft"

# Styles --------------------------------------------------------------------
# Every key below is passed straight to Leaflet, so anything Leaflet accepts
# works here: color (stroke), weight, opacity, dashArray, fillColor,
# fillOpacity, stroke, fill. dashArray None draws a continuous line.

# Household dots. Fill colour comes from commitment (section 9); these are the
# outline and transparency shared by every dot.
MARKER_RADIUS_VOLUNTEER = 11      # pixels, a household that will accompany
MARKER_RADIUS_PLAIN = 8           # pixels, a household that will not

# Households that answered "non" to the interest question keep the same marker
# shape, in one flat colour and at a fraction of the size.
SHOW_NOT_INTERESTED = True
NOT_INTERESTED_SCALE = 0.6

HOUSEHOLD_STYLE = {
    "color": "#ffffff",
    "weight": 2,
    "opacity": 1,
    "fillOpacity": 0.95,
}
HOUSEHOLD_STYLE_NOT_INTERESTED = {
    "color": "#ffffff",
    "weight": 1.5,
    "opacity": 1,
    "fillOpacity": 0.95,
}

# Proximity groups: solid orange outline, never dashed, so it cannot be taken
# for a walking-time ring.
CLUSTER_PADDING_M = 45            # how far the wash extends past the outermost home

# Print each group's number at its centre, so a row in the table can be found
# on the map at a glance.
CLUSTER_SHOW_NUMBER = True

CLUSTER_STYLE = {
    "color": "#f08a24",
    "weight": 2.5,
    "opacity": 1,
    "dashArray": None,
    "fillColor": "#f08a24",
    "fillOpacity": 0.35,
}

# Walking-time rings: black, dashed, thick for the nearest ring and thinning
# outwards. Widths and dashes are interpolated between the two extremes across
# however many rings WALK_CIRCLES_MIN defines.
WALK_RING_STYLE = {
    "color": "#1a1a1a",
    "opacity": 0.75,
    "fill": False,
}
WALK_RING_WIDTH_MAX = 3.2         # innermost ring
WALK_RING_WIDTH_MIN = 1.0         # outermost ring
WALK_RING_DASH_MAX = (10, 4)      # innermost: long dashes, tight gaps
WALK_RING_DASH_MIN = (5, 10)      # outermost: short dashes, wide gaps
WALK_RING_LABEL = "{minutes} min"

# School markers: a square drawn in HTML, not a Leaflet path.
SCHOOL_STYLE = {
    "size": 20,                   # outer box, pixels
    "color": "#1d4ed8",
    "borderColor": "#ffffff",
    "borderWidth": 3,
    "cornerRadius": 4,
}

# ==========================================================================
# 9. FRENCH USER-FACING STRINGS
# ==========================================================================
# Every label the user sees. Translating the tool means editing this section
# and nothing else.

# Commitment categories, derived from the survey wording.
COMMITMENT_FIXED = "Fixe"
COMMITMENT_OCCASIONAL = "Occasionnel"
COMMITMENT_BOTH = "Fixe + occasionnel"
COMMITMENT_NONE = "Pas accompagnant"

IN_SCOPE = "Chatel"
OUT_OF_SCOPE_LABEL = "Hors (bus)"
GROUP_OUT_OF_SCOPE = "Paccots / Frasse"
GROUP_NO_ADDRESS = "(sans adresse)"

# Fill colour of each household dot, by commitment.
COLORS = {
    COMMITMENT_FIXED: "#1a7f37",
    COMMITMENT_BOTH: "#1a7f37",
    COMMITMENT_OCCASIONAL: "#c77700",
    COMMITMENT_NONE: "#8a94a0",
}

# Households that answered "non" to the interest question: one flat colour,
# whatever their commitment.
COLOR_NOT_INTERESTED = "#5b6672"

MAP_TITLE = "Pedibus &ndash; interet des parents"
MAP_PAGE_TITLE = "Pedibus &ndash; Chatel-St-Denis"
MAP_LEGEND_FIXED = "Accompagnant fixe"
MAP_LEGEND_OCCASIONAL = "Accompagnant occasionnel"
MAP_LEGEND_PLAIN = "Interesse, sans accompagner"
MAP_LEGEND_NOT_INTERESTED = "Pas interesse"
MAP_LEGEND_SCHOOL = "Ecole"
MAP_LAYER_MAP = "Carte swisstopo"
MAP_LAYER_AERIAL = "Vue aerienne"
# Where Leaflet puts the layer selector. Keep it clear of the legend panel,
# which sits top right.
LAYER_CONTROL_POSITION = "topleft"

MAP_STATUS_NO_LEAFLET = (
    "Leaflet n'a pas pu etre charge depuis le reseau. "
    "Verifie ta connexion, puis recharge la page.")
MAP_LAYER_HOUSEHOLDS = "Domiciles"
MAP_LAYER_CLUSTERS = "Groupes"
MAP_LAYER_WALK = "Temps de marche"
MAP_LAYER_SCHOOLS = "Ecoles"
MAP_COL_NUMBER = "N\u00b0"
MAP_COL_GROUP = "Groupe"
MAP_COL_HOUSEHOLDS = "Foyers"
MAP_COL_INTERESTED = "Interesses"
MAP_COL_VOLUNTEERS = "Accomp."
MAP_ISOLATED = "Groupe 0"
LABEL_LEFTOVERS = "Isoles et non interesses"

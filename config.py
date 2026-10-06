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

CLUSTER_RADIUS_M = 250     # 250 m = same stretch of street; 400 m = neighbourhood
MIN_HOUSEHOLDS = 2         # smallest group DBSCAN will form

# Volunteers needed before a route can realistically run for a whole year.
# Adjust once Pedibus Fribourg confirms what works in practice.
ROUTE_THRESHOLD = 4

# ==========================================================================
# 4. SCHOOLS
# ==========================================================================
# Either an address (geocoded automatically) or a (lat, lon) tuple read off
# https://map.geo.admin.ch -- more reliable.

SCHOOLS = {
    "Ecole des Pleiades": "Route des Pleiades 24, 1618 Chatel-St-Denis",
    "Ecole du Lussy": "Route du Lac Lussy 30, 1618 Chatel-St-Denis",
    "Ecole du Bourg": "Le Bourg 1, 1618 Chatel-St-Denis",
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

LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css"
LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"

TILES_MAP = ("https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe"
             "/default/current/3857/{z}/{x}/{y}.jpeg")
TILES_AERIAL = ("https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage"
                "/default/current/3857/{z}/{x}/{y}.jpeg")
ATTRIBUTION = '&copy; <a href="https://www.swisstopo.admin.ch">swisstopo</a>'
MAX_ZOOM = 19

COLOR_SCHOOL = "#1d4ed8"
COLOR_CLUSTER = "#55606c"
MARKER_RADIUS_VOLUNTEER = 7     # pixels
MARKER_RADIUS_PLAIN = 5
CLUSTER_PADDING_M = 45          # how far the group circle extends past its edge

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

# Colour of each household dot, by commitment.
COLORS = {
    COMMITMENT_FIXED: "#1a7f37",
    COMMITMENT_BOTH: "#1a7f37",
    COMMITMENT_OCCASIONAL: "#c77700",
    COMMITMENT_NONE: "#8a94a0",
}

MAP_TITLE = "Pedibus &ndash; interet des parents"
MAP_PAGE_TITLE = "Pedibus &ndash; Chatel-St-Denis"
MAP_LEGEND_FIXED = "Accompagnant fixe"
MAP_LEGEND_OCCASIONAL = "Accompagnant occasionnel"
MAP_LEGEND_PLAIN = "Interesse, sans accompagner"
MAP_LEGEND_SCHOOL = "Ecole"
MAP_LAYER_MAP = "Carte swisstopo"
MAP_LAYER_AERIAL = "Vue aerienne"
MAP_LAYER_HOUSEHOLDS = "Domiciles"
MAP_LAYER_CLUSTERS = "Groupes"
MAP_LAYER_WALK = "Temps de marche"
MAP_LAYER_SCHOOLS = "Ecoles"
MAP_COL_GROUP = "Groupe"
MAP_COL_HOUSEHOLDS = "Foyers"
MAP_COL_VOLUNTEERS = "Accomp."
MAP_ISOLATED = "Isole"

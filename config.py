# -*- coding: utf-8 -*-
"""Tous les reglages du projet.

C'est le seul fichier a modifier. Aucun parametre n'est code en dur ailleurs.
"""

from pathlib import Path

RACINE = Path(__file__).parent
DATA = RACINE / "data"
SORTIE = RACINE / "sortie"

# ==========================================================================
# 1. ENTREE
# ==========================================================================

EXCEL = DATA / "Lignes_Pedibus_-_Sondage_d_interet_aupres_des_parents.xlsx"

# Les colonnes du sondage, dans leur ordre d'apparition.
COLONNES = ["nom", "interet", "engagement", "utiliserait",
            "moments", "commentaire", "adresse"]

# ==========================================================================
# 2. SORTIES
# ==========================================================================

# Chaque etape lit le fichier de la precedente : on peut les relancer une a une.
FICHIER_NORMALISE = SORTIE / "1_sondage_normalise.csv"   # etape preparer
FICHIER_GEOCODE = SORTIE / "2_foyers_geocodes.csv"       # etape geocoder
FICHIER_ECOLES = SORTIE / "2_ecoles.json"                # etape geocoder
FICHIER_GROUPES = SORTIE / "3_groupes.csv"               # etape grouper
FICHIER_CARTE = SORTIE / "4_carte.html"                  # etape carte
CACHE = SORTIE / ".cache_geocode.json"

# ==========================================================================
# 3. REGROUPEMENT
# ==========================================================================

RAYON_CLUSTER_M = 250     # 250 m = "meme bout de rue" ; 400 m = quartier
MIN_FOYERS = 2            # taille minimale d'un groupe

# Nombre d'accompagnants a partir duquel une ligne peut tenir une semaine.
# A ajuster selon ce que dit Pedibus Fribourg.
SEUIL_LIGNE = 4

# ==========================================================================
# 4. ECOLES
# ==========================================================================
# Soit une adresse (geocodee automatiquement), soit un tuple (lat, lon)
# releve sur https://map.geo.admin.ch -- plus sur.

ECOLES = {
    "Ecole des Pleiades": "Route des Pleiades 24, 1618 Chatel-St-Denis",
    "Ecole du Lussy": "Route du Lac Lussy 30, 1618 Chatel-St-Denis",
    "Ecole du Bourg": "Le Bourg 1, 1618 Chatel-St-Denis",
}

CERCLES_MIN = [5, 10, 15]   # cercles de temps de marche autour des ecoles
VITESSE_KMH = 4.0           # allure d'un enfant de 6-10 ans

# ==========================================================================
# 5. PERIMETRE
# ==========================================================================
# Secteurs desservis par un bus scolaire ou la ligne 492 : exclus de l'analyse.
# Mots cherches dans l'adresse mise a plat (minuscules, sans accents).

HORS_PERIMETRE = {"cierne", "rosalys", "dailles", "verollys",
                  "moille critsou", "paccot", "frasse"}

# ==========================================================================
# 6. NOMS DE RUES
# ==========================================================================
# Rapproche les orthographes d'une meme rue. La cle est cherchee dans
# l'adresse une fois mise a plat (sans accents, sans numero, sans "route de").
# Ajouter ici toute nouvelle rue apparaissant dans un sondage ulterieur.

RUES = {
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

LIBELLE_HORS = "Paccots / Frasse"
LIBELLE_SANS_ADRESSE = "(sans adresse)"

# Ajoutes aux adresses incompletes, pour que le geocodage aboutisse.
NPA_DEFAUT = ", 1618 Chatel-St-Denis"
NPA_PACCOTS = ", 1619 Les Paccots"
PAYS = ", Suisse"

# ==========================================================================
# 7. GEOCODAGE
# ==========================================================================

API_SWISSTOPO = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
API_NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "pedibus-chatel/1.0 (conseil des parents)"
TIMEOUT_API = 12          # secondes
PAUSE_API = 0.25          # politesse entre deux appels

# ==========================================================================
# 8. CARTE
# ==========================================================================

LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css"
LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"

TUILE_CARTE = ("https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe"
               "/default/current/3857/{z}/{x}/{y}.jpeg")
TUILE_PHOTO = ("https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage"
               "/default/current/3857/{z}/{x}/{y}.jpeg")
ATTRIBUTION = '&copy; <a href="https://www.swisstopo.admin.ch">swisstopo</a>'
ZOOM_MAX = 19

TITRE_CARTE = "Pedibus &ndash; Chatel-St-Denis"

# Couleur des domiciles selon l'engagement declare.
COULEURS = {
    "Fixe": "#1a7f37",
    "Fixe + occasionnel": "#1a7f37",
    "Occasionnel": "#c77700",
    "Pas accompagnant": "#8a94a0",
}

COULEUR_ECOLE = "#1d4ed8"
COULEUR_CLUSTER = "#55606c"
RAYON_POINT_ACCOMPAGNANT = 7    # pixels
RAYON_POINT_SIMPLE = 5
MARGE_ENVELOPPE_M = 45          # debord du cercle autour d'un groupe

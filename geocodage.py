# -*- coding: utf-8 -*-
"""Adresse -> (lat, lon). Geoportail federal d'abord, Nominatim en repli.

Les resultats sont caches sur disque : une relance du pipeline ne
reinterroge aucune API.
"""

import json
import time

import requests

import config

_cache = None


def _ouvrir_cache():
    global _cache
    if _cache is None:
        if config.CACHE.exists():
            _cache = json.loads(config.CACHE.read_text(encoding="utf-8"))
        else:
            _cache = {}
    return _cache


def fermer_cache():
    if _cache is not None:
        config.CACHE.parent.mkdir(parents=True, exist_ok=True)
        config.CACHE.write_text(
            json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _swisstopo(adresse):
    """api3.geo.admin.ch : nettement meilleur que Nominatim en Suisse."""
    r = requests.get(
        config.API_SWISSTOPO,
        params={"searchText": adresse.replace(", Suisse", "").strip(),
                "type": "locations", "origins": "address,parcel",
                "sr": "4326", "limit": 1},
        timeout=config.TIMEOUT_API)
    r.raise_for_status()
    res = r.json().get("results") or []
    if not res:
        return None
    a = res[0]["attrs"]
    return float(a["lat"]), float(a["lon"]), a.get("label", "")


def _nominatim(adresse):
    r = requests.get(
        config.API_NOMINATIM,
        params={"q": adresse, "format": "json", "limit": 1, "countrycodes": "ch"},
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.TIMEOUT_API)
    r.raise_for_status()
    res = r.json()
    if not res:
        return None
    return float(res[0]["lat"]), float(res[0]["lon"]), res[0].get("display_name", "")


def geocoder(adresse):
    """Renvoie (lat, lon, libelle) ou None. Resultat mis en cache."""
    cache = _ouvrir_cache()
    if adresse in cache:
        v = cache[adresse]
        return tuple(v) if v else None

    trouve = None
    for fonction in (_swisstopo, _nominatim):
        try:
            trouve = fonction(adresse)
            if trouve:
                break
        except Exception as err:
            print(f"    ! {fonction.__name__} : {err}")
        time.sleep(config.PAUSE_API)

    cache[adresse] = list(trouve) if trouve else None
    time.sleep(config.PAUSE_API)
    return trouve


def geocoder_serie(adresses, etiquette="adresses"):
    """Geocode une liste. Renvoie (lats, lons, libelles, echecs)."""
    lats, lons, libelles, echecs = [], [], [], []
    total = len(adresses)
    for i, adresse in enumerate(adresses, 1):
        resultat = geocoder(adresse)
        if resultat:
            lats.append(resultat[0]); lons.append(resultat[1]); libelles.append(resultat[2])
        else:
            lats.append(None); lons.append(None); libelles.append("")
            echecs.append(adresse)
        if i % 20 == 0 or i == total:
            print(f"  {etiquette} : {i}/{total}")
    fermer_cache()
    return lats, lons, libelles, echecs

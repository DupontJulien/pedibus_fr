# -*- coding: utf-8 -*-
"""Address to (lat, lon).

Swiss federal geoportal first, Nominatim as a fallback. Results are cached on
disk, so re-running the pipeline queries no API at all.
"""

import json
import time

import requests

import config

_cache = None


def _open_cache():
    global _cache
    if _cache is None:
        if config.GEOCODE_CACHE.exists():
            _cache = json.loads(config.GEOCODE_CACHE.read_text(encoding="utf-8"))
        else:
            _cache = {}
    return _cache


def save_cache():
    if _cache is not None:
        config.GEOCODE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        config.GEOCODE_CACHE.write_text(
            json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _swisstopo(address):
    """api3.geo.admin.ch: markedly better than Nominatim on Swiss addresses."""
    response = requests.get(
        config.SWISSTOPO_API,
        params={"searchText": address.replace(config.COUNTRY, "").strip(),
                "type": "locations", "origins": "address,parcel",
                "sr": "4326", "limit": 1},
        timeout=config.API_TIMEOUT)
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None
    attrs = results[0]["attrs"]
    return float(attrs["lat"]), float(attrs["lon"]), attrs.get("label", "")


def _nominatim(address):
    response = requests.get(
        config.NOMINATIM_API,
        params={"q": address, "format": "json", "limit": 1, "countrycodes": "ch"},
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.API_TIMEOUT)
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return (float(results[0]["lat"]), float(results[0]["lon"]),
            results[0].get("display_name", ""))


def geocode(address):
    """Return (lat, lon, label) or None. Cached."""
    cache = _open_cache()
    if address in cache:
        hit = cache[address]
        return tuple(hit) if hit else None

    found = None
    for provider in (_swisstopo, _nominatim):
        try:
            found = provider(address)
            if found:
                break
        except Exception as error:
            print(f"    ! {provider.__name__}: {error}")
        time.sleep(config.API_PAUSE)

    cache[address] = list(found) if found else None
    time.sleep(config.API_PAUSE)
    return found


def geocode_series(addresses, on_progress=None):
    """Geocode a list. Returns (lats, lons, labels, failures)."""
    lats, lons, labels, failures = [], [], [], []
    total = len(addresses)
    for index, address in enumerate(addresses, 1):
        found = geocode(address)
        if found:
            lats.append(found[0]); lons.append(found[1]); labels.append(found[2])
        else:
            lats.append(None); lons.append(None); labels.append("")
            failures.append(address)
        if on_progress and (index % 20 == 0 or index == total):
            on_progress(index, total)
    save_cache()
    return lats, lons, labels, failures

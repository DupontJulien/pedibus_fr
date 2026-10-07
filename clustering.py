# -*- coding: utf-8 -*-
"""Group households by real distance.

Default method is complete-linkage agglomerative clustering, which bounds the
*diameter* of each group: every household in a group is within
CLUSTER_DIAMETER_M of every other one. That is what a walking route needs.

DBSCAN is available but chains badly in a dense village: houses 80 m apart form
a continuous chain and the whole place collapses into one group whatever the
radius. Keep it only for comparison.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.metrics import pairwise_distances

import config

EARTH_RADIUS_M = 6_371_000.0


def _distance_matrix(df):
    """Pairwise great-circle distances in metres."""
    coords = np.radians(df[["lat", "lon"]].to_numpy())
    return pairwise_distances(coords, metric="haversine") * EARTH_RADIUS_M


def compute(df, diameter_m=None, min_households=None, method=None,
            interested_only=None):
    """Add 'cluster', 'volunteer' and 'interested'.

    Groups are numbered from 1, largest first. Group 0 collects everything
    left over: homes with no close enough neighbour, and — unless
    interested_only is off — every household that answered "non".
    """
    diameter_m = diameter_m or config.CLUSTER_DIAMETER_M
    min_households = min_households or config.MIN_HOUSEHOLDS
    method = (method or config.CLUSTER_METHOD).lower()
    if interested_only is None:
        interested_only = config.CLUSTER_INTERESTED_ONLY

    df = df.copy()
    df["volunteer"] = df["Engagement"].ne(config.COMMITMENT_NONE)
    df["interested"] = df["Interesse"].astype(str).str.strip().str.lower().eq("oui")

    taking_part = df["interested"] if interested_only else pd.Series(True, index=df.index)
    subset = df[taking_part]

    # One point per home, not per answer: two parents of the same household
    # must not count as two households, nor pull the group's centre twice.
    homes = (subset.groupby("Foyer", sort=False)[["lat", "lon"]]
             .first().reset_index())
    if len(homes) < min_households:
        df["cluster"] = 0
        return df

    if method == "dbscan":
        coords = np.radians(homes[["lat", "lon"]].to_numpy())
        labels = DBSCAN(eps=diameter_m / EARTH_RADIUS_M,
                        min_samples=min_households,
                        metric="haversine").fit_predict(coords)
    else:
        labels = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=diameter_m,
            linkage="complete",
            metric="precomputed",
        ).fit_predict(_distance_matrix(homes))

        # Groups too small to be a route are marked isolated, as DBSCAN does.
        counts = np.bincount(labels)
        labels = np.array([-1 if counts[l] < min_households else l
                           for l in labels])

    # Number the groups from 1, largest first. 0 is reserved for the leftovers.
    order = [l for l, _ in sorted(
        ((l, (labels == l).sum()) for l in set(labels) if l >= 0),
        key=lambda x: -x[1])]
    remap = {old: new for new, old in enumerate(order, start=1)}

    homes["cluster"] = [remap.get(l, 0) for l in labels]
    by_home = dict(zip(homes["Foyer"], homes["cluster"]))
    df["cluster"] = 0
    df.loc[subset.index, "cluster"] = subset["Foyer"].map(by_home).fillna(0).astype(int)
    return df


def spread(df, cluster_id):
    """Largest distance between two homes of a group, in metres."""
    group = df[df.cluster == cluster_id].drop_duplicates(subset="Foyer")
    if len(group) < 2:
        return 0.0
    return float(_distance_matrix(group).max())


def _sort_key(number):
    """Sort '7' before '10' and '10a' right after '10'."""
    digits = "".join(c for c in number if c.isdigit())
    letters = "".join(c for c in number if c.isalpha())
    return (int(digits) if digits else 0, letters)


def label(group):
    """Describe a cluster by its addresses, not just its street names.

    A long street split across several clusters would otherwise give every
    one of them the same label.
    """
    parts = []
    for street in sorted(set(group["Groupe"])):
        rows = group[group["Groupe"] == street]
        numbers = sorted({str(n).strip() for n in rows.get("Numero", [])
                          if str(n).strip() and str(n).strip().lower() != "nan"},
                         key=_sort_key)
        if not numbers:
            parts.append(street)
        elif len(numbers) <= 3:
            parts.append(f"{street} {', '.join(numbers)}")
        else:
            parts.append(f"{street} {numbers[0]}-{numbers[-1]} "
                         f"({len(numbers)} nos)")
    return " \u00b7 ".join(parts)


def summary(df):
    """One row per group, largest first. Group 0 (leftovers) comes last."""
    out = (df[df.cluster > 0]
           .groupby("cluster")
           .agg(households=("Foyer", "nunique"),
                answers=("Nom", "size"),
                volunteers=("volunteer", "sum"),
                fixed=("Engagement",
                       lambda s: s.eq(config.COMMITMENT_FIXED).sum()),
                streets=("Groupe", lambda s: ", ".join(sorted(set(s)))))
           # Numbers are already assigned largest first, so sorting by id
           # gives size order and ascending numbers at the same time.
           .sort_index())
    out["spread_m"] = [round(spread(df, cid)) for cid in out.index]
    out["streets"] = [label(df[df.cluster == cid]) for cid in out.index]

    leftovers = df[df.cluster == 0]
    if len(leftovers):
        out.loc[0] = {
            "households": int(leftovers["Foyer"].nunique()),
            "answers": int(len(leftovers)),
            "volunteers": int(leftovers["volunteer"].sum()),
            "fixed": int(leftovers["Engagement"].eq(config.COMMITMENT_FIXED).sum()),
            "streets": config.LABEL_LEFTOVERS,
            "spread_m": 0,
        }
    return out


def envelopes(df):
    """Centre and radius of each group, for drawing on the map."""
    out = []
    for cluster_id, group in df[df.cluster > 0].groupby("cluster"):
        centre_lat, centre_lon = group["lat"].mean(), group["lon"].mean()
        reach = np.hypot(
            (group["lat"] - centre_lat) * 111_320,
            (group["lon"] - centre_lon) * 111_320 * np.cos(np.radians(centre_lat)),
        ).max()
        out.append({
            "cluster": int(cluster_id),
            "lat": float(centre_lat),
            "lon": float(centre_lon),
            "radius": float(reach + config.CLUSTER_PADDING_M),
            "households": int(group["Foyer"].nunique()),
            "volunteers": int(group["volunteer"].sum()),
            "streets": label(group),
        })
    return sorted(out, key=lambda e: e["cluster"])

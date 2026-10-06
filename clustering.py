# -*- coding: utf-8 -*-
"""Group households by real distance (DBSCAN on haversine)."""

import numpy as np
from sklearn.cluster import DBSCAN

import config

EARTH_RADIUS_M = 6_371_000.0


def compute(df, radius_m=None, min_households=None):
    """Add 'cluster' and 'volunteer' columns. cluster == -1 means isolated."""
    radius_m = radius_m or config.CLUSTER_RADIUS_M
    min_households = min_households or config.MIN_HOUSEHOLDS

    coords = np.radians(df[["lat", "lon"]].to_numpy())
    df = df.copy()
    df["cluster"] = DBSCAN(
        eps=radius_m / EARTH_RADIUS_M,
        min_samples=min_households,
        metric="haversine",
    ).fit_predict(coords)
    df["volunteer"] = df["Engagement"].ne(config.COMMITMENT_NONE)
    return df


def summary(df):
    """One row per group, sorted by number of volunteers."""
    return (df[df.cluster >= 0]
            .groupby("cluster")
            .agg(households=("Nom", "size"),
                 volunteers=("volunteer", "sum"),
                 fixed=("Engagement",
                        lambda s: s.eq(config.COMMITMENT_FIXED).sum()),
                 streets=("Groupe", lambda s: ", ".join(sorted(set(s)))))
            .sort_values(["volunteers", "households"], ascending=False))


def envelopes(df):
    """Centre and radius of each group, for drawing on the map."""
    out = []
    for cluster_id, group in df[df.cluster >= 0].groupby("cluster"):
        centre_lat, centre_lon = group["lat"].mean(), group["lon"].mean()
        spread = np.hypot(
            (group["lat"] - centre_lat) * 111_320,
            (group["lon"] - centre_lon) * 111_320 * np.cos(np.radians(centre_lat)),
        ).max()
        out.append({
            "cluster": int(cluster_id),
            "lat": float(centre_lat),
            "lon": float(centre_lon),
            "radius": float(spread + config.CLUSTER_PADDING_M),
            "households": int(len(group)),
            "volunteers": int(group["volunteer"].sum()),
            "streets": ", ".join(sorted(set(group["Groupe"]))),
        })
    return sorted(out, key=lambda e: -e["volunteers"])

# -*- coding: utf-8 -*-
"""Regroupement des domiciles par distance reelle (DBSCAN haversine)."""

import numpy as np
from sklearn.cluster import DBSCAN

import config

TERRE_M = 6_371_000.0


def calculer(df, rayon_m=None, min_foyers=None):
    """Ajoute les colonnes 'cluster' et 'accompagnant'. -1 = point isole."""
    rayon_m = rayon_m or config.RAYON_CLUSTER_M
    min_foyers = min_foyers or config.MIN_FOYERS

    coords = np.radians(df[["lat", "lon"]].to_numpy())
    df = df.copy()
    df["cluster"] = DBSCAN(
        eps=rayon_m / TERRE_M, min_samples=min_foyers, metric="haversine"
    ).fit_predict(coords)
    df["accompagnant"] = df["Engagement"].ne("Pas accompagnant")
    return df


def recapitulatif(df):
    """Un tableau par groupe, trie par nombre d'accompagnants."""
    return (df[df.cluster >= 0]
            .groupby("cluster")
            .agg(foyers=("Nom", "size"),
                 accompagnants=("accompagnant", "sum"),
                 fixes=("Engagement", lambda s: s.str.startswith("Fixe").sum()),
                 rues=("Groupe", lambda s: ", ".join(sorted(set(s)))))
            .sort_values(["accompagnants", "foyers"], ascending=False))


def enveloppes(df):
    """Centre et rayon de chaque groupe, pour le trace sur la carte."""
    out = []
    for cid, grp in df[df.cluster >= 0].groupby("cluster"):
        clat, clon = grp["lat"].mean(), grp["lon"].mean()
        dist = np.hypot(
            (grp["lat"] - clat) * 111_320,
            (grp["lon"] - clon) * 111_320 * np.cos(np.radians(clat)),
        ).max()
        out.append({
            "cluster": int(cid),
            "lat": float(clat),
            "lon": float(clon),
            "rayon": float(dist + config.MARGE_ENVELOPPE_M),
            "foyers": int(len(grp)),
            "accompagnants": int(grp["accompagnant"].sum()),
            "rues": ", ".join(sorted(set(grp["Groupe"]))),
        })
    return sorted(out, key=lambda e: -e["accompagnants"])

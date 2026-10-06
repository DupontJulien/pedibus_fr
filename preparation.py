# -*- coding: utf-8 -*-
"""Lit le sondage Excel et le normalise : doublons, adresses, rues, engagement."""

import re
import unicodedata

import pandas as pd

import config

def _aplatir(s):
    """Minuscules, sans accents, sans ponctuation."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[,\.]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _rue(adresse):
    """Ne garde que le nom de rue : sans numero, sans NPA, sans prefixe."""
    a = _aplatir(adresse)
    a = re.sub(r"\b1618\b|\b1619\b", " ", a)
    a = re.sub(r"chatel[- ]?st[- ]?denis|chatel[- ]?saint[- ]?denis|"
               r"chatelet st denis|les paccots|paccots|chatel\b", " ", a)
    a = re.sub(r"\d+[a-z]?", " ", a)
    if re.search(r"\bgrand[- ]?rue\b", a):
        return "grand rue"
    a = re.sub(r"\b(rte|route|ch|chemin|impasse|place|rue|"
               r"de|des|du|la|le|l|a|au|aux)\b", " ", a)
    return re.sub(r"\s+", " ", a).strip()


def _groupe(rue):
    for mot in config.HORS_PERIMETRE:
        if mot in rue:
            return config.LIBELLE_HORS
    for cle, libelle in config.RUES.items():
        if cle in rue:
            return libelle
    return rue.title() if rue else config.LIBELLE_SANS_ADRESSE


def _adresse_complete(brute):
    """Ajoute NPA, commune et pays : indispensable pour le geocodage."""
    a = re.sub(r"\s+", " ", str(brute).strip())
    if "1618" not in a and "1619" not in a:
        suffixe = config.NPA_PACCOTS if "paccot" in a.lower() else config.NPA_DEFAUT
        a = a.rstrip(" ,") + suffixe
    return a.rstrip(" ,") + config.PAYS


def _engagement(ligne):
    fixe = "fixe" in str(ligne["engagement"])
    occas = "occasionnel" in str(ligne["engagement"])
    if fixe and occas:
        return "Fixe + occasionnel"
    if fixe:
        return "Fixe"
    if occas:
        return "Occasionnel"
    return "Pas accompagnant"


def charger():
    """Renvoie le sondage normalise, une ligne par foyer."""
    df = pd.read_excel(config.EXCEL)
    if len(df.columns) != len(config.COLONNES):
        raise ValueError(
            f"{len(df.columns)} colonnes dans l'Excel, {len(config.COLONNES)} "
            f"attendues. Ajuste COLONNES dans config.py.\n"
            f"Trouvees : {list(df.columns)}"
        )
    df.columns = config.COLONNES

    avant = len(df)
    cle = df["nom"].map(_aplatir) + "|" + df["adresse"].map(_aplatir)
    df = df[~cle.duplicated()].copy()
    if avant != len(df):
        print(f"  {avant - len(df)} doublon(s) retire(s).")

    df["Nom"] = df["nom"].astype(str).str.strip()
    df["Adresse"] = df["adresse"].map(_adresse_complete)
    df["Groupe"] = df["adresse"].map(lambda a: _groupe(_rue(a)))
    df["Engagement"] = df.apply(_engagement, axis=1)
    df["Interesse"] = df["interet"].astype(str).str.startswith("Oui") \
        .map({True: "Oui", False: "Non"})
    df["Perimetre"] = df.apply(
        lambda r: "Hors (bus)"
        if r["Groupe"] == config.LIBELLE_HORS
        or "paccot" in r["Adresse"].lower()
        or "frasse" in r["Adresse"].lower()
        else "Chatel", axis=1)
    df.loc[df["Perimetre"] == "Hors (bus)", "Groupe"] = config.LIBELLE_HORS
    df["Moments"] = df["moments"].fillna("")
    df["Commentaire"] = df["commentaire"].fillna("")

    cols = ["Nom", "Adresse", "Groupe", "Interesse", "Engagement",
            "Perimetre", "Moments", "Commentaire"]
    return df[cols].sort_values(["Perimetre", "Groupe", "Nom"]).reset_index(drop=True)

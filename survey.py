# -*- coding: utf-8 -*-
"""Read the survey spreadsheet and normalise it.

Handles duplicate responses, incomplete addresses, street-name variants and
the free-text commitment answers.
"""

import re
import unicodedata

import pandas as pd

import config


def _flatten(text):
    """Lowercase, strip accents and punctuation."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[,\.]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _street(address):
    """Keep only the street name: no number, no postcode, no prefix."""
    s = _flatten(address)
    s = re.sub(r"\b1618\b|\b1619\b", " ", s)
    s = re.sub(r"chatel[- ]?st[- ]?denis|chatel[- ]?saint[- ]?denis|"
               r"chatelet st denis|les paccots|paccots|chatel\b", " ", s)
    s = re.sub(r"\d+[a-z]?", " ", s)
    if re.search(r"\bgrand[- ]?rue\b", s):
        return "grand rue"
    s = re.sub(r"\b(rte|route|ch|chemin|impasse|place|rue|"
               r"de|des|du|la|le|l|a|au|aux)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _group(street):
    for keyword in config.OUT_OF_SCOPE:
        if keyword in street:
            return config.GROUP_OUT_OF_SCOPE
    for key, label in config.STREETS.items():
        if key in street:
            return label
    return street.title() if street else config.GROUP_NO_ADDRESS


def _first_address(raw):
    """Some answers list two addresses; keep the first one."""
    text = re.sub(r"\s+", " ", str(raw).strip())
    lowered = text.lower()
    cut = len(text)
    for separator in config.ADDRESS_SEPARATORS:
        found = lowered.find(separator)
        # Ignore a separator before any digit: that is still one address.
        if found > 0 and any(c.isdigit() for c in text[:found]):
            cut = min(cut, found)
    return text[:cut].rstrip(" ,")


def _full_address(raw):
    """Add postcode, town and country, without which geocoding fails."""
    text = _first_address(raw)
    if "1618" not in text and "1619" not in text:
        suffix = (config.POSTCODE_PACCOTS if "paccot" in text.lower()
                  else config.POSTCODE_DEFAULT)
        text = text.rstrip(" ,") + suffix
    return text.rstrip(" ,") + config.COUNTRY


def address_key(address):
    """Normalised address, used to tell one home from another."""
    flat = _flatten(address)
    flat = re.sub(r"[^a-z0-9]+", " ", flat)
    return re.sub(r"\s+", " ", flat).strip()


def _drop_renamed_duplicates(df):
    """Same home, same person written differently.

    At one address, two answers whose name tokens are equal, or where one set
    is contained in the other ("Carolina" vs "Carolina Vieira"), are the same
    person. Different names at one address are left alone: they are a couple
    or two flats, and only the survey's author can tell which.
    """
    keep, seen = [], {}
    for index, row in df.iterrows():
        key = address_key(row["address"])
        tokens = frozenset(_flatten(row["name"]).split())
        duplicate_of = None
        for previous, previous_tokens in seen.get(key, []):
            if tokens <= previous_tokens or previous_tokens <= tokens:
                duplicate_of = previous
                break
        if duplicate_of is None:
            seen.setdefault(key, []).append((index, tokens))
            keep.append(index)
        else:
            # Keep whichever spelling is the fuller one.
            position = keep.index(duplicate_of)
            existing = dict(seen[key])[duplicate_of]
            if len(tokens) > len(existing):
                keep[position] = index
                seen[key] = [(index, tokens) if i == duplicate_of else (i, t)
                             for i, t in seen[key]]
    return df.loc[keep]


def _house_number(raw):
    """Pull the house number out of an address, '' if there is none."""
    text = _first_address(raw)
    text = re.sub(r"\b1618\b|\b1619\b.*", "", text)      # drop postcode and after
    numbers = re.findall(r"\b(\d{1,4}[a-zA-Z]?)\b", text)
    return numbers[-1] if numbers else ""


def _commitment(row):
    answer = str(row["commitment"])
    fixed = "fixe" in answer
    occasional = "occasionnel" in answer
    if fixed and occasional:
        return config.COMMITMENT_BOTH
    if fixed:
        return config.COMMITMENT_FIXED
    if occasional:
        return config.COMMITMENT_OCCASIONAL
    return config.COMMITMENT_NONE


def load():
    """Return the normalised survey, one row per household."""
    df = pd.read_excel(config.SURVEY_FILE)
    if len(df.columns) != len(config.SURVEY_COLUMNS):
        raise ValueError(
            f"{len(df.columns)} columns in the spreadsheet, "
            f"{len(config.SURVEY_COLUMNS)} expected. Adjust SURVEY_COLUMNS "
            f"in config.py.\nFound: {list(df.columns)}"
        )
    df.columns = config.SURVEY_COLUMNS

    before = len(df)
    key = df["name"].map(_flatten) + "|" + df["address"].map(_flatten)
    df = df[~key.duplicated()]
    df = _drop_renamed_duplicates(df).copy()
    duplicates = before - len(df)

    df["Nom"] = df["name"].astype(str).str.strip()
    df["Adresse"] = df["address"].map(_full_address)
    df["Groupe"] = df["address"].map(lambda a: _group(_street(a)))
    df["Numero"] = df["address"].map(_house_number)
    df["Foyer"] = df["address"].map(address_key)
    df["Engagement"] = df.apply(_commitment, axis=1)
    df["Interesse"] = (df["interested"].astype(str).str.startswith("Oui")
                       .map({True: "Oui", False: "Non"}))
    df["Perimetre"] = df.apply(
        lambda r: config.OUT_OF_SCOPE_LABEL
        if r["Groupe"] == config.GROUP_OUT_OF_SCOPE
        or "paccot" in r["Adresse"].lower()
        or "frasse" in r["Adresse"].lower()
        else config.IN_SCOPE, axis=1)
    df.loc[df["Perimetre"] == config.OUT_OF_SCOPE_LABEL,
           "Groupe"] = config.GROUP_OUT_OF_SCOPE
    df["Moments"] = df["time_slots"].fillna("")
    df["Commentaire"] = df["comment"].fillna("")

    columns = ["Nom", "Adresse", "Groupe", "Numero", "Foyer", "Interesse",
               "Engagement", "Perimetre", "Moments", "Commentaire"]
    out = df[columns].sort_values(["Perimetre", "Groupe", "Nom"])
    return out.reset_index(drop=True), duplicates

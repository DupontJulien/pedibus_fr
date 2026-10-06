#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interface en ligne de commande du projet Pedibus.

    python cli.py tout              pipeline complet
    python cli.py preparer          Excel -> table normalisee
    python cli.py geocoder          adresses -> lat / lon
    python cli.py grouper           regroupement par distance
    python cli.py carte             carte HTML
    python cli.py reglages          affiche la configuration courante
    python cli.py --help            aide
"""

import json
from typing import Optional

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

import carte as module_carte
import clusters
import config
import geocodage
import preparation

app = typer.Typer(
    add_completion=False,
    help="Analyse du sondage Pedibus de Chatel-St-Denis.",
    no_args_is_help=True,
)
console = Console()


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------
def _exige(chemin, commande):
    if not chemin.exists():
        console.print(f"[red]Fichier manquant :[/red] {chemin}")
        console.print(f"Lance d'abord [bold]python cli.py {commande}[/bold].")
        raise typer.Exit(1)


def _titre(texte):
    console.print(f"\n[bold]{texte}[/bold]")


def _table_groupes(recap, seuil):
    t = Table(show_header=True, header_style="bold")
    t.add_column("Groupe", overflow="fold")
    t.add_column("Foyers", justify="right")
    t.add_column("Accomp.", justify="right")
    t.add_column("dont fixes", justify="right")
    for cid, r in recap.iterrows():
        pret = r.accompagnants >= seuil
        t.add_row(
            f"[green]{r.rues}[/green]" if pret else r.rues,
            str(r.foyers),
            f"[bold green]{r.accompagnants}[/bold green]" if pret else str(r.accompagnants),
            str(r.fixes),
        )
    return t


# --------------------------------------------------------------------------
# Etape 1
# --------------------------------------------------------------------------
@app.command()
def preparer():
    """Lit l'Excel et le normalise : doublons, adresses, rues, engagement."""
    _titre("1. Preparation")
    if not config.EXCEL.exists():
        console.print(f"[red]Introuvable :[/red] {config.EXCEL}")
        console.print("Depose le .xlsx dans data/ ou corrige EXCEL dans config.py.")
        raise typer.Exit(1)

    config.SORTIE.mkdir(parents=True, exist_ok=True)
    df = preparation.charger()
    df.to_csv(config.FICHIER_NORMALISE, index=False, encoding="utf-8-sig")

    dedans = int((df.Perimetre == "Chatel").sum())
    console.print(f"   {len(df)} foyers, dont [bold]{dedans}[/bold] dans le perimetre "
                  f"({len(df) - dedans} desservis par un bus).")
    console.print(f"   [dim]{config.FICHIER_NORMALISE}[/dim]")


# --------------------------------------------------------------------------
# Etape 2
# --------------------------------------------------------------------------
@app.command()
def geocoder():
    """Transforme les adresses en coordonnees. Les resultats sont caches."""
    _exige(config.FICHIER_NORMALISE, "preparer")
    _titre("2. Geocodage")

    df = pd.read_csv(config.FICHIER_NORMALISE)
    sub = df[df.Perimetre == "Chatel"].copy()
    lats, lons, libelles, echecs = geocodage.geocoder_serie(sub["Adresse"], "foyers")
    sub["lat"], sub["lon"], sub["label_geo"] = lats, lons, libelles

    if echecs:
        console.print(f"   [yellow]{len(echecs)} adresse(s) introuvable(s)[/yellow]")
        for a in echecs:
            console.print(f"     [dim]- {a}[/dim]")

    sub = sub.dropna(subset=["lat", "lon"])
    sub.to_csv(config.FICHIER_GEOCODE, index=False, encoding="utf-8-sig")
    console.print(f"   [bold]{len(sub)}[/bold] foyers positionnes.")

    ecoles = []
    for nom, valeur in config.ECOLES.items():
        if isinstance(valeur, (tuple, list)):
            ecoles.append({"nom": nom, "lat": valeur[0], "lon": valeur[1]})
            continue
        g = geocodage.geocoder(valeur)
        if g:
            ecoles.append({"nom": nom, "lat": g[0], "lon": g[1]})
        else:
            console.print(f"   [yellow]ecole introuvable :[/yellow] {nom} -> "
                          f"mets ses coordonnees dans config.py")
    geocodage.fermer_cache()
    config.FICHIER_ECOLES.write_text(
        json.dumps(ecoles, ensure_ascii=False, indent=1), encoding="utf-8")
    console.print(f"   {len(ecoles)} ecole(s) positionnee(s).")
    console.print(f"   [dim]{config.FICHIER_GEOCODE}[/dim]")


# --------------------------------------------------------------------------
# Etape 3
# --------------------------------------------------------------------------
@app.command()
def grouper(
    rayon: int = typer.Option(None, "--rayon", "-r",
                              help="rayon de regroupement en metres"),
    seuil: int = typer.Option(None, "--seuil", "-s",
                              help="accompagnants necessaires pour une ligne"),
):
    """Regroupe les domiciles par distance reelle et affiche le recapitulatif."""
    _exige(config.FICHIER_GEOCODE, "geocoder")
    rayon = rayon or config.RAYON_CLUSTER_M
    seuil = seuil or config.SEUIL_LIGNE
    _titre(f"3. Regroupement a {rayon} m")

    df = pd.read_csv(config.FICHIER_GEOCODE)
    df = clusters.calculer(df, rayon_m=rayon)
    df.to_csv(config.FICHIER_GROUPES, index=False, encoding="utf-8-sig")

    recap = clusters.recapitulatif(df)
    if len(recap):
        console.print(_table_groupes(recap, seuil))
        pretes = int((recap.accompagnants >= seuil).sum())
        console.print(f"   [bold green]{pretes}[/bold green] groupe(s) avec "
                      f"{seuil} accompagnants ou plus.")
    else:
        console.print("   [yellow]aucun groupe a ce rayon[/yellow]")
    console.print(f"   {int((df.cluster == -1).sum())} point(s) isole(s).")
    console.print(f"   [dim]{config.FICHIER_GROUPES}[/dim]")


# --------------------------------------------------------------------------
# Etape 4
# --------------------------------------------------------------------------
@app.command()
def carte():
    """Genere la carte HTML sur fond swisstopo."""
    _exige(config.FICHIER_GROUPES, "grouper")
    _exige(config.FICHIER_ECOLES, "geocoder")
    _titre("4. Carte")

    df = pd.read_csv(config.FICHIER_GROUPES)
    ecoles = json.loads(config.FICHIER_ECOLES.read_text(encoding="utf-8"))
    chemin = module_carte.generer(df, ecoles, clusters.enveloppes(df),
                                  config.FICHIER_CARTE)
    console.print(f"   [dim]{chemin}[/dim]")
    console.print("   Ouvre ce fichier dans ton navigateur.")


# --------------------------------------------------------------------------
# Pipeline complet
# --------------------------------------------------------------------------
@app.command()
def tout(
    rayon: int = typer.Option(None, "--rayon", "-r",
                              help="rayon de regroupement en metres"),
    seuil: int = typer.Option(None, "--seuil", "-s",
                              help="accompagnants necessaires pour une ligne"),
    sans_carte: bool = typer.Option(False, "--sans-carte",
                                    help="ne pas generer le HTML"),
):
    """Enchaine les quatre etapes."""
    preparer()
    geocoder()
    grouper(rayon=rayon, seuil=seuil)
    if not sans_carte:
        carte()


# --------------------------------------------------------------------------
# Inspection
# --------------------------------------------------------------------------
@app.command()
def reglages():
    """Affiche la configuration courante."""
    t = Table(show_header=True, header_style="bold")
    t.add_column("Reglage")
    t.add_column("Valeur", overflow="fold")
    for cle in ["EXCEL", "RAYON_CLUSTER_M", "MIN_FOYERS", "SEUIL_LIGNE",
                "CERCLES_MIN", "VITESSE_KMH", "ZOOM_MAX"]:
        t.add_row(cle, str(getattr(config, cle)))
    t.add_row("ECOLES", "\n".join(f"{k} : {v}" for k, v in config.ECOLES.items()))
    t.add_row("HORS_PERIMETRE", ", ".join(sorted(config.HORS_PERIMETRE)))
    t.add_row("RUES", f"{len(config.RUES)} entrees")
    console.print(t)
    console.print("[dim]Tout se modifie dans config.py.[/dim]")


if __name__ == "__main__":
    app()

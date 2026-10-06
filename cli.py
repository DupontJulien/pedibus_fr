#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command-line interface.

    python cli.py all          full pipeline
    python cli.py prepare      spreadsheet -> normalised table
    python cli.py geocode      addresses -> lat / lon
    python cli.py cluster      group by distance
    python cli.py map          HTML map
    python cli.py settings     show current configuration
    python cli.py --help
"""

import json

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

import clustering
import config
import geocoding
import mapping
import survey

app = typer.Typer(
    add_completion=False,
    help="Analyse du sondage Pedibus de Chatel-St-Denis.",
    no_args_is_help=True,
)
console = Console()


def _require(path, command):
    if not path.exists():
        console.print(f"[red]Fichier manquant :[/red] {path}")
        console.print(f"Lance d'abord [bold]python cli.py {command}[/bold].")
        raise typer.Exit(1)


def _summary_table(summary, threshold):
    table = Table(show_header=True, header_style="bold")
    table.add_column("Groupe", overflow="fold")
    table.add_column("Foyers", justify="right")
    table.add_column("Accomp.", justify="right")
    table.add_column("dont fixes", justify="right")
    for _, row in summary.iterrows():
        ready = row.volunteers >= threshold
        table.add_row(
            f"[green]{row.streets}[/green]" if ready else row.streets,
            str(row.households),
            f"[bold green]{row.volunteers}[/bold green]" if ready else str(row.volunteers),
            str(row.fixed),
        )
    return table


@app.command()
def prepare():
    """Lit le fichier du sondage et le normalise."""
    console.print("\n[bold]1. Preparation[/bold]")
    if not config.SURVEY_FILE.exists():
        console.print(f"[red]Introuvable :[/red] {config.SURVEY_FILE}")
        console.print("Depose le fichier dans data/ ou corrige SURVEY_FILE "
                      "dans config.py.")
        raise typer.Exit(1)

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, duplicates = survey.load()
    df.to_csv(config.NORMALISED_FILE, index=False, encoding="utf-8-sig")

    if duplicates:
        console.print(f"   {duplicates} doublon(s) retire(s).")
    inside = int((df.Perimetre == config.IN_SCOPE).sum())
    console.print(f"   {len(df)} foyers, dont [bold]{inside}[/bold] dans le "
                  f"perimetre ({len(df) - inside} desservis par un bus).")
    console.print(f"   [dim]{config.NORMALISED_FILE}[/dim]")


@app.command()
def geocode():
    """Transforme les adresses en coordonnees. Les resultats sont caches."""
    _require(config.NORMALISED_FILE, "prepare")
    console.print("\n[bold]2. Geocodage[/bold]")

    df = pd.read_csv(config.NORMALISED_FILE)
    inside = df[df.Perimetre == config.IN_SCOPE].copy()
    lats, lons, labels, failures = geocoding.geocode_series(
        inside["Adresse"],
        on_progress=lambda i, n: console.print(f"   foyers : {i}/{n}", style="dim"))
    inside["lat"], inside["lon"], inside["geo_label"] = lats, lons, labels

    if failures:
        console.print(f"   [yellow]{len(failures)} adresse(s) introuvable(s)[/yellow]")
        for address in failures:
            console.print(f"     [dim]- {address}[/dim]")

    inside = inside.dropna(subset=["lat", "lon"])
    inside.to_csv(config.GEOCODED_FILE, index=False, encoding="utf-8-sig")
    console.print(f"   [bold]{len(inside)}[/bold] foyers positionnes.")

    schools = []
    for name, value in config.SCHOOLS.items():
        if isinstance(value, (tuple, list)):
            schools.append({"nom": name, "lat": value[0], "lon": value[1]})
            continue
        found = geocoding.geocode(value)
        if found:
            schools.append({"nom": name, "lat": found[0], "lon": found[1]})
        else:
            console.print(f"   [yellow]ecole introuvable :[/yellow] {name} "
                          f"-> mets ses coordonnees dans config.py")
    geocoding.save_cache()
    config.SCHOOLS_FILE.write_text(
        json.dumps(schools, ensure_ascii=False, indent=1), encoding="utf-8")
    console.print(f"   {len(schools)} ecole(s) positionnee(s).")
    console.print(f"   [dim]{config.GEOCODED_FILE}[/dim]")


@app.command()
def cluster(
    radius: int = typer.Option(None, "--radius", "-r",
                               help="rayon de regroupement en metres"),
    threshold: int = typer.Option(None, "--threshold", "-t",
                                  help="accompagnants necessaires pour une ligne"),
):
    """Regroupe les domiciles par distance et affiche le recapitulatif."""
    _require(config.GEOCODED_FILE, "geocode")
    radius = radius or config.CLUSTER_RADIUS_M
    threshold = threshold or config.ROUTE_THRESHOLD
    console.print(f"\n[bold]3. Regroupement a {radius} m[/bold]")

    df = pd.read_csv(config.GEOCODED_FILE)
    df = clustering.compute(df, radius_m=radius)
    df.to_csv(config.CLUSTERED_FILE, index=False, encoding="utf-8-sig")

    summary = clustering.summary(df)
    if len(summary):
        console.print(_summary_table(summary, threshold))
        ready = int((summary.volunteers >= threshold).sum())
        console.print(f"   [bold green]{ready}[/bold green] groupe(s) avec "
                      f"{threshold} accompagnants ou plus.")
    else:
        console.print("   [yellow]aucun groupe a ce rayon[/yellow]")
    console.print(f"   {int((df.cluster == -1).sum())} point(s) isole(s).")
    console.print(f"   [dim]{config.CLUSTERED_FILE}[/dim]")


@app.command("map")
def build_map():
    """Genere la carte HTML sur fond swisstopo."""
    _require(config.CLUSTERED_FILE, "cluster")
    _require(config.SCHOOLS_FILE, "geocode")
    console.print("\n[bold]4. Carte[/bold]")

    df = pd.read_csv(config.CLUSTERED_FILE)
    schools = json.loads(config.SCHOOLS_FILE.read_text(encoding="utf-8"))
    path = mapping.build(df, schools, clustering.envelopes(df), config.MAP_FILE)
    console.print(f"   [dim]{path}[/dim]")
    console.print("   Ouvre ce fichier dans ton navigateur.")


@app.command("all")
def run_all(
    radius: int = typer.Option(None, "--radius", "-r",
                               help="rayon de regroupement en metres"),
    threshold: int = typer.Option(None, "--threshold", "-t",
                                  help="accompagnants necessaires pour une ligne"),
    no_map: bool = typer.Option(False, "--no-map", help="ne pas generer le HTML"),
):
    """Enchaine les quatre etapes."""
    prepare()
    geocode()
    cluster(radius=radius, threshold=threshold)
    if not no_map:
        build_map()


@app.command()
def settings():
    """Affiche la configuration courante."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Reglage")
    table.add_column("Valeur", overflow="fold")
    for key in ["SURVEY_FILE", "CLUSTER_RADIUS_M", "MIN_HOUSEHOLDS",
                "ROUTE_THRESHOLD", "WALK_CIRCLES_MIN", "WALK_SPEED_KMH"]:
        table.add_row(key, str(getattr(config, key)))
    table.add_row("SCHOOLS", "\n".join(f"{k} : {v}" for k, v in config.SCHOOLS.items()))
    table.add_row("OUT_OF_SCOPE", ", ".join(sorted(config.OUT_OF_SCOPE)))
    table.add_row("STREETS", f"{len(config.STREETS)} entrees")
    console.print(table)
    console.print("[dim]Tout se modifie dans config.py.[/dim]")


if __name__ == "__main__":
    app()

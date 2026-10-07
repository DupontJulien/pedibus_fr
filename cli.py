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

import numpy as np
import pandas as pd
import typer
from sklearn.metrics import pairwise_distances
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
    table.add_column("N", justify="right")
    table.add_column("Groupe", overflow="fold")
    table.add_column("Foyers", justify="right")
    table.add_column("Accomp.", justify="right")
    table.add_column("dont fixes", justify="right")
    table.add_column("Etendue", justify="right")
    for cluster_id, row in summary.iterrows():
        leftovers = cluster_id == 0
        ready = row.volunteers >= threshold and not leftovers
        if leftovers:
            table.add_row(*(f"[dim]{v}[/dim]" for v in
                            ("0", row.streets, row.households, row.volunteers,
                             row.fixed, "")))
            continue
        table.add_row(
            str(cluster_id),
            f"[green]{row.streets}[/green]" if ready else row.streets,
            str(row.households),
            f"[bold green]{row.volunteers}[/bold green]" if ready else str(row.volunteers),
            str(row.fixed),
            f"{row.spread_m} m",
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
    diameter: int = typer.Option(None, "--diameter", "-d",
                                 help="etendue maximale d'un groupe, en metres"),
    threshold: int = typer.Option(None, "--threshold", "-t",
                                  help="accompagnants necessaires pour une ligne"),
    method: str = typer.Option(None, "--method", "-m",
                               help="complete (defaut) ou dbscan"),
):
    """Regroupe les domiciles par distance et affiche le recapitulatif."""
    _require(config.GEOCODED_FILE, "geocode")
    diameter = diameter or config.CLUSTER_DIAMETER_M
    threshold = threshold or config.ROUTE_THRESHOLD
    method = method or config.CLUSTER_METHOD
    console.print(f"\n[bold]3. Regroupement, groupes de {diameter} m "
                  f"au maximum[/bold]")

    df = pd.read_csv(config.GEOCODED_FILE)
    df = clustering.compute(df, diameter_m=diameter, method=method)
    df.to_csv(config.CLUSTERED_FILE, index=False, encoding="utf-8-sig")

    summary = clustering.summary(df)
    if len(summary):
        console.print(_summary_table(summary, threshold))
        ready = int((summary.drop(index=0, errors="ignore").volunteers
                     >= threshold).sum())
        console.print(f"   [bold green]{ready}[/bold green] groupe(s) avec "
                      f"{threshold} accompagnants ou plus.")
    else:
        console.print("   [yellow]aucun groupe a ce rayon[/yellow]")
    excluded = int((~df["interested"]).sum()) if config.CLUSTER_INTERESTED_ONLY else 0
    detail = f", dont {excluded} non interesse(s)" if excluded else ""
    console.print(f"   Groupe 0 : {int((df.cluster == 0).sum())} reponse(s) "
                  f"sans groupe{detail}.")
    console.print(f"   [dim]{config.CLUSTERED_FILE}[/dim]")


@app.command("map")
def build_map():
    """Genere la carte HTML sur fond swisstopo."""
    _require(config.CLUSTERED_FILE, "cluster")
    _require(config.SCHOOLS_FILE, "geocode")
    console.print("\n[bold]4. Carte[/bold]")

    df = pd.read_csv(config.CLUSTERED_FILE)
    schools = json.loads(config.SCHOOLS_FILE.read_text(encoding="utf-8"))
    recap = clustering.summary(df)
    leftovers = None
    if 0 in recap.index:
        row = recap.loc[0]
        leftovers = {"cluster": 0, "streets": row.streets,
                     "households": int(row.households),
                     "volunteers": int(row.volunteers)}
    path = mapping.build(df, schools, clustering.envelopes(df), config.MAP_FILE,
                         leftovers=leftovers)
    console.print(f"   [dim]{path}[/dim]")
    console.print("   Ouvre ce fichier dans ton navigateur.")


@app.command("all")
def run_all(
    diameter: int = typer.Option(None, "--diameter", "-d",
                                 help="etendue maximale d'un groupe, en metres"),
    threshold: int = typer.Option(None, "--threshold", "-t",
                                  help="accompagnants necessaires pour une ligne"),
    no_map: bool = typer.Option(False, "--no-map", help="ne pas generer le HTML"),
):
    """Enchaine les quatre etapes."""
    prepare()
    geocode()
    cluster(diameter=diameter, threshold=threshold, method=None)
    if not no_map:
        build_map()


@app.command()
def check():
    """Controle le geocodage : points suspects, distances entre rues, etendues."""
    _require(config.GEOCODED_FILE, "geocode")
    console.print("\n[bold]Controle du geocodage[/bold]")

    df = pd.read_csv(config.GEOCODED_FILE)

    # 1. Coordonnees identiques pour des adresses DIFFERENTES : signe d'un
    #    repli du geocodeur sur le centre d'une rue ou de la commune.
    distinct = df.groupby(["lat", "lon"]).Foyer.nunique()
    suspects = distinct[distinct > 1]
    if len(suspects):
        console.print(f"\n[yellow]{len(suspects)} coordonnee(s) partagee(s) par "
                      f"des adresses differentes[/yellow] — probablement un repli "
                      f"du geocodeur sur le centre de la rue ou de la commune :")
        for (lat, lon), count in suspects.items():
            rows = df[(df.lat == lat) & (df.lon == lon)]
            adresses = sorted(set(rows.Adresse.str[:40]))
            console.print(f"   [dim]{lat:.5f}, {lon:.5f}[/dim] — {count} adresses : "
                          f"{' | '.join(adresses)}")
    else:
        console.print("   Aucune coordonnee suspecte.")

    # 2. Adresses partagees par plusieurs reponses : couple ou immeuble ?
    shared = df.groupby("Foyer").filter(lambda g: len(g) > 1)
    if len(shared):
        console.print(f"\n[bold]Adresses partagees par plusieurs reponses[/bold] "
                      f"— comptees comme un seul foyer")
        for _, group in shared.groupby("Foyer"):
            noms = " / ".join(group.Nom)
            accs = int(group.Engagement.ne(config.COMMITMENT_NONE).sum())
            console.print(f"   {group.Adresse.iloc[0][:44]:46s} {noms}"
                          f"  [dim]({accs} accompagnant(s))[/dim]")
        console.print("   [dim]Un couple ou deux familles d'un meme immeuble ? "
                      "Dans le doute, un seul foyer est compte : cela sous-estime "
                      "la demande plutot que de la gonfler.[/dim]")

    # 3. Distance entre les centres de chaque rue.
    centres = df.groupby("Groupe")[["lat", "lon"]].mean()
    console.print(f"\n[bold]Distances entre rues[/bold] (centre a centre)")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Rue")
    table.add_column("Rue la plus proche")
    table.add_column("Distance", justify="right")
    coords = np.radians(centres.to_numpy())
    matrix = pairwise_distances(coords, metric="haversine") * 6_371_000
    np.fill_diagonal(matrix, np.inf)
    for i, name in enumerate(centres.index):
        j = int(matrix[i].argmin())
        table.add_row(name, centres.index[j], f"{matrix[i][j]:.0f} m")
    console.print(table)

    # 4. Etalement de chaque rue : une rue tres etalee se repartira
    #    legitimement sur plusieurs groupes.
    console.print("\n[bold]Rues les plus etalees[/bold]")
    spreads = []
    for name, group in df.groupby("Groupe"):
        if len(group) < 2:
            continue
        c = np.radians(group[["lat", "lon"]].to_numpy())
        spreads.append((name, len(group),
                        (pairwise_distances(c, metric="haversine") * 6_371_000).max()))
    for name, count, spread in sorted(spreads, key=lambda x: -x[2])[:8]:
        flag = "  [yellow]<- se repartira sur plusieurs groupes[/yellow]" \
            if spread > config.CLUSTER_DIAMETER_M else ""
        console.print(f"   {name:24s} {count:2d} foyers   {spread:5.0f} m{flag}")


@app.command()
def settings():
    """Affiche la configuration courante."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Reglage")
    table.add_column("Valeur", overflow="fold")
    for key in ["SURVEY_FILE", "CLUSTER_METHOD", "CLUSTER_DIAMETER_M", "MIN_HOUSEHOLDS",
                "ROUTE_THRESHOLD", "WALK_CIRCLES_MIN", "WALK_SPEED_KMH"]:
        table.add_row(key, str(getattr(config, key)))
    table.add_row("SCHOOLS", "\n".join(f"{k} : {v}" for k, v in config.SCHOOLS.items()))
    table.add_row("OUT_OF_SCOPE", ", ".join(sorted(config.OUT_OF_SCOPE)))
    table.add_row("STREETS", f"{len(config.STREETS)} entrees")
    console.print(table)
    console.print("[dim]Tout se modifie dans config.py.[/dim]")


if __name__ == "__main__":
    app()

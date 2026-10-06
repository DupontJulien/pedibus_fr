# Pédibus — Châtel-St-Denis

Analyse du sondage d'intérêt des parents : regroupement des domiciles par
distance réelle et carte interactive sur fond swisstopo, pour identifier les
lignes Pédibus réalisables.

## Installation

```bash
conda env create -f environment.yml
conda activate pedibus
```

Mettre à jour l'environnement plus tard :

```bash
conda env update -f environment.yml --prune
```

## Utilisation

Déposer le fichier du sondage dans `data/` sous le nom
`Lignes_Pedibus_-_Sondage_d_interet_aupres_des_parents.xlsx`
(ou corriger `EXCEL` dans `config.py`), puis :

```bash
python cli.py tout
```

Les quatre étapes peuvent aussi se lancer séparément, dans l'ordre. Chacune lit
le fichier produit par la précédente, donc on peut en relancer une seule après
avoir modifié un réglage :

```bash
python cli.py preparer              # Excel → table normalisée
python cli.py geocoder              # adresses → lat/lon (met en cache)
python cli.py grouper               # regroupement par distance
python cli.py carte                 # carte HTML
```

Options utiles :

```bash
python cli.py grouper --rayon 400   # groupes plus larges (quartiers)
python cli.py grouper --seuil 3     # une ligne tient avec 3 accompagnants
python cli.py tout --sans-carte     # tout sauf le HTML
python cli.py reglages              # affiche la configuration courante
python cli.py --help                # aide
```

Le géocodage est l'étape lente (environ une minute la première fois) mais ses
résultats sont mis en cache : les relances suivantes sont instantanées. En
pratique, après un premier `tout`, on ne relance plus que `grouper` et `carte`
pour comparer des réglages.

## Ce que ça produit

Dans `sortie/`, numéroté dans l'ordre des étapes :

| Fichier | Contenu |
|---|---|
| `1_sondage_normalise.csv` | le sondage nettoyé : doublons retirés, adresses complétées, rues regroupées, engagement en quatre valeurs |
| `2_foyers_geocodes.csv` | les foyers du périmètre avec `lat` et `lon` |
| `2_ecoles.json` | les coordonnées des trois écoles |
| `3_groupes.csv` | les mêmes foyers avec leur `cluster` |
| `4_carte.html` | la carte, à ouvrir dans un navigateur |
| `.cache_geocode.json` | cache du géocodage — à conserver |

La carte superpose quatre couches activables séparément : les domiciles
colorés selon l'engagement, les groupes de proximité, les cercles de temps de
marche autour des écoles, et les écoles. Un sélecteur bascule entre la carte
swisstopo et la vue aérienne. Le panneau de droite classe les groupes par
nombre d'accompagnants, la seule colonne qui décide si une ligne est faisable.

## Réglages

Tout se règle dans `config.py` — aucun paramètre n'est codé en dur ailleurs.
Le fichier est découpé en huit sections.

| Section | Ce qu'on y règle |
|---|---|
| 1. Entrée | chemin du fichier Excel, noms des colonnes |
| 2. Sorties | noms des trois fichiers produits et du cache |
| 3. Regroupement | `RAYON_CLUSTER_M`, `MIN_FOYERS`, `SEUIL_LIGNE` |
| 4. Écoles | adresses ou coordonnées, cercles de marche, vitesse |
| 5. Périmètre | secteurs desservis par un bus, exclus de l'analyse |
| 6. Noms de rues | table `RUES` qui rapproche les orthographes |
| 7. Géocodage | URL des API, délai d'attente, pause entre appels |
| 8. Carte | tuiles, couleurs, taille des points, titre |

Les quatre à connaître :

- `RAYON_CLUSTER_M` — 250 m donne des voisinages de type « même bout de rue »,
  400 m des quartiers. Comparer les deux est instructif.
- `SEUIL_LIGNE` — nombre d'accompagnants à partir duquel une ligne peut tenir
  une semaine. Fixé à 4 par défaut ; à ajuster selon ce que dit Pédibus
  Fribourg. Il pilote à la fois le comptage affiché et la mise en évidence
  dans le tableau de la carte.
- `ECOLES` — les adresses sont approximatives. Les corriger, ou mieux,
  remplacer par un tuple `(46.52xx, 6.90xx)` relevé sur
  [map.geo.admin.ch](https://map.geo.admin.ch).
- `RUES` — à compléter si un sondage ultérieur fait apparaître une rue que la
  table ne connaît pas. Sans entrée correspondante, l'adresse est quand même
  géocodée, mais son libellé de groupe sera brut.

## Architecture

```
cli.py           interface en ligne de commande (Typer)
config.py        réglages — le seul fichier à modifier au quotidien
preparation.py   Excel → table normalisée (doublons, adresses, rues, engagement)
geocodage.py     adresse → lat/lon (geo.admin.ch, Nominatim en repli, cache disque)
clusters.py      DBSCAN haversine + récapitulatif + enveloppes
carte.py         gabarit HTML (Leaflet + tuiles swisstopo)
```

Les quatre modules métier ne dépendent pas de `cli.py` : ils sont importables
directement depuis un notebook si besoin.

## Lecture des résultats

Dans le récapitulatif, `cluster = -1` n'est pas un groupe : c'est l'ensemble
des domiciles sans voisin dans le rayon.

La colonne qui compte est `accompagnants`. Quatre et plus permettent de couvrir
une semaine, deux ou trois demandent de fusionner avec un groupe voisin, un ou
zéro ne mène à rien même quand la demande est forte. Un groupe avec beaucoup de
foyers et peu d'accompagnants est un secteur où il faut recruter, pas ouvrir
une ligne.

## Notes

Les géocodeurs utilisés sont gratuits et sans clé. Le cache évite de les
solliciter inutilement — le conserver.

Le fichier contient les noms et adresses du domicile de familles avec enfants.
Garder les sorties hors de tout service tiers et hors d'un dépôt public.


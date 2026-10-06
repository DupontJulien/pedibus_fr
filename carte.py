# -*- coding: utf-8 -*-
"""Genere une carte HTML autonome : fond swisstopo, domiciles, groupes, ecoles."""

import json

import pandas as pd

import config

GABARIT = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITRE__</title>
<link rel="stylesheet" href="__LEAFLET_CSS__">
<script src="__LEAFLET_JS__"></script>
<style>
  html,body{margin:0;height:100%;font:14px/1.45 system-ui,-apple-system,sans-serif}
  #map{position:absolute;inset:0}
  .panneau{position:absolute;top:12px;right:12px;z-index:1000;background:#fff;
    border:1px solid #d6dae0;border-radius:6px;padding:12px 14px;max-width:278px;
    box-shadow:0 2px 10px rgba(0,0,0,.14);max-height:88vh;overflow:auto}
  .panneau h1{font:600 14px/1.3 Georgia,serif;margin:0 0 9px}
  .cle{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}
  .pastille{width:12px;height:12px;border-radius:50%;border:1.5px solid #fff;
    box-shadow:0 0 0 1px rgba(0,0,0,.35);flex:none}
  .note{font-size:12px;color:#5d6773;margin:10px 0 0;line-height:1.45}
  table{border-collapse:collapse;font-size:12.5px;margin-top:10px;width:100%}
  th,td{text-align:left;padding:3px 6px 3px 0;border-bottom:1px solid #eceff2}
  th{font-weight:600;color:#5d6773}
  td.n{text-align:right;font-variant-numeric:tabular-nums}
  tr.fort td{background:#f0f7f1}
  .pop b{font-size:13px}.pop span{color:#5d6773}
</style>
</head>
<body>
<div id="map"></div>
<div class="panneau">
  <h1>__TITRE__</h1>
  <div class="cle"><span class="pastille" style="background:__C_FIXE__"></span>Accompagnant fixe</div>
  <div class="cle"><span class="pastille" style="background:__C_OCCAS__"></span>Accompagnant occasionnel</div>
  <div class="cle"><span class="pastille" style="background:__C_SIMPLE__"></span>Sans accompagner</div>
  <div class="cle"><span class="pastille" style="background:__C_ECOLE__;border-radius:2px"></span>Ecole</div>
  <table id="recap"></table>
  <p class="note">Lignes vertes : __SEUIL__ accompagnants ou plus, de quoi tenir une
  semaine. Cercles bleus : __CERCLES_TXT__ min de marche a vol d'oiseau
  (__VITESSE__ km/h) &mdash; le trajet reel est plus long. Zones grisees :
  domiciles distants de moins de __RAYON__ m.</p>
</div>
<script>
const POINTS=__POINTS__, ECOLES=__ECOLES__, CLUSTERS=__CLUSTERS__,
      CERCLES=__CERCLES__, COULEURS=__COULEURS__;

const carte = L.map('map');
const fondCarte = L.tileLayer('__TUILE_CARTE__',
 {maxZoom:__ZOOM_MAX__, attribution:'__ATTRIBUTION__'});
const fondPhoto = L.tileLayer('__TUILE_PHOTO__',
 {maxZoom:__ZOOM_MAX__, attribution:'__ATTRIBUTION__'});
fondCarte.addTo(carte);

const gClusters=L.layerGroup().addTo(carte), gMarche=L.layerGroup().addTo(carte),
      gFoyers=L.layerGroup().addTo(carte),   gEcoles=L.layerGroup().addTo(carte);

CLUSTERS.forEach(c=>{
  L.circle([c.lat,c.lon],{radius:c.rayon,color:'__C_CLUSTER__',weight:1,
    fillColor:'__C_CLUSTER__',fillOpacity:.07,dashArray:'4,4'})
   .bindTooltip(`Groupe ${c.cluster} &mdash; ${c.foyers} foyers, `+
                `<b>${c.accompagnants} accompagnant(s)</b><br>${c.rues}`)
   .addTo(gClusters);
});

ECOLES.forEach(e=>{
  CERCLES.forEach(c=>{
    L.circle([e.lat,e.lon],{radius:c.rayon,color:'__C_ECOLE__',weight:1,opacity:.45,
      fill:false,dashArray:'2,5'})
     .bindTooltip(`${c.min} min &ndash; ${e.nom}`).addTo(gMarche);
  });
  L.marker([e.lat,e.lon],{icon:L.divIcon({className:'',iconSize:[16,16],
    html:'<div style="width:14px;height:14px;background:__C_ECOLE__;border:2px solid #fff;'+
         'border-radius:3px;box-shadow:0 0 0 1px __C_ECOLE__"></div>'})})
   .bindPopup(`<b>${e.nom}</b>`).addTo(gEcoles);
});

POINTS.forEach(p=>{
  const c=COULEURS[p.engagement]||'#8a94a0', fort=p.engagement!=='Pas accompagnant';
  L.circleMarker([p.lat,p.lon],{radius:fort?__R_ACC__:__R_SIMPLE__,color:'#fff',weight:1.5,
    fillColor:c,fillOpacity:.95})
   .bindPopup(`<div class="pop"><b>${p.nom}</b><br><span>${p.adresse}</span><br><br>`+
     `${p.engagement}`+
     (p.cluster>=0?`<br><span>Groupe ${p.cluster}</span>`:'<br><span>Isole</span>')+
     (p.moments?`<br><br><span>${p.moments}</span>`:'')+`</div>`)
   .addTo(gFoyers);
});

document.getElementById('recap').innerHTML =
 '<tr><th>Groupe</th><th class="n">Foyers</th><th class="n">Accomp.</th></tr>'+
 CLUSTERS.map(c=>`<tr class="${c.accompagnants>=__SEUIL__?'fort':''}"><td>${c.rues}</td>`+
   `<td class="n">${c.foyers}</td><td class="n"><b>${c.accompagnants}</b></td></tr>`).join('');

L.control.layers(
 {'Carte swisstopo':fondCarte,'Vue aerienne':fondPhoto},
 {'Domiciles':gFoyers,'Groupes':gClusters,'Temps de marche':gMarche,'Ecoles':gEcoles},
 {collapsed:false}).addTo(carte);

carte.fitBounds(L.featureGroup([gFoyers,gEcoles]).getBounds().pad(.12));
</script>
</body>
</html>
"""


def generer(df, ecoles, enveloppes, chemin):
    points = [{
        "nom": str(r["Nom"]),
        "adresse": str(r["Adresse"]).replace(", Suisse", ""),
        "groupe": str(r["Groupe"]),
        "engagement": str(r["Engagement"]),
        "moments": "" if pd.isna(r.get("Moments")) else str(r["Moments"]),
        "cluster": int(r["cluster"]),
        "lat": float(r["lat"]), "lon": float(r["lon"]),
    } for _, r in df.iterrows()]

    cercles = [{"min": m, "rayon": config.VITESSE_KMH * 1000 / 60 * m}
               for m in config.CERCLES_MIN]

    html = (GABARIT
            .replace("__POINTS__", json.dumps(points, ensure_ascii=False))
            .replace("__ECOLES__", json.dumps(ecoles, ensure_ascii=False))
            .replace("__CLUSTERS__", json.dumps(enveloppes, ensure_ascii=False))
            .replace("__CERCLES__", json.dumps(cercles))
            .replace("__COULEURS__", json.dumps(config.COULEURS, ensure_ascii=False))
            .replace("__CERCLES_TXT__", " / ".join(str(m) for m in config.CERCLES_MIN))
            .replace("__VITESSE__", str(config.VITESSE_KMH))
            .replace("__RAYON__", str(config.RAYON_CLUSTER_M))
            .replace("__TITRE__", config.TITRE_CARTE)
            .replace("__LEAFLET_CSS__", config.LEAFLET_CSS)
            .replace("__LEAFLET_JS__", config.LEAFLET_JS)
            .replace("__TUILE_CARTE__", config.TUILE_CARTE)
            .replace("__TUILE_PHOTO__", config.TUILE_PHOTO)
            .replace("__ATTRIBUTION__", config.ATTRIBUTION)
            .replace("__ZOOM_MAX__", str(config.ZOOM_MAX))
            .replace("__SEUIL__", str(config.SEUIL_LIGNE))
            .replace("__C_FIXE__", config.COULEURS["Fixe"])
            .replace("__C_OCCAS__", config.COULEURS["Occasionnel"])
            .replace("__C_SIMPLE__", config.COULEURS["Pas accompagnant"])
            .replace("__C_ECOLE__", config.COULEUR_ECOLE)
            .replace("__C_CLUSTER__", config.COULEUR_CLUSTER)
            .replace("__R_ACC__", str(config.RAYON_POINT_ACCOMPAGNANT))
            .replace("__R_SIMPLE__", str(config.RAYON_POINT_SIMPLE)))

    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(html, encoding="utf-8")
    return chemin

# -*- coding: utf-8 -*-
"""Build a self-contained HTML map: swisstopo tiles, households, groups, schools.

All visible text comes from the French strings in config, section 9.
"""

import json

import pandas as pd

import config

TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<link rel="stylesheet" href="{leaflet_css}">
<script src="{leaflet_js}"></script>
<style>
  html,body{{margin:0;height:100%;font:14px/1.45 system-ui,-apple-system,sans-serif}}
  #map{{position:absolute;inset:0}}
  .panel{{position:absolute;top:12px;right:12px;z-index:1000;background:#fff;
    border:1px solid #d6dae0;border-radius:6px;padding:12px 14px;max-width:278px;
    box-shadow:0 2px 10px rgba(0,0,0,.14);max-height:88vh;overflow:auto}}
  .panel h1{{font:600 14px/1.3 Georgia,serif;margin:0 0 9px}}
  .key{{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}}
  .dot{{width:12px;height:12px;border-radius:50%;border:1.5px solid #fff;
    box-shadow:0 0 0 1px rgba(0,0,0,.35);flex:none}}
  .note{{font-size:12px;color:#5d6773;margin:10px 0 0;line-height:1.45}}
  table{{border-collapse:collapse;font-size:12.5px;margin-top:10px;width:100%}}
  th,td{{text-align:left;padding:3px 6px 3px 0;border-bottom:1px solid #eceff2}}
  th{{font-weight:600;color:#5d6773}}
  td.n{{text-align:right;font-variant-numeric:tabular-nums}}
  tr.ready td{{background:#f0f7f1}}
  .pop b{{font-size:13px}}.pop span{{color:#5d6773}}
</style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <h1>{title}</h1>
  <div class="key"><span class="dot" style="background:{color_fixed}"></span>{legend_fixed}</div>
  <div class="key"><span class="dot" style="background:{color_occasional}"></span>{legend_occasional}</div>
  <div class="key"><span class="dot" style="background:{color_plain}"></span>{legend_plain}</div>
  <div class="key"><span class="dot" style="background:{color_school};border-radius:2px"></span>{legend_school}</div>
  <table id="summary"></table>
  <p class="note">Lignes vertes : {threshold} accompagnants ou plus, de quoi tenir
  une semaine. Cercles bleus : {circles_text} min de marche a vol d'oiseau
  ({speed} km/h) &mdash; le trajet reel est plus long. Zones grisees :
  domiciles distants de moins de {radius} m.</p>
</div>
<script>
const HOUSEHOLDS={households}, SCHOOLS={schools}, CLUSTERS={clusters},
      RINGS={rings}, COLORS={colors}, THRESHOLD={threshold};

const map = L.map('map');
const baseMap = L.tileLayer('{tiles_map}',
 {{maxZoom:{max_zoom}, attribution:'{attribution}'}});
const baseAerial = L.tileLayer('{tiles_aerial}',
 {{maxZoom:{max_zoom}, attribution:'{attribution}'}});
baseMap.addTo(map);

const layerClusters=L.layerGroup().addTo(map), layerRings=L.layerGroup().addTo(map),
      layerHouseholds=L.layerGroup().addTo(map), layerSchools=L.layerGroup().addTo(map);

CLUSTERS.forEach(c=>{{
  L.circle([c.lat,c.lon],{{radius:c.radius,color:'{color_cluster}',weight:1,
    fillColor:'{color_cluster}',fillOpacity:.07,dashArray:'4,4'}})
   .bindTooltip(`Groupe ${{c.cluster}} &mdash; ${{c.households}} foyers, `+
                `<b>${{c.volunteers}} accompagnant(s)</b><br>${{c.streets}}`)
   .addTo(layerClusters);
}});

SCHOOLS.forEach(s=>{{
  RINGS.forEach(r=>{{
    L.circle([s.lat,s.lon],{{radius:r.radius,color:'{color_school}',weight:1,
      opacity:.45,fill:false,dashArray:'2,5'}})
     .bindTooltip(`${{r.minutes}} min &ndash; ${{s.nom}}`).addTo(layerRings);
  }});
  L.marker([s.lat,s.lon],{{icon:L.divIcon({{className:'',iconSize:[16,16],
    html:'<div style="width:14px;height:14px;background:{color_school};'+
         'border:2px solid #fff;border-radius:3px;'+
         'box-shadow:0 0 0 1px {color_school}"></div>'}})}})
   .bindPopup(`<b>${{s.nom}}</b>`).addTo(layerSchools);
}});

HOUSEHOLDS.forEach(h=>{{
  const color=COLORS[h.commitment]||'{color_plain}',
        isVolunteer=h.commitment!=='{commitment_none}';
  L.circleMarker([h.lat,h.lon],{{radius:isVolunteer?{radius_volunteer}:{radius_plain},
    color:'#fff',weight:1.5,fillColor:color,fillOpacity:.95}})
   .bindPopup(`<div class="pop"><b>${{h.name}}</b><br><span>${{h.address}}</span>`+
     `<br><br>${{h.commitment}}`+
     (h.cluster>=0?`<br><span>Groupe ${{h.cluster}}</span>`:`<br><span>{isolated}</span>`)+
     (h.slots?`<br><br><span>${{h.slots}}</span>`:'')+`</div>`)
   .addTo(layerHouseholds);
}});

document.getElementById('summary').innerHTML =
 '<tr><th>{col_group}</th><th class="n">{col_households}</th>'+
 '<th class="n">{col_volunteers}</th></tr>'+
 CLUSTERS.map(c=>`<tr class="${{c.volunteers>=THRESHOLD?'ready':''}}">`+
   `<td>${{c.streets}}</td><td class="n">${{c.households}}</td>`+
   `<td class="n"><b>${{c.volunteers}}</b></td></tr>`).join('');

L.control.layers(
 {{'{layer_map}':baseMap,'{layer_aerial}':baseAerial}},
 {{'{layer_households}':layerHouseholds,'{layer_clusters}':layerClusters,
   '{layer_walk}':layerRings,'{layer_schools}':layerSchools}},
 {{collapsed:false}}).addTo(map);

map.fitBounds(L.featureGroup([layerHouseholds,layerSchools]).getBounds().pad(.12));
</script>
</body>
</html>
"""


def build(df, schools, envelopes, path):
    """Write the HTML map and return its path."""
    households = [{
        "name": str(row["Nom"]),
        "address": str(row["Adresse"]).replace(config.COUNTRY, ""),
        "group": str(row["Groupe"]),
        "commitment": str(row["Engagement"]),
        "slots": "" if pd.isna(row.get("Moments")) else str(row["Moments"]),
        "cluster": int(row["cluster"]),
        "lat": float(row["lat"]), "lon": float(row["lon"]),
    } for _, row in df.iterrows()]

    rings = [{"minutes": m, "radius": config.WALK_SPEED_KMH * 1000 / 60 * m}
             for m in config.WALK_CIRCLES_MIN]

    html = TEMPLATE.format(
        page_title=config.MAP_PAGE_TITLE,
        title=config.MAP_TITLE,
        leaflet_css=config.LEAFLET_CSS,
        leaflet_js=config.LEAFLET_JS,
        tiles_map=config.TILES_MAP,
        tiles_aerial=config.TILES_AERIAL,
        attribution=config.ATTRIBUTION,
        max_zoom=config.MAX_ZOOM,
        households=json.dumps(households, ensure_ascii=False),
        schools=json.dumps(schools, ensure_ascii=False),
        clusters=json.dumps(envelopes, ensure_ascii=False),
        rings=json.dumps(rings),
        colors=json.dumps(config.COLORS, ensure_ascii=False),
        color_fixed=config.COLORS[config.COMMITMENT_FIXED],
        color_occasional=config.COLORS[config.COMMITMENT_OCCASIONAL],
        color_plain=config.COLORS[config.COMMITMENT_NONE],
        color_school=config.COLOR_SCHOOL,
        color_cluster=config.COLOR_CLUSTER,
        commitment_none=config.COMMITMENT_NONE,
        radius_volunteer=config.MARKER_RADIUS_VOLUNTEER,
        radius_plain=config.MARKER_RADIUS_PLAIN,
        threshold=config.ROUTE_THRESHOLD,
        radius=config.CLUSTER_RADIUS_M,
        circles_text=" / ".join(str(m) for m in config.WALK_CIRCLES_MIN),
        speed=config.WALK_SPEED_KMH,
        legend_fixed=config.MAP_LEGEND_FIXED,
        legend_occasional=config.MAP_LEGEND_OCCASIONAL,
        legend_plain=config.MAP_LEGEND_PLAIN,
        legend_school=config.MAP_LEGEND_SCHOOL,
        layer_map=config.MAP_LAYER_MAP,
        layer_aerial=config.MAP_LAYER_AERIAL,
        layer_households=config.MAP_LAYER_HOUSEHOLDS,
        layer_clusters=config.MAP_LAYER_CLUSTERS,
        layer_walk=config.MAP_LAYER_WALK,
        layer_schools=config.MAP_LAYER_SCHOOLS,
        col_group=config.MAP_COL_GROUP,
        col_households=config.MAP_COL_HOUSEHOLDS,
        col_volunteers=config.MAP_COL_VOLUNTEERS,
        isolated=config.MAP_ISOLATED,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path

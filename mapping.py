# -*- coding: utf-8 -*-
"""Build a self-contained HTML map: swisstopo tiles, households, groups, schools.

Every colour, width, dash pattern and opacity comes from the style dicts in
section 8 of config; they are serialised to JSON and spread straight into the
Leaflet calls, so nothing is restyled here. All visible text comes from the
French strings in section 9.
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
  tr.leftovers td{{color:#9aa4af}}
  .pop b{{font-size:13px}}.pop span{{color:#5d6773}}
  .cluster-number{{font:700 13px/18px system-ui,sans-serif;color:{color_cluster};
    text-align:center;
    text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff,0 0 3px #fff}}
  .ring-label{{font:600 11px/16px system-ui,sans-serif;color:{ring_color};
    text-align:center;white-space:nowrap;
    text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff,0 0 3px #fff}}
  #status{{position:absolute;left:12px;bottom:12px;z-index:1000;background:#fff;
    border:1px solid #d6dae0;border-left:3px solid #c77700;border-radius:5px;
    padding:8px 11px;font-size:12.5px;color:#3d464f;max-width:min(420px,70vw);
    box-shadow:0 2px 8px rgba(0,0,0,.12);display:none}}
</style>
</head>
<body>
<div id="map"></div>
<div id="status"></div>
<div class="panel">
  <h1>{title}</h1>
  <div class="key"><span class="dot" style="background:{color_fixed}"></span>{legend_fixed}</div>
  <div class="key"><span class="dot" style="background:{color_occasional}"></span>{legend_occasional}</div>
  <div class="key"><span class="dot" style="background:{color_plain}"></span>{legend_plain}</div>
  <div class="key"><span class="dot" style="background:{color_not_interested};width:7px;height:7px;margin:0 2px"></span>{legend_not_interested}</div>
  <div class="key"><span class="dot" style="background:{color_school};border-radius:2px"></span>{legend_school}</div>
  <table id="summary"></table>
  <p class="note"><b>Lignes vertes</b> : {threshold} accompagnants ou plus, de
  quoi tenir une semaine.<br>
  <b>Cercles noirs</b> : temps de marche depuis chaque ecole, du plus epais au
  plus fin &mdash; {circles_text} minutes, a {speed} km/h, l'allure d'un enfant
  de 6 a 10 ans. Distance a vol d'oiseau : compte environ un tiers de plus en
  suivant les rues.<br>
  <b>Aplats orange</b> : les groupes de proximite &mdash; un groupe ne depasse
  jamais {radius} m d'un bout a l'autre.</p>
</div>
<script>
function showStatus(text) {{
  const box = document.getElementById('status');
  box.textContent = text; box.style.display = 'block';
}}
if (typeof L === 'undefined') {{
  showStatus({no_leaflet});
}} else {{
const HOUSEHOLDS={households}, SCHOOLS={schools}, CLUSTERS={clusters},
      LEFTOVERS={leftovers}, RINGS={rings}, COLORS={colors}, THRESHOLD={threshold};

// Styles, tels qu'ils sont definis dans config.py section 8.
const S_HOUSEHOLD={style_household}, S_HOUSEHOLD_NI={style_household_ni},
      S_CLUSTER={style_cluster}, S_RING={style_ring}, S_SCHOOL={style_school},
      COLOR_NOT_INTERESTED={color_not_interested_js};

const map = L.map('map');

// Deux ordres d'axes possibles pour les tuiles swisstopo. On essaie le
// premier ; si les tuiles reviennent en erreur, on bascule sur l'autre.
const TILE_OPTS = {{maxZoom:{max_zoom}, maxNativeZoom:{max_native_zoom},
                   attribution:'{attribution}'}};
const URLS = {{
  map:    ['{tiles_map}', '{tiles_map_alt}'],
  aerial: ['{tiles_aerial}', '{tiles_aerial_alt}']
}};

let tileErrors = 0, tilesLoaded = 0, swapped = false;
const baseMap    = L.tileLayer(URLS.map[0], TILE_OPTS);
const baseAerial = L.tileLayer(URLS.aerial[0], TILE_OPTS);
baseMap.addTo(map);

function watch(layer) {{
  layer.on('tileload', () => {{ tilesLoaded++; }});
  layer.on('tileerror', () => {{
    if (++tileErrors >= 4 && !swapped) {{
      swapped = true;
      console.warn('Tuiles swisstopo en erreur, bascule sur ' + URLS.map[1]);
      baseMap.setUrl(URLS.map[1]);
      baseAerial.setUrl(URLS.aerial[1]);
      tileErrors = 0;
    }}
  }});
}}
watch(baseMap); watch(baseAerial);

const layerClusters=L.layerGroup().addTo(map), layerRings=L.layerGroup().addTo(map),
      layerHouseholds=L.layerGroup().addTo(map), layerSchools=L.layerGroup().addTo(map);

CLUSTERS.forEach(c=>{{
  L.circle([c.lat,c.lon], Object.assign({{}}, S_CLUSTER, {{radius:c.radius}}))
   .bindTooltip(`Groupe ${{c.cluster}} &mdash; ${{c.households}} foyers, `+
                `<b>${{c.volunteers}} accompagnant(s)</b><br>${{c.streets}}`)
   .addTo(layerClusters);
  if ({show_cluster_number}) {{
    L.marker([c.lat,c.lon], {{interactive:false, icon:L.divIcon({{
      className:'', iconSize:[26,18], iconAnchor:[13,9],
      html:`<div class="cluster-number">${{c.cluster}}</div>`}})}})
     .addTo(layerClusters);
  }}
}});

SCHOOLS.forEach((s,si)=>{{
  RINGS.forEach(r=>{{
    L.circle([s.lat,s.lon], Object.assign({{}}, S_RING,
      {{radius:r.radius, weight:r.width, dashArray:r.dash}}))
     .bindTooltip(`${{r.label}} de marche &ndash; ${{s.nom}}`).addTo(layerRings);

    // Etiquette posee sur le cercle, orientee differemment par ecole
    // pour que celles de deux ecoles voisines ne se superposent pas.
    const bearing = (-90 + si*35) * Math.PI/180;
    const dLat = r.radius*Math.cos(bearing)/111320;
    const dLon = r.radius*Math.sin(bearing)/(111320*Math.cos(s.lat*Math.PI/180));
    L.marker([s.lat+dLat, s.lon+dLon], {{interactive:false, icon:L.divIcon({{
      className:'', iconSize:[52,16], iconAnchor:[26,8],
      html:`<div class="ring-label">${{r.label}}</div>`}})}}).addTo(layerRings);
  }});

  const inner = S_SCHOOL.size - 2*S_SCHOOL.borderWidth;
  L.marker([s.lat,s.lon],{{icon:L.divIcon({{className:'',
    iconSize:[S_SCHOOL.size,S_SCHOOL.size],
    iconAnchor:[S_SCHOOL.size/2,S_SCHOOL.size/2],
    html:`<div style="width:${{inner}}px;height:${{inner}}px;`+
         `background:${{S_SCHOOL.color}};`+
         `border:${{S_SCHOOL.borderWidth}}px solid ${{S_SCHOOL.borderColor}};`+
         `border-radius:${{S_SCHOOL.cornerRadius}}px;`+
         `box-shadow:0 0 0 1.5px ${{S_SCHOOL.color}}"></div>`}})}})
   .bindPopup(`<b>${{s.nom}}</b>`).addTo(layerSchools);
}});

HOUSEHOLDS.forEach(h=>{{
  if (!h.interested && !{show_not_interested}) return;
  const isVolunteer = h.commitment !== '{commitment_none}';
  const base = isVolunteer ? {radius_volunteer} : {radius_plain};
  const style = h.interested
    ? Object.assign({{}}, S_HOUSEHOLD, {{
        radius: base,
        fillColor: COLORS[h.commitment] || '{color_plain}'}})
    : Object.assign({{}}, S_HOUSEHOLD_NI, {{
        radius: base * {not_interested_scale},
        fillColor: COLOR_NOT_INTERESTED}});
  L.circleMarker([h.lat,h.lon], style)
   .bindPopup(`<div class="pop"><b>${{h.name}}</b><br><span>${{h.address}}</span>`+
     `<br><br>${{h.interested ? '' : '{not_interested_label} \u00b7 '}}${{h.commitment}}`+
     `<br><span>Groupe ${{h.cluster}}</span>`+
     (h.slots?`<br><br><span>${{h.slots}}</span>`:'')+`</div>`)
   .addTo(layerHouseholds);
}});

document.getElementById('summary').innerHTML =
 '<tr><th class="n">{col_number}</th><th>{col_group}</th>'+
 '<th class="n">{col_households}</th><th class="n">{col_volunteers}</th></tr>'+
 CLUSTERS.concat(LEFTOVERS?[LEFTOVERS]:[])
  .map(c=>`<tr class="${{c.cluster===0?'leftovers':(c.volunteers>=THRESHOLD?'ready':'')}}">`+
   `<td class="n"><b>${{c.cluster}}</b></td><td>${{c.streets}}</td>`+
   `<td class="n">${{c.households}}</td>`+
   `<td class="n"><b>${{c.volunteers}}</b></td></tr>`).join('');

L.control.layers(
 {{'{layer_map}':baseMap,'{layer_aerial}':baseAerial}},
 {{'{layer_households}':layerHouseholds,'{layer_clusters}':layerClusters,
   '{layer_walk}':layerRings,'{layer_schools}':layerSchools}},
 {{collapsed:false, position:'{control_position}'}}).addTo(map);

// Cadrage sur les domiciles seuls : une ecole mal geocodee ne doit pas
// faire dezoomer toute la carte.
map.setView([46.5230, 6.9020], 14);
if (HOUSEHOLDS.length) {{
  map.fitBounds(L.featureGroup([layerHouseholds]).getBounds().pad(.12));
}}

// Diagnostic visible : combien de points traces, et les tuiles repondent-elles.
setTimeout(() => {{
  const parts = [`${{HOUSEHOLDS.length}} domiciles traces`,
                 `${{CLUSTERS.length}} groupes`,
                 `${{SCHOOLS.length}} ecoles`];
  if (tilesLoaded === 0) {{
    parts.push('aucune tuile de fond chargee (swisstopo ne repond pas) : '
               + 'les points et les groupes restent exploitables');
    showStatus(parts.join(' \u00b7 '));
  }} else if (!HOUSEHOLDS.length) {{
    showStatus('Aucun domicile a afficher : relance python cli.py geocode');
  }}
}}, 3000);
}}
</script>
</body>
</html>
"""


def _rings():
    """Walking rings, widths and dashes interpolated from the two extremes."""
    minutes = sorted(config.WALK_CIRCLES_MIN)
    span = max(len(minutes) - 1, 1)
    dash_on_max, dash_off_max = config.WALK_RING_DASH_MAX
    dash_on_min, dash_off_min = config.WALK_RING_DASH_MIN

    out = []
    for index, value in enumerate(minutes):
        share = index / span
        width = (config.WALK_RING_WIDTH_MAX
                 - share * (config.WALK_RING_WIDTH_MAX - config.WALK_RING_WIDTH_MIN))
        dash_on = dash_on_max - share * (dash_on_max - dash_on_min)
        dash_off = dash_off_max - share * (dash_off_max - dash_off_min)
        out.append({
            "minutes": value,
            "radius": config.WALK_SPEED_KMH * 1000 / 60 * value,
            "width": round(width, 2),
            "dash": f"{round(dash_on)},{round(dash_off)}",
            "label": config.WALK_RING_LABEL.format(minutes=value),
        })
    return out


def build(df, schools, envelopes, path, leftovers=None):
    """Write the HTML map and return its path."""
    households = [{
        "name": str(row["Nom"]),
        "address": str(row["Adresse"]).replace(config.COUNTRY, ""),
        "group": str(row["Groupe"]),
        "commitment": str(row["Engagement"]),
        "interested": bool(row.get("interested",
                                   str(row.get("Interesse", "")).strip().lower() == "oui")),
        "slots": "" if pd.isna(row.get("Moments")) else str(row["Moments"]),
        "cluster": int(row["cluster"]),
        "lat": float(row["lat"]), "lon": float(row["lon"]),
    } for _, row in df.iterrows()]

    html = TEMPLATE.format(
        page_title=config.MAP_PAGE_TITLE,
        title=config.MAP_TITLE,
        leaflet_css=config.LEAFLET_CSS,
        leaflet_js=config.LEAFLET_JS,
        tiles_map=config.TILES_MAP,
        tiles_map_alt=config.TILES_MAP_ALT,
        tiles_aerial=config.TILES_AERIAL,
        tiles_aerial_alt=config.TILES_AERIAL_ALT,
        attribution=config.ATTRIBUTION,
        max_zoom=config.MAX_ZOOM,
        max_native_zoom=config.MAX_NATIVE_ZOOM,
        control_position=config.LAYER_CONTROL_POSITION,
        households=json.dumps(households, ensure_ascii=False),
        schools=json.dumps(schools, ensure_ascii=False),
        clusters=json.dumps(envelopes, ensure_ascii=False),
        leftovers=json.dumps(leftovers, ensure_ascii=False),
        rings=json.dumps(_rings()),
        colors=json.dumps(config.COLORS, ensure_ascii=False),
        # Styles, serialised straight from config.
        style_household=json.dumps(config.HOUSEHOLD_STYLE),
        style_household_ni=json.dumps(config.HOUSEHOLD_STYLE_NOT_INTERESTED),
        style_cluster=json.dumps(config.CLUSTER_STYLE),
        style_ring=json.dumps(config.WALK_RING_STYLE),
        style_school=json.dumps(config.SCHOOL_STYLE),
        color_not_interested_js=json.dumps(config.COLOR_NOT_INTERESTED),
        color_not_interested=config.COLOR_NOT_INTERESTED,
        color_fixed=config.COLORS[config.COMMITMENT_FIXED],
        color_occasional=config.COLORS[config.COMMITMENT_OCCASIONAL],
        color_plain=config.COLORS[config.COMMITMENT_NONE],
        color_school=config.SCHOOL_STYLE["color"],
        ring_color=config.WALK_RING_STYLE["color"],
        commitment_none=config.COMMITMENT_NONE,
        radius_volunteer=config.MARKER_RADIUS_VOLUNTEER,
        radius_plain=config.MARKER_RADIUS_PLAIN,
        not_interested_scale=config.NOT_INTERESTED_SCALE,
        show_not_interested=json.dumps(config.SHOW_NOT_INTERESTED),
        threshold=config.ROUTE_THRESHOLD,
        radius=config.CLUSTER_DIAMETER_M,
        circles_text=" / ".join(str(m) for m in config.WALK_CIRCLES_MIN),
        speed=config.WALK_SPEED_KMH,
        legend_fixed=config.MAP_LEGEND_FIXED,
        legend_occasional=config.MAP_LEGEND_OCCASIONAL,
        legend_plain=config.MAP_LEGEND_PLAIN,
        legend_not_interested=config.MAP_LEGEND_NOT_INTERESTED,
        not_interested_label=config.MAP_LEGEND_NOT_INTERESTED,
        legend_school=config.MAP_LEGEND_SCHOOL,
        layer_map=config.MAP_LAYER_MAP,
        layer_aerial=config.MAP_LAYER_AERIAL,
        layer_households=config.MAP_LAYER_HOUSEHOLDS,
        layer_clusters=config.MAP_LAYER_CLUSTERS,
        layer_walk=config.MAP_LAYER_WALK,
        layer_schools=config.MAP_LAYER_SCHOOLS,
        col_group=config.MAP_COL_GROUP,
        col_households=config.MAP_COL_HOUSEHOLDS,
        col_number=config.MAP_COL_NUMBER,
        color_cluster=config.CLUSTER_STYLE['color'],
        show_cluster_number=json.dumps(config.CLUSTER_SHOW_NUMBER),
        col_volunteers=config.MAP_COL_VOLUNTEERS,
        isolated=config.MAP_ISOLATED,
        no_leaflet=json.dumps(config.MAP_STATUS_NO_LEAFLET),
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path

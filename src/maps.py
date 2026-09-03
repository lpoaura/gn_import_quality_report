"""
maps.py
=======
Équivalent Python (Folium / Leaflet.js) des cartes `leaflet` générées en R.
Chaque fonction retourne un fragment HTML autonome (`Map()._repr_html_()`)
prêt à être injecté dans le template Jinja2.

R (leaflet)                                Python (folium)
addProviderTiles("CartoDB.Positron")   ->  tiles="CartoDB positron"
addPolygons(fillColor=~pal(nb_data))   ->  folium.GeoJson + branca.colormap
addCircleMarkers(...)                  ->  folium.CircleMarker / MarkerCluster
addLegend(...)                         ->  colormap.add_to(m)
fitBounds(...)                         ->  m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])
"""

from __future__ import annotations

import json
import logging

import branca.colormap as cm
import folium
import pandas as pd
from folium.plugins import MarkerCluster

from .formatting import format_number

logger = logging.getLogger(__name__)


DEFAULT_CENTER = (45.444, 3.75)  # Centre approximatif de l'Auvergne-Rhône-Alpes

# Option 1 — OSM standard (le plus simple, le plus connu)
#TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
#TILES_ATTR = "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"

# Option 2 — CartoDB Voyager (fond plus doux, très lisible, gratuit en usage raisonnable)
TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
TILES_ATTR = "&copy; OpenStreetMap contributors &copy; <a href='https://carto.com/attributions'>CARTO</a>"

# Option 3 — Esri World Street Map (aucune clé requise, bonne fiabilité)
# TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
# TILES_ATTR = "Tiles &copy; Esri"


def _empty_map(message: str = "Pas de données à afficher") -> str:
    m = folium.Map(location=DEFAULT_CENTER, zoom_start=6, tiles=TILES, attr=TILES_ATTR)
    folium.Marker(DEFAULT_CENTER, tooltip=message, icon=folium.Icon(color="lightgray")).add_to(m)
    return m._repr_html_()


def map_maillage(df: pd.DataFrame) -> str:
    """Carte choroplèthe du maillage M5 (nombre de données par maille) —
    section 3, équivalent de `carto_1` en R."""
    if df.empty or "geojson" not in df:
        return _empty_map("Aucune donnée géographique pour cette source")

    values = df["nb_data"].astype(float)
    colormap = cm.linear.PuRd_09.scale(values.min(), values.max())
    colormap.caption = "Nombre de données"

    m = folium.Map(tiles=TILES, attr=TILES_ATTR)
    bounds: list[list[float]] = []

    for _, row in df.iterrows():
        try:
            geom = json.loads(row["geojson"])
        except (TypeError, ValueError):
            continue
        feature = {"type": "Feature", "geometry": geom, "properties": {}}
        folium.GeoJson(
            feature,
            style_function=lambda _feat, nb=row["nb_data"]: {
                "fillColor": colormap(float(nb)),
                "color": "grey",
                "weight": 1,
                "fillOpacity": 0.75,
            },
            tooltip=folium.Tooltip(
                f"Nombre de données : {format_number(row['nb_data'])}<br>"
                f"Nombre d'espèces : {format_number(row.get('nb_esp'))}"
            ),
        ).add_to(m)
        # Accumulation des bornes pour le fitBounds
        coords = geom.get("coordinates")
        for lon, lat in _iter_coords(geom.get("type"), coords):
            bounds.append([lat, lon])

    colormap.add_to(m)
    if bounds:
        m.fit_bounds(bounds)
    else:
        m.location = DEFAULT_CENTER
        m.zoom_start = 6
    return m._repr_html_()


def _iter_coords(geom_type: str, coords):
    """Aplatit récursivement les coordonnées GeoJSON (Polygon/MultiPolygon)."""
    if geom_type in ("Polygon",):
        for ring in coords:
            for lon, lat in ring:
                yield lon, lat
    elif geom_type in ("MultiPolygon",):
        for polygon in coords:
            for ring in polygon:
                for lon, lat in ring:
                    yield lon, lat
    elif geom_type == "Point":
        yield coords[0], coords[1]


def map_points(
    df: pd.DataFrame,
    lat_col: str = "lat",
    lon_col: str = "lon",
    popup_fields: list[str] | None = None,
    color: str = "#e52329",
    fill_color: str = "#ea7200",
    cluster: bool = False,
    empty_message: str = "Aucune donnée à afficher",
) -> str:
    """Carte générique de points (doublons, données hors-région, EEE) —
    équivalent des `addCircleMarkers` en R."""
    if df.empty:
        return _empty_map(empty_message)

    df = df.dropna(subset=[lat_col, lon_col])
    if df.empty:
        return _empty_map(empty_message)

    m = folium.Map(tiles=TILES, attr=TILES_ATTR)
    target = MarkerCluster().add_to(m) if cluster else m

    popup_fields = popup_fields or []
    for _, row in df.iterrows():
        popup_html = "<br>".join(f"<b>{col}</b> : {row[col]}" for col in popup_fields if col in row)
        folium.CircleMarker(
            location=(row[lat_col], row[lon_col]),
            radius=6,
            color=color,
            weight=1,
            opacity=0.85,
            fill=True,
            fill_color=fill_color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=300) if popup_html else None,
        ).add_to(target)

    bounds = [[df[lat_col].min(), df[lon_col].min()], [df[lat_col].max(), df[lon_col].max()]]
    if bounds[0] != bounds[1]:
        m.fit_bounds(bounds)
    else:
        m.location = bounds[0]
        m.zoom_start = 10
    return m._repr_html_()

"""
charts.py
=========
Équivalent Python (Plotly) des graphiques `plotly` générés en R dans
`rapport.Rmd`. Chaque fonction retourne un fragment HTML autonome
(`fig.to_html(full_html=False, include_plotlyjs=False, ...)`) prêt à être
injecté dans le template Jinja2. `plotly.js` n'est chargé qu'une seule fois,
dans le `<head>` du template (voir `templates/report_template.html`).
"""

from __future__ import annotations

import itertools

import pandas as pd
import plotly.graph_objects as go

PURPLE = "#8031a7"

# Palette réutilisée pour les graphiques catégoriels (types de géométrie),
# fidèle aux couleurs du rapport R d'origine.
COULEURS_GEOM = {
    "Points": "#6ab023",
    "Lignes": "#0099d0",
    "Polygones": "#ea7200",
    "Sans geometrie": "#e52329",
    "Autre": "#9aa0a6",
}

COULEURS_VALIDATION = {
    "Certain - très probable": "#007e84",
    "Probable": "#00628b",
    "En attente de validation": "#e2c33a",
    "Douteux": "#e49937",
    "Non réalisable": "#333332",
    "Inconnu": "#626a6e",
    "Invalide": "#e52329",
}

_QUALITATIVE_PALETTE = itertools.cycle(
    ["#8031a7", "#0099d0", "#6ab023", "#ea7200", "#e52329", "#007e84", "#e2c33a", "#333332"]
)


def _fig_to_html(fig: go.Figure, div_id: str) -> str:
    fig.update_layout(margin=dict(t=30, b=40, l=40, r=20), font=dict(family="Inter, sans-serif"))
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id, config={"displaylogo": False})


def chart_data_par_an(df: pd.DataFrame, div_id: str = "chart_annee") -> str:
    """Barres 'Nombre de données par an' (section 2)."""
    fig = go.Figure(
        go.Bar(x=df["an"], y=df["Donnees"], marker_color=PURPLE, name="Données",
               hovertemplate="<b>%{x}</b><br>Données : %{y:,.0f}<extra></extra>")
    )
    fig.update_layout(
        xaxis=dict(title="Année", rangeslider=dict(visible=True)),
        yaxis=dict(title="Nombre de données"),
    )
    return _fig_to_html(fig, div_id)


def chart_data_par_mois(df: pd.DataFrame, div_id: str = "chart_mois") -> str:
    """Barres 'Nombre de données par mois' (section 2)."""
    fig = go.Figure(
        go.Bar(x=df["date2"], y=df["Donnees"], marker_color=PURPLE, name="Données",
               hovertemplate="<b>%{x|%Y-%m}</b><br>Données : %{y:,.0f}<extra></extra>")
    )
    fig.update_layout(
        xaxis=dict(title="Année - Mois", rangeslider=dict(visible=True)),
        yaxis=dict(title="Nombre de données"),
    )
    return _fig_to_html(fig, div_id)


def chart_donut(df: pd.DataFrame, label_col: str, value_col: str, div_id: str,
                 colors: dict[str, str] | None = None) -> str:
    """Camembert (donut) générique : répartition taxonomique, type de géométrie,
    statut de validation, etc. (sections 3, 4, 6)."""
    labels = df[label_col].astype(str).tolist()
    if colors:
        marker_colors = [colors.get(lbl, next(_QUALITATIVE_PALETTE)) for lbl in labels]
    else:
        marker_colors = [next(_QUALITATIVE_PALETTE) for _ in labels]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=df[value_col],
            hole=0.55,
            textinfo="label+percent",
            marker=dict(colors=marker_colors),
            hovertemplate="%{label}<br>%{value:,.0f} (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(showlegend=True)
    return _fig_to_html(fig, div_id)


def chart_altitudes(df: pd.DataFrame, div_id: str = "chart_altitudes") -> str:
    """Barres horizontales empilées (échelle log) — répartition des altitudes
    (section 3)."""
    df = df.sort_values("classe_altitude_order")
    fig = go.Figure()
    couleurs = {"correct": "#6ab023", "incorrect": "#ea7200"}
    for statut in ["correct", "incorrect"]:
        sous_df = df[df["validite"] == statut]
        if sous_df.empty:
            continue
        fig.add_trace(
            go.Bar(
                y=sous_df["classe_altitude"],
                x=sous_df["tot_data"],
                name=statut,
                orientation="h",
                marker_color=couleurs[statut],
                hovertemplate="Nombre de données : %{x}<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Nombre de données (échelle log)", type="log"),
        yaxis=dict(title="Classe d'altitude en mètres"),
        legend=dict(title="Statut de validité"),
    )
    return _fig_to_html(fig, div_id)

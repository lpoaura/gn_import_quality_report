"""
report_generator.py
====================
Assemble les données (data_service), les graphiques (charts), les cartes
(maps) et les tableaux (tables) au sein du template Jinja2
`templates/report_template.html`, puis écrit le fichier HTML final.

C'est l'équivalent Python de l'exécution de `rmarkdown::render(rapport.Rmd)`
pour une source donnée.
"""

from __future__ import annotations

import datetime as dt
import logging
import pandas as pd
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import Connection

from . import charts as charts
from . import maps as maps
from . import tables as tables

from .config import config
from .data_service import SourceReportData, load_source_data
from .formatting import csv_download_link, format_number, format_percent, sanitize_filename

logger = logging.getLogger(__name__)

_jinja_env = Environment(
    loader=FileSystemLoader(str(config.TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)
_jinja_env.filters["fmt_num"] = format_number
_jinja_env.filters["fmt_pct"] = format_percent


def _load_inline_css() -> str:
    """Charge la feuille de style pour l'injecter directement dans le `<style>`
    du rapport : le fichier HTML produit reste ainsi totalement autonome
    (déplaçable, envoyable par email) sans dépendre d'un chemin relatif,
    à l'image du fichier unique produit par `rmarkdown::render()` en R."""
    css_path = config.STATIC_DIR / "report.css"
    try:
        return css_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Feuille de style introuvable (%s) — rapport généré sans CSS personnalisé", css_path)
        return ""


def _build_context(data: SourceReportData) -> dict:
    """Construit le contexte Jinja2 : KPI, tableaux HTML, graphiques HTML, cartes HTML."""

    context: dict = {
        "nom_source": data.nom_source,
        "date_edition": dt.date.today().strftime("%d/%m/%Y"),
        "author": config.AUTHOR,
        "logo_url": config.LOGO_URL,
        "contact_email": config.CONTACT_EMAIL,
        "inline_css": _load_inline_css(),
        # -- KPI section 1 --------------------------------------------------
        "nb_obs": data.nb_obs,
        "nb_taxon": data.nb_taxon,
        "nb_esp": data.nb_esp,
        "nb_jdd": data.nb_jdd,
        "nb_ca": data.nb_ca,
        # -- flags conditionnels (équivalent eval=show_xxx en R) ------------
        "show_doublon": data.show_doublon,
        "show_doublon_source": data.show_doublon_source,
        "show_validation": data.show_validation,
        "show_data_hors_regions": data.show_data_hors_regions,
        "show_data_hors_altitude": data.show_data_hors_altitude,
        "show_data_mois_hors_plage": data.show_data_mois_hors_plage,
        "show_eee": data.show_eee,
        "nb_data_hors_regions": len(data.data_hors_regions),
        "nb_data_hors_altitude": data.nb_data_hors_altitude,
        "nb_data_mois_hors_plage": data.nb_data_mois_hors_plage,
        "dates_mois_hors_plage": data.dates_mois_hors_plage,
        "nb_nouvelles_eee": data.nb_nouvelles_eee,
        "nb_doublon": len(data.data_doublon),
        "nb_validation": len(data.data_validation),

    }

    # -- section 2 : répartition temporelle ---------------------------------
    context["chart_annee"] = charts.chart_data_par_an(data.data_year) if not data.data_year.empty else ""
    context["chart_mois"] = charts.chart_data_par_mois(data.data_month) if not data.data_month.empty else ""

    # -- section 3 : répartition spatiale ------------------------------------
    context["map_maillage"] = maps.map_maillage(data.data_geom_mesh)
    context["map_hors_regions"] = (
        maps.map_points(
            data.data_hors_regions,
            popup_fields=["id_synthese", "nom_cite", "date_max", "observers"],
            color="#e52329",
            fill_color="#ea7200",
            empty_message="Aucune donnée hors région",
        )
        if data.show_data_hors_regions
        else ""
    )
    context["chart_type_geom"] = (
        charts.chart_donut(data.data_type_geom, "type_geom", "nb_data", "chart_type_geom", charts.COULEURS_GEOM)
        if not data.data_type_geom.empty
        else ""
    )
    lignes_df = data.data_taille_geom[data.data_taille_geom.get("type_geom") == "Lignes"] if not data.data_taille_geom.empty else pd.DataFrame()
    polygones_df = data.data_taille_geom[data.data_taille_geom.get("type_geom") == "Polygones"] if not data.data_taille_geom.empty else pd.DataFrame()
    context["chart_taille_lignes"] = (
        charts.chart_taille_geom(lignes_df, "longueur", "chart_taille_lignes") if not lignes_df.empty else ""
    )
    context["chart_taille_polygones"] = (
        charts.chart_taille_geom(polygones_df, "surface", "chart_taille_polygones") if not polygones_df.empty else ""
    )
    context["show_geom_imprecise"] = data.show_geom_imprecise
    context["nb_geom_imprecise"] = data.nb_geom_imprecise
    context["seuil_longueur_alerte_km"] = config.SEUIL_LONGUEUR_ALERTE_KM
    context["seuil_surface_alerte_ha"] = config.SEUIL_SURFACE_ALERTE_HA

    context["chart_altitudes"] = (
        charts.chart_altitudes(data.data_altitudes) if not data.data_altitudes.empty else ""
    )

    # -- section 4 : répartition taxonomique ---------------------------------
    data_esp_grouped = charts.group_small_categories(data.data_repartition_esp, "groupe_taxo", "nb_esp")
    context["chart_esp_taxo"] = (
        charts.chart_donut(data_esp_grouped, "groupe_taxo", "nb_esp", "chart_esp_taxo", charts.COULEURS_TAXO)
        if not data.data_repartition_esp.empty else ""
    )

    data_data_grouped = charts.group_small_categories(data.data_repartition_data, "groupe_taxo", "nb_data")
    context["chart_data_taxo"] = (
        charts.chart_donut(data_data_grouped, "groupe_taxo", "nb_data", "chart_data_taxo", charts.COULEURS_TAXO)
        if not data.data_repartition_data.empty else ""
    )
    tab_rang_tax_fmt = data.tab_rang_tax.copy()
    if not tab_rang_tax_fmt.empty:
        tab_rang_tax_fmt["part_data"] = tab_rang_tax_fmt["part_data"].apply(format_percent)
        tab_rang_tax_fmt["repartition_total"] = tab_rang_tax_fmt["repartition_total"].apply(format_percent)
        tab_rang_tax_fmt["nb_data"] = tab_rang_tax_fmt["nb_data"].apply(format_number)
        tab_rang_tax_fmt = tab_rang_tax_fmt.rename(
            columns={
                "Rang": "Rang",
                "nb_data": "Nb. de données importées",
                "part_data": "Part du lot de données",
                "repartition_total": "Répartition totale dans la base",
            }
        )
    context["tab_rang_tax"] = tables.render_static_table(tab_rang_tax_fmt)

    # -- section 5 : métadonnées ----------------------------------------------
    tab_ca_fmt = data.tab_ca.copy()
    if not tab_ca_fmt.empty:
        tab_ca_fmt["nb_data"] = tab_ca_fmt["nb_data"].apply(format_number)
        tab_ca_fmt = tab_ca_fmt.rename(columns={"nb_data": "Nb. de données"})
    context["tab_ca"] = tables.render_interactive_table(tab_ca_fmt)

    tab_jdd_fmt = data.tab_jdd.copy()
    if not tab_jdd_fmt.empty:
        tab_jdd_fmt["nb_data"] = tab_jdd_fmt["nb_data"].apply(format_number)
        tab_jdd_fmt = tab_jdd_fmt.rename(columns={"nb_data": "Nb. de données"})
    context["tab_jdd"] = tables.render_interactive_table(tab_jdd_fmt)

    # -- section 6 : validation -------------------------------------------------
    context["chart_validation"] = (
        charts.chart_donut(data.data_valid, "label_valid_status", "nb_data", "chart_validation", charts.COULEURS_VALIDATION)
        if not data.data_valid.empty
        else ""
    )
    context["tab_validation"] = tables.render_interactive_table(data.data_validation)

    # -- section 7 : doublons -----------------------------------------------
    context["nb_source_doublon"] = len(data.source_doublon)
    context["tab_source_doublon"] = tables.render_static_table(data.source_doublon)
    

    doublon_display = data.data_doublon.copy()
    if not doublon_display.empty:
        doublon_display = doublon_display[
            [c for c in ["cd_nom", "nom_vern", "lb_nom", "date", "observers", "nb_data_similaire"] if c in doublon_display]
        ].rename(
            columns={
                "cd_nom": "cd_nom",
                "nom_vern": "Nom vernaculaire",
                "lb_nom": "Nom scientifique",
                "date": "Date",
                "observers": "Observateur",
                "nb_data_similaire": "Nb données similaires",
            }
        )
    context["tab_doublon"] = tables.render_interactive_table(doublon_display)
    context["doublon_csv_link"] = csv_download_link(
        data.data_doublon, "donnees_doublonnees.csv", "Télécharger les données doublonnées"
    )
    context["map_doublon"] = (
        maps.map_points(
            data.data_doublon,
            popup_fields=["nom_vern", "lb_nom", "cd_nom", "date", "observers", "nb_data_similaire"],
            cluster=True,
            empty_message="Aucun doublon détecté",
        )
        if data.show_doublon
        else ""
    )

    # -- section 8 : EEE ------------------------------------------------------
    tab_eee_fmt = data.data_eee_synthese.copy()
    if not tab_eee_fmt.empty:
        tab_eee_fmt = tab_eee_fmt.rename(
            columns={
                "nom_vern": "Nom vernaculaire",
                "lb_nom": "Nom scientifique",
                "cd_ref": "Cd_ref",
                "presence_connue_orb": "Présence connue",
                "secteur_obs": "Secteur(s) d'observation",
                "nouvelle_presence": "Nouvelle présence",
                "nb_donnees": "Nombre d'observations",
                "premiere_observation": "Première obs.",
                "derniere_observation": "Dernière obs.",
            }
        )
        tab_eee_fmt = tab_eee_fmt.drop(columns=["effectif_min", "effectif_max"], errors="ignore")
    context["tab_eee"] = tables.render_static_table(tab_eee_fmt)
    context["map_eee"] = (
        maps.map_points(
            data.data_eee_points,
            popup_fields=["nom_vern", "lb_nom", "secteur_obs"],
            color="#8031a7",
            fill_color="#8031a7",
            cluster=True,
            empty_message="Aucune EEE nouvellement observée",
        )
        if data.show_eee
        else ""
    )

    return context


def generate_report(conn: Connection, nom_source: str, list_id: list[str], output_dir: Path | None = None) -> Path:
    """Génère le rapport HTML complet pour une source et retourne le chemin du fichier écrit."""

    output_dir = output_dir or config.OUTPUT_DIR
    logger.info("=== Génération du rapport pour « %s » ===", nom_source)

    data = load_source_data(conn, nom_source, list_id)
    context = _build_context(data)

    template = _jinja_env.get_template("report_template.html")
    html_content = template.render(**context)

    filename = sanitize_filename(nom_source) + ".html"
    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")

    logger.info("Rapport généré avec succès : %s", output_path)
    return output_path

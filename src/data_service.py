"""
data_service.py
================
Couche « métier » qui orchestre l'ensemble des requêtes nécessaires à la
génération d'un rapport pour une source donnée, et calcule les indicateurs
dérivés (équivalent des blocs `{r include = FALSE}` de `rapport.Rmd`).

Chaque requête est isolée dans un bloc try/except : si une table optionnelle
est absente ou vide sur une instance GeoNature donnée (ex. pas de module de
validation), le rapport continue à être généré avec la section correspondante
simplement masquée, au lieu d'interrompre tout le traitement comme l'aurait
fait le script R (`dbGetQuery` qui lève une erreur non interceptée).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy import Connection

import queries as q
from .config import config
from .db import fetch_df

logger = logging.getLogger(__name__)


@dataclass
class SourceReportData:
    nom_source: str
    list_id: list[str]

    # Indicateurs généraux (section 1)
    nb_obs: int = 0
    nb_taxon: int = 0
    nb_esp: int = 0
    nb_jdd: int = 0
    nb_ca: int = 0

    # Tableaux (section 4 & 5)
    tab_jdd: pd.DataFrame = field(default_factory=pd.DataFrame)
    tab_ca: pd.DataFrame = field(default_factory=pd.DataFrame)
    tab_rang_tax: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Répartition temporelle (section 2)
    data_year: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_month: pd.DataFrame = field(default_factory=pd.DataFrame)
    nb_data_mois_hors_plage: int = 0
    dates_mois_hors_plage: list = field(default_factory=list)


    # Répartition taxonomique (section 4)
    data_repartition_esp: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_repartition_data: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Validation (section 6)
    data_valid: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_validation: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Doublons (section 7)
    data_doublon: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_doublon: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Spatial (section 3)
    data_geom_mesh: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_hors_regions: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_altitudes: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_type_geom: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_taille_geom: pd.DataFrame = field(default_factory=pd.DataFrame)

    # EEE (section 8)
    data_eee_synthese: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_eee_points: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Indicateurs calculés (équivalent show_xxx / eval=... en R)
    nb_data_hors_altitude: int = 0

    @property
    def show_doublon(self) -> bool:
        return not self.data_doublon.empty

    @property
    def show_doublon_source(self) -> bool:
        return not self.source_doublon.empty

    @property
    def show_validation(self) -> bool:
        return not self.data_validation.empty

    @property
    def show_data_hors_regions(self) -> bool:
        return not self.data_hors_regions.empty

    @property
    def show_data_hors_altitude(self) -> bool:
        return self.nb_data_hors_altitude > 0

    @property
    def show_data_mois_hors_plage(self) -> bool:
        return self.nb_data_mois_hors_plage > 0

    @property
    def nb_geom_imprecise(self) -> int:
        if self.data_taille_geom.empty or "imprecise" not in self.data_taille_geom:
            return 0
        return int(self.data_taille_geom.loc[self.data_taille_geom["imprecise"], "nb_data"].sum())

    @property
    def show_geom_imprecise(self) -> bool:
        return self.nb_geom_imprecise > 0

    @property
    def nb_nouvelles_eee(self) -> int:
        if self.data_eee_synthese.empty or "nouvelle_presence" not in self.data_eee_synthese:
            return 0
        return int((self.data_eee_synthese["nouvelle_presence"] == "Oui").sum())

    @property
    def show_eee(self) -> bool:
        return self.nb_nouvelles_eee > 0


def _safe_fetch(conn: Connection, label: str, query_fn, params: dict) -> pd.DataFrame:
    """Exécute une requête avec gestion d'erreur : logue et retourne un
    DataFrame vide en cas d'échec, sans interrompre la génération du rapport."""
    try:
        return fetch_df(conn, query_fn(), params)
    except Exception:  # noqa: BLE001
        logger.exception("Échec de la requête '%s' — la section correspondante sera vide", label)
        conn.rollback()  
        return pd.DataFrame()


def load_source_data(conn: Connection, nom_source: str, list_id: list[str]) -> SourceReportData:
    """Exécute l'ensemble des requêtes pour une source et construit le contexte
    de données complet utilisé par `report_generator.generate_report`."""

    logger.info("Chargement des données pour la source « %s » (%d import(s))", nom_source, len(list_id))
    data = SourceReportData(nom_source=nom_source, list_id=list_id)
    ids_params = {"ids": list_id}

    data.nb_obs = int(_scalar(_safe_fetch(conn, "nb_obs", q.q_nb_obs, ids_params), "nb_data"))
    data.nb_taxon = int(_scalar(_safe_fetch(conn, "nb_taxon", q.q_nb_taxon, ids_params), "nb_tax"))
    data.nb_esp = int(_scalar(_safe_fetch(conn, "nb_esp", q.q_nb_esp, ids_params), "nb_sp"))
    data.nb_jdd = int(_scalar(_safe_fetch(conn, "nb_jdd", q.q_nb_jdd, ids_params), "nb_jdd"))
    data.nb_ca = int(_scalar(_safe_fetch(conn, "nb_ca", q.q_nb_ca, ids_params), "nb_ca"))

    data.tab_jdd = _safe_fetch(conn, "tab_jdd", q.q_tab_jdd, ids_params)
    data.tab_ca = _safe_fetch(conn, "tab_ca", q.q_tab_ca, ids_params)
    data.tab_rang_tax = _safe_fetch(conn, "tab_rang_tax", q.q_tab_rang_tax, ids_params)

    data.data_year = _safe_fetch(conn, "data_year", q.q_data_year, ids_params)
    data.data_month = _safe_fetch(conn, "data_month", q.q_data_month, ids_params)
    data.data_month_out = _safe_fetch(conn, "data_month_out", q.q_data_out, ids_params)
    
    if not data.data_month.empty:
        seuil_annee = config.ANNEE_MIN_VALIDE
        masque_hors_plage = data.data_month["an"].astype(int) < seuil_annee
        hors_plage = data.data_month[masque_hors_plage]
        if not hors_plage.empty:
            data.nb_data_mois_hors_plage = int(hors_plage["Donnees"].sum())
            data.dates_mois_hors_plage = sorted(hors_plage["date"].astype(str).unique().tolist())
            logger.warning(
                "%s : %d donnée(s) antérieure(s) à l'année %d exclue(s) du graphique mensuel (%s)",
                nom_source, data.nb_data_mois_hors_plage, seuil_annee, data.dates_mois_hors_plage,
            )
        data.data_month = data.data_month[~masque_hors_plage].copy()
 
    if not data.data_month.empty:
        data.data_month["date2"] = pd.to_datetime(data.data_month["date2"], errors="coerce")
        non_convertibles = data.data_month["date2"].isna()
        if non_convertibles.any():
            extra = data.data_month[non_convertibles]
            data.nb_data_mois_hors_plage += int(extra["Donnees"].sum())
            data.dates_mois_hors_plage = sorted(
                set(data.dates_mois_hors_plage) | set(extra["date"].astype(str).unique().tolist())
            )
            data.data_month = data.data_month[~non_convertibles].copy()
 
    data.data_repartition_esp = _safe_fetch(conn, "data_repartition_esp", q.q_data_repartition_esp, ids_params)
    data.data_repartition_data = _safe_fetch(conn, "data_repartition_data", q.q_data_repartition_data, ids_params)

    data.data_valid = _safe_fetch(conn, "data_valid", q.q_data_valid, ids_params)
    data.data_validation = _safe_fetch(conn, "data_validation", q.q_data_validation, ids_params)

    data.data_doublon = _safe_fetch(conn, "data_doublon", q.q_data_doublon, ids_params)
    data.source_doublon = _safe_fetch(conn, "source_doublon", q.q_source_doublon, ids_params)

    data.data_geom_mesh = _safe_fetch(conn, "data_geom_mesh", q.q_data_geom_mesh, ids_params)

    hors_region_params = {"ids": list_id, "region_pattern": config.REGION_NAME_PATTERN}
    data.data_hors_regions = _safe_fetch(conn, "data_hors_regions", q.q_data_hors_regions, hors_region_params)

    data.data_altitudes = _safe_fetch(conn, "data_altitudes", q.q_data_altitudes, ids_params)
    if not data.data_altitudes.empty:
        incorrect = data.data_altitudes[data.data_altitudes["validite"] == "incorrect"]
        data.nb_data_hors_altitude = int(incorrect["tot_data"].sum())

    data.data_type_geom = _safe_fetch(conn, "data_type_geom", q.q_data_type_geom, ids_params)
    data.data_taille_geom = _safe_fetch(conn, "data_taille_geom", q.q_data_taille_geom, ids_params)

    # NB : la synthèse EEE utilise volontairement une liste d'imports fixe
    eee_params = {"ids": list(config.EEE_SOURCE_IDS), "region_pattern": config.REGION_NAME_PATTERN}
    data.data_eee_synthese = _safe_fetch(conn, "data_eee_synthese", q.q_data_eee_synthese, eee_params)
    data.data_eee_points = _safe_fetch(conn, "data_eee_points", q.q_data_eee_points, eee_params)

    logger.info("Chargement terminé pour « %s » : %s données au total", nom_source, data.nb_obs)
    return data


def _scalar(df: pd.DataFrame, column: str, default: float = 0) -> float:
    if df.empty or column not in df or pd.isna(df.iloc[0][column]):
        return default
    return df.iloc[0][column]


def fetch_liste_rapports(conn: Connection) -> pd.DataFrame:
    """Récupère la liste des rapports à générer (équivalent `tableau_rapport`)."""
    df = fetch_df(conn, q.q_liste_rapports())
    logger.info("%d rapport(s) à générer d'après %s", len(df), config.SOURCE_LIST_VIEW)
    return df

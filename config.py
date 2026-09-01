"""
config.py
=========
Configuration centralisée du projet, équivalent Python des variables
d'environnement lues par `RScripts/connexion.R` (Sys.getenv(...)).

Toutes les valeurs peuvent être surchargées par des variables d'environnement
ou par un fichier `.env` (voir `.env.example`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Charge un éventuel fichier .env situé à la racine du projet
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class Config:
    # -- Connexion base de données -------------------------------------------------
    DBNAME: str = os.getenv("DBNAME", "geonature")
    DBHOST: str = os.getenv("DBHOST", "localhost")
    DBPORT: str = os.getenv("DBPORT", "5432")
    DBUSER: str = os.getenv("DBUSER", "grafana")
    DBPWD: str = os.getenv("DBPWD", "")

    # -- /!\ Point de vigilance (cf. SQL/creation_mv) -------------------------------
    # ID source du module d'import de GeoNature. À adapter à VOTRE instance.
    # C'est ce champ qui pilote la lecture de additional_data->>'desc_source'
    # dans gn_imports.t_imports pour la source concernée.
    ID_SOURCE_IMPORT_MODULE: int = int(os.getenv("ID_SOURCE_IMPORT_MODULE", "7087"))

    # Liste des id_source_news fixes utilisés historiquement pour la synthèse EEE.
    # Dans le script R d'origine cette liste était figée en dur dans le rapport.Rmd ;
    # elle est ici externalisée pour rester paramétrable sans toucher au code.
    EEE_SOURCE_IDS: tuple[str, ...] = tuple(
        s.strip()
        for s in os.getenv(
            "EEE_SOURCE_IDS", "7087_390,7087_391,7087_392,7087_394"
        ).split(",")
        if s.strip()
    )

    # Nom de la région utilisée pour les filtres spatiaux (cf. ILIKE '%Auvergne-Rh%ne-Alpes%')
    REGION_NAME_PATTERN: str = os.getenv("REGION_NAME_PATTERN", "%Auvergne-Rh%ne-Alpes%")
    ANNEE_MIN_VALIDE: int = int(os.getenv("ANNEE_MIN_VALIDE", "1677"))

    # -- Chemins ---------------------------------------------------------------------
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "output"))))
    TEMPLATE_DIR: Path = field(default_factory=lambda: Path(os.getenv("TEMPLATE_DIR", str(BASE_DIR / "templates"))))
    STATIC_DIR: Path = field(default_factory=lambda: Path(os.getenv("STATIC_DIR", str(BASE_DIR / "static"))))
    LOG_DIR: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs"))))

    # -- Logging -----------------------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE_NAME: str = os.getenv("LOG_FILE_NAME", "rapport_synthese.log")

    # -- Divers ------------------------------------------------------------------
    LOGO_URL: str = os.getenv(
        "LOGO_URL",
        "https://www.biodiversite-auvergne-rhone-alpes.fr/wp-content/uploads/2020/12/"
        "Logo_Pole_vertebres-e1607781136184.png",
    )
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "orb.aura@lpo.fr")
    AUTHOR: str = os.getenv("AUTHOR", "ORB - Pôle vertébrés")

    # Vue exposant la liste des rapports à générer (équivalent tableau_rapport en R)
    SOURCE_LIST_VIEW: str = os.getenv("SOURCE_LIST_VIEW", "gn_imports.v_c_rapport_generated")

    # Vues matérialisées à rafraîchir avant génération (cf. SQL/creation_mv)
    MATERIALIZED_VIEWS: tuple[str, ...] = (
        "grafana.mv_source_geom_info",
        "grafana.mv_source_dataset",
        "grafana.mv_source_detail",
        "grafana.mv_source_acquisition_framework",
        "grafana.mv_source_niveau_taxonomique",
        "grafana.mv_source_info_temporelle",
    )

    def ensure_directories(self) -> None:
        for d in (self.OUTPUT_DIR, self.LOG_DIR):
            d.mkdir(parents=True, exist_ok=True)


config = Config()
config.ensure_directories()

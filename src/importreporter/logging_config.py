"""
logging_config.py
==================
Mise en place du logging applicatif. Le script R d'origine se contentait de
`print()`/`cat()` : ici chaque étape (connexion BDD, rafraîchissement des vues,
génération de chaque rapport) est tracée avec un niveau de sévérité, un
horodatage, et est conservée dans un fichier journal tournant.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys

from .config import config


def setup_logging() -> logging.Logger:
    """Initialise le logger racine et retourne un logger applicatif dédié."""

    root = logging.getLogger()
    root.setLevel(config.LOG_LEVEL)

    # Évite les handlers dupliqués si setup_logging() est appelé plusieurs fois
    if root.handlers:
        return logging.getLogger("rapport_synthese")

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_DIR / config.LOG_FILE_NAME,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # Bibliothèques tierces trop verbeuses
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logging.getLogger("rapport_synthese")

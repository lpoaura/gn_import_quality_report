"""
main.py
=======
Point d'entrée du programme. Équivalent Python de `RScripts/traitement_analyses.R` :

  1. Rafraîchit les vues matérialisées `grafana.mv_*`
  2. Récupère la liste des sources à traiter (`gn_imports.v_c_rapport_generated`)
  3. Génère un rapport HTML autonome pour chaque source
  4. Journalise le déroulement complet et résume le résultat final

Usage :
    python main.py
    python main.py --source-filter "Association naturaliste"
    python main.py --output-dir ./mes_rapports --log-level DEBUG
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from config import config
from data_service import fetch_liste_rapports
from db import check_connection, get_connection, get_engine, refresh_materialized_views
from formatting import parse_id_list
from logging_config import setup_logging
from report_generator import generate_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Génération des rapports de synthèse des données importées.")
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Répertoire de sortie des rapports HTML (défaut : config.OUTPUT_DIR)",
    )
    parser.add_argument(
        "--source-filter", type=str, default=None,
        help="Ne génère que les rapports dont le nom de source contient ce texte (insensible à la casse)",
    )
    parser.add_argument(
        "--skip-refresh", action="store_true",
        help="Ne rafraîchit pas les vues matérialisées avant génération (utile en développement)",
    )
    parser.add_argument("--log-level", type=str, default=None, help="Surcharge le niveau de log (DEBUG, INFO, ...)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.log_level:
        config.LOG_LEVEL = args.log_level

    logger = setup_logging()
    logger.info("=== Démarrage de la génération des rapports de synthèse ===")

    start = time.monotonic()
    output_dir = args.output_dir or config.OUTPUT_DIR

    engine = get_engine()
    if not check_connection(engine):
        logger.error("Arrêt du programme : connexion à la base de données impossible.")
        return 1

    if not args.skip_refresh:
        try:
            refresh_materialized_views(engine, config.MATERIALIZED_VIEWS)
        except Exception:
            logger.error("Arrêt du programme suite à l'échec du rafraîchissement des vues matérialisées.")
            return 1
    else:
        logger.warning("Rafraîchissement des vues matérialisées ignoré (--skip-refresh)")

    with get_connection(engine) as conn:
        tableau_rapport = fetch_liste_rapports(conn)

        if args.source_filter:
            filtre = args.source_filter.strip()
            mask = (tableau_rapport["nom_fichier"].astype(str).str.strip().eq(filtre))
            #print("Filtre reçu :", repr(filtre))
            #print("Mask :", mask.tolist())
            tableau_rapport = tableau_rapport[mask]
            logger.info(
                "Filtre appliqué sur '%s' : %d rapport(s) restant(s)",
                filtre,
                len(tableau_rapport),
            )


        if tableau_rapport.empty:
            logger.warning("Aucun rapport à générer d'après %s.", config.SOURCE_LIST_VIEW)
            return 0

        succes, echecs = 0, 0
        for i, row in tableau_rapport.iterrows():
            nom_source = row["desc_source"]
            list_id = parse_id_list(str(row["list_import"]))
            logger.info(
                "Rapport [%d/%d] : « %s » -> %s (%d import(s) : %s)",
                i + 1, len(tableau_rapport), nom_source, row["nom_fichier"], len(list_id), list_id,
            )
            try:
                generate_report(conn, nom_source, list_id, output_dir=output_dir)
                succes += 1
            except Exception:
                logger.exception("Échec de la génération du rapport pour « %s »", nom_source)
                echecs += 1
                continue  # on poursuit avec les sources suivantes plutôt que de tout interrompre

    duration = time.monotonic() - start
    logger.info(
        "=== Terminé en %.1fs : %d rapport(s) généré(s) avec succès, %d échec(s) ===",
        duration, succes, echecs,
    )
    return 0 if echecs == 0 else 2


if __name__ == "__main__":
    sys.exit(main())


"""
db.py
=====
Équivalent Python de `RScripts/connexion.R`.

R (RPostgreSQL/DBI)               ->  Python (SQLAlchemy 2.x + psycopg2)
dbDriver("PostgreSQL")            ->  create_engine("postgresql+psycopg2://...")
dbConnect(...)                    ->  engine.connect()
dbGetQuery(conn, sql)              ->  pandas.read_sql(sql, conn)
dbSendQuery(conn, "REFRESH ...")   ->  conn.execute(text("REFRESH ..."))
dbDisconnect(conn)                ->  conn.close() / context manager
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Sequence

import pandas as pd
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL

from .config import config

logger = logging.getLogger(__name__)


def get_engine() -> Engine:
    """Crée le moteur SQLAlchemy de connexion à la base GeoNature."""

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=config.DBUSER,
        password=config.DBPWD,
        host=config.DBHOST,
        port=int(config.DBPORT),
        database=config.DBNAME,
    )
    logger.info(
        "Initialisation du moteur de connexion PostgreSQL (%s@%s:%s/%s)",
        config.DBUSER,
        config.DBHOST,
        config.DBPORT,
        config.DBNAME,
    )
    # pool_pre_ping évite les connexions mortes lors de génération de rapports longs
    return create_engine(url, pool_pre_ping=True, future=True)

@contextmanager
def get_connection(engine: Engine) -> Iterator[Connection]:
    """Context manager ouvrant/fermant proprement une connexion, avec logs."""

    conn = engine.connect()
    logger.debug("Connexion base de données ouverte")
    try:
        yield conn
    except Exception:
        logger.exception("Erreur lors de l'utilisation de la connexion base de données")
        raise
    finally:
        conn.close()
        logger.debug("Connexion base de données fermée")


def check_connection(engine: Engine) -> bool:
    """Vérifie que la connexion fonctionne (équivalent du tryCatch R)."""

    try:
        with get_connection(engine) as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connexion à la base de données réussie !")
        return True
    except Exception as exc:  # noqa: BLE001 - on veut logguer puis remonter/gérer
        logger.error("Impossible de se connecter à la base de données : %s", exc)
        return False


def refresh_materialized_views(engine: Engine, views: Sequence[str] = config.MATERIALIZED_VIEWS) -> None:
    """Rafraîchit les vues matérialisées `grafana.mv_*` avant génération des rapports."""

    with engine.begin() as conn:  # transaction unique, rollback auto en cas d'erreur
        for view in views:
            logger.info("Rafraîchissement de la vue matérialisée %s ...", view)
            try:
                conn.execute(text(f"REFRESH MATERIALIZED VIEW {view};"))
                logger.info("Vue %s rafraîchie avec succès", view)
            except Exception:
                logger.exception("Échec du rafraîchissement de la vue %s", view)
                raise


def fetch_df(conn: Connection, query, params: dict | None = None) -> pd.DataFrame:
    """Exécute une requête et retourne un DataFrame pandas (équivalent dbGetQuery)."""

    label = getattr(query, "text", str(query))
    logger.debug("Exécution requête SQL : %s", label[:150].replace("\n", " "))
    df = pd.read_sql(query, conn, params=params)
    logger.debug("Requête terminée : %s ligne(s) retournée(s)", len(df))
    return df

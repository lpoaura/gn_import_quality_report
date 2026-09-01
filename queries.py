"""
queries.py
==========
Toutes les requêtes SQL utilisées par `RScripts/rapport.Rmd` sont regroupées
ici sous forme de fonctions retournant un objet `sqlalchemy.text` paramétré.

Différence importante avec le script R : en R, `list_id` est injecté par simple
concaténation de chaîne (`paste0("... in (", list_id, ")")`), ce qui est
fonctionnel mais fragile côté sécurité/robustesse. Ici, la clause `IN` est
construite avec un *bind parameter* "expanding" (`bindparam(..., expanding=True)`),
ce qui protège des injections SQL et gère proprement les listes vides.

Chaque fonction est documentée avec la section du rapport R d'origine qu'elle
alimente, pour faciliter la relecture croisée avec `rapport.Rmd`.
"""

from __future__ import annotations

from sqlalchemy import bindparam, text

from config import config


def _ids_query(sql: str):
    """Prépare une requête utilisant `:ids` comme clause IN dynamique."""
    return text(sql).bindparams(bindparam("ids", expanding=True))


# ---------------------------------------------------------------------------
# 0. Liste des rapports à générer (équivalent `tableau_rapport` dans
#    traitement_analyses.R)
# ---------------------------------------------------------------------------

def q_liste_rapports():
    return text(f"SELECT desc_source, nom_fichier, list_import FROM {config.SOURCE_LIST_VIEW};")


# ---------------------------------------------------------------------------
# 1. Informations générales
# ---------------------------------------------------------------------------

def q_nb_obs():
    return _ids_query(
        "SELECT SUM(nb_data) AS nb_data FROM grafana.mv_source_dataset WHERE id_source_news IN :ids;"
    )


def q_nb_taxon():
    return _ids_query(
        "SELECT COUNT(DISTINCT mv.cd_ref) AS nb_tax FROM grafana.mv_source_detail mv "
        "WHERE id_source_news IN :ids;"
    )


def q_nb_esp():
    return _ids_query(
        "SELECT COUNT(DISTINCT mv.cd_ref) AS nb_sp FROM grafana.mv_source_detail mv "
        "WHERE id_rang = 'ES' AND id_source_news IN :ids;"
    )


def q_nb_jdd():
    return _ids_query(
        "SELECT COUNT(DISTINCT id_dataset) AS nb_jdd FROM grafana.mv_source_dataset "
        "WHERE id_source_news IN :ids;"
    )


def q_nb_ca():
    return _ids_query(
        "SELECT COUNT(DISTINCT id_acquisition_framework) AS nb_ca FROM grafana.mv_source_dataset "
        "WHERE id_source_news IN :ids;"
    )


# ---------------------------------------------------------------------------
# 5. Répartition en fonction des métadonnées (JDD / cadres d'acquisition)
# ---------------------------------------------------------------------------

def q_tab_jdd():
    return _ids_query(
        """
        SELECT DISTINCT msaf.acquisition_framework_name AS "Cadre d'acquisition",
               msd.dataset_name AS "Jeu de données",
               msd.unique_dataset_id AS "UUID JDD",
               SUM(msd.nb_data) AS nb_data
        FROM grafana.mv_source_dataset msd
        LEFT JOIN grafana.mv_source_acquisition_framework msaf
               ON msaf.id_acquisition_framework = msd.id_acquisition_framework
              AND msaf.id_source_news = msd.id_source_news
        WHERE msd.id_source_news IN :ids AND msaf.id_source_news IN :ids
        GROUP BY msaf.acquisition_framework_name, msd.dataset_name, msd.unique_dataset_id
        ORDER BY 1, 2;
        """
    )


def q_tab_ca():
    return _ids_query(
        """
        SELECT DISTINCT unique_acquisition_framework_id AS "UUID",
               acquisition_framework_name AS "Cadre d'acquisition",
               SUM(nb_data) AS nb_data
        FROM grafana.mv_source_acquisition_framework
        WHERE id_source_news IN :ids
        GROUP BY acquisition_framework_name, unique_acquisition_framework_id
        ORDER BY acquisition_framework_name;
        """
    )


# ---------------------------------------------------------------------------
# 4. Répartition par groupe taxonomique
# ---------------------------------------------------------------------------

def q_tab_rang_tax():
    return _ids_query(
        """
        WITH data_tot AS (
            SELECT SUM(nb_data) AS tot FROM grafana.mv_source_niveau_taxonomique
        ),
        repartition_tot AS (
            SELECT nom_rang, SUM(nb_data) / data_tot.tot AS tot_part
            FROM grafana.mv_source_niveau_taxonomique, data_tot
            GROUP BY nom_rang, data_tot.tot
        ),
        data_tot_source AS (
            SELECT SUM(nb_data) AS source_tot
            FROM grafana.mv_source_niveau_taxonomique
            WHERE id_source_news IN :ids
        )
        SELECT mv.nom_rang AS "Rang",
               SUM(mv.nb_data) AS nb_data,
               SUM(mv.nb_data) / data_tot_source.source_tot AS part_data,
               repartition_tot.tot_part AS repartition_total
        FROM grafana.mv_source_niveau_taxonomique mv
        LEFT JOIN repartition_tot ON repartition_tot.nom_rang = mv.nom_rang
        CROSS JOIN data_tot_source
        WHERE mv.id_source_news IN :ids
        GROUP BY mv.nom_rang, data_tot_source.source_tot, repartition_tot.tot_part
        ORDER BY SUM(mv.nb_data) DESC;
        """
    )


def q_data_repartition_esp():
    return _ids_query(
        """
        SELECT group2_inpn AS groupe_taxo, COUNT(DISTINCT cd_ref) AS nb_esp
        FROM grafana.mv_source_detail
        WHERE id_source_news IN :ids AND id_rang = 'ES'
        GROUP BY group2_inpn
        ORDER BY group2_inpn;
        """
    )


def q_data_repartition_data():
    return _ids_query(
        """
        SELECT group2_inpn AS groupe_taxo, SUM(nb_data) AS nb_data
        FROM grafana.mv_source_detail
        WHERE id_source_news IN :ids AND id_rang = 'ES'
        GROUP BY group2_inpn
        ORDER BY group2_inpn;
        """
    )


# ---------------------------------------------------------------------------
# 2. Répartition temporelle
# ---------------------------------------------------------------------------

def q_data_year():
    return _ids_query(
        """
        SELECT annee AS an, SUM(nb_data) AS "Donnees"
        FROM grafana.mv_source_info_temporelle
        WHERE id_source_news IN :ids
        GROUP BY annee
        ORDER BY annee;
        """
    )


def q_data_month():
    return _ids_query(
        """
        SELECT CONCAT(annee, '-', LPAD(mois::text, 2, '0')) AS date2,
               concat(annee, '-', mois) AS date,
               mois, annee AS an,
               SUM(nb_data) AS "Donnees"
        FROM grafana.mv_source_info_temporelle
        WHERE id_source_news IN :ids
        AND annee >= 1600
        GROUP BY annee, mois
        ORDER BY annee, mois;        
        """
    )

def q_data_out():
    return _ids_query(
        """
        SELECT SUM(nb_data) AS "Donnees"
        FROM grafana.mv_source_info_temporelle
        WHERE id_source_news IN :ids
        AND annee < 1600
        GROUP BY annee, mois
        ORDER BY annee, mois;        
        """
    )


# ---------------------------------------------------------------------------
# 6. Validation des données
# ---------------------------------------------------------------------------

def q_data_valid():
    return _ids_query(
        """
        SELECT tn.label_default AS label_valid_status,
               COUNT(s.id_synthese) AS nb_data
        FROM gn_synthese.synthese s
        LEFT JOIN ref_nomenclatures.t_nomenclatures tn
               ON s.id_nomenclature_valid_status = tn.id_nomenclature
        WHERE concat(s.id_source, '_', s.id_import) IN :ids
        GROUP BY 1
        ORDER BY 1;
        """
    )


def q_data_validation():
    return _ids_query(
        """
        SELECT s.unique_id_sinp AS uuid,
               t.cd_ref,
               br.nom_rang AS rang,
               t.nom_vern,
               t.lb_nom,
               tn.label_default AS label_valid_status,
               v.validation_comment AS "Commentaire",
               (v.validation_date::date)::text AS "Date_commentaire"
        FROM gn_synthese.synthese s
        JOIN ref_nomenclatures.t_nomenclatures tn ON s.id_nomenclature_valid_status = tn.id_nomenclature
        JOIN taxonomie.taxref t ON s.cd_nom = t.cd_nom
        JOIN taxonomie.bib_taxref_rangs br ON t.id_rang = br.id_rang
        JOIN gn_commons.v_latest_validation v ON s.unique_id_sinp = v.uuid_attached_row
        WHERE concat(s.id_source, '_', s.id_import) IN :ids
          AND v.id_nomenclature_valid_status NOT IN (
              ref_nomenclatures.get_id_nomenclature('STATUT_VALID', '0'),
              ref_nomenclatures.get_id_nomenclature('STATUT_VALID', '1'),
              ref_nomenclatures.get_id_nomenclature('STATUT_VALID', '2')
          );
        """
    )


# ---------------------------------------------------------------------------
# 7. Analyse des doublons
# ---------------------------------------------------------------------------

def q_data_doublon():
    """Doublons potentiels *au sein* du lot fourni, avec latitude/longitude
    directement calculées côté SQL (évite le recours à un pipeline geopandas)."""
    return _ids_query(
        """
        WITH recent_data AS (
            SELECT s.id_synthese, s.id_dataset, s.id_source, s.cd_nom, s.observers,
                   s.id_nomenclature_sex, s.id_nomenclature_obs_technique,
                   s.count_max, s.count_min, s.id_nomenclature_life_stage,
                   s.date_min, s.date_max, s.the_geom_local
            FROM gn_synthese.synthese s
            WHERE concat(s.id_source, '_', s.id_import) IN :ids
        ),
        geom_normalisee AS (
            SELECT rd.*,
                 CASE
                        WHEN GeometryType(the_geom_local) = 'POINT'
                            THEN ST_Transform(ST_SnapToGrid(the_geom_local, 0.000001),4326)
                        WHEN GeometryType(the_geom_local) IN ('MULTIPOINT','LINESTRING','MULTILINESTRING','POLYGON','MULTIPOLYGON','GEOMETRYCOLLECTION')
                            THEN ST_Transform(ST_Centroid(ST_SnapToGrid(the_geom_local, 0.000001)),4326)
                 END AS geom
            FROM recent_data rd
        )
        SELECT rd.cd_nom, t.lb_nom, t.nom_vern,
               GeometryType(rd.the_geom_local) AS geom_type,
               ST_Y(rd.geom) AS lat, ST_X(rd.geom) AS lon,
               rd.observers, rd.id_nomenclature_sex, rd.id_nomenclature_obs_technique,
               rd.count_max, rd.count_min, rd.id_nomenclature_life_stage,
               (rd.date_min::date)::text AS date,
               COUNT(*) AS nb_data_similaire
        FROM geom_normalisee rd
        LEFT JOIN taxonomie.taxref t ON t.cd_nom = rd.cd_nom
        GROUP BY rd.cd_nom, t.lb_nom, t.nom_vern, rd.observers, rd.id_nomenclature_sex,
                 rd.id_nomenclature_obs_technique, rd.date_min, rd.count_max, rd.count_min,
                 rd.id_nomenclature_life_stage, GeometryType(rd.the_geom_local), rd.geom
        HAVING COUNT(*) > 1
        ORDER BY 14 DESC;
        """
    )


def q_source_doublon():
    """Doublons potentiels *entre* la source analysée et d'autres sources."""
    return _ids_query(
        f"""
        WITH recent_data AS (
            SELECT id_synthese, id_dataset, concat(s.id_source, '_', s.id_import) AS id_source_news,
                   cd_nom, observers, date_min, date_max, the_geom_local
            FROM gn_synthese.synthese s
            WHERE concat(s.id_source, '_', s.id_import) IN :ids
        )
        SELECT
            CASE WHEN s.id_source = {config.ID_SOURCE_IMPORT_MODULE}
                 THEN (ti.additional_data ->> 'desc_source')::text
                 ELSE ts.desc_source END AS "Nom_source",
            COUNT(DISTINCT s.id_synthese) AS "Nombre_donnees_dupliquees"
        FROM recent_data r
        JOIN gn_synthese.synthese s
              ON r.cd_nom = s.cd_nom
             AND r.date_min = s.date_min
             AND ST_DWithin(r.the_geom_local, s.the_geom_local, 1)
        JOIN gn_synthese.t_sources ts ON s.id_source = ts.id_source
        LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
        WHERE s.id_synthese <> r.id_synthese
          AND concat(s.id_source, '_', s.id_import) <> r.id_source_news
        GROUP BY CASE WHEN s.id_source = {config.ID_SOURCE_IMPORT_MODULE}
                      THEN (ti.additional_data ->> 'desc_source')::text
                      ELSE ts.desc_source END
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC;
        """
    )


# ---------------------------------------------------------------------------
# 3. Répartition spatiale
# ---------------------------------------------------------------------------

def q_data_geom_mesh():
    """Maillage M5 avec GeoJSON directement calculé côté PostGIS (pour Folium)."""
    return _ids_query(
        """
        SELECT id_area,
               ST_AsGeoJSON(geom_4326) AS geojson,
               SUM(nb_data) AS nb_data,
               MAX(cardinality(tab_lb_nom)) AS nb_esp
        FROM grafana.mv_source_geom_info
        WHERE id_source_news IN :ids
        GROUP BY id_area, geom_4326;
        """
    )


def q_data_hors_regions():
    return _ids_query(
        """
        SELECT s.id_synthese,
               ST_Y(ST_Transform(ST_Centroid(s.the_geom_local), 4326)) AS lat,
               ST_X(ST_Transform(ST_Centroid(s.the_geom_local), 4326)) AS lon,
               s.id_source, s.id_import, s.nom_cite, s.date_max::date AS date_max,
               s.observers
        FROM gn_synthese.synthese s
        LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
        WHERE NOT ST_DWithin(
                  ST_Centroid(s.the_geom_local),
                  (SELECT geom FROM ref_geo.l_areas la WHERE la.area_name ILIKE :region_pattern LIMIT 1),
                  5000)
          AND concat(s.id_source, '_', s.id_import) IN :ids;
        """
    ).bindparams(bindparam("region_pattern"))


def q_data_altitudes():
    return _ids_query(
        """
         SELECT --s.id_source, s.id_import,
               CASE
                   WHEN altitude_min < 0 THEN '< 0'
                   WHEN altitude_min < 40 THEN '0-40'
                   WHEN altitude_min < 250 THEN '40-250'
                   WHEN altitude_min < 500 THEN '250-500'
                   WHEN altitude_min < 750 THEN '500-750'
                   WHEN altitude_min < 1000 THEN '750-1000'
                   WHEN altitude_min < 1250 THEN '1000-1250'
                   WHEN altitude_min < 1500 THEN '1250-1500'
                   WHEN altitude_min < 1750 THEN '1500-1750'
                   WHEN altitude_min < 2000 THEN '1750-2000'
                   WHEN altitude_min < 2250 THEN '2000-2250'
                   WHEN altitude_min < 2500 THEN '2250-2500'
                   WHEN altitude_max < 2750 THEN '2500-2750'
                   WHEN altitude_max < 3000 THEN '2750-3000'
                   WHEN altitude_max < 3250 THEN '3000-3250'
                   WHEN altitude_max < 3500 THEN '3250-3500'
                   WHEN altitude_max < 3750 THEN '3500-3750'
                   WHEN altitude_max < 4000 THEN '3750-4000'
                   WHEN altitude_max < 4250 THEN '4000-4250'
                   WHEN altitude_max < 4500 THEN '4250-4500'
                   WHEN altitude_max < 4750 THEN '4500-4750'
                   WHEN altitude_max > 4750 THEN '> 4750'
                   WHEN altitude_min IS NULL OR altitude_max IS NULL THEN 'Sans donnees'
                   ELSE 'Autres'
               END AS classe_altitude,
               CASE
                   WHEN altitude_min < 0 THEN 0
                   WHEN altitude_min < 40 THEN 1
                   WHEN altitude_min < 250 THEN 2
                   WHEN altitude_min < 500 THEN 3
                   WHEN altitude_min < 750 THEN 4
                   WHEN altitude_min < 1000 THEN 5
                   WHEN altitude_min < 1250 THEN 6
                   WHEN altitude_min < 1500 THEN 7
                   WHEN altitude_min < 1750 THEN 8
                   WHEN altitude_min < 2000 THEN 9
                   WHEN altitude_min < 2250 THEN 10
                   WHEN altitude_min < 2500 THEN 11
                   WHEN altitude_max < 2750 THEN 12
                   WHEN altitude_max < 3000 THEN 13
                   WHEN altitude_max < 3250 THEN 14
                   WHEN altitude_max < 3500 THEN 15
                   WHEN altitude_max < 3750 THEN 16
                   WHEN altitude_max < 4000 THEN 17
                   WHEN altitude_max < 4250 THEN 18
                   WHEN altitude_max < 4500 THEN 19
                   WHEN altitude_max < 4750 THEN 20
                   WHEN altitude_max > 4750 THEN 21
                   WHEN altitude_min IS NULL OR altitude_max IS NULL THEN -1
                   ELSE -2
               END AS classe_altitude_order,
               CASE
                   WHEN s.altitude_min IS NULL OR s.altitude_max IS NULL THEN 'incorrect'
                   WHEN s.altitude_min < 40 OR s.altitude_max < 40 THEN 'incorrect'
                   WHEN s.altitude_min > 4750 OR s.altitude_max > 4750 THEN 'incorrect'
                   ELSE 'correct'
               END AS validite,
               COUNT(DISTINCT s.id_synthese) AS tot_data
        FROM gn_synthese.synthese s
        LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
        WHERE concat(s.id_source, '_', s.id_import) IN :ids
        GROUP BY  1,2,3
        ORDER BY 2 ASC;
        """
    )


def q_data_type_geom():
    return _ids_query(
        """
        SELECT s.id_source, s.id_import,
               CASE
                   WHEN ST_GeometryType(s.the_geom_local) IN ('ST_LineString', 'ST_MultiLineString') THEN 'Lignes'
                   WHEN ST_GeometryType(s.the_geom_local) IN ('ST_Polygon', 'ST_MultiPolygon') THEN 'Polygones'
                   WHEN ST_GeometryType(s.the_geom_local) IN ('ST_Point', 'ST_MultiPoint') THEN 'Points'
                   WHEN s.the_geom_local IS NULL THEN 'Sans geometrie'
                   ELSE 'Autre'
               END AS type_geom,
               COUNT(DISTINCT s.id_synthese) AS nb_data
        FROM gn_synthese.synthese s
        LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
        WHERE concat(s.id_source, '_', s.id_import) IN :ids
        GROUP BY s.id_source, s.id_import, 3;
        """
    )

def q_data_taille_geom():
    """Classes de taille (longueur/surface) des géométries linéaires et
    surfaciques — permet de repérer des géométries trop grossières
    (ex : donnée saisie à l'échelle de la maille plutôt qu'au point réel).
    Section 3."""
    seuil_long_m = config.SEUIL_LONGUEUR_ALERTE_KM * 1000
    seuil_surf_m2 = config.SEUIL_SURFACE_ALERTE_HA * 10000
    return _ids_query(
        f"""
        WITH geoms AS (
            SELECT
                CASE
                    WHEN ST_GeometryType(s.the_geom_local) IN ('ST_LineString','ST_MultiLineString') THEN 'Lignes'
                    WHEN ST_GeometryType(s.the_geom_local) IN ('ST_Polygon','ST_MultiPolygon') THEN 'Polygones'
                END AS type_geom,
                CASE
                    WHEN ST_GeometryType(s.the_geom_local) IN ('ST_LineString','ST_MultiLineString')
                        THEN ST_Length(s.the_geom_local)
                    WHEN ST_GeometryType(s.the_geom_local) IN ('ST_Polygon','ST_MultiPolygon')
                        THEN ST_Area(s.the_geom_local)
                END AS taille
            FROM gn_synthese.synthese s
            WHERE concat(s.id_source, '_', s.id_import) IN :ids
              AND ST_GeometryType(s.the_geom_local) IN
                  ('ST_LineString','ST_MultiLineString','ST_Polygon','ST_MultiPolygon')
        )
        SELECT
            type_geom,
            CASE
                WHEN type_geom = 'Lignes' AND taille < 100 THEN '< 100 m'
                WHEN type_geom = 'Lignes' AND taille < 1000 THEN '100 m - 1 km'
                WHEN type_geom = 'Lignes' AND taille < 5000 THEN '1 - 5 km'
                WHEN type_geom = 'Lignes' AND taille < {seuil_long_m} THEN '5 - {config.SEUIL_LONGUEUR_ALERTE_KM:g} km'
                WHEN type_geom = 'Lignes' THEN '> {config.SEUIL_LONGUEUR_ALERTE_KM:g} km'
                WHEN type_geom = 'Polygones' AND taille < 1000 THEN '< 0,1 ha'
                WHEN type_geom = 'Polygones' AND taille < 10000 THEN '0,1 - 1 ha'
                WHEN type_geom = 'Polygones' AND taille < 100000 THEN '1 - 10 ha'
                WHEN type_geom = 'Polygones' AND taille < 1000000 THEN '10 - 100 ha'
                WHEN type_geom = 'Polygones' AND taille < {seuil_surf_m2} THEN '100 - {config.SEUIL_SURFACE_ALERTE_HA:g} ha'
                WHEN type_geom = 'Polygones' THEN '> {config.SEUIL_SURFACE_ALERTE_HA:g} ha'
            END AS classe_taille,
            CASE
                WHEN type_geom = 'Lignes' AND taille < 100 THEN 1
                WHEN type_geom = 'Lignes' AND taille < 1000 THEN 2
                WHEN type_geom = 'Lignes' AND taille < 5000 THEN 3
                WHEN type_geom = 'Lignes' AND taille < {seuil_long_m} THEN 4
                WHEN type_geom = 'Lignes' THEN 5
                WHEN type_geom = 'Polygones' AND taille < 1000 THEN 1
                WHEN type_geom = 'Polygones' AND taille < 10000 THEN 2
                WHEN type_geom = 'Polygones' AND taille < 100000 THEN 3
                WHEN type_geom = 'Polygones' AND taille < 1000000 THEN 4
                WHEN type_geom = 'Polygones' AND taille < {seuil_surf_m2} THEN 5
                WHEN type_geom = 'Polygones' THEN 6
            END AS classe_order,
            (taille >= CASE WHEN type_geom = 'Lignes' THEN {seuil_long_m} ELSE {seuil_surf_m2} END) AS imprecise,
            COUNT(*) AS nb_data
        FROM geoms
        WHERE type_geom IS NOT NULL
        GROUP BY type_geom, classe_taille, classe_order, imprecise
        ORDER BY type_geom, classe_order;
        """
    )


# ---------------------------------------------------------------------------
# 8. Espèces Exotiques Envahissantes (EEE)
# ---------------------------------------------------------------------------

def q_data_eee_synthese():
    """Tableau de synthèse EEE (agrégé, sans géométrie)."""
    return _ids_query(
        """
        WITH secteurs AS (
            SELECT 'RA'::text AS secteur, geom FROM ref_geo.l_areas
             WHERE id_type = 26 AND area_name IN ('Ain', 'Ardeche', 'Drome', 'Haute-Savoie', 'Isere', 'Loire', 'Rhone', 'Savoie')
            UNION ALL
            SELECT 'Au', geom FROM ref_geo.l_areas
             WHERE id_type = 26 AND area_name IN ('Allier', 'Haute-Loire', 'Puy-de-Dome', 'Cantal')
            UNION ALL
            SELECT 'AuRA', geom FROM ref_geo.l_areas
             WHERE area_name ILIKE :region_pattern
        ),
        donnees_eee AS (
            SELECT t.nom_vern, t.lb_nom, t.cd_ref, eee.presence,
                   s.date_min, s.date_max, s.count_min, s.count_max,
                   s.id_synthese, s.the_geom_local
            FROM grafana.t_orb_eee_aura_2025 eee
            LEFT JOIN taxonomie.taxref t ON eee.cd_nom = t.cd_nom
            JOIN gn_synthese.synthese s ON t.cd_ref = s.cd_nom
            WHERE concat(s.id_source, '_', s.id_import) IN :ids
        ),
        donnees_secteurs AS (
            SELECT d.*, st.secteur AS secteur_spatial
            FROM donnees_eee d
            LEFT JOIN secteurs st ON ST_Intersects(d.the_geom_local, st.geom)
        )
        SELECT nom_vern, lb_nom, cd_ref, presence AS presence_connue_orb,
               string_agg(DISTINCT secteur_spatial, ', ') FILTER (WHERE secteur_spatial != 'AuRA') AS secteur_obs,
               CASE
                   WHEN presence ILIKE 'AuRA' THEN 'Non'
                   WHEN presence = 'RA' AND SUM(CASE WHEN secteur_spatial = 'Au' THEN 1 ELSE 0 END) > 0 THEN 'Oui'
                   WHEN presence = 'Au' AND SUM(CASE WHEN secteur_spatial = 'RA' THEN 1 ELSE 0 END) > 0 THEN 'Oui'
                   WHEN presence = 'Absente' AND COUNT(id_synthese) > 0 THEN 'Oui'
                   ELSE 'Non'
               END AS nouvelle_presence,
               COUNT(DISTINCT id_synthese) AS nb_donnees,
               MIN(date_min) AS premiere_observation,
               MAX(date_max) AS derniere_observation,
               MIN(count_min) AS effectif_min,
               MAX(count_max) AS effectif_max
        FROM donnees_secteurs
        GROUP BY nom_vern, lb_nom, cd_ref, presence
        ORDER BY nb_donnees DESC;
        """
    ).bindparams(bindparam("region_pattern"))


def q_data_eee_points():
    """Points individuels d'observation EEE (pour la carte, sans agrégation
    géométrique préalable — plus simple et plus fidèle que le
    st_union()+st_cast('POINT') utilisé côté R)."""
    return _ids_query(
        """
        WITH secteurs AS (
            SELECT 'RA'::text AS secteur, geom FROM ref_geo.l_areas
             WHERE id_type = 26 AND area_name IN ('Ain', 'Ardeche', 'Drome', 'Haute-Savoie', 'Isere', 'Loire', 'Rhone', 'Savoie')
            UNION ALL
            SELECT 'Au', geom FROM ref_geo.l_areas
             WHERE id_type = 26 AND area_name IN ('Allier', 'Haute-Loire', 'Puy-de-Dome', 'Cantal')
            UNION ALL
            SELECT 'AuRA', geom FROM ref_geo.l_areas
             WHERE area_name ILIKE :region_pattern
        ),
        donnees_eee AS (
            SELECT t.nom_vern, t.lb_nom, t.cd_ref, eee.presence, s.id_synthese, s.the_geom_local
            FROM grafana.t_orb_eee_aura_2025 eee
            LEFT JOIN taxonomie.taxref t ON eee.cd_nom = t.cd_nom
            JOIN gn_synthese.synthese s ON t.cd_ref = s.cd_nom
            WHERE concat(s.id_source, '_', s.id_import) IN :ids
        ),
        donnees_secteurs AS (
            SELECT d.*, st.secteur AS secteur_spatial
            FROM donnees_eee d
            LEFT JOIN secteurs st ON ST_Intersects(d.the_geom_local, st.geom)
        )
        SELECT nom_vern, lb_nom, cd_ref, presence AS presence_connue_orb,
               string_agg(DISTINCT secteur_spatial, ', ') FILTER (WHERE secteur_spatial != 'AuRA') AS secteur_obs,
               ST_Y(ST_Transform(ST_Centroid(the_geom_local), 4326)) AS lat,
               ST_X(ST_Transform(ST_Centroid(the_geom_local), 4326)) AS lon
        FROM donnees_secteurs
        GROUP BY nom_vern, lb_nom, cd_ref, presence, the_geom_local;
        """
    ).bindparams(bindparam("region_pattern"))

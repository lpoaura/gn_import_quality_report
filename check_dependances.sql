-- =============================================================================
-- check_dependances.sql
-- =============================================================================
-- À exécuter sur une nouvelle instance AVANT le premier `python main.py`,
-- pour vérifier en un coup d'œil la présence de tous les objets requis par
--
-- Lecture du résultat : la colonne "statut" indique OK / MANQUANT.
-- =============================================================================

WITH objets_requis (schema_objet, nom_objet, type_objet, origine, criticite) AS (
    VALUES
    -- Section 0 : orchestration
    ('gn_imports',        'v_c_rapport_generated',            'vue',   'Spécifique projet',        'Bloquant'),
    -- Section 1 : vues matérialisées grafana.mv_*
    ('grafana',           'mv_source_dataset',                'mv',    'Spécifique projet (creation_mv)', 'Bloquant'),
    ('grafana',           'mv_source_detail',                 'mv',    'Spécifique projet (creation_mv)', 'Bloquant'),
    ('grafana',           'mv_source_acquisition_framework',  'mv',    'Spécifique projet (creation_mv)', 'Majeur'),
    ('grafana',           'mv_source_niveau_taxonomique',     'mv',    'Spécifique projet (creation_mv)', 'Majeur'),
    ('grafana',           'mv_source_info_temporelle',        'mv',    'Spécifique projet (creation_mv)', 'Majeur'),
    ('grafana',           'mv_source_geom_info',              'mv',    'Spécifique projet (creation_mv)', 'Majeur'),
    -- Section 2 : core GeoNature (tables/vues)
    ('gn_synthese',       'synthese',                         'table', 'Core',                     'Bloquant'),
    ('gn_synthese',       't_sources',                        'table', 'Core',                     'Mineur'),
    ('taxonomie',         'taxref',                           'table', 'Core',                     'Bloquant'),
    ('taxonomie',         'bib_taxref_rangs',                 'table', 'Core',                     'Mineur'),
    ('ref_geo',           'l_areas',                          'table', 'Core',                     'Majeur'),
    ('ref_nomenclatures', 't_nomenclatures',                  'table', 'Core',                     'Majeur'),
    -- Section 3 : modules optionnels
    ('gn_imports',        't_imports',                        'table', 'Module Import',            'Majeur'),
    ('gn_commons',        'v_latest_validation',               'vue',   'Module Validation',        'Mineur'),
    -- Section 4 : spécifique projet
    ('grafana',           't_orb_eee_aura_2025',              'table', 'Spécifique projet',        'Mineur')
)
SELECT
    o.schema_objet,
    o.nom_objet,
    o.type_objet,
    o.origine,
    o.criticite,
    CASE
        WHEN o.type_objet = 'mv' AND EXISTS (
            SELECT 1 FROM pg_matviews m
            WHERE m.schemaname = o.schema_objet AND m.matviewname = o.nom_objet
        ) THEN 'OK'
        WHEN o.type_objet IN ('table', 'vue') AND EXISTS (
            SELECT 1 FROM information_schema.tables t
            WHERE t.table_schema = o.schema_objet AND t.table_name = o.nom_objet
        ) THEN 'OK'
        ELSE 'MANQUANT'
    END AS statut
FROM objets_requis o
ORDER BY
    CASE o.criticite WHEN 'Bloquant' THEN 0 WHEN 'Majeur' THEN 1 ELSE 2 END,
    o.schema_objet, o.nom_objet;

-- Vérification séparée de la fonction utilisée (ref_nomenclatures.get_id_nomenclature)
SELECT
    'ref_nomenclatures' AS schema_objet,
    'get_id_nomenclature' AS nom_objet,
    'fonction' AS type_objet,
    'Core' AS origine,
    'Majeur' AS criticite,
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'ref_nomenclatures' AND p.proname = 'get_id_nomenclature'
    ) THEN 'OK' ELSE 'MANQUANT' END AS statut;



-- =============================================================================
-- Création des VM et VUE 
-- =============================================================================
-- À exécuter si les vues matérialisées et la vue de synthèse n'existent pas encore.
-- =============================================================================

-- gn_imports.v_c_rapport_generated 
CREATE OR REPLACE VIEW gn_imports.v_c_rapport_generated AS
 WITH prep AS (
         SELECT ti.additional_data ->> 'desc_source'::text AS desc_source,
            lower(replace(replace(replace(replace(ti.additional_data ->> 'desc_source'::text, ' '::text, '_'::text), '/'::text, '_'::text), '['::text, ''::text), ']'::text, ''::text)) AS nom_fichier,
            max(ti.date_create_import) AS last_date,
            string_agg(DISTINCT concat('''', s.id_source, '_', ti.id_import::text, ''''), ', '::text) AS list_import
           FROM gn_synthese.synthese s
             LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
          WHERE ti.additional_data IS NOT NULL AND (ti.additional_data ->> 'create_rapport'::text) = 'true'::text
          GROUP BY (ti.additional_data ->> 'desc_source'::text)
        UNION
         SELECT ts.desc_source,
            lower(replace(replace(replace(replace(ts.desc_source, ' '::text, '_'::text), '/'::text, '_'::text), '['::text, ''::text), ']'::text, ''::text)) AS nom_fichier,
            max(ts.meta_update_date) AS last_date,
            string_agg(DISTINCT concat('''', s.id_source, '_', ''''), ', '::text) AS list_import
           FROM gn_synthese.synthese s
             LEFT JOIN gn_synthese.t_sources ts ON s.id_source = ts.id_source
          WHERE ts.additional_data IS NOT NULL AND (ts.additional_data ->> 'create_rapport'::text) = 'true'::text
          GROUP BY ts.desc_source
        )
 SELECT desc_source,
    nom_fichier,
    last_date,
    list_import,
    concat('https://XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX', regexp_replace(translate(lower(unaccent(nom_fichier)), ' '::text, '_'::text), '[^a-z0-9_]'::text, ''::text, 'g'::text), '.html') AS url
   FROM prep;

-- grafana
CREATE SCHEMA IF NOT EXISTS grafana;

--grafana.mv_source_acquisition_framework
CREATE MATERIALIZED VIEW grafana.mv_source_acquisition_framework AS
 SELECT DISTINCT s.id_source,
    s.id_import,
    concat(s.id_source, '_', s.id_import) AS id_source_news,
    ca.acquisition_framework_name,
    ca.acquisition_framework_desc,
    ca.unique_acquisition_framework_id,
    ca.id_acquisition_framework,
    count(s.id_synthese) AS nb_data
   FROM gn_synthese.synthese s
     JOIN gn_meta.t_datasets td ON td.id_dataset = s.id_dataset
     LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
     JOIN gn_meta.t_acquisition_frameworks ca ON td.id_acquisition_framework = ca.id_acquisition_framework
  GROUP BY s.id_source, s.id_import, (concat(s.id_source, '_', s.id_import)), ca.acquisition_framework_name, ca.acquisition_framework_desc, ca.unique_acquisition_framework_id, ca.id_acquisition_framework;


--grafana.mv_source_dataset
CREATE MATERIALIZED VIEW grafana.mv_source_dataset AS
 SELECT DISTINCT s.id_source,
    s.id_import,
    concat(s.id_source, '_', s.id_import) AS id_source_news,
    td.id_acquisition_framework,
    td.unique_dataset_id,
    td.dataset_name,
    td.dataset_desc,
    td.id_dataset,
    count(s.id_synthese) AS nb_data,
    'https://XXXXXXXXXXXXXXXXX'::text || s.id_dataset AS url_jdd,
    (td.additional_data ->> 'to_pole_vert'::text)::boolean AS pole_vert,
    (td.additional_data ->> 'to_pole_inv'::text)::boolean AS pole_inv,
    (td.additional_data ->> 'to_pifh'::text)::boolean AS pifh
   FROM gn_synthese.synthese s
     JOIN gn_meta.t_datasets td ON td.id_dataset = s.id_dataset
     LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
  GROUP BY s.id_source, s.id_import, td.unique_dataset_id, (concat(s.id_source, '_', s.id_import)), td.id_acquisition_framework, td.dataset_name, td.dataset_desc, td.id_dataset, ('https://grafana.aura.local/d/b2af1a26-5950-473b-9f80-8454f656fe59/geonature-jeux-de-donnees?orgId=1&var-dataset'::text || s.id_dataset);


-- grafana.mv_source_detail
CREATE MATERIALIZED VIEW grafana.mv_source_detail AS
 SELECT s.id_source,
    s.id_import,
    concat(s.id_source, '_', s.id_import) AS id_source_news,
    ts.name_source,
    ts.desc_source,
        CASE
            WHEN s.id_source = XXXX THEN ti.additional_data ->> 'desc_source'::text
            ELSE ts.desc_source
        END AS desc_source_final,
    count(s.id_synthese) AS nb_data,
    t.cd_ref,
    t.id_rang,
    t.group2_inpn
   FROM gn_synthese.synthese s
     JOIN taxonomie.taxref t ON t.cd_nom = s.cd_nom
     JOIN gn_synthese.t_sources ts ON s.id_source = ts.id_source
     LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
  GROUP BY s.id_source, s.id_import, (concat(s.id_source, '_', s.id_import)), ts.name_source, ts.desc_source, t.cd_ref, t.id_rang, t.group2_inpn, (
        CASE
            WHEN s.id_source = XXXX THEN ti.additional_data ->> 'desc_source'::text
            ELSE ts.desc_source
        END);


-- grafana.mv_source_geom_info
CREATE MATERIALIZED VIEW grafana.mv_source_geom_info AS
 SELECT la.id_area,
    la.geom_4326,
    s.id_source,
    s.id_import,
    concat(s.id_source, '_', s.id_import) AS id_source_news,
    count(DISTINCT s.id_synthese) AS nb_data,
    array_agg(DISTINCT t.lb_nom) AS tab_lb_nom
   FROM gn_synthese.synthese s
     LEFT JOIN taxonomie.taxref t ON t.cd_nom = s.cd_nom
     LEFT JOIN gn_synthese.cor_area_synthese cas ON cas.id_synthese = s.id_synthese
     LEFT JOIN ref_geo.l_areas la ON la.id_area = cas.id_area
     LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
  WHERE la.id_type = ref_geo.get_id_area_type('M5'::character varying)
  GROUP BY la.id_area, la.geom_4326, s.id_source, s.id_import, (concat(s.id_source, '_', s.id_import));


-- grafana.mv_source_info_temporelle
CREATE MATERIALIZED VIEW grafana.mv_source_info_temporelle AS
 SELECT s.id_source,
    s.id_import,
    concat(s.id_source, '_', s.id_import) AS id_source_news,
    count(s.id_synthese) AS nb_data,
    EXTRACT(year FROM s.date_min) AS annee,
    EXTRACT(month FROM s.date_min) AS mois
   FROM gn_synthese.synthese s
     JOIN taxonomie.taxref t ON t.cd_nom = s.cd_nom
     LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
  GROUP BY s.id_source, s.id_import, (concat(s.id_source, '_', s.id_import)), (EXTRACT(year FROM s.date_min)), (EXTRACT(month FROM s.date_min));


--grafana.mv_source_niveau_taxonomique
CREATE MATERIALIZED VIEW grafana.mv_source_niveau_taxonomique AS
 SELECT s.id_source,
    s.id_import,
    concat(s.id_source, '_', s.id_import) AS id_source_news,
    bib.nom_rang,
    count(s.id_synthese) AS nb_data
   FROM gn_synthese.synthese s
     JOIN taxonomie.taxref t ON t.cd_nom = s.cd_nom
     JOIN taxonomie.bib_taxref_rangs bib ON bib.id_rang = t.id_rang::bpchar
     LEFT JOIN gn_imports.t_imports ti ON s.id_import = ti.id_import
  GROUP BY s.id_source, s.id_import, (concat(s.id_source, '_', s.id_import)), bib.nom_rang;


  -- gn_commons.v_latest_validation 
CREATE OR REPLACE VIEW gn_commons.v_latest_validation AS
 SELECT v.id_validation,
    v.uuid_attached_row,
    v.id_nomenclature_valid_status,
    v.validation_auto,
    v.id_validator,
    v.validation_comment,
    v.validation_date
   FROM gn_commons.t_validations v
     JOIN ( SELECT t_validations.uuid_attached_row,
            max(t_validations.validation_date) AS max_date
           FROM gn_commons.t_validations
          GROUP BY t_validations.uuid_attached_row) last_val ON v.uuid_attached_row = last_val.uuid_attached_row AND v.validation_date = last_val.max_date;


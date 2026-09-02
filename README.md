# Rapport Automatisé des Données importées

Génération pour chaque source/JDD importé dans GeoNature, une page HTML de synthèse
(informations générales, répartitions temporelle/spatiale/taxonomique,
métadonnées, validation, doublons, EEE) avec graphiques interactifs,
cartographies web et tableaux triables/filtrables.


## Architecture

```
rapport_python/
├── config.py              # Variables d'environnement, constantes, chemins
├── logging_config.py      # Logging console + fichier tournant
├── db.py                  # Connexion PostgreSQL/PostGIS (SQLAlchemy)
├── queries.py              # Toutes les requêtes SQL, paramétrées (IN :ids)
├── data_service.py         # Exécute les requêtes -> objet SourceReportData
├── charts.py               # Graphiques interactifs Plotly
├── maps.py                  # Cartographies web Folium/Leaflet
├── tables.py                # Tableaux HTML statiques et DataTables
├── formatting.py            # Formats nombres/%, noms de fichiers, CSV base64
├── report_generator.py      # Assemble tout -> rend le template -> écrit le .html
├── main.py                  # Orchestration complète (CLI)
├── test_render_demo.py      # Génère un rapport de démo SANS base de données
├── templates/
│   └── report_template.html # Template Jinja2 (structure des 8 sections)
├── static/
│   └── report.css           # Feuille de style (injectée en ligne dans le HTML)
├── requirements.txt
└── .env.example
```

1. `main.py` rafraîchit les vues matérialisées `grafana.mv_*`
2. Récupère la liste des sources à traiter depuis
   `gn_imports.v_c_rapport_generated` (`desc_source`, `nom_fichier`, `list_import`)
3. Pour chaque source : `data_service.load_source_data()` exécute toutes les
   requêtes, `report_generator.generate_report()` construit les graphiques/
   cartes/tableaux et rend `report_template.html` en un fichier HTML autonome
   (CSS et JS embarqués ou chargés depuis un CDN, aucune dépendance externe au
   moment de l'ouverture du fichier hormis les CDN JS pour l'interactivité)


## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis éditer les identifiants de connexion
```

## Utilisation

```bash
# Génération complète (toutes les sources de gn_imports.v_c_rapport_generated)
python main.py

# Ne générer que les sources dont le nom contient un texte donné
python main.py --source-filter "Cantal"

# Développement : sans rafraîchir les vues matérialisées, logs en DEBUG
python main.py --skip-refresh --log-level DEBUG

# Prévisualiser le rendu SANS base de données (données factices)
python test_render_demo.py
```

Les rapports sont écrits dans `OUTPUT_DIR` (`./output` par défaut), un fichier
`.html` autonome par source, nommé d'après `nom_fichier`.


## Dépendances principales

`SQLAlchemy`, `psycopg2-binary`, `pandas`, `plotly`, `folium`, `branca`,
`Jinja2`, `Unidecode`, `python-dotenv` — voir `requirements.txt`.


## Inventaire des dépendances SQL du rapport

Ce document liste tous les objets PostgreSQL/PostGIS (tables, vues, vues
matérialisées, fonctions) sollicités par `queries.py`, avec leur origine
probable et leur niveau de criticité pour le bon fonctionnement du rapport.

Vous pouvez retrouver dans le fichier `check_dependances.sql` un requêtes
permettant de vérifier la présences/absences des tables, vues, vues matérialisées.
Puis l'ensembles des requêtes pour créer ses vues et vues matérialisées.

Légende **Origine** :
- 🟦 **Core GeoNature** : fait partie du socle GeoNature standard (existe
  normalement sur toute instance à jour).
- 🟨 **Module optionnel GeoNature** : fourni par un module officiel
  (Import, Validation…) mais qui doit être installé/activé.
- 🟥 **Spécifique projet (ORB AuRA)** : objet créé pour ce projet, à recréer
  manuellement sur toute nouvelle instance.

Légende **Criticité** :
- 🔴 **Bloquant** : son absence empêche la génération du rapport
  (`main.py` s'arrête, ou la source n'est jamais identifiée).
- 🟠 **Majeur** : son absence vide une section entière du rapport (grâce au
  `try/except` de `_safe_fetch`, ça ne casse rien, mais l'info manque).
- 🟢 **Mineur** : n'affecte qu'un sous-bloc optionnel (`show_xxx = False`).

### 0. Orchestration (liste des sources à traiter)

| Objet | Type | Origine | Utilisé par | Criticité |
|---|---|---|---|---|
| `gn_imports.v_c_rapport_generated` (configurable via `SOURCE_LIST_VIEW`) | Vue | 🟥 Spécifique projet | `q_liste_rapports` (`main.py`) | 🔴 Bloquant — sans elle, `main.py` ne trouve aucune source à traiter |

### 1. Vues matérialisées `grafana.mv_*` (rafraîchies avant chaque run)

| Objet | Type | Origine | Utilisé par | Section rapport | Criticité |
|---|---|---|---|---|---|
| `grafana.mv_source_dataset` | Vue matérialisée | 🟥 Spécifique projet | `q_nb_obs`, `q_nb_jdd`, `q_nb_ca`, `q_tab_jdd` | 1, 5 | 🔴 Bloquant (KPI principaux) |
| `grafana.mv_source_detail` | Vue matérialisée | 🟥 Spécifique projet | `q_nb_taxon`, `q_nb_esp`, `q_data_repartition_esp`, `q_data_repartition_data` | 1, 4 | 🔴 Bloquant (KPI principaux) |
| `grafana.mv_source_acquisition_framework` | Vue matérialisée | 🟥 Spécifique projet | `q_tab_jdd` (jointure), `q_tab_ca` | 5 | 🟠 Majeur |
| `grafana.mv_source_niveau_taxonomique` | Vue matérialisée | 🟥 Spécifique projet | `q_tab_rang_tax` | 4 | 🟠 Majeur |
| `grafana.mv_source_info_temporelle` | Vue matérialisée | 🟥 Spécifique projet | `q_data_year`, `q_data_month`, `q_data_out` | 2 | 🟠 Majeur |
| `grafana.mv_source_geom_info` | Vue matérialisée | 🟥 Spécifique projet | `q_data_geom_mesh` | 3 (carte maillage) | 🟠 Majeur |

> Ces 6 VM sont déjà couvertes par `SQL/creation_mv/` (mentionné dans le
> README) — **ne pas dupliquer**, seulement vérifier leur présence sur la
> nouvelle instance.

### 2. Tables / vues core GeoNature

| Objet | Type | Origine | Utilisé par | Criticité |
|---|---|---|---|---|
| `gn_synthese.synthese` | Table | 🟦 Core | `q_data_valid`, `q_data_validation`, `q_data_doublon`, `q_source_doublon`, `q_data_hors_regions`, `q_data_altitudes`, `q_data_type_geom`, `q_data_eee_synthese`, `q_data_eee_points` | 🔴 Bloquant (table centrale GeoNature) |
| `gn_synthese.t_sources` | Table | 🟦 Core | `q_source_doublon` | 🟢 Mineur (section doublons inter-sources) |
| `taxonomie.taxref` | Table | 🟦 Core (référentiel TaxRef) | `q_data_validation`, `q_data_doublon`, `q_data_eee_synthese`, `q_data_eee_points` | 🔴 Bloquant |
| `taxonomie.bib_taxref_rangs` | Table | 🟦 Core | `q_data_validation` | 🟢 Mineur |
| `ref_geo.l_areas` | Table | 🟦 Core (référentiel géo) | `q_data_hors_regions`, `q_data_eee_synthese`, `q_data_eee_points` | 🟠 Majeur — dépend aussi du bon peuplement des départements/région (`REGION_NAME_PATTERN`, `id_type = 26`) |
| `ref_nomenclatures.t_nomenclatures` | Table | 🟦 Core | `q_data_valid`, `q_data_validation` | 🟠 Majeur |
| `ref_nomenclatures.get_id_nomenclature(mnemonique, cd_nomenclature)` | Fonction | 🟦 Core | `q_data_validation` | 🟠 Majeur |

### 3. Modules optionnels GeoNature

| Objet | Type | Origine | Utilisé par | Criticité |
|---|---|---|---|---|
| `gn_imports.t_imports` | Table | 🟨 Module Import | `q_source_doublon`, `q_data_hors_regions`, `q_data_altitudes`, `q_data_type_geom` | 🟠 Majeur — nécessite le module Import activé, et surtout **`ID_SOURCE_IMPORT_MODULE`** (config) correctement réglé pour lire `additional_data->>'desc_source'` |
| `gn_commons.v_latest_validation` | Vue | 🟨 Module Validation | `q_data_validation` | 🟢 Mineur (si absent, section 6 « Données à revoir » reste vide, `show_validation=False`) |

### 4. Objets spécifiques au projet (à recréer sur toute nouvelle instance)

| Objet | Type | Origine | Utilisé par | Section | Criticité |
|---|---|---|---|---|---|
| `grafana.t_orb_eee_aura_2025` | Table | 🟥 Spécifique projet (référentiel EEE ORB AuRA, secteurs de présence connue) | `q_data_eee_synthese`, `q_data_eee_points` | 8 (EEE) | 🟢 Mineur — si absente, la section EEE est vide, mais **attention** : `q_data_eee_synthese`/`q_data_eee_points` utilisent aussi `EEE_SOURCE_IDS` (config), une liste d'imports **fixe**, indépendante de la source traitée — à revalider par instance |
| `gn_imports.v_c_rapport_generated` | Vue | 🟥 Spécifique projet | voir section 0 | — | 🔴 Bloquant |





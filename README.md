# Rapport Automatisé des Données importées — version Python

Réécriture en Python du pipeline R (`RScripts/` + `SQL/creation_mv`) qui génère,
pour chaque source/JDD importé dans GeoNature, une page HTML de synthèse
(informations générales, répartitions temporelle/spatiale/taxonomique,
métadonnées, validation, doublons, EEE) avec graphiques interactifs,
cartographies web et tableaux triables/filtrables.

Le SQL de création des vues matérialisées (`SQL/creation_mv`) n'a **pas** été
modifié : il reste le même, ces vues sont utilisées telles quelles par le
Python (`grafana.mv_*`).

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

Le flux général reproduit `traitement_analyses.R` :

1. `main.py` rafraîchit les vues matérialisées `grafana.mv_*`
2. Récupère la liste des sources à traiter depuis
   `gn_imports.v_c_rapport_generated` (`desc_source`, `nom_fichier`, `list_import`)
3. Pour chaque source : `data_service.load_source_data()` exécute toutes les
   requêtes, `report_generator.generate_report()` construit les graphiques/
   cartes/tableaux et rend `report_template.html` en un fichier HTML autonome
   (CSS et JS embarqués ou chargés depuis un CDN, aucune dépendance externe au
   moment de l'ouverture du fichier hormis les CDN JS pour l'interactivité)

Contrairement au script R, une erreur sur **une** source (table absente, JDD
mal formé, etc.) est journalisée et n'interrompt pas la génération des autres
rapports (`try/except` par requête dans `data_service._safe_fetch`, et par
rapport dans `main.py`).

## Correspondance R → Python

| R (avant)                                   | Python (après)                                   |
|----------------------------------------------|---------------------------------------------------|
| `RPostgreSQL` / `DBI`                        | `SQLAlchemy` + `psycopg2`                          |
| `dbGetQuery(conn, sql_concatene)`            | `pandas.read_sql(text(sql), conn, params=...)`     |
| Concaténation de `list_id` dans le SQL       | Bind parameter `IN :ids` (expanding), sans injection SQL |
| `dplyr` / `tidyverse`                        | `pandas`                                            |
| `plotly` (R)                                 | `plotly` (Python), `fig.to_html(...)`               |
| `leaflet`                                    | `folium` (+ `branca` pour les échelles de couleur)  |
| `sf` / `st_read`                              | Géométrie récupérée en GeoJSON / lat-lon directement via PostGIS (`ST_AsGeoJSON`, `ST_X`, `ST_Y`) — pas de dépendance GDAL/geopandas |
| `kableExtra::kable_styling()`                 | `tables.render_static_table()`                      |
| `DT::datatable()`                             | `tables.render_interactive_table()` (DataTables.js) |
| `base64enc::base64encode()`                    | `formatting.csv_download_link()`                    |
| `stringi::stri_trans_general()` + `gsub()`     | `formatting.sanitize_filename()` (Unidecode + regex)|
| `rmarkdown::render(rapport.Rmd, params=...)`   | `report_generator.generate_report()` + Jinja2       |
| `print()` / `cat()`                            | module `logging` (console + fichier tournant, niveaux) |
| Script arrêté à la première erreur              | Erreurs journalisées, traitement des sources suivantes poursuivi |

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
`.html` autonome par source, nommé d'après `nom_fichier` translittéré et
nettoyé (accents supprimés, espaces → `_`).

## Points de vigilance conservés du script R d'origine

- **`ID_SOURCE_IMPORT_MODULE`** (`config.py` / `.env`, défaut `7087`) : id de
  la source du module d'import de GeoNature sur votre instance, utilisé pour
  lire `additional_data->>'desc_source'` dans `gn_imports.t_imports`. À adapter
  impérativement à votre configuration.
- **`EEE_SOURCE_IDS`** : liste fixe d'`id_source_news` utilisée pour la
  synthèse EEE (section 8), reprise telle quelle du `rapport.Rmd` d'origine
  (indépendante de la source en cours de traitement). Externalisée en config
  pour rester ajustable sans toucher au code.
- La table `grafana.t_orb_eee_aura_2025` (EEE autorisées en AuRA) doit exister,
  comme dans la version R.

## Dépendances principales

`SQLAlchemy`, `psycopg2-binary`, `pandas`, `plotly`, `folium`, `branca`,
`Jinja2`, `Unidecode`, `python-dotenv` — voir `requirements.txt`.

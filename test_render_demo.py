"""
test_render_demo.py
====================
Script de démonstration/validation : construit un jeu de données factice
(sans connexion BDD) reproduisant la forme des données réelles, et exécute
la chaîne complète charts -> maps -> tables -> template Jinja2, afin de
vérifier que le rendu HTML fonctionne de bout en bout.

Ce script n'est PAS destiné à la production : il sert uniquement à valider
`report_generator._build_context` et le template hors ligne.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from data_service import SourceReportData
from logging_config import setup_logging
from report_generator import _build_context, _jinja_env
from config import config

logger = setup_logging()

# -- Construction d'un jeu de données factice --------------------------------

data = SourceReportData(nom_source="Association Naturaliste de Test", list_id=["7087_999"])

data.nb_obs = 128_430
data.nb_taxon = 842
data.nb_esp = 731
data.nb_jdd = 6
data.nb_ca = 2

data.tab_ca = pd.DataFrame({
    "UUID": ["uuid-ca-1", "uuid-ca-2"],
    "Cadre d'acquisition": ["Suivi naturaliste régional", "Programme EEE 2025"],
    "nb_data": [98230, 30200],
})

data.tab_jdd = pd.DataFrame({
    "Cadre d'acquisition": ["Suivi naturaliste régional"] * 2 + ["Programme EEE 2025"],
    "Jeu de données": ["Observations printemps", "Observations automne", "Suivi écrevisses"],
    "UUID JDD": ["uuid-jdd-1", "uuid-jdd-2", "uuid-jdd-3"],
    "nb_data": [45000, 53230, 30200],
})

data.tab_rang_tax = pd.DataFrame({
    "Rang": ["Espèce", "Genre", "Famille"],
    "nb_data": [120000, 6000, 2430],
    "part_data": [0.934, 0.047, 0.019],
    "repartition_total": [0.912, 0.06, 0.028],
})

data.data_year = pd.DataFrame({"an": [2021, 2022, 2023, 2024, 2025], "Donnees": [12000, 18500, 24000, 35400, 38530]})

mois = pd.date_range("2024-01-01", periods=18, freq="MS")
data.data_month = pd.DataFrame({
    "date2": mois,
    "date": [d.strftime("%Y-%m") for d in mois],
    "mois": [d.month for d in mois],
    "an": [d.year for d in mois],
    "Donnees": [800 + 60 * i for i in range(len(mois))],
})

data.data_repartition_esp = pd.DataFrame({
    "groupe_taxo": ["Oiseaux", "Mammifères", "Amphibiens", "Reptiles", "Insectes"],
    "nb_esp": [280, 90, 24, 18, 319],
})
data.data_repartition_data = pd.DataFrame({
    "groupe_taxo": ["Oiseaux", "Mammifères", "Amphibiens", "Reptiles", "Insectes"],
    "nb_data": [72000, 18000, 6500, 4200, 27730],
})

data.data_valid = pd.DataFrame({
    "label_valid_status": ["Certain - très probable", "Probable", "En attente de validation", "Douteux"],
    "nb_data": [98000, 21000, 8000, 1430],
})

data.data_validation = pd.DataFrame({
    "uuid": [f"uuid-{i}" for i in range(5)],
    "cd_ref": [1234, 5678, 9012, 3456, 7890],
    "rang": ["Espèce"] * 5,
    "nom_vern": ["Chouette hulotte", "Renard roux", "Salamandre tachetée", "Lézard vert", "Grand capricorne"],
    "lb_nom": ["Strix aluco", "Vulpes vulpes", "Salamandra salamandra", "Lacerta bilineata", "Cerambyx cerdo"],
    "label_valid_status": ["Douteux", "Douteux", "Invalide", "Douteux", "Non réalisable"],
    "Commentaire": ["Localisation à vérifier", "Date incohérente", "Doublon suspect", "Effectif improbable", "Photo manquante"],
    "Date_commentaire": ["2025-03-01"] * 5,
})

data.data_doublon = pd.DataFrame({
    "cd_nom": [1234, 5678],
    "lb_nom": ["Strix aluco", "Vulpes vulpes"],
    "nom_vern": ["Chouette hulotte", "Renard roux"],
    "geom_type": ["ST_Point", "ST_Point"],
    "lat": [45.44, 45.75],
    "lon": [3.75, 4.83],
    "observers": ["J. Dupont", "M. Martin"],
    "date": ["2024-05-12", "2024-06-03"],
    "nb_data_similaire": [3, 2],
})

data.source_doublon = pd.DataFrame({
    "Nom_source": ["Faune-AuRA", "OpenObs"],
    "Nombre_donnees_dupliquees": [42, 17],
})

data.data_geom_mesh = pd.DataFrame({
    "id_area": [1, 2, 3],
    "geojson": [
        '{"type": "Polygon", "coordinates": [[[3.7,45.4],[3.8,45.4],[3.8,45.5],[3.7,45.5],[3.7,45.4]]]}',
        '{"type": "Polygon", "coordinates": [[[4.7,45.7],[4.8,45.7],[4.8,45.8],[4.7,45.8],[4.7,45.7]]]}',
        '{"type": "Polygon", "coordinates": [[[5.7,45.9],[5.8,45.9],[5.8,46.0],[5.7,46.0],[5.7,45.9]]]}',
    ],
    "nb_data": [5200, 1800, 300],
    "nb_esp": [180, 90, 40],
})

data.data_hors_regions = pd.DataFrame({
    "id_synthese": [111, 222],
    "lat": [43.6, 48.85],
    "lon": [1.44, 2.35],
    "nom_cite": ["Buse variable", "Hérisson d'Europe"],
    "date_max": ["2024-04-01", "2024-04-15"],
    "observers": ["A. Petit", "L. Bernard"],
})

data.data_altitudes = pd.DataFrame({
    "classe_altitude": ["0-80", "80-250", "250-500", "500-750", "> 4750"],
    "classe_altitude_order": [1, 2, 3, 4, 21],
    "validite": ["correct", "correct", "correct", "correct", "incorrect"],
    "tot_data": [200, 45000, 60000, 20000, 12],
})
data.nb_data_hors_altitude = 12

data.data_type_geom = pd.DataFrame({
    "type_geom": ["Points", "Lignes", "Polygones"],
    "nb_data": [120000, 5000, 3430],
})

data.data_eee_synthese = pd.DataFrame({
    "nom_vern": ["Écrevisse de Louisiane", "Renouée du Japon"],
    "lb_nom": ["Procambarus clarkii", "Reynoutria japonica"],
    "cd_ref": [111222, 333444],
    "presence_connue_orb": ["RA", "Absente"],
    "secteur_obs": ["Au", ""],
    "nouvelle_presence": ["Oui", "Oui"],
    "nb_donnees": [14, 3],
    "premiere_observation": ["2023-06-01", "2024-02-11"],
    "derniere_observation": ["2025-05-20", "2025-04-02"],
    "effectif_min": [1, 1],
    "effectif_max": [12, 5],
})

data.data_eee_points = pd.DataFrame({
    "nom_vern": ["Écrevisse de Louisiane", "Renouée du Japon"],
    "lb_nom": ["Procambarus clarkii", "Reynoutria japonica"],
    "secteur_obs": ["Au", ""],
    "lat": [45.55, 45.2],
    "lon": [3.9, 4.1],
})

data.data_taille_geom = pd.DataFrame({
    "type_geom": ["Lignes"] * 5 + ["Polygones"] * 6,
    "classe_taille": [
        "< 100 m", "100 m - 1 km", "1 - 5 km", "5 - 20 km", "> 20 km",
        "< 0,1 ha", "0,1 - 1 ha", "1 - 10 ha", "10 - 100 ha", "100 - 2500 ha", "> 2500 ha",
    ],
    "classe_order": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5, 6],
    "imprecise": [False, False, False, False, True, False, False, False, False, False, True],
    "nb_data": [120, 340, 210, 60, 8, 900, 1500, 620, 180, 40, 5],
})

# -- Construction du contexte + rendu template --------------------------------

logger.info("Construction du contexte de test...")
context = _build_context(data)
template = _jinja_env.get_template("report_template.html")
html = template.render(**context)

output_path = config.OUTPUT_DIR / "DEMO_rapport_test.html"
output_path.write_text(html, encoding="utf-8")
logger.info("Rapport de démonstration écrit dans %s (%d caractères)", output_path, len(html))
print(f"OK -> {output_path}")

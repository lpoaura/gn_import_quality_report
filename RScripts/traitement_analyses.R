# . -------------------------------------------------------------------------- =============
# 0 - Objectifs du script ====
# . -------------------------------------------------------------------------- =============
## Créer un rapport RMarkDown qui détaille les données importée en fonction des id_source fournies.
## Le rapport ce fait automatique avec un résultat dans : Y:/01_dossiers_regionaux/02_thematiques/Base_de_donnees/11_synthese_automatique/4_synthese_ORB/Rendu/
## /!\ il est important de changer la variables :  /!\


# vue matérialized a rafraichir avant de lancer le script 
dbSendQuery(connDb, "refresh materialized view grafana.mv_source_geom_info;" ) 
dbSendQuery(connDb, "refresh materialized view grafana.mv_source_dataset;" ) 
dbSendQuery(connDb, "refresh materialized view grafana.mv_source_detail;" ) 
dbSendQuery(connDb, "refresh materialized view grafana.mv_source_acquisition_framework;" ) 
dbSendQuery(connDb, "refresh materialized view grafana.mv_source_niveau_taxonomique;" ) 
dbSendQuery(connDb, "refresh materialized view grafana.mv_source_info_temporelle;" ) 

# . -------------------------------------------------------------------------- =============
# 1 - Librairie ====
# . -------------------------------------------------------------------------- =============

# chargement de la base de données 
source(paste0("./connexion.R"))
source(paste0("./deps.R"))

# . -------------------------------------------------------------------------- =============
# 2 - /!\ Variable a changer /!\ ====
# . -------------------------------------------------------------------------- =============

tableau_rapport <- dbGetQuery(connDb, "select desc_source, nom_fichier, list_import from gn_imports.v_c_rapport_generated;" ) 

for (i in 1:nrow(tableau_rapport)) { 

nom_source <- tableau_rapport$desc_source[i]
list_id <- tableau_rapport$list_import[i]
nom_source_emplacement <- tableau_rapport$nom_fichier[i]

cat(paste0("Le rapport : ",nom_source,
"\n seras généré dans : ",nom_source_emplacement,
"\n il comprend les id import suivant : ", list_id),"\n")


# 1. Translitérer les accents
nom_source_emplacement_corr <- stringi::stri_trans_general(nom_source_emplacement, "Latin-ASCII")
# 2. Remplacer les espaces par des underscores
nom_source_emplacement_corr <- gsub(" ", "_", nom_source_emplacement_corr)
# 3. Supprimer tous les caractères sauf lettres, chiffres et underscores
nom_source_emplacement_corr <- gsub("[^A-Za-z0-9_]", "", nom_source_emplacement_corr)


emplacement_dossier = paste0("./output/",nom_source_emplacement_corr)
# Chemin vers le fichier R Markdown
fichier_rmd <- paste0("./rapport.Rmd") 
# Lancer la génération du document
rmarkdown::render(input = fichier_rmd, 
                  params = list(nom_source = nom_source, list_id = list_id),
                  output_file = emplacement_dossier)

cat("Le document a été généré avec succès !\n \n \n \n")
}

cat("L'ensemble des documents on étaient généré' !")
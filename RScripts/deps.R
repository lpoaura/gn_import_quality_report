# pkgUrl <- "https://cran.r-project.org/src/contrib/Archive/sf/sf_1.0-20.tar.gz"

# install.packages(pkgUrl, repos=NULL, type = "source")


pkgs <-  c("RPostgreSQL", "DBI","readr","rmarkdown","tinytex","xfun","fastmap","dplyr",
            "tidyverse","lubridate","stringr", "readxl","reticulate","ggplot2",
            "sf","leaflet","stringi","kableExtra", "plotly","scales","DT")
print("Vérification des packages R nécessaires...")

if (length(setdiff(pkgs, rownames(installed.packages()))) > 0) {
  # installation des packages 
  install.packages(setdiff(pkgs, rownames(installed.packages())))  
}
# chargement des packages 
lapply(pkgs, library, character.only = TRUE)
rm(pkgs)


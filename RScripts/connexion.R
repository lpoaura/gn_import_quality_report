# . -------------------------------------------------------------------------- =============
# 0 - Objectifs ====
# . -------------------------------------------------------------------------- =============

# Le script a pour objectif de realiser la connexion ? la base de donnees LPO
# qui nous permettras de requeter des donnees

# . -------------------------------------------------------------------------- =============
# 2 - Connexion BDD postGIS ====
# . -------------------------------------------------------------------------- =============

pkgs <-  c("RPostgreSQL", "DBI")

lapply(pkgs, library, character.only = TRUE)
rm(pkgs)

# ## Supressions de toutes les connexions pr?c?dentes
# lapply(dbListConnections(drv = dbDriver("PostgreSQL")),
#        function(x) {dbDisconnect(conn = x)})

lapply(dbListConnections(drv = dbDriver("PostgreSQL")),
       function(x) {dbDisconnect(conn = x)})
# type de connexion PostgreSQL et information de connexion 
drv <- dbDriver("PostgreSQL")
# Declare db connection settings
dbname = Sys.getenv("DBNAME")
dbhost = Sys.getenv("DBHOST")
dbport = Sys.getenv("DBPORT")
dbuser = Sys.getenv("DBUSER")
dbpwd = Sys.getenv("DBPWD")

# connexion a la BDD
tryCatch({
    drv <- dbDriver("PostgreSQL")
    print("Connecting to Database…")
    connDb <- dbConnect(drv, 
      dbname = dbname,
      host = dbhost,
      port = dbport,
      password = dbpwd,
      user = dbuser,
      #base::list(sslmode="require", connect_timeout="10"),
    )
    df <- dbGetQuery(conDb, "SELECT * FROM gn_commons.t_parameters")
    print("Database Connected!")
    # dbListTables(connDb)
  },
  error=function(cond) {
    print("Unable to connect to Database.")
  }
)

# lists des tables dans la BDD 
rm(dbname,dbhost,dbport,dbuser,dbpwd)
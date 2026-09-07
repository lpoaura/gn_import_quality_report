# ---Choix de l'image de base ----------------
FROM python:3.13-slim
# ---Déclarations d'environnement ----------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /home/user
# ---récupération des dossiers ----------------
COPY pyproject.toml README.md ./
COPY src/ src/
# ---Installation des dépendances ----------------
RUN pip install --no-cache-dir .

# ---Création des utilisateurs ----------------
RUN useradd -ms /bin/bash user && chown -R user:user /home/user
# ---Création des répertoires ----------------
RUN mkdir -p /home/user/output 
RUN mkdir -p /home/user/logs && chown -R user:user /home/user/logs
# --- Important dans le dossier il faut penser a donner les droits à l'utilisateur ----------------
    # Dans bash à l'endroit du output logs lancer la commande :  docker run --rm --entrypoint id lpoaura/importgenerator:latest
    # Puis lancer la commande en changeant les XXXX en fonction du résultat précédant : sudo chown -R XXXX:XXXX output logs
# --- Bascule vers un utilisateur non-root ----------------
USER user

# --- fonction ----------------
ENTRYPOINT ["importreporter"]
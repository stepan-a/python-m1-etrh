#!/bin/bash
set -e

CIBLE="/puck/www/le-mans.adjemian.eu/python-m1-etrh"

# --- Nettoyage incrémental (équivalent GIT_CLEAN_FLAGS) -------------------
# .venv (~31000 fichiers) et .cache (distribution Pyodide, 334 Mo) sont
# volontairement préservés d'un build à l'autre : coûteux à reconstruire,
# et make les réutilise tels quels de façon incrémentale.
git clean -ffdx -e .venv -e .cache

# --- Vérification (stage "verify" / job "corriges") -----------------------
# Garde-fou de la source unique : construit les dix notebooks puis exécute
# les cinq corrigés. Un exercice dont la solution ne tourne plus arrête
# le pipeline avant tout déploiement.
make check
test -f content/seance-1.ipynb
test -f content/seance-5-corrige.ipynb
test -f content/data/salaires.csv

# --- Déploiement (stage "deploy" / job "site") -----------------------------
# Construit le site JupyterLite et l'archive hors ligne, puis publie sous
# le-mans.adjemian.eu. --delete est sans risque : répertoire dédié à ce
# cours, sur un vhost distinct du site personnel.
make lite
make zip
test -f dist/index.html
test -f dist/lite/lab/index.html
test -f dist/lite/files/seance-4.ipynb
test -f dist/zip/cours-python-etrh.zip

mkdir -p "$CIBLE"
rsync -a --delete dist/ "$CIBLE/"

echo "Déployé sur https://le-mans.adjemian.eu/python-m1-etrh/"

# Makefile — construire les notebooks du cours à partir des sources Org.
#
# Cibles principales :
#   make            (= make notebooks) : construit les 5 notebooks étudiants
#   make corriges   : construit les 5 notebooks corrigés
#   make check      : exécute les corrigés (vérifie que les solutions tournent)
#   make content    : assemble le dossier servi dans le navigateur
#   make lite       : construit le site JupyterLite dans dist/
#   make serve      : sert dist/ en local sur http://localhost:8000
#   make venv       : crée l'environnement virtuel et installe les dépendances
#   make lab        : lance JupyterLab sur les notebooks
#   make lock       : fige les versions exactes dans requirements.lock
#   make clean      : supprime tout ce qui est généré
#   make distclean  : supprime aussi l'environnement virtuel
#
# La CI GitLab (.gitlab-ci.yml) surcharge les outils par ceux du runner :
#   make notebooks JUPYTEXT=jupytext PANDOC=pandoc VENV_PREREQ=

PYTHON   := python3
VENV     := .venv
BIN      := $(VENV)/bin
JUPYTEXT := $(BIN)/jupytext
JUPYTER  := $(BIN)/jupyter
PANDOC   := pandoc            # dépendance système (apt install pandoc)
REQ      := requirements.txt
STAMP    := $(VENV)/.installed

# Prérequis « environnement » des cibles de construction. Par défaut le stamp
# de la .venv ; la CI le vide (VENV_PREREQ=) car elle fournit jupytext et
# pandoc directement, sans .venv.
VENV_PREREQ ?= $(STAMP)

SEANCES   := 1 2 3 4 5
SOURCES   := $(patsubst %,seances/seance-%.org,$(SEANCES))
NOTEBOOKS := $(patsubst %,notebooks/seance-%.ipynb,$(SEANCES))
CORRIGES  := $(patsubst %,notebooks/corriges/seance-%.ipynb,$(SEANCES))

LUA       := build/title-block.lua build/exercices.lua

.PHONY: all notebooks corriges check content lite zip serve venv lab lock clean distclean

all: notebooks

notebooks: $(NOTEBOOKS)

corriges: $(CORRIGES)

# --------------------------------------------------------------------------
# Org --(pandoc)--> Markdown --(jupytext)--> notebook
# --------------------------------------------------------------------------
#
# Options pandoc :
#   -t gfm           : Markdown GitHub (évite les attributs {.verbatim}, les
#                      apostrophes échappées et les blocs ```{=org})
#   --wrap=none      : pas de coupure des lignes à 72 colonnes
#   --lua-filter     : title-block réinjecte le titre en tête du document,
#                      exercices bascule énoncé/corrigé
#
# Pré-nettoyage (sed) : on retire les caractères de largeur nulle (U+200B
# ZWSP, U+200C, U+200D, U+FEFF BOM) qui parasitent la source. Sans cela, un
# verbatim org comme =X= n'est pas reconnu comme du code et ressort tel quel.
STRIP_ZW := sed -e 's/\xe2\x80\x8b//g; s/\xe2\x80\x8c//g; s/\xe2\x80\x8d//g; s/\xef\xbb\xbf//g'

# Post-filtre : GFM échappe « < » et « > » en « \< » / « \> ». On les remplace
# par les entités &lt; / &gt; : pas de backslash dans la source, et un rendu
# correct partout. (Un « > » nu en début d'item de liste serait interprété
# comme une citation — d'où les entités plutôt qu'un « > » brut.)
UNESCAPE := sed -e 's/\\</\&lt;/g' -e 's/\\>/\&gt;/g'

ORG2MD = $(STRIP_ZW) $< \
	   | $(PANDOC) -f org -t gfm --wrap=none $(addprefix --lua-filter=,$(LUA)) \
	   | $(UNESCAPE)

# Les deux versions transitent par des dossiers distincts plutôt que par un
# suffixe : aucune règle à motif n'est alors ambiguë.
build/etudiant/seance-%.md: seances/seance-%.org $(LUA)
	@mkdir -p $(@D)
	$(ORG2MD) > $@

# « export » et non « CORRIGE=1 $(ORG2MD) » : dans un pipeline, un préfixe
# d'affectation ne s'applique qu'à la PREMIÈRE commande — ici sed — alors que
# c'est pandoc, plus loin dans le tuyau, qui lit la variable.
build/corrige/seance-%.md: seances/seance-%.org $(LUA)
	@mkdir -p $(@D)
	export CORRIGE=1; $(ORG2MD) > $@

# Prérequis venv en « order-only » (|) et surchargeable : il garantit la
# présence des outils en local sans forcer la régénération des notebooks, et
# peut être neutralisé en CI (VENV_PREREQ=).
notebooks/seance-%.ipynb: build/etudiant/seance-%.md | $(VENV_PREREQ)
	@mkdir -p $(@D)
	$(JUPYTEXT) --to ipynb $< -o $@

notebooks/corriges/seance-%.ipynb: build/corrige/seance-%.md | $(VENV_PREREQ)
	@mkdir -p $(@D)
	$(JUPYTEXT) --to ipynb $< -o $@

# --------------------------------------------------------------------------
# Site JupyterLite : le dossier servi aux étudiants
# --------------------------------------------------------------------------
# content/ devient la racine du navigateur de fichiers dans le site.
#
# L'arborescence est PLATE, et ce n'est pas un détail. Le répertoire courant
# n'est pas le même des deux côtés : dans le navigateur il vaut toujours
# « /drive » (la racine du contenu), sous nbconvert il vaut le dossier du
# notebook. Ranger les corrigés dans un sous-dossier casserait donc
# « pd.read_csv("data/…") » sous « make check » pendant que le site, lui,
# continuerait de marcher — le bug ne se serait vu qu'en cours. Tout au même
# niveau que data/, et les deux environnements s'accordent.
content: $(NOTEBOOKS) $(CORRIGES)
	@rm -rf content
	@mkdir -p content/data content/wheels
	@cp $(NOTEBOOKS) content/
	@for n in $(SEANCES); do \
	  cp notebooks/corriges/seance-$$n.ipynb content/seance-$$n-corrige.ipynb ; \
	done
	@cp data/* content/data/
	@cp lite/wheels/*.whl content/wheels/ 2>/dev/null || true
	@echo "✓ content/ assemblé."

# --------------------------------------------------------------------------
# Vérification : les corrigés doivent s'exécuter sans erreur.
# --------------------------------------------------------------------------
# C'est le garde-fou du choix « source unique, deux sorties » : un exercice
# dont la solution ne tourne plus casse le pipeline, pas la séance.
#
# On exécute depuis content/, c'est-à-dire dans l'arborescence exacte que les
# étudiants auront sous les yeux. Vérifier ailleurs validerait autre chose
# que ce qui est servi.
check: content | $(VENV_PREREQ)
	@for n in $(SEANCES); do \
	  echo "▶ exécution du corrigé de la séance $$n" ; \
	  (cd content && ../$(JUPYTER) nbconvert --to notebook --execute --stdout \
	     --ExecutePreprocessor.timeout=600 "seance-$$n-corrige.ipynb" > /dev/null) \
	     || exit 1 ; \
	done
	@echo "✓ les 5 corrigés s'exécutent sans erreur."

# --contents et --output-dir sont résolus relativement à --lite-dir : on passe
# donc des chemins absolus, sans quoi jupyterlite cherche « lite/content ».
lite: content | $(VENV_PREREQ)
	@rm -rf dist
	$(JUPYTER) lite build \
	  --lite-dir lite \
	  --contents $(CURDIR)/content \
	  --output-dir $(CURDIR)/dist/lite \
	  --no-sourcemaps
	@# Le portail est déposé À CÔTÉ de l'application, jamais dedans.
	@# jupyterlite remonte de son application jusqu'à sa racine en lisant le
	@# index.html de chaque niveau, dont il extrait « jupyter-config-data » ;
	@# écraser dist/lite/index.html par une page maison casse donc le
	@# chargement de toutes les interfaces d'un coup.
	@cp lite/index.html dist/index.html
	@echo "✓ site construit dans dist/ ($$(du -sh dist | cut -f1))"

# Archive hors ligne, servie DEPUIS le site : dist/zip/ est donc construit
# avant le rsync et part avec le reste. C'est ce qui garantit que l'archive
# téléchargée correspond toujours aux notebooks en ligne — et cela évite le
# piège du « rsync --delete », qui effacerait un zip déposé séparément.
ZIPDIR := cours-python-etrh

zip: content lite/zip-index.html
	@rm -rf $(ZIPDIR) dist/zip
	@mkdir -p $(ZIPDIR) dist/zip
	@cp content/*.ipynb $(ZIPDIR)/
	@cp -r content/data content/wheels $(ZIPDIR)/
	@cp cours.py requirements.txt LISEZMOI.txt DONNEES.md $(ZIPDIR)/
	@$(PYTHON) -m zipfile -c dist/zip/$(ZIPDIR).zip $(ZIPDIR)/
	@rm -rf $(ZIPDIR)
	@cp lite/zip-index.html dist/zip/index.html
	@echo "✓ dist/zip/$(ZIPDIR).zip ($$(du -h dist/zip/$(ZIPDIR).zip | cut -f1))"

serve: lite zip
	@echo "▶ http://localhost:8000/  (Ctrl-C pour arrêter)"
	@cd dist && $(PYTHON) -m http.server

# --------------------------------------------------------------------------
# Environnement
# --------------------------------------------------------------------------
venv: $(STAMP)

# Le « stamp » est refait dès que requirements.txt est modifié : make détecte
# alors qu'il faut réinstaller les dépendances.
$(STAMP): $(REQ)
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r $(REQ)
	touch $(STAMP)

lab: $(NOTEBOOKS) | $(STAMP)
	$(JUPYTER) lab notebooks

lock: $(STAMP)
	$(BIN)/pip freeze > requirements.lock

clean:
	rm -rf build/etudiant build/corrige notebooks content dist $(ZIPDIR) .jupyterlite.doit.db

distclean: clean
	rm -rf $(VENV)

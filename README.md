# Introduction à Python — M1 ETRH

Cours d'initiation à Python pour économistes du travail : cinq séances de
2 h, sans prérequis en programmation, orientées analyse de données du marché
du travail.

Les étudiants n'installent rien. Le cours s'exécute dans leur navigateur :

**<https://le-mans.adjemian.eu/python-m1-etrh/>**

La source unique de chaque séance est un fichier Org dans [`seances/`](seances) ;
les notebooks Jupyter en sont **générés**, en deux versions — celle de
l'étudiant et le corrigé.

## Aperçu de la chaîne

```
seances/seance-N.org
  │  sed        retire les caractères de largeur nulle (U+200B…)
  │  pandoc     Org → Markdown (GFM)
  │             ├── title-block.lua  réinjecte titre / sous-titre / auteur
  │             └── exercices.lua    bascule énoncé ⇄ corrigé, marque les
  │                                  cellules non exécutables
  │  sed        \< \>  →  &lt; &gt;
  │  jupytext   Markdown → notebook (les blocs ```python deviennent
  ▼             des cellules de code)
notebooks/seance-N.ipynb          (cellules d'exercice vides)
notebooks/corriges/seance-N.ipynb (solutions remplies)
  │
  │  make content    arborescence plate : notebooks + data/ + wheels/
  │  make lite       JupyterLite (Pyodide) + portail
  ▼
dist/  →  rsync  →  le-mans.adjemian.eu/python-m1-etrh/
```

## Démarrage rapide

Il suffit d'avoir **Python 3** et **pandoc** installés :

```bash
make            # construit les 5 notebooks étudiants
make corriges   # et les 5 corrigés
make check      # exécute les corrigés — aucun exercice cassé
make serve      # construit le site et le sert sur http://localhost:8000
```

`make venv` est appelé automatiquement au besoin.

Pour un usage hors ligne sans `make`, `python cours.py` fait tout — création
de l'environnement, construction des notebooks, ouverture de JupyterLab.

## Écrire une séance

### Un exercice et son corrigé

La solution vit dans la source, juste sous l'énoncé, dans un bloc marqué
`:corrige t` :

```org
*Exercice 4.2* /(socle)/ — Salaire net moyen par diplôme.

#+BEGIN_SRC python :corrige t
salaires.groupby("diplome")["salaire_net_mensuel"].mean()
#+END_SRC
```

Le bloc devient une **cellule d'amorce vide** dans `notebooks/seance-4.ipynb`
et une **cellule remplie** dans `notebooks/corriges/seance-4.ipynb`. Un seul
fichier à maintenir, et `make check` garantit que la solution tourne encore.

Les exercices sont marqués `/(socle)/` ou `/(bonus)/`, conformément au
syllabus : un socle pour tout le monde, un bonus pour ceux qui vont plus vite.

### Une cellule qu'on ne peut pas exécuter automatiquement

`input()` bloquerait indéfiniment sous `make check`. Le marqueur `:skip t`
attache le tag Jupyter `skip-execution`, respecté par `nbclient` :

```org
#+BEGIN_SRC python :skip t
prenom = input("Quel est votre prénom ? ")
#+END_SRC
```

L'étudiant l'exécute normalement dans son navigateur ; la CI la saute. Les
deux marqueurs se combinent (`:corrige t :skip t`).

### Les blocs ordinaires

Un `#+BEGIN_SRC python` sans en-tête est un exemple du cours : il traverse le
filtre intact, et **il est exécuté par `make check`**. Tout exemple doit donc
fonctionner.

## Cibles du Makefile

| Commande         | Effet                                                        |
|------------------|--------------------------------------------------------------|
| `make`           | construit les 5 notebooks étudiants (= `make notebooks`)      |
| `make corriges`  | construit les 5 corrigés                                      |
| `make content`   | assemble le dossier servi (notebooks + `data/` + `wheels/`)   |
| `make check`     | exécute les 5 corrigés dans l'arborescence du site            |
| `make lite`      | construit le site JupyterLite dans `dist/`                    |
| `make serve`     | construit puis sert `dist/` sur <http://localhost:8000>       |
| `make venv`      | crée `.venv` et installe les dépendances                      |
| `make lab`       | ouvre JupyterLab sur les notebooks                            |
| `make lock`      | fige les versions exactes dans `requirements.lock`            |
| `make clean`     | supprime tout ce qui est généré                               |
| `make distclean` | supprime en plus l'environnement virtuel                      |

## Deux pièges de la chaîne, déjà payés

Ils sont documentés dans le `Makefile`, mais valent d'être signalés ici.

**L'arborescence servie est plate.** Les deux environnements ne placent pas
le répertoire courant au même endroit : dans le navigateur, il vaut toujours
`/drive`, la racine du contenu ; sous `nbconvert` — donc sous `make check` —
il vaut le dossier du notebook. Ranger les corrigés dans un sous-dossier
casserait donc `pd.read_csv("data/…")` à la vérification, alors même que le
site fonctionnerait : le bug ne se serait vu qu'en cours. Tout au même niveau
que `data/`, et les deux environnements s'accordent.

**Le portail est déposé à côté de l'application, jamais dedans.** JupyterLite
remonte de son application jusqu'à sa racine en lisant l'`index.html` de
chaque niveau, dont il extrait `jupyter-config-data`. Écraser
`dist/lite/index.html` par une page maison fait échouer le chargement de
toutes les interfaces d'un coup, sans message clair. D'où `dist/index.html`
(le portail) et `dist/lite/` (l'application).

## Versions

`jupyterlite-pyodide-kernel` embarque une version précise de Pyodide, qui
fixe les versions vues par les étudiants. Aujourd'hui, Pyodide 314.0.5 :

| Bibliothèque | Version servie |
|--------------|----------------|
| pandas       | 3.0.2          |
| numpy        | 2.4.6          |
| matplotlib   | 3.10.8         |
| statsmodels  | 0.14.6         |
| scipy        | 1.18.0         |

`requirements.txt` aligne l'environnement local sur ces versions, pour que
`make check` valide bien ce que les étudiants exécuteront. **Après toute mise
à jour de `jupyterlite-pyodide-kernel`, revérifier ce tableau.**

`openpyxl` n'est pas fourni par Pyodide. Son wheel et celui de sa dépendance
`et_xmlfile` sont versionnés dans [`lite/wheels/`](lite/wheels) et **indexés à
la construction** par `--piplite-wheels`. La séance 4 écrit alors simplement :

```python
import piplite
await piplite.install("openpyxl")
```

`piplite` puise dans un catalogue servi par le site, sans accès à Internet, et
résout lui-même les dépendances.

Une tentative précédente passait par `micropip.install("emfs:wheels/…")`,
c'est-à-dire par un chemin de fichier. **Ne refaites pas cela** : le système
de fichiers de JupyterLite est paresseux, les entrées d'un dossier ne se
matérialisent qu'au premier accès, et l'installation échouait donc en
`FileNotFoundError` — sauf si une cellule antérieure avait listé le dossier,
ce qui rendait le bogue intermittent et très trompeur à diagnostiquer.

Le cours s'en tient à **matplotlib** pour les graphiques : histogramme, nuage
de points et diagramme en barres suffisent au programme, et une seule API
graphique vaut mieux que deux pour des débutants.

## Données

Trois jeux dans [`data/`](data), reconstructibles par
`python3 scripts/prepare-data.py`. Le chômage vient de l'INSEE et est réel ;
les salaires et le jeu RH sont **simulés**, faute de microdonnées d'enquête
librement redistribuables. Provenance, calibrage et défauts délibérés sont
documentés dans **[DONNEES.md](DONNEES.md)** — à lire avant d'utiliser ces
fichiers ailleurs que dans le cours.

## Structure du dépôt

| Chemin                  | Rôle                                                    |
|-------------------------|---------------------------------------------------------|
| `seances/*.org`         | sources du cours (à éditer)                             |
| `build/title-block.lua` | filtre pandoc : titre / sous-titre / auteur             |
| `build/exercices.lua`   | filtre pandoc : bascule corrigé, cellules non exécutées |
| `data/`                 | jeux de données versionnés                              |
| `scripts/prepare-data.py` | construction et documentation des données             |
| `lite/`                 | configuration JupyterLite, portail, wheels indexées      |
| `Makefile`              | chaîne de construction (auteur)                          |
| `cours.py`              | lanceur tout-en-un (utilisateur, hors ligne)             |
| `requirements.txt`      | dépendances voulues, bornées sur Pyodide                 |
| `requirements.lock`     | versions exactes figées                                  |
| `.gitlab-ci.yml`        | construction, vérification, déploiement, release         |

`notebooks/`, `content/`, `dist/` et `build/etudiant|corrige/` sont générés
et ignorés par git.

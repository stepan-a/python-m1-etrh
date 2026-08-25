#!/usr/bin/env python3
"""Lanceur tout-en-un du cours « Introduction à Python » (M1 ETRH).

Le cours s'utilise normalement en ligne, dans le navigateur :

    https://le-mans.adjemian.eu/python-m1-etrh/

Ce script est le repli hors ligne — utile pour le projet de groupe, où l'on
finit par vouloir un vrai Python local. Avec le seul Python du système, il :

  1. crée un environnement virtuel (.venv) si besoin ;
  2. y installe les dépendances (requirements.txt) ;
  3. (re)construit les notebooks depuis les sources Org, si elles sont là ;
  4. lance JupyterLab sur les notebooks.

    python cours.py

Options :
    python cours.py --no-launch   # tout préparer sans ouvrir JupyterLab
    python cours.py --rebuild     # forcer la reconstruction des notebooks
    python cours.py --corriges    # construire aussi les corrigés

Seule dépendance externe : « pandoc », et uniquement en mode auteur (quand
les sources Org sont présentes). Depuis l'archive zip distribuée, les
notebooks sont déjà construits et pandoc est inutile.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQ = ROOT / "requirements.txt"
STAMP = VENV / ".installed"

SOURCES = ROOT / "seances"
BUILD = ROOT / "build"
NOTEBOOKS = ROOT / "notebooks"

SEANCES = [1, 2, 3, 4, 5]

# Caractères de largeur nulle à retirer (cf. Makefile).
ZERO_WIDTH = ["​", "‌", "‍", "﻿"]


def bin_dir() -> Path:
    """Dossier des exécutables de la .venv (diffère sous Windows)."""
    return VENV / ("Scripts" if os.name == "nt" else "bin")


def venv_exe(name: str) -> Path:
    exe = bin_dir() / name
    if os.name == "nt" and not exe.suffix:
        exe = exe.with_suffix(".exe")
    return exe


def info(msg: str) -> None:
    print(f"\033[1;36m▶ {msg}\033[0m")


def ensure_venv() -> None:
    """Crée la .venv et installe les dépendances si nécessaire."""
    if not VENV.exists():
        info("Création de l'environnement virtuel (.venv)…")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)

    # Réinstaller si le marqueur manque ou est plus ancien que requirements.
    needs_install = (
        not STAMP.exists() or STAMP.stat().st_mtime < REQ.stat().st_mtime
    )
    if needs_install:
        info("Installation des dépendances (cela peut prendre une minute)…")
        pip = venv_exe("pip")
        subprocess.run([str(pip), "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(pip), "install", "-r", str(REQ)], check=True)
        STAMP.write_text("ok", encoding="utf-8")
    else:
        info("Dépendances déjà installées.")


def exiger_pandoc() -> None:
    if shutil.which("pandoc") is not None:
        return
    print(
        "\n\033[1;31mErreur : « pandoc » est introuvable.\033[0m\n"
        "Il n'est nécessaire que pour reconstruire les notebooks depuis les\n"
        "sources Org. Installe-le puis relance :\n"
        "  • Debian/Ubuntu : sudo apt install pandoc\n"
        "  • macOS (brew)  : brew install pandoc\n"
        "  • Windows       : https://pandoc.org/installing.html\n",
        file=sys.stderr,
    )
    sys.exit(1)


def construire(numero: int, corrige: bool) -> Path:
    """Org -> Markdown -> notebook, pour une séance.

    Reproduit exactement le pipeline du Makefile ; les deux doivent rester
    d'accord.
    """
    source = SOURCES / f"seance-{numero}.org"
    variante = "corrige" if corrige else "etudiant"
    md = BUILD / variante / f"seance-{numero}.md"
    if corrige:
        notebook = NOTEBOOKS / "corriges" / f"seance-{numero}.ipynb"
    else:
        notebook = NOTEBOOKS / f"seance-{numero}.ipynb"

    md.parent.mkdir(parents=True, exist_ok=True)
    notebook.parent.mkdir(parents=True, exist_ok=True)

    texte = source.read_text(encoding="utf-8")
    for zw in ZERO_WIDTH:
        texte = texte.replace(zw, "")

    env = dict(os.environ)
    if corrige:
        env["CORRIGE"] = "1"
    else:
        env.pop("CORRIGE", None)

    resultat = subprocess.run(
        ["pandoc", "-f", "org", "-t", "gfm", "--wrap=none",
         f"--lua-filter={BUILD / 'title-block.lua'}",
         f"--lua-filter={BUILD / 'exercices.lua'}"],
        input=texte, text=True, capture_output=True, check=True, env=env,
    ).stdout
    resultat = resultat.replace(r"\<", "&lt;").replace(r"\>", "&gt;")
    md.write_text(resultat, encoding="utf-8")

    subprocess.run(
        [str(venv_exe("jupytext")), "--to", "ipynb", str(md), "-o", str(notebook)],
        check=True,
    )
    return notebook


def a_reconstruire(numero: int, corrige: bool) -> bool:
    source = SOURCES / f"seance-{numero}.org"
    if corrige:
        notebook = NOTEBOOKS / "corriges" / f"seance-{numero}.ipynb"
    else:
        notebook = NOTEBOOKS / f"seance-{numero}.ipynb"
    if not notebook.exists():
        return True
    return notebook.stat().st_mtime < source.stat().st_mtime


def launch() -> None:
    info("Ouverture de JupyterLab… (ferme la fenêtre/onglet pour quitter)")
    subprocess.run([str(venv_exe("jupyter")), "lab", str(NOTEBOOKS)])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prépare et lance le cours « Introduction à Python » (M1 ETRH)."
    )
    parser.add_argument("--no-launch", action="store_true",
                        help="Tout préparer sans ouvrir JupyterLab.")
    parser.add_argument("--rebuild", action="store_true",
                        help="Forcer la reconstruction des notebooks.")
    parser.add_argument("--corriges", action="store_true",
                        help="Construire aussi les notebooks corrigés.")
    args = parser.parse_args()

    ensure_venv()

    if SOURCES.is_dir():
        # Mode auteur : les sources Org sont là -> (re)construire au besoin.
        variantes = [False, True] if args.corriges else [False]
        a_faire = [(n, c) for n in SEANCES for c in variantes
                   if args.rebuild or a_reconstruire(n, c)]
        if a_faire:
            exiger_pandoc()
            info(f"Construction de {len(a_faire)} notebook(s)…")
            for numero, corrige in a_faire:
                construire(numero, corrige)
        else:
            info("Notebooks déjà à jour.")
    else:
        # Mode distribution (zip) : les notebooks fournis sont utilisés tels quels.
        info("Notebooks fournis — utilisés tels quels.")

    if args.no_launch:
        info("Prêt. Lance « python cours.py » pour ouvrir le cours.")
    else:
        launch()


if __name__ == "__main__":
    main()

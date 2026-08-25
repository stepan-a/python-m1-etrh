#!/usr/bin/env python3
"""Construit les jeux de données du cours dans data/.

Ce script n'est pas exécuté par les étudiants : il documente la provenance et
les traitements, et se relance quand on veut rafraîchir les données.

    python3 scripts/prepare-data.py

Trois fichiers sont produits :

  data/chomage-bit.csv     DONNÉES RÉELLES — INSEE, taux de chômage au sens
                           du BIT, trimestriel, par sexe et tranche d'âge.
  data/salaires.csv        DONNÉES SIMULÉES — les microdonnées de l'enquête
                           Emploi ne sont pas librement téléchargeables (accès
                           soumis à convention via Progedo/ADISP). Ce fichier
                           est donc engendré par simulation, calibrée sur les
                           ordres de grandeur publiés par l'INSEE et la DARES.
  data/rh-turnover.csv     DONNÉES SIMULÉES — jeu RH d'entreprise fictif.

Les deux fichiers simulés portent volontairement des défauts réalistes
(valeurs manquantes, codages incohérents, doublons, valeurs aberrantes) : ils
servent de support à la section « nettoyage » de la séance 4.

Voir DONNEES.md pour les sources, licences et dictionnaires de variables.
"""

import io
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

# Graine fixe : les fichiers simulés sont reproductibles à l'identique.
SEED = 20260901


# ---------------------------------------------------------------------------
# 1. Chômage — données réelles INSEE
# ---------------------------------------------------------------------------

SDMX_URL = "https://bdm.insee.fr/series/sdmx/data/CHOMAGE-TRIM-NATIONAL"

SEXE = {"0": "Ensemble", "1": "Hommes", "2": "Femmes"}
AGE = {"00-": "Ensemble", "00-24": "Moins de 25 ans",
       "25-49": "25 à 49 ans", "50-": "50 ans ou plus"}


def build_chomage() -> None:
    """Taux de chômage BIT trimestriel, par sexe et âge, depuis 1975.

    Source : INSEE, Banque de données macro-économiques, dataflow
    CHOMAGE-TRIM-NATIONAL, indicateur CTTXC (taux de chômage au sens du BIT),
    données CVS, France hors Mayotte (REF_AREA = FR-D976). On écarte les
    séries marquées SERIE_ARRETEE.
    """
    print("▶ téléchargement des séries INSEE…")
    with urllib.request.urlopen(SDMX_URL, timeout=120) as fh:
        raw = fh.read()

    root = ET.parse(io.BytesIO(raw)).getroot()
    lignes = []
    for serie in (e for e in root.iter() if e.tag.endswith("Series")):
        a = serie.attrib
        if a.get("INDICATEUR") != "CTTXC":
            continue
        if a.get("SERIE_ARRETEE") == "TRUE":
            continue
        if a.get("REF_AREA") != "FR-D976":     # France hors Mayotte, série longue
            continue
        for obs in (o for o in serie if o.tag.endswith("Obs")):
            valeur = obs.attrib.get("OBS_VALUE")
            if valeur in (None, ""):
                continue
            trimestre = obs.attrib["TIME_PERIOD"]        # ex. « 2026-Q2 »
            annee, num = trimestre.split("-Q")
            lignes.append({
                "trimestre": trimestre,
                "annee": int(annee),
                "num_trimestre": int(num),
                "sexe": SEXE[a["SEXE"]],
                "age": AGE[a["AGE"]],
                "taux_chomage": float(valeur),
            })

    df = (pd.DataFrame(lignes)
            .sort_values(["trimestre", "sexe", "age"])
            .reset_index(drop=True))
    df.to_csv(DATA / "chomage-bit.csv", index=False)
    print(f"  data/chomage-bit.csv : {len(df)} lignes, "
          f"{df.trimestre.min()} → {df.trimestre.max()}")


# ---------------------------------------------------------------------------
# 2. Salaires — simulation calibrée
# ---------------------------------------------------------------------------

# Diplôme -> (part dans la population, années d'études, prime salariale)
# Parts et primes calées sur les ordres de grandeur INSEE (Formations et
# emploi ; Emploi, chômage, revenus du travail). Les années d'études sont la
# durée théorique après l'entrée à l'école élémentaire.
DIPLOMES = {
    "Aucun diplôme":      (0.14,  7, -0.22),
    "CAP-BEP":            (0.24, 10, -0.10),
    "Baccalauréat":       (0.20, 12,  0.00),
    "Bac+2":              (0.16, 14,  0.14),
    "Bac+3/4":            (0.13, 15,  0.26),
    "Bac+5 ou plus":      (0.13, 17,  0.52),
}

SECTEURS = {
    "Industrie":                 (0.13,  0.06),
    "Construction":              (0.07,  0.01),
    "Commerce":                  (0.13, -0.04),
    "Services aux entreprises":  (0.18,  0.09),
    "Services aux particuliers": (0.11, -0.12),
    "Santé - action sociale":    (0.16, -0.02),
    "Enseignement":              (0.08,  0.00),
    "Administration publique":   (0.14,  0.01),
}


def build_salaires(n: int = 5000) -> None:
    """Échantillon individuel simulé de salariés.

    Le salaire est engendré par une équation de Mincer :

        log(salaire) = const + 0.075 * années d'études
                             + 0.021 * expérience - 0.00032 * expérience²
                             - 0.135 * (femme)
                             + effet secteur + bruit

    Le rendement de l'éducation (7,5 % par année) et l'écart salarial
    femmes-hommes à temps de travail comparable (~13 %) reproduisent les
    ordres de grandeur usuellement estimés sur données françaises. Le niveau
    est calé pour un salaire net médian à temps plein proche de 2 100 € par
    mois (INSEE, salaires dans le secteur privé).
    """
    rng = np.random.default_rng(SEED)

    femme = rng.random(n) < 0.485
    sexe = np.where(femme, "Femme", "Homme")

    noms_dip = list(DIPLOMES)
    parts = np.array([DIPLOMES[d][0] for d in noms_dip])
    diplome = rng.choice(noms_dip, size=n, p=parts / parts.sum())
    annees_etudes = np.array([DIPLOMES[d][1] for d in diplome], dtype=float)

    noms_sec = list(SECTEURS)
    parts_sec = np.array([SECTEURS[s][0] for s in noms_sec])
    secteur = rng.choice(noms_sec, size=n, p=parts_sec / parts_sec.sum())
    effet_secteur = np.array([SECTEURS[s][1] for s in secteur])

    # Âge : entrée sur le marché du travail après les études, puis une
    # ancienneté sur le marché tirée au sort et bornée par l'âge de départ.
    age_entree = annees_etudes + 6
    experience = rng.gamma(shape=3.2, scale=4.6, size=n)
    experience = np.clip(experience, 0, 45)
    age = np.clip(age_entree + experience, 16, 66)

    # Temps partiel : nettement plus fréquent chez les femmes (~28 % contre
    # ~8 %), et concentré dans les services aux particuliers.
    p_partiel = np.where(femme, 0.27, 0.08)
    p_partiel = np.where(secteur == "Services aux particuliers",
                         p_partiel + 0.12, p_partiel)
    temps_partiel = rng.random(n) < p_partiel
    temps_travail = np.where(temps_partiel, "Temps partiel", "Temps complet")
    heures = np.where(temps_partiel,
                      rng.normal(22, 5, n).clip(5, 33),
                      rng.normal(36.5, 2.2, n).clip(34, 48))

    # Équation de Mincer, en équivalent temps plein.
    log_salaire = (
        6.529
        + 0.075 * annees_etudes
        + 0.021 * experience
        - 0.00032 * experience ** 2
        - 0.135 * femme
        + effet_secteur
        + rng.normal(0, 0.30, n)
    )
    salaire_etp = np.exp(log_salaire)
    # Salaire effectivement perçu : proportionnel au temps de travail.
    salaire = salaire_etp * (heures / 35.0)
    salaire = np.clip(salaire, 700, None)

    # Catégorie socioprofessionnelle, déduite du diplôme et du salaire ETP.
    csp = np.full(n, "Employé", dtype=object)
    csp[(annees_etudes <= 10) & (salaire_etp < 2200)] = "Ouvrier"
    csp[(annees_etudes >= 14) & (salaire_etp > 2400)] = "Profession intermédiaire"
    csp[(annees_etudes >= 15) & (salaire_etp > 3200)] = "Cadre"

    anciennete = np.minimum(experience, rng.gamma(2.0, 4.0, n)).round(0)

    df = pd.DataFrame({
        "id": np.arange(1, n + 1),
        "sexe": sexe,
        "age": age.round(0).astype(int),
        "diplome": diplome,
        "annees_etudes": annees_etudes.astype(int),
        "experience": experience.round(0).astype(int),
        "secteur": secteur,
        "csp": csp,
        "temps_travail": temps_travail,
        "heures_hebdo": heures.round(1),
        "anciennete": anciennete.astype(int),
        "salaire_net_mensuel": salaire.round(0),
    })

    df = _salir(df, rng)
    df.to_csv(DATA / "salaires.csv", index=False)
    print(f"  data/salaires.csv : {len(df)} lignes, {df.shape[1]} colonnes")

    # Le même échantillon au format Excel : la séance 4 doit montrer que
    # read_excel s'utilise exactement comme read_csv. Un extrait suffit, le
    # fichier est plus lourd que le CSV.
    df.head(500).to_excel(DATA / "salaires-extrait.xlsx", index=False)
    print("  data/salaires-extrait.xlsx : 500 lignes (démonstration read_excel)")


def _salir(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Introduit des défauts réalistes — support de la section « nettoyage ».

    Un jeu de données parfait ne permet pas d'enseigner le nettoyage. Les
    défauts posés ici sont ceux qu'on rencontre vraiment : non-réponse sur le
    salaire, codage du sexe hétérogène selon la source, âges impossibles,
    salaires saisis en annuel, et quelques doublons de collecte.
    """
    n = len(df)

    # Non-réponse sur le salaire (~6 %), comme dans toute enquête.
    manquants = rng.choice(n, size=int(0.06 * n), replace=False)
    df.loc[manquants, "salaire_net_mensuel"] = np.nan

    # Codage du sexe hétérogène (fichiers concaténés de sources différentes).
    incoherents = rng.choice(n, size=int(0.08 * n), replace=False)
    df.loc[incoherents, "sexe"] = df.loc[incoherents, "sexe"].map(
        {"Femme": "F", "Homme": "H"})

    # Âges impossibles (erreurs de saisie).
    for idx, valeur in zip(rng.choice(n, size=12, replace=False),
                           rng.choice([0, 1, 199, 999], size=12)):
        df.loc[idx, "age"] = valeur

    # Salaires saisis en annuel au lieu de mensuel : valeurs aberrantes.
    annuels = rng.choice(df.dropna(subset=["salaire_net_mensuel"]).index,
                         size=15, replace=False)
    df.loc[annuels, "salaire_net_mensuel"] *= 12

    # Doublons de collecte.
    doublons = df.loc[rng.choice(n, size=25, replace=False)]
    df = pd.concat([df, doublons], ignore_index=True)

    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Turnover RH — simulation
# ---------------------------------------------------------------------------

def build_rh(n: int = 1200) -> None:
    """Jeu RH d'entreprise fictif : qui démissionne, et pourquoi ?

    Terrain volontairement simple, proposé aux groupes qui veulent une
    question nette (déterminants du départ) sans avoir à affronter le
    nettoyage d'une enquête.
    """
    rng = np.random.default_rng(SEED + 1)

    departement = rng.choice(
        ["Production", "Commercial", "R&D", "Support", "Administratif"],
        size=n, p=[0.32, 0.22, 0.18, 0.16, 0.12])
    anciennete = rng.gamma(2.0, 3.2, n).clip(0, 35).round(1)
    age = (24 + anciennete + rng.gamma(2.0, 4.0, n)).clip(20, 64).round(0)
    salaire = (1800 + 55 * anciennete
               + rng.normal(0, 450, n)
               + np.where(departement == "R&D", 700, 0)
               + np.where(departement == "Commercial", 350, 0)).clip(1500, None)
    satisfaction = rng.integers(1, 6, n)
    heures_sup = rng.random(n) < 0.31
    distance_km = rng.gamma(2.0, 6.0, n).clip(0, 60).round(1)
    promotions = rng.poisson(anciennete / 6.0).clip(0, 6)

    # Probabilité de départ : insatisfaction, heures supplémentaires, absence
    # de promotion et éloignement pèsent dans le même sens.
    score = (-0.9
             - 0.42 * satisfaction
             + 0.75 * heures_sup
             - 0.28 * promotions
             + 0.022 * distance_km
             - 0.045 * anciennete
             + 0.8)   # constante calée pour un taux de démission ~18 %
    a_demissionne = rng.random(n) < 1 / (1 + np.exp(-score))

    pd.DataFrame({
        "id_salarie": np.arange(1, n + 1),
        "departement": departement,
        "age": age.astype(int),
        "anciennete": anciennete,
        "salaire_mensuel": salaire.round(0),
        "satisfaction": satisfaction,
        "heures_supplementaires": np.where(heures_sup, "Oui", "Non"),
        "distance_domicile_km": distance_km,
        "promotions": promotions,
        "a_demissionne": np.where(a_demissionne, "Oui", "Non"),
    }).to_csv(DATA / "rh-turnover.csv", index=False)
    print(f"  data/rh-turnover.csv : {n} lignes")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    try:
        build_chomage()
    except Exception as exc:                     # réseau indisponible
        print(f"  ⚠ chômage INSEE non rafraîchi ({exc}) — "
              f"le fichier versionné est conservé.", file=sys.stderr)
    print("▶ simulation des jeux de données individuels…")
    build_salaires()
    build_rh()
    print("✓ terminé.")


if __name__ == "__main__":
    main()

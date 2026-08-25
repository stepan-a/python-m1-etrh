# Jeux de données du cours

Trois fichiers, dans `data/`, tous reconstructibles par
`python3 scripts/prepare-data.py`. Ils sont versionnés pour que le cours
fonctionne hors ligne et dans le navigateur — voir « Pourquoi pas de
téléchargement » plus bas.

> **À lire avant d'utiliser ces données ailleurs que dans le cours.**
> `chomage-bit.csv` contient de **vraies statistiques INSEE**.
> `salaires.csv` et `rh-turnover.csv` sont **simulés**. Ils reproduisent les
> ordres de grandeur publiés, mais ce ne sont pas des observations : aucun
> résultat obtenu sur ces fichiers ne peut être cité comme un fait empirique.

---

## 1. `chomage-bit.csv` — données réelles

Taux de chômage au sens du Bureau international du travail, trimestriel.

| | |
|---|---|
| **Source** | INSEE, Banque de données macro-économiques, dataflow `CHOMAGE-TRIM-NATIONAL`, indicateur `CTTXC` |
| **Accès** | `https://bdm.insee.fr/series/sdmx/data/CHOMAGE-TRIM-NATIONAL` (SDMX, libre) |
| **Champ** | France hors Mayotte (`REF_AREA = FR-D976`), données CVS |
| **Période** | 1975-Q1 à 2026-Q2 — 2 472 lignes |
| **Licence** | Licence Ouverte / Open Licence (Etalab) |

Séries retenues : les 12 croisements sexe × âge encore actifs. Les séries
marquées `SERIE_ARRETEE` sont écartées.

| Variable | Type | Description |
|---|---|---|
| `trimestre` | texte | Trimestre au format `AAAA-Qn`, ex. `2026-Q2` |
| `annee` | entier | Année, extraite de `trimestre` |
| `num_trimestre` | entier | Numéro du trimestre, 1 à 4 |
| `sexe` | texte | `Ensemble`, `Hommes`, `Femmes` |
| `age` | texte | `Ensemble`, `Moins de 25 ans`, `25 à 49 ans`, `50 ans ou plus` |
| `taux_chomage` | décimal | Taux de chômage BIT, en % de la population active |

---

## 2. `salaires.csv` — données simulées

Échantillon individuel de 5 000 salariés (plus 25 doublons délibérés).

**Pourquoi simulé.** Le cours aurait dû s'appuyer sur les microdonnées de
l'enquête Emploi. Elles ne sont pas librement téléchargeables : leur accès
passe par une convention via Progedo/ADISP. Impossible, donc, de les
distribuer dans un dépôt public ou de les charger dans un navigateur. Le
fichier est donc engendré par simulation, **calibrée** pour que les faits
stylisés que les étudiants vont retrouver soient les bons.

**Calibrage.** Le salaire suit une équation de Mincer :

```
log(salaire) = 6.529 + 0.075 × années d'études
                     + 0.021 × expérience − 0.00032 × expérience²
                     − 0.135 × femme
                     + effet secteur + bruit
```

Ce que le fichier reproduit, une fois nettoyé :

| Grandeur | Fichier | Référence |
|---|---|---|
| Salaire net médian, temps complet | 2 099 € | ~2 100 € (INSEE, secteur privé) |
| Rendement d'une année d'études | 7,6 % | 7–8 % sur données françaises |
| Écart femmes-hommes à temps complet | 13,4 % | 14–15 % en EQTP (INSEE) |
| Part de temps partiel, femmes | 28,0 % | ~28 % |
| Part de temps partiel, hommes | 9,3 % | ~8 % |
| Rapport interdécile D9/D1 | 2,8 | ~3,0 |

*Limite connue* : la queue haute de la distribution est plus mince que dans
la réalité (pas de très hautes rémunérations), d'où un salaire **moyen** un
peu bas (2 292 € contre ~2 735 €). La médiane, elle, est juste.

**Défauts délibérés.** Le fichier est volontairement sale : c'est le support
de la section « nettoyage » de la séance 4. Un jeu propre ne permet pas
d'enseigner le nettoyage.

| Défaut | Ampleur | Ce qu'il fait travailler |
|---|---|---|
| Salaire manquant | ~6 % des lignes | `isna`, `dropna`, choix d'imputation |
| `sexe` codé `F`/`H` ou `Femme`/`Homme` | ~8 % des lignes | `replace`, `value_counts` |
| Âges impossibles (0, 1, 199, 999) | 12 lignes | filtrage, `describe` |
| Salaires saisis en annuel | 15 lignes | valeurs aberrantes, `quantile` |
| Doublons de collecte | 25 lignes | `duplicated`, `drop_duplicates` |

| Variable | Type | Description |
|---|---|---|
| `id` | entier | Identifiant de l'individu |
| `sexe` | texte | `Femme`/`Homme`, **ou** `F`/`H` (codage à harmoniser) |
| `age` | entier | Âge en années (contient des valeurs impossibles) |
| `diplome` | texte | 6 niveaux, de `Aucun diplôme` à `Bac+5 ou plus` |
| `annees_etudes` | entier | Durée théorique d'études, 7 à 17 ans |
| `experience` | entier | Années depuis la fin des études |
| `secteur` | texte | 8 secteurs d'activité |
| `csp` | texte | `Ouvrier`, `Employé`, `Profession intermédiaire`, `Cadre` |
| `temps_travail` | texte | `Temps complet` / `Temps partiel` |
| `heures_hebdo` | décimal | Heures hebdomadaires travaillées |
| `anciennete` | entier | Années dans l'entreprise actuelle |
| `salaire_net_mensuel` | décimal | Salaire net mensuel en euros (manquants et aberrants) |

---

## 3. `rh-turnover.csv` — données simulées

1 200 salariés d'une entreprise fictive. Terrain propre et question nette
(qui démissionne, et pourquoi ?), proposé aux groupes qui préfèrent
travailler l'analyse plutôt que le nettoyage.

La probabilité de démission suit un modèle logistique où l'insatisfaction,
les heures supplémentaires, l'absence de promotion et l'éloignement du
domicile poussent au départ, tandis que l'ancienneté retient.

| Variable | Type | Description |
|---|---|---|
| `id_salarie` | entier | Identifiant |
| `departement` | texte | `Production`, `Commercial`, `R&D`, `Support`, `Administratif` |
| `age` | entier | Âge en années |
| `anciennete` | décimal | Années dans l'entreprise |
| `salaire_mensuel` | décimal | Salaire mensuel en euros |
| `satisfaction` | entier | Score déclaré de 1 (très insatisfait) à 5 |
| `heures_supplementaires` | texte | `Oui` / `Non` |
| `distance_domicile_km` | décimal | Distance domicile-travail en km |
| `promotions` | entier | Nombre de promotions obtenues |
| `a_demissionne` | texte | `Oui` / `Non` — variable à expliquer |

---

## Pourquoi pas de téléchargement dans les notebooks

Aucun notebook du cours n'écrit `pd.read_csv("https://…")`, pour trois
raisons :

1. **Le navigateur ne peut pas.** En ligne, le cours tourne sous Pyodide, qui
   n'a pas de sockets : une requête réseau classique échoue.
2. **Le réseau de la salle n'est pas fiable**, et un TP qui dépend du wifi
   est un TP qui s'arrête.
3. **Les URL de l'INSEE changent** d'un millésime à l'autre. Un notebook
   distribué en septembre doit encore marcher en janvier.

Le téléchargement reste évidemment le geste normal hors du cours : c'est
`scripts/prepare-data.py` qui le fait, une fois, et qui documente ce qu'il a
fait. C'est aussi ce que les étudiants devront faire pour leur projet.

## Sources ouvertes pour les projets

INSEE ([insee.fr](https://www.insee.fr), [BDM SDMX](https://bdm.insee.fr)),
DARES, [data.gouv.fr](https://www.data.gouv.fr), Eurostat, OCDE.Stat.

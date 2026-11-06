# Module 1 — Algorithme d’analyse de zonages protégés

## Objectif
Algorithme de traitement QGIS (PyQGIS) qui, pour un territoire donné en Auvergne-Rhône-Alpes, identifie les zonages protégés qui le recoupent (ZNIEFF, Natura 2000, etc.) et calcule les surfaces concernées.
Données : DREAL AURA via datARA.

## Architecture

```mermaid
flowchart LR
    A[Territoire sélectionné] --> C[Extraction des zonages proches]
    B[Couches de zonages] --> C
    C --> D[Reprojection Lambert-93]
    D --> E[Réparation des géométries]
    E --> F[Intersection territoire x zonage]
    F --> G[Calcul surfaces/pourcentages]
    G --> H[Couche de résultat]
```

## Stack
- QGIS 3.x / PyQGIS
- Python 3

## Utilisation

### Prérequis
- QGIS 3.40+ avec PyQGIS
- Le dossier `src/scripts_traitement` ajouté dans
  `Préférences > Options > Traitement > Fournisseurs > Scripts`
- Les données téléchargées et placées dans `data/raw/` (voir section Données)

### Étapes

1. **Nettoyer le projet.** Avant toute exécution, vérifier qu'aucune couche
   résultant d'un essai précédent (nommée par défaut « Zonages recoupés »)
   n'est encore chargée dans le panneau des couches. La supprimer si besoin
   (clic droit > Supprimer la couche).

2. **Charger les données sources.** Glisser-déposer dans QGIS :
   - la couche du territoire (ex : `communes_73.geojson`)
   - les couches de zonages à analyser (ZNIEFF type 1, ZNIEFF type 2,
     Natura 2000 habitats, Natura 2000 oiseaux)

3. **Sélectionner le territoire d'étude.** Activer la couche de communes,
   utiliser l'outil « Sélectionner une entité » et cliquer sur la ou les
   commune(s) à analyser (surlignée(s) en jaune).

4. **Lancer l'outil.** Boîte à outils de traitements (`Ctrl+Alt+T`) >
   Scripts > Biodiversité AURA > *Zonages protégés d'un territoire*.

5. **Renseigner les paramètres :**
   - *Territoire* : la couche de communes, avec la case
     **« Entité(s) sélectionnée(s) uniquement »** cochée
   - *Couches de zonages* : cocher **uniquement** les couches sources
     (ne jamais inclure une couche de résultat d'un essai précédent)
   - *Zonages recoupés* : laisser « Créer une couche temporaire »

6. **Exécuter**, puis vérifier dans l'onglet Journal que la surface du
   territoire affichée est cohérente avec la zone sélectionnée.

7. **Contrôler le résultat** dans la table attributaire de la couche
   produite : un site = une ligne, avec un `pct_territoire` plausible
   (entre 0 et 100).

## Limites connues :

Pourcentage calculé par rapport à chaque commune individuellement ;
Esquilles filtrées sous 1 m²

## Exemple de résultat :

<img width="3507" height="2480" alt="ZNatura2000_DirectivesOiseaux" src="https://github.com/user-attachments/assets/4858018b-a0e9-4fa7-b575-9f01f3f55f4d" />

<img width="3507" height="2480" alt="ZNIEFF_Type1_Maurienne" src="https://github.com/user-attachments/assets/57932be6-c9a3-4187-967f-366a3010ccf8" />

<img width="3507" height="2480" alt="Zonages_recoupes_Maurienne" src="https://github.com/user-attachments/assets/171c9c44-0d90-4475-a311-4512740af3e5" />

<img width="3507" height="2480" alt="Attributs_Zonages_Recoupes" src="https://github.com/user-attachments/assets/b169c269-417b-4d5c-b4a9-2ae825decc1a" />



# Module 2 — Génération automatique de fiches diagnostic départementales

## Statut
🚧 En cours de développement

## Objectif
Algorithme qui génère automatiquement, pour chaque département d’AURA, une fiche PDF avec carte et statistiques de recouvrement par les zonages protégés (mise en page cartographique automatisée).

## Architecture
🚧 En cours de développement

## Stack
🚧 En cours de développement

## Utilisation
🚧 En cours de développement

## Limites connues 
🚧 En cours de développement

# Exemple de résultat 
<img width="1275" height="900" alt="fiche_73_Savoie" src="https://github.com/user-attachments/assets/0548eada-0bfa-42e8-8ac3-ee13affab38b" />
[![Aperçu de la fiche PDF](images/apercu.png)](outputs/fiches/fiche_73_Savoie.pdf)

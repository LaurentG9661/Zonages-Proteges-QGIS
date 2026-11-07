"""
Étape 2 du projet "Fiches PDF par département" : génère un PDF par
département, à partir du gabarit qgis/gabarit_fiche.qgz et des
statistiques calculées par calcul_stats_departements.py.

À exécuter dans la console Python de QGIS, après avoir ouvert le
projet qui contient les couches (départements + zonages).
"""

import os
from qgis.core import (
    QgsProject, QgsLayoutExporter, QgsRectangle,
    QgsVectorLayer, QgsFeature, QgsFields, QgsField, QgsCoordinateTransform
)
from qgis.PyQt.QtCore import QVariant

from pathlib import Path
# RACINE_PROJET = Path(r"C:\Users\Tonton\Documents\Projets_SIG\Zonages_Proteges") # chemin personnel pour une exécution dans la console QGIS
# DOSSIER_SORTIE = r"C:\Users\Tonton\Documents\Projets_SIG\Zonages_Proteges\outputs\fiches" # chemin personnel pour une exécution dans la console QGIS
RACINE_PROJET = Path(__file__).resolve().parents[2]
print('RACINE_PROJET  : ', RACINE_PROJET )
DOSSIER_SORTIE = RACINE_PROJET / "outputs" / "fiches"
print('DOSSIER_SORTIE : ', DOSSIER_SORTIE)
CHEMIN_GABARIT = RACINE_PROJET / "qgis" / "gabarit_fiche.qgz"
print('CHEMIN_GABARIT : ', CHEMIN_GABARIT)

NOM_MISE_EN_PAGE = "fiche_departement"  # nom donné dans l'éditeur de mise en page

NOMS_COUCHES_ZONAGES = [
    "ZNIEFF_Type1", "ZNIEFF_Type2", "ZonesNatura2000_DirHabitats", "ZonesNatura2000_DirOiseaux"
]


def stats_vers_couche_memoire(stats_departement):
    """Transforme la liste de dicts d'un département en couche QGIS temporaire, pour pouvoir l'afficher dans le tableau du gabarit."""
    couche = QgsVectorLayer("None", "stats_temp", "memory")
    champs = QgsFields()
    champs.append(QgsField("couche", QVariant.String))
    champs.append(QgsField("surface_ha", QVariant.Double))
    champs.append(QgsField("pct_departement", QVariant.Double))
    couche.dataProvider().addAttributes(champs)
    couche.updateFields()

    for ligne in stats_departement:
        f = QgsFeature(champs)
        f.setAttributes([ligne["couche"], ligne["surface_ha"], ligne["pct_departement"]])
        couche.dataProvider().addFeature(f)
    couche.updateExtents()
    return couche


def generer_toutes_les_fiches():
    from calcul_stats_departements import calculer_stats_departements

    projet = QgsProject.instance()
    if not projet.read(str(CHEMIN_GABARIT)):
        raise RuntimeError(f"Impossible de lire le projet : {CHEMIN_GABARIT}")

    gestionnaire = projet.layoutManager()
    mise_en_page = gestionnaire.layoutByName(NOM_MISE_EN_PAGE)
    if mise_en_page is None:
        raise RuntimeError(
            f"Mise en page '{NOM_MISE_EN_PAGE}' introuvable. "
            "Vérifie qu'elle existe dans le projet et que son nom correspond."
        )

    # Les stats de TOUS les départements, calculées une seule fois
    toutes_les_stats = calculer_stats_departements("departements-auvergne-rhone-alpes", NOMS_COUCHES_ZONAGES)

    departements_layer = projet.mapLayersByName("departements-auvergne-rhone-alpes")[0]
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

    cadre_carte = mise_en_page.itemById("carte_principale")  # id donné dans l'éditeur
    titre = mise_en_page.itemById("titre")
    tableau_inter = mise_en_page.itemById("tableau_stats")
    tableau = tableau_inter.multiFrame()

    transfo = QgsCoordinateTransform(departements_layer.crs(), cadre_carte.crs(), projet)

    for dept_feat in departements_layer.getFeatures():
        nom_dept = dept_feat["nom"]
        code_dept = dept_feat["code"]
        print(f"Génération de la fiche : {nom_dept}")

        # 1. Zoom de la carte sur l'emprise du département, avec une marge de 10 %
        emprise = transfo.transformBoundingBox(dept_feat.geometry().boundingBox())
        emprise.scale(1.1)
        cadre_carte.zoomToExtent(emprise)
        print(f"  échelle : 1/{cadre_carte.scale():.0f}")

        # 2. Mise à jour du titre
        titre.setText(f"Diagnostic biodiversité — {nom_dept}")

        # 3. Mise à jour du tableau : on filtre les stats de ce département
        stats_dept = [s for s in toutes_les_stats if s["code_insee"] == code_dept]
        couche_stats = stats_vers_couche_memoire(stats_dept)
        tableau.setVectorLayer(couche_stats)

        # 4. Export PDF
        exporteur = QgsLayoutExporter(mise_en_page)
        chemin_pdf = DOSSIER_SORTIE / f"fiche_{code_dept}_{nom_dept}.pdf"
        resultat = exporteur.exportToPdf(str(chemin_pdf), QgsLayoutExporter.PdfExportSettings())

        if resultat != QgsLayoutExporter.Success:
            print(f"  ⚠ Échec de l'export pour {nom_dept}")
        else:
            print(f"  ✓ {chemin_pdf}")

    # projet.read(str(CHEMIN_GABARIT)) # utile seulement pour une execution dans la console qgis



if __name__ == "__console__":
    generer_toutes_les_fiches()

if __name__ == "__main__": # Exécution autonome (hors interface QGIS). Besoin d'une initialisation “headless” de QGIS
    import sys
    sys.path.append(r"C:\Program Files\QGIS 3.40.15\apps\qgis-ltr\python\plugins")
    
    from qgis.core import QgsApplication
        
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.40.15\apps\qgis-ltr", True)
    qgs = QgsApplication([], True)   # True = moteur graphique activé (indispensable pour les PDF)
    qgs.initQgis()
    from processing.core.Processing import Processing
    Processing.initialize()
    try :
        generer_toutes_les_fiches()
    finally :
        qgs.exitQgis()

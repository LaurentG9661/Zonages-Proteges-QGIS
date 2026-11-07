"""
Étape 1 du projet "Fiches PDF par département" : calcule, pour chaque
département d'AURA, la surface et le pourcentage couverts par chaque
couche de zonage (ZNIEFF, Natura 2000...).

À exécuter dans la console Python de QGIS (Ctrl+Alt+P), après avoir
chargé la couche des départements et les couches de zonages.
"""

import processing
import os
from qgis.core import (
    QgsProject, QgsLayoutExporter, QgsRectangle,
    QgsVectorLayer, QgsFeature, QgsFields, QgsField,
)
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsCoordinateTransform

CRS_CALCUL = "EPSG:2154"


def couche(resultat, context):
    """Même logique que _couche/_executer dans l'algorithme principal : garantit qu'on manipule une vraie couche, pas un identifiant texte."""
    if isinstance(resultat, str):
        return context.getMapLayer(resultat)
    return resultat


def executer(algo, parametres, context, feedback):
    resultat = processing.run(
        algo, {**parametres, "OUTPUT": "TEMPORARY_OUTPUT"},
        context=context, feedback=feedback,
    )["OUTPUT"]
    return couche(resultat, context)


def calculer_stats_departements(nom_couche_departements, noms_couches_zonages):
    """
    nom_couche_departements : nom de la couche des départements, déjà chargée
    noms_couches_zonages : liste des noms des couches de zonages, déjà chargées

    Renvoie une liste de dicts :
    [{"departement": "Savoie", "code_insee": "73", "couche": "l_znieff1_s_r84", "surface_ha": 12345.6, "pct_departement": 23.4}, ...]
    """
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    projet = QgsProject.instance()

    departements = projet.mapLayersByName(nom_couche_departements)[0]
    departements_2154 = executer(
        "native:reprojectlayer",
        {"INPUT": departements, "TARGET_CRS": CRS_CALCUL}, context, feedback
    )

    resultats = []

    # On traite chaque département séparément (contrairement à l'outil "zonages protégés", ici on veut un total par département, pas par commune)
    for dept_feat in departements_2154.getFeatures():
        nom_dept = dept_feat["nom"]
        code_dept = dept_feat["code"]
        surface_dept = dept_feat.geometry().area()
        print(f"--- {nom_dept} ({code_dept}) : {surface_dept / 10000:.0f} ha ---")

        # Un territoire "à la volée" ne contenant que ce département, réutilisable tel quel avec native:extractbylocation / intersection
        territoire_dept = executer(
            "native:extractbyexpression",
            {"INPUT": departements_2154, "EXPRESSION": f'"code" = \'{code_dept}\''},
            context, feedback,
        )

        for nom_couche_zonage in noms_couches_zonages:
            zonage = projet.mapLayersByName(nom_couche_zonage)[0]

            proches = executer(
                "native:extractbylocation",
                {"INPUT": zonage, "PREDICATE": [0], "INTERSECT": territoire_dept},
                context, feedback,
            )
            if proches.featureCount() == 0:
                resultats.append({
                    "departement": nom_dept, "code_insee": code_dept,
                    "couche": nom_couche_zonage,
                    "surface_ha": 0.0, "pct_departement": 0.0,
                })
                continue

            zonage_2154 = executer(
                "native:reprojectlayer",
                {"INPUT": proches, "TARGET_CRS": CRS_CALCUL}, context, feedback
            )
            zonage_ok = executer(
                "native:fixgeometries", {"INPUT": zonage_2154}, context, feedback
            )
            # dissolve : on ne veut qu'UN total par (département, couche), pas une ligne par site -> on fusionne avant de sommer
            inter = executer(
                "native:intersection",
                {"INPUT": zonage_ok, "OVERLAY": territoire_dept}, context, feedback
            )
            fusion = executer("native:dissolve", {"INPUT": inter}, context, feedback)

            surface_totale = sum(
                f.geometry().area() for f in fusion.getFeatures()
                if not f.geometry().isNull() and not f.geometry().isEmpty()
            )

            resultats.append({
                "departement": nom_dept,
                "code_insee": code_dept,
                "couche": nom_couche_zonage,
                "surface_ha": round(surface_totale / 10000, 2),
                "pct_departement": round(surface_totale / surface_dept * 100, 2),
            })

    return resultats


# --- Utilisation (à adapter aux noms réels de tes couches chargées) ---
if __name__ == "__console__":
    stats = calculer_stats_departements(
        "departements-auvergne-rhone-alpes",
        ["ZNIEFF_Type1", "ZNIEFF_Type2", "ZonesNatura2000_DirHabitats", "ZonesNatura2000_DirOiseaux"],
    )
    for ligne in stats:
        print(ligne)
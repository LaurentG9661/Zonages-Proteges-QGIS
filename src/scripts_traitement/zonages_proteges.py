"""Algorithme de traitement QGIS : zonages protégés d'un territoire (AURA)."""

from qgis.core import (
    NULL,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterMultipleLayers,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant
import processing

CRS_CALCUL = "EPSG:2154"  # Lambert-93 : les surfaces sortent en m²


class ZonagesProtegesAlgorithm(QgsProcessingAlgorithm):
    # Identifiants internes des 3 paramètres (entrées/sortie)
    TERRITOIRE = "TERRITOIRE"
    ZONAGES = "ZONAGES"
    SORTIE = "SORTIE"

    # ---------- 1) Carte d'identité de l'algorithme (obligatoire) ----------

    def name(self):
        return "zonages_proteges"  # identifiant technique

    def displayName(self):
        return "Zonages protégés d'un territoire"  # nom affiché

    def group(self):
        return "Biodiversité AURA"  # dossier dans la boîte à outils

    def groupId(self):
        return "biodiversite_aura"

    def createInstance(self):
        return ZonagesProtegesAlgorithm()  # QGIS crée une copie à chaque lancement

    # ---------- 2) Les paramètres : ce qui construit la fenêtre ----------

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TERRITOIRE, "Territoire (polygones)",
                [QgsProcessing.TypeVectorPolygon],
            )
        )
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.ZONAGES, "Couches de zonages",
                QgsProcessing.TypeVectorPolygon,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.SORTIE, "Zonages recoupés", QgsProcessing.TypeVectorPolygon
            )
        )

    # ---------- 3) Petits outils internes ----------

    def _executer(self, algo, parametres, context, feedback):
        """Lance un outil QGIS et renvoie toujours une vraie couche."""
        resultat = processing.run(
            algo,
            {**parametres, "OUTPUT": "TEMPORARY_OUTPUT"},
            context=context,
            feedback=feedback,
        )["OUTPUT"]
        # Selon le contexte, on reçoit une couche ou son identifiant (texte)
        if isinstance(resultat, str):
            return context.getMapLayer(resultat)
        return resultat

    def _premier_champ(self, couche, candidats):
        """Renvoie le premier nom de champ qui existe dans la couche."""
        for c in candidats:
            if couche.fields().indexFromName(c) >= 0:
                return c
        return None

    def _texte(self, valeur):
        """Convertit en texte, en gardant les valeurs vides vides."""
        return None if valeur is None or valeur == NULL else str(valeur)

    # ---------- 4) Le travail : exécuté quand on clique sur « Exécuter » ----------

    def processAlgorithm(self, parameters, context, feedback):
        # a) Lecture des entrées
        zonages = self.parameterAsLayerList(parameters, self.ZONAGES, context)
        if not zonages:
            raise QgsProcessingException("Aucune couche de zonage fournie.")

        # On passe le paramètre brut pour respecter la sélection d'entités
        territoire = self._executer(
            "native:reprojectlayer",
            {"INPUT": parameters[self.TERRITOIRE], "TARGET_CRS": CRS_CALCUL},
            context, feedback,
        )
        if territoire is None or territoire.featureCount() == 0:
            raise QgsProcessingException(
                "Territoire vide : vérifie qu'une commune est bien sélectionnée."
            )
        # Fusion de toutes les communes en un seul polygone
        territoire = self._executer(
            "native:dissolve", {"INPUT": territoire}, context, feedback
        )
        surface_territoire = sum(f.geometry().area() for f in territoire.getFeatures())
        
        if surface_territoire == 0:
            raise QgsProcessingException("Surface du territoire nulle.")
        feedback.pushInfo(f"Territoire : {surface_territoire / 10000:.0f} ha")

        # b) Structure (colonnes) de la couche de sortie
        champs = QgsFields()
        champs.append(QgsField("couche", QVariant.String))
        champs.append(QgsField("nom_site", QVariant.String))
        champs.append(QgsField("id_site", QVariant.String))
        champs.append(QgsField("surface_ha", QVariant.Double))
        champs.append(QgsField("pct_territoire", QVariant.Double))

        sink, dest_id = self.parameterAsSink(
            parameters, self.SORTIE, context, champs,
            QgsWkbTypes.MultiPolygon, QgsCoordinateReferenceSystem(CRS_CALCUL),
        )
        if sink is None:
            raise self.invalidSinkError(parameters, self.SORTIE)

        # c) Boucle : une couche de zonage après l'autre
        for i, zonage in enumerate(zonages):
            if feedback.isCanceled():
                break
            feedback.setProgress(int(i / len(zonages) * 100))
            feedback.pushInfo(f"Traitement de : {zonage.name()}")

            # Noms des colonnes « nom » et « identifiant » selon la couche
            champ_nom = self._premier_champ(zonage, ["nom"])
            champ_id = self._premier_champ(zonage, ["id_mnhn", "cd_sig"])

            # 1. On ne garde que les sites qui touchent le territoire (rapide)
            proches = self._executer(
                "native:extractbylocation",
                {"INPUT": zonage, "PREDICATE": [0], "INTERSECT": territoire},
                context, feedback,
            )
            if proches.featureCount() == 0:
                feedback.pushInfo("  Aucun site dans ce territoire.")
                continue

            # 2. Reprojection en Lambert-93
            zonage_2154 = self._executer(
                "native:reprojectlayer",
                {"INPUT": proches, "TARGET_CRS": CRS_CALCUL},
                context, feedback,
            )
            # 3. Réparation des géométries invalides
            zonage_ok = self._executer(
                "native:fixgeometries", {"INPUT": zonage_2154}, context, feedback
            )
            # 4. Découpe des sites par le territoire
            inter = self._executer(
                "native:intersection",
                {"INPUT": zonage_ok, "OVERLAY": territoire},
                context, feedback,
            )

            # 5. Calcul des surfaces et écriture dans la sortie
            for feat in inter.getFeatures():
                geom = feat.geometry()
                if geom.isNull() or geom.isEmpty():
                    continue
                geom.convertToMultiType()
                surface = geom.area()  # en m²

                f = QgsFeature(champs)
                f.setGeometry(geom)
                f.setAttributes([
                    zonage.name(),
                    self._texte(feat[champ_nom]) if champ_nom else None,
                    self._texte(feat[champ_id]) if champ_id else None,
                    round(surface / 10000, 2),  # m² -> hectares
                    round(surface / surface_territoire * 100, 2),
                ])
                sink.addFeature(f, QgsFeatureSink.FastInsert)

        feedback.setProgress(100)
        return {self.SORTIE: dest_id}  # QGIS charge cette couche dans le projet
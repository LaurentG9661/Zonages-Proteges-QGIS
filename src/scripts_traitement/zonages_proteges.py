from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsFeature,
    QgsFeatureSink,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
)
from qgis.PyQt.QtCore import QVariant
import processing

CRS_CALCUL = "EPSG:2154"  # Lambert-93 : surfaces en m²


class ZonagesProtegesAlgorithm(QgsProcessingAlgorithm):
    TERRITOIRE = "TERRITOIRE"
    ZONAGES = "ZONAGES"
    SORTIE = "SORTIE"

    def name(self):
        return "zonages_proteges"

    def displayName(self):
        return "Zonages protégés d'un territoire"

    def group(self):
        return "Biodiversité AURA"

    def groupId(self):
        return "biodiversite_aura"

    def createInstance(self):
        return ZonagesProtegesAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TERRITOIRE,
                "Territoire (polygones)",
                [QgsProcessing.TypeVectorPolygon],
            )
        )
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.ZONAGES,
                "Couches de zonages",
                QgsProcessing.TypeVectorPolygon,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.SORTIE, "Zonages recoupés")
        )

    def _reprojeter(self, couche, context, feedback):
        return processing.run(
            "native:reprojectlayer",
            {"INPUT": couche, "TARGET_CRS": CRS_CALCUL, "OUTPUT": "memory:"},
            context=context,
            feedback=feedback,
        )["OUTPUT"]

    def processAlgorithm(self, parameters, context, feedback):
        territoire = self.parameterAsVectorLayer(parameters, self.TERRITOIRE, context)
        zonages = self.parameterAsLayerList(parameters, self.ZONAGES, context)
        if territoire is None or not zonages:
            raise QgsProcessingException("Territoire ou zonages manquants.")

        territoire = self._reprojeter(territoire, context, feedback)
        surface_territoire = sum(f.geometry().area() for f in territoire.getFeatures())
        if surface_territoire == 0:
            raise QgsProcessingException("Surface du territoire nulle.")

        champs = QgsFields()
        champs.append(QgsField("couche", QVariant.String))
        champs.append(QgsField("surface_ha", QVariant.Double))
        champs.append(QgsField("pct_territoire", QVariant.Double))

        sink, dest_id = self.parameterAsSink(
            parameters, self.SORTIE, context, champs,
            QgsWkbTypes.MultiPolygon, QgsCoordinateReferenceSystem(CRS_CALCUL),
        )

        for i, zonage in enumerate(zonages):
            if feedback.isCanceled():
                break
            feedback.pushInfo(f"Traitement de : {zonage.name()}")

            zonage_2154 = self._reprojeter(zonage, context, feedback)
            # Si l'intersection échoue sur une géométrie invalide,
            # ajouter d'abord native:fixgeometries
            inter = processing.run(
                "native:intersection",
                {"INPUT": zonage_2154, "OVERLAY": territoire, "OUTPUT": "memory:"},
                context=context,
                feedback=feedback,
            )["OUTPUT"]

            for feat in inter.getFeatures():
                geom = feat.geometry()
                geom.convertToMultiType()
                surface = geom.area()
                f = QgsFeature(champs)
                f.setGeometry(geom)
                f.setAttributes([
                    zonage.name(),
                    round(surface / 10000, 2),
                    round(surface / surface_territoire * 100, 2),
                ])
                sink.addFeature(f, QgsFeatureSink.FastInsert)

            feedback.setProgress(int((i + 1) / len(zonages) * 100))

        return {self.SORTIE: dest_id}
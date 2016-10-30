package org.datakind.ci.pdfestrian.extraction

import org.datakind.ci.pdfestrian.api.{Metadata, MetadataExtractor, Record}

/**
  * Created by sam on 10/26/16.
  */
class MetadataClassifier extends MetadataExtractor {

  val metadataMap = Map(
    "biome" -> new BiomeClassifier("/biomeRankerTest"),
    "interv" -> new IntervClassifier("/intervRankerTest"),
    "outcome" -> new OutcomeClassifier("/OutcomeRankerTest")
  )

  override def getMetaData(record: Record, metaData: String): Seq[Metadata] = {
    metadataMap.get(metaData.toLowerCase()) match {
      case None => Seq()
      case Some(m) => m.getMetaData(record, metaData)
    }
  }
}

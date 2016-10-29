package org.datakind.ci.pdfestrian.api

trait MetadataExtraction {
  val metaDataExtractor : MetadataExtractor
  def getMetaData(record : Record, metaData : String) : Seq[Metadata] = metaDataExtractor.getMetaData(record, metaData)
}
trait MetadataExtractor {
  def getMetaData(record : Record, metaData : String) : Seq[Metadata]
}

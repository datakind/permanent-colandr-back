package org.datakind.ci.pdfestrian.api

class DummyMetadataExtractor extends MetadataExtractor {
  def getMetaData(record: Record, metaData: String) = Seq()
}
class DummyLocationExtractor extends LocationExtractor {
  def getLocations(record : Record) = Seq()
}
class DummyFileRetriever extends Access {
  def getFile(record: String): Option[Record] = None
}
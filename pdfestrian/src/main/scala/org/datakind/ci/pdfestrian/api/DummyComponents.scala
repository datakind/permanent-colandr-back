package org.datakind.ci.pdfestrian.api

class DummyMetadataExtractor extends AllMetaDataExtractor {
  def extractData(record: Record, min : Int, numMoreDataToRetrain : Int, threshold : Double) : Seq[Metadata] = Seq()
}
class DummyLocationExtractor extends LocationExtractor {
  def getLocations(record : Record) = Seq()
}
class DummyFileRetriever extends Access {
  def getFile(record: String): Option[Record] = None
}
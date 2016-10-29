package org.datakind.ci.pdfestrian.api

trait LocationExtraction {
  val locationExtractor : LocationExtractor
  def getLocations(record : Record) = locationExtractor.getLocations(record)
}

trait LocationExtractor {
  def getLocations(record : Record) : Seq[Metadata]
}


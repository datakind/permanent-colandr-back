package org.datakind.ci.pdfestrian.api.apiservice.components

import org.datakind.ci.pdfestrian.api.apiservice.{Metadata, Record}

/**
  * Location extraction component, needs to be mixed into APIservice
  */
trait LocationExtraction {
  val locationExtractor : LocationExtractor

  /**
    * Get predicted location from record
    * @param record DB record
    * @return predicted Locations
    */
  def getLocations(record : Record) = locationExtractor.getLocations(record)
}

trait LocationExtractor {
  /**
    * Get predicted location from record
    * @param record DB record
    * @return predicted Locations
    */
  def getLocations(record : Record) : Seq[Metadata]
}
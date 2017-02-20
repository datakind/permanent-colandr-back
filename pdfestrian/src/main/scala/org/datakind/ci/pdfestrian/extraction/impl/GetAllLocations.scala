package org.datakind.ci.pdfestrian.extraction.impl

import org.datakind.ci.pdfestrian.api.apiservice.{Metadata, Record}
import org.datakind.ci.pdfestrian.api.apiservice.components.LocationExtractor
import org.datakind.ci.pdfestrian.extraction.GetLocations

/**
  * Implements LocationExtractor for getAlllocations. Works by simply getting all location mentions
  * from the document, and ranking them by # of times they are seen in the document
  */
class GetAllLocations extends LocationExtractor {

  /**
    * Gets all locations from record
    * @param record DB record
    * @return predicted Locations
    */
  def getLocations(record : Record) : Seq[Metadata] = {

    GetLocations.groupedLocations(record.content).toSeq.
      sortBy(-_._2.length)  // sort by # of sentences containing DESC
      .map{ case (location, sentences) =>

        val sortedSentences = sentences.sortBy(_._3) // sort by location in document

        Metadata(record.id.toString,
          "location",
          location,
          sentences.map(_._1).mkString("\n"),
          sortedSentences.head._3,
          1.0)

      }

  }

}

package org.datakind.ci.pdfestrian.api

/**
  * Metadata is returned predictions from API
  * @param record Identifier for record (usually recordId)
  * @param metaData The labelname of the metadata returned  (e.x. biome)
  * @param value The label of the metadata returned  (e.x. forest)
  * @param sentence Context from where the ML model predicted the value
  * @param sentenceLocation The location in the fulltext sentence can be found
  * @param confidence The probability under the model for the returned label
  */
case class Metadata(record : String,
                    metaData : String,
                    value : String,
                    sentence : String,
                    sentenceLocation : Int,
                    confidence : Double)
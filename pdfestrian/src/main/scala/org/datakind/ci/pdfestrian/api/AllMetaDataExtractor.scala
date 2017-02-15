package org.datakind.ci.pdfestrian.api

import org.datakind.ci.pdfestrian.extraction.ReviewTrainer
import org.json4s.jackson.Serialization._

/**
  * Created by sam on 2/14/17.
  */
trait AllMetaDataExtraction {
  val minimum : Int
  val numMoreDataToRetrain : Int
  val allMetaDataExtractor : AllMetaDataExtractor

  def extractData(record: Record) : Seq[Metadata] = allMetaDataExtractor.extractData(record, minimum, numMoreDataToRetrain)
}

trait AllMetaDataExtractor {
  def extractData(record: Record, min : Int, numMoreDataToRetrain : Int) : Seq[Metadata]
}

class ReviewMetadataExtractor extends AllMetaDataExtractor {

  def extractData(record: Record, min : Int, numMoreDataToRetrain : Int): Seq[Metadata] = {
    ReviewTrainer.getModel(record.reviewId, min, numMoreDataToRetrain) match {
      case None => Seq()
      case Some(model) => model.classifier match {
        case None => Seq()
        case Some(m) => m.getMetaData(record)
      }
    }
  }
}
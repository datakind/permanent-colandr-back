package org.datakind.ci.pdfestrian.api

import org.datakind.ci.pdfestrian.extraction.ReviewTrainer
import org.json4s.jackson.Serialization._

/**
  * Created by sam on 2/14/17.
  */
trait AllMetaDataExtraction {
  val minimum : Int
  val numMoreDataToRetrain : Int
  val threshold : Double
  val allMetaDataExtractor : AllMetaDataExtractor

  def extractData(record: Record) : Seq[Metadata] =
    allMetaDataExtractor.extractData(record, minimum, numMoreDataToRetrain, threshold)
}

trait AllMetaDataExtractor {
  def extractData(record: Record, min : Int, numMoreDataToRetrain : Int, threshold : Double) : Seq[Metadata]
}

class ReviewMetadataExtractor extends AllMetaDataExtractor {

  def extractData(record: Record, min : Int, numMoreDataToRetrain : Int, threshold : Double): Seq[Metadata] = {
    ReviewTrainer.getModel(record.reviewId, min, numMoreDataToRetrain) match {
      case None => Seq()
      case Some(model) => model.classifier match {
        case None => Seq()
        case Some(m) =>
          m.getMetaData(record, threshold).groupBy(_.metaData)
            .map{ case (metadata, extractions) =>
              extractions.groupBy(_.value).toSeq.map(_._2).toArray
                .sortBy(-_.head.confidence).flatten
            }.toSeq.sortBy(-_.head.confidence).flatten
      }
    }
  }
}
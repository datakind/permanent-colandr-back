package org.datakind.ci.pdfestrian.api.apiservice.components

import org.datakind.ci.pdfestrian.api.apiservice.{Metadata, Record}

/**
  * Component to be mixed in to APIService, representing providing general metadata extraction.
  */
trait AllMetaDataExtraction {
  /**
    * Minimum # of documents for training to start
    */
  val minimum : Int
  /**
    * # of new labels needed to retrain classifier
    */
  val numMoreDataToRetrain : Int
  /**
    * Probability threshold to return a metadata
    */
  val threshold : Double

  /**
    * Implementation of metadata extraction
    */
  val allMetaDataExtractor : AllMetaDataExtractor

  /**
    * Takes in a DB record, and returns a seq to predicted metadata
    * @param record DB record
    * @return predicted metadata
    */
  def extractData(record: Record) : Seq[Metadata] =
    allMetaDataExtractor.extractData(record, minimum, numMoreDataToRetrain, threshold)
}

/**
  * Implementation trait of metadata extractor. Extractor implementations should extend this..
  */
trait AllMetaDataExtractor {
  /**
    * Extracts metadata
    * @param record DB record
    * @param min Minimum # of documents for training to start
    * @param numMoreDataToRetrain # of new labels needed to retrain classifier
    * @param threshold Probability threshold to return a metadata
    * @return Seq of predicted metadata
    */
  def extractData(record: Record, min : Int, numMoreDataToRetrain : Int, threshold : Double) : Seq[Metadata]
}
package org.datakind.ci.pdfestrian.api.apiservice.components

import org.datakind.ci.pdfestrian.api.apiservice.Record
import org.datakind.ci.pdfestrian.trainingData.{GetTrainingData, TrainingData}

/**
  * Trait to be mixed in to APIservice to implement access to a record
  */
trait FileRetriever {
  val access : Access

  /**
    * Gets a record from an id
    * @param record record id
    * @return Option, record returned if id exists, None otherwise
    */
  def getFile(record : String) : Option[Record] = access.getFile(record)

  /**
    * Get all training data from a review
    * @param review the id of the review
    * @return an array of [[TrainingData]] instances
    */
  def getTrainingData(review : Int) = access.getTrainingData(review)

  /**
    * Gets all the training data from the review, but doesn't get the fulltext
    * @param review the id of the review
    * @return an array of [[TrainingData]] instances with empty fulltext content
    */
  def getTrainingLabels(review : Int) = access.getTrainingLabels(review)

}

/**
  * Trait to implement record access
  */
trait Access {
  /**
    * Gets a record from an id
    * @param record record id
    * @return Option, record returned if id exists, None otherwise
    */
  def getFile(record : String) : Option[Record]

  /**
    * Get all training data from a review
    * @param review the id of the review
    * @return an array of [[TrainingData]] instances
    */
  def getTrainingData(review : Int) : Array[TrainingData]

  /**
    * Gets all the training data from the review, but doesn't get the fulltext
    * @param review the id of the review
    * @return an array of [[TrainingData]] instances with empty fulltext content
    */
  def getTrainingLabels(review : Int) : Array[TrainingData]

}
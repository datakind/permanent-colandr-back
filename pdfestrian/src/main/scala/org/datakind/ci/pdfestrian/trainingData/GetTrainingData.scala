package org.datakind.ci.pdfestrian.trainingData

import java.sql.ResultSet

import org.datakind.ci.pdfestrian.db.Datasource
import org.json4s.DefaultFormats
import org.json4s.jackson.Serialization._

import scala.collection.mutable.ListBuffer

/**
  * Class that gets training data from a review
  */
class GetTrainingData {
  implicit val formats = DefaultFormats

  /**
    * Get all training data from a review
    * @param reviewId the id of the review
    * @return an array of [[TrainingData]] instances
    */
  def getTrainingData(reviewId : Int) : Array[TrainingData] = {
    val cx = Datasource.getConnection
    val query = cx.prepareStatement("select f.id, de.extracted_items, f.text_content from data_extractions as de inner join fulltexts as f on f.id=de.id where extracted_items != '{}' and extracted_items != '[]' and f.review_id=?")
    try {
      query.setInt(1, reviewId)
      toRecord(query.executeQuery())
    } finally {
      query.close()
      cx.close()
    }
  }

  /**
    * Gets all the training data from the review, but doesn't get the fulltext
    * @param reviewId the id of the review
    * @return an array of [[TrainingData]] instances with empty fulltext content
    */
  def getLabels(reviewId : Int) : Array[TrainingData] = {
    val cx = Datasource.getConnection
    val query = cx.prepareStatement("select de.id, de.extracted_items from data_extractions as de where extracted_items != '{}' and extracted_items != '[]' and de.review_id=?")
    try {
      query.setInt(1, reviewId)
      labelsToRecord(query.executeQuery())
    } finally {
      query.close()
      cx.close()
    }
  }

  private def labelsToRecord(results : ResultSet) : Array[TrainingData] = {
    getItems(results, results => {
      val id = results.getInt(1)
      val labels = read[Array[JLabel]](results.getString(2)).map(_.toLabel)

      TrainingData(id, "", labels)
    }).filter(_.fullText != null).toArray
  }

  private def toRecord(results : ResultSet) : Array[TrainingData] = {
    getItems(results, results => {
      val id = results.getInt(1)
      val text = results.getString(3)
      val labels = read[Array[JLabel]](results.getString(2)).map(_.toLabel)

      TrainingData(id, text, labels)
    }).filter(_.fullText != null).toArray
  }

  private def getItems[E](results : ResultSet, getItem : ResultSet => E) : Traversable[E] = {
    val items = new ListBuffer[E]
    while(results.next())
      items += getItem(results)
    items
  }
}
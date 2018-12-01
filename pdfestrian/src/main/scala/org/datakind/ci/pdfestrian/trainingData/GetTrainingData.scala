package org.datakind.ci.pdfestrian.trainingData

import java.sql.ResultSet

import org.datakind.ci.pdfestrian.db.Datasource
import org.json4s.DefaultFormats
import org.json4s.jackson.Serialization._
import org.slf4j.LoggerFactory

import scala.collection.mutable.ListBuffer

/**
  * Class that gets training data from a review
  */
class GetTrainingData {

  private val logger = LoggerFactory.getLogger(this.getClass)

  implicit val formats = DefaultFormats

  case class RecordType(label: String, field_type: String, description: String, allowed_values : Option[Array[String]]) {
    def trim() : RecordType = {
      this.copy(label = this.label.trim, field_type = this.field_type.trim, description = this.description.trim, allowed_values.map{ _.map(_.trim)} )
    }
  }

  private val validTypes = Set("select_one", "select_many")

  def getExtractionForm(reviewId : Int) : Array[RecordType] = {
    val cx = Datasource.getConnection
    val query = cx.prepareStatement("""select data_extraction_form from review_plans where id = ?""")
    try {
      query.setInt(1, reviewId)
      val form = getItems(query.executeQuery(), results =>
        read[Array[RecordType]](results.getString(1))
      ).headOption.getOrElse(Array()).map(_.trim())
      logger.info(s"Get extraction form for review $reviewId, ${form.mkString(",")}")
      form
    } finally {
      query.close()
      cx.close()
    }
  }

  def filterValid(labelTypes : Array[RecordType], trainingData: Array[TrainingData]) : Array[TrainingData] = {
    val validLabels = labelTypes.filter(lt => validTypes.contains(lt.field_type)).map{_.label}.toSet
    trainingData.map{ td =>
      val newLabels = td.labels.filter{ l =>
        validLabels.contains(l.label)
      }
      td.copy(labels = newLabels)
    }
  }

  /**
    * Get all training data from a review
    * @param reviewId the id of the review
    * @return an array of [[TrainingData]] instances
    */
  def getTrainingData(reviewId : Int) : Array[TrainingData] = {
    val extractionForm = getExtractionForm(reviewId)
    val cx = Datasource.getConnection
    val query = cx.prepareStatement("select f.id, de.extracted_items, f.text_content from data_extractions as de " +
      "inner join fulltexts as f on f.id=de.id " +
      "where extracted_items != '{}' and " +
      "extracted_items != '[]' and " +
      "f.review_id=? and f.text_content IS NOT NULL")
    try {
      query.setInt(1, reviewId)
      filterValid(extractionForm, toRecord(query.executeQuery()))
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
    val extractionForm = getExtractionForm(reviewId)
    val cx = Datasource.getConnection
    val query = cx.prepareStatement("select f.id, de.extracted_items from data_extractions as de " +
      "inner join fulltexts as f on f.id=de.id " +
      "where extracted_items != '{}' and " +
      "extracted_items != '[]' and " +
      "f.review_id=? and f.text_content IS NOT NULL")
    try {
      query.setInt(1, reviewId)
      filterValid(extractionForm, labelsToRecord(query.executeQuery()))
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
package org.datakind.ci.pdfestrian.extraction

import java.sql.ResultSet

import org.datakind.ci.pdfestrian.api.{Datasource, Record}
import org.json4s.DefaultFormats
import org.json4s.JsonAST.JValue
import org.json4s.jackson.Serialization.{read, write}
import org.json4s.jackson.JsonMethods.parse

import scala.collection.mutable.ListBuffer

/**
  * Created by sameyeam on 2/8/17.
  */
/**
  * Example:
  *    [{"label": "intervention_type", "value": ["area protection", "enterprises and livelihood alternatives", "policies and regulations"]},
  *    {"label": "outcome_type", "value": ["economic living standards", "governance and empowerment", "material living standards"]}]
  * @param label label name
  * @param value value
  */
case class JLabel(label : String, value : JValue) {
   def toLabel : Label = {
      value.children.length match {
         case 0 => SingleValue(label, value.values.toString)
         case _ => MultiValue(label, value.children.map(_.values.toString).toArray)
      }
   }
}
trait Label
case class MultiValue(label : String, value : Array[String]) extends Label
case class SingleValue(label : String, value : String) extends Label

case class TrainingData(id : Int, fullText : String, labels : Array[Label])
class GetTrainingData {
   implicit val formats = DefaultFormats
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

   def toRecord(results : ResultSet) : Array[TrainingData] = {
      getItems(results, results => {
         val id = results.getInt(1)
         val text = results.getString(3)
         val labels = read[Array[JLabel]](results.getString(2)).map(_.toLabel)

         TrainingData(id, text, labels)
      }).filter(_.fullText != null).toArray
   }

   def getItems[E](results : ResultSet, getItem : ResultSet => E) : Traversable[E] = {
      val items = new ListBuffer[E]
      while(results.next())
         items += getItem(results)
      items
   }
}

object GetTrainingData {
   implicit val formats = DefaultFormats

  def apply(review : Int) = (new GetTrainingData).getTrainingData(review)

   def main(args: Array[String]): Unit = {
      val gtd = new GetTrainingData
      println(write(gtd.getTrainingData(1)))
   }

}

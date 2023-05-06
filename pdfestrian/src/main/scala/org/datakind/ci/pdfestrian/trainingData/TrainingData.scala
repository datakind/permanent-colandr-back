package org.datakind.ci.pdfestrian.trainingData

import org.json4s.JsonAST.JValue

/**
  * Label whose value is a json value
  * Example:
  *    [{"label": "intervention_type", "value": ["area protection", "enterprises and livelihood alternatives", "policies and regulations"]},
  *    {"label": "outcome_type", "value": ["economic living standards", "governance and empowerment", "material living standards"]}]
  * @param label label name
  * @param value value
  */
case class JLabel(label : String, value : JValue) {
  /**
    * Converts JLabel into a label by parsing the values in the label
    * @return
    */
  def toLabel : Label = {
    value.children.length match {
      case 0 => SingleValue(label, value.values.toString)
      case _ => MultiValue(label, value.children.map(_.values.toString).toArray)
    }
  }
}

trait Label {
  val label : String
}

/**
  * Label which contains multiple values
  * @param label label name
  * @param value values of label
  */
case class MultiValue(label : String, value : Array[String]) extends Label

/**
  * Label which contains a single value
  * @param label label name
  * @param value value of label
  */
case class SingleValue(label : String, value : String) extends Label

/**
  * Training data
  * @param id id of the record
  * @param fullText the fulltext content of the record
  * @param labels labels associated with the record
  */
case class TrainingData(id : Int, fullText : String, labels : Array[Label])

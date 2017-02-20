package org.datakind.ci.pdfestrian.extraction.review

sealed trait ValueType
object Multi extends ValueType
object Single extends ValueType

/**
  * Review label types, stored in a classifier
  * @param labelName name of a review
  * @param allowedValues allowed values
  * @param value single or multi
  * @param trainingSize # of examples of label
  */
case class ReviewLabel(labelName : String, allowedValues : Set[String], value : ValueType, trainingSize : Int)
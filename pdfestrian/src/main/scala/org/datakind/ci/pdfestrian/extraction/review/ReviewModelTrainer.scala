package org.datakind.ci.pdfestrian.extraction.review

import org.datakind.ci.pdfestrian.api.apiservice.components.Access
import org.datakind.ci.pdfestrian.document.PDFToDocument
import org.datakind.ci.pdfestrian.extraction.features.CombinedSent
import org.datakind.ci.pdfestrian.trainingData.{GetTrainingData, MultiValue, SingleValue, TrainingData}
import org.slf4j.LoggerFactory

/**
  * Class that can train a [[ReviewModel]], determines if a model should be trained based on the parameters
  * @param minLabels minimum number of labels need to start training
  * @param increaseRequirement number of new labels needs to retrain
  * @param w2vSource the resource name of the w2v vectors
  */
class ReviewModelTrainer(minLabels : Int, increaseRequirement : Int, access : Access, w2vSource : String) {
  val logger = LoggerFactory.getLogger(this.getClass)

  /**
    * Gets counts of different labels
    * @param trainingData corpus
    * @return counts of different labels
    */
  private def splitLabels(trainingData: Array[TrainingData]) = {
    trainingData.flatMap(_.labels).foldRight(Map[String, ReviewLabel]()){ case (label, map) =>
      label match {
        case MultiValue(labelName, values) =>
          val l = map.getOrElse(labelName, ReviewLabel(labelName, Set(), Multi, 0))
          val updated = l.copy(allowedValues = l.allowedValues ++ values.toSet, trainingSize = l.trainingSize + values.length)
          map + (labelName -> updated)
        case SingleValue(labelName, value) =>
          val l = map.getOrElse(labelName, ReviewLabel(labelName, Set(), Single, 0))
          val updated = l.copy(allowedValues = l.allowedValues + value, trainingSize = l.trainingSize + 1)
          map + (labelName -> updated)
      }
    }
  }

  /**
    * Take a prev model and new training data, and determines if we need to retrain, if so retrains a model
    * @param prevModel a previously trained [[ReviewModel]]
    * @param trainingData corpus to train on
    * @param reviewId review id of corpus
    * @return tuple of (whether a new model was trained, and the current model)
    */
  def compareAndTrain(prevModel : ReviewModel, trainingData: Array[TrainingData], reviewId : Int) : (Boolean, ReviewModel) = {
    splitLabels(trainingData).filter(_._2.trainingSize > minLabels) match {
      case a : Map[String, ReviewLabel] if a.map(_._2.trainingSize).max >= prevModel.labels.map(_._2.trainingSize).max + increaseRequirement =>
        logger.info(s"Training new model ${a.map(_._2.trainingSize).max} old: ${prevModel.labels.map(_._2.trainingSize).max} and increase is $increaseRequirement")
        (true, train(reviewId))
      case a : Map[String, ReviewLabel] =>
        logger.info(s"Not training new model ${a.map(_._2.trainingSize).max} old: ${prevModel.labels.map(_._2.trainingSize).max} and increase is $increaseRequirement")
        (false, prevModel)
    }
  }

  /**
    * Will start training a model if there is enough training data to.
    * @param trainingData training data to train
    * @param reviewId review id to train
    * @return A model (if there is enough training data) or None
    */
  def startTrain(trainingData : Array[TrainingData], reviewId : Int) : Option[ReviewModel] = {
    val labels = splitLabels(trainingData)
    labels.filter(_._2.trainingSize >= minLabels) match {
      case a : Map[String, ReviewLabel] if a.isEmpty =>
        logger.info(s"Not training model ${labels.map(_._2.trainingSize).max} < $minLabels")
        None
      case a : Map[String, ReviewLabel] =>
        logger.info(s"Training model ${labels.map(_._2.trainingSize).max} >= $minLabels")
        Some(train(reviewId))
    }
  }

  /**
    * Trains a model given a review Id
    * @param reviewId review ID of review to train a model on
    * @return a new [[ReviewModel]]
    */
  private def train(reviewId : Int) : ReviewModel = {

    val trainingData = access.getTrainingData(reviewId)

    val pdf2doc = PDFToDocument(trainingData)

    val labels = splitLabels(trainingData)

    val labelCounts = trainingData.flatMap(_.labels)
      .flatMap{
        case MultiValue(labelName, values) => values.map(v => labelName + ":" + v)
        case SingleValue(labelName, value) => Array(labelName + ":" + value)
      }
      .foldRight(Map[String, Int]()) { case (label, map) =>
        map + (label -> (map.getOrElse(label, 0) + 1))
      }

    val featureExtractor = CombinedSent(trainingData, pdf2doc, w2vSource)

    val model = new ReviewModel(labels, labelCounts, trainingData.length, featureExtractor, pdf2doc)
    model.train(trainingData)
    model
  }
}

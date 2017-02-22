package org.datakind.ci.pdfestrian.extraction.review

import org.datakind.ci.pdfestrian.api.apiservice.components.Access
import org.json4s.DefaultFormats
import spray.caching.LruCache
import spray.util._

import scala.concurrent.ExecutionContext.Implicits.global

object ReviewModels {

  private implicit val formats = DefaultFormats

  private val cache = LruCache.apply[ReviewModel](maxCapacity = 25, initialCapacity = 10)

  /**
    * Gets a model from cache, or trains a model if needed
    * @param review review id of model to get
    * @param minRequired minimum required documents needed to train
    * @param increaseRequirement number of additional labels needed to retrain
    * @return Option, if model returned is a [[ReviewModel]] otherwise it's a None
    */
  def getModel(review : Int, access : Access, w2vSource : String, minRequired : Int = 40, increaseRequirement : Int = 5) : Option[ReviewModel] = {
    val trainer = new ReviewModelTrainer(minRequired, increaseRequirement, access, w2vSource)
    cache.get(review) match {
      case None =>
        trainer.startTrain(access.getTrainingLabels(review), review) match {
          case None => None
          case Some(model) =>
            cache(review)(model)
            Some(model)
        }
      case Some(modelFuture) =>
        modelFuture.map{ model =>
          trainer.compareAndTrain(model, access.getTrainingLabels(review), review) match {
            case (true, newModel) =>
              cache.remove(review)
              cache(review)(newModel)
              Some(newModel)
            case (false, oldModel) =>
              Some(oldModel)
          }
        }.await
    }
  }

}

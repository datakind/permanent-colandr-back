package org.datakind.ci.pdfestrian.extraction.review

import org.datakind.ci.pdfestrian.api.apiservice.components.Access
import org.json4s.DefaultFormats
import org.slf4j.LoggerFactory
import spray.caching.LruCache
import spray.util._

import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.Future

object ReviewModels {

  private implicit val formats = DefaultFormats

  private val cache = LruCache.apply[ReviewModel](maxCapacity = 25, initialCapacity = 10)

  private val logger = LoggerFactory.getLogger(this.getClass)


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
        Future{
          trainer.startTrain(access.getTrainingLabels(review), review) match {
            case None => None
            case Some(model) =>
              cache(review)(model)
              model
         }
        }.onComplete{ x =>
          logger.info(s"Model for Review $review finished training")
        }
        None
      case Some(modelFuture) =>
        modelFuture.map{ model =>
          Future {
            trainer.compareAndTrain(model, access.getTrainingLabels(review), review) match {
              case (true, newModel) =>
                cache.remove(review)
                cache(review)(newModel)
                newModel
            }
          }.onComplete{ x =>
            logger.info(s"Model for Review $review finished retraining")
          }
          Some(model)
        }.await
    }
  }

}
package org.datakind.ci.pdfestrian.review

import org.datakind.ci.pdfestrian.db.{MockDBExtractor, MockTrainingData}
import org.datakind.ci.pdfestrian.extraction.review.{ReviewModel, ReviewModels}
import org.scalatest.{FlatSpec, Matchers}

/**
  * Created by sameyeam on 2/21/17.
  */
class ReviewModelsTest extends FlatSpec with Matchers {

  def getModel(reviewId : Int) : Option[ReviewModel] = {
    ReviewModels.getModel(reviewId, new MockDBExtractor, "mock2vec.txt.gz", 1, 1)
  }

  "Get model with no training data" should "be None" in {
    getModel(0) should be (None)
  }

  "Get model with some training data" should "not be None" in {
    MockTrainingData.add()
    MockTrainingData.add()
    getModel(0) should not be (None)
    val model = getModel(0)
    getModel(0) should be (model)
    MockTrainingData.add()
    getModel(0) should be (model)
    MockTrainingData.add()
    getModel(0) should not be (model)
  }

}

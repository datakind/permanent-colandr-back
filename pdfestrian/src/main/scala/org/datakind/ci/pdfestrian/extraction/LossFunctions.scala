package org.datakind.ci.pdfestrian.extraction

import cc.factorie.{DenseTensor1, Tensor1}
import cc.factorie.la.SparseIndexedTensor1
import cc.factorie.optimize.MultivariateOptimizableObjective

/**
  * Created by sam on 10/30/16.
  */
object LossFunctions {
  class SigmoidalLoss extends MultivariateOptimizableObjective[Tensor1] {
    def sigmoid(d : Double) : Double = {
      1.0/(1.0f + math.exp(-d))
    }

    def valueAndGradient(prediction: Tensor1, label: Tensor1): (Double, Tensor1) = {
      var objective = 0.0
      val gradient = new SparseIndexedTensor1(prediction.size)
      for (i <- prediction.activeDomain) {
        val sigvalue = sigmoid(prediction(i))
        val diff = -(sigvalue - label(i))
        val value = -(label(i)*prediction(i)) + math.log1p(math.exp(prediction(i)))
        if(!value.isNaN) {
          objective -= value
          gradient += (i, diff)
        }
      }
      (objective, gradient)
    }
  }

  class WeightedSigmoidalLoss(weight : DenseTensor1) extends MultivariateOptimizableObjective[Tensor1] {
    def sigmoid(d : Double) : Double = {
      1.0/(1.0f + math.exp(-d))
    }

    def valueAndGradient(prediction: Tensor1, label: Tensor1): (Double, Tensor1) = {
      var objective = 0.0
      val gradient = new SparseIndexedTensor1(prediction.size)
      for (i <- prediction.activeDomain) {
        val w = if(label(i) == 1.0) weight(i) else 1.0
        val sigvalue = sigmoid(prediction(i))
        val diff = -(sigvalue - label(i))
        val value = -(label(i)*prediction(i)) + math.log1p(math.exp(prediction(i)))
        if(!value.isNaN) {
          objective -= value * w
          gradient += (i, diff * w)
        }
      }
      (objective, gradient)
    }
  }


  class HingeLoss extends MultivariateOptimizableObjective[Tensor1] {

    def valueAndGradient(prediction: Tensor1, label: Tensor1): (Double, Tensor1) = {
      var objective = 0.0
      val gradient = new SparseIndexedTensor1(prediction.size)
      for (i <- prediction.activeDomain) {
        if(prediction(i) < 0.1 && label(i) == 1.0) {
          gradient += (i, 1.0f)
          objective += prediction(i) - 0.1
        } else if(prediction(i) > 0.0 && label(i) == 0.0) {
          gradient += (i, -1.0f)
          objective += - prediction(i)
        }
      }
      (objective, gradient)
    }
  }

  class WeightedHingeLoss(weight : DenseTensor1) extends MultivariateOptimizableObjective[Tensor1] {

    def valueAndGradient(prediction: Tensor1, label: Tensor1): (Double, Tensor1) = {
      var objective = 0.0
      val gradient = new SparseIndexedTensor1(prediction.size)
      for (i <- prediction.activeDomain) {
        if(prediction(i) < 0.1 && label(i) == 1.0) {
          gradient += (i, weight(i))
          objective += (prediction(i) - 0.1) * weight(i)
        } else if(prediction(i) > 0.0 && label(i) == 0.0) {
          gradient += (i, -1.0f)
          objective += - prediction(i)
        }
      }
      (objective, gradient)
    }
  }
}

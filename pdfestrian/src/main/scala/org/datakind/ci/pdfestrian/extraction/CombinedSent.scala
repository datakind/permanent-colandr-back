package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.la.SparseTensor1

/**
  * Created by sam on 8/26/16.
  */
object CombinedSent {
  val featureSize = Word2VecSent.featureSize + TfIdfSent.featureSize

  def apply(doc : Sentence, location : Double, name : String) : SparseTensor1 = {
    val sparseTensor = new SparseTensor1(featureSize)
    val sparse = TfIdfSent(doc)
    for(i <- sparse.activeElements) {
      sparseTensor(i._1) = i._2
    }
    val w2v = Word2VecSent(doc, location)
    for(i <- 0 until Word2VecSent.featureSize) {
      sparseTensor(i+TfIdfSent.featureSize) = w2v(i)
    }
    sparseTensor
  }

}

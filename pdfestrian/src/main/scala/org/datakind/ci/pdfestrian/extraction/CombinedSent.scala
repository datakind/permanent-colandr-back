package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.la.SparseTensor1

/**
  * Created by sam on 8/26/16.
  */
object CombinedSent {
  val featureSize = Word2Vec.featureSize + TfIdf.featureSize + LDAVectorize.featureSize + 1

  def apply(doc : Sentence, location : Double, name : String) : SparseTensor1 = {
    val sparseTensor = new SparseTensor1(featureSize)
    val sparse = TfIdfSent(doc)
    for(i <- sparse.activeElements) {
      sparseTensor(i._1) = i._2
    }
    val w2v = Word2VecSent(doc, location)
    for(i <- 0 until Word2Vec.featureSize) {
      sparseTensor(i+TfIdf.featureSize) = w2v(i)
    }
    val lda = LDAVectorize(name)
    for(i <- 0 until LDAVectorize.featureSize) {
      sparseTensor(i+TfIdf.featureSize + Word2Vec.featureSize) = lda(i)
    }
    sparseTensor
  }

}

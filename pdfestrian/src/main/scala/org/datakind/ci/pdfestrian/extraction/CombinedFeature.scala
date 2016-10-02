package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.Document
import cc.factorie.la.SparseTensor1

/**
  * Created by sam on 8/26/16.
  */
object CombinedFeature {
  val featureSize = Word2Vec.featureSize + TfIdf.featureSize + LDAVectorize.featureSize

  def apply(doc : Document) : SparseTensor1 = {
    val sparseTensor = new SparseTensor1(featureSize)
    val sparse = TfIdf(doc)
    for(i <- sparse.activeElements) {
      sparseTensor(i._1) = i._2
    }
    val w2v = Word2Vec(doc)
    for(i <- 0 until Word2Vec.featureSize) {
      sparseTensor(i+TfIdf.featureSize) = w2v(i)
    }
    val lda = LDAVectorize(doc.name)
    for(i <- 0 until LDAVectorize.featureSize) {
      sparseTensor(i+TfIdf.featureSize + Word2Vec.featureSize) = lda(i)
    }
    sparseTensor
  }

}

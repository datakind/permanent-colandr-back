package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.la.SparseTensor1

/**
  * Created by sam on 8/26/16.
  */
class CombinedSent(word2VecSent : Word2VecSent, tfIdfSent: TfIdfSent) {
  val featureSize = word2VecSent.featureSize + tfIdfSent.featureSize

  def apply(doc : Sentence, location : Double, name : String) : SparseTensor1 = {
    val sparseTensor = new SparseTensor1(featureSize)
    val sparse = tfIdfSent(doc)
    for(i <- sparse.activeElements) {
      sparseTensor(i._1) = i._2
    }
    val w2v = word2VecSent(doc, location)
    for(i <- 0 until word2VecSent.featureSize) {
      sparseTensor(i+tfIdfSent.featureSize) = w2v(i)
    }
    sparseTensor
  }

}

object CombinedSent {
  def apply() = new CombinedSent(Word2VecSent(), TfIdfSent())

  def apply(trainingData: Seq[TrainingData], pdf2doc: PDFToDocument) = {
    val documents = trainingData.map(td => pdf2doc.fromString(td.fullText)._1)
    new CombinedSent(Word2VecSent(documents), TfIdfSent(documents))
  }
}

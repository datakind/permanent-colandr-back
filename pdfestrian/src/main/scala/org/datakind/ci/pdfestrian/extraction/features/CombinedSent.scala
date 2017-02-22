package org.datakind.ci.pdfestrian.extraction.features

import cc.factorie.app.nlp.Sentence
import cc.factorie.la.SparseTensor1
import org.datakind.ci.pdfestrian.document.PDFToDocument
import org.datakind.ci.pdfestrian.trainingData.TrainingData

/**
  * Combines word2vec and tfidf features into one vector
  * @param word2VecSent word2vec feature computation instance
  * @param tfIdfSent tfidf feature computation instance
  */
class CombinedSent(word2VecSent : Word2VecSent, tfIdfSent: TfIdfSent) {

  /**
    * Featuresize - size of vector returned by apply
    */
  val featureSize = word2VecSent.featureSize + tfIdfSent.featureSize

  /**
    * Computes the feature vector of sentence
    * @param sent the sentence to compute feature vector of
    * @param location the % position of sentence in document
    * @return the returned vector
    */
  def apply(sent : Sentence, location : Double) : SparseTensor1 = {
    val sparseTensor = new SparseTensor1(featureSize)
    val sparse = tfIdfSent(sent)
    for(i <- sparse.activeElements) {
      sparseTensor(i._1) = i._2
    }
    val w2v = word2VecSent(sent, location)
    for(i <- 0 until word2VecSent.featureSize) {
      sparseTensor(i+tfIdfSent.featureSize) = w2v(i)
    }
    sparseTensor
  }

}

object CombinedSent {
  /**
    * Creates a combined w2v and tfidf feature vectorizer from training data
    * @param trainingData corpus of training data
    * @param pdf2doc PDFToDocument object
    * @return CombinedSent feature vectorizer
    */
  def apply(trainingData: Seq[TrainingData], pdf2doc: PDFToDocument, w2vSource : String) = {
    val documents = trainingData.map(td => pdf2doc.fromString(td.fullText)._1)
    new CombinedSent(Word2VecSent(documents, w2vSource), TfIdfSent(documents))
  }
}

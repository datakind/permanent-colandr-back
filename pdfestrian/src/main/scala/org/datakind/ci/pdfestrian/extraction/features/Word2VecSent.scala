package org.datakind.ci.pdfestrian.extraction.features

import java.util.zip.GZIPInputStream

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.{Document, Sentence}

import scala.io.Source

/**
  * Class that computes the word2vec sentence features for review label ranking
  * @param wordCounts Counts of unigram stems
  * @param N Number of "documents" (sentences) in corpus
  *          Needs to be greater than any count of wordCounts and bigram counts to be a valid tfidf
  */
class Word2VecSent(wordCounts : Map[String, (Int, Int)], N : Int, w2vSource : String = "glove.6B.50d.txt.gz") {

  private val vectors = W2VVectors(w2vSource)

  private val arrayCounts = wordCounts.map{ _._2.swap}.toSeq.sortBy(_._1).map{_._2}
  private val words = wordCounts.map{ a => a._2._2 -> a._1}.toSeq.sortBy(_._1).map{_._2}

  private val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  val featureSize = vectors.dim+1

  private def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  private val idf = new DenseTensor1(arrayCounts.map{a => math.log(N.toDouble/a.toDouble)}.toArray)

  /**
    * Takes a sentence and returns a Densetensor whose indicies are index into words, the value is word2vec value
    *   weighted by tfidf
    * @param sentence the sentence to vectorize
    * @param location the % location of sentence in document
    * @return word2vec feature vector for sentence
    */
  def apply(sentence : Sentence, location : Double) : DenseTensor1 = {
    val tensor = new DenseTensor1(featureSize)
    var wordsInTensor = 0
    for (token <- sentence.tokens) {
      val current = clean(token.string)
      if (current.length > 0 && current.count(_.isLetter) > 0 && !stopWords.contains(current)) {
        if (wordCounts.contains(current) && vectors.words.contains(current)) {
          val count = wordCounts(current)
          tensor += (new DenseTensor1(vectors.words(current).vector.map {
            _.toDouble
          }) * idf(count._2))
          wordsInTensor += 1
        }
      }
    }
    tensor /= wordsInTensor.toDouble
    tensor /= tensor.twoNorm
    tensor(vectors.dim) = location
    tensor
  }

}


object Word2VecSent {
  /**
    * Create Word2VecSent out of corpus.
    * @param docs Documents out of corpus
    * @return a Word2VecSent feature vectorizer
    */
  def apply(docs : Seq[Document], w2vSource : String = "glove.6B.50d.txt.gz") = {
    var  i = -1

    val unigrams = GetCounts.getUnigramCounts(docs, stemmmer = false)

    val wordCounts = unigrams.map{ m =>
      i += 1
      m._1 -> (m._2, i)
    }

    new Word2VecSent(wordCounts, wordCounts.values.maxBy(_._1)._1+1, w2vSource)

  }
}
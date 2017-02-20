package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la.SparseTensor1

import scala.io.Source


/**
  * Class that computes the TfIdf sentence features for review label ranking
  * @param wordCounts Counts of unigram stems
  * @param bigramCounts Counts of bigram stems
  * @param N Number of "documents" (sentences) in corpus
  *          Needs to be greater than any count of wordCounts and bigram counts to be a valid tfidf
  */
class TfIdfSent(wordCounts : Map[String, (Int, Int)], bigramCounts : Map[String, (Int, Int)], N : Int) {
  private val arrayCounts = (wordCounts ++ bigramCounts).map{ _._2.swap}.toSeq.sortBy(_._1).map{_._2}

  private val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt"))
    .getLines()
    .map{ _.toLowerCase}.toSet

  val featureSize = wordCounts.size + bigramCounts.size

  private def clean(string : String) : String = {
    val lower = PorterStemmer(string.toLowerCase())
    lower.filter(_.isLetterOrDigit)
  }

  private val idf = new DenseTensor1(arrayCounts.map{a => math.log10(N.toDouble/a.toDouble)}.toArray)

  /**
    * Takes a sentence and returns a sparsetensor whose indicies are index into words, the value is tfidf value
    * @param document the sentence to vectorize
    * @return tfidf feature vector for sentence
    */
  def apply(document : Sentence) : SparseTensor1 = {
    val tensor = new SparseTensor1(featureSize)
    for(token <- document) {
      val current = clean(token.string)
      if(current.length > 0 && current.count(_.isLetter) > 0 && !stopWords.contains(current)) {
        if(wordCounts.contains(current)) {
          val count = wordCounts(current)
          tensor(count._2) += 1
        }
        if(token.hasNext) {
          val next = clean(token.next.string)
          if(next.length > 0 && next.count(_.isLetter) > 0 && !stopWords.contains(next)) {
            val bigram = current+"-"+next
            if(bigramCounts.contains(bigram)) {
              val count = bigramCounts(bigram)
              tensor(count._2) += 1
            }
          }
        }
      }
    }
    tensor *= idf
    tensor /= tensor.twoNorm // Normalize vector
    tensor
  }

}

object TfIdfSent {
  /**
    * Create TfIdf sent out of corpus.
    * @param docs Documents out of corpus
    * @return a TfIfdSent feature vectorizer
    */
  def apply(docs : Seq[Document]) : TfIdfSent = {
    var  i = -1

    val (unigrams, bigrams) = GetCounts.getCounts(docs, stemmmer = true)

    val wordCounts = unigrams.map{ m =>
      i += 1
      m._1 -> (m._2, i)
    }

    val bigramCounts = bigrams.map{ m =>
      i += 1
      m._1 -> (m._2, i)
    }

    new TfIdfSent(wordCounts, bigramCounts, wordCounts.values.maxBy(_._1)._1+1)
  }

}
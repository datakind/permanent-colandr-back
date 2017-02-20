package org.datakind.ci.pdfestrian.extraction.features

import cc.factorie.app.nlp.Document
import cc.factorie.app.strings.PorterStemmer

object GetCounts {

  private def clean(string : String, stem : Boolean = false) : String = {
    val lower = if(stem) PorterStemmer(string.toLowerCase()) else string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  /**
    * Gets count of words -> count in corpus
    * @param docs documents to compute counts from
    * @param stemmmer whether to stem the words in a document
    * @return Counts
    */
  def getUnigramCounts(docs : Seq[Document], stemmmer : Boolean = false) : Map[String, Int] = {
    docs.foldRight(Map[String,Int]()){ case(doc, bm) =>
      val lm = doc.tokens.map(_.string)
        .map(d => clean(d, stemmmer)).foldRight(Map[String, Int]()){ case (stem, map) =>
        map + (stem -> (map.getOrElse(stem,0)+1))
      }
      bm ++ lm.map{ case(stem, count) =>
        stem -> (bm.getOrElse(stem, 0) + count)
      }
    }
  }

  /**
    * Gets count of words -> count and bigrams -> count in corpus
    * @param docs documents to compute counts from
    * @param stemmmer whether to stem the words in a document
    * @return (unigram counts, bigram counts)
    */
  def getCounts(docs : Seq[Document], stemmmer : Boolean = false) : (Map[String, Int], Map[String, Int]) = {
     val unigrams = docs.foldRight(Map[String,Int]()){ case(doc, bm) =>
      val lm = doc.tokens.map(_.string)
        .map(d => clean(d, stemmmer)).foldRight(Map[String, Int]()){ case (stem, map) =>
          map + (stem -> (map.getOrElse(stem,0)+1))
      }
      bm ++ lm.map{ case(stem, count) =>
        stem -> (bm.getOrElse(stem, 0) + count)
      }
     }

    val bigrams = docs.foldRight(Map[String,Int]()) { case (doc, bm) =>
      val lm = doc.tokens.map(_.string)
        .map(d => clean(d, stemmmer))
        .sliding(2).foldRight(Map[String, Int]()) { case (stems, map) =>
        val stem = stems.mkString("-")
        map + (stem -> (map.getOrElse(stem, 0) + 1))
      }
      bm ++ lm.map { case (stem, count) =>
        stem -> (bm.getOrElse(stem, 0) + count)
      }
    }
    (unigrams, bigrams)
  }

}

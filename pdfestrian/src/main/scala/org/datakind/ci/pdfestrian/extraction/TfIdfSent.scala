package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la.SparseTensor1

import scala.io.Source

/**
  * Created by sameyeam on 8/3/16.
  */
class TfIdfSent(wordCounts : Map[String, (Int, Int)], bigramCounts : Map[String, (Int, Int)], N : Int) {
  var  i = -1
  val arrayCounts = (wordCounts ++ bigramCounts).map{ _._2.swap}.toSeq.sortBy(_._1).map{_._2}
  val words = (wordCounts ++ bigramCounts).map{ a => a._2._2 -> a._1}.toSeq.sortBy(_._1).map{_._2}

  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  val featureSize = wordCounts.size + bigramCounts.size

  def clean(string : String) : String = {
    val lower = PorterStemmer(string.toLowerCase())
    lower.filter(_.isLetterOrDigit)
  }

  val idf = new DenseTensor1(arrayCounts.map{a => math.log10(N.toDouble/a.toDouble)}.toArray)

  def apply(document : Sentence) : SparseTensor1 = {
    //val counts = new Array[Int](featureSize)
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
    tensor /= tensor.twoNorm
    tensor
  }

}

object TfIdfSent {
  def apply() : TfIdfSent = {
    var  i = -1
    val wordCounts = Source.fromInputStream(getClass.getResourceAsStream("/words.sample.doc.counts")).getLines().map{ s =>
      val split = s.split(",")
      i += 1
      split.head -> (split.last.toInt, i)
    }.toMap

    val bigramCounts = Source.fromInputStream(getClass.getResourceAsStream("/bigram.sample.doc.counts")).getLines().map{ s =>
      val split = s.split(",")
      i += 1
      split.head -> (split.last.toInt, i)
    }.toMap

    new TfIdfSent(wordCounts, bigramCounts, 920)
  }

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
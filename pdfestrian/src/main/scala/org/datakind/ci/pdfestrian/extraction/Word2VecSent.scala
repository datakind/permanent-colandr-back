package org.datakind.ci.pdfestrian.extraction

import java.util.zip.GZIPInputStream

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.{Document, Sentence}

import scala.io.Source

/**
  * Created by sameyeam on 8/3/16.
  */
class Word2VecSent(wordCounts : Map[String, (Int, Int)], N : Int) {
  val vectors = Source.fromInputStream(new GZIPInputStream(getClass.getResourceAsStream("/glove.6B.50d.txt.gz"))).getLines().map { word =>
    val split = word.split(" ")
    split.head -> split.takeRight(50).map{_.toFloat}
  }.toMap

  val arrayCounts = wordCounts.map{ _._2.swap}.toSeq.sortBy(_._1).map{_._2}
  val words = wordCounts.map{ a => a._2._2 -> a._1}.toSeq.sortBy(_._1).map{_._2}

  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  val featureSize = 51

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  val idf = new DenseTensor1(arrayCounts.map{a => math.log(N.toDouble/a.toDouble)}.toArray)

  def apply(sentence : Sentence, location : Double) : DenseTensor1 = {
    val tensor = new DenseTensor1(featureSize)
    var wordsInTensor = 0
    for(token <- sentence.tokens) {
      val current = clean(token.string)
      if(current.length > 0 && current.count(_.isLetter) > 0 && !stopWords.contains(current)) {
        if(wordCounts.contains(current) && vectors.contains(current)) {
          val count = wordCounts(current)
          tensor += (new DenseTensor1(vectors(current).map{_.toDouble}) * idf(count._2))
          wordsInTensor += 1
        }
      }
    }
    tensor /= wordsInTensor.toDouble
    tensor /= tensor.twoNorm
    tensor(50) = location
    tensor
  }

  def main(args: Array[String]): Unit = {
    val doc = PDFToDocument(args.head)
    val sentences = doc.get._1.sentences.toArray
    for((sent,i) <- sentences.zipWithIndex) {
      val location = i.toDouble/sentences.length.toDouble
      apply(sent, location)
    }
  }



}


object Word2VecSent {
  def apply() = {
    var  i = -1
    val wordCounts = Source.fromInputStream(getClass.getResourceAsStream("/words.sample.doc.counts.old")).getLines().map{ s =>
      val split = s.split(",")
      i += 1
      split.head -> (split.last.toInt, i)
    }.toMap

    new Word2VecSent(wordCounts, 920)
  }

  def apply(tds : Seq[TrainingData]) = {
    var  i = -1

    val docs = tds.map{ td =>
      PDFToDocument.fromString(td.fullText, td.id.toString)._1
    }

    val unigrams = GetCounts.getUnigramCounts(docs, stemmmer = false)

    val wordCounts = unigrams.map{ m =>
      i += 1
      m._1 -> (m._2, i)
    }

    new Word2VecSent(wordCounts, wordCounts.values.maxBy(_._1)._1+1)

  }
}
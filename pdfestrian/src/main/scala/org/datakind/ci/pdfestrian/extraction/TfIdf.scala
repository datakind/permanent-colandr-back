package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.Document
import cc.factorie.la.SparseTensor1

import scala.io.Source

/**
  * Created by sameyeam on 8/3/16.
  */
object TfIdf {
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

  val arrayCounts = (wordCounts ++ bigramCounts).map{ _._2.swap}.toSeq.sortBy(_._1).map{_._2}
  val words = (wordCounts ++ bigramCounts).map{ a => a._2._2 -> a._1}.toSeq.sortBy(_._1).map{_._2}

  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  val featureSize = wordCounts.size + bigramCounts.size

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  val N = 920
  val idf = new DenseTensor1(arrayCounts.map{a => math.log10(N.toDouble/a.toDouble)}.toArray)

  def apply(document : Document) : SparseTensor1 = {
    //val counts = new Array[Int](featureSize)
    val tensor = new SparseTensor1(featureSize)
    for(sentence <- document.sentences; token <- sentence.tokens) {
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
    tensor
  }

  def main(args: Array[String]): Unit = {
    val doc = PDFToDocument(args.head)
    this.apply(doc.get._1)
  }



}

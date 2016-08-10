package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, File, FileWriter}

import cc.factorie.app.strings.PorterStemmer

import scala.collection.mutable
import scala.io.Source

/**
  * Created by sameyeam on 8/3/16.
  */
object GetCounts {
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet
  def clean(string : String) : String = {
    val lower = PorterStemmer(string.toLowerCase())
    lower.filter(_.isLetterOrDigit)
  }

  def main(args: Array[String]): Unit = {
    val counts = new mutable.HashMap[String, Int]() {
      override def default(s : String) : Int = {
        this(s) = 0
        0
      }
    }
    new File(args.head).listFiles().filter( _.getAbsolutePath.endsWith(".pdf")).foreach{ f =>
      val path = f.getAbsolutePath.split("/").last.dropRight(4)
      val pdf = PDFToDocument(path)
      pdf.foreach{ d=>
        val bigrams = new mutable.HashSet[String]()
        d._1.sentences.foreach{ _.tokens.foreach{t =>
          val current = clean(t.string)
          if(current.length > 0 && current.count(_.isLetter) > 0 && !stopWords.contains(current)) {
            bigrams += current
             if(t.hasNext) {
               val next = clean(t.next.string)
                if(next.length > 0 && next.count(_.isLetter) > 0 && !stopWords.contains(next)) {
                   val bigram = current+"-"+next
                   //counts(bigram)+=1
                   bigrams += bigram
                }
               }
          }
        }   }
        for(b <- bigrams) counts(b) += 1
      }
    }
    val out = new BufferedWriter(new FileWriter("words.doc.counts"))
    for(count <- counts.toSeq.sortBy(-_._2)) {
      out.write( count._1 + "," + count._2 + "\n")
    }
    out.flush()
  }
}

package org.datakind.ci.pdfestrian

import java.io.FileInputStream
import java.text.Normalizer

import scala.util.Random

/**
  * Created by samanzaroot on 6/2/16.
  */
class GrobidAccuracy {

  def getAccuracy(matched : Seq[(BiblioItem, PDFExtractedData)]) : Seq[(String,Double)] = {
    import GrobidAccuracy._
    val booleans = matched.map { case (bi, pdf) =>
      val pdfTitle = clean(pdf.title)
      val cleanBiTitle = clean(bi.Title)
      val title = clean(pdf.title).contains(clean(bi.Title)) || EditDistance(pdfTitle, cleanBiTitle) < 2
      val biAuthors = bi.Authors.split(" ").map(e => e.filter(i => i != '.' && i != ',' && i != ';').toLowerCase()).filter(e => e.length > 1 && e != "and")
      val pdfAuthors = pdf.authors.split(" ").map(e => e.filter(_ != '.').toLowerCase()).filter(e => e.length > 1 && e != "and")
      val authors = biAuthors.zip(pdfAuthors).forall(a => a._1 == a._2)
      //val abstr = true //EditDistance(bi..toLowerCase(), pdf.authors.toLowerCase)
      (title, authors) //abstr)
    }

    val boolInd = booleans.zip(matched)

    val titleSamples = Random.shuffle(boolInd.filter(!_._1._1)).take(10).map{ _._2 }
    val authorSamples = Random.shuffle(boolInd.filter(!_._1._2)).take(10).map{ _._2 }
    //val abstSamples = Random.shuffle(boolInd.filter(!_._1._3)).take(10).map{ _._2 }

    println(titleSamples.map{ case (b,p) => Seq(b.Title, p.title).mkString("\n")}.mkString("\n\n"))
    println()
    println(authorSamples.map{ case (b,p) => Seq(b.Authors, p.authors).mkString("\n")}.mkString("\n\n"))
    println()
    //println(abstSamples.map{ case (b,p) => Seq(b., p.title)})

    val counts = booleans.foldRight( (0,0) ){ case (a,b) =>
      (b._1 + (if(a._1) 1 else 0), b._2 + (if(a._2) 1 else 0))//, b._3 + (if(a._3) 1 else 0))
    }

    val (tileAccuracy, authorAccuracy) = (counts._1.toDouble/booleans.length, counts._2.toDouble/booleans.length)//, counts._3.toDouble/booleans.length)

    val allAccuracy = (counts._1 + counts._2).toDouble/(booleans.length*2)
    Seq(("title",tileAccuracy), ("author", authorAccuracy), ("all", allAccuracy))
  }
}

object GrobidAccuracy {

  val puncs = "\\p{Punct}".r

  def clean(s : String) : String = {
    Normalizer.normalize(puncs.replaceAllIn(s.toLowerCase(), " ").replaceAll("\\s+"," "), Normalizer.Form.NFD);
  }

  def main(args: Array[String]) {
    val pdfs = PDFExtractedData.load(new FileInputStream(args.head))
    val bibs = BiblioItem.load(new FileInputStream(args(1)))
    val bibmap = bibs.map{ b => b.aid -> b}.toMap
    val matched = pdfs.filter(_.aid.isDefined)
                      .map{ pdf => (bibmap.get(pdf.aid.get), pdf) }
                      .filter(_._1.isDefined)
                      .map{ a => (a._1.get,a._2)}

    println((new GrobidAccuracy).getAccuracy(matched).mkString("\n"))
  }
}

object Matched {
  def loadMatches(pdfFile : String, bibFile : String) : Seq[(BiblioItem, PDFExtractedDataMore)] = {
    val pdfs = PDFExtractedData.loadMore(new FileInputStream(pdfFile))
    val bibs = BiblioItem.load(new FileInputStream(bibFile))
    val bibmap = bibs.map{ b => b.aid -> b}.toMap
    pdfs.filter(_.aid.isDefined)
      .map{ pdf => (bibmap.get(pdf.aid.get), pdf) }
      .filter(_._1.isDefined)
      .map{ a => (a._1.get,a._2)}
  }
}


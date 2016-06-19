package org.datakind.ci.pdfestrian.extraction

import java.io.File

import cc.factorie.app.nlp.Document
import cc.factorie.app.nlp.segment.{DeterministicNormalizingTokenizer, DeterministicSentenceSegmenter}
import cc.factorie.app.nlp.segment.PunktSentenceSegmenter.Punkt.PunktSentenceTokenizer

import scala.io.Source

/**
  * Created by sameyeam on 6/18/16.
  */
object PDFToDocument {

  val dir = "/Users/sameyeam/ci"
  def apply(name : String) : Option[Document] = {
    val txt = dir + "/txt/" + name + ".pdf.txt"
    val ocrtxt = dir + "/ocrTxt/" + name + ".pdf.ocr.txt"
    val file = if(new File(txt).exists())
      new File(txt)
    else if(new File(ocrtxt).exists())
      new File(ocrtxt)
    else null
    if(file == null) return None
    Some(fromFile(file, name = name))
  }

  def fromFile(file : File, name : String = "") : Document = {
    val docTxt = Source.fromFile(file).mkString
    val doc = new Document(docTxt).setName(name)
    val tokenized = DeterministicNormalizingTokenizer.process(doc)
    DeterministicSentenceSegmenter.process(tokenized)
  }

  def main(args: Array[String]) {
    val doc = apply("Zhang 2012")
    doc match {
      case None => println("Couldn't find")
      case Some(d) =>
        println(d)
        for(sentence <- d.sentences) {
          println(sentence)
        }
    }
  }
}

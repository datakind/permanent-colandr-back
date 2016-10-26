package org.datakind.ci.pdfestrian.extraction

import java.io.File

import cc.factorie.app.nlp.{Document, Sentence, Token}
import cc.factorie.app.nlp.segment.{DeterministicNormalizingTokenizer, DeterministicSentenceSegmenter}
import cc.factorie.app.nlp.segment.PunktSentenceSegmenter.Punkt.PunktSentenceTokenizer
import org.datakind.ci.pdfestrian.reformat.Reformat

import scala.io.Source

/**
  * Created by sameyeam on 6/18/16.
  */
object PDFToDocument {

  val dir = "/home/sam/ci/theText/"
  def apply(name : String) : Option[(Document,Document)] = {
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

  def fromFile(file : File, name : String = "") : (Document, Document) = {
    val docTxt = Source.fromFile(file).mkString
    val doc = new Document(docTxt).setName(name)
    val tokenized = DeterministicNormalizingTokenizer.process(doc)
    splitReferences(Reformat(DeterministicSentenceSegmenter.process(tokenized)))
  }

  def fromString(string : String, filename : String) : (Document, Document) = {
    val docTxt = string
    val doc = new Document(docTxt).setName(filename)
    val tokenized = DeterministicNormalizingTokenizer.process(doc)
    splitReferences(Reformat(DeterministicSentenceSegmenter.process(tokenized)))
  }

  def splitReferences(doc : Document) : (Document, Document) = {
    val document = new Document().setName(doc.name)
    val references = new Document().setName(doc.name)
    var i = 0
    val sentences = doc.sentences.toArray
    var found = false
    while(i < doc.sentenceCount && !found) {
      val sentence = sentences(i)
      if (sentence.length >= 1 && sentence.tokens.head.string.toLowerCase() == "references") {
        found = true
      }
      if (sentence.length >= 2) {
        val lower = sentence.tokens.take(2).map {
          _.string
        }.mkString(" ").toLowerCase()
        if (lower == "works cited" || lower == "literature cited") {
          found = true
        }
      }
      i += 1
      if (sentence.tokens.nonEmpty) {
        val sent = new Sentence(document)
        for (t <- sentence.tokens) {
          new Token(sent, t.string)
        }
      }
    }
    while(i < doc.sentenceCount && !found) {
      val sentence = sentences(i)
      i += 1
      val sent = new Sentence(references)
      for(t <- sentence.tokens) {
        new Token(sent, t.string)
      }
    }
    (document, references)
  }

  def main(args: Array[String]) {
    val doc = apply("Vega 2013")
    doc match {
      case None => println("Couldn't find")
      case Some(d) =>
        println(d)
        for(sentence <- d._1.sentences) {
          println(sentence.tokens.map{_.string}.mkString(", "))
          println()
        }
    }
  }
}
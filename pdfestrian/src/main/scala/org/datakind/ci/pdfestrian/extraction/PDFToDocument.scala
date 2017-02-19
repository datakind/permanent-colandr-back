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
class PDFToDocument(reformat : Reformat) {

  def fromFile(file : File, name : String = "") : (Document, Document) = {
    val docTxt = Source.fromFile(file).mkString
    val doc = new Document(docTxt).setName(name)
    val tokenized = DeterministicNormalizingTokenizer.process(doc)
    splitReferences(reformat(DeterministicSentenceSegmenter.process(tokenized)))
  }

  def fromString(string : String, filename : String = "") : (Document, Document) = {
    val docTxt = string
    val doc = new Document(docTxt).setName(filename)
    val tokenized = DeterministicNormalizingTokenizer.process(doc)
    splitReferences(reformat(DeterministicSentenceSegmenter.process(tokenized)))
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
}

object PDFToDocument {

  def apply() : PDFToDocument = {
    new PDFToDocument(Reformat(Seq()))
  }

  def apply(trainingData: Seq[TrainingData]) : PDFToDocument = {
    new PDFToDocument(Reformat(trainingData))
  }
}
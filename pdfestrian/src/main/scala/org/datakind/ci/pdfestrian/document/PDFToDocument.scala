package org.datakind.ci.pdfestrian.document

import java.io.File

import cc.factorie.app.nlp.segment.{DeterministicNormalizingTokenizer, DeterministicSentenceSegmenter}
import cc.factorie.app.nlp.{Document, Sentence, Token}
import org.datakind.ci.pdfestrian.trainingData.TrainingData

import scala.io.Source

/**
  * Class that can take in a string, and return a processes document (dehyphenated, references removed)
  * @param dehypenator an corpus specific instance of a dehyphenator
  */
class PDFToDocument(dehypenator : Dehyphenator) {

  /**
    * Takes in a textfile and returns two documents, a main document and a references document
    * @param file textfile to create document from
    * @param name the filename of the document (optional)
    * @return tuple of (main document, references document)
    */
  def fromFile(file : File, name : String = "") : (Document, Document) = {
    val docTxt = Source.fromFile(file).mkString
    val doc = new Document(docTxt).setName(name)
    val tokenized = DeterministicNormalizingTokenizer.process(doc)
    splitReferences(dehypenator(DeterministicSentenceSegmenter.process(tokenized)))
  }

  /**
    * Takes in a string and returns two documents, a main document and a references document
    * @param string string to create document from
    * @param filename the filename of the document (optional)
    * @return tuple of (main document, references document)
    */
  def fromString(string : String, filename : String = "") : (Document, Document) = {
    val docTxt = string
    val doc = new Document(docTxt).setName(filename)
    val tokenized = DeterministicNormalizingTokenizer.process(doc)
    splitReferences(dehypenator(DeterministicSentenceSegmenter.process(tokenized)))
  }

  /**
    * Attempts to split a document into head document, and references document
    * @param doc document to split
    * @return tuple of (main document, references document)
    */
  private def splitReferences(doc : Document) : (Document, Document) = {
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
    new PDFToDocument(Dehyphenator(Seq()))
  }

  def apply(trainingData: Seq[TrainingData]) : PDFToDocument = {
    new PDFToDocument(Dehyphenator(trainingData))
  }
}
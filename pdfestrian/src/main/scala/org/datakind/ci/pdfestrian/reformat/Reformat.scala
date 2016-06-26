package org.datakind.ci.pdfestrian.reformat

import cc.factorie.app.nlp.{Document, Sentence, Token}

import scala.io.Source

/**
  * Created by sameyeam on 6/26/16.
  */
class Reformat(doc : Document) {
  import Reformat._
  def apply() : Document = {
    val document = new Document().setName(doc.name)
    document.appendString(doc.string)
    var sent = new Sentence(document)
    var skip = 0
    for(sentence <- doc.sentences) {
      for(tok <- sentence.tokens) {
        if(tok.hasNext && tok.next.string == "-" && tok.next.hasNext) {
          val potential = tok.string + tok.next.next.string
          if(goodWords.contains(potential)) {
            new Token(sent, potential)
          }
          skip = 2
        } else {
          if(skip == 0 && tok.string.trim.length > 0)
            new Token(sent, tok.string)
          else
            skip -= 1
        }
        if(tok.isSentenceEnd) {
          if(tok.hasNext && tok.next.string.head.isLetter && tok.string != ";") {
            sent = new Sentence(document)
          }
        }
      }
    }
    document
  }
}

object Reformat {
  val goodWords = Source.fromInputStream(getClass.getResourceAsStream("/goodWords.txt"))
                      .getLines().filter(!_.contains("-"))
                      .map{ _.toLowerCase()}.toSet
  def apply(doc : Document) : Document = {
    new Reformat(doc).apply()
  }
}

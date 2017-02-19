package org.datakind.ci.pdfestrian.reformat

import cc.factorie.app.nlp.{Document, Sentence, Token}
import org.datakind.ci.pdfestrian.extraction.TrainingData

import scala.io.Source

/**
  * Dehyphenator, dehyphenates common words in the dataset.
  * @param doc
  */
class Reformat(goodWords : Set[String]) {
  import Reformat._
  def apply(doc : Document) : Document = {
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

  private def getGoodWords(tds : Seq[TrainingData]) : Set[String] = {
    tds.flatMap(td => td.fullText.split(' ').map(l => l.toLowerCase -> 1))
      .groupBy(_._1).map{ case (phrase, count) =>
        phrase -> count.map(_._2).sum
    }.filter(_._2 > 10).keySet
  }

  def apply(trainingData: Seq[TrainingData]) : Reformat = {
    new Reformat(getGoodWords(trainingData))
  }

}

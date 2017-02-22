package org.datakind.ci.pdfestrian.document

import cc.factorie.app.nlp.{Document, Sentence, Token}
import org.datakind.ci.pdfestrian.trainingData.TrainingData

/**
  * Dehyphenator, dehyphenates common words in the dataset.
  * @param goodWords Set of possible words that if matched, dehypenation occurs
  */
class Dehyphenator(goodWords : Set[String]) {

  /**
    * Dehyphenates a document
    * @param doc document to dehypenate
    * @return new dehypenated document
    */
  def apply(doc : Document) : Document = {
    val document = new Document().setName(doc.name)
    document.appendString(doc.string)
    var sent = new Sentence(document)
    var skip = 0
    for(sentence <- doc.sentences) {
      for(tok <- sentence.tokens) {
        if(tok.hasNext && tok.next.string == "-" && tok.next.hasNext) { // Hyphenated text
          val potential = tok.string + tok.next.next.string // De-hyphenated string
          if(goodWords.contains(potential)) {
            new Token(sent, potential)  // combine de-hyphenated text if contained in goodwords
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

object Dehyphenator {

  private def getGoodWords(tds : Seq[TrainingData]) : Set[String] = {
    tds.flatMap(td => td.fullText.split(' ').map(l => l.toLowerCase -> 1))
      .groupBy(_._1).map{ case (phrase, count) =>
        phrase -> count.map(_._2).sum
    }.filter(_._2 > 10).keySet
  }

  /**
    * Creates a Dehyphenator from a corpus of training data
    * @param trainingData corpus to creat dehyphenator from
    * @return a dehypenator
    */
  def apply(trainingData: Seq[TrainingData]) : Dehyphenator = {
    new Dehyphenator(getGoodWords(trainingData))
  }

}

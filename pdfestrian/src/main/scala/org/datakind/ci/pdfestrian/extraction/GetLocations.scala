package org.datakind.ci.pdfestrian.extraction

import cc.factorie.app.nlp.{Document, TokenSpan}
import cc.factorie.app.nlp.ner.{BilouConllNerDomain, NoEmbeddingsConllStackedChainNer, StaticLexiconFeatures}
import cc.factorie.util.ModelProvider
import org.datakind.ci.pdfestrian.document.PDFToDocument

object GetLocations {
  private val model = new NoEmbeddingsConllStackedChainNer()(ModelProvider.classpath[NoEmbeddingsConllStackedChainNer](), StaticLexiconFeatures())
  private val pdfToDoc = PDFToDocument()

  /**
    * Determines if a tokenspan is a reference
    * @param tokenSpan tokenspan to check
    * @return true if in reference
    */
  private def isInReference(tokenSpan: TokenSpan) : Boolean = {
    var current = tokenSpan.tokens.head
    while (current.sentenceHasPrev) {
      current = current.sentencePrev
      if(current.string == ")") return false
      if(current.string == "(") return true
    }
    false
  }

  /**
    * Gets tokenspans containing locations in document
    * @param doc document to extract locations
    * @return the location tokenspans
    */
  private def apply(doc : Document) : Seq[TokenSpan] = {
    if(doc.tokenCount == 0) return Seq()
    val document = model.process(doc)
    val tags = BilouConllNerDomain.spanList(document.asSection)
    tags.filter{_.label.categoryValue.contains("LOC")}.filter(!isInReference(_))
  }

  /**
    * Gets all locations in document
    * @param document document to extract locations from
    * @return text of location, the sentence context,
    *         percentage location of sentence in doc, position in doc of sentence
    */
  private def getLocations(document : String) : Seq[(String, String, Double, Int)] = {
    val (d, _) = pdfToDoc.fromString(document,"")
    val sentences = d.sentences.toSeq
    apply(d).map { l =>
      val percentage = l.sentence.indexInSection.toDouble/sentences.length.toDouble
      val text = (math.max(0,l.sentence.indexInSection-3) until math.min(d.sentenceCount-1, l.sentence.indexInSection+3)).map{ i =>
        d.asSection.sentences(i).tokensString(" ")
      }.mkString("\n")

      (l.tokensString(" "), text, percentage, l.sentence.indexInSection)
    }
  }

  /**
    * Gets all locations in document grouped by location name
    * @param document document to extract locations from
    * @return text of location -> the sentence context,
    *         percentage location of sentence in doc, position in doc of sentence
    */
  def groupedLocations(document : String) : Map[String, Seq[(String, Double, Int)]] = getLocations(document).groupBy(_._1)
      .map{ a =>
        a._1 -> a._2.map{i => (i._2, i._3, i._4)}
      }

  private def normalize(line : String) : String = {
    if (line == "Viet Nam") "vietnam"
    else line.toLowerCase()
  }

  private def normalizeLocations(locations : Map[String, Seq[(String, Double)]]) : Map[String, Seq[(String, Double)]] = {
    locations.map{ l => normalize(l._1) -> l._2}
  }

}
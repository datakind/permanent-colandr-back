package org.datakind.ci.pdfestrian.extraction

import cc.factorie.app.nlp.{Document, TokenSpan}
import cc.factorie.app.nlp.ner.{BilouConllNerDomain, NoEmbeddingsConllStackedChainNer, NoEmbeddingsOntonotesStackedChainNer, StaticLexiconFeatures}
import cc.factorie.util.ModelProvider
import org.datakind.ci.pdfestrian.api.{LocationExtractor, Metadata, Record}

/**
  * Created by sameyeam on 6/29/16.
  */
object GetLocations {
  val model = new NoEmbeddingsConllStackedChainNer()(ModelProvider.classpath[NoEmbeddingsConllStackedChainNer](), StaticLexiconFeatures())

  def isInReference(tokenSpan: TokenSpan) : Boolean = {
    var current = tokenSpan.tokens.head
    while (current.hasPrev) {
      current = current.prev
      if(current.string == ")") return false
      if(current.string == "(") return true
    }
    false
  }

  def apply(doc : Document) : Seq[TokenSpan] = {
    if(doc.tokenCount == 0) return Seq()
    val document = model.process(doc)
    val tags = BilouConllNerDomain.spanList(document.asSection)
    tags.filter{_.label.categoryValue.contains("LOC")}.filter(!isInReference(_))
  }
}

class GetAllLocations extends LocationExtractor {

  val pdfToDoc = PDFToDocument()
  private def getLocations(trip : String) : Seq[(String, String, Double, Int)] = {
    val (d, _) = pdfToDoc.fromString(trip,"")
    val sentences = d.sentences.toSeq
    GetLocations(d).map { l =>
      val percentage = l.sentence.indexInSection.toDouble/sentences.length.toDouble
      val text = (math.max(0,l.sentence.indexInSection-3) until math.min(d.sentenceCount-1, l.sentence.indexInSection+3)).map{ i =>
        d.asSection.sentences(i).tokensString(" ")
      }.mkString("\n")

      (l.tokensString(" "), text, percentage, l.sentence.indexInSection)
    }
  }

  private def groupedLocations(trip : String) : Map[String, Seq[(String, Double, Int)]] = getLocations(trip).groupBy(_._1)
      .map{ a =>
        a._1 -> a._2.map{i => (i._2,i._3, i._4)}
      }

  private def normalize(line : String) : String = {
    if (line == "Viet Nam") "vietnam"
    else line.toLowerCase()
  }

  private def normalizeLocations(locations : Map[String, Seq[(String, Double)]]) : Map[String, Seq[(String, Double)]] = {
    locations.map{ l => normalize(l._1) -> l._2}
  }

  def getLocations(record : Record) : Seq[Metadata] = {
    groupedLocations(record.content).toSeq.
      sortBy(-_._2.length)
      .map{ case (location, sentences) =>
        val sortedSentences = sentences.sortBy(_._3)
        Metadata(record.id.toString, "location", location, sentences.map(_._1).mkString("\n"), sortedSentences.head._3, 1.0)
     }
  }

}
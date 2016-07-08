package org.datakind.ci.pdfestrian.extraction

import cc.factorie.app.nlp.{Document, TokenSpan}
import cc.factorie.app.nlp.ner.{BilouConllNerDomain, NoEmbeddingsConllStackedChainNer, NoEmbeddingsOntonotesStackedChainNer, StaticLexiconFeatures}
import cc.factorie.util.ModelProvider
import org.datakind.ci.pdfestrian.scripts.Aid

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

  def main(args: Array[String]) {
    val doc = PDFToDocument.apply("Thondhlana 2012")
    doc match {
      case None => println("Couldn't find")
      case Some(d) =>
        val locations = apply(d._1).map{ ts =>
          ts.sentence.tokensString(" ") + "\n" +
            ts.tokens.map{_.string}.mkString(" ") + "\n\n"
        }
        println(locations)
    }
  }
}

object GetAllLocations {
  def apply(seq : Seq[Aid]) : Seq[(Aid, Seq[String])] = {
     seq.map{ s => (s,this(s))}
  }

  def apply(trip : Aid) : Seq[String] = {
    PDFToDocument.apply(trip.pdf.filename) match {
      case None => Seq()
      case Some(d) => GetLocations(d._1).map {
        _.tokensString(" ")
      }
    }
  }

  def main(args: Array[String]) {
    val withLocations = this(Aid.load(args.head))
    withLocations.foreach{ case(aid, locations) =>
      aid.interv match {
        case Some(l) => {
          println(aid.bib.Title)
          println(l.Int_area)
          println(locations.mkString(", "))
          println("======================")
          println()
        }
        case None =>
          println("No aid")
          println("======================")
          println()
      }
    }
  }
}
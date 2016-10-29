package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.app.nlp.{Document, TokenSpan}
import cc.factorie.app.nlp.ner.{BilouConllNerDomain, NoEmbeddingsConllStackedChainNer, NoEmbeddingsOntonotesStackedChainNer, StaticLexiconFeatures}
import cc.factorie.util.ModelProvider
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper
import org.datakind.ci.pdfestrian.scripts.{Aid, Interv}

import scala.io.Source

case class LocationTrainData(aid : Option[Aid] = None, location : String, sentences : Array[PredictedLocation]) {
  def toJson : String = {
    LocationTrainData.mapper.writeValueAsString(this)
  }
}
case class PredictedLocation(valid : Boolean, location : String, sentences : Array[LocationSentence])
case class LocationSentence(sentence : String, percent : Double)


object LocationTrainData {
  val mapper = new ObjectMapper() with ScalaObjectMapper
  mapper.registerModule(DefaultScalaModule)
  def load(string : String) : LocationTrainData =  {
    mapper.readValue[LocationTrainData](string)
  }
  def fromFile(string : String) : Array[LocationTrainData] = {
    Source.fromFile(string).getLines().toArray.map{ l=>
      load(l)
    }
  }
}
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
     seq.map{ s => (s,this(s).map{_._1})}
  }

  def apply(trip : Aid) : Seq[(String, String, Double)] = {
    PDFToDocument.apply(trip.pdf.filename) match {
      case None => Seq()
      case Some(d) =>
        val sentences = d._1.sentences.toSeq
        GetLocations(d._1).map { l =>
          val percentage = sentences.indexOf(l.sentence).toDouble/sentences.length.toDouble
        (l.tokensString(" "), l.sentence.tokens.map{ _.string }.mkString(" "), percentage)
      }
    }
  }

  def apply(trip : String) : Seq[(String, String, Double)] = {
    val (d, _) = PDFToDocument.fromString(trip,"")
    val sentences = d.sentences.toSeq
    GetLocations(d).map { l =>
      val percentage = sentences.indexOf(l.sentence).toDouble/sentences.length.toDouble
      (l.tokensString(" "), l.sentence.tokens.map{ _.string }.mkString(" "), percentage)
    }
  }

  def grouped(trip : Aid) : Map[String, Seq[(String, Double)]] = {
    val locations = apply(trip)
    locations.groupBy(_._1).map{ a => a._1 -> a._2.map{i => (i._2,i._3)}}
  }

  def grouped(trip : String) : Map[String, Seq[(String, Double)]] = {
    val locations = apply(trip)
    locations.groupBy(_._1).map{ a => a._1 -> a._2.map{i => (i._2,i._3)}}
  }

  def normalize(line : String) : String = {
    if (line == "Viet Nam") "vietnam"
    else if (line.startsWith("Tanzania")) "tanzania"
    else if (line.startsWith("Iran")) "iran"
    else if( line.startsWith("Taiwan")) "taiwan"
    else line.toLowerCase()
  }

  def normalizeLocations(locations : Map[String, Seq[(String, Double)]]) : Map[String, Seq[(String, Double)]] = {
    locations.map{ l => normalize(l._1) -> l._2}
  }

  def featureData(trip : String) : Option[LocationTrainData] = {
    val locations = grouped(trip)
    val normalizedLocations = normalizeLocations(locations)
    val locSentences = normalizedLocations.map{ nl =>
      val sentences = nl._2.map{ s =>
        LocationSentence(s._1, s._2)
      }.toArray
      PredictedLocation(valid = true, nl._1, sentences)
    }.toArray
    Some(LocationTrainData(None, "", locSentences))
  }

  def trainingData(aid : Option[Aid], locations : Map[String, Seq[(String, Double)]]) : Option[LocationTrainData] = {
    if(aid.get.interv.isEmpty) return None
    val line = aid.get.interv.get.Int_area
    val location = normalize(line)
    val normalizedLocations = normalizeLocations(locations)
    val locSentences = normalizedLocations.map{ nl =>
      val sentences = nl._2.map{ s =>
        LocationSentence(s._1, s._2)
      }.toArray
      PredictedLocation(location == nl._1, nl._1, sentences)
    }.toArray
    Some(LocationTrainData(aid, location, locSentences))
  }

  def main(args: Array[String]): Unit = {
    val out = new BufferedWriter(new FileWriter("locationTraining"))
    Aid.load(args.head).foreach{ a =>
      trainingData(Some(a),grouped(a)) match {
        case Some(td) =>
          out.write(td.toJson + "\n")
        case _ =>
          println("No location: " + a.bib.Title)
      }
    }
    out.flush()
    out.close()
  }
}

object FindFalse {
  def main(args: Array[String]): Unit = {
    LocationTrainData.fromFile(args.head).foreach{ ltd =>
      if(!ltd.sentences.exists(_.valid) && ltd.sentences.length > 0) {
        println(ltd.aid.get.bib.Title + "\n")
        println(ltd.location + "\n")
        println(ltd.sentences.map{ l => "Predicted: " + l.location + "\n" + l.sentences.map{_.sentence}.mkString("\n")}.mkString("\n"))
        println("=========")
        println("")
      }
     }
  }
}


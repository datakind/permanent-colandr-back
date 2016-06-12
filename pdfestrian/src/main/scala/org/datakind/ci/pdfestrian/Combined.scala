package org.datakind.ci.pdfestrian

import java.io._

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

import scala.io.Source

/**
  * Created by samanzaroot on 6/5/16.
  */
case class Combined(author : String, year : Int, title : String, dAbstract :String, journal : String, included : Boolean, abstractReview : Boolean, unresolved : Boolean)

object Loader {
  val mapper = new ObjectMapper() with ScalaObjectMapper
  mapper.registerModule(DefaultScalaModule)
}

object CombinedLoader {
  def load(is : InputStream) : Seq[Combined] = {
   Source.fromInputStream(is).getLines().map{ s =>
     Loader.mapper.readValue(s,classOf[Combined])
   }.toSeq
  }
}

object CombinedMatch {
  def main(args: Array[String]) {
    val bib = args.head
    val pdfs = args(1)
    val comb = args(2)
    val firstMatch = Matched.loadMatches(bib, pdfs)
    val combined = CombinedLoader.load(new FileInputStream(comb))
    val searcher = new SimpleSearchEngine[Combined]
    searcher.load(combined.map{ c => (c.title, c)})
    val map = combined.map{ c => GrobidAccuracy.clean(c.title).trim -> c}.toMap
    val matches = firstMatch.flatMap{ fm =>
      if(fm._1.Title.length == 0) None
      else {
        val found = searcher.search(fm._1.Title).take(5)
        found.find( c => EditDistance(GrobidAccuracy.clean(c.title), GrobidAccuracy.clean(fm._1.Title)) < 5) match {
          case None =>
            None
          case Some(a) =>
            Some((fm._1, fm._2, a))
        }
      }
    }
    println(matches.length.toDouble/firstMatch.length.toDouble)
  }
}

object AllFieldsMatch {
  val mapper = new ObjectMapper() with ScalaObjectMapper
  mapper.registerModule(DefaultScalaModule)

  def loadFromFile(s : String) : AllFieldsRecord = {
    val source = Source.fromFile("dir/"+s+".json")
    val json = source.getLines().mkString
    source.close()
    mapper.readValue[AllFieldsRecord](json)
  }

  def main(args: Array[String]) {
    val bib = args.head
    val pdfs = args(1)
    val firstMatch = Matched.loadMatches(pdfs,bib)
    val dir = new File("dir").listFiles().filter(_.getAbsolutePath.endsWith("json"))
    val searcher = new SimpleSearchEngine[String]
    dir.foreach{ f =>
      val source = Source.fromFile(f, "UTF-8")
      val json = source.getLines().mkString
      source.close()
      searcher.load(mapper.readValue[AllFieldsRecord](json).Title, mapper.readValue[AllFieldsRecord](json).Record_Number)
    }
    val matches = firstMatch.flatMap{ fm =>
      if(fm._1.Title.length == 0) None
      else {
        val found = searcher.search(fm._1.Title).take(5).map{loadFromFile}
        found.find( c => EditDistance(GrobidAccuracy.clean(c.Title), GrobidAccuracy.clean(fm._1.Title)) < 5) match {
          case None =>
            None
          case Some(a) =>
            Some((fm._1, fm._2, a))
        }
      }
    }
    println(matches.length.toDouble/firstMatch.length.toDouble)
    val out = new BufferedWriter(new FileWriter("json/triple.json"))
    for(m <- matches) {
      out.write(Triple(m._2, m._1, m._3).toJson + "\n")
    }
    out.flush()
  }
}
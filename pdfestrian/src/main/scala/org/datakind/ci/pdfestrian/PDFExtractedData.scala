package org.datakind.ci.pdfestrian

import java.io.{BufferedWriter, FileInputStream, FileWriter, InputStream}

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

import scala.io.Source

/**
  * Created by samanzaroot on 5/20/16.
  */
case class PDFExtractedData(filename : String, year : Int, title : String, authors : String, dAbstract : String, aid : Option[Int] = None) {
  def toJson : String = {
    val mapper = new ObjectMapper() with ScalaObjectMapper
    mapper.registerModule(DefaultScalaModule)
    mapper.writeValueAsString(this)
  }
}

case class PDFExtractedDataMore(filename : String, year : Int, title : String, authors : String, dAbstract : String, doi : String, journal : Option[Journal], aid : Option[Int] = None) {
  def toJson : String = {
    val mapper = new ObjectMapper() with ScalaObjectMapper
    mapper.registerModule(DefaultScalaModule)
    mapper.writeValueAsString(this)
  }
}

case class Triple(pdf : PDFExtractedDataMore, bib : BiblioItem, allFields : AllFieldsRecord) {
    def toJson : String = {
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.writeValueAsString(this)
    }
}

object Triple {
  def load(file : String) : Seq[Triple] = {
    Source.fromFile(file).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[Triple])
    }.toSeq
  }
}

case class Journal(name : String, volume : String, issue : String)

object PDFExtractedData {
  def load(stream : InputStream) : Seq[PDFExtractedData] = {
    Source.fromInputStream(stream).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[PDFExtractedData])
    }.toSeq
  }

  def loadMore(stream : InputStream) : Seq[PDFExtractedDataMore] = {
    Source.fromInputStream(stream).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[PDFExtractedDataMore])
    }.toSeq
  }


  def main(args: Array[String]) {
    val items = load(new FileInputStream(args.head))
    for(i <- items; if i.aid.isEmpty) {
      println(i)
    }
    val out = new BufferedWriter(new FileWriter("dups.txt"))
    items.toArray.groupBy(_.aid.get).filter(_._2.length > 1).foreach{ a =>
      out.write(a._1 + "\n")
      for(e <- a._2) {
        out.write(e.toJson + "\n")
      }
    }
    out.flush()
  }
}

object AddFeilds {
  def main(args: Array[String]) {
    val more = PDFExtractedData.loadMore(new FileInputStream(args.head))
    val wasMatched = PDFExtractedData.load(new FileInputStream(args(1)))
    val map = more.map{ m => m.filename -> m}.toMap
    val moreMatched = wasMatched.map{ m =>
      map.get(m.filename) match {
        case None =>
          PDFExtractedDataMore(m.filename, m.year, m.title, m.authors, m.dAbstract, "", None, aid = m.aid)
        case Some(mat) =>
          mat.copy(aid = m.aid)
      }
    }
    val out = new BufferedWriter(new FileWriter("wasmatchmore.json"))
    moreMatched.foreach{ m =>
      out.write(m.toJson + "\n")
    }
    out.flush()
    out.close()
  }
}
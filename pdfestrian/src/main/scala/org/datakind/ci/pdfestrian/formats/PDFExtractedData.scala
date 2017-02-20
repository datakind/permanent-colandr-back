package org.datakind.ci.pdfestrian.formats

import java.io.InputStream

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

import scala.io.Source

/**
  * Created by samanzaroot on 5/20/16.
  */
case class Journal(name : String, volume : String, issue : String)

case class PDFExtractedData(filename : String, year : Int, title : String, authors : String, dAbstract : String, doi : String, journal : Option[Journal], aid : Option[Int] = None) {
  def toJson : String = {
    val mapper = new ObjectMapper() with ScalaObjectMapper
    mapper.registerModule(DefaultScalaModule)
    mapper.writeValueAsString(this)
  }
}

object PDFExtractedData {

  def load(stream : InputStream) : Seq[PDFExtractedData] = {
    Source.fromInputStream(stream).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[PDFExtractedData])
    }.toSeq
  }

}
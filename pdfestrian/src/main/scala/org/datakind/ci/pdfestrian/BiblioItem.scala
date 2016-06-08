package org.datakind.ci.pdfestrian

import java.io.{FileInputStream, InputStream}

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

import scala.io.Source

/**
  * Created by samanzaroot on 5/20/16.
  */
case class BiblioItem(num : Int, aid : Int, Assessor : String, Assess_date : String,Assessor_2 :String,
                     Pub_type : String, Authors : String, DOI : String, Pub_year : String, Title : String,  Journal : String,
                     Vol : String, Page_num : String, Publisher : String, Publisher_loc : String ,
                     Author_affil : String ,  Funding : String, Affil_type : String, Bib_notes : String
                    ) {
  def toJson : String = {
    val mapper = new ObjectMapper() with ScalaObjectMapper
    mapper.registerModule(DefaultScalaModule)
    mapper.writeValueAsString(this)
  }
}

object BiblioItem {
  def load(stream : InputStream) : Seq[BiblioItem] = {
    Source.fromInputStream(stream).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[BiblioItem])
    }.toSeq
  }

  def main(args: Array[String]) {
    val items = load(new FileInputStream(args.head))
    for(i <- items) println(i.aid)
  }
}
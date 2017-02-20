package org.datakind.ci.pdfestrian.scripts

import java.io.{DataInputStream, File, FileInputStream}

import org.datakind.ci.pdfestrian.formats.AidSeq
import org.json4s.DefaultFormats
import org.json4s.jackson.Serialization._

import scala.io.Source
import scalaj.http.{Http, MultiPart}

/**
  * Bulk uploads pdfs to colandr API, needs to have a mapping between pdf and record id
  */
object PopulateFullTexts {

  implicit val formats = DefaultFormats

  def putPDF(id : Int, fileName : String, pdfdirectory : String,  host : String, username : String, password : String) : Boolean = {
    val file = new File(pdfdirectory + fileName + ".pdf")
    if(file.isFile) {
      val inputStream = new DataInputStream(new FileInputStream(file))
      val byteData = new Array[Byte](file.length().toInt)
      inputStream.readFully(byteData)
      val response = Http(s"$host/api/fulltexts/$id/upload")
        .auth(username, password)
        .postMulti(MultiPart("uploaded_file", fileName + ".pdf", "application/pdf", byteData)).asString
      println(response.body)
      if (response.isError) return false
      val data = read[Response](response.body)
      data.extracted_items.length > 0
    } else false
  }

  case class PopulateFullTextsConfig(aids : String = "", idMap : String = "", fulltextids : String = "",
                                     pdfdirecory : String = "/Users/sameyeam/ci/included/",
                                     host : String = "http://localhost:5000", username : String = "", password : String = "")

  val parser = new scopt.OptionParser[PopulateFullTextsConfig]("PopulateFullTexts") {
    head("PopulateFullTexts", "0.1")

    opt[String]('a', "aids").required().action((x, c) =>
      c.copy(aids = x)).text("AidSeq file")

    opt[String]('i', "idMap").required().action((x, c) =>
      c.copy(idMap = x)).text("IdMap file")

    opt[String]('h', "host").action((x, c) =>
      c.copy(host = x)).text("host name")

    opt[String]('u', "user").required().action((x, c) =>
      c.copy(username = x)).text("username")

    opt[String]('p', "password").required().action((x, c) =>
      c.copy(password = x)).text("password")

    opt[String]('d', "pdfdir").action((x, c) =>
      c.copy(pdfdirecory = x)).text("directory containing pdfs to upload")

  }

  def main(args : Array[String]) : Unit = {
    parser.parse(args, PopulateFullTextsConfig()) match {
      case Some(config) =>
        val aids = AidSeq.load(config.aids)
        val idMap = Source.fromFile(config.idMap).getLines().map(_.split("\t"))
          .map(a => a(0) -> a(1)).toMap
        val revIdMap = idMap.map(_.swap)
        val idsPublishing = Source.fromFile(config.fulltextids).getLines().toSeq
        for(id <- idsPublishing) {
          aids.find(a => a.index == revIdMap(id).toInt) match {
            case Some(aid) =>
              putPDF(id.toInt, aid.pdf.filename, config.pdfdirecory, config.host, config.username, config.password)
            case None =>
              Nil
          }
        }
      case None => Nil
    }
  }

}

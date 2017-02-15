package org.datakind.ci.pdfestrian.scripts

import java.io.{DataInputStream, File, FileInputStream}

import org.json4s.DefaultFormats
import org.json4s.jackson.Serialization._

import scala.io.Source
import scalaj.http.{Http, MultiPart}

/**
  * Created by sameyeam on 2/8/17.
  */
object PopulateFullTexts {
  implicit val formats = DefaultFormats
  def putPDF(id : Int, fileName : String) : Boolean = {
    val file = new File("/Users/sameyeam/ci/included/" + fileName + ".pdf")
    if(file.isFile) {
      val inputStream = new DataInputStream(new FileInputStream(file))
      val byteData = new Array[Byte](file.length().toInt)
      inputStream.readFully(byteData)
      val response = Http(s"http://localhost:5000/api/fulltexts/$id/upload")
        .auth("samanzaroot@gmail.com", "password")
        .postMulti(MultiPart("uploaded_file", fileName + ".pdf", "application/pdf", byteData)).asString
      println(response.body)
      if (response.isError) return false
      val data = read[Response](response.body)
      data.extracted_items.length > 0
    } else false
  }

  def main(args: Array[String]): Unit = {
    val aids = AidSeq.load(args.head)
    val idMap = Source.fromFile(args(1)).getLines().map(_.split("\t"))
      .map(a => a(0) -> a(1)).toMap
    val revIdMap = idMap.map(_.swap)
    val idsPublishing = Source.fromFile(args(2)).getLines().toSeq
    for(id <- idsPublishing) {
       aids.find(a => a.index == revIdMap(id).toInt) match {
         case Some(aid) =>
           putPDF(id.toInt, aid.pdf.filename)
         case None =>
           Nil
       }
    }
  }

}

package org.datakind.ci.pdfestrian.scripts

import org.datakind.ci.pdfestrian.extraction.BiomeMap

import scalaj.http.Http
import org.json4s.{DefaultFormats, NoTypeHints}
import org.json4s.jackson.{Json, Serialization}
import org.json4s.jackson.Serialization.{read, write}

import scala.collection.mutable.ArrayBuffer
import scala.io.Source

/**
  * Created by sameyeam on 2/6/17.
  */

case class Label(label : String, value : Array[String])
case class Response(created_at : String, extracted_items : Array[Label], id : Int, last_updated : String, review_id : Int)
object PopulateLabels {
  implicit val formats = DefaultFormats
  def putLabels(id : Int, labels : Array[Label]) : Boolean = {
    val response = Http(s"http://localhost:5000/api/data_extractions/$id")
      .auth("samanzaroot@gmail.com", "password")
      .header("Content-Type", "application/json")
      .put(write(labels)).asString
    if(response.isError) return false
    val data = read[Response](response.body)
    data.extracted_items.length > 0
  }

  def toLabels(label : String, labels : Array[String]) : Array[Label] = if(labels.nonEmpty)
    Array(Label(label, labels))
  else Array()

  def main(args: Array[String]): Unit = {
    val aids = AidSeq.load(args.head)
    val idMap = Source.fromFile(args.last).getLines().map(_.split("\t"))
      .map(a => a(0) -> a(1)).toMap
    var successful = new ArrayBuffer[Int]()
    val lbm = Map("grasslands" -> "grassland")
    for(aid <- aids) {
       idMap.get(aid.index.toString) match {
         case Some(id) =>
           val biomes = aid.biome.map(_.biome).map(BiomeMap.map).map(_.toLowerCase).distinct.toArray
             .map(e => lbm.getOrElse(e, e))
           val intervs = aid.interv.map(_.Int_type).map(IntervMap.map).distinct.toArray
           val outcomes = aid.outcome.map(_.Outcome).map(OutcomeMap.map).distinct.toArray
           val labels = toLabels("biome", biomes) ++
             toLabels("intervention_type", intervs) ++
             toLabels("outcome_type", outcomes)
           if(putLabels(id.toInt, labels)) {
             successful += id.toInt
             println("added for " + id)
           } else {
             println("failed for " + id)
           }
         case None => Nil
       }
    }
    println(successful.mkString(", "))
  }

}

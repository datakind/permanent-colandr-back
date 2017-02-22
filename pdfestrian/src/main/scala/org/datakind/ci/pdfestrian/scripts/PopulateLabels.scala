package org.datakind.ci.pdfestrian.scripts

import org.datakind.ci.pdfestrian.formats.AidSeq
import org.datakind.ci.pdfestrian.scripts.maps.{BiomeMap, IntervMap, OutcomeMap}

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

/**
  * Populates labels for the default review using the information in original CSV
  */
object PopulateLabels {
  implicit val formats = DefaultFormats

  def putLabels(id: Int, labels: Array[Label], host: String, username: String, password: String): Boolean = {
    val response = Http(s"$host/api/data_extractions/$id")
      .auth(username, password)
      .header("Content-Type", "application/json")
      .put(write(labels)).asString
    if (response.isError) return false
    val data = read[Response](response.body)
    data.extracted_items.length > 0
  }

  def toLabels(label: String, labels: Array[String]): Array[Label] = if (labels.nonEmpty)
    Array(Label(label, labels))
  else Array()

  case class PopulateLabelsConfig(aids: String = "", idMap: String = "", fulltextids: String = "",
                                  host: String = "http://localhost:5000", username: String = "", password: String = "")

  val parser = new scopt.OptionParser[PopulateLabelsConfig]("PopulateLabels") {
    head("PopulateLabels", "0.1")

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

  }


  def main(args: Array[String]): Unit = {
    parser.parse(args, PopulateLabelsConfig()) match {
      case Some(config) =>
        val aids = AidSeq.load(config.aids)
        val idMap = Source.fromFile(config.idMap).getLines().map(_.split("\t"))
          .map(a => a(0) -> a(1)).toMap
        var successful = new ArrayBuffer[Int]()
        val lbm = Map("grasslands" -> "grassland")
        for (aid <- aids) {
          idMap.get(aid.index.toString) match {
            case Some(id) =>
              val biomes = aid.biome.map(_.biome).map(BiomeMap.map).map(_.toLowerCase).distinct.toArray
                .map(e => lbm.getOrElse(e, e))
              val intervs = aid.interv.map(_.Int_type).map(IntervMap.map).distinct.toArray
              val outcomes = aid.outcome.map(_.Outcome).map(OutcomeMap.map).distinct.toArray
              val labels = toLabels("biome", biomes) ++
                toLabels("intervention_type", intervs) ++
                toLabels("outcome_type", outcomes)
              if (putLabels(id.toInt, labels, config.host, config.username, config.password)) {
                successful += id.toInt
                println("added for " + id)
              } else {
                println("failed for " + id)
              }
            case None => Nil
          }
        }
        println(successful.mkString(", "))
      case None =>
        Nil
    }
  }
}
